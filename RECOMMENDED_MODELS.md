# 🤖 Recommended Models for MacBook M4 (16GB RAM)

## Quick Start

**Switch to your existing model immediately:**
```bash
>>> /model mistral-nemo:12b-instruct-2407-q2_K
```

Then test:
```bash
>>> list files in this directory
```

---

## Top 3 Models for Your Hardware

### 🥇 **qwen2.5:7b** (Best Overall)
```bash
# Install
ollama pull qwen2.5:7b

# Use in agent
>>> /model qwen2.5:7b
```

**Specs:**
- Size: 4.7GB
- RAM: ~6GB during inference
- Speed: Very fast on M4
- Tool Calling: ✅ Full support
- Quality: Excellent for coding, tool usage, general chat

**Why it's best:**
- Designed for tool calling
- Fast inference on Apple Silicon
- Great at following instructions
- Handles complex tasks well

---

### 🥈 **mistral-nemo:12b-instruct-2407-q2_K** (You Have This!)
```bash
>>> /model mistral-nemo:12b-instruct-2407-q2_K
```

**Specs:**
- Size: 4.8GB
- RAM: ~6-7GB during inference
- Speed: Fast on M4
- Tool Calling: ✅ Supported
- Quality: Excellent instruction following

**Why it's good:**
- Already installed on your system
- Reliable tool calling
- Good at understanding context
- Works well with MCP tools

---

### 🥉 **llama3.2:3b** (Fastest)
```bash
# Install
ollama pull llama3.2:3b

# Use
>>> /model llama3.2:3b
```

**Specs:**
- Size: 2GB
- RAM: ~3-4GB during inference
- Speed: Extremely fast
- Tool Calling: ✅ Supported
- Quality: Good for simple tasks

**Why it's good:**
- Lightning fast responses
- Low memory usage
- Good enough for most tasks
- Great for quick interactions

---

## Detailed Comparison Table

| Model | Size | RAM | Speed | Tool Support | Quality | Best For |
|-------|------|-----|-------|--------------|---------|----------|
| **qwen2.5:7b** | 4.7GB | 6GB | ⚡⚡⚡ | ✅ Yes | ⭐⭐⭐⭐⭐ | Everything |
| **mistral-nemo:12b** | 4.8GB | 7GB | ⚡⚡⚡ | ✅ Yes | ⭐⭐⭐⭐ | General use |
| **llama3.2:3b** | 2GB | 4GB | ⚡⚡⚡⚡⚡ | ✅ Yes | ⭐⭐⭐ | Quick tasks |
| **qwen2.5:3b** | 2GB | 3GB | ⚡⚡⚡⚡ | ✅ Yes | ⭐⭐⭐⭐ | Lightweight |
| deepseek-r1:8b ❌ | 5.2GB | 8GB | ⚡⚡ | ❌ NO | ⭐⭐⭐⭐ | Not for tools |

---

## Performance on M4 MacBook (16GB RAM)

### qwen2.5:7b Performance
- **Simple chat**: ~2-3 seconds
- **Tool calling**: ~5-8 seconds
- **Complex tasks**: ~10-15 seconds
- **Memory**: 6GB used, 10GB free
- **Battery**: Good efficiency

### mistral-nemo:12b Performance
- **Simple chat**: ~3-4 seconds
- **Tool calling**: ~6-10 seconds
- **Complex tasks**: ~12-18 seconds
- **Memory**: 7GB used, 9GB free
- **Battery**: Moderate efficiency

### llama3.2:3b Performance
- **Simple chat**: ~1-2 seconds
- **Tool calling**: ~3-5 seconds
- **Complex tasks**: ~8-12 seconds
- **Memory**: 4GB used, 12GB free
- **Battery**: Excellent efficiency

---

## Models to AVOID

### ❌ deepseek-r1 (Any version)
**Problems:**
- No tool calling support
- Outputs `<think>` tags that break parsing
- Designed for reasoning, not tool execution
- Slower inference

**Error you'll see:**
```
Error in chat: registry.ollama.ai/library/deepseek-r1:8b does not support tools (status code: 400)
```

### ❌ Other "Reasoning" Models
- qwq:*
- deepseek-r1:*
- Any model with "reasoning" in description

**Why:** They output their thinking process, which interferes with tool calling.

---

## Installation Commands

```bash
# Recommended: Install all three for flexibility
ollama pull qwen2.5:7b
ollama pull llama3.2:3b
ollama pull qwen2.5:3b

# Alternative: Just install the best one
ollama pull qwen2.5:7b
```

---

## How to Switch Models

### In the Agent
```bash
>>> /model qwen2.5:7b
ℹ Switched to model: qwen2.5:7b

>>> /model
# Shows available models
```

### In Config (Persistent)
Edit `config/agent_config.yaml`:
```yaml
agent:
  default_model: "qwen2.5:7b"  # Change this line
```

---

## Testing Your Model

After switching, test with these commands:

### Test 1: Simple Chat
```bash
>>> hi
# Should respond in 2-3 seconds
```

### Test 2: Tool Calling
```bash
>>> list files in this directory
# Should execute list_directory tool
```

### Test 3: File Reading
```bash
>>> read README.md
# Should execute read_file tool
```

### Test 4: Search
```bash
>>> search for "TODO" in all python files
# Should execute grep tool
```

---

## Optimization Tips for M4

### 1. Use Quantized Models
- **q4_K_M**: Good balance (recommended)
- **q2_K**: Fastest, slightly lower quality
- **q8_0**: Best quality, slower

Example:
```bash
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 2. Adjust Context Length
Edit `config/agent_config.yaml`:
```yaml
agent:
  tokens:
    max_context_tokens: 4096  # Lower = faster
```

### 3. Reduce Temperature
```yaml
ollama:
  temperature: 0.3  # Lower = faster, more deterministic
```

---

## My Recommendation for You

**Start with this:**
```bash
# 1. Switch to your existing model right now
>>> /model mistral-nemo:12b-instruct-2407-q2_K

# 2. Test it
>>> list files in current directory

# 3. If it works well, keep using it
# 4. If you want better quality, install qwen2.5:7b
ollama pull qwen2.5:7b
>>> /model qwen2.5:7b
```

**Why this order:**
1. mistral-nemo works immediately (no download)
2. Good quality for your hardware
3. Supports tool calling perfectly
4. You can upgrade later if needed

---

## Troubleshooting

### "Model doesn't support tools"
**Solution:** Switch to qwen2.5, mistral-nemo, or llama3.2

### "Too slow"
**Solution:** Use llama3.2:3b or reduce context tokens

### "Not accurate enough"
**Solution:** Use qwen2.5:7b or increase to 14b model

### "Out of memory"
**Solution:** Use smaller model (3b) or close other apps

---

## Summary

**For your M4 MacBook with 16GB RAM:**
- ✅ **Best overall**: qwen2.5:7b
- ✅ **Available now**: mistral-nemo:12b-instruct-2407-q2_K
- ✅ **Fastest**: llama3.2:3b
- ❌ **Don't use**: deepseek-r1:8b

**Action items:**
1. Switch to mistral-nemo right now (you have it)
2. Test with tool calling
3. Optionally install qwen2.5:7b for better quality

