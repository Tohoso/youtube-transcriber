"""Enhanced error handling with user-friendly messages and recovery strategies."""

import asyncio
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union
from loguru import logger


class ErrorCategory:
    """Error categorization for better handling."""
    NETWORK = "Network Error"
    PERMISSION = "Permission Error"
    NOT_FOUND = "Not Found"
    RATE_LIMIT = "Rate Limit"
    QUOTA = "Quota Exceeded"
    TIMEOUT = "Timeout"
    TRANSCRIPT = "Transcript Error"
    FORMAT = "Format Error"
    UNKNOWN = "Unknown Error"


class UserFriendlyError(Exception):
    """Base exception with user-friendly message."""
    
    def __init__(self, technical_message: str, user_message: str, recovery_hint: Optional[str] = None):
        self.technical_message = technical_message
        self.user_message = user_message
        self.recovery_hint = recovery_hint
        super().__init__(technical_message)


class ErrorHandler:
    """Enhanced error handler with recovery strategies."""
    
    # Mapping of error patterns to categories and user messages
    ERROR_PATTERNS = {
        "network": {
            "category": ErrorCategory.NETWORK,
            "message": "Network connection issue detected",
            "hint": "Please check your internet connection and try again"
        },
        "connection": {
            "category": ErrorCategory.NETWORK,
            "message": "Unable to connect to YouTube",
            "hint": "The service might be temporarily unavailable"
        },
        "403": {
            "category": ErrorCategory.PERMISSION,
            "message": "Access denied to this resource",
            "hint": "The video might be private or restricted in your region"
        },
        "404": {
            "category": ErrorCategory.NOT_FOUND,
            "message": "Resource not found",
            "hint": "Please verify the channel URL or video ID"
        },
        "429": {
            "category": ErrorCategory.RATE_LIMIT,
            "message": "Too many requests",
            "hint": "Please wait a moment before trying again"
        },
        "quota": {
            "category": ErrorCategory.QUOTA,
            "message": "API quota limit reached",
            "hint": "Daily limit exceeded. Try again tomorrow or use a different API key"
        },
        "timeout": {
            "category": ErrorCategory.TIMEOUT,
            "message": "Request timed out",
            "hint": "The operation took too long. Try again with fewer videos"
        },
        "transcript": {
            "category": ErrorCategory.TRANSCRIPT,
            "message": "Unable to retrieve transcript",
            "hint": "This video might not have captions available"
        },
        "no transcript": {
            "category": ErrorCategory.TRANSCRIPT,
            "message": "No transcript available",
            "hint": "Try enabling auto-generated captions or choose a different video"
        }
    }
    
    @classmethod
    def categorize_error(cls, error: Exception) -> tuple[str, str, str]:
        """Categorize error and return category, user message, and hint.
        
        Args:
            error: The exception to categorize
            
        Returns:
            Tuple of (category, user_message, recovery_hint)
        """
        error_str = str(error).lower()
        
        # Check error patterns
        for pattern, info in cls.ERROR_PATTERNS.items():
            if pattern in error_str:
                return info["category"], info["message"], info["hint"]
        
        # Specific exception types
        if isinstance(error, asyncio.TimeoutError):
            return ErrorCategory.TIMEOUT, "Operation timed out", "Try reducing the number of concurrent operations"
        
        if isinstance(error, PermissionError):
            return ErrorCategory.PERMISSION, "Permission denied", "Check file permissions and API credentials"
        
        # Default unknown error
        return ErrorCategory.UNKNOWN, "An unexpected error occurred", "Please try again or contact support"
    
    @classmethod
    def create_user_friendly_error(cls, error: Exception) -> UserFriendlyError:
        """Convert technical error to user-friendly error.
        
        Args:
            error: The original exception
            
        Returns:
            UserFriendlyError with helpful messages
        """
        category, user_message, hint = cls.categorize_error(error)
        
        # Log technical details
        logger.error(f"[{category}] {error.__class__.__name__}: {str(error)}")
        
        return UserFriendlyError(
            technical_message=str(error),
            user_message=user_message,
            recovery_hint=hint
        )
    
    @classmethod
    def wrap_with_fallback(cls, fallback_result: Any = None, reraise: bool = False):
        """Decorator to wrap functions with error handling and fallback.
        
        Args:
            fallback_result: Result to return on error
            reraise: Whether to reraise the error after handling
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    user_error = cls.create_user_friendly_error(e)
                    
                    # Log the error with context
                    logger.error(
                        f"Error in {func.__name__}: {user_error.user_message}",
                        exc_info=True
                    )
                    
                    if reraise:
                        raise user_error
                    
                    return fallback_result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    user_error = cls.create_user_friendly_error(e)
                    
                    # Log the error with context
                    logger.error(
                        f"Error in {func.__name__}: {user_error.user_message}",
                        exc_info=True
                    )
                    
                    if reraise:
                        raise user_error
                    
                    return fallback_result
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    @staticmethod
    def get_recovery_strategy(error_category: str) -> Dict[str, Any]:
        """Get recovery strategy for error category.
        
        Args:
            error_category: The error category
            
        Returns:
            Dictionary with recovery strategy details
        """
        strategies = {
            ErrorCategory.NETWORK: {
                "retry": True,
                "retry_count": 3,
                "retry_delay": 5,
                "fallback": "offline_mode"
            },
            ErrorCategory.RATE_LIMIT: {
                "retry": True,
                "retry_count": 1,
                "retry_delay": 60,
                "fallback": "reduce_rate"
            },
            ErrorCategory.QUOTA: {
                "retry": False,
                "fallback": "wait_for_reset",
                "alternative": "use_different_key"
            },
            ErrorCategory.TIMEOUT: {
                "retry": True,
                "retry_count": 2,
                "retry_delay": 10,
                "fallback": "reduce_batch_size"
            },
            ErrorCategory.TRANSCRIPT: {
                "retry": False,
                "fallback": "skip_video",
                "alternative": "try_different_language"
            },
            ErrorCategory.NOT_FOUND: {
                "retry": False,
                "fallback": "skip_resource"
            },
            ErrorCategory.PERMISSION: {
                "retry": False,
                "fallback": "skip_resource"
            },
            ErrorCategory.UNKNOWN: {
                "retry": True,
                "retry_count": 1,
                "retry_delay": 5,
                "fallback": "log_and_continue"
            }
        }
        
        return strategies.get(error_category, strategies[ErrorCategory.UNKNOWN])


class ErrorAggregator:
    """Aggregate and analyze errors for batch operations."""
    
    def __init__(self):
        self.errors: list[tuple[str, Exception]] = []
        self.error_counts: Dict[str, int] = {}
    
    def add_error(self, context: str, error: Exception) -> None:
        """Add an error with context."""
        self.errors.append((context, error))
        
        category, _, _ = ErrorHandler.categorize_error(error)
        self.error_counts[category] = self.error_counts.get(category, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary."""
        if not self.errors:
            return {"total_errors": 0}
        
        most_common = max(self.error_counts.items(), key=lambda x: x[1])
        
        return {
            "total_errors": len(self.errors),
            "error_categories": dict(self.error_counts),
            "most_common_error": most_common[0],
            "most_common_count": most_common[1],
            "error_rate": len(self.errors) / len(self.errors)  # Will be updated with total operations
        }
    
    def get_user_friendly_summary(self) -> str:
        """Get user-friendly error summary."""
        if not self.errors:
            return "No errors occurred."
        
        summary = self.get_summary()
        lines = [
            f"Total errors: {summary['total_errors']}",
            f"Most common issue: {summary['most_common_error']} ({summary['most_common_count']} occurrences)"
        ]
        
        # Add specific advice based on most common error
        strategy = ErrorHandler.get_recovery_strategy(summary['most_common_error'])
        if strategy.get('alternative'):
            lines.append(f"Suggestion: {strategy['alternative']}")
        
        return "\n".join(lines)


def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any, Optional[Exception]]:
    """Safely execute a function and return success status, result, and error.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Tuple of (success, result, error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        return False, None, e


async def safe_execute_async(func: Callable, *args, **kwargs) -> tuple[bool, Any, Optional[Exception]]:
    """Safely execute an async function and return success status, result, and error.
    
    Args:
        func: Async function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Tuple of (success, result, error)
    """
    try:
        result = await func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        return False, None, e