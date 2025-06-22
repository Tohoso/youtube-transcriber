"""Integration tests for edge cases and error handling in multi-channel processing."""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest
import aiohttp
import psutil

from src.application.batch_orchestrator import BatchChannelOrchestrator
from src.models.batch import BatchProcessingResult, ProcessingStatus
from src.models.channel import Channel
from src.models.config import AppSettings, BatchConfig
from src.models.video import Video
from src.exceptions.base import (
    YouTubeAPIError, TranscriptAPIError, NetworkError, 
    RateLimitError, ConfigurationError
)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error scenarios in multi-channel processing."""
    
    @pytest.fixture
    def app_settings(self):
        """Create test settings with edge case configurations."""
        return AppSettings(
            api={"youtube_api_key": "test_key", "quota_limit": 100},
            processing={"concurrent_limit": 5, "retry_attempts": 2},
            batch=BatchConfig(
                max_channels=3,
                save_progress=True,
                error_handling_mode="continue_on_error",
                memory_limit_mb=1024
            )
        )
    
    @pytest.mark.asyncio
    async def test_empty_and_null_inputs(self, app_settings):
        """Test handling of empty, null, and invalid inputs."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        # Test empty channel list
        result = await orchestrator.process_channels([])
        assert result.total_channels == 0
        assert result.successful_channels == 0
        assert result.failed_channels == 0
        
        # Test None values
        with pytest.raises(TypeError):
            await orchestrator.process_channels(None)
        
        # Test list with None/empty values
        invalid_inputs = [None, "", "   ", "@", "https://", "not_a_url"]
        with patch.object(orchestrator, '_process_single_channel') as mock_process:
            mock_process.side_effect = ValueError("Invalid channel")
            result = await orchestrator.process_channels(invalid_inputs)
            
            assert result.failed_channels == len([x for x in invalid_inputs if x])
    
    @pytest.mark.asyncio
    async def test_malformed_channel_inputs(self, app_settings):
        """Test handling of various malformed channel inputs."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        malformed_inputs = [
            "https://youtube.com/",  # No channel
            "youtube.com/@channel",  # Missing protocol
            "https://notyt.com/@channel",  # Wrong domain
            "@channel with spaces",  # Invalid characters
            "UC_!@#$%^&*()",  # Special characters in ID
            "https://youtube.com/watch?v=video",  # Video URL, not channel
            "../../../etc/passwd",  # Path traversal attempt
            "'; DROP TABLE channels; --",  # SQL injection attempt
            "x" * 1000,  # Extremely long input
        ]
        
        results = {}
        
        async def mock_process_with_validation(channel_input, **kwargs):
            # Simulate validation
            if len(channel_input) > 100:
                raise ValueError("Input too long")
            if "../" in channel_input or ";" in channel_input:
                raise ValueError("Invalid characters")
            if not channel_input.startswith(("@", "UC", "https://youtube.com")):
                raise ValueError("Invalid channel format")
            
            return Mock(spec=Channel)
        
        with patch.object(orchestrator, '_process_single_channel', 
                         side_effect=mock_process_with_validation):
            result = await orchestrator.process_channels(malformed_inputs)
            
            # All should fail validation
            assert result.failed_channels == len(malformed_inputs)
    
    @pytest.mark.asyncio
    async def test_network_failure_scenarios(self, app_settings):
        """Test various network failure scenarios."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        network_errors = [
            aiohttp.ClientConnectionError("Connection refused"),
            aiohttp.ServerTimeoutError("Request timeout"),
            aiohttp.ClientOSError("Network unreachable"),
            asyncio.TimeoutError("Operation timed out"),
            aiohttp.ServerDisconnectedError("Server disconnected"),
        ]
        
        error_index = 0
        
        async def mock_process_with_network_errors(channel_input, **kwargs):
            nonlocal error_index
            if error_index < len(network_errors):
                error = network_errors[error_index]
                error_index += 1
                raise error
            return Mock(spec=Channel)
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_network_errors):
            channels = [f"@channel_{i}" for i in range(len(network_errors) + 2)]
            result = await orchestrator.process_channels(channels)
            
            # Network errors should be retried but ultimately fail
            assert result.failed_channels == len(network_errors)
            assert result.successful_channels == 2
    
    @pytest.mark.asyncio
    async def test_api_quota_exhaustion(self, app_settings):
        """Test behavior when API quota is exhausted."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        quota_used = 0
        quota_limit = 100
        
        async def mock_process_with_quota_tracking(channel_input, **kwargs):
            nonlocal quota_used
            # Each channel uses 30 quota units
            quota_needed = 30
            
            if quota_used + quota_needed > quota_limit:
                raise YouTubeAPIError(
                    message="Quota exceeded",
                    status_code=403,
                    error_code="quotaExceeded"
                )
            
            quota_used += quota_needed
            channel = Mock(spec=Channel)
            channel.videos = [Mock() for _ in range(10)]
            return channel
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_quota_tracking):
            # Try to process 5 channels (150 quota needed, but only 100 available)
            channels = [f"@channel_{i}" for i in range(5)]
            result = await orchestrator.process_channels(channels)
            
            # Should process 3 channels before quota exhaustion
            assert result.successful_channels == 3
            assert result.failed_channels == 2
            assert any("quota" in str(error).lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self, app_settings):
        """Test handling of high memory usage scenarios."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        # Simulate memory pressure
        memory_usage = 50.0
        
        async def mock_process_with_memory_simulation(channel_input, **kwargs):
            nonlocal memory_usage
            
            # Simulate memory increase
            memory_usage += 15.0
            
            if memory_usage > 85.0:
                # Simulate OOM-like behavior
                raise MemoryError("Insufficient memory")
            
            # Create channel with many videos to simulate memory usage
            channel = Mock(spec=Channel)
            channel.videos = [Mock() for _ in range(1000)]
            
            # Simulate memory release after processing
            await asyncio.sleep(0.01)
            memory_usage -= 10.0
            
            return channel
        
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value = Mock(percent=memory_usage)
            
            with patch.object(orchestrator, '_process_single_channel',
                             side_effect=mock_process_with_memory_simulation):
                channels = [f"@channel_{i}" for i in range(10)]
                result = await orchestrator.process_channels(channels)
                
                # Some channels should fail due to memory pressure
                assert result.failed_channels > 0
                assert any("memory" in str(error).lower() for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self, app_settings):
        """Test rate limiting with concurrent requests."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        rate_limit_hits = 0
        
        async def mock_process_with_rate_limits(channel_input, **kwargs):
            nonlocal rate_limit_hits
            
            # Simulate rate limiting on every 3rd request
            if rate_limit_hits % 3 == 2:
                raise RateLimitError(
                    message="Rate limit exceeded",
                    retry_after=1
                )
            
            rate_limit_hits += 1
            return Mock(spec=Channel, videos=[])
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_rate_limits):
            channels = [f"@channel_{i}" for i in range(10)]
            
            start_time = asyncio.get_event_loop().time()
            result = await orchestrator.process_channels(channels)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Should handle rate limits with delays
            assert result.total_channels == 10
            assert elapsed > 1.0  # Should have delays due to rate limiting
    
    @pytest.mark.asyncio
    async def test_cascading_failures(self, app_settings):
        """Test handling of cascading failures across channels."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        failure_count = 0
        
        async def mock_process_with_cascading_failures(channel_input, **kwargs):
            nonlocal failure_count
            
            # First few channels succeed
            if failure_count < 2:
                failure_count += 1
                return Mock(spec=Channel, videos=[])
            
            # Then failures cascade
            if failure_count < 5:
                failure_count += 1
                raise aiohttp.ClientConnectionError("Service degradation")
            
            # Service completely fails
            raise aiohttp.ServerError("Service unavailable")
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_cascading_failures):
            channels = [f"@channel_{i}" for i in range(10)]
            result = await orchestrator.process_channels(channels)
            
            # Should gracefully handle cascading failures
            assert result.successful_channels == 2
            assert result.failed_channels == 8
    
    @pytest.mark.asyncio
    async def test_channel_with_extreme_video_counts(self, app_settings):
        """Test channels with extreme numbers of videos."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        extreme_configs = [
            ("empty_channel", 0),
            ("tiny_channel", 1),
            ("huge_channel", 10000),
            ("massive_channel", 50000),
        ]
        
        async def mock_process_extreme_channels(channel_input, **kwargs):
            for name, video_count in extreme_configs:
                if name in channel_input:
                    channel = Mock(spec=Channel)
                    channel.id = channel_input
                    channel.videos = [Mock(id=f"v_{i}") for i in range(video_count)]
                    
                    # Simulate processing time based on size
                    if video_count > 1000:
                        await asyncio.sleep(0.1)
                    
                    return channel
            
            return Mock(spec=Channel, videos=[])
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_extreme_channels):
            channels = [f"@{name}" for name, _ in extreme_configs]
            result = await orchestrator.process_channels(channels)
            
            # All should be processed despite extreme sizes
            assert result.successful_channels == len(extreme_configs)
    
    @pytest.mark.asyncio
    async def test_corrupted_progress_file_recovery(self, app_settings, tmp_path):
        """Test recovery from corrupted progress files."""
        progress_file = tmp_path / "progress.json"
        app_settings.batch.progress_file = str(progress_file)
        
        # Create corrupted progress file
        progress_file.write_text("{ invalid json ][")
        
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        # Should handle corrupted file gracefully
        with patch.object(orchestrator, '_process_single_channel',
                         return_value=Mock(spec=Channel, videos=[])):
            channels = ["@channel1", "@channel2"]
            result = await orchestrator.process_channels(channels)
            
            # Should process all channels despite corrupted progress
            assert result.total_channels == 2
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, app_settings):
        """Test handling of Unicode and special characters in channel data."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        unicode_channels = [
            "@日本語チャンネル",
            "@Канал_Россия",
            "@القناة_العربية",
            "@🎮GamingChannel🎯",
            "@Channel(™)®",
        ]
        
        async def mock_process_unicode(channel_input, **kwargs):
            channel = Mock(spec=Channel)
            channel.id = f"UC_{hash(channel_input)}"
            channel.title = channel_input.replace("@", "")
            channel.videos = [
                Mock(
                    id=f"video_{i}",
                    title=f"動画 {i} - 🎬"
                ) for i in range(5)
            ]
            return channel
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_unicode):
            result = await orchestrator.process_channels(unicode_channels)
            
            # Should handle Unicode correctly
            assert result.successful_channels == len(unicode_channels)
    
    @pytest.mark.asyncio
    async def test_timeout_handling_at_different_stages(self, app_settings):
        """Test timeout handling at various processing stages."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        timeout_stages = {
            "@channel_info_timeout": "channel_info",
            "@video_list_timeout": "video_list",
            "@transcript_timeout": "transcript",
            "@export_timeout": "export",
        }
        
        async def mock_process_with_stage_timeouts(channel_input, **kwargs):
            stage = timeout_stages.get(channel_input)
            
            if stage == "channel_info":
                # Timeout during channel info fetch
                await asyncio.sleep(10)  # Will timeout
            elif stage == "video_list":
                # Timeout during video list fetch
                channel = Mock(spec=Channel)
                channel.id = channel_input
                await asyncio.sleep(10)  # Will timeout
            elif stage == "transcript":
                # Return channel but transcript processing will timeout
                channel = Mock(spec=Channel)
                channel.videos = [Mock() for _ in range(100)]
                # Simulate long transcript processing
                await asyncio.sleep(0.1)
                return channel
            elif stage == "export":
                # Process but export will timeout
                channel = Mock(spec=Channel)
                channel.videos = []
                return channel
            
            return Mock(spec=Channel, videos=[])
        
        # Set aggressive timeout
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            with patch.object(orchestrator, '_process_single_channel',
                             side_effect=mock_process_with_stage_timeouts):
                channels = list(timeout_stages.keys()) + ["@normal_channel"]
                result = await orchestrator.process_channels(channels)
                
                # Timeouts should be handled gracefully
                assert result.failed_channels >= len(timeout_stages)
    
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(self, app_settings):
        """Test detection of circular dependencies or infinite loops."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        processed_channels = set()
        redirect_count = {}
        
        async def mock_process_with_redirects(channel_input, **kwargs):
            # Track redirect chains
            if channel_input not in redirect_count:
                redirect_count[channel_input] = 0
            
            redirect_count[channel_input] += 1
            
            # Detect circular redirects
            if redirect_count[channel_input] > 3:
                raise ValueError("Circular redirect detected")
            
            # Simulate channel redirects
            if channel_input == "@channel_a":
                # Redirect to channel_b
                return await mock_process_with_redirects("@channel_b", **kwargs)
            elif channel_input == "@channel_b":
                # Redirect to channel_c
                return await mock_process_with_redirects("@channel_c", **kwargs)
            elif channel_input == "@channel_c":
                # Redirect back to channel_a (circular)
                return await mock_process_with_redirects("@channel_a", **kwargs)
            
            # Normal channel
            return Mock(spec=Channel, videos=[])
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_redirects):
            channels = ["@channel_a", "@channel_normal"]
            result = await orchestrator.process_channels(channels)
            
            # Should detect and handle circular dependency
            assert result.failed_channels >= 1
            assert any("circular" in str(error).lower() for error in result.errors)


