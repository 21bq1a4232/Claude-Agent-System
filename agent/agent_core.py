"""Core agent implementation with agentic loop."""

import asyncio
import uuid
from typing import Any, Dict, List, Optional
from agent.ollama_client import OllamaClient
from agent.context_manager import ContextManager
from agent.error_recovery import ErrorRecoverySystem
from agent.tool_executor import ToolExecutor
from agent.prompts.system_prompt import get_system_prompt


class AgentCore:
    """Core agent with Think -> Plan -> Act -> Observe -> Reflect loop."""

    def __init__(self, config: Dict[str, Any], mcp_server_url: str = "http://localhost:8000"):
        """
        Initialize agent core.

        Args:
            config: Agent configuration
            mcp_server_url: MCP server URL
        """
        self.config = config
        self.agent_config = config.get("agent", {})
        self.loop_config = self.agent_config.get("loop", {})

        # Initialize components
        self.ollama = OllamaClient(config)
        self.context = ContextManager(config)
        self.error_recovery = ErrorRecoverySystem(config)
        self.tool_executor = ToolExecutor(mcp_server_url)

        # Agent state
        self.enabled = self.agent_config.get("enabled", True)
        self.verbose = self.agent_config.get("verbose", True)
        self.max_steps = self.agent_config.get("max_steps", 10)

        # Add system message
        system_prompt = get_system_prompt("main")
        self.context.add_message("system", system_prompt)

    async def process_request(self, user_message: str) -> str:
        """
        Process a user request through the agentic loop.

        Args:
            user_message: User's message

        Returns:
            Agent's response
        """
        # Add user message to context
        self.context.add_message("user", user_message)

        if not self.enabled:
            # Direct mode - no agent loop
            return await self._direct_response(user_message)

        # Agent mode - full agentic loop
        return await self._agentic_loop(user_message)

    async def _direct_response(self, user_message: str) -> str:
        """Generate direct response without agentic loop."""
        messages = self.context.get_messages_for_llm()
        response = await self.ollama.chat(messages)

        assistant_message = response.get("message", {}).get("content", "")
        self.context.add_message("assistant", assistant_message)

        return assistant_message

    async def _agentic_loop(self, user_message: str) -> str:
        """Execute agentic loop (simplified for direct tool execution)."""
        step = 0
        final_response = ""

        while step < self.max_steps:
            step += 1

            # Phase 1: Think (optional - usually disabled to prevent hallucinations)
            if self.loop_config.get("phases", {}).get("think", {}).get("enabled", False):
                thought = await self._think(user_message, step)
                if self.verbose:
                    print(f"\n[Think] {thought}")

            # Phase 2: Plan (optional - usually disabled for direct execution)
            plan = None
            if self.loop_config.get("phases", {}).get("plan", {}).get("enabled", False):
                plan = await self._plan(user_message, step)
                if self.verbose:
                    print(f"\n[Plan] {plan}")

                # Check if we have a complete plan
                if "no further action needed" in plan.lower() or "task complete" in plan.lower():
                    final_response = await self._generate_final_response()
                    break

            # Phase 3: Act (core - directly determine and execute tool)
            if self.loop_config.get("phases", {}).get("act", {}).get("enabled", True):
                # If no plan, pass user message directly for tool selection
                action_result = await self._act_direct(user_message) if not plan else await self._act(plan)
                if self.verbose:
                    action_summary = f"{action_result.get('action', 'unknown')} - {'✓' if action_result.get('success') else '✗'}"
                    print(f"\n[Act] {action_summary}")

            # Phase 4: Observe
            if self.loop_config.get("phases", {}).get("observe", {}).get("enabled", True):
                observation = await self._observe(action_result if 'action_result' in locals() else None)
                if self.verbose and observation.get("error"):
                    print(f"\n[Observe] Error: {observation.get('error')}")

                # Check if task is complete (successful tool execution = done)
                if observation.get("complete", False):
                    final_response = await self._generate_final_response()
                    break

            # Phase 5: Reflect (optional - usually disabled for simpler operation)
            if self.loop_config.get("phases", {}).get("reflect", {}).get("enabled", False):
                reflection = await self._reflect(observation if 'observation' in locals() else None)
                if self.verbose:
                    print(f"\n[Reflect] {reflection}")

        # Generate final response if not already done
        if not final_response:
            final_response = await self._generate_final_response()

        self.context.add_message("assistant", final_response)
        return final_response

    async def _think(self, user_message: str, step: int) -> str:
        """Think phase - analyze the request."""
        prompt = f"""Step {step}: Analyze this request:
{user_message}

What needs to be done? What information is needed?"""

        response = await self.ollama.generate(
            prompt=prompt,
            system=get_system_prompt("system_think"),
        )
        return response

    async def _plan(self, user_message: str, step: int) -> str:
        """Plan phase - create action plan."""
        prompt = f"""Step {step}: Create a plan for:
{user_message}

List the specific actions needed."""

        response = await self.ollama.generate(
            prompt=prompt,
            system=get_system_prompt("system_plan"),
        )
        return response

    async def _act_direct(self, user_request: str) -> Dict[str, Any]:
        """Act phase - directly determine and execute tool from user request."""
        # Direct, concise prompt for tool selection
        tool_selection_prompt = f"""User request: "{user_request}"

Choose the ONE most appropriate tool and respond ONLY with valid JSON (no extra text):

{{
  "tool": "tool_name",
  "arguments": {{...}}
}}

Available tools:
- list_directory(directory=".", pattern=None) - List files in a directory
- read_file(file_path, offset=None, limit=None) - Read file contents
- write_file(file_path, content, create_backup=None) - Write to a file
- edit_file(file_path, old_string, new_string, replace_all=False) - Edit a file
- grep(pattern, path=".", case_insensitive=False, max_results=None) - Search in files
- glob(pattern, path=".", max_results=None) - Find files by pattern
- bash(command, timeout=None, cwd=None) - Execute shell command
- web_fetch(url, timeout=None) - Fetch URL content

Respond with JSON only."""

        try:
            # Get tool call from model
            response = await self.ollama.generate(
                prompt=tool_selection_prompt,
                temperature=0.1,  # Low temperature for more deterministic output
            )

            # Parse JSON response
            import json
            import re

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*?\}', response)
            if not json_match:
                return {
                    "action": "parse_error",
                    "result": f"No JSON found in response: {response[:200]}",
                    "success": False,
                }

            tool_call = json.loads(json_match.group())
            tool_name = tool_call.get("tool")
            arguments = tool_call.get("arguments", {})

            if not tool_name:
                return {
                    "action": "parse_error",
                    "result": "No tool name in response",
                    "success": False,
                }

            # Execute the tool
            result = await self.tool_executor.execute_tool(tool_name, arguments)

            return {
                "action": tool_name,
                "arguments": arguments,
                "result": result,
                "success": result.get("success", False),
            }

        except Exception as e:
            return {
                "action": "error",
                "result": f"Failed to execute: {str(e)}",
                "success": False,
            }

    async def _act(self, plan: Optional[str]) -> Dict[str, Any]:
        """Act phase - execute actions based on plan (fallback when plan phase enabled)."""
        if not plan:
            return {
                "action": "no_plan",
                "result": "No plan provided",
                "success": False,
            }

        # Ask Ollama to generate a tool call based on the plan
        # Build messages with tool execution context
        messages = self.context.get_messages_for_llm()
        messages.append({
            "role": "user",
            "content": f"""Based on this plan: {plan}

Choose ONE tool to execute right now. Respond with a JSON object in this format:
{{
    "tool": "tool_name",
    "arguments": {{
        "param1": "value1",
        "param2": "value2"
    }},
    "reasoning": "why this tool and these arguments"
}}

Available tools:
- read_file(file_path, offset=None, limit=None)
- write_file(file_path, content, create_backup=None)
- edit_file(file_path, old_string, new_string, replace_all=False)
- list_directory(directory=".", pattern=None)
- grep(pattern, path=".", regex=False, case_insensitive=False, context_before=0, context_after=0, max_results=None, file_pattern=None)
- glob(pattern, path=".", max_results=None)
- find(name=None, path=".", file_type=None, max_depth=None)
- bash(command, timeout=None, cwd=None, background=False)
- web_fetch(url, timeout=None)
- web_search(query, max_results=10)

Respond ONLY with the JSON object, no other text."""
        })

        # Get tool call from Ollama
        response = await self.ollama.chat(messages)
        content = response.get("message", {}).get("content", "")

        # Try to parse tool call from response
        import json
        import re

        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                tool_call = json.loads(json_match.group())

                tool_name = tool_call.get("tool")
                arguments = tool_call.get("arguments", {})
                reasoning = tool_call.get("reasoning", "")

                if not tool_name:
                    return {
                        "action": "parse_error",
                        "result": "No tool name in response",
                        "response": content,
                        "success": False,
                    }

                # Execute the tool
                if self.verbose:
                    print(f"\n[Act] Executing: {tool_name}")
                    print(f"[Act] Arguments: {arguments}")
                    print(f"[Act] Reasoning: {reasoning}")

                result = await self.tool_executor.execute_tool(tool_name, arguments)

                return {
                    "action": tool_name,
                    "arguments": arguments,
                    "reasoning": reasoning,
                    "result": result,
                    "success": result.get("success", False),
                }

            else:
                return {
                    "action": "no_tool_call",
                    "result": "No JSON tool call found in response",
                    "response": content,
                    "success": False,
                }

        except json.JSONDecodeError as e:
            return {
                "action": "json_error",
                "result": f"Failed to parse JSON: {str(e)}",
                "response": content,
                "success": False,
            }
        except Exception as e:
            return {
                "action": "error",
                "result": f"Execution failed: {str(e)}",
                "success": False,
            }

    async def _observe(self, action_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Observe phase - analyze results."""
        if not action_result:
            return {"complete": False, "error": None}

        # Check for errors
        if not action_result.get("success", True):
            error = action_result.get("error", {})
            operation_id = str(uuid.uuid4())

            # Try error recovery
            recovery = await self.error_recovery.handle_error(
                error,
                operation_id,
                {"operation": action_result.get("action")},
            )

            return {
                "complete": False,
                "error": error,
                "recovery": recovery,
            }

        # Success
        return {
            "complete": True,
            "error": None,
            "result": action_result.get("result"),
        }

    async def _reflect(self, observation: Optional[Dict[str, Any]]) -> str:
        """Reflect phase - learn from results."""
        if not observation:
            return "No observation to reflect on"

        if observation.get("error"):
            return f"Error encountered: {observation['error']}. Recovery: {observation.get('recovery', {})}"

        return "Action completed successfully"

    async def _generate_final_response(self) -> str:
        """Generate final response to user."""
        messages = self.context.get_messages_for_llm()
        response = await self.ollama.chat(messages)

        return response.get("message", {}).get("content", "Task completed.")

    def toggle_agent_mode(self) -> bool:
        """Toggle agent mode on/off."""
        self.enabled = not self.enabled
        return self.enabled

    def is_enabled(self) -> bool:
        """Check if agent mode is enabled."""
        return self.enabled

    def switch_model(self, model_name: str) -> bool:
        """Switch Ollama model."""
        return self.ollama.switch_model(model_name)

    def get_current_model(self) -> str:
        """Get current model name."""
        return self.ollama.get_current_model()

    def list_models(self) -> List[str]:
        """List available models."""
        return self.ollama.list_models()

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.tool_executor.close()
