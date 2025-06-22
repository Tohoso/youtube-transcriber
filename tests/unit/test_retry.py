"""Unit tests for retry functionality - Critical for reliability."""

import asyncio
from unittest.mock import Mock, AsyncMock, patch
import pytest
import aiohttp

from src.utils.retry import retry_with_exponential_backoff


class TestRetryMechanism:
    """Test retry with exponential backoff - CRITICAL for handling transient failures."""
    
    @pytest.mark.asyncio
    async def test_successful_operation_no_retry(self):
        """Test that successful operations don't trigger retries."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_attempts=3)
        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_operation()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retry on transient failures."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_attempts=3, initial_delay=0.01)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientError("Network error")
            return "success"
        
        result = await failing_then_success()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test that retries stop after max attempts."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_attempts=3, initial_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise aiohttp.ClientError("Persistent error")
        
        with pytest.raises(aiohttp.ClientError):
            await always_fails()
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff increases delay correctly."""
        delays = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            delays.append(delay)
            await original_sleep(0.001)  # Minimal actual delay
        
        with patch('asyncio.sleep', mock_sleep):
            @retry_with_exponential_backoff(
                max_attempts=4,
                initial_delay=1.0,
                max_delay=10.0,
                exponential_base=2.0
            )
            async def always_fails():
                raise aiohttp.ClientError("Error")
            
            with pytest.raises(aiohttp.ClientError):
                await always_fails()
        
        # Check exponential progression: 1, 2, 4 (capped at max)
        assert len(delays) == 3  # 3 retries after initial attempt
        assert delays[0] == pytest.approx(1.0, rel=0.1)
        assert delays[1] == pytest.approx(2.0, rel=0.1)
        assert delays[2] == pytest.approx(4.0, rel=0.1)
    
    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delays = []
        
        async def mock_sleep(delay):
            delays.append(delay)
        
        with patch('asyncio.sleep', mock_sleep):
            @retry_with_exponential_backoff(
                max_attempts=5,
                initial_delay=1.0,
                max_delay=5.0,
                exponential_base=3.0
            )
            async def always_fails():
                raise aiohttp.ClientError("Error")
            
            with pytest.raises(aiohttp.ClientError):
                await always_fails()
        
        # Delays should be: 1, 3, 5 (capped), 5 (capped)
        assert delays[-1] <= 5.0
        assert delays[-2] <= 5.0
    
    @pytest.mark.asyncio
    async def test_different_exception_types(self):
        """Test retry behavior with different exception types."""
        # Test that some exceptions are retried
        retryable_exceptions = [
            aiohttp.ClientError("Network error"),
            aiohttp.ServerTimeoutError("Timeout"),
            asyncio.TimeoutError("Operation timed out"),
            ConnectionError("Connection failed"),
        ]
        
        for exception in retryable_exceptions:
            call_count = 0
            
            @retry_with_exponential_backoff(max_attempts=2, initial_delay=0.01)
            async def raises_exception():
                nonlocal call_count
                call_count += 1
                raise exception
            
            with pytest.raises(type(exception)):
                await raises_exception()
            
            assert call_count == 2  # Should retry once
    
    @pytest.mark.asyncio
    async def test_non_retryable_exceptions(self):
        """Test that certain exceptions are not retried."""
        non_retryable_exceptions = [
            ValueError("Invalid input"),
            KeyError("Missing key"),
            AttributeError("Missing attribute"),
        ]
        
        for exception in non_retryable_exceptions:
            call_count = 0
            
            @retry_with_exponential_backoff(max_attempts=3, initial_delay=0.01)
            async def raises_exception():
                nonlocal call_count
                call_count += 1
                raise exception
            
            with pytest.raises(type(exception)):
                await raises_exception()
            
            assert call_count == 1  # Should not retry
    
    @pytest.mark.asyncio
    async def test_retry_with_jitter(self):
        """Test retry with jitter to prevent thundering herd."""
        delays = []
        
        async def mock_sleep(delay):
            delays.append(delay)
        
        with patch('asyncio.sleep', mock_sleep):
            @retry_with_exponential_backoff(
                max_attempts=3,
                initial_delay=1.0,
                jitter=True
            )
            async def always_fails():
                raise aiohttp.ClientError("Error")
            
            with pytest.raises(aiohttp.ClientError):
                await always_fails()
        
        # With jitter, delays should vary
        assert len(delays) == 2
        # Check that delays are not exactly 1.0 and 2.0
        assert delays[0] != 1.0
        assert delays[1] != 2.0
        # But should be in reasonable range
        assert 0.5 <= delays[0] <= 1.5
        assert 1.0 <= delays[1] <= 3.0
    
    @pytest.mark.asyncio
    async def test_retry_with_callback(self):
        """Test retry with callback for logging/monitoring."""
        retry_attempts = []
        
        async def on_retry(exception, attempt):
            retry_attempts.append((str(exception), attempt))
        
        @retry_with_exponential_backoff(
            max_attempts=3,
            initial_delay=0.01,
            on_retry=on_retry
        )
        async def failing_operation():
            raise aiohttp.ClientError("Test error")
        
        with pytest.raises(aiohttp.ClientError):
            await failing_operation()
        
        assert len(retry_attempts) == 2  # 2 retries after initial attempt
        assert retry_attempts[0] == ("Test error", 1)
        assert retry_attempts[1] == ("Test error", 2)
    
    @pytest.mark.asyncio
    async def test_retry_preserves_function_metadata(self):
        """Test that retry decorator preserves function metadata."""
        @retry_with_exponential_backoff(max_attempts=2)
        async def documented_function():
            """This function has documentation."""
            return "result"
        
        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This function has documentation."
    
    @pytest.mark.asyncio
    async def test_concurrent_retries(self):
        """Test multiple concurrent operations with retries."""
        call_counts = {}
        
        @retry_with_exponential_backoff(max_attempts=2, initial_delay=0.01)
        async def operation_with_id(op_id: str):
            if op_id not in call_counts:
                call_counts[op_id] = 0
            call_counts[op_id] += 1
            
            if call_counts[op_id] == 1:
                raise aiohttp.ClientError(f"Error for {op_id}")
            return f"Success for {op_id}"
        
        # Run multiple operations concurrently
        tasks = [operation_with_id(f"op_{i}") for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all("Success" in r for r in results)
        assert all(count == 2 for count in call_counts.values())


class TestAPISpecificRetryScenarios:
    """Test retry scenarios specific to YouTube API and transcript services."""
    
    @pytest.mark.asyncio
    async def test_youtube_api_quota_exceeded(self):
        """Test handling of YouTube API quota exceeded errors."""
        @retry_with_exponential_backoff(max_attempts=3, initial_delay=0.01)
        async def youtube_api_call():
            # Simulate quota exceeded error
            error_response = Mock()
            error_response.status = 403
            error_response.reason = "quotaExceeded"
            raise aiohttp.ClientResponseError(
                request_info=Mock(),
                history=(),
                status=403,
                message="Quota exceeded",
                headers={}
            )
        
        with pytest.raises(aiohttp.ClientResponseError) as exc_info:
            await youtube_api_call()
        
        # Should not retry on quota errors (403)
        assert exc_info.value.status == 403
    
    @pytest.mark.asyncio
    async def test_transcript_service_temporary_failure(self):
        """Test retry on transcript service temporary failures."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_attempts=3, initial_delay=0.01)
        async def get_transcript():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt: service unavailable
                raise aiohttp.ServerError("Service temporarily unavailable")
            return {"text": "Transcript content"}
        
        result = await get_transcript()
        assert result["text"] == "Transcript content"
        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])