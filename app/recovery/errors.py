"""
Error classification and custom exceptions for recovery module.
"""

from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Categories of errors for diagnosis and recovery."""

    NETWORK = "network"  # Network connectivity issues
    API = "api"  # API call failures
    RATE_LIMIT = "rate_limit"  # Rate limiting / quota exceeded
    AUTHENTICATION = "auth"  # Authentication / authorization failures
    BROWSER = "browser"  # Browser automation errors
    FILESYSTEM = "filesystem"  # File system operations
    TIMEOUT = "timeout"  # Operation timeouts
    CONFIGURATION = "config"  # Configuration errors
    RESOURCE = "resource"  # Resource unavailable (memory, disk, etc.)
    UNKNOWN = "unknown"  # Unclassified errors


class RecoveryError(Exception):
    """Base exception for recovery-related errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        original_error: Optional[Exception] = None,
    ):
        self.message = message
        self.category = category
        self.original_error = original_error
        super().__init__(message)


class RetryableError(RecoveryError):
    """Error that can be retried with exponential backoff."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        original_error: Optional[Exception] = None,
        suggested_delay: Optional[float] = None,
    ):
        super().__init__(message, category, original_error)
        self.retryable = True
        self.suggested_delay = suggested_delay  # Override default delay


class FatalError(RecoveryError):
    """Fatal error that should not be retried."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message, category, original_error)
        self.retryable = False


def classify_error(error: Exception) -> ErrorCategory:
    """
    Classify an exception into an error category.

    Args:
        error: The exception to classify

    Returns:
        ErrorCategory enum value
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Network errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in [
            "connection",
            "network",
            "unreachable",
            "dns",
            "socket",
            "connectionerror",
            "connectionrefusederror",
        ]
    ):
        return ErrorCategory.NETWORK

    # Timeout errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in ["timeout", "timed out", "timeouterror"]
    ):
        return ErrorCategory.TIMEOUT

    # Rate limiting
    if any(
        keyword in error_str
        for keyword in ["rate limit", "429", "too many requests", "quota"]
    ):
        return ErrorCategory.RATE_LIMIT

    # Authentication errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in [
            "api key",
            "authentication",
            "unauthorized",
            "401",
            "403",
            "forbidden",
            "invalid key",
        ]
    ):
        return ErrorCategory.AUTHENTICATION

    # Browser errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in [
            "browser",
            "playwright",
            "selenium",
            "chrome",
            "firefox",
            "page crashed",
        ]
    ):
        return ErrorCategory.BROWSER

    # Filesystem errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in [
            "file not found",
            "permission denied",
            "disk",
            "filesystem",
            "ioerror",
            "oserror",
        ]
    ):
        return ErrorCategory.FILESYSTEM

    # Configuration errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in ["config", "configuration", "missing", "not configured"]
    ):
        return ErrorCategory.CONFIGURATION

    # Resource errors
    if any(
        keyword in error_str or keyword in error_type
        for keyword in ["memory", "out of memory", "resource", "memoryerror"]
    ):
        return ErrorCategory.RESOURCE

    # API errors (generic)
    if any(
        keyword in error_str or keyword in error_type
        for keyword in ["api", "500", "502", "503", "504", "bad gateway"]
    ):
        return ErrorCategory.API

    return ErrorCategory.UNKNOWN


def is_retryable(error: Exception) -> bool:
    """
    Determine if an error is retryable.

    Args:
        error: The exception to check

    Returns:
        True if the error can be retried
    """
    # If it's one of our custom errors, use the retryable attribute
    if isinstance(error, (RetryableError, FatalError)):
        return error.retryable

    # Classify the error and determine if it's retryable
    category = classify_error(error)

    # These categories are typically retryable
    retryable_categories = {
        ErrorCategory.NETWORK,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.API,
        ErrorCategory.BROWSER,
    }

    # These are typically not retryable
    fatal_categories = {
        ErrorCategory.AUTHENTICATION,
        ErrorCategory.CONFIGURATION,
        ErrorCategory.FILESYSTEM,
    }

    if category in retryable_categories:
        return True
    elif category in fatal_categories:
        return False

    # For unknown errors, be conservative and don't retry
    return False
