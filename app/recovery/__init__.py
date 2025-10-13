"""
Error recovery and resilience module for OpenManus.

This module provides:
- Automatic retry with exponential backoff
- Error diagnosis and suggestions
- Checkpoint and rollback mechanisms
- Graceful degradation
"""

from app.recovery.errors import (
    ErrorCategory,
    FatalError,
    RecoveryError,
    RetryableError,
)
from app.recovery.retry import RetryHandler, RetryStrategy


__all__ = [
    "ErrorCategory",
    "RetryableError",
    "FatalError",
    "RecoveryError",
    "RetryStrategy",
    "RetryHandler",
]


def get_retry_handler() -> RetryHandler:
    """Get or create the global retry handler instance."""
    global _retry_handler_instance
    if "_retry_handler_instance" not in globals():
        _retry_handler_instance = RetryHandler()
    return _retry_handler_instance
