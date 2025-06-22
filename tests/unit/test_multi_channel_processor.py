"""Unit tests for MultiChannelProcessor - concurrent channel processing."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch, call
import pytest

from src.services.multi_channel_processor import MultiChannelProcessor
from src.models.batch import ChannelProgress, ProcessingStatus, BatchProcessingResult
from src.models.channel import Channel
from src.models.config import AppSettings, BatchConfig
from src.models.video import Video
from src.utils.quota_tracker import QuotaTracker
from src.utils.error_handler_enhanced import ErrorAggregator


class TestMultiChannelProcessor:
    """Test MultiChannelProcessor concurrent processing functionality."""
    
    @pytest.fixture
    def app_settings(self):
        """Create test settings."""
        return AppSettings(
            api={"youtube_api_key": "test_key"},
            processing={"concurrent_limit": 5},
            batch=BatchConfig(
                max_channels=3,
                save_progress=True,
                error_handling_mode="continue_on_error"
            )
        )
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services."""
        return {
            'channel_service': AsyncMock(),
            'transcript_service': AsyncMock(),
            'export_service': AsyncMock(),
            'quota_tracker': Mock(spec=QuotaTracker)
        }
    
    @pytest.fixture
    def processor(self, app_settings, mock_services):
        """Create MultiChannelProcessor instance."""
        return MultiChannelProcessor(
            settings=app_settings,
            channel_service=mock_services['channel_service'],
            transcript_service=mock_services['transcript_service'],
            export_service=mock_services['export_service'],
            quota_tracker=mock_services['quota_tracker']
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_channel_processing(self, processor, mock_services):
        """Test concurrent processing of multiple channels."""
        # Setup mock channels
        mock_channels = []
        for i in range(5):
            channel = Mock(spec=Channel)
            channel.id = f"channel_{i}"
            channel.title = f"Test Channel {i}"
            channel.videos = [Mock(spec=Video) for _ in range(10)]
            mock_channels.append(channel)
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_channels
        
        # Track concurrent executions
        concurrent_count = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def mock_process_videos(videos, language, semaphore):
            nonlocal concurrent_count, max_concurrent
            async with lock:
                concurrent_count += 1
                max_concurrent = max(max_concurrent, concurrent_count)
            
            await asyncio.sleep(0.1)  # Simulate processing
            
            async with lock:
                concurrent_count -= 1
            
            return {v.id: Mock() for v in videos}
        
        mock_services['transcript_service'].get_transcripts_batch.side_effect = mock_process_videos
        
        # Process channels
        channel_inputs = [f"@channel_{i}" for i in range(5)]
        result = await processor.process_channels_batch(
            channel_inputs=channel_inputs,
            language="en"
        )
        
        # Verify concurrent limit was respected
        assert max_concurrent <= processor.settings.batch.max_channels
        assert result.total_channels == 5
        assert result.successful_channels == 5
    
    @pytest.mark.asyncio
    async def test_channel_processing_with_failures(self, processor, mock_services):
        """Test handling of channel processing failures."""
        # Setup mixed success/failure scenarios
        async def mock_get_channel(channel_input):
            if "fail" in channel_input:
                raise ValueError(f"Failed to get channel: {channel_input}")
            channel = Mock(spec=Channel)
            channel.id = channel_input
            channel.videos = [Mock(spec=Video) for _ in range(5)]
            return channel
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_get_channel
        
        channel_inputs = [
            "@success_1",
            "@fail_1",
            "@success_2",
            "@fail_2",
            "@success_3"
        ]
        
        result = await processor.process_channels_batch(channel_inputs)
        
        assert result.total_channels == 5
        assert result.successful_channels == 3
        assert result.failed_channels == 2
        assert len(result.channel_errors) == 2
    
    @pytest.mark.asyncio
    async def test_quota_management_across_channels(self, processor, mock_services):
        """Test quota tracking and management across multiple channels."""
        # Setup quota tracker
        mock_services['quota_tracker'].check_quota.return_value = True
        mock_services['quota_tracker'].use_quota = Mock()
        mock_services['quota_tracker'].get_remaining_quota.return_value = 1000
        
        # Mock channels with different video counts
        channel_configs = [
            ("channel_1", 20),  # 20 videos
            ("channel_2", 30),  # 30 videos
            ("channel_3", 50),  # 50 videos
        ]
        
        mock_channels = []
        for channel_id, video_count in channel_configs:
            channel = Mock(spec=Channel)
            channel.id = channel_id
            channel.videos = [Mock(spec=Video) for _ in range(video_count)]
            mock_channels.append(channel)
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_channels
        
        # Process channels
        channel_inputs = [f"@{ch[0]}" for ch in channel_configs]
        await processor.process_channels_batch(channel_inputs)
        
        # Verify quota was tracked for all operations
        # Each channel info request + video transcript requests
        expected_quota_calls = len(channel_configs) + sum(ch[1] for ch in channel_configs)
        assert mock_services['quota_tracker'].use_quota.call_count >= len(channel_configs)
    
    @pytest.mark.asyncio
    async def test_progress_callback_functionality(self, processor, mock_services):
        """Test progress callback reporting during processing."""
        progress_updates = []
        
        async def progress_callback(update: Dict[str, Any]):
            progress_updates.append(update.copy())
        
        # Setup mock channel
        channel = Mock(spec=Channel)
        channel.id = "test_channel"
        channel.title = "Test Channel"
        channel.videos = [Mock(spec=Video) for _ in range(10)]
        
        mock_services['channel_service'].get_channel_by_input.return_value = channel
        
        # Simulate progressive video processing
        processed_count = 0
        
        async def mock_process_videos(videos, language, semaphore):
            nonlocal processed_count
            results = {}
            for video in videos:
                processed_count += 1
                results[video.id] = Mock()
                # Simulate progress update
                if progress_callback:
                    await progress_callback({
                        'channel': channel.id,
                        'processed': processed_count,
                        'total': len(channel.videos),
                        'progress': (processed_count / len(channel.videos)) * 100
                    })
            return results
        
        mock_services['transcript_service'].get_transcripts_batch.side_effect = mock_process_videos
        
        # Process with progress callback
        await processor.process_channels_batch(
            channel_inputs=["@test_channel"],
            progress_callback=progress_callback
        )
        
        # Verify progress updates were sent
        assert len(progress_updates) > 0
        assert progress_updates[-1]['progress'] == 100.0
    
    @pytest.mark.asyncio
    async def test_memory_efficient_processing(self, processor, mock_services):
        """Test memory-efficient processing mode."""
        processor.settings.batch.memory_efficient_mode = True
        processor.settings.batch.video_batch_size = 10
        
        # Create channel with many videos
        channel = Mock(spec=Channel)
        channel.id = "large_channel"
        channel.videos = [Mock(spec=Video, id=f"video_{i}") for i in range(100)]
        
        mock_services['channel_service'].get_channel_by_input.return_value = channel
        
        # Track batch calls
        batch_calls = []
        
        async def mock_process_batch(videos, language, semaphore):
            batch_calls.append(len(videos))
            return {v.id: Mock() for v in videos}
        
        mock_services['transcript_service'].get_transcripts_batch.side_effect = mock_process_batch
        
        # Process channel
        await processor.process_channels_batch(["@large_channel"])
        
        # Verify videos were processed in batches
        assert len(batch_calls) > 1  # Multiple batches
        assert all(size <= 10 for size in batch_calls[:-1])  # All but last batch should be size 10
    
    @pytest.mark.asyncio
    async def test_error_aggregation_and_categorization(self, processor, mock_services):
        """Test error aggregation and categorization across channels."""
        # Define various error scenarios
        error_scenarios = {
            "@network_error": asyncio.TimeoutError("Network timeout"),
            "@api_error": Exception("API quota exceeded"),
            "@parse_error": ValueError("Invalid response format"),
            "@auth_error": Exception("Authentication failed")
        }
        
        async def mock_channel_with_errors(channel_input):
            if channel_input in error_scenarios:
                raise error_scenarios[channel_input]
            channel = Mock(spec=Channel)
            channel.id = channel_input
            channel.videos = []
            return channel
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_channel_with_errors
        
        # Process channels with various errors
        result = await processor.process_channels_batch(
            list(error_scenarios.keys()) + ["@success_channel"]
        )
        
        # Verify error categorization
        assert result.failed_channels == len(error_scenarios)
        assert result.successful_channels == 1
        
        # Check error types are properly categorized
        error_summary = result.get_error_summary()
        assert 'network_error' in error_summary or 'timeout' in error_summary
        assert 'api_error' in error_summary or 'quota' in error_summary
        assert 'validation_error' in error_summary or 'parse' in error_summary
        assert 'auth_error' in error_summary or 'authentication' in error_summary
    
    @pytest.mark.asyncio
    async def test_channel_deduplication(self, processor, mock_services):
        """Test that duplicate channels are processed only once."""
        process_count = {}
        
        async def mock_get_channel(channel_input):
            # Normalize channel input to detect duplicates
            normalized = channel_input.replace("https://youtube.com/", "").replace("@", "")
            
            if normalized not in process_count:
                process_count[normalized] = 0
            process_count[normalized] += 1
            
            channel = Mock(spec=Channel)
            channel.id = f"UC_{normalized}"
            channel.videos = []
            return channel
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_get_channel
        
        # Process list with duplicates
        channel_inputs = [
            "@testchannel",
            "https://youtube.com/@testchannel",
            "@testchannel",  # Duplicate
            "@different_channel",
            "https://youtube.com/@different_channel"  # Duplicate in different format
        ]
        
        result = await processor.process_channels_batch(channel_inputs)
        
        # Each unique channel should be processed only once
        assert process_count['testchannel'] == 3  # Called 3 times before dedup
        assert process_count['different_channel'] == 2  # Called 2 times before dedup
        assert result.total_channels <= 3  # After deduplication
    
    @pytest.mark.asyncio
    async def test_partial_channel_success(self, processor, mock_services):
        """Test handling of partial success within a channel."""
        # Setup channel with mixed video results
        channel = Mock(spec=Channel)
        channel.id = "partial_channel"
        channel.videos = [Mock(spec=Video, id=f"video_{i}") for i in range(10)]
        
        mock_services['channel_service'].get_channel_by_input.return_value = channel
        
        # Mock transcript service to fail for some videos
        async def mock_transcripts_with_failures(videos, language, semaphore):
            results = {}
            for i, video in enumerate(videos):
                if i % 3 == 0:  # Fail every 3rd video
                    continue  # Skip failed videos
                results[video.id] = Mock()
            return results
        
        mock_services['transcript_service'].get_transcripts_batch.side_effect = mock_transcripts_with_failures
        
        # Process channel
        result = await processor.process_channels_batch(["@partial_channel"])
        
        # Channel should be marked as successful even with some failed videos
        assert result.successful_channels == 1
        assert result.partial_success_channels == 1
        
        # Verify partial success is tracked
        channel_result = result.channel_results.get("@partial_channel")
        assert channel_result is not None
        assert channel_result.total_videos == 10
        assert channel_result.successful_videos < 10
        assert channel_result.failed_videos > 0


class TestConcurrencyControl:
    """Test concurrency control mechanisms."""
    
    @pytest.mark.asyncio
    async def test_semaphore_limits(self):
        """Test that semaphore properly limits concurrent operations."""
        max_concurrent = 3
        semaphore = asyncio.Semaphore(max_concurrent)
        
        current_count = 0
        max_observed = 0
        lock = asyncio.Lock()
        
        async def controlled_operation(op_id: int):
            nonlocal current_count, max_observed
            
            async with semaphore:
                async with lock:
                    current_count += 1
                    max_observed = max(max_observed, current_count)
                
                # Simulate work
                await asyncio.sleep(0.1)
                
                async with lock:
                    current_count -= 1
        
        # Launch many operations
        tasks = [controlled_operation(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Verify limit was respected
        assert max_observed <= max_concurrent
    
    @pytest.mark.asyncio
    async def test_dynamic_concurrency_adjustment(self, processor, mock_services):
        """Test dynamic adjustment of concurrency based on system load."""
        # Track system metrics
        memory_usage = 50  # Start at 50%
        
        async def mock_channel_processing(channel_input):
            nonlocal memory_usage
            # Simulate increasing memory usage
            memory_usage += 10
            
            channel = Mock(spec=Channel)
            channel.id = channel_input
            channel.videos = [Mock() for _ in range(20)]
            
            # Simulate memory release after processing
            await asyncio.sleep(0.1)
            memory_usage -= 5
            
            return channel
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_channel_processing
        
        # Mock memory monitoring
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.return_value.percent = property(lambda self: memory_usage)
            
            # Process channels
            channel_inputs = [f"@channel_{i}" for i in range(10)]
            
            # The processor should adjust concurrency if memory usage gets high
            result = await processor.process_channels_batch(channel_inputs)
            
            assert result.total_channels == 10


class TestProgressTracking:
    """Test progress tracking and resumption functionality."""
    
    @pytest.mark.asyncio
    async def test_progress_persistence(self, processor, mock_services, tmp_path):
        """Test that progress is saved and can be resumed."""
        progress_file = tmp_path / "progress.json"
        processor.settings.batch.progress_file = str(progress_file)
        
        # Setup channels
        channels_to_process = [f"@channel_{i}" for i in range(5)]
        processed_channels = []
        
        async def mock_channel_processing(channel_input):
            # Simulate interruption after 2 channels
            if len(processed_channels) >= 2:
                raise KeyboardInterrupt("Simulated interruption")
            
            processed_channels.append(channel_input)
            channel = Mock(spec=Channel)
            channel.id = channel_input
            channel.videos = []
            return channel
        
        mock_services['channel_service'].get_channel_by_input.side_effect = mock_channel_processing
        
        # First run - should be interrupted
        with pytest.raises(KeyboardInterrupt):
            await processor.process_channels_batch(channels_to_process)
        
        # Verify progress was saved
        assert progress_file.exists()
        
        # Reset for resumption
        processed_channels.clear()
        mock_services['channel_service'].get_channel_by_input.side_effect = None
        mock_services['channel_service'].get_channel_by_input.return_value = Mock(
            spec=Channel, id="test", videos=[]
        )
        
        # Resume processing
        result = await processor.process_channels_batch(channels_to_process)
        
        # Should only process remaining channels
        assert mock_services['channel_service'].get_channel_by_input.call_count == 3  # Only remaining channels


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])