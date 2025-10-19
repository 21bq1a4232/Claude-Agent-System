"""Shell execution tools (Bash)."""

import asyncio
import signal
from typing import Any, Dict, Optional
from mcp_server.permissions import PermissionManager, InputValidator
from mcp_server.utils import get_logger, ToolError, TimeoutError, create_error_response


logger = get_logger(__name__)


class ShellTools:
    """Shell execution tools."""

    def __init__(self, permission_manager: PermissionManager, config: Dict[str, Any]):
        """
        Initialize shell tools.

        Args:
            permission_manager: Permission manager instance
            config: Tool configuration
        """
        self.permission_manager = permission_manager
        self.config = config.get("tools", {})
        self.background_jobs: Dict[str, asyncio.subprocess.Process] = {}

    async def bash(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        background: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a bash command.

        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            env: Environment variables
            background: Run in background

        Returns:
            Dictionary with command result
        """
        try:
            # Validate command
            InputValidator.validate_command(command)

            # Check permissions
            self.permission_manager.check_command(command)

            # Get config
            bash_config = self.config.get("bash", {})
            timeout = timeout or bash_config.get("default_timeout", 120)
            max_timeout = bash_config.get("max_timeout", 600)

            if timeout > max_timeout:
                timeout = max_timeout

            # Prepare environment
            exec_env = bash_config.get("env", {}).copy()
            if env:
                exec_env.update(env)

            # Execute command
            if background:
                return await self._execute_background(command, cwd, exec_env)
            else:
                return await self._execute_foreground(command, timeout, cwd, exec_env)

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return create_error_response(e)

    async def _execute_foreground(
        self,
        command: str,
        timeout: int,
        cwd: Optional[str],
        env: Dict[str, str],
    ) -> Dict[str, Any]:
        """Execute command in foreground with timeout."""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(
                    f"Command timed out after {timeout} seconds",
                    timeout=timeout,
                )

            return {
                "success": process.returncode == 0,
                "command": command,
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "timed_out": False,
            }

        except Exception as e:
            if isinstance(e, TimeoutError):
                return create_error_response(e)
            raise

    async def _execute_background(
        self,
        command: str,
        cwd: Optional[str],
        env: Dict[str, str],
    ) -> Dict[str, Any]:
        """Execute command in background."""
        import uuid

        job_id = str(uuid.uuid4())[:8]

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        self.background_jobs[job_id] = process

        return {
            "success": True,
            "command": command,
            "job_id": job_id,
            "pid": process.pid,
            "background": True,
            "message": f"Command started in background with job ID: {job_id}",
        }

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a background job.

        Args:
            job_id: Job ID

        Returns:
            Dictionary with job status
        """
        try:
            if job_id not in self.background_jobs:
                raise ToolError(f"Job not found: {job_id}")

            process = self.background_jobs[job_id]

            if process.returncode is None:
                # Still running
                return {
                    "success": True,
                    "job_id": job_id,
                    "status": "running",
                    "pid": process.pid,
                }
            else:
                # Completed
                stdout, stderr = await process.communicate()

                result = {
                    "success": process.returncode == 0,
                    "job_id": job_id,
                    "status": "completed",
                    "exit_code": process.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace") if stdout else "",
                    "stderr": stderr.decode("utf-8", errors="replace") if stderr else "",
                }

                # Remove from jobs
                del self.background_jobs[job_id]

                return result

        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return create_error_response(e)

    async def kill_job(self, job_id: str) -> Dict[str, Any]:
        """
        Kill a background job.

        Args:
            job_id: Job ID

        Returns:
            Dictionary with result
        """
        try:
            if job_id not in self.background_jobs:
                raise ToolError(f"Job not found: {job_id}")

            process = self.background_jobs[job_id]
            process.kill()
            await process.wait()

            del self.background_jobs[job_id]

            return {
                "success": True,
                "job_id": job_id,
                "message": f"Job {job_id} killed",
            }

        except Exception as e:
            logger.error(f"Error killing job: {e}")
            return create_error_response(e)
