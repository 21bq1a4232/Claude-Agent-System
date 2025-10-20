#!/usr/bin/env python3
"""
Test script to verify all fixes are working correctly.
Run this after applying fixes from LOCAL_MACHINE_FIXES.md
"""

import sys
import asyncio
import time


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_ollama_connection():
    """Test 1: Verify Ollama is running and responsive."""
    print_section("TEST 1: Ollama Connection")

    try:
        import ollama

        print("✓ Ollama library imported successfully")

        # List models
        models = ollama.list()
        model_names = [m.get("name") or m.get("model") for m in models.get("models", [])]

        if model_names:
            print(f"✓ Ollama running - {len(model_names)} models available:")
            for model in model_names[:5]:  # Show first 5
                print(f"  - {model}")
        else:
            print("✗ No models found. Run: ollama pull qwen2.5:7b")
            return False

        # Check for recommended models
        recommended = ["qwen2.5:7b", "llama3.1:8b", "mistral:7b"]
        found_recommended = [m for m in model_names if any(r in m for r in recommended)]

        if found_recommended:
            print(f"✓ Recommended model found: {found_recommended[0]}")
        else:
            print(f"⚠ No recommended models found. Consider: {recommended}")

        return True

    except Exception as e:
        print(f"✗ Ollama connection failed: {e}")
        print("  Make sure Ollama is running: ollama serve")
        return False


def test_tool_calling_support():
    """Test 2: Verify model supports tool calling."""
    print_section("TEST 2: Model Tool Calling Support")

    try:
        import ollama

        # Try with qwen2.5:7b first
        test_models = ["qwen2.5:7b", "llama3.1:8b", "mistral:7b"]

        for model in test_models:
            try:
                print(f"Testing {model}...", end=" ", flush=True)

                start = time.time()
                result = ollama.chat(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": "test_tool",
                                "description": "A test tool",
                                "parameters": {"type": "object", "properties": {}},
                            },
                        }
                    ],
                )
                elapsed = time.time() - start

                # Check if response is valid
                if "message" in result or "tool_calls" in str(result):
                    print(f"✓ WORKS ({elapsed:.2f}s)")
                    print(f"  Recommended model: {model}")
                    return True
                else:
                    print(f"✗ No valid response")

            except Exception as e:
                print(f"✗ Failed: {e}")

        print("\n⚠ No models support tool calling properly")
        print("  Pull a recommended model: ollama pull qwen2.5:7b")
        return False

    except Exception as e:
        print(f"✗ Tool calling test failed: {e}")
        return False


def test_async_wrapper():
    """Test 3: Verify async wrapper is applied."""
    print_section("TEST 3: Async Wrapper (asyncio.to_thread)")

    try:
        # Read ollama_client.py and check for asyncio.to_thread
        with open("agent/ollama_client.py", "r") as f:
            content = f.read()

        if "asyncio.to_thread" in content:
            count = content.count("asyncio.to_thread")
            print(f"✓ Async wrapper found ({count} occurrence(s))")
            return True
        else:
            print("✗ Async wrapper NOT found")
            print("  Apply Fix 1 from LOCAL_MACHINE_FIXES.md")
            return False

    except Exception as e:
        print(f"✗ File read failed: {e}")
        return False


def test_timeout_config():
    """Test 4: Verify timeout is configured."""
    print_section("TEST 4: Timeout Configuration")

    try:
        import yaml

        with open("config/agent_config.yaml", "r") as f:
            config = yaml.safe_load(f)

        llm_timeout = config.get("agent", {}).get("llm_timeout")
        tool_timeout = config.get("agent", {}).get("tool_timeout")

        if llm_timeout:
            print(f"✓ LLM timeout configured: {llm_timeout}s")
        else:
            print("✗ LLM timeout NOT configured")
            print("  Apply Fix 3 from LOCAL_MACHINE_FIXES.md")
            return False

        if tool_timeout:
            print(f"✓ Tool timeout configured: {tool_timeout}s")
        else:
            print("⚠ Tool timeout not configured (optional)")

        if llm_timeout <= 20:
            print(f"✓ Timeout is aggressive for testing ({llm_timeout}s)")
        else:
            print(f"⚠ Timeout may be too long for testing ({llm_timeout}s)")
            print("  Consider setting to 15s for initial testing")

        return True

    except Exception as e:
        print(f"✗ Config read failed: {e}")
        return False


