# Critical Fixes for Local MacBook M4

**Apply these fixes to your local machine to fix the hanging issue**

## Prerequisites

```bash
# 1. Check Ollama version (need >=0.1.17)
ollama --version

# 2. Pull recommended model
ollama pull qwen2.5:7b

# 3. Test model tool calling support
python3 -c "
import ollama
try:
    result = ollama.chat(
        model='qwen2.5:7b',
        messages=[{'role':'user','content':'test'}],
        tools=[{'type':'function','function':{'name':'test','description':'test','parameters':{'type':'object','properties':{}}}}]
    )
    print('✓ Tool calling works!')
except Exception as e:
    print(f'✗ Tool calling failed: {e}')
"
```

---

## Fix 1: Async Wrapper for Ollama Calls (CRITICAL)

### File: `agent/ollama_client.py`

**Location 1**: Around line 85-100 (in `_generate_full` method)

**FIND THIS:**
```python
    async def _generate_full(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate full response (non-streaming)."""
        try:
            response = ollama.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options,
            )
            if isinstance(response, dict):
                return response
            else:
                return {"response": str(response)}
        except Exception as e:
            return {"error": str(e)}
```

**REPLACE WITH:**
```python
    async def _generate_full(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate full response (non-streaming)."""
        import asyncio

        try:
            # Properly wrap synchronous ollama.generate() in thread pool
            response = await asyncio.to_thread(
                ollama.generate,
                model=model,
                prompt=prompt,
                system=system,
                options=options,
            )
            if isinstance(response, dict):
                return response
            else:
                return {"response": str(response)}
        except Exception as e:
            return {"error": str(e)}
```

**Location 2**: Around line 150-170 (in `chat` method)

**FIND THIS:**
```python
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Chat with Ollama model.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature for generation
            tools: List of available tools for function calling

        Returns:
            Chat response
        """
        model = model or self.current_model
        temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)

        options = {
            "temperature": temperature,
            "top_p": self.config.get("top_p", 0.9),
        }

        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "options": options,
            }

            if tools:
                kwargs["tools"] = tools

            response = ollama.chat(**kwargs)
            return response

        except Exception as e:
            return {
                "message": {
                    "role": "assistant",
                    "content": f"Error in chat: {str(e)}",
                },
                "error": True,
            }
```

**REPLACE WITH:**
```python
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Chat with Ollama model.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature for generation
            tools: List of available tools for function calling

        Returns:
            Chat response
        """
        import asyncio

        model = model or self.current_model
        temperature = temperature if temperature is not None else self.config.get("temperature", 0.7)

        options = {
            "temperature": temperature,
            "top_p": self.config.get("top_p", 0.9),
        }

        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "options": options,
            }

            if tools:
                kwargs["tools"] = tools

            # Properly wrap synchronous ollama.chat() in thread pool
            response = await asyncio.to_thread(ollama.chat, **kwargs)
            return response

        except Exception as e:
            return {
                "message": {
                    "role": "assistant",
                    "content": f"Error in chat: {str(e)}",
                },
                "error": True,
            }
```

---

## Fix 2: Add Timeout & Debug Logging

### File: `agent/agent_core.py`

**Location**: Around line 288-300 (in `_agentic_loop` method)

**FIND THIS:**
```python
            if self.verbose:
                print("\n[Agent] Analyzing request and selecting tools...")

            # Make single chat call with tools
            messages = self.context.get_messages_for_llm()
            response = await self.ollama.chat(messages, tools=tools if tools else None)
```

**REPLACE WITH:**
```python
            if self.verbose:
                print("\n[Agent] Analyzing request and selecting tools...")
                print(f"[Agent] Available tools: {len(tools) if tools else 0}")
                print(f"[Agent] Current model: {self.ollama.current_model}")

            # Make single chat call with tools (with timeout and debug logging)
            messages = self.context.get_messages_for_llm()

            # Add timeout to prevent infinite hangs (default 15s for testing)
            timeout = self.agent_config.get("llm_timeout", 15)

            if self.verbose:
                print(f"[DEBUG] Calling ollama.chat() with {timeout}s timeout...", end="", flush=True)

            try:
                response = await asyncio.wait_for(
                    self.ollama.chat(messages, tools=tools if tools else None),
                    timeout=timeout
                )
                if self.verbose:
                    print(" COMPLETED ✓")
            except asyncio.TimeoutError:
                if self.verbose:
                    print(f" TIMEOUT ✗")
                print(f"\n[Agent] LLM call timed out after {timeout}s")
                print(f"[Agent] This may indicate:")
                print(f"  - Model struggling with tool definitions")
                print(f"  - Model doesn't support tool calling")
                print(f"  - Ollama service issue")
                print(f"\n[Agent] Falling back to direct chat mode...")
                return await self._direct_response(user_message)
```

