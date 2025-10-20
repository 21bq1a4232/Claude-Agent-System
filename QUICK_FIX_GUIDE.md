# 🚀 QUICK FIX GUIDE - 3 Minutes to Working Agent

**Copy these files to your MacBook and run the automated fix script**

---

## 📦 Files You Need (Download from this repo)

```
Claude-Agent-System/
├── auto_fix.py                    ← Automated fix script (RUN THIS!)
├── test_fixes.py                  ← Verify fixes worked
├── critical_fixes.patch           ← Git patch (alternative method)
├── LOCAL_MACHINE_FIXES.md         ← Manual fix guide (if needed)
└── APPLY_ON_LOCAL_MACHINE.md      ← Detailed walkthrough
```

---

## ⚡ Method 1: Automated Fix (RECOMMENDED - 30 seconds)

### On Your MacBook:

```bash
# 1. Go to project directory
cd ~/Downloads/Agents/Claude-Agent-System

# 2. Run automated fix script
python3 auto_fix.py
```

**That's it!** The script will:
- ✅ Backup all files
- ✅ Apply asyncio.to_thread() wrapper
- ✅ Add timeout & debug logging
- ✅ Update config with timeouts

**Output you should see:**
```
==================================================================
  CLAUDE AGENT SYSTEM - AUTOMATED FIX SCRIPT
==================================================================

✓ All required files found

📝 Fixing agent/ollama_client.py...
   ✓ Backup created: agent/ollama_client.py.backup_20250120_143022
   ✓ Fixed: Added asyncio.to_thread() wrapper

📝 Fixing agent/agent_core.py...
   ✓ Backup created: agent/agent_core.py.backup_20250120_143022
   ✓ Fixed: Added timeout and debug logging

📝 Fixing config/agent_config.yaml...
   ✓ Backup created: config/agent_config.yaml.backup_20250120_143022
   ✓ Fixed: Added timeout configuration

==================================================================
  ✓ ALL FIXES APPLIED SUCCESSFULLY!
==================================================================
```

---

## 🧪 Verify Fixes Worked

```bash
# Run test script
python3 test_fixes.py
```

**Expected output:**
```
✓ PASS - Ollama Connection
✓ PASS - Tool Calling Support
✓ PASS - Async Wrapper
✓ PASS - Timeout Config
✓ PASS - Debug Logging
✓ PASS - Simple Query

6 passed, 0 failed, 0 skipped

✓ ALL TESTS PASSED - Ready to run agent!
```

---

## 🎯 Test the Agent

```bash
# 1. Install recommended model
ollama pull qwen2.5:7b

# 2. Start agent
poetry run python main.py

# 3. In agent terminal - switch model
/model qwen2.5:7b

# 4. Test simple query
>>> hello

# Expected: Quick response (1-2s)

# 5. Test tool calling
>>> list files in this directory

# Expected:
# [Agent] Analyzing request and selecting tools...
# [Agent] Available tools: 4
# [DEBUG] Calling ollama.chat() with 15s timeout... COMPLETED ✓
# ⚙️ Executing: list_directory...
# [Lists files intelligently]
```

---

## 🔄 Method 2: Git Patch (Alternative)

```bash
cd ~/Downloads/Agents/Claude-Agent-System

# Apply patch
git apply critical_fixes.patch

# If you get errors, try:
patch -p1 < critical_fixes.patch
```

---

## 🛠️ Method 3: Manual Fix (If automated fails)

Read and follow: `LOCAL_MACHINE_FIXES.md`

---

## ❓ Troubleshooting

### Script says "Already fixed"?
✓ Good! Fixes already applied. Continue to testing.

### Script fails with import errors?
```bash
poetry install
# or
pip install pyyaml
```

### Test script fails?
Check specific test output and consult `LOCAL_MACHINE_FIXES.md`

### Agent still hangs?
1. Verify async wrapper was applied:
   ```bash
   grep -n "asyncio.to_thread" agent/ollama_client.py
   ```
   Should show 2 lines

2. Try different model:
   ```bash
   ollama pull llama3.1:8b
   /model llama3.1:8b
   ```

3. Check Ollama is running:
   ```bash
   ollama list
   ```

---

## 📊 Before vs After

### Before (❌ Hanging):
```
>>> list files in this directory
🤔 Processing your request...
[Agent] Analyzing request and selecting tools...
[HANGS FOREVER - NO OUTPUT]
```

### After (✅ Working):
```
>>> list files in this directory
🤔 Processing your request...
[Agent] Analyzing request and selecting tools...
[Agent] Available tools: 4
[Agent] Current model: qwen2.5:7b
[DEBUG] Calling ollama.chat() with 15s timeout... COMPLETED ✓
⚙️ Executing: list_directory...

Here are the files in the current directory:
- main.py
- README.md
- CLAUDE.md
[Intelligent summary...]
```

---

## ✅ Success Checklist

After running `auto_fix.py` and `test_fixes.py`:

- [ ] Backups created (*.backup_* files exist)
- [ ] All tests pass (`python3 test_fixes.py`)
- [ ] Model installed (`ollama list` shows qwen2.5:7b)
- [ ] Agent starts (`poetry run python main.py`)
- [ ] Simple queries work (`>>> hello`)
- [ ] Tool calling works (`>>> list files in this directory`)
- [ ] No hanging (completes in <15s or shows timeout)

---

## 🎉 What You Get

After fixes:
- ⚡ **Fast responses** (1-3s for simple queries)
- 🛠️ **Working tool calling** (reads files, lists directories, etc.)
- 🧠 **Intelligent summaries** (not raw dumps)
- ⏱️ **No more infinite hangs** (15s timeout)
- 📊 **Debug visibility** (see what's happening)
- 🔍 **Full logging** (logs/mcp_tools.log for debugging)

---

## 📞 Still Need Help?

1. **Check logs**:
   ```bash
   tail -f logs/mcp_tools.log
   tail -f logs/agent.log
   ```

2. **Enable full debug**:
   - In `config/agent_config.yaml`: Set `verbose: true`
   - In `config/tools_config.yaml`: Set `level: "DEBUG"`

3. **Review detailed guide**: `LOCAL_MACHINE_FIXES.md`

---

## 🚀 Final Command Sequence

```bash
# Complete fix in 5 commands:
cd ~/Downloads/Agents/Claude-Agent-System
python3 auto_fix.py
python3 test_fixes.py
ollama pull qwen2.5:7b
poetry run python main.py
```

Then in agent:
```
/model qwen2.5:7b
>>> list files in this directory
```

**Done!** 🎉

---

_All files include automatic backups. If something goes wrong, restore from .backup_* files._
