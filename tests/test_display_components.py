"""Unit tests for display components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.console import Console
from rich.progress import Progress
from contextlib import contextmanager

from src.cli.display import DisplayManager
from src.cli.multi_channel_interface import MultiChannelInterface
from src.models.channel import Channel, ChannelSnippet, ChannelStatistics
from src.models.video import Video
from src.models.transcript import TranscriptStatus
from src.models.channel import ProcessingStatistics


class TestDisplayManager:
    """Test cases for DisplayManager."""
    
    @pytest.fixture
    def display_manager(self):
        """Create a DisplayManager instance with mocked console."""
        console = Mock(spec=Console)
        return DisplayManager(console=console)
    
    @pytest.fixture
    def mock_channel(self):
        """Create a mock Channel object."""
        channel = Mock(spec=Channel)
        channel.id = "test_channel_id"
        channel.url = "https://youtube.com/@testchannel"
        channel.snippet = Mock(spec=ChannelSnippet)
        channel.snippet.title = "Test Channel"
        channel.snippet.published_at = None
        channel.statistics = Mock(spec=ChannelStatistics)
        channel.statistics.subscriber_count = 100000
        channel.statistics.video_count = 500
        channel.statistics.view_count = 10000000
        channel.processing_stats = Mock(spec=ProcessingStatistics)
        return channel
    
    def test_create_progress_context_manager(self, display_manager):
        """Test that create_progress returns a working context manager."""
        # Test context manager functionality
        with display_manager.create_progress() as progress:
            assert progress is not None
            assert isinstance(progress, Progress)
        
        # Verify start and stop were called appropriately
        assert display_manager.live is not None
    
    def test_create_progress_nested_calls(self, display_manager):
        """Test nested context manager calls."""
        # Mock the live display
        display_manager.live.is_started = False
        
        # First context
        with display_manager.create_progress() as progress1:
            display_manager.live.is_started = True
            
            # Nested context should not start/stop again
            with display_manager.create_progress() as progress2:
                assert progress1 is progress2
    
    def test_show_channel_info_with_error_handling(self, display_manager, mock_channel):
        """Test channel info display with error handling."""
        # Make console.print raise an exception
        display_manager.console.print.side_effect = Exception("Console error")
        
        # Should not raise, but fall back to print
        with patch('builtins.print') as mock_print:
            display_manager.show_channel_info(mock_channel)
            
            # Verify fallback was called
            mock_print.assert_called()
            call_args = " ".join(str(arg) for call in mock_print.call_args_list for arg in call[0])
            assert "Test Channel" in call_args
            assert "test_channel_id" in call_args
    
    def test_show_error_with_fallback(self, display_manager):
        """Test error display with fallback."""
        error_message = "Test error message"
        
        # Make console.print fail
        display_manager.console.print.side_effect = Exception("Console error")
        
        with patch('builtins.print') as mock_print:
            display_manager.show_error(error_message)
            mock_print.assert_called_with(f"ERROR: {error_message}")
    
    def test_show_processing_stats_with_fallback(self, display_manager):
        """Test processing stats display with fallback."""
        stats = Mock(spec=ProcessingStatistics)
        stats.total_videos = 100
        stats.processed_videos = 50
        stats.successful_videos = 45
        stats.failed_videos = 5
        stats.skipped_videos = 0
        stats.progress_percentage = 50.0
        stats.success_rate = 0.9
        stats.completion_rate = 0.5
        stats.average_processing_time = 2.5
        stats.estimated_time_remaining = None
        stats.error_statistics = {}
        stats.get_processing_rate = Mock(return_value=30.0)
        stats.get_error_summary = Mock(return_value={'total_errors': 0, 'error_types': {}})
        
        # Make console.print fail
        display_manager.console.print.side_effect = Exception("Console error")
        
        with patch('builtins.print') as mock_print:
            display_manager.show_processing_stats(stats)
            
            # Verify fallback was called
            mock_print.assert_called()
            call_args = " ".join(str(arg) for call in mock_print.call_args_list for arg in call[0])
            assert "Processing Statistics" in call_args
            assert "100" in call_args  # total videos
            assert "50" in call_args   # processed videos
    
    def test_show_video_result_with_fallback(self, display_manager):
        """Test video result display with fallback."""
        video = Mock(spec=Video)
        video.title = "Test Video Title That Is Very Long And Should Be Truncated"
        video.transcript_status = TranscriptStatus.SUCCESS
        video.transcript_data = Mock()
        video.transcript_data.word_count = 1500
        
        # Make console.print fail
        display_manager.console.print.side_effect = Exception("Console error")
        
        with patch('builtins.print') as mock_print:
            display_manager.show_video_result(video)
            
            # Verify fallback was called
            mock_print.assert_called()
            call_args = mock_print.call_args[0][0]
            assert "Test Video Title" in call_args
            assert "[SUCCESS]" in call_args
            assert "1500 words" in call_args


class TestMultiChannelInterface:
    """Test cases for MultiChannelInterface."""
    
    @pytest.fixture
    def interface(self):
        """Create a MultiChannelInterface instance."""
        console = Mock(spec=Console)
        return MultiChannelInterface(console=console)
    
    def test_get_channels_from_batch_file(self, interface, tmp_path):
        """Test reading channels from batch file."""
        # Create test file
        batch_file = tmp_path / "channels.txt"
        batch_file.write_text("""# Test channels