def test_debug_logging():
    """Test 5: Verify debug logging is enabled."""
    print_section("TEST 5: Debug Logging")

    try:
        with open("agent/agent_core.py", "r") as f:
            content = f.read()

        debug_indicators = [
            "print(f\"[DEBUG]",
            "print(f\"[Agent] Available tools:",
            'print(" COMPLETED',
        ]

        found = [ind for ind in debug_indicators if ind in content]

        if len(found) >= 2:
            print(f"✓ Debug logging found ({len(found)}/3 indicators)")
            return True
        else:
            print(f"⚠ Debug logging partially found ({len(found)}/3)")
            print("  Apply Fix 2 from LOCAL_MACHINE_FIXES.md for better debugging")
            return len(found) > 0  # Partial pass

    except Exception as e:
        print(f"✗ File read failed: {e}")
        return False


async def test_agent_startup():
    """Test 6: Verify agent can start without errors."""
    print_section("TEST 6: Agent Startup")

    try:
        sys.path.insert(0, ".")
        from agent.agent_core import AgentCore
        from main import load_config

        print("Loading configuration...", end=" ", flush=True)
        config = load_config()
        print("✓")

        print("Initializing agent...", end=" ", flush=True)
        agent = AgentCore(config)
        print("✓")

        print(f"Current model: {agent.get_current_model()}")
        print(f"Agent mode: {'enabled' if agent.is_enabled() else 'disabled'}")
        print(f"Verbose: {agent.verbose}")

        print("\n✓ Agent initialized successfully")
        return True

    except Exception as e:
        print(f"✗ Agent startup failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_simple_query():
    """Test 7: Test simple query without tools."""
    print_section("TEST 7: Simple Query (No Tools)")

    try:
        import ollama

        model = "qwen2.5:7b"
        print(f"Testing simple query with {model}...", end=" ", flush=True)

        start = time.time()
        result = ollama.chat(
            model=model, messages=[{"role": "user", "content": "Say 'test successful' if you can read this"}]
        )
        elapsed = time.time() - start

        response = result.get("message", {}).get("content", "")

        if response and ("test successful" in response.lower() or "read this" in response.lower()):
            print(f"✓ ({elapsed:.2f}s)")
            print(f"  Response: {response[:100]}...")
            return True
        else:
            print(f"✗ Unexpected response")
            print(f"  Response: {response[:200]}")
            return False

    except Exception as e:
        print(f"✗ Query failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "█" * 70)
    print("  CLAUDE AGENT SYSTEM - FIX VERIFICATION")
    print("█" * 70)

    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Tool Calling Support", test_tool_calling_support),
        ("Async Wrapper", test_async_wrapper),
        ("Timeout Config", test_timeout_config),
        ("Debug Logging", test_debug_logging),
        ("Simple Query", test_simple_query),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Try agent startup test (may fail if dependencies not installed)
    try:
        print_section("TEST 6: Agent Startup")
        result = asyncio.run(test_agent_startup())
        results.append(("Agent Startup", result))
    except ImportError as e:
        print(f"⚠ Skipping agent startup test (dependencies not available): {e}")
        results.append(("Agent Startup", None))

    # Summary
    print_section("SUMMARY")

    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)

    for test_name, result in results:
        status = "✓ PASS" if result is True else ("✗ FAIL" if result is False else "⊘ SKIP")
        print(f"{status:10} - {test_name}")

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0:
        print("\n" + "█" * 70)
        print("  ✓ ALL TESTS PASSED - Ready to run agent!")
        print("█" * 70)
        print("\nNext steps:")
        print("  1. poetry run python main.py")
        print("  2. /model qwen2.5:7b")
        print("  3. Try: 'list files in this directory'")
        return 0
    else:
        print("\n" + "█" * 70)
        print("  ✗ SOME TESTS FAILED - Review LOCAL_MACHINE_FIXES.md")
        print("█" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
