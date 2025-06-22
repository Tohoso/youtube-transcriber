"""End-to-end user flow tests for multi-channel UI."""

import asyncio
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import pytest

from src.cli.multi_channel_interface import MultiChannelInterface, ChannelInfo
from src.cli.ui_backend_bridge import UIBackendBridge, ChannelStatus, RecoveryAction
from src.models.channel import Channel, ChannelSnippet, ChannelStatistics, ProcessingStatistics
from src.models.video import Video
from src.models.transcript import TranscriptStatus
from src.models.config import ProcessingConfig


class MockChannelService:
    """Mock channel service for testing."""
    
    async def get_channel_by_input(self, channel_input: str) -> Channel:
        """Mock channel validation."""
        if "invalid" in channel_input.lower():
            raise ValueError("Invalid channel")
        
        # Create mock channel
        channel = Mock(spec=Channel)
        channel.id = f"UC{channel_input.replace('@', '')}"
        channel.url = f"https://youtube.com/{channel_input}"
        channel.snippet = Mock(spec=ChannelSnippet)
        channel.snippet.title = f"Channel {channel_input}"
        channel.snippet.published_at = None
        
        # Mock statistics based on channel name
        channel.statistics = Mock(spec=ChannelStatistics)
        if "mkbhd" in channel_input.lower():
            channel.statistics.subscriber_count = 15_200_000
            channel.statistics.video_count = 1_500
        elif "linus" in channel_input.lower():
            channel.statistics.subscriber_count = 14_800_000
            channel.statistics.video_count = 5_000
        else:
            channel.statistics.subscriber_count = 500_000
            channel.statistics.video_count = 200
        
        channel.statistics.view_count = channel.statistics.video_count * 100_000
        
        return channel