class TestErrorRecoveryStrategies:
    """Test various error recovery strategies."""
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_recovery(self, app_settings):
        """Test exponential backoff in error recovery."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        attempt_times = []
        
        async def mock_process_with_backoff(channel_input, **kwargs):
            attempt_times.append(asyncio.get_event_loop().time())
            
            # Fail first 2 attempts
            if len(attempt_times) < 3:
                raise aiohttp.ServerError("Temporary failure")
            
            return Mock(spec=Channel, videos=[])
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_backoff):
            start_time = asyncio.get_event_loop().time()
            result = await orchestrator.process_channels(["@test_channel"])
            
            # Verify exponential backoff timing
            if len(attempt_times) > 1:
                delays = [attempt_times[i] - attempt_times[i-1] 
                         for i in range(1, len(attempt_times))]
                # Each delay should be roughly double the previous
                for i in range(1, len(delays)):
                    assert delays[i] > delays[i-1] * 1.5
    
    @pytest.mark.asyncio
    async def test_partial_data_recovery(self, app_settings):
        """Test recovery and use of partial data when full processing fails."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        
        async def mock_partial_success(channel_input, **kwargs):
            channel = Mock(spec=Channel)
            channel.id = channel_input
            channel.videos = [Mock(id=f"video_{i}") for i in range(10)]
            
            # Simulate partial transcript success
            channel.processing_stats = Mock()
            channel.processing_stats.total_videos = 10
            channel.processing_stats.successful_videos = 6
            channel.processing_stats.failed_videos = 4
            
            return channel
        
        with patch.object(orchestrator, '_process_single_channel',
                         side_effect=mock_partial_success):
            result = await orchestrator.process_channels(["@partial_channel"])
            
            # Should report as successful with partial data
            assert result.successful_channels == 1
            assert result.partial_success_channels == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])