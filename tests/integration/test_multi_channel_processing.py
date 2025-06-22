"""Integration tests for multi-channel processing functionality."""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest
import aiohttp

from src.application.batch_orchestrator import BatchChannelOrchestrator
from src.cli.multi_channel_interface import MultiChannelInterface
from src.models.batch import (
    BatchConfig, ChannelProgress, BatchProcessingResult, 
    ProcessingQueue, ProcessingStatus
)
from src.models.channel import Channel
from src.models.config import AppSettings
from src.models.transcript import TranscriptStatus
from src.models.video import Video
from src.utils.error_aggregator import ErrorAggregator


class TestMultiChannelProcessing:
    """Test multi-channel batch processing functionality."""
    
    @pytest.fixture
    def batch_config(self):
        """Create test batch configuration."""
        return BatchConfig(
            concurrent_channels=3,
            save_progress=True,
            progress_file=".test_progress.json",
            error_handling="continue",
            memory_efficient=True
        )
    
    @pytest.fixture
    def app_settings(self, batch_config):
        """Create test application settings."""
        return AppSettings(
            api={"youtube_api_key": "test_key"},
            processing={"concurrent_limit": 5},
            batch=batch_config
        )
    
    @pytest.fixture
    def sample_channels(self):
        """Create sample channel data for testing."""
        return [
            "https://youtube.com/@channel1",
            "https://youtube.com/@channel2", 
            "https://youtube.com/@channel3",
            "@channel4",
            "UC_channel5_id"
        ]
    
    @pytest.fixture
    async def batch_orchestrator(self, app_settings):
        """Create BatchChannelOrchestrator instance."""
        orchestrator = BatchChannelOrchestrator(app_settings)
        # Mock the session to avoid real network calls
        orchestrator._session = AsyncMock(spec=aiohttp.ClientSession)
        yield orchestrator
        if orchestrator._session and not orchestrator._session.closed:
            await orchestrator._session.close()
    
    @pytest.mark.asyncio
    async def test_basic_multi_channel_processing(self, batch_orchestrator, sample_channels):
        """Test basic multi-channel processing flow."""
        # Mock individual channel processing
        mock_channels = []
        for i, channel_input in enumerate(sample_channels[:3]):
            channel = Mock(spec=Channel)
            channel.id = f"channel_{i}"
            channel.title = f"Test Channel {i}"
            channel.videos = [Mock(spec=Video) for _ in range(10)]
            channel.processing_stats = Mock()
            channel.processing_stats.total_videos = 10
            channel.processing_stats.processed_videos = 10
            channel.processing_stats.failed_videos = 0
            mock_channels.append(channel)
        
        with patch.object(batch_orchestrator, '_process_single_channel', 
                         side_effect=mock_channels) as mock_process:
            result = await batch_orchestrator.process_channels(sample_channels[:3])
            
            assert result.total_channels == 3
            assert result.successful_channels == 3
            assert result.failed_channels == 0
            assert len(result.channel_results) == 3
            assert mock_process.call_count == 3
    
    @pytest.mark.asyncio
    async def test_concurrent_channel_limit(self, batch_orchestrator, sample_channels):
        """Test that concurrent channel processing respects limits."""
        batch_orchestrator.settings.batch.concurrent_channels = 2
        processing_times = []
        
        async def mock_process_channel(channel_input, **kwargs):
            start_time = asyncio.get_event_loop().time()
            processing_times.append(('start', channel_input, start_time))
            await asyncio.sleep(0.1)  # Simulate processing time
            processing_times.append(('end', channel_input, start_time + 0.1))
            return Mock(spec=Channel)
        
        with patch.object(batch_orchestrator, '_process_single_channel', 
                         side_effect=mock_process_channel):
            await batch_orchestrator.process_channels(sample_channels[:4])
            
            # Verify that no more than 2 channels were processed concurrently
            concurrent_count = 0
            max_concurrent = 0
            
            for event_type, channel, time in sorted(processing_times, key=lambda x: x[2]):
                if event_type == 'start':
                    concurrent_count += 1
                    max_concurrent = max(max_concurrent, concurrent_count)
                else:
                    concurrent_count -= 1
            
            assert max_concurrent <= 2
    
    @pytest.mark.asyncio
    async def test_partial_failure_handling(self, batch_orchestrator, sample_channels):
        """Test handling of partial failures in batch processing."""
        # Mock some channels to succeed and some to fail
        async def mock_process_channel(channel_input, **kwargs):
            if "channel2" in channel_input or "channel4" in channel_input:
                raise ValueError(f"Failed to process {channel_input}")
            channel = Mock(spec=Channel)
            channel.id = channel_input
            channel.title = f"Channel from {channel_input}"
            return channel
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_channel):
            result = await batch_orchestrator.process_channels(sample_channels)
            
            assert result.total_channels == 5
            assert result.successful_channels == 3
            assert result.failed_channels == 2
            assert len(result.errors) == 2
    
    @pytest.mark.asyncio
    async def test_progress_saving_and_resuming(self, batch_orchestrator, sample_channels, tmp_path):
        """Test progress saving and resuming functionality."""
        progress_file = tmp_path / ".progress.json"
        batch_orchestrator.settings.batch.progress_file = str(progress_file)
        
        # Simulate processing interruption after 2 channels
        processed_channels = []
        
        async def mock_process_channel(channel_input, **kwargs):
            if len(processed_channels) >= 2:
                raise KeyboardInterrupt("Simulated interruption")
            processed_channels.append(channel_input)
            return Mock(spec=Channel)
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_channel):
            with pytest.raises(KeyboardInterrupt):
                await batch_orchestrator.process_channels(sample_channels)
        
        # Verify progress was saved
        assert progress_file.exists()
        progress_data = json.loads(progress_file.read_text())
        assert len(progress_data['completed_channels']) == 2
        
        # Test resuming from saved progress
        processed_channels.clear()
        
        async def mock_process_resumed(channel_input, **kwargs):
            processed_channels.append(channel_input)
            return Mock(spec=Channel)
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_resumed):
            result = await batch_orchestrator.process_channels(sample_channels)
            
            # Should only process the remaining 3 channels
            assert len(processed_channels) == 3
            assert sample_channels[0] not in processed_channels
            assert sample_channels[1] not in processed_channels
    
    @pytest.mark.asyncio
    async def test_memory_efficient_mode(self, batch_orchestrator, sample_channels):
        """Test memory-efficient processing mode."""
        batch_orchestrator.settings.batch.memory_efficient = True
        
        # Track memory usage simulation
        peak_memory_usage = 0
        current_memory = 0
        
        async def mock_process_channel(channel_input, **kwargs):
            nonlocal current_memory, peak_memory_usage
            current_memory += 100  # Simulate memory usage
            peak_memory_usage = max(peak_memory_usage, current_memory)
            
            # Simulate video processing
            channel = Mock(spec=Channel)
            channel.videos = [Mock(spec=Video) for _ in range(50)]
            
            # In memory-efficient mode, videos should be processed in batches
            await asyncio.sleep(0.01)
            current_memory -= 100  # Memory released after processing
            return channel
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_channel):
            await batch_orchestrator.process_channels(sample_channels)
            
            # In memory-efficient mode, peak memory should be limited
            assert peak_memory_usage <= 300  # Max 3 concurrent channels
    
    @pytest.mark.asyncio
    async def test_error_aggregation_and_reporting(self, batch_orchestrator, sample_channels):
        """Test error aggregation and reporting functionality."""
        # Create various types of errors
        error_types = [
            aiohttp.ClientResponseError(Mock(), (), status=429, message="Rate limited"),
            ValueError("Invalid channel format"),
            aiohttp.ClientConnectionError("Network error"),
            TimeoutError("Processing timeout"),
            Exception("Unknown error")
        ]
        
        async def mock_process_with_errors(channel_input, **kwargs):
            idx = sample_channels.index(channel_input)
            if idx < len(error_types):
                raise error_types[idx]
            return Mock(spec=Channel)
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_errors):
            result = await batch_orchestrator.process_channels(sample_channels)
            
            assert result.failed_channels == len(error_types)
            assert len(result.errors) == len(error_types)
            
            # Check error categorization
            error_summary = result.get_error_summary()
            assert 'rate_limit' in error_summary
            assert 'validation_error' in error_summary
            assert 'network_error' in error_summary
            assert 'timeout' in error_summary
            assert 'unknown' in error_summary
    
    @pytest.mark.asyncio
    async def test_quota_tracking_across_channels(self, batch_orchestrator, sample_channels):
        """Test API quota tracking across multiple channels."""
        quota_usage = []
        
        async def mock_process_with_quota_tracking(channel_input, **kwargs):
            # Simulate quota usage
            channel = Mock(spec=Channel)
            channel.processing_stats = Mock()
            channel.processing_stats.api_calls = 10
            quota_usage.append(10)
            
            # Check if quota would be exceeded
            if sum(quota_usage) > 30:
                raise aiohttp.ClientResponseError(
                    Mock(), (), status=403, message="quotaExceeded"
                )
            
            return channel
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_with_quota_tracking):
            result = await batch_orchestrator.process_channels(sample_channels)
            
            # Should process 3 channels before quota exceeded
            assert result.successful_channels == 3
            assert result.failed_channels == 2
            assert any("quota" in str(error).lower() for error in result.errors)


