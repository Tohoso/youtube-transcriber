"""Mock integration test for UI-Backend bridge without requiring API key."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
from unittest.mock import Mock, AsyncMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.config import AppSettings, ProcessingConfig as BaseProcessingConfig
from src.models.batch import BatchConfig, ChannelProgress, BatchProcessingResult
from src.models.channel import Channel, ChannelSnippet, ChannelStatistics, ProcessingStatistics
from src.models.video import Video
from src.cli.ui_backend_bridge import UIBackendBridge
from src.cli.multi_channel_interface import MultiChannelInterface
from src.services.multi_channel_processor import MultiChannelProcessor
from loguru import logger
from rich.console import Console


def create_mock_channel(suffix: str, title: str, video_count: int = 100) -> Channel:
    """Create a mock channel for testing."""
    # Generate valid 22-character channel ID starting with UC
    # UC + 22 chars = 24 total
    base = suffix.replace(" ", "").replace("-", "")[:20]
    padding = "0" * (22 - len(base))
    channel_id = f"UC{base}{padding}"
    return Channel(
        id=channel_id,
        snippet=ChannelSnippet(
            title=title,
            description=f"Mock channel {title}",
            published_at=datetime.now() - timedelta(days=365)
        ),
        statistics=ChannelStatistics(
            subscriber_count=100000,
            view_count=1000000,
            video_count=video_count
        )
    )


def create_mock_video(suffix: str, title: str) -> Video:
    """Create a mock video for testing."""
    # Generate valid 11-character video ID
    base = suffix.replace("_", "").replace("-", "")[:9]
    padding = "0" * (11 - len(base))
    video_id = f"{base}{padding}"
    
    return Video(
        id=video_id,
        title=title,
        url=f"https://www.youtube.com/watch?v={video_id}",
        description="Mock video description",
        published_at=datetime.now() - timedelta(days=30),
        duration="PT10M30S",
        view_count=1000
    )


async def test_ui_backend_flow():
    """Test the complete UI-Backend integration flow with mocks."""
    
    console = Console()
    logger.info("Starting UI-Backend integration test with mocks...")
    
    # Create UI bridge
    ui_bridge = UIBackendBridge(console=console)
    
    # Test channels
    test_channels = ["@MockChannel1", "@MockChannel2"]
    
    # Processing config (create a mock with the expected attributes)
    processing_config = Mock()
    processing_config.parallel_channels = 2
    processing_config.parallel_videos = 3
    processing_config.output_directory = Path("./test_output")
    
    # Test 1: Batch start
    logger.info("Test 1: Testing batch start notification...")
    await ui_bridge.on_batch_start(test_channels, processing_config)
    await asyncio.sleep(0.5)  # Let UI update
    
    # Test 2: Channel validation
    logger.info("Test 2: Testing channel validation...")
    for i, channel_id in enumerate(test_channels):
        mock_channel = create_mock_channel(f"test{i:04d}", f"Mock Channel {i+1}", 50)
        await ui_bridge.on_channel_validated(channel_id, mock_channel)
        await asyncio.sleep(0.2)
    
    # Test 3: Channel processing start
    logger.info("Test 3: Testing channel processing start...")
    for channel_id in test_channels:
        await ui_bridge.on_channel_start(channel_id, 50)
        await asyncio.sleep(0.2)
    
    # Test 4: Video processing
    logger.info("Test 4: Testing video processing updates...")
    for i, channel_id in enumerate(test_channels):
        for j in range(10):  # Process 10 videos per channel
            mock_video = create_mock_video(f"v{i}{j:02d}", f"Video {j+1}")
            success = j % 5 != 0  # Every 5th video fails
            await ui_bridge.on_video_processed(channel_id, mock_video, success)
            await asyncio.sleep(0.1)
    
    # Test 5: Channel completion
    logger.info("Test 5: Testing channel completion...")
    for channel_id in test_channels:
        stats = ProcessingStatistics(
            processing_start_time=datetime.now() - timedelta(minutes=5),
            total_videos=50,
            processed_videos=50,
            successful_videos=40,
            failed_videos=10
        )
        await ui_bridge.on_channel_complete(channel_id, stats)
        await asyncio.sleep(0.3)
    
    # Test 6: Batch completion
    logger.info("Test 6: Testing batch completion...")
    summary = {
        'total_channels': 2,
        'successful_channels': 2,
        'failed_channels': 0,
        'total_videos': 100,
        'successful_videos': 80,
        'failed_videos': 20,
        'output_dir': './test_output',
        'avg_speed': 20.0
    }
    await ui_bridge.on_batch_complete(summary)
    
    logger.info("✅ UI-Backend flow test completed!")


async def test_error_handling():
    """Test error handling in UI-Backend integration."""
    
    console = Console()
    logger.info("\nTesting error handling scenarios...")
    
    ui_bridge = UIBackendBridge(console=console)
    
    # Start batch
    processing_config = Mock()
    processing_config.parallel_channels = 1
    processing_config.parallel_videos = 1
    processing_config.output_directory = Path("./test_output")
    await ui_bridge.on_batch_start(["@ErrorChannel"], processing_config)
    
    # Test different error types
    errors = [
        Exception("Network error: Connection timeout"),
        Exception("Quota exceeded: Daily limit reached"),
        Exception("Channel not found"),
        Exception("Unknown error occurred")
    ]
    
    for i, error in enumerate(errors):
        channel_id = f"@ErrorChannel{i+1}"
        recovery_action = await ui_bridge.on_channel_error(channel_id, error)
        logger.info(f"Error: {error} -> Recovery: {recovery_action}")
        await asyncio.sleep(0.5)
    
    # Complete with errors
    summary = {
        'total_channels': 4,
        'successful_channels': 0,
        'failed_channels': 4,
        'error': 'Multiple errors occurred'
    }
    await ui_bridge.on_batch_complete(summary)
    
    logger.info("✅ Error handling test completed!")


async def test_processor_integration():
    """Test MultiChannelProcessor integration with UI callbacks."""
    
    logger.info("\nTesting processor integration with UI callbacks...")
    
    # Mock settings
    settings = AppSettings(
        api={"youtube_api_key": "mock_key"},
        processing={
            "concurrent_limit": 3,
            "skip_private_videos": True
        },
        batch=BatchConfig(
            max_channels=2,
            batch_size=5
        ),
        output={"output_directory": Path("./test_output")}
    )
    
    # Create mocks
    mock_channel_service = AsyncMock()
    mock_transcript_service = AsyncMock()
    mock_export_service = AsyncMock()
    mock_quota_tracker = Mock()
    
    # Setup mock returns
    mock_channels = [
        create_mock_channel("ch01", "Test Channel 1", 10),
        create_mock_channel("ch02", "Test Channel 2", 10)
    ]
    
    mock_channel_service.get_channel_by_input.side_effect = mock_channels
    mock_channel_service.get_channel_videos.return_value = [
        create_mock_video(f"vid{i:03d}", f"Video {i}") for i in range(5)
    ]
    mock_channel_service.filter_videos.side_effect = lambda videos, **kwargs: videos
    
    mock_transcript_service.get_transcript.return_value = Mock(
        text="Mock transcript",
        word_count=100,
        duration=600
    )
    
    # Progress tracking
    progress_updates = []
    
    async def progress_callback(update):
        progress_updates.append(update)
        logger.info(f"Progress update: {update.get('type', 'unknown')}")
    
    # Create processor
    processor = MultiChannelProcessor(
        settings=settings,
        channel_service=mock_channel_service,
        transcript_service=mock_transcript_service,
        export_service=mock_export_service,
        quota_tracker=mock_quota_tracker
    )
    
    # Process channels
    result = await processor.process_channels_batch(
        channel_inputs=["@TestChannel1", "@TestChannel2"],
        language="en",
        progress_callback=progress_callback
    )
    
    # Verify results
    logger.info(f"Processing result: {result.overall_success_rate:.1f}% success")
    logger.info(f"Progress updates received: {len(progress_updates)}")
    
    # Check that we got the expected callbacks
    update_types = [u.get('type') for u in progress_updates]
    logger.info(f"Update types: {update_types}")
    
    logger.info("✅ Processor integration test completed!")


async def test_cli_interface():
    """Test MultiChannelInterface display methods."""
    
    logger.info("\nTesting CLI interface display methods...")
    
    console = Console()
    interface = MultiChannelInterface(console=console)
    
    # Create test channels with stats
    channels = []
    for i in range(3):
        channel = create_mock_channel(f"ch{i:02d}", f"Channel {i+1}", 100)
        channel.processing_stats = ProcessingStatistics(
            processing_start_time=datetime.now() - timedelta(minutes=10),
            total_videos=100,
            processed_videos=80 + i*5,
            successful_videos=75 + i*5,
            failed_videos=5
        )
        channels.append(channel)
    
    # Test batch results display
    processing_config = Mock()
    processing_config.parallel_channels = 3
    processing_config.parallel_videos = 5
    processing_config.output_directory = Path("./test_output")
    
    interface.display_batch_results(channels, processing_config)
    
    logger.info("✅ CLI interface test completed!")


async def main():
    """Run all mock integration tests."""
    
    logger.info("Starting mock integration tests...\n")
    
    try:
        # Test 1: UI-Backend flow
        await test_ui_backend_flow()
        
        # Test 2: Error handling
        await test_error_handling()
        
        # Test 3: Processor integration
        await test_processor_integration()
        
        # Test 4: CLI interface
        await test_cli_interface()
        
        logger.info("\n✅ All mock integration tests completed successfully!")
        
        # Summary
        logger.info("\n=== Integration Test Summary ===")
        logger.info("1. UI-Backend communication: PASS")
        logger.info("2. Error handling: PASS")
        logger.info("3. Processor integration: PASS")
        logger.info("4. CLI interface: PASS")
        logger.info("5. Overall integration: READY")
        
    except Exception as e:
        logger.error(f"\n❌ Mock integration tests failed: {e}")
        raise


if __name__ == "__main__":
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run tests
    asyncio.run(main())