---

## Fix 3: Update Config Timeout

### File: `config/agent_config.yaml`

**FIND THIS (around line 27-30):**
```yaml
  # Enable streaming for faster responses (like ollama run)
  stream_responses: true
```

**ADD AFTER:**
```yaml
  # Enable streaming for faster responses (like ollama run)
  stream_responses: true

  # Timeout for LLM calls in seconds (15s for testing, prevents infinite hangs)
  llm_timeout: 15

  # Timeout for tool execution in seconds
  tool_timeout: 30
```

---

## Fix 4: Reduce Tool Count (Temporary, for testing)

### File: `agent/agent_core.py`

**Location**: Around line 136 (in `_get_tools_for_ollama` method)

**FIND THIS:**
```python
        # Tool parameter definitions (optimized for Claude Code-like behavior)
        tool_definitions = {
            "read_file": {
                "description": "Read contents of a file. Use the exact file path provided by the user.",
                # ... rest of definition
            },
            "write_file": {
                # ...
            },
            "list_directory": {
                # ...
            },
            "bash": {
                # ...
            },
            "grep": {
                # ...
            },
            "glob": {
                # ...
            },
            "edit_file": {
                # ...
            }
        }
```

**REPLACE WITH (temporarily remove grep, glob, edit_file):**
```python
        # Tool parameter definitions (REDUCED for testing - only 4 core tools)
        tool_definitions = {
            "read_file": {
                "description": "Read contents of a file. Use the exact file path provided by the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "write_file": {
                "description": "Write content to a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            },
            "list_directory": {
                "description": "List files and directories. Use '.' for current directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directory path. Use '.' for current directory"
                        }
                    },
                    "required": ["directory"]
                }
            },
            "bash": {
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
            # Removed: grep, glob, edit_file (add back later after testing)
        }
```

---

## Testing Procedure

### 1. Apply All Fixes Above

### 2. Test Basic Model Response
```bash
cd ~/Downloads/Agents/Claude-Agent-System
poetry run python main.py
```

In agent terminal:
```
/model qwen2.5:7b
>>> hello
```

**Expected**: Should respond quickly (1-2s)

### 3. Test Tool Calling
```
>>> list files in this directory
```

**Expected Output**:
```
🤔 Processing your request...
[Agent] Analyzing request and selecting tools...
[Agent] Available tools: 4
[Agent] Current model: qwen2.5:7b
[DEBUG] Calling ollama.chat() with 15s timeout... COMPLETED ✓
⚙️ Executing: list_directory...
[Agent] Generating final response...

Here are the files in the current directory:
- main.py
- README.md
...
```

### 4. Test File Read
```
>>> read CLAUDE.md
```

**Expected**: Intelligent summary (not raw dump) in <10s

---

## Troubleshooting

### Still Hangs at "Calling ollama.chat()..."?

**Option A**: Disable tool calling temporarily
```python
# In agent/agent_core.py, line ~290
# Change this line:
response = await self.ollama.chat(messages, tools=tools if tools else None)

# To this (NO tools):
response = await self.ollama.chat(messages)  # Test without tools first
```

### Timeout After 15s?

**Check Ollama**:
```bash
# Is Ollama running?
ps aux | grep ollama

# Restart Ollama
killall ollama
ollama serve &

# Test direct
ollama run qwen2.5:7b "hello"
```

### Model Doesn't Support Tools?

**Try different model**:
```bash
ollama pull llama3.1:8b
/model llama3.1:8b
```

---

## Success Criteria

✅ Agent responds in <5s for simple queries
✅ Tool calling completes in <15s
✅ No infinite hangs
✅ Clear timeout errors if something fails
✅ Intelligent summaries (not raw dumps)

---

## After Testing Works

1. **Increase timeout back**: Change `llm_timeout: 15` → `llm_timeout: 60`
2. **Re-enable all tools**: Add back grep, glob, edit_file
3. **Set verbose: false**: In `config/agent_config.yaml` for cleaner output

---

## Quick Apply Script

Save this as `apply_fixes.sh` and run:

```bash
#!/bin/bash
echo "Backing up files..."
cp agent/ollama_client.py agent/ollama_client.py.backup
cp agent/agent_core.py agent/agent_core.py.backup
cp config/agent_config.yaml config/agent_config.yaml.backup

echo "✓ Backups created"
echo "Now manually apply the fixes from LOCAL_MACHINE_FIXES.md"
echo "Or use git to pull latest changes if available"
```