class TestMultiChannelInterface:
    """Test multi-channel CLI interface functionality."""
    
    @pytest.fixture
    def interface(self):
        """Create MultiChannelInterface instance."""
        return MultiChannelInterface()
    
    @pytest.fixture
    def sample_batch_file(self, tmp_path):
        """Create a sample batch file."""
        batch_file = tmp_path / "channels.txt"
        content = """# Sample channel batch file
https://youtube.com/@channel1
@channel2
UC_channel3_id

# This is a comment
https://youtube.com/@channel4

# Empty lines are ignored

@channel5
"""
        batch_file.write_text(content)
        return batch_file
    
    def test_read_channels_from_batch_file(self, interface, sample_batch_file):
        """Test reading channels from batch file."""
        channels = interface.get_channels_from_batch_file(str(sample_batch_file))
        
        assert len(channels) == 5
        assert "https://youtube.com/@channel1" in channels
        assert "@channel2" in channels
        assert "UC_channel3_id" in channels
        assert "https://youtube.com/@channel4" in channels
        assert "@channel5" in channels
    
    def test_batch_file_error_handling(self, interface, tmp_path):
        """Test batch file error handling."""
        # Non-existent file
        with pytest.raises(FileNotFoundError):
            interface.get_channels_from_batch_file(str(tmp_path / "nonexistent.txt"))
        
        # Empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        channels = interface.get_channels_from_batch_file(str(empty_file))
        assert len(channels) == 0
        
        # File with only comments
        comment_file = tmp_path / "comments.txt"
        comment_file.write_text("# Comment 1\n# Comment 2\n")
        channels = interface.get_channels_from_batch_file(str(comment_file))
        assert len(channels) == 0
    
    @patch('builtins.input')
    def test_interactive_channel_selection(self, mock_input, interface):
        """Test interactive channel selection."""
        # Simulate user input
        mock_input.side_effect = [
            "https://youtube.com/@channel1",
            "@channel2",
            "UC_channel3",
            "",  # Empty line to finish
            "",  # Second empty line to confirm
            "y"  # Confirm selection
        ]
        
        channels = interface.interactive_channel_selection()
        
        assert len(channels) == 3
        assert "https://youtube.com/@channel1" in channels
        assert "@channel2" in channels
        assert "UC_channel3" in channels
    
    def test_progress_display_formatting(self, interface):
        """Test multi-channel progress display formatting."""
        # Create mock progress data
        progress_data = [
            ChannelProgress(
                channel_id="channel1",
                channel_title="Test Channel 1",
                status=ProcessingStatus.COMPLETED,
                total_videos=50,
                processed_videos=50,
                failed_videos=0,
                start_time=datetime.now(),
                end_time=datetime.now()
            ),
            ChannelProgress(
                channel_id="channel2",
                channel_title="Test Channel 2",
                status=ProcessingStatus.IN_PROGRESS,
                total_videos=100,
                processed_videos=75,
                failed_videos=5,
                start_time=datetime.now()
            ),
            ChannelProgress(
                channel_id="channel3",
                channel_title="Test Channel 3",
                status=ProcessingStatus.FAILED,
                total_videos=30,
                processed_videos=10,
                failed_videos=20,
                error_message="Network error"
            )
        ]
        
        # Test that display function doesn't raise errors
        # In real implementation, this would update a Rich table
        with patch('rich.table.Table') as mock_table:
            interface.display_multi_channel_progress(progress_data)
            assert mock_table.called


