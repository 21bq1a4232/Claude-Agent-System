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
        
        # Cache for available tools (fetched dynamically)
        self._available_tools_cache: Optional[List[str]] = None

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
        """Generate direct response without agentic loop (with streaming)."""
        messages = self.context.get_messages_for_llm()
        
        # Use streaming for faster perceived response
        if self.agent_config.get("stream_responses", True):
            full_response = ""
            # chat_stream() is a synchronous generator (ollama lib is sync)
            for chunk in self.ollama.chat_stream(messages):
                print(chunk, end="", flush=True)
                full_response += chunk
            print()  # New line after streaming
            
            self.context.add_message("assistant", full_response)
            return full_response
        else:
            # Non-streaming fallback
            response = await self.ollama.chat(messages)
            assistant_message = response.get("message", {}).get("content", "")
            self.context.add_message("assistant", assistant_message)
            return assistant_message

    def _is_conversational(self, message: str) -> bool:
        """
        Check if message is conversational (doesn't need tools).
        Uses simple heuristics - let the LLM decide for ambiguous cases.
        
        Args:
            message: User's message
            
        Returns:
            True if obviously conversational, False if might need tools
        """
        message_lower = message.lower().strip()
        
        # Very simple greetings and responses (no tool needed)
        simple_greetings = ["hi", "hello", "hey", "thanks", "thank you", "bye", "yes", "no", "ok", "okay"]
        
        # If it's just a greeting, it's conversational
        if message_lower in simple_greetings:
            return True
        
        # If message starts with greeting and is very short
        for greeting in simple_greetings:
            if message_lower.startswith(greeting) and len(message_lower.split()) <= 2:
                return True
        
        # Everything else - let the LLM and tools handle it
        # The model will decide if tools are needed
        return False

    async def _get_tools_for_ollama(self) -> List[Dict[str, Any]]:
        """
        Get tools in Ollama tool calling format.
        
        Returns:
            List of tool definitions for Ollama
        """
        available_tools = await self._get_available_tools()
        
        # Ensure we have a valid list
        if not available_tools:
            if self.verbose:
                print("[Agent] Warning: No tools available, using fallback set")
            available_tools = ["read_file", "write_file", "list_directory", "bash", "grep", "glob"]
        
        # Convert to Ollama format (simplified - Ollama uses function calling format)
        ollama_tools = []
        
        # Tool parameter definitions (optimized for Claude Code-like behavior)
        tool_definitions = {
            "read_file": {
                "description": "Read contents of a file. Use the exact file path provided by the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string", 
                            "description": "Path to the file to read (e.g., 'main.py', './config/settings.yaml')"
                        },
                        "offset": {
                            "type": "integer", 
                            "description": "Optional: Line number to start reading from (1-indexed)"
                        },
                        "limit": {
                            "type": "integer", 
                            "description": "Optional: Maximum number of lines to read"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "write_file": {
                "description": "Write content to a file. Creates the file if it doesn't exist.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string", 
                            "description": "Path to the file to write (e.g., 'output.txt')"
                        },
                        "content": {
                            "type": "string", 
                            "description": "Content to write to the file"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            "list_directory": {
                "description": "List files and directories. IMPORTANT: Use '.' for current directory, not 'home' or other names.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string", 
                            "description": "Directory path. Use '.' for current/this directory, '..' for parent, or specify a path like './src'"
                        },
                        "pattern": {
                            "type": "string", 
                            "description": "Optional: Glob pattern to filter results (e.g., '*.py', '*.txt')"
                        }
                    },
                    "required": ["directory"]
                }
            },
            "bash": {
                "description": "Execute a shell command in the current directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string", 
                            "description": "Shell command to execute (e.g., 'ls -la', 'pwd', 'git status')"
                        }
                    },
                    "required": ["command"]
                }
            },
            "grep": {
                "description": "Search for text patterns in files (like ripgrep). Use '.' to search in current directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string", 
                            "description": "Text pattern to search for"
                        },
                        "path": {
                            "type": "string", 
                            "description": "Path to search in. Use '.' for current directory (default: '.')"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            "glob": {
                "description": "Find files matching a pattern. Use '.' to search from current directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g., '**/*.py' for all Python files, '*.txt' for text files)"
                        },
                        "path": {
                            "type": "string",
                            "description": "Base directory to search from. Use '.' for current directory (default: '.')"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            "edit_file": {
                "description": "Edit a file by replacing text. Use for making changes to existing files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to edit"
                        },
                        "old_string": {
                            "type": "string",
                            "description": "Exact text to find and replace"
                        },
                        "new_string": {
                            "type": "string",
                            "description": "New text to replace with"
                        }
                    },
                    "required": ["file_path", "old_string", "new_string"]
                }
            }
        }
        
        for tool_name in available_tools:
            if tool_name in tool_definitions:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_definitions[tool_name]["description"],
                        "parameters": tool_definitions[tool_name]["parameters"]
                    }
                })
        
        return ollama_tools

    async def _agentic_loop(self, user_message: str) -> str:
        """Execute agentic loop with native Ollama tool calling (optimized)."""
        # Check if message is conversational
        if self._is_conversational(user_message):
            if self.verbose:
                print("\n[Agent] Conversational message detected, responding directly")
            return await self._direct_response(user_message)
        
        try:
            # Use native Ollama tool calling for single LLM call
            # Get available tools in Ollama format
            tools = await self._get_tools_for_ollama()
            
            # Make single chat call with tools
            messages = self.context.get_messages_for_llm()
            response = await self.ollama.chat(messages, tools=tools if tools else None)
            
            # Check for errors in response
            if response.get("error"):
                error_msg = response.get("message", {}).get("content", str(response.get("error")))
                if self.verbose:
                    print(f"\n[Agent] Error from model: {error_msg}")
                # Fall back to direct response if tool calling not supported
                return await self._direct_response(user_message)
            
            message = response.get("message", {})
            
            # Check if model wants to use tools
            tool_calls = message.get("tool_calls", [])
            
            # Ensure tool_calls is iterable
            if tool_calls is None:
                tool_calls = []
            
            if tool_calls and self.verbose:
                print(f"\n[Agent] Model requested {len(tool_calls)} tool call(s)")
            
            # Execute any tool calls
            tool_results = []
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                tool_name = function.get("name")
                arguments = function.get("arguments", {})
                
                if self.verbose:
                    print(f"\n[Act] Executing: {tool_name}")
                    print(f"[Act] Arguments: {arguments}")
                
                try:
                    result = await self.tool_executor.execute_tool(tool_name, arguments)
                    tool_results.append({
                        "tool": tool_name,
                        "result": result,
                        "success": result.get("success", False)
                    })
                    
                    if self.verbose:
                        status = "✓" if result.get("success") else "✗"
                        print(f"[Act] {tool_name} - {status}")
                        if not result.get("success"):
                            err = result.get("error", "Unknown error")
                            print(f"[Act] Error: {err}")
                            
                except Exception as e:
                    tool_results.append({
                        "tool": tool_name,
                        "result": None,
                        "success": False,
                        "error": str(e)
                    })
                    if self.verbose:
                        print(f"[Act] {tool_name} - ✗ (Exception: {e})")
            
            # If tools were called, add tool results to context and get final response
            if tool_results:
                # Format tool results properly for the model to process
                tool_results_formatted = []
                for r in tool_results:
                    tool_info = {
                        "tool": r['tool'],
                        "success": r['success'],
                    }
                    if r['success']:
                        # Include the actual result data
                        tool_info["data"] = r.get('result', {})
                    else:
                        tool_info["error"] = r.get('error', 'Unknown error')
                    tool_results_formatted.append(tool_info)
                
                # Add tool results to context in a structured way
                import json
                tool_results_json = json.dumps(tool_results_formatted, indent=2)
                self.context.add_message("system", f"Tool execution completed. Here are the results:\n{tool_results_json}\n\nNow format this data in a clear, user-friendly way for the user.")
                
                if self.verbose:
                    print(f"\n[Agent] Generating final response based on tool results...")
                
                # Get final response from model with streaming
                if self.agent_config.get("stream_responses", True):
                    print()  # New line before streaming
                    final_response = ""
                    # chat_stream() is a synchronous generator (ollama lib is sync)
                    for chunk in self.ollama.chat_stream(self.context.get_messages_for_llm()):
                        print(chunk, end="", flush=True)
                        final_response += chunk
                    print()  # New line after streaming
                else:
                    final_response = await self._generate_final_response()
            else:
                # No tools called, use model's direct response
                final_response = message.get("content", "Task completed.")
            
            self.context.add_message("assistant", final_response)
            return final_response
            
        except Exception as e:
            # Catch any errors in the tool calling flow
            if self.verbose:
                print(f"\n[Agent] Error in agentic loop: {e}")
            # Fall back to direct response
            return await self._direct_response(user_message)

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

    async def _get_available_tools(self) -> List[str]:
        """
        Get available tools from MCP server (with caching).
        
        Returns:
            List of tool names
        """
        if self._available_tools_cache is None:
            try:
                self._available_tools_cache = await self.tool_executor.list_tools()
            except Exception as e:
                if self.verbose:
                    print(f"[Agent] Warning: Could not fetch tools from MCP server: {e}")
                # Fallback to basic set
                self._available_tools_cache = [
                    "read_file", "write_file", "edit_file", "list_directory",
                    "grep", "glob", "bash", "web_fetch"
                ]
        return self._available_tools_cache

    async def _act_direct(self, user_request: str) -> Dict[str, Any]:
        """Act phase - directly determine and execute tool from user request."""
        # Get available tools dynamically
        available_tools = await self._get_available_tools()
        
        # Build tool descriptions
        tool_list = "\n".join([f"- {tool}" for tool in available_tools])
        
        # Direct, concise prompt for tool selection
        tool_selection_prompt = f"""User request: "{user_request}"

Choose the ONE most appropriate tool and respond ONLY with valid JSON (no extra text):

{{
  "tool": "tool_name",
  "arguments": {{...}}
}}

Available tools:
{tool_list}

Respond with JSON only."""

        try:
            # Get tool call from model
            response = await self.ollama.generate(
                prompt=tool_selection_prompt,
                temperature=0.1,  # Low temperature for more deterministic output
            )

            # Parse JSON response from Ollama
            # generate() returns: {"response": "text"}
            if isinstance(response, dict):
                response_text = response.get("response", "")
                if not response_text:
                    # Fallback for chat() format: {"message": {"content": "text"}}
                    response_text = response.get("message", {}).get("content", "")
            else:
                response_text = str(response)

            # Extract JSON from response text
            import json
            import re

            # Find JSON object in response
            json_match = re.search(r'\{[\s\S]*?\}', response_text)
            if not json_match:
                return {
                    "action": "parse_error",
                    "error": f"No JSON found in response: {response[:200]}",
                    "success": False,
                }

            tool_call = json.loads(json_match.group())
            tool_name = tool_call.get("tool")
            arguments = tool_call.get("arguments", {})

            if not tool_name:
                return {
                    "action": "parse_error",
                    "error": "No tool name in response",
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
                "error": f"Failed to execute: {str(e)}",
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
                        "error": "No tool name in response",
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
                    "error": "No JSON tool call found in response",
                    "response": content,
                    "success": False,
                }

        except json.JSONDecodeError as e:
            return {
                "action": "json_error",
                "error": f"Failed to parse JSON: {str(e)}",
                "response": content,
                "success": False,
            }
        except Exception as e:
            return {
                "action": "error",
                "error": f"Execution failed: {str(e)}",
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