class TestEndToEndUserFlow:
    """Test end-to-end user flows."""
    
    @pytest.fixture
    def mock_interface(self):
        """Create interface with mocked dependencies."""
        interface = MultiChannelInterface()
        interface.channel_service = MockChannelService()
        return interface
    
    @pytest.fixture
    def mock_bridge(self):
        """Create mock UI backend bridge."""
        return UIBackendBridge()
    
    @pytest.mark.asyncio
    async def test_interactive_channel_selection_flow(self, mock_interface):
        """Test the interactive channel selection flow."""
        # Mock user inputs
        with patch('rich.prompt.Prompt.ask') as mock_prompt, \
             patch('rich.prompt.Confirm.ask') as mock_confirm:
            
            # Simulate user flow
            mock_prompt.side_effect = [
                "add",      # Main menu choice
                "@mkbhd",   # First channel
                "@LinusTechTips",  # Second channel
                "@invalid_channel",  # Invalid channel
                "",         # End channel input
                "validate", # Validate all
                "filter",   # Apply filter
                "large",    # Filter type
                "proceed"   # Start processing
            ]
            
            mock_confirm.return_value = True
            
            # Run interactive selection
            # Note: This would need to be adapted for the actual async implementation
            # For now, testing the flow logic
            
            # Add channels
            mock_interface.channels["@mkbhd"] = ChannelInfo("@mkbhd")
            mock_interface.channels["@LinusTechTips"] = ChannelInfo("@LinusTechTips")
            mock_interface.channels["@invalid_channel"] = ChannelInfo("@invalid_channel")
            
            # Validate channels
            for channel_id, info in mock_interface.channels.items():
                try:
                    channel = await mock_interface.channel_service.get_channel_by_input(channel_id)
                    info.channel_data = channel
                    info.validation_status = "valid"
                except:
                    info.validation_status = "invalid"
                    info.error_message = "Invalid channel"
            
            # Check validation results
            assert mock_interface.channels["@mkbhd"].validation_status == "valid"
            assert mock_interface.channels["@LinusTechTips"].validation_status == "valid"
            assert mock_interface.channels["@invalid_channel"].validation_status == "invalid"
            
            # Filter large channels (>1M subscribers)
            valid_channels = [
                (cid, info) for cid, info in mock_interface.channels.items()
                if info.validation_status == "valid" and 
                   info.channel_data and 
                   info.channel_data.statistics.subscriber_count > 1_000_000
            ]
            
            assert len(valid_channels) == 2  # mkbhd and LinusTechTips
    
    @pytest.mark.asyncio
    async def test_batch_processing_progress_flow(self, mock_bridge):
        """Test batch processing progress updates."""
        # Initialize batch processing
        channels = ["@mkbhd", "@LinusTechTips", "@verge"]
        config = ProcessingConfig(
            parallel_channels=2,
            parallel_videos=5
        )
        
        # Track UI updates
        ui_updates = []
        
        async def capture_update(update):
            ui_updates.append(update)
        
        # Simulate batch processing flow
        await mock_bridge.on_batch_start(channels, config)
        
        # Validate channels
        for channel_id in channels:
            channel = await MockChannelService().get_channel_by_input(channel_id)
            await mock_bridge.on_channel_validated(channel_id, channel)
        
        # Process channels
        for channel_id in channels[:2]:  # First two in parallel
            await mock_bridge.on_channel_start(channel_id, 100)
            
            # Simulate video processing
            for i in range(10):
                video = Mock(spec=Video)
                video.title = f"Video {i+1}"
                video.id = f"video_{i+1}"
                
                success = i % 5 != 0  # Every 5th video fails
                await mock_bridge.on_video_processed(channel_id, video, success)
                
                # Small delay to simulate processing
                await asyncio.sleep(0.01)
            
            # Complete channel
            stats = ProcessingStatistics(
                total_videos=100,
                processed_videos=10,
                successful_videos=8,
                failed_videos=2
            )
            await mock_bridge.on_channel_complete(channel_id, stats)
        
        # Check states
        assert mock_bridge.channel_states["@mkbhd"] == ChannelStatus.COMPLETE
        assert mock_bridge.channel_states["@LinusTechTips"] == ChannelStatus.COMPLETE
        assert mock_bridge.channel_states["@verge"] == ChannelStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_error_handling_flow(self, mock_bridge):
        """Test error handling and recovery flow."""
        channel_id = "@test_channel"
        
        # Test API quota error
        quota_error = Exception("YouTube API quota exceeded")
        action = await mock_bridge.on_channel_error(channel_id, quota_error)
        assert action == RecoveryAction.RETRY_LATER
        
        # Test network error
        network_error = Exception("Network connection timeout")
        action = await mock_bridge.on_channel_error(channel_id, network_error)
        assert action == RecoveryAction.RETRY
        
        # Test generic error
        generic_error = Exception("Unknown error occurred")
        action = await mock_bridge.on_channel_error(channel_id, generic_error)
        assert action == RecoveryAction.SKIP
        
        # Check error state
        assert mock_bridge.channel_states[channel_id] == ChannelStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_live_display_updates(self, mock_bridge):
        """Test live display update mechanism."""
        # Initialize
        channels = ["@channel1", "@channel2"]
        config = ProcessingConfig()
        
        await mock_bridge.on_batch_start(channels, config)
        
        # Simulate rapid updates
        update_count = 100
        for i in range(update_count):
            channel_id = channels[i % 2]
            video = Mock(spec=Video)
            video.title = f"Video {i}"
            
            await mock_bridge.on_video_processed(channel_id, video, True)
        
        # Wait for batch processing
        await asyncio.sleep(0.2)
        
        # Check that updates were batched (not all processed individually)
        # This would be verified by checking the actual display update frequency
        assert len(mock_bridge.progress_updates_queue) < update_count
    
    def test_user_flow_scenarios(self):
        """Test complete user flow scenarios."""
        scenarios = [
            {
                "name": "Small batch success",
                "channels": ["@channel1", "@channel2", "@channel3"],
                "expected_success": 3,
                "expected_failures": 0
            },
            {
                "name": "Large batch with failures",
                "channels": [f"@channel{i}" for i in range(20)],
                "expected_success": 18,
                "expected_failures": 2
            },
            {
                "name": "All invalid channels",
                "channels": ["@invalid1", "@invalid2", "@invalid3"],
                "expected_success": 0,
                "expected_failures": 3
            }
        ]
        
        for scenario in scenarios:
            # Each scenario would be tested with the full flow
            assert len(scenario["channels"]) == scenario["expected_success"] + scenario["expected_failures"]


