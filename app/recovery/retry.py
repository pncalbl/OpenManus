"""
Retry mechanism with exponential backoff for resilient operations.
"""

import asyncio
import random
from typing import Any, Callable, Optional, TypeVar

from app.logger import logger
from app.recovery.errors import (
    ErrorCategory,
    FatalError,
    RetryableError,
    classify_error,
    is_retryable,
)


T = TypeVar("T")


class RetryStrategy:
    """Configuration for retry behavior with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_categories: Optional[set[ErrorCategory]] = None,
    ):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff calculation
            jitter: Add random jitter to delay to avoid thundering herd
            retry_on_categories: Specific error categories to retry on (None = all retryable)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on_categories = retry_on_categories

    def get_delay(self, attempt: int, suggested_delay: Optional[float] = None) -> float:
        """
        Calculate delay before next retry using exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)
            suggested_delay: Override delay suggested by error

        Returns:
            Delay in seconds
        """
        if suggested_delay is not None:
            base_delay = suggested_delay
        else:
            # Exponential backoff: initial_delay * (base ^ attempt)
            base_delay = min(
                self.initial_delay * (self.exponential_base**attempt), self.max_delay
            )

        # Add jitter: multiply by random value between 0.5 and 1.5
        if self.jitter:
            jitter_factor = 0.5 + random.random()  # 0.5 to 1.5
            base_delay *= jitter_factor

        return base_delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if an error should be retried.

        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        # Check if we've exceeded max retries
        if attempt >= self.max_retries:
            return False

        # Check if error is retryable
        if not is_retryable(error):
            return False

        # If specific categories specified, check if error matches
        if self.retry_on_categories:
            category = classify_error(error)
            return category in self.retry_on_categories

        return True


class RetryHandler:
    """Handler for executing operations with retry logic."""

    def __init__(self, default_strategy: Optional[RetryStrategy] = None):
        """
        Initialize retry handler.

        Args:
            default_strategy: Default retry strategy to use
        """
        self.default_strategy = default_strategy or RetryStrategy()
        self.retry_stats = {
            "total_attempts": 0,
            "successful_retries": 0,
            "failed_retries": 0,
        }

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        strategy: Optional[RetryStrategy] = None,
        on_retry: Optional[Callable[[Exception, int, float], None]] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with automatic retry on failure.

        Args:
            func: Function to execute (can be sync or async)
            *args: Positional arguments for func
            strategy: Retry strategy (uses default if None)
            on_retry: Optional callback called before each retry
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            Last exception if all retries exhausted
        """
        strategy = strategy or self.default_strategy
        last_exception = None

        for attempt in range(strategy.max_retries + 1):
            self.retry_stats["total_attempts"] += 1

            try:
                # Execute function (handle both sync and async)
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success!
                if attempt > 0:
                    self.retry_stats["successful_retries"] += 1
                    logger.info(
                        f"Operation succeeded after {attempt} retry(ies)"
                    )

                return result

            except Exception as e:
                last_exception = e
                category = classify_error(e)

                # Check if we should retry this error
                if not strategy.should_retry(e, attempt):
                    logger.error(
                        f"Non-retryable error or max retries reached: {type(e).__name__}: {e}"
                    )
                    self.retry_stats["failed_retries"] += 1
                    raise

                # Calculate delay
                suggested_delay = (
                    e.suggested_delay
                    if isinstance(e, RetryableError)
                    else None
                )
                delay = strategy.get_delay(attempt, suggested_delay)

                # Log retry attempt
                logger.warning(
                    f"Retry {attempt + 1}/{strategy.max_retries} "
                    f"after {delay:.1f}s due to {category.value} error: {e}"
                )

                # Call retry callback if provided
                if on_retry:
                    on_retry(e, attempt, delay)

                # Wait before retry
                await asyncio.sleep(delay)

        # All retries exhausted
        self.retry_stats["failed_retries"] += 1
        logger.error(f"All {strategy.max_retries} retries exhausted")
        raise last_exception

    def get_stats(self) -> dict:
        """
        Get retry statistics.

        Returns:
            Dictionary of retry stats
        """
        return self.retry_stats.copy()

    def reset_stats(self):
        """Reset retry statistics."""
        self.retry_stats = {
            "total_attempts": 0,
            "successful_retries": 0,
            "failed_retries": 0,
        }


# Predefined retry strategies for common scenarios

# For API calls (more aggressive)
API_RETRY_STRATEGY = RetryStrategy(
    max_retries=5,
    initial_delay=2.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_categories={
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.API,
        ErrorCategory.RATE_LIMIT,
    },
)

# For browser operations
BROWSER_RETRY_STRATEGY = RetryStrategy(
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retry_on_categories={ErrorCategory.BROWSER, ErrorCategory.NETWORK},
)

# For file operations
FILESYSTEM_RETRY_STRATEGY = RetryStrategy(
    max_retries=2,
    initial_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0,
    jitter=False,
    retry_on_categories={ErrorCategory.FILESYSTEM},
)

# Quick retries for transient errors
QUICK_RETRY_STRATEGY = RetryStrategy(
    max_retries=2, initial_delay=0.5, max_delay=2.0, exponential_base=2.0, jitter=True
)
