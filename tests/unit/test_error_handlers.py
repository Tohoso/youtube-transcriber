"""Unit tests for error handling utilities."""

import pytest
from unittest.mock import Mock, patch
import aiohttp

from src.utils.error_handlers import (
    handle_api_error,
    classify_error,
    format_error_message,
    should_retry_error
)
from src.exceptions.base import (
    YouTubeAPIError,
    TranscriptAPIError,
    NetworkError,
    RateLimitError,
    ConfigurationError
)


class TestErrorClassification:
    """Test error classification and handling."""
    
    def test_classify_youtube_api_errors(self):
        """Test classification of YouTube API specific errors."""
        # Quota exceeded
        error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=403,
            message="quotaExceeded"
        )
        classification = classify_error(error)
        assert classification["type"] == "quota_exceeded"
        assert classification["retryable"] is False
        
        # Invalid API key
        error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=403,
            message="The API key is invalid"
        )
        classification = classify_error(error)
        assert classification["type"] == "auth_error"
        assert classification["retryable"] is False
        
        # Not found
        error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=404,
            message="Channel not found"
        )
        classification = classify_error(error)
        assert classification["type"] == "not_found"
        assert classification["retryable"] is False
    
    def test_classify_network_errors(self):
        """Test classification of network-related errors."""
        # Connection error
        error = aiohttp.ClientConnectionError("Cannot connect to host")
        classification = classify_error(error)
        assert classification["type"] == "connection_error"
        assert classification["retryable"] is True
        
        # Timeout
        error = aiohttp.ServerTimeoutError("Request timeout")
        classification = classify_error(error)
        assert classification["type"] == "timeout"
        assert classification["retryable"] is True
        
        # Server error
        error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=500,
            message="Internal server error"
        )
        classification = classify_error(error)
        assert classification["type"] == "server_error"
        assert classification["retryable"] is True
    
    def test_classify_rate_limit_errors(self):
        """Test classification of rate limit errors."""
        # 429 Too Many Requests
        error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=429,
            message="Too many requests"
        )
        classification = classify_error(error)
        assert classification["type"] == "rate_limit"
        assert classification["retryable"] is True
        assert "retry_after" in classification
    
    def test_classify_unknown_errors(self):
        """Test classification of unknown errors."""
        error = ValueError("Some unexpected error")
        classification = classify_error(error)
        assert classification["type"] == "unknown"
        assert classification["retryable"] is False


class TestErrorHandling:
    """Test error handling functions."""
    
    @pytest.mark.asyncio
    async def test_handle_api_error_with_retry(self):
        """Test API error handling with retry logic."""
        mock_operation = Mock(side_effect=[
            aiohttp.ServerTimeoutError("Timeout"),
            aiohttp.ServerTimeoutError("Timeout"),
            {"success": True}
        ])
        
        result = await handle_api_error(
            mock_operation,
            max_retries=3,
            initial_delay=0.01
        )
        
        assert result == {"success": True}
        assert mock_operation.call_count == 3
    
    @pytest.mark.asyncio
    async def test_handle_api_error_non_retryable(self):
        """Test API error handling with non-retryable error."""
        mock_operation = Mock(side_effect=aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=403,
            message="Invalid API key"
        ))
        
        with pytest.raises(YouTubeAPIError):
            await handle_api_error(
                mock_operation,
                max_retries=3
            )
        
        # Should not retry for auth errors
        assert mock_operation.call_count == 1
    
    @pytest.mark.asyncio
    async def test_handle_api_error_max_retries_exceeded(self):
        """Test API error handling when max retries exceeded."""
        mock_operation = Mock(side_effect=aiohttp.ServerTimeoutError("Timeout"))
        
        with pytest.raises(NetworkError):
            await handle_api_error(
                mock_operation,
                max_retries=3,
                initial_delay=0.01
            )
        
        assert mock_operation.call_count == 3
    
    def test_format_error_message(self):
        """Test error message formatting."""
        # Simple error
        error = ValueError("Test error")
        message = format_error_message(error)
        assert "Test error" in message
        
        # API error with details
        error = aiohttp.ClientResponseError(
            request_info=Mock(url="https://api.example.com/test"),
            history=(),
            status=404,
            message="Not found"
        )
        message = format_error_message(error, include_details=True)
        assert "404" in message
        assert "Not found" in message
        assert "api.example.com" in message
        
        # With context
        error = RuntimeError("Processing failed")
        message = format_error_message(
            error,
            context="While processing video ABC123"
        )
        assert "Processing failed" in message
        assert "While processing video ABC123" in message
    
    def test_should_retry_error(self):
        """Test retry decision logic."""
        # Retryable errors
        retryable_errors = [
            aiohttp.ServerTimeoutError("Timeout"),
            aiohttp.ClientConnectionError("Connection failed"),
            aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=500, message="Server error"
            ),
            aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=429, message="Rate limited"
            ),
        ]
        
        for error in retryable_errors:
            assert should_retry_error(error) is True
        
        # Non-retryable errors
        non_retryable_errors = [
            ValueError("Invalid input"),
            aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=403, message="Forbidden"
            ),
            aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=404, message="Not found"
            ),
            ConfigurationError("Invalid config"),
        ]
        
        for error in non_retryable_errors:
            assert should_retry_error(error) is False