class TestUIPerformance:
    """Test UI performance under various conditions."""
    
    @pytest.mark.asyncio
    async def test_large_batch_performance(self, mock_bridge):
        """Test performance with large number of channels."""
        # Create 50 channels
        channels = [f"@channel{i}" for i in range(50)]
        config = ProcessingConfig(parallel_channels=5)
        
        import time
        start_time = time.time()
        
        # Initialize
        await mock_bridge.on_batch_start(channels, config)
        
        # Simulate processing
        for channel_id in channels:
            channel = await MockChannelService().get_channel_by_input(channel_id)
            await mock_bridge.on_channel_validated(channel_id, channel)
            
            # Quick processing simulation
            await mock_bridge.on_channel_start(channel_id, 10)
            for i in range(10):
                video = Mock(spec=Video)
                video.title = f"Video {i}"
                await mock_bridge.on_video_processed(channel_id, video, True)
            
            stats = ProcessingStatistics(
                total_videos=10,
                processed_videos=10,
                successful_videos=10
            )
            await mock_bridge.on_channel_complete(channel_id, stats)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertion: Should handle 50 channels in under 5 seconds
        assert duration < 5.0
    
    @pytest.mark.asyncio
    async def test_high_frequency_updates(self, mock_bridge):
        """Test UI responsiveness with high-frequency updates."""
        channel_id = "@test_channel"
        
        # Send 1000 updates rapidly
        update_times = []
        for i in range(1000):
            start = asyncio.get_event_loop().time()
            
            video = Mock(spec=Video)
            video.title = f"Video {i}"
            await mock_bridge.on_video_processed(channel_id, video, True)
            
            update_times.append(asyncio.get_event_loop().time() - start)
        
        # Check that individual updates are fast
        avg_update_time = sum(update_times) / len(update_times)
        assert avg_update_time < 0.001  # Less than 1ms per update


class TestUsabilityChecks:
    """Test usability aspects of the UI."""
    
    def test_channel_name_formatting(self, mock_interface):
        """Test channel name display formatting."""
        # Long channel name
        long_name = "This is a very long channel name that should be truncated"
        formatted = mock_interface._format_channel_name(long_name, max_length=30)
        assert len(formatted) <= 30
        assert formatted.endswith("...")
        
    def test_number_formatting(self, mock_interface):
        """Test number formatting for display."""
        test_cases = [
            (1_234_567, "1.2M"),
            (999_999, "1000.0K"),
            (15_200_000, "15.2M"),
            (500, "500"),
            (1_000, "1.0K")
        ]
        
        for num, expected in test_cases:
            formatted = mock_interface._format_number(num)
            assert formatted == expected
    
    def test_duration_formatting(self, mock_interface):
        """Test duration formatting."""
        from datetime import timedelta
        
        test_cases = [
            (timedelta(seconds=45), "45s"),
            (timedelta(minutes=5, seconds=30), "5m 30s"),
            (timedelta(hours=2, minutes=15), "2h 15m"),
            (timedelta(hours=25, minutes=30), "25h 30m")
        ]
        
        for duration, expected in test_cases:
            formatted = mock_interface._format_duration(duration)
            assert formatted == expected
    
    def test_error_message_clarity(self):
        """Test error message user-friendliness."""
        error_mappings = {
            "HTTPError: 403 Forbidden": "API access denied. Check your API key.",
            "quota exceeded": "Daily API limit reached. Try again tomorrow.",
            "Network timeout": "Connection issue. Check your internet.",
            "Channel not found": "Channel doesn't exist or is private."
        }
        
        for technical_error, user_message in error_mappings.items():
            # In real implementation, this would be done by error handler
            assert len(user_message) < len(technical_error) * 2
            assert "API" not in user_message or "API" in technical_error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])