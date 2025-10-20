#!/usr/bin/env python3
"""
Test to verify tool results fix (Fix #4).
Checks that 'tool' role messages are included in LLM messages.
"""

import sys


def test_context_manager_fix():
    """Test that context manager includes 'tool' role messages."""
    print("=" * 70)
    print("  TESTING FIX #4: Tool Results Reaching Model")
    print("=" * 70)

    try:
        # Import context manager
        from agent.context_manager import ContextManager

        # Create instance
        config = {"memory": {"enabled": True, "max_messages": 100}}
        context = ContextManager(config)

        # Add different message types
        context.add_message("system", "You are a helpful assistant")
        context.add_message("user", "Read file /path/to/file.txt")
        context.add_message("tool", '{"success": true, "content": "File contents here..."}')
        context.add_message("assistant", "Here's a summary of the file...")

        # Get messages for LLM
        llm_messages = context.get_messages_for_llm()

        # Check if tool message is included
        tool_messages = [msg for msg in llm_messages if msg["role"] == "tool"]

        print(f"\nTotal messages added: 4")
        print(f"Messages sent to LLM: {len(llm_messages)}")
        print(f"Tool messages in LLM input: {len(tool_messages)}")

        print("\nMessage roles sent to LLM:")
        for i, msg in enumerate(llm_messages, 1):
            print(f"  {i}. {msg['role']:12} - {msg['content'][:50]}...")

        if len(tool_messages) > 0:
            print("\n" + "=" * 70)
            print("  ✓ FIX VERIFIED: Tool messages ARE reaching the model!")
            print("=" * 70)
            print("\nTool results will now be visible to the LLM.")
            print("Agent can properly use tool outputs in responses.")
            return True
        else:
            print("\n" + "=" * 70)
            print("  ✗ FIX NOT APPLIED: Tool messages NOT reaching model")
            print("=" * 70)
            print("\nTool role messages are being filtered out.")
            print("Apply fix: Add 'tool' to allowed roles in context_manager.py")
            return False

    except Exception as e:
        print(f"\n✗ Error running test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_context_manager_fix()
    sys.exit(0 if success else 1)