class TestErrorRecovery:
    """Test error recovery strategies."""
    
    @pytest.mark.asyncio
    async def test_partial_failure_recovery(self):
        """Test recovery from partial failures in batch operations."""
        # Simulate batch processing with some failures
        async def process_batch(items):
            results = []
            errors = []
            
            for item in items:
                try:
                    if item == "fail":
                        raise ValueError(f"Failed to process {item}")
                    results.append(f"processed_{item}")
                except Exception as e:
                    errors.append((item, str(e)))
            
            return results, errors
        
        items = ["item1", "fail", "item3", "fail", "item5"]
        results, errors = await process_batch(items)
        
        assert len(results) == 3
        assert len(errors) == 2
        assert "processed_item1" in results
        assert "processed_item3" in results
        assert "processed_item5" in results
        assert errors[0][0] == "fail"
        assert errors[1][0] == "fail"
    
    @pytest.mark.asyncio
    async def test_fallback_strategy(self):
        """Test fallback strategies for failed operations."""
        # Primary operation that fails
        async def primary_operation():
            raise aiohttp.ClientConnectionError("Primary service unavailable")
        
        # Fallback operation
        async def fallback_operation():
            return {"source": "fallback", "data": "cached_data"}
        
        try:
            result = await primary_operation()
        except aiohttp.ClientConnectionError:
            result = await fallback_operation()
        
        assert result["source"] == "fallback"
        assert result["data"] == "cached_data"
    
    def test_error_aggregation(self):
        """Test aggregation of multiple errors."""
        errors = []
        
        # Collect errors from multiple operations
        operations = [
            ("channel1", ValueError("Invalid channel")),
            ("channel2", aiohttp.ClientConnectionError("Connection failed")),
            ("channel3", None),  # Success
            ("channel4", RateLimitError("Rate limit exceeded")),
        ]
        
        for op_id, error in operations:
            if error:
                errors.append({
                    "operation": op_id,
                    "error": classify_error(error),
                    "message": str(error)
                })
        
        # Aggregate error statistics
        error_stats = {
            "total_errors": len(errors),
            "retryable": sum(1 for e in errors if e["error"]["retryable"]),
            "by_type": {}
        }
        
        for error in errors:
            error_type = error["error"]["type"]
            error_stats["by_type"][error_type] = error_stats["by_type"].get(error_type, 0) + 1
        
        assert error_stats["total_errors"] == 3
        assert error_stats["retryable"] == 2  # connection_error and rate_limit
        assert error_stats["by_type"]["unknown"] == 1  # ValueError
        assert error_stats["by_type"]["connection_error"] == 1
        assert error_stats["by_type"]["rate_limit"] == 1


class TestCustomExceptions:
    """Test custom exception handling."""
    
    def test_youtube_api_error(self):
        """Test YouTubeAPIError creation and properties."""
        error = YouTubeAPIError(
            message="Channel not found",
            status_code=404,
            error_code="channelNotFound",
            retry_after=None
        )
        
        assert str(error) == "Channel not found"
        assert error.status_code == 404
        assert error.error_code == "channelNotFound"
        assert error.retry_after is None
        assert not error.is_retryable()
    
    def test_rate_limit_error(self):
        """Test RateLimitError with retry_after."""
        error = RateLimitError(
            message="Rate limit exceeded",
            retry_after=60
        )
        
        assert error.retry_after == 60
        assert error.is_retryable()
    
    def test_transcript_api_error(self):
        """Test TranscriptAPIError."""
        error = TranscriptAPIError(
            message="No transcript available",
            video_id="ABC123",
            language="en"
        )
        
        assert "No transcript available" in str(error)
        assert error.video_id == "ABC123"
        assert error.language == "en"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])