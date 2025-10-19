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
        """Execute full agentic loop."""
        step = 0
        final_response = ""

        while step < self.max_steps:
            step += 1

            # Phase 1: Think
            if self.loop_config.get("phases", {}).get("think", {}).get("enabled", True):
                thought = await self._think(user_message, step)
                if self.verbose:
                    print(f"\n[Think] {thought}")

            # Phase 2: Plan
            if self.loop_config.get("phases", {}).get("plan", {}).get("enabled", True):
                plan = await self._plan(user_message, step)
                if self.verbose:
                    print(f"\n[Plan] {plan}")

                # Check if we have a complete plan
                if "no further action needed" in plan.lower() or "task complete" in plan.lower():
                    final_response = await self._generate_final_response()
                    break

            # Phase 3: Act
            if self.loop_config.get("phases", {}).get("act", {}).get("enabled", True):
                action_result = await self._act(plan if 'plan' in locals() else None)
                if self.verbose:
                    print(f"\n[Act] {action_result}")

            # Phase 4: Observe
            if self.loop_config.get("phases", {}).get("observe", {}).get("enabled", True):
                observation = await self._observe(action_result if 'action_result' in locals() else None)
                if self.verbose:
                    print(f"\n[Observe] {observation}")

                # Check if task is complete
                if observation.get("complete", False):
                    final_response = await self._generate_final_response()
                    break

            # Phase 5: Reflect
            if self.loop_config.get("phases", {}).get("reflect", {}).get("enabled", True):
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

    async def _act(self, plan: Optional[str]) -> Dict[str, Any]:
        """Act phase - execute actions."""
        # Simplified: In a full implementation, this would parse the plan
        # and execute actual tool calls

        return {
            "action": "simulated",
            "result": "Action executed (implementation simplified for demo)",
            "success": True,
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
