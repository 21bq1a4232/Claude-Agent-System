# 🚀 Quick Start - Get It Working Now

## The Error You're Seeing

```
Error: Error processing message: 'NoneType' object is not iterable
```

**Cause**: You need to restart BOTH the MCP server and agent with the new code!

---

## ✅ 3-Step Fix (Takes 2 minutes)

### **Step 1: Restart MCP Server** ⭐ IMPORTANT!

**Terminal 1** (Your server terminal):
```bash
# Press Ctrl+C to stop current server

# Then restart:
cd /Users/pranavkrishnadanda/Downloads/Agents/Claude-Agent-System
poetry run python start_server.py
```

**Wait for this message:**
```
INFO: Starting MCP SSE server on 0.0.0.0:8000
INFO: Application startup complete.
```

✅ Keep this terminal running!

---

### **Step 2: Restart Agent**

**Terminal 2** (Your agent terminal):
```bash
# Press Ctrl+C to stop current agent

# Then restart:
poetry run python main.py
```

**Wait for:**
```
✓ MCP server is running
✓ Configuration loaded
✓ Ollama connected (2 models available)
```

---

### **Step 3: Test It!**

In the agent terminal:

```bash
# Switch to working model
>>> /model mistral-nemo:12b-instruct-2407-q2_K

# Test 1: Simple greeting (should be fast)
>>> hi

# Test 2: List files (THE BIG TEST!)
>>> list files in this directory

# Expected output:
# [Agent] Model requested 1 tool call(s)
# [Act] Executing: list_directory
# [Act] Arguments: {'directory': '.'}  ← Should be '.' not 'home'!
# [Act] list_directory - ✓
# 
# Files found:
# - main.py
# - README.md
# - agent/
# - config/
# ...
```

---

## 🎯 If It Works

You should see:
- ✅ Arguments show `{'directory': '.'}`  (not 'home')
- ✅ Tool executes successfully
- ✅ List of files appears

**Then try:**
```bash
>>> read README.md
>>> find all python files
>>> search for "TODO" in all files
```

---

## ⚠️ If It Still Fails

### Problem: Still says "home" instead of "."

**Solution**: Install better model
```bash
# In a NEW terminal (Terminal 3):
ollama pull qwen2.5:7b

# Then in agent:
>>> /model qwen2.5:7b
>>> list files in this directory
```

### Problem: "does not support tools"

**Solution**: Model doesn't support tool calling
```bash
# Use better model:
>>> /model qwen2.5:7b

# Or if that's not available:
ollama pull llama3.2:3b
>>> /model llama3.2:3b
```

### Problem: "Connection refused"

**Solution**: MCP server not running
```bash
# Check Terminal 1 is running
# Should see: "INFO: Application startup complete"

# If not, restart:
poetry run python start_server.py
```

---

## 📊 Quick Check - Is Everything Working?

Run this test sequence:

```bash
# Test 1: Greeting (conversational)
>>> hi
# Should: [Agent] Conversational message detected ✓

# Test 2: List directory (tool calling)
>>> list files here
# Should: [Act] Executing: list_directory ✓
# Should: Arguments: {'directory': '.'} ✓

# Test 3: Read file (tool calling)
>>> read main.py
# Should: [Act] Executing: read_file ✓

# Test 4: Thanks (conversational)
>>> thanks
# Should: [Agent] Conversational message detected ✓
```

**If all 4 pass: YOU'RE DONE! 🎉**

---

## 🔍 Debugging Output

### Good Output (Working):
```
>>> list files in this directory
🤔 Processing your request...

[Agent] Model requested 1 tool call(s)
[Act] Executing: list_directory
[Act] Arguments: {'directory': '.'}  ← CORRECT!
[Act] list_directory - ✓
```

### Bad Output (Not Working):
```
>>> list files in this directory
🤔 Processing your request...
Error: Error processing message: 'NoneType' object is not iterable  ← MCP server not restarted
```

OR

```
[Act] Executing: list_directory
[Act] Arguments: {'directory': 'home'}  ← WRONG! Model not understanding
[Act] list_directory - ✗
[Act] Error: Path does not exist
```

---

## 💡 Pro Tips

### Best Model for Your M4 MacBook:
```bash
ollama pull qwen2.5:7b
>>> /model qwen2.5:7b
```

**Why:**
- Perfect size for 16GB RAM (uses 6GB)
- Fast on Apple Silicon
- Best tool calling support
- Great at understanding context

### Check What's Running:
```bash
# Check MCP server:
curl http://localhost:8000/tools

# Should return:
{"success":true,"tools":["read_file","write_file",...]}

# If 404 or connection refused: MCP server not running!
```

### Model Compatibility:
```
✅ qwen2.5:7b          - BEST (install this!)
✅ mistral-nemo:12b    - GOOD (you have it)
✅ llama3.2:3b         - OK (lightweight)
❌ deepseek-r1:8b      - DON'T USE (no tool support)
```

---

## 🎯 Summary

**If you're getting errors:**
1. ✅ Restart MCP server (Terminal 1)
2. ✅ Restart Agent (Terminal 2)
3. ✅ Switch model to mistral-nemo or qwen2.5
4. ✅ Test: "list files in this directory"

**Expected result:** Should see `{'directory': '.'}`  ← This is correct!

---

**Still stuck?** Share the exact error message and I'll help debug!

