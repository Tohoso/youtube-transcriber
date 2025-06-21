"""
Custom exception classes for YouTube Transcriber application
"""
from typing import Optional, Dict, Any
from datetime import datetime


class TranscriberError(Exception):
    """Base exception class for all transcriber errors"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.retry_after = retry_after
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details,
            'retry_after': self.retry_after,
            'timestamp': self.timestamp.isoformat()
        }


class APIError(TranscriberError):
    """Base class for API-related errors"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body
        if status_code:
            self.details['status_code'] = status_code
        if response_body:
            self.details['response_body'] = response_body


class YouTubeAPIError(APIError):
    """YouTube Data API specific errors"""
    
    def __init__(
        self,
        message: str,
        reason: Optional[str] = None,
        domain: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.reason = reason
        self.domain = domain
        if reason:
            self.details['reason'] = reason
        if domain:
            self.details['domain'] = domain
        
        # Set error code based on YouTube API error reasons
        if reason:
            self.error_code = f"YOUTUBE_{reason.upper()}"


class TranscriptNotFoundError(TranscriberError):
    """Raised when transcript is not available for a video"""
    
    def __init__(
        self,
        video_id: str,
        message: Optional[str] = None,
        available_languages: Optional[list] = None,
        **kwargs
    ):
        if not message:
            message = f"No transcript found for video: {video_id}"
        super().__init__(message, error_code="TRANSCRIPT_NOT_FOUND", **kwargs)
        self.video_id = video_id
        self.available_languages = available_languages or []
        self.details.update({
            'video_id': video_id,
            'available_languages': available_languages
        })


class ConfigurationError(TranscriberError):
    """Raised when there's a configuration issue"""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
        self.config_key = config_key
        self.expected_type = expected_type
        self.actual_value = actual_value
        self.details.update({
            'config_key': config_key,
            'expected_type': expected_type,
            'actual_value': str(actual_value) if actual_value is not None else None
        })


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    
    def __init__(
        self,
        message: str,
        retry_after_seconds: Optional[int] = None,
        quota_used: Optional[int] = None,
        quota_limit: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            message,
            status_code=429,
            retry_after=retry_after_seconds,
            **kwargs
        )
        self.error_code = "RATE_LIMIT_EXCEEDED"
        self.quota_used = quota_used
        self.quota_limit = quota_limit
        self.details.update({
            'quota_used': quota_used,
            'quota_limit': quota_limit,
            'retry_after_seconds': retry_after_seconds
        })


class NetworkError(TranscriberError):
    """Raised when network-related errors occur"""
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, error_code="NETWORK_ERROR", **kwargs)
        self.url = url
        self.timeout = timeout
        self.original_error = original_error
        self.details.update({
            'url': url,
            'timeout': timeout,
            'original_error_type': type(original_error).__name__ if original_error else None,
            'original_error_message': str(original_error) if original_error else None
        })


class ValidationError(TranscriberError):
    """Raised when input validation fails"""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.validation_rule = validation_rule
        self.details.update({
            'field_name': field_name,
            'invalid_value': str(invalid_value) if invalid_value is not None else None,
            'validation_rule': validation_rule
        })


class FileWriteError(TranscriberError):
    """Raised when file writing operations fail"""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        super().__init__(message, error_code="FILE_WRITE_ERROR", **kwargs)
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error
        self.details.update({
            'file_path': file_path,
            'operation': operation,
            'original_error_type': type(original_error).__name__ if original_error else None,
            'original_error_message': str(original_error) if original_error else None
        })


class ProcessingError(TranscriberError):
    """Raised when processing operations fail"""
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        item_id: Optional[str] = None,
        item_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, error_code="PROCESSING_ERROR", **kwargs)
        self.stage = stage
        self.item_id = item_id
        self.item_type = item_type
        self.details.update({
            'stage': stage,
            'item_id': item_id,
            'item_type': item_type
        })