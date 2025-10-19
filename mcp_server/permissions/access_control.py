"""Access control and permission management."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml
from mcp_server.utils.logger import get_logger
from mcp_server.utils.error_handlers import PermissionError as PermissionDeniedError


logger = get_logger(__name__)


class PermissionManager:
    """Manages permissions for file/directory access and operations."""

    def __init__(self, config_path: str):
        """
        Initialize permission manager.

        Args:
            config_path: Path to permissions configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.mode = self.config.get("permissions", {}).get("mode", "moderate")
        self.session_approvals: Set[str] = set()
        self.persistent_approvals: Set[str] = set()

    def _load_config(self) -> Dict[str, Any]:
        """Load permissions configuration from YAML."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load permissions config: {e}")
            return {}

    def _normalize_path(self, path: str) -> Path:
        """Normalize a path for comparison."""
        # Expand custom variables
        expanded = path.replace("${CWD}", os.getcwd())
        expanded = expanded.replace("${HOME}", str(Path.home()))
        return Path(expanded).expanduser().resolve()

    def _match_pattern(self, path: Path, pattern: str) -> bool:
        """
        Check if a path matches a pattern.

        Args:
            path: Path to check
            pattern: Pattern (supports wildcards)

        Returns:
            True if matches
        """
        pattern_path = Path(pattern).expanduser().resolve()

        # Convert pattern to regex
        pattern_str = str(pattern_path)
        pattern_str = pattern_str.replace("*", ".*")
        pattern_regex = re.compile(f"^{pattern_str}")

        return bool(pattern_regex.match(str(path)))

    def _is_safe_directory(self, path: Path) -> bool:
        """Check if path is in safe directories."""
        safe_dirs = self.config.get("permissions", {}).get("safe_directories", [])

        for safe_dir in safe_dirs:
            safe_path = self._normalize_path(safe_dir)
            try:
                # Check if path is under safe directory
                path.relative_to(safe_path)
                return True
            except ValueError:
                # Check pattern matching
                if self._match_pattern(path, safe_dir):
                    return True

        return False

    def _is_blocked_directory(self, path: Path) -> bool:
        """Check if path is in blocked directories."""
        blocked_dirs = self.config.get("permissions", {}).get("blocked_directories", [])

        for blocked_dir in blocked_dirs:
            blocked_path = self._normalize_path(blocked_dir)
            try:
                path.relative_to(blocked_path)
                return True
            except ValueError:
                if self._match_pattern(path, blocked_dir):
                    return True

        return False

    def _requires_approval(self, path: Path) -> bool:
        """Check if path requires user approval."""
        require_approval = self.config.get("permissions", {}).get("require_approval", [])

        for approval_dir in require_approval:
            approval_path = self._normalize_path(approval_dir)
            try:
                path.relative_to(approval_path)
                return True
            except ValueError:
                if self._match_pattern(path, approval_dir):
                    return True

        return False

    def check_file_access(
        self,
        path: str,
        operation: str = "read",
        auto_approve: bool = False,
    ) -> bool:
        """
        Check if file access is allowed.

        Args:
            path: File path
            operation: Operation type ('read', 'write', 'delete')
            auto_approve: Auto-approve if in cache

        Returns:
            True if allowed

        Raises:
            PermissionDeniedError: If access denied
        """
        file_path = self._normalize_path(path)

        # Check if blocked
        if self._is_blocked_directory(file_path):
            raise PermissionDeniedError(
                f"Access denied: {file_path} is in blocked directories",
                path=str(file_path),
            )

        # Check file type restrictions
        if operation == "read" or operation == "write":
            suffix = file_path.suffix.lower()
            blocked_types = self.config.get("permissions", {}).get("file_types", {}).get("blocked", [])
            if suffix in blocked_types:
                raise PermissionDeniedError(
                    f"File type {suffix} is blocked",
                    path=str(file_path),
                )

        # Check if auto-approved
        approval_key = f"{operation}:{file_path}"
        if auto_approve and approval_key in self.session_approvals:
            return True

        # Check if safe directory (auto-approve)
        if self._is_safe_directory(file_path):
            self.session_approvals.add(approval_key)
            return True

        # Check if requires approval
        if self._requires_approval(file_path) or self.mode == "strict":
            # In real implementation, this would prompt user
            # For now, we'll just log and deny
            logger.warning(f"User approval required for {operation} on {file_path}")
            raise PermissionDeniedError(
                f"User approval required for {operation} on {file_path}",
                path=str(file_path),
                suggestions=[
                    "Add the directory to safe_directories in config",
                    "Approve the operation when prompted",
                ],
            )

        # Permissive mode or moderate mode without specific restrictions
        self.session_approvals.add(approval_key)
        return True

    def check_command(self, command: str) -> bool:
        """
        Check if command execution is allowed.

        Args:
            command: Command to check

        Returns:
            True if allowed

        Raises:
            PermissionDeniedError: If command blocked
        """
        shell_config = self.config.get("permissions", {}).get("operations", {}).get("shell_execute", {})

        # Check blocked commands
        blocked = shell_config.get("blocked_commands", [])
        for blocked_cmd in blocked:
            if blocked_cmd in command or command.startswith(blocked_cmd):
                raise PermissionDeniedError(
                    f"Command blocked: {command}",
                    details={"command": command},
                )

        # Check dangerous commands
        dangerous = shell_config.get("require_approval_commands", [])
        cmd_parts = command.split()
        if cmd_parts and cmd_parts[0] in dangerous:
            logger.warning(f"Dangerous command requires approval: {command}")
            # In real implementation, would prompt user
            raise PermissionDeniedError(
                f"Command requires user approval: {command}",
                details={"command": command},
                suggestions=["Approve the command when prompted"],
            )

        return True

    def check_url_access(self, url: str) -> bool:
        """
        Check if URL access is allowed.

        Args:
            url: URL to check

        Returns:
            True if allowed

        Raises:
            PermissionDeniedError: If URL blocked
        """
        web_config = self.config.get("permissions", {}).get("operations", {}).get("web_fetch", {})

        # Check blocked domains
        blocked = web_config.get("blocked", [])
        for blocked_domain in blocked:
            if blocked_domain in url:
                raise PermissionDeniedError(
                    f"URL domain blocked: {url}",
                    details={"url": url, "blocked_domain": blocked_domain},
                )

        # Check require approval
        require_approval = web_config.get("require_approval", [])
        for approval_pattern in require_approval:
            if approval_pattern in url:
                logger.warning(f"URL requires approval: {url}")
                raise PermissionDeniedError(
                    f"URL requires user approval: {url}",
                    details={"url": url},
                )

        return True

    def approve(self, operation: str, resource: str, persistent: bool = False) -> None:
        """
        Manually approve an operation.

        Args:
            operation: Operation type
            resource: Resource identifier
            persistent: Whether to persist across sessions
        """
        approval_key = f"{operation}:{resource}"
        self.session_approvals.add(approval_key)

        if persistent:
            self.persistent_approvals.add(approval_key)
            # In real implementation, would save to file
            logger.info(f"Persistently approved: {approval_key}")

    def revoke(self, operation: str, resource: str) -> None:
        """
        Revoke an approval.

        Args:
            operation: Operation type
            resource: Resource identifier
        """
        approval_key = f"{operation}:{resource}"
        self.session_approvals.discard(approval_key)
        self.persistent_approvals.discard(approval_key)
        logger.info(f"Revoked approval: {approval_key}")

    def list_approvals(self) -> Dict[str, List[str]]:
        """List all approvals."""
        return {
            "session": list(self.session_approvals),
            "persistent": list(self.persistent_approvals),
        }
