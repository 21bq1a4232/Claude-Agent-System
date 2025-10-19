"""Terminal chat interface."""

import asyncio
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from cli.renderer import OutputRenderer
from cli.commands import CommandHandler
from agent.agent_core import AgentCore


class TerminalInterface:
    """Interactive terminal chat interface."""

    def __init__(self, agent_core: AgentCore, config: dict):
        """
        Initialize terminal interface.

        Args:
            agent_core: Agent core instance
            config: UI configuration
        """
        self.agent = agent_core
        self.config = config.get("ui", {})

        # Initialize renderer
        self.renderer = OutputRenderer(
            color_scheme=self.config.get("color_scheme", "auto"),
            syntax_highlighting=self.config.get("syntax_highlighting", True),
        )

        # Initialize command handler
        self.command_handler = CommandHandler(self.agent, config, self.renderer)

        # Setup prompt session
        self.session = PromptSession(history=InMemoryHistory())
        self.running = True

        # Prompt style
        self.style = Style.from_dict({
            'prompt': '#ansigreen bold',
        })

    async def start(self) -> None:
        """Start the interactive terminal interface."""
        self.renderer.print_panel(
            "Claude Agent System\nAn intelligent assistant with MCP tools and Ollama",
            title="Welcome",
            style="green",
        )
        self.renderer.print_info("Type /help for available commands, or just chat naturally")
        self.renderer.print_separator()

        while self.running:
            try:
                # Get user input
                user_input = await asyncio.to_thread(
                    self.session.prompt,
                    ">>> ",
                    style=self.style,
                )

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                else:
                    await self._handle_message(user_input)

            except KeyboardInterrupt:
                if await self._confirm_exit():
                    break
            except EOFError:
                break
            except Exception as e:
                self.renderer.print_error(f"Unexpected error: {e}")

        await self._cleanup()

    async def _handle_command(self, input_text: str) -> None:
        """Handle slash command."""
        parts = input_text[1:].split()
        command = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        result = await self.command_handler.execute(command, args)

        if result == "EXIT":
            self.running = False
        elif result:
            self.renderer.print_info(result)

    async def _handle_message(self, message: str) -> None:
        """Handle regular chat message."""
        try:
            # Show processing indicator
            if self.agent.is_enabled() and self.config.get("show_thinking", True):
                self.renderer.print_thinking("Processing your request...")

            # Get response from agent
            response = await self.agent.process_request(message)

            # Display response
            self.renderer.print_separator()
            self.renderer.print_markdown(response)
            self.renderer.print_separator()

        except Exception as e:
            self.renderer.print_error(f"Error processing message: {e}")

    async def _confirm_exit(self) -> bool:
        """Confirm exit with user."""
        self.renderer.print_warning("Press Ctrl+C again to exit, or press Enter to continue")
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self.session.prompt, ""),
                timeout=3.0,
            )
            return False
        except asyncio.TimeoutError:
            return True
        except KeyboardInterrupt:
            return True

    async def _cleanup(self) -> None:
        """Cleanup before exit."""
        self.renderer.print_info("Saving conversation...")
        saved_path = self.agent.context.save()
        if saved_path:
            self.renderer.print_success(f"Conversation saved to: {saved_path}")

        self.renderer.print_info("Cleaning up resources...")
        await self.agent.cleanup()

        self.renderer.print_panel(
            "Thank you for using Claude Agent System!",
            title="Goodbye",
            style="blue",
        )


async def run_terminal_interface(config: dict) -> None:
    """
    Run the terminal interface.

    Args:
        config: Application configuration
    """
    # Initialize agent core
    agent = AgentCore(config)

    # Create and start interface
    interface = TerminalInterface(agent, config)
    await interface.start()