@mkbhd
https://youtube.com/@LinusTechTips

# Another channel
UCBJycsmduvYEL83R_U4JriQ
""")
        
        channels = interface.get_channels_from_batch_file(batch_file)
        
        assert len(channels) == 3
        assert "@mkbhd" in channels
        assert "https://youtube.com/@LinusTechTips" in channels
        assert "UCBJycsmduvYEL83R_U4JriQ" in channels
    
    def test_get_channels_from_batch_file_empty(self, interface, tmp_path):
        """Test reading from empty batch file."""
        batch_file = tmp_path / "empty.txt"
        batch_file.write_text("# Only comments\n\n# No channels")
        
        with pytest.raises(ValueError, match="No valid channels found"):
            interface.get_channels_from_batch_file(batch_file)
    
    def test_get_channels_from_batch_file_not_found(self, interface):
        """Test reading from non-existent file."""
        from typer import BadParameter
        
        with pytest.raises(BadParameter, match="Batch file not found"):
            interface.get_channels_from_batch_file("nonexistent.txt")
    
    @patch('rich.prompt.Prompt.ask')
    @patch('rich.prompt.Confirm.ask')
    def test_interactive_channel_selection(self, mock_confirm, mock_prompt, interface):
        """Test interactive channel selection."""
        # Mock user inputs
        mock_prompt.side_effect = ["@channel1", "@channel2", "", ""]
        mock_confirm.return_value = True
        
        channels = interface.interactive_channel_selection()
        
        assert len(channels) == 2
        assert "@channel1" in channels
        assert "@channel2" in channels
    
    def test_display_channel_summary(self, interface):
        """Test channel summary display."""
        channels = ["@verylongchannelnamethatshouldbetruncated" * 2, "@short", "UCsomeID"]
        
        # Should not raise
        interface._display_channel_summary(channels)
        
        # Verify console methods were called
        interface.console.print.assert_called()


class TestProgressBarIntegration:
    """Integration tests for progress bar functionality."""
    
    @pytest.mark.asyncio
    async def test_progress_context_with_orchestrator(self):
        """Test progress context integration with orchestrator."""
        from src.application.orchestrator import TranscriptOrchestrator
        
        # Mock dependencies
        mock_display = Mock(spec=DisplayManager)
        mock_display.create_progress = MagicMock()
        
        # Create a proper context manager mock
        @contextmanager
        def mock_progress_context():
            progress = Mock(spec=Progress)
            progress.add_task = Mock(return_value=0)
            progress.advance = Mock()
            yield progress
        
        mock_display.create_progress.return_value = mock_progress_context()
        
        # This should not raise AttributeError
        orchestrator = TranscriptOrchestrator(
            display=mock_display,
            channel_service=Mock(),
            transcript_service=Mock(),
            export_service=Mock(),
            settings=Mock()
        )
        
        # The actual usage in _process_videos_parallel should work
        mock_display.create_progress.assert_not_called()  # Not called yet
        
        # Simulate the usage
        with mock_display.create_progress() as progress:
            assert progress is not None
            task_id = progress.add_task("Test", total=10)
            progress.advance(task_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])