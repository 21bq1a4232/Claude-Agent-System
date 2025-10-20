#!/usr/bin/env python3
"""
Automated fix script for Claude Agent System.
Applies all critical fixes to make the agent work on MacBook M4.

Usage:
    python3 auto_fix.py
"""

import os
import sys
import shutil
from datetime import datetime


def create_backup(file_path):
    """Create a backup of the file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def fix_ollama_client():
    """Fix 1: Add asyncio.to_thread() wrapper to ollama_client.py"""
    file_path = "agent/ollama_client.py"

    print(f"\n📝 Fixing {file_path}...")

    # Create backup
    backup_path = create_backup(file_path)
    print(f"   ✓ Backup created: {backup_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Check if already fixed
    if "asyncio.to_thread" in content:
        print(f"   ⊙ Already fixed (asyncio.to_thread found)")
        return True

    # Fix 1: _generate_full method
    old_generate = """    async def _generate_full(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        \"\"\"Generate full response (non-streaming).\"\"\"
        try:
            response = ollama.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options,
            )"""

    new_generate = """    async def _generate_full(
        self,
        model: str,
        prompt: str,
        system: Optional[str],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        \"\"\"Generate full response (non-streaming).\"\"\"
        import asyncio

        try:
            # Properly wrap synchronous ollama.generate() in thread pool
            response = await asyncio.to_thread(
                ollama.generate,
                model=model,
                prompt=prompt,
                system=system,
                options=options,
            )"""

    content = content.replace(old_generate, new_generate)

    # Fix 2: chat method
    old_chat = """            if tools:
                kwargs["tools"] = tools

            response = ollama.chat(**kwargs)
            return response"""

    new_chat = """            if tools:
                kwargs["tools"] = tools

            # Properly wrap synchronous ollama.chat() in thread pool
            response = await asyncio.to_thread(ollama.chat, **kwargs)
            return response"""

    content = content.replace(old_chat, new_chat)

    # Add import at the top of chat method if not there
    if "import asyncio" not in content.split("async def chat(")[1].split("try:")[0]:
        old_chat_start = """    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        \"\"\"
        Chat with Ollama model.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature for generation
            tools: List of available tools for function calling

        Returns:
            Chat response
        \"\"\"
        model = model or self.current_model"""

        new_chat_start = """    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        \"\"\"
        Chat with Ollama model.

        Args:
            messages: List of chat messages
            model: Model name
            temperature: Temperature for generation
            tools: List of available tools for function calling

        Returns:
            Chat response
        \"\"\"
        import asyncio

        model = model or self.current_model"""

        content = content.replace(old_chat_start, new_chat_start)

    # Write updated content
    with open(file_path, "w") as f:
        f.write(content)

    print(f"   ✓ Fixed: Added asyncio.to_thread() wrapper")
    return True


def fix_agent_core():
    """Fix 2: Add timeout and debug logging to agent_core.py"""
    file_path = "agent/agent_core.py"

    print(f"\n📝 Fixing {file_path}...")

    # Create backup
    backup_path = create_backup(file_path)
    print(f"   ✓ Backup created: {backup_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Check if already fixed
    if 'print(f"[DEBUG] Calling ollama.chat()' in content:
        print(f"   ⊙ Already fixed (debug logging found)")
        return True

    # Fix: Add timeout and debug logging
    old_code = """            if self.verbose:
                print("\\n[Agent] Analyzing request and selecting tools...")

            # Make single chat call with tools
            messages = self.context.get_messages_for_llm()
            response = await self.ollama.chat(messages, tools=tools if tools else None)"""

    new_code = """            if self.verbose:
                print("\\n[Agent] Analyzing request and selecting tools...")
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
                print(f"\\n[Agent] LLM call timed out after {timeout}s - falling back to direct mode")
                return await self._direct_response(user_message)"""

    content = content.replace(old_code, new_code)

    # Write updated content
    with open(file_path, "w") as f:
        f.write(content)

    print(f"   ✓ Fixed: Added timeout and debug logging")
    return True


def fix_config():
    """Fix 3: Add timeout configuration to agent_config.yaml"""
    file_path = "config/agent_config.yaml"

    print(f"\n📝 Fixing {file_path}...")

    # Create backup
    backup_path = create_backup(file_path)
    print(f"   ✓ Backup created: {backup_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Check if already fixed
    if "llm_timeout:" in content:
        print(f"   ⊙ Already fixed (llm_timeout found)")
        return True

    # Fix: Add timeout configuration
    old_config = """  # Enable streaming for faster responses (like ollama run)
  stream_responses: true

  # Token management"""

    new_config = """  # Enable streaming for faster responses (like ollama run)
  stream_responses: true

  # Timeout for LLM calls in seconds (prevents infinite hangs)
  llm_timeout: 15

  # Timeout for tool execution in seconds
  tool_timeout: 30

  # Token management"""

    content = content.replace(old_config, new_config)

    # Write updated content
    with open(file_path, "w") as f:
        f.write(content)

    print(f"   ✓ Fixed: Added timeout configuration")
    return True


def verify_files_exist():
    """Verify required files exist."""
    required_files = [
        "agent/ollama_client.py",
        "agent/agent_core.py",
        "config/agent_config.yaml",
    ]

    missing = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing.append(file_path)

    if missing:
        print("\n❌ ERROR: Missing required files:")
        for file_path in missing:
            print(f"   - {file_path}")
        print("\nMake sure you're running this from the project root directory.")
        return False

    return True


def main():
    """Main function."""
    print("=" * 70)
    print("  CLAUDE AGENT SYSTEM - AUTOMATED FIX SCRIPT")
    print("  Applying critical fixes for MacBook M4")
    print("=" * 70)

    # Verify we're in the right directory
    if not verify_files_exist():
        return 1

    print("\n✓ All required files found")

    # Apply fixes
    fixes = [
        ("Async Wrapper (ollama_client.py)", fix_ollama_client),
        ("Timeout & Debug Logging (agent_core.py)", fix_agent_core),
        ("Config Timeout (agent_config.yaml)", fix_config),
    ]

    results = []
    for fix_name, fix_func in fixes:
        try:
            result = fix_func()
            results.append((fix_name, result))
        except Exception as e:
            print(f"\n   ✗ Error applying {fix_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((fix_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    for fix_name, result in results:
        status = "✓ APPLIED" if result else "✗ FAILED"
        print(f"{status:12} - {fix_name}")

    failed = sum(1 for _, r in results if not r)

    if failed == 0:
        print("\n" + "=" * 70)
        print("  ✓ ALL FIXES APPLIED SUCCESSFULLY!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Install recommended model:")
        print("     ollama pull qwen2.5:7b")
        print("\n  2. Test the fixes:")
        print("     python3 test_fixes.py")
        print("\n  3. Start the agent:")
        print("     poetry run python main.py")
        print("\n  4. Switch to recommended model:")
        print("     /model qwen2.5:7b")
        print("\n  5. Test tool calling:")
        print("     >>> list files in this directory")
        return 0
    else:
        print("\n" + "=" * 70)
        print("  ✗ SOME FIXES FAILED")
        print("=" * 70)
        print("\nPlease apply fixes manually using LOCAL_MACHINE_FIXES.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
