"""Context and conversation management."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class ContextManager:
    """Manages conversation context and history."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize context manager.

        Args:
            config: Memory configuration
        """
        self.config = config.get("memory", {})
        self.enabled = self.config.get("enabled", True)
        self.max_messages = self.config.get("max_messages", 100)
        self.messages: List[Dict[str, Any]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to context.

        Args:
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Additional metadata
        """
        if not self.enabled:
            return

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }

        if metadata:
            message["metadata"] = metadata

        self.messages.append(message)

        # Trim if needed
        if len(self.messages) > self.max_messages:
            self._trim_messages()

    def _trim_messages(self) -> None:
        """Trim messages to fit within max_messages."""
        summarize_config = self.config.get("summarize", {})
        if summarize_config.get("enabled", True):
            # Keep system message, recent messages, and summarize the rest
            threshold = summarize_config.get("threshold_messages", 50)
            keep_recent = summarize_config.get("keep_recent", 10)

            if len(self.messages) > threshold:
                # Keep first (system) and last N messages
                recent = self.messages[-keep_recent:]
                self.messages = self.messages[:1] + [
                    {
                        "role": "system",
                        "content": f"[Previous {len(self.messages) - keep_recent - 1} messages summarized]",
                        "timestamp": datetime.now().isoformat(),
                    }
                ] + recent
        else:
            # Simple truncation - remove oldest (except first)
            self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]

    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation messages.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of messages
        """
        if limit:
            return self.messages[-limit:]
        return self.messages.copy()

    def get_messages_for_llm(self) -> List[Dict[str, str]]:
        """
        Get messages formatted for LLM.

        Returns:
            List of messages in LLM format
        """
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in self.messages
            if msg["role"] in ["user", "assistant", "system", "tool"]
        ]

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []

    def save(self, filepath: Optional[str] = None) -> str:
        """
        Save conversation to file.

        Args:
            filepath: Path to save file

        Returns:
            Path where conversation was saved
        """
        persist_config = self.config.get("persist", {})
        if not persist_config.get("enabled", True):
            return ""

        if not filepath:
            persist_dir = Path(persist_config.get("directory", "~/.claude-agent/history")).expanduser()
            persist_dir.mkdir(parents=True, exist_ok=True)
            filepath = str(persist_dir / f"conversation_{self.session_id}.json")

        data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "messages": self.messages,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    def load(self, filepath: str) -> bool:
        """
        Load conversation from file.

        Args:
            filepath: Path to conversation file

        Returns:
            True if successful
        """
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            self.messages = data.get("messages", [])
            self.session_id = data.get("session_id", self.session_id)
            return True

        except Exception:
            return False
