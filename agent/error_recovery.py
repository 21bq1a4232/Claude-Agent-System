"""Intelligent error recovery system."""

import time
from typing import Any, Dict, Optional
from enum import Enum


class RetryStrategy(str, Enum):
    """Retry strategies."""
    REQUEST_APPROVAL = "request_approval"
    SEARCH_ALTERNATIVES = "search_alternatives"
    FIX_AND_RETRY = "fix_and_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    INCREASE_TIMEOUT = "increase_timeout"
    WAIT_AND_RETRY = "wait_and_retry"
    REPORT_AND_ASK = "report_and_ask"


class ErrorRecoverySystem:
    """System for intelligent error recovery and retry logic."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize error recovery system.

        Args:
            config: Error recovery configuration
        """
        self.config = config.get("error_recovery", {})
        self.enabled = self.config.get("enabled", True)
        self.max_retries = self.config.get("max_retries", 3)
        self.strategies = self.config.get("strategies", {})
        self.retry_counts: Dict[str, int] = {}

    def should_retry(self, error: Dict[str, Any], operation_id: str) -> bool:
        """
        Determine if an operation should be retried.

        Args:
            error: Error information
            operation_id: Unique operation identifier

        Returns:
            True if should retry
        """
        if not self.enabled:
            return False

        if not error.get("retryable", False):
            return False

        retry_count = self.retry_counts.get(operation_id, 0)
        if retry_count >= self.max_retries:
            return False

        return True

    def get_retry_strategy(self, error: Dict[str, Any]) -> Optional[RetryStrategy]:
        """
        Get retry strategy for an error.

        Args:
            error: Error information

        Returns:
            Retry strategy or None
        """
        error_type = error.get("error_type", "unknown")
        strategy_name = error.get("retry_strategy")

        if not strategy_name:
            strategy_config = self.strategies.get(error_type, {})
            strategy_name = strategy_config.get("action")

        if strategy_name:
            try:
                return RetryStrategy(strategy_name)
            except ValueError:
                return RetryStrategy.REPORT_AND_ASK

        return None

    async def handle_error(
        self,
        error: Dict[str, Any],
        operation_id: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle an error with intelligent recovery.

        Args:
            error: Error information
            operation_id: Operation identifier
            context: Operation context

        Returns:
            Recovery action to take
        """
        if not self.should_retry(error, operation_id):
            return {
                "action": "fail",
                "message": "Maximum retries exceeded or error not retryable",
                "error": error,
            }

        strategy = self.get_retry_strategy(error)
        if not strategy:
            return {
                "action": "fail",
                "message": "No retry strategy available",
                "error": error,
            }

        # Increment retry count
        self.retry_counts[operation_id] = self.retry_counts.get(operation_id, 0) + 1

        # Execute strategy
        recovery = await self._execute_strategy(strategy, error, context)
        recovery["retry_count"] = self.retry_counts[operation_id]

        return recovery

    async def _execute_strategy(
        self,
        strategy: RetryStrategy,
        error: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a specific retry strategy."""

        if strategy == RetryStrategy.REQUEST_APPROVAL:
            return {
                "action": "request_approval",
                "message": "Requesting user approval",
                "resource": context.get("resource"),
                "operation": context.get("operation"),
                "suggestions": error.get("suggestions", []),
            }

        elif strategy == RetryStrategy.SEARCH_ALTERNATIVES:
            return {
                "action": "search",
                "message": "Searching for alternatives",
                "pattern": context.get("pattern"),
                "suggestions": error.get("suggestions", []),
            }

        elif strategy == RetryStrategy.FIX_AND_RETRY:
            return {
                "action": "fix",
                "message": "Attempting to fix the issue",
                "error_details": error.get("details", {}),
                "suggestions": error.get("suggestions", []),
            }

        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            backoff_config = self.strategies.get("network_error", {})
            backoff_base = backoff_config.get("backoff_base", 2)
            backoff_max = backoff_config.get("backoff_max", 30)
            retry_count = self.retry_counts.get(context.get("operation_id", ""), 0)

            wait_time = min(backoff_base ** retry_count, backoff_max)

            return {
                "action": "wait",
                "message": f"Waiting {wait_time}s before retry (exponential backoff)",
                "wait_seconds": wait_time,
            }

        elif strategy == RetryStrategy.INCREASE_TIMEOUT:
            timeout_config = self.strategies.get("timeout", {})
            multiplier = timeout_config.get("timeout_multiplier", 1.5)
            current_timeout = context.get("timeout", 30)
            new_timeout = int(current_timeout * multiplier)

            return {
                "action": "retry",
                "message": f"Increasing timeout to {new_timeout}s",
                "new_timeout": new_timeout,
            }

        elif strategy == RetryStrategy.WAIT_AND_RETRY:
            retry_after = error.get("details", {}).get("retry_after_seconds", 5)
            return {
                "action": "wait",
                "message": f"Waiting {retry_after}s before retry",
                "wait_seconds": retry_after,
            }

        else:  # REPORT_AND_ASK
            return {
                "action": "ask_user",
                "message": "Need user input to proceed",
                "error": error,
                "suggestions": error.get("suggestions", []),
            }

    def reset_retry_count(self, operation_id: str) -> None:
        """Reset retry count for an operation."""
        if operation_id in self.retry_counts:
            del self.retry_counts[operation_id]

    def get_retry_count(self, operation_id: str) -> int:
        """Get current retry count for an operation."""
        return self.retry_counts.get(operation_id, 0)
