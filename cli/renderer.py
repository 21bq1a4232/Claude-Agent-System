"""Markdown and output rendering with Rich."""

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from typing import Optional


class OutputRenderer:
    """Renders output with Rich formatting."""

    def __init__(self, color_scheme: str = "auto", syntax_highlighting: bool = True):
        """
        Initialize renderer.

        Args:
            color_scheme: Color scheme (auto/dark/light)
            syntax_highlighting: Enable syntax highlighting
        """
        self.console = Console()
        self.color_scheme = color_scheme
        self.syntax_highlighting = syntax_highlighting

    def print_markdown(self, content: str) -> None:
        """
        Print markdown content.

        Args:
            content: Markdown text
        """
        md = Markdown(content)
        self.console.print(md)

    def print_code(self, code: str, language: str = "python") -> None:
        """
        Print syntax-highlighted code.

        Args:
            code: Code to print
            language: Programming language
        """
        if self.syntax_highlighting:
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            self.console.print(syntax)
        else:
            self.console.print(code)

    def print_panel(
        self,
        content: str,
        title: Optional[str] = None,
        style: str = "blue",
    ) -> None:
        """
        Print content in a panel.

        Args:
            content: Panel content
            title: Panel title
            style: Panel style
        """
        panel = Panel(content, title=title, border_style=style)
        self.console.print(panel)

    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def print_thinking(self, message: str) -> None:
        """Print thinking/processing message."""
        self.console.print(f"[dim]🤔 {message}[/dim]")

    def print_tool_execution(self, tool_name: str, status: str = "running") -> None:
        """Print tool execution status."""
        emoji = "🔧" if status == "running" else "✓"
        color = "yellow" if status == "running" else "green"
        self.console.print(f"[{color}]{emoji} {tool_name}[/{color}]")

    def clear(self) -> None:
        """Clear the console."""
        self.console.clear()

    def print_separator(self) -> None:
        """Print a separator line."""
        self.console.print("─" * self.console.width)
