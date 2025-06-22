"""YouTube API quota tracking and management."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger


class QuotaTracker:
    """Track and manage YouTube API quota usage."""
    
    # YouTube API quota costs (approximate)
    QUOTA_COSTS = {
        'search': 100,           # Search for videos
        'channels': 1,           # Get channel info
        'videos': 1,             # Get video details
        'video_list': 1,         # List videos (per page)
    }
    
    def __init__(self, daily_limit: int = 10000):
        """Initialize quota tracker.
        
        Args:
            daily_limit: Daily quota limit (default: 10000)
        """
        self.daily_limit = daily_limit
        self.used_quota = 0
        self.reset_time = self._next_reset_time()
        self.operation_history: Dict[str, int] = {}
        self._lock = asyncio.Lock()
    
    def _next_reset_time(self) -> datetime:
        """Calculate next quota reset time (midnight Pacific Time)."""
        now = datetime.utcnow()
        # YouTube uses Pacific Time for quota reset
        # Approximate by using UTC-8
        pacific_now = now - timedelta(hours=8)
        tomorrow = pacific_now.date() + timedelta(days=1)
        reset_time = datetime.combine(tomorrow, datetime.min.time()) + timedelta(hours=8)
        return reset_time
    
    async def check_quota(self, operation: str, cost: Optional[int] = None) -> bool:
        """Check if operation can be performed within quota limits.
        
        Args:
            operation: Type of API operation
            cost: Custom cost (uses predefined if not provided)
            
        Returns:
            True if operation is allowed, False if quota exceeded
        """
        async with self._lock:
            # Check if quota should be reset
            if datetime.utcnow() >= self.reset_time:
                self._reset_quota()
            
            operation_cost = cost or self.QUOTA_COSTS.get(operation, 1)
            
            if self.used_quota + operation_cost > self.daily_limit:
                logger.warning(
                    f"Quota limit would be exceeded. "
                    f"Used: {self.used_quota}, "
                    f"Requested: {operation_cost}, "
                    f"Limit: {self.daily_limit}"
                )
                return False
            
            return True
    
    async def consume_quota(self, operation: str, cost: Optional[int] = None) -> bool:
        """Consume quota for an operation.
        
        Args:
            operation: Type of API operation
            cost: Custom cost (uses predefined if not provided)
            
        Returns:
            True if quota was consumed, False if insufficient quota
        """
        async with self._lock:
            # Check if quota should be reset
            if datetime.utcnow() >= self.reset_time:
                self._reset_quota()
            
            operation_cost = cost or self.QUOTA_COSTS.get(operation, 1)
            
            if self.used_quota + operation_cost > self.daily_limit:
                return False
            
            self.used_quota += operation_cost
            self.operation_history[operation] = self.operation_history.get(operation, 0) + 1
            
            # Log quota usage periodically
            if self.used_quota % 1000 == 0:
                logger.info(f"Quota usage: {self.used_quota}/{self.daily_limit} ({self.get_usage_percentage():.1f}%)")
            
            return True
    
    async def wait_until_available(self, operation: str, cost: Optional[int] = None) -> None:
        """Wait until quota is available for operation.
        
        Args:
            operation: Type of API operation
            cost: Custom cost (uses predefined if not provided)
        """
        operation_cost = cost or self.QUOTA_COSTS.get(operation, 1)
        
        while not await self.check_quota(operation, operation_cost):
            time_until_reset = (self.reset_time - datetime.utcnow()).total_seconds()
            
            if time_until_reset > 0:
                logger.info(f"Quota exceeded. Waiting {time_until_reset/3600:.1f} hours until reset...")
                # Wait in smaller chunks to allow for interruption
                wait_time = min(300, time_until_reset)  # Max 5 minutes at a time
                await asyncio.sleep(wait_time)
            else:
                # Reset time has passed, quota should be reset on next check
                await asyncio.sleep(1)
    
    def _reset_quota(self) -> None:
        """Reset quota counters."""
        logger.info(f"Resetting quota. Previous usage: {self.used_quota}/{self.daily_limit}")
        self.used_quota = 0
        self.operation_history.clear()
        self.reset_time = self._next_reset_time()
    
    def get_remaining_quota(self) -> int:
        """Get remaining quota for the day."""
        return max(0, self.daily_limit - self.used_quota)
    
    def get_usage_percentage(self) -> float:
        """Get quota usage percentage."""
        return (self.used_quota / self.daily_limit) * 100 if self.daily_limit > 0 else 0
    
    def get_time_until_reset(self) -> timedelta:
        """Get time until quota reset."""
        return max(timedelta(0), self.reset_time - datetime.utcnow())
    
    def get_usage_summary(self) -> Dict:
        """Get detailed usage summary."""
        return {
            'used': self.used_quota,
            'limit': self.daily_limit,
            'remaining': self.get_remaining_quota(),
            'percentage': self.get_usage_percentage(),
            'reset_time': self.reset_time.isoformat(),
            'time_until_reset': str(self.get_time_until_reset()),
            'operations': dict(self.operation_history)
        }
    
    def estimate_operations_remaining(self, operation: str) -> int:
        """Estimate how many operations of a type can still be performed.
        
        Args:
            operation: Type of API operation
            
        Returns:
            Estimated number of operations remaining
        """
        operation_cost = self.QUOTA_COSTS.get(operation, 1)
        return self.get_remaining_quota() // operation_cost if operation_cost > 0 else 0


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on error rates."""
    
    def __init__(self, initial_rate: int = 60, min_rate: int = 10, max_rate: int = 100):
        """Initialize adaptive rate limiter.
        
        Args:
            initial_rate: Initial requests per minute
            min_rate: Minimum requests per minute
            max_rate: Maximum requests per minute
        """
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.error_count = 0
        self.success_count = 0
        self.last_adjustment = datetime.utcnow()
        self.adjustment_interval = timedelta(minutes=5)
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.success_count += 1
        self._check_adjustment()
    
    def record_error(self, is_rate_limit: bool = False) -> None:
        """Record a failed request.
        
        Args:
            is_rate_limit: Whether the error was due to rate limiting
        """
        self.error_count += 1
        
        # Immediately reduce rate on rate limit errors
        if is_rate_limit:
            self._reduce_rate(factor=0.5)
        
        self._check_adjustment()
    
    def _check_adjustment(self) -> None:
        """Check if rate should be adjusted."""
        now = datetime.utcnow()
        
        if now - self.last_adjustment < self.adjustment_interval:
            return
        
        total_requests = self.success_count + self.error_count
        if total_requests < 10:  # Need minimum sample size
            return
        
        error_rate = self.error_count / total_requests if total_requests > 0 else 0
        
        if error_rate > 0.1:  # More than 10% errors
            self._reduce_rate(factor=0.8)
        elif error_rate < 0.01 and self.success_count > 50:  # Less than 1% errors
            self._increase_rate(factor=1.1)
        
        # Reset counters
        self.error_count = 0
        self.success_count = 0
        self.last_adjustment = now
    
    def _reduce_rate(self, factor: float) -> None:
        """Reduce the current rate."""
        old_rate = self.current_rate
        self.current_rate = max(self.min_rate, int(self.current_rate * factor))
        if old_rate != self.current_rate:
            logger.info(f"Reduced rate limit from {old_rate} to {self.current_rate} requests/min")
    
    def _increase_rate(self, factor: float) -> None:
        """Increase the current rate."""
        old_rate = self.current_rate
        self.current_rate = min(self.max_rate, int(self.current_rate * factor))
        if old_rate != self.current_rate:
            logger.info(f"Increased rate limit from {old_rate} to {self.current_rate} requests/min")
    
    def get_current_rate(self) -> int:
        """Get the current rate limit."""
        return self.current_rate
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        total = self.success_count + self.error_count
        return {
            'current_rate': self.current_rate,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / total if total > 0 else 0,
            'last_adjustment': self.last_adjustment.isoformat()
        }