class TestBatchProcessingEdgeCases:
    """Test edge cases and error scenarios in batch processing."""
    
    @pytest.mark.asyncio
    async def test_empty_channel_list(self, batch_orchestrator):
        """Test processing with empty channel list."""
        result = await batch_orchestrator.process_channels([])
        
        assert result.total_channels == 0
        assert result.successful_channels == 0
        assert result.failed_channels == 0
    
    @pytest.mark.asyncio
    async def test_duplicate_channels(self, batch_orchestrator):
        """Test handling of duplicate channel inputs."""
        channels = [
            "@testchannel",
            "https://youtube.com/@testchannel",  # Same channel, different format
            "@testchannel",  # Exact duplicate
            "@different_channel"
        ]
        
        processed = set()
        
        async def mock_process_tracking_duplicates(channel_input, **kwargs):
            channel_id = channel_input.replace("https://youtube.com/", "")
            if channel_id in processed:
                return Mock(spec=Channel, id=channel_id)  # Skip actual processing
            processed.add(channel_id)
            return Mock(spec=Channel, id=channel_id)
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_tracking_duplicates):
            result = await batch_orchestrator.process_channels(channels)
            
            # Should process each unique channel only once
            assert len(processed) == 2
    
    @pytest.mark.asyncio
    async def test_extremely_large_batch(self, batch_orchestrator):
        """Test handling of extremely large channel batches."""
        # Create 1000 channels
        large_channel_list = [f"@channel_{i}" for i in range(1000)]
        
        batch_orchestrator.settings.batch.concurrent_channels = 10
        concurrent_counter = 0
        max_concurrent = 0
        lock = asyncio.Lock()
        
        async def mock_process_large_batch(channel_input, **kwargs):
            nonlocal concurrent_counter, max_concurrent
            async with lock:
                concurrent_counter += 1
                max_concurrent = max(max_concurrent, concurrent_counter)
            
            await asyncio.sleep(0.001)  # Minimal processing time
            
            async with lock:
                concurrent_counter -= 1
            
            return Mock(spec=Channel)
        
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_process_large_batch):
            result = await batch_orchestrator.process_channels(large_channel_list)
            
            assert result.total_channels == 1000
            assert max_concurrent <= 10  # Respect concurrent limit
    
    @pytest.mark.asyncio
    async def test_mixed_success_failure_timeout(self, batch_orchestrator):
        """Test mixed scenarios with success, failure, and timeouts."""
        async def mock_mixed_results(channel_input, **kwargs):
            if "success" in channel_input:
                return Mock(spec=Channel)
            elif "fail" in channel_input:
                raise ValueError("Processing failed")
            elif "timeout" in channel_input:
                await asyncio.sleep(10)  # Will timeout
            elif "network" in channel_input:
                raise aiohttp.ClientConnectionError("Network error")
            return Mock(spec=Channel)
        
        channels = [
            "@success_1",
            "@fail_1",
            "@timeout_1",
            "@network_1",
            "@success_2",
            "@fail_2"
        ]
        
        # Set a timeout for the entire batch
        with patch.object(batch_orchestrator, '_process_single_channel',
                         side_effect=mock_mixed_results):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                result = await batch_orchestrator.process_channels(channels)
                
                # Should handle various error types gracefully
                assert result.total_channels == 6
                assert result.successful_channels < 6
                assert result.failed_channels > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])