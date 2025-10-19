"""Slash command handlers."""

from typing import Any, Dict, Callable, Optional
import yaml
from pathlib import Path


class CommandHandler:
    """Handles slash commands."""

    def __init__(self, agent_core: Any, config: Dict[str, Any], renderer: Any):
        """
        Initialize command handler.

        Args:
            agent_core: Agent core instance
            config: Configuration
            renderer: Output renderer
        """
        self.agent = agent_core
        self.config = config
        self.renderer = renderer
        self.commands: Dict[str, Callable] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all slash commands."""
        self.commands = {
            "help": self._cmd_help,
            "model": self._cmd_model,
            "agent": self._cmd_agent,
            "tools": self._cmd_tools,
            "config": self._cmd_config,
            "history": self._cmd_history,
            "clear": self._cmd_clear,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "permissions": self._cmd_permissions,
            "retry": self._cmd_retry,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
        }

    async def execute(self, command: str, args: list[str]) -> Optional[str]:
        """
        Execute a slash command.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Response message or None
        """
        if command not in self.commands:
            return f"Unknown command: /{command}. Type /help for available commands."

        return await self.commands[command](args)

    async def _cmd_help(self, args: list[str]) -> str:
        """Show help information."""
        help_text = """
# Available Commands

- `/help` - Show this help message
- `/model [name]` - Switch Ollama model or list available models
- `/agent on|off` - Toggle agent mode
- `/tools` - List available MCP tools
- `/config [key]` - Show configuration
- `/history [limit]` - View conversation history
- `/clear` - Clear conversation history
- `/save [file]` - Save conversation to file
- `/load [file]` - Load conversation from file
- `/permissions` - View/manage permissions
- `/retry` - Retry last failed operation
- `/exit` or `/quit` - Exit the application

## Examples

```
/model deepseek-r1:1.5b
/agent on
/tools
/save my_conversation.json
```
"""
        self.renderer.print_markdown(help_text)
        return None

    async def _cmd_model(self, args: list[str]) -> str:
        """Handle model command."""
        if not args:
            # List models
            models = self.agent.list_models()
            current = self.agent.get_current_model()

            output = "# Available Models\n\n"
            for model in models:
                marker = "→" if model == current else " "
                output += f"{marker} {model}\n"

            self.renderer.print_markdown(output)
            return None

        # Switch model
        model_name = args[0]
        if self.agent.switch_model(model_name):
            return f"Switched to model: {model_name}"
        else:
            return f"Model not found: {model_name}"

    async def _cmd_agent(self, args: list[str]) -> str:
        """Handle agent mode toggle."""
        if not args:
            status = "enabled" if self.agent.is_enabled() else "disabled"
            return f"Agent mode is currently {status}"

        mode = args[0].lower()
        if mode == "on":
            self.agent.enabled = True
            return "Agent mode enabled"
        elif mode == "off":
            self.agent.enabled = False
            return "Agent mode disabled (direct mode)"
        else:
            return "Usage: /agent on|off"

    async def _cmd_tools(self, args: list[str]) -> str:
        """List available tools."""
        tools = await self.agent.tool_executor.list_tools()

        output = "# Available MCP Tools\n\n"
        for i, tool in enumerate(tools, 1):
            output += f"{i}. `{tool}`\n"

        self.renderer.print_markdown(output)
        return None

    async def _cmd_config(self, args: list[str]) -> str:
        """Show configuration."""
        if not args:
            # Show summary
            output = "# Configuration Summary\n\n"
            output += f"- Model: {self.agent.get_current_model()}\n"
            output += f"- Agent Mode: {'enabled' if self.agent.is_enabled() else 'disabled'}\n"
            output += f"- Verbose: {self.agent.verbose}\n"
            output += f"- Max Steps: {self.agent.max_steps}\n"

            self.renderer.print_markdown(output)
            return None

        # Show specific config
        key = args[0]
        value = self._get_nested_config(self.config, key.split("."))
        if value is not None:
            return f"{key}: {value}"
        else:
            return f"Config key not found: {key}"

    def _get_nested_config(self, config: Dict[str, Any], keys: list[str]) -> Any:
        """Get nested configuration value."""
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    async def _cmd_history(self, args: list[str]) -> str:
        """Show conversation history."""
        limit = int(args[0]) if args else 10
        messages = self.agent.context.get_messages(limit=limit)

        output = f"# Conversation History (last {len(messages)} messages)\n\n"
        for msg in messages:
            role = msg["role"].capitalize()
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            output += f"**{role}:** {content}\n\n"

        self.renderer.print_markdown(output)
        return None

    async def _cmd_clear(self, args: list[str]) -> str:
        """Clear conversation history."""
        self.agent.context.clear()
        self.renderer.clear()
        return "Conversation history cleared"

    async def _cmd_save(self, args: list[str]) -> str:
        """Save conversation."""
        filepath = args[0] if args else None
        saved_path = self.agent.context.save(filepath)
        if saved_path:
            return f"Conversation saved to: {saved_path}"
        else:
            return "Failed to save conversation"

    async def _cmd_load(self, args: list[str]) -> str:
        """Load conversation."""
        if not args:
            return "Usage: /load <filepath>"

        filepath = args[0]
        if self.agent.context.load(filepath):
            return f"Conversation loaded from: {filepath}"
        else:
            return f"Failed to load conversation from: {filepath}"

    async def _cmd_permissions(self, args: list[str]) -> str:
        """Show permissions info."""
        output = """
# Permission System

Current permission mode: moderate

## Safe Directories
- /home/ec2-user/environment

## Blocked Directories
- /root, /sys, /proc, /boot, /dev

Use configuration files to modify permissions.
"""
        self.renderer.print_markdown(output)
        return None

    async def _cmd_retry(self, args: list[str]) -> str:
        """Retry last failed operation."""
        return "Retry functionality coming soon"

    async def _cmd_exit(self, args: list[str]) -> str:
        """Exit the application."""
        return "EXIT"

    def list_commands(self) -> list[str]:
        """List all available commands."""
        return list(self.commands.keys())
