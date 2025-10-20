# 🚀 Apply Fixes to Your MacBook M4

**Quick guide to fix the hanging issue on your local machine**

---

## Step 1: Download These Files to Your MacBook

Copy these files from this Cloud9 environment to your local MacBook:

```bash
# On your MacBook, in the project directory:
cd ~/Downloads/Agents/Claude-Agent-System

# Download the guide and test script
# (Copy LOCAL_MACHINE_FIXES.md and test_fixes.py from this repo)
```

---

## Step 2: Install Recommended Model

```bash
# Pull the best model for M4 16GB
ollama pull qwen2.5:7b

# Verify it works
ollama run qwen2.5:7b "hello"
```

---

## Step 3: Run Diagnostic Test (BEFORE fixes)

```bash
# Make test script executable
chmod +x test_fixes.py

# Run it
python3 test_fixes.py
```

**Expected**: Some tests will FAIL (that's OK - we'll fix them)

---

## Step 4: Apply Critical Fixes

Open `LOCAL_MACHINE_FIXES.md` and apply **at minimum**:

### ✅ **MUST DO** (Fixes hanging):
1. **Fix 1**: Add `asyncio.to_thread()` wrapper (2 locations in `agent/ollama_client.py`)
2. **Fix 2**: Add timeout + debug logging (`agent/agent_core.py`)
3. **Fix 3**: Update timeout config (`config/agent_config.yaml`)

### 📋 **RECOMMENDED** (Better debugging):
4. **Fix 4**: Reduce tool count to 4 tools (temporary)

### ⏭️ **OPTIONAL** (Can do later):
5. Apply advanced system prompt
6. Add comprehensive logging

---

## Step 5: Run Diagnostic Test (AFTER fixes)

```bash
python3 test_fixes.py
```

**Expected**: All tests should PASS ✓

---

## Step 6: Test the Agent

```bash
# Start agent
poetry run python main.py

# In the agent terminal:
/model qwen2.5:7b

# Test 1: Simple chat
>>> hello

# Expected: Quick response (1-2s)

# Test 2: Tool calling
>>> list files in this directory

# Expected:
# - Shows debug output
# - Completes in <15s
# - Lists files intelligently
```

---

## What Each Fix Does

| Fix | Purpose | Impact if Skipped |
|-----|---------|-------------------|
| Fix 1: `asyncio.to_thread()` | Prevents blocking the event loop | **Agent hangs forever** |
| Fix 2: Timeout + logging | Fails fast, shows what's happening | Hangs with no visibility |
| Fix 3: Config timeout | Sets aggressive timeout for testing | Uses default 60s (too long) |
| Fix 4: Reduce tools | Faster tool processing | May still work but slower |

---

## Troubleshooting

### ❓ Still hangs after applying fixes?

**Check 1**: Did you apply Fix 1 correctly?
```bash
grep -n "asyncio.to_thread" agent/ollama_client.py
```
Should show **2 lines** (around line 90 and line 163)

**Check 2**: Is the timeout configured?
```bash
grep "llm_timeout" config/agent_config.yaml
```
Should show: `llm_timeout: 15`

**Check 3**: Test Ollama directly
```bash
python3 -c "
import ollama
import time
start = time.time()
result = ollama.chat(model='qwen2.5:7b', messages=[{'role':'user','content':'hi'}])
print(f'Completed in {time.time()-start:.2f}s')
"
```
Should complete in <3s

---

### ❓ Timeout after 15s?

**Model may not support tools** - Try without tools:

In `agent/agent_core.py`, line ~290, temporarily change:
```python
# BEFORE:
response = await asyncio.wait_for(
    self.ollama.chat(messages, tools=tools if tools else None),
    timeout=timeout
)

# AFTER (test without tools):
response = await asyncio.wait_for(
    self.ollama.chat(messages),  # NO TOOLS
    timeout=timeout
)
```

If this works, your model doesn't support tool calling → Try `llama3.1:8b`

---

### ❓ Getting errors about missing modules?

```bash
# Reinstall dependencies
poetry install

# Or with pip
pip install -r requirements.txt
```

---

## Success Checklist

After applying fixes, you should have:

- [x] `qwen2.5:7b` or `llama3.1:8b` model installed
- [x] `asyncio.to_thread()` in 2 places (`agent/ollama_client.py`)
- [x] Timeout and debug logging added (`agent/agent_core.py`)
- [x] `llm_timeout: 15` in config (`config/agent_config.yaml`)
- [x] All tests pass: `python3 test_fixes.py`
- [x] Agent responds quickly to simple queries
- [x] Tool calling works (lists files, reads files, etc.)

---

## Next Steps After It Works

1. **Increase timeout**: Change `llm_timeout: 15` → `60` in config
2. **Add more tools back**: Un-comment grep, glob, edit_file in `agent_core.py`
3. **Disable verbose mode**: Set `verbose: false` in config for cleaner output
4. **Apply advanced features**: System prompt improvements, logging, etc.

---

## Need Help?

Check logs:
```bash
# If logs directory exists
tail -f logs/mcp_tools.log
tail -f logs/agent.log
```

Or run with full debug:
```bash
# Set in config/agent_config.yaml
verbose: true

# And in config/tools_config.yaml
logging:
  level: "DEBUG"
```

---

## Quick Reference: File Locations

```
Your Local MacBook:
~/Downloads/Agents/Claude-Agent-System/
├── agent/
│   ├── ollama_client.py     ← Fix 1 (2 locations)
│   └── agent_core.py         ← Fix 2 + Fix 4
├── config/
│   └── agent_config.yaml     ← Fix 3
├── LOCAL_MACHINE_FIXES.md    ← Detailed fixes
└── test_fixes.py             ← Run to verify
```

---

## Final Test Commands

```bash
# 1. Apply all fixes from LOCAL_MACHINE_FIXES.md

# 2. Run tests
python3 test_fixes.py

# 3. Start agent
poetry run python main.py

# 4. Switch model
/model qwen2.5:7b

# 5. Test
>>> list files in this directory
>>> read README.md
```

**Expected behavior**: Fast, intelligent responses with no hanging!

---

Good luck! 🚀
