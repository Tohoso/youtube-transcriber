"""
Error handler utilities for graceful error handling and recovery
"""
import asyncio
from typing import Optional, Dict, Any, Callable, TypeVar, Union, List
from functools import wraps
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from loguru import logger

from src.exceptions import (
    TranscriberError,
    APIError,
    RateLimitError,
    NetworkError,
    TranscriptNotFoundError,
    FileWriteError,
    ProcessingError,
    YouTubeAPIError
)
from src.utils.retry import async_retry, API_RETRY_CONFIG, NETWORK_RETRY_CONFIG
from src.utils.error_logging import log_error

T = TypeVar('T')


class ErrorHandler:
    """Central error handler with recovery strategies"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_errors: Dict[str, datetime] = {}
        self.circuit_breakers: Dict[str, 'CircuitBreaker'] = {}
    
    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        recovery_strategy: Optional[Callable] = None
    ) -> Optional[Any]:
        """Handle error with optional recovery strategy"""
        # Log error
        log_error(
            error,
            context=context,
            video_id=context.get('video_id'),
            channel_id=context.get('channel_id')
        )
        
        # Update error counts
        error_key = f"{type(error).__name__}:{context.get('operation', 'unknown')}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_errors[error_key] = datetime.now()
        
        # Apply recovery strategy if provided
        if recovery_strategy:
            try:
                return recovery_strategy(error, context)
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
                return None
        
        # Default handling based on error type
        return self._default_error_handling(error, context)
    
    def _default_error_handling(self, error: Exception, context: Dict[str, Any]) -> Optional[Any]:
        """Default error handling based on error type"""
        if isinstance(error, RateLimitError):
            # Return retry information
            return {
                'should_retry': True,
                'retry_after': error.retry_after or 60,
                'action': 'wait_and_retry'
            }
        elif isinstance(error, TranscriptNotFoundError):
            # Mark as permanently failed
            return {
                'should_retry': False,
                'action': 'skip',
                'reason': 'transcript_not_available'
            }
        elif isinstance(error, NetworkError):
            # Retry with backoff
            return {
                'should_retry': True,
                'retry_after': 5,
                'action': 'retry_with_backoff'
            }
        else:
            # Unknown error, log and skip
            return {
                'should_retry': False,
                'action': 'skip',
                'reason': 'unknown_error'
            }
    
    def get_circuit_breaker(self, service_name: str) -> 'CircuitBreaker':
        """Get or create circuit breaker for service"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                failure_threshold=5,
                recovery_timeout=60
            )
        return self.circuit_breakers[service_name]


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance"""
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._state = 'closed'  # closed, open, half_open
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state"""
        if self._state == 'open':
            if self._last_failure_time and \
               datetime.now() - self._last_failure_time > timedelta(seconds=self.recovery_timeout):
                self._state = 'half_open'
                logger.info(f"Circuit breaker for {self.service_name} moved to half_open state")
        return self._state
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function with circuit breaker protection"""
        if self.state == 'open':
            raise ProcessingError(
                f"Circuit breaker for {self.service_name} is open",
                stage='circuit_breaker',
                item_type=self.service_name
            )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def async_call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Async call function with circuit breaker protection"""
        if self.state == 'open':
            raise ProcessingError(
                f"Circuit breaker for {self.service_name} is open",
                stage='circuit_breaker',
                item_type=self.service_name
            )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        if self._state == 'half_open':
            self._state = 'closed'
            self._failure_count = 0
            logger.info(f"Circuit breaker for {self.service_name} closed after successful call")
    
    def _on_failure(self):
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self.failure_threshold:
            self._state = 'open'
            logger.warning(
                f"Circuit breaker for {self.service_name} opened after "
                f"{self._failure_count} failures"
            )


def with_error_handling(
    fallback_value: Any = None,
    error_types: tuple = (Exception,),
    log_errors: bool = True
):
    """Decorator for functions with error handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except error_types as e:
                if log_errors:
                    log_error(e, context={'function': func.__name__, 'args': args, 'kwargs': kwargs})
                return fallback_value
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                if log_errors:
                    log_error(e, context={'function': func.__name__, 'args': args, 'kwargs': kwargs})
                return fallback_value
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def handle_youtube_errors(video_id: Optional[str] = None):
    """Context manager for handling YouTube-specific errors"""
    try:
        yield
    except YouTubeAPIError as e:
        if e.reason == 'quotaExceeded':
            raise RateLimitError(
                "YouTube API quota exceeded",
                quota_used=e.details.get('quota_used'),
                quota_limit=e.details.get('quota_limit'),
                retry_after_seconds=3600  # Wait 1 hour
            )
        elif e.reason == 'videoNotFound':
            raise ProcessingError(
                f"Video not found: {video_id}",
                stage='youtube_api',
                item_id=video_id,
                item_type='video'
            )
        else:
            raise
    except Exception as e:
        if 'HttpError 403' in str(e):
            raise APIError(
                "YouTube API access forbidden",
                status_code=403,
                details={'video_id': video_id}
            )
        raise


@contextmanager
def suppress_and_log(*exceptions: type, context: Optional[Dict[str, Any]] = None):
    """Context manager to suppress and log specific exceptions"""
    try:
        yield
    except exceptions as e:
        log_error(e, context=context)


class RateLimiter:
    """Rate limiter with quota management"""
    
    def __init__(
        self,
        max_requests: int,
        time_window: timedelta = timedelta(minutes=1),
        quota_limit: Optional[int] = None
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.quota_limit = quota_limit
        
        self.requests: List[datetime] = []
        self.quota_used = 0
    
    async def acquire(self, quota_cost: int = 1):
        """Acquire permission to make a request"""
        now = datetime.now()
        
        # Remove old requests outside time window
        self.requests = [req for req in self.requests if now - req < self.time_window]
        
        # Check rate limit
        if len(self.requests) >= self.max_requests:
            wait_time = (self.requests[0] + self.time_window - now).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                return await self.acquire(quota_cost)  # Retry
        
        # Check quota limit
        if self.quota_limit and self.quota_used + quota_cost > self.quota_limit:
            raise RateLimitError(
                "Quota limit exceeded",
                quota_used=self.quota_used,
                quota_limit=self.quota_limit,
                retry_after_seconds=86400  # 24 hours
            )
        
        # Record request
        self.requests.append(now)
        self.quota_used += quota_cost
    
    def reset_quota(self):
        """Reset quota counter"""
        self.quota_used = 0
        logger.info("Quota counter reset")


# Global error handler instance
error_handler = ErrorHandler()


# Recovery strategies
def skip_on_transcript_not_found(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Recovery strategy for transcript not found errors"""
    if isinstance(error, TranscriptNotFoundError):
        return {
            'action': 'skip',
            'reason': 'transcript_not_available',
            'video_id': error.video_id,
            'available_languages': error.available_languages
        }
    raise error


def retry_on_network_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Recovery strategy for network errors"""
    if isinstance(error, NetworkError):
        return {
            'action': 'retry',
            'retry_config': NETWORK_RETRY_CONFIG,
            'reason': 'network_error'
        }
    raise error


def wait_on_rate_limit(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Recovery strategy for rate limit errors"""
    if isinstance(error, RateLimitError):
        return {
            'action': 'wait',
            'wait_time': error.retry_after or 60,
            'reason': 'rate_limit_exceeded'
        }
    raise error