"""Unit tests for rate limiter - Critical for API quota management."""

import asyncio
import time
from unittest.mock import patch
import pytest

from src.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """Test rate limiting functionality - CRITICAL for preventing API quota violations."""
    
    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test that rate limiter enforces the specified rate."""
        # 10 requests per second
        limiter = RateLimiter(rate=10, per=1.0)
        
        start_time = time.time()
        
        # Try to make 15 requests
        for i in range(15):
            await limiter.acquire()
        
        elapsed = time.time() - start_time
        
        # Should take at least 0.5 seconds for the extra 5 requests
        assert elapsed >= 0.4  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_burst_allowance(self):
        """Test that burst allowance works correctly."""
        # 5 requests per second with burst of 10
        limiter = RateLimiter(rate=5, per=1.0, burst=10)
        
        # Should be able to make 10 requests immediately
        start_time = time.time()
        for i in range(10):
            await limiter.acquire()
        elapsed = time.time() - start_time
        
        # Should be nearly instant
        assert elapsed < 0.1
        
        # 11th request should be delayed
        start_time = time.time()
        await limiter.acquire()
        elapsed = time.time() - start_time
        
        # Should have some delay
        assert elapsed >= 0.1
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test rate limiter with concurrent requests."""
        limiter = RateLimiter(rate=10, per=1.0)
        
        async def make_request(request_id: int):
            await limiter.acquire()
            return request_id
        
        # Create 20 concurrent requests
        start_time = time.time()
        tasks = [make_request(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        # Should take at least 1 second for 20 requests at 10/sec
        assert elapsed >= 0.9
        assert len(results) == 20
        assert len(set(results)) == 20  # All unique
    
    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self):
        """Test that rate limiter resets properly over time."""
        limiter = RateLimiter(rate=5, per=1.0, burst=5)
        
        # Use up the burst
        for i in range(5):
            await limiter.acquire()
        
        # Wait for allowance to refill
        await asyncio.sleep(1.0)
        
        # Should be able to make 5 more requests quickly
        start_time = time.time()
        for i in range(5):
            await limiter.acquire()
        elapsed = time.time() - start_time
        
        assert elapsed < 0.2
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization with various parameters."""
        # Valid initialization
        limiter = RateLimiter(rate=100, per=60.0)
        assert limiter.rate == 100
        assert limiter.per == 60.0
        
        # With burst
        limiter = RateLimiter(rate=10, per=1.0, burst=20)
        assert limiter.burst == 20
        
        # Edge cases
        with pytest.raises(ValueError):
            RateLimiter(rate=0, per=1.0)  # Zero rate
        
        with pytest.raises(ValueError):
            RateLimiter(rate=10, per=0)  # Zero period
        
        with pytest.raises(ValueError):
            RateLimiter(rate=-10, per=1.0)  # Negative rate
    
    @pytest.mark.asyncio
    async def test_rate_limiter_with_different_rates(self):
        """Test various rate configurations."""
        test_cases = [
            (60, 60.0),   # 1 per second
            (100, 1.0),   # 100 per second
            (1, 1.0),     # 1 per second
            (3600, 3600.0),  # 1 per second (hourly rate)
        ]
        
        for rate, per in test_cases:
            limiter = RateLimiter(rate=rate, per=per)
            
            # Make 2 requests
            start_time = time.time()
            await limiter.acquire()
            await limiter.acquire()
            elapsed = time.time() - start_time
            
            expected_delay = per / rate
            # Second request should be delayed
            assert elapsed >= expected_delay * 0.8  # Allow 20% tolerance
    
    @pytest.mark.asyncio
    async def test_floating_point_precision(self):
        """Test that floating point arithmetic doesn't cause issues."""
        # This tests the potential bug mentioned in the quality report
        limiter = RateLimiter(rate=3, per=1.0)
        
        # Make many requests to accumulate potential floating point errors
        timings = []
        for i in range(100):
            start = time.time()
            await limiter.acquire()
            timings.append(time.time() - start)
        
        # Check that timing remains consistent (no drift)
        # Average time between requests should be close to 1/3 second
        avg_timing = sum(timings[10:]) / len(timings[10:])  # Skip initial burst
        expected = 1.0 / 3.0
        
        assert abs(avg_timing - expected) < 0.05  # 50ms tolerance
    
    @pytest.mark.asyncio 
    async def test_youtube_api_quota_scenario(self):
        """Test realistic YouTube API quota scenario."""
        # YouTube API has 10,000 quota units per day
        # Search costs 100 units, so 100 searches per day
        # That's approximately 1 search per 864 seconds
        
        limiter = RateLimiter(rate=1, per=864.0)  # 1 per ~14.4 minutes
        
        # First request should be immediate
        start = time.time()
        await limiter.acquire()
        first_elapsed = time.time() - start
        assert first_elapsed < 0.1
        
        # Second request should be delayed significantly
        start = time.time()
        # We won't actually wait 14 minutes, just check it would delay
        task = asyncio.create_task(limiter.acquire())
        await asyncio.sleep(0.1)
        
        # Should still be waiting
        assert not task.done()
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])