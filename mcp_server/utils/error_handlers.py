"""Error handling utilities for MCP tools."""

from typing import Any, Dict, Optional, Type
from enum import Enum
import traceback


class ErrorType(str, Enum):
    """Error types for categorization."""

    PERMISSION_DENIED = "permission_denied"
    FILE_NOT_FOUND = "file_not_found"
    INVALID_INPUT = "invalid_input"
    SYNTAX_ERROR = "syntax_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


class ToolError(Exception):
    """Base exception for tool errors with structured information."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[list[str]] = None,
        retryable: bool = False,
        retry_strategy: Optional[str] = None,
    ):
        """
        Initialize tool error.

        Args:
            message: Error message
            error_type: Type of error
            details: Additional error details
            suggestions: Suggestions to fix the error
            retryable: Whether the error is retryable
            retry_strategy: Suggested retry strategy
        """
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.suggestions = suggestions or []
        self.retryable = retryable
        self.retry_strategy = retry_strategy

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for structured response."""
        return {
            "error": True,
            "error_type": self.error_type.value,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "retryable": self.retryable,
            "retry_strategy": self.retry_strategy,
        }


class PermissionError(ToolError):
    """Permission denied error."""

    def __init__(self, message: str, path: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if path:
            details["path"] = path
        super().__init__(
            message=message,
            error_type=ErrorType.PERMISSION_DENIED,
            details=details,
            suggestions=[
                "Check if the path requires user approval",
                "Verify the path is not in the blocked list",
                "Try requesting permission first",
            ],
            retryable=True,
            retry_strategy="request_approval",
            **kwargs,
        )


class FileNotFoundError(ToolError):
    """File not found error."""

    def __init__(self, message: str, path: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if path:
            details["path"] = path
        super().__init__(
            message=message,
            error_type=ErrorType.FILE_NOT_FOUND,
            details=details,
            suggestions=[
                "Check if the file path is correct",
                "Use Glob to search for similar files",
                "Verify the file exists in the directory",
            ],
            retryable=True,
            retry_strategy="search_alternatives",
            **kwargs,
        )


class ValidationError(ToolError):
    """Input validation error."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            error_type=ErrorType.INVALID_INPUT,
            details=details,
            retryable=False,
            **kwargs,
        )


class NetworkError(ToolError):
    """Network-related error."""

    def __init__(self, message: str, url: Optional[str] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if url:
            details["url"] = url
        super().__init__(
            message=message,
            error_type=ErrorType.NETWORK_ERROR,
            details=details,
            suggestions=["Check network connectivity", "Verify the URL is accessible"],
            retryable=True,
            retry_strategy="exponential_backoff",
            **kwargs,
        )


class TimeoutError(ToolError):
    """Timeout error."""

    def __init__(self, message: str, timeout: Optional[int] = None, **kwargs: Any):
        details = kwargs.pop("details", {})
        if timeout:
            details["timeout_seconds"] = timeout
        super().__init__(
            message=message,
            error_type=ErrorType.TIMEOUT,
            details=details,
            suggestions=["Increase timeout value", "Check if the operation is too slow"],
            retryable=True,
            retry_strategy="increase_timeout",
            **kwargs,
        )


class RateLimitError(ToolError):
    """Rate limit exceeded error."""

    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        retry_after: Optional[int] = None,
        **kwargs: Any,
    ):
        details = kwargs.pop("details", {})
        if limit:
            details["rate_limit"] = limit
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message=message,
            error_type=ErrorType.RATE_LIMIT,
            details=details,
            suggestions=[f"Wait {retry_after} seconds before retrying" if retry_after else "Wait before retrying"],
            retryable=True,
            retry_strategy="wait_and_retry",
            **kwargs,
        )


def create_error_response(
    error: Exception,
    include_traceback: bool = False,
) -> Dict[str, Any]:
    """
    Create a structured error response from an exception.

    Args:
        error: The exception
        include_traceback: Whether to include stack trace

    Returns:
        Structured error response
    """
    if isinstance(error, ToolError):
        response = error.to_dict()
    else:
        # Handle standard exceptions
        response = {
            "error": True,
            "error_type": ErrorType.UNKNOWN.value,
            "message": str(error),
            "details": {"exception_type": type(error).__name__},
            "suggestions": [],
            "retryable": False,
            "retry_strategy": None,
        }

    if include_traceback:
        response["traceback"] = traceback.format_exc()

    return response


def map_exception_to_error(exc: Exception) -> ToolError:
    """
    Map standard Python exceptions to ToolError.

    Args:
        exc: Standard Python exception

    Returns:
        Mapped ToolError
    """
    import builtins

    exc_type = type(exc)

    if exc_type == builtins.FileNotFoundError:
        return FileNotFoundError(str(exc))
    elif exc_type == builtins.PermissionError:
        return PermissionError(str(exc))
    elif exc_type == builtins.ValueError:
        return ValidationError(str(exc))
    elif exc_type == builtins.TimeoutError:
        return TimeoutError(str(exc))
    else:
        return ToolError(str(exc), error_type=ErrorType.UNKNOWN)
