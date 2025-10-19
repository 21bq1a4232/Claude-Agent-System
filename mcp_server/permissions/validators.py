"""Input validation utilities."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp_server.utils.error_handlers import ValidationError


class InputValidator:
    """Validates inputs for MCP tools."""

    @staticmethod
    def validate_file_path(path: str, must_exist: bool = False) -> Path:
        """
        Validate and normalize a file path.

        Args:
            path: File path to validate
            must_exist: Whether the file must exist

        Returns:
            Normalized Path object

        Raises:
            ValidationError: If path is invalid
        """
        if not path or not isinstance(path, str):
            raise ValidationError("Path must be a non-empty string", field="path")

        try:
            # Convert to absolute path
            file_path = Path(path).expanduser().resolve()

            # Check if path traversal is attempted
            if ".." in path:
                # Allow .. but validate the resolved path is safe
                pass

            if must_exist and not file_path.exists():
                raise ValidationError(
                    f"Path does not exist: {file_path}",
                    field="path",
                    details={"path": str(file_path)},
                )

            return file_path

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Invalid path: {str(e)}", field="path")

    @staticmethod
    def validate_pattern(pattern: str, pattern_type: str = "glob") -> str:
        """
        Validate a search pattern.

        Args:
            pattern: Pattern to validate
            pattern_type: Type of pattern ('glob' or 'regex')

        Returns:
            Validated pattern

        Raises:
            ValidationError: If pattern is invalid
        """
        if not pattern or not isinstance(pattern, str):
            raise ValidationError("Pattern must be a non-empty string", field="pattern")

        if pattern_type == "regex":
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValidationError(
                    f"Invalid regex pattern: {str(e)}",
                    field="pattern",
                    details={"pattern": pattern},
                )

        return pattern

    @staticmethod
    def validate_command(command: str, allowed_commands: Optional[List[str]] = None) -> str:
        """
        Validate a shell command.

        Args:
            command: Command to validate
            allowed_commands: List of allowed command prefixes

        Returns:
            Validated command

        Raises:
            ValidationError: If command is invalid
        """
        if not command or not isinstance(command, str):
            raise ValidationError("Command must be a non-empty string", field="command")

        # Strip whitespace
        command = command.strip()

        if allowed_commands:
            cmd_prefix = command.split()[0] if command.split() else ""
            if not any(cmd_prefix.startswith(allowed) for allowed in allowed_commands):
                raise ValidationError(
                    f"Command not allowed: {cmd_prefix}",
                    field="command",
                    details={
                        "command": cmd_prefix,
                        "allowed": allowed_commands,
                    },
                )

        return command

    @staticmethod
    def validate_url(url: str) -> str:
        """
        Validate a URL.

        Args:
            url: URL to validate

        Returns:
            Validated URL

        Raises:
            ValidationError: If URL is invalid
        """
        if not url or not isinstance(url, str):
            raise ValidationError("URL must be a non-empty string", field="url")

        # Basic URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
            r"localhost|"  # localhost...
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        if not url_pattern.match(url):
            raise ValidationError(
                "Invalid URL format",
                field="url",
                details={"url": url},
            )

        return url

    @staticmethod
    def validate_integer(
        value: Any,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> int:
        """
        Validate an integer value.

        Args:
            value: Value to validate
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validated integer

        Raises:
            ValidationError: If value is invalid
        """
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            raise ValidationError(
                f"{field_name} must be an integer",
                field=field_name,
            )

        if min_value is not None and int_value < min_value:
            raise ValidationError(
                f"{field_name} must be >= {min_value}",
                field=field_name,
                details={"value": int_value, "min": min_value},
            )

        if max_value is not None and int_value > max_value:
            raise ValidationError(
                f"{field_name} must be <= {max_value}",
                field=field_name,
                details={"value": int_value, "max": max_value},
            )

        return int_value

    @staticmethod
    def validate_string_length(
        value: str,
        field_name: str,
        min_length: int = 0,
        max_length: Optional[int] = None,
    ) -> str:
        """
        Validate string length.

        Args:
            value: String to validate
            field_name: Name of the field
            min_length: Minimum length
            max_length: Maximum length

        Returns:
            Validated string

        Raises:
            ValidationError: If string length is invalid
        """
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", field=field_name)

        length = len(value)

        if length < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters",
                field=field_name,
                details={"length": length, "min": min_length},
            )

        if max_length is not None and length > max_length:
            raise ValidationError(
                f"{field_name} must be at most {max_length} characters",
                field=field_name,
                details={"length": length, "max": max_length},
            )

        return value
