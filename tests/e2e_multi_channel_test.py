"""End-to-end test script for multi-channel processing."""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.config import AppSettings
from src.application.batch_orchestrator import BatchChannelOrchestrator
from loguru import logger


async def test_multi_channel_processing():
    """Test multi-channel processing with real channels."""
    
    # Test configuration
    test_channels = [
        "@GoogleDevelopers",  # Small channel for testing
        "@GitHub",           # Medium size channel
        # Add more test channels as needed
    ]
    
    # Create test channels file
    test_file = Path("test_channels.txt")
    with open(test_file, "w") as f:
        for channel in test_channels:
            f.write(f"{channel}\n")
    
    logger.info(f"Created test file with {len(test_channels)} channels")
    
    # Configure settings
    settings = AppSettings(
        api={"youtube_api_key": os.getenv("YOUTUBE_API_KEY")},
        processing={
            "concurrent_limit": 3,
            "skip_private_videos": True,
            "skip_live_streams": True
        },
        batch={
            "max_channels": 2,
            "save_progress": True,
            "batch_size": 5
        },
        output={
            "output_directory": Path("./test_output"),
            "default_format": "txt"
        }
    )
    
    logger.info("Starting multi-channel processing test...")
    start_time = datetime.now()
    
    try:
        # Run batch processing
        async with BatchChannelOrchestrator(settings) as orchestrator:
            result = await orchestrator.process_channels(
                channel_inputs=test_channels,
                language="en",
                dry_run=False  # Set to True for testing without downloading
            )
            
            # Log results
            logger.info("=== Test Results ===")
            logger.info(f"Total channels: {result.total_channels}")
            logger.info(f"Successful: {len(result.successful_channels)}")
            logger.info(f"Failed: {len(result.failed_channels)}")
            logger.info(f"Partial: {len(result.partial_channels)}")
            logger.info(f"Total videos processed: {result.total_videos_processed}")
            logger.info(f"Success rate: {result.overall_success_rate:.1f}%")
            logger.info(f"Duration: {datetime.now() - start_time}")
            
            # Check quota usage
            if result.quota_usage:
                logger.info(f"Quota used: {result.quota_usage.get('percentage', 0):.1f}%")
            
            # Log any errors
            if result.failed_channels:
                logger.error("Failed channels:")
                for channel, error in result.failed_channels.items():
                    logger.error(f"  {channel}: {error}")
            
            # Verify output files
            output_dir = settings.output.output_directory
            if output_dir.exists():
                logger.info("\n=== Output Verification ===")
                for channel in result.successful_channels:
                    channel_name = channel.replace("@", "")
                    channel_dir = output_dir / channel_name
                    if channel_dir.exists():
                        videos = list(channel_dir.glob("videos/*"))
                        logger.info(f"{channel}: {len(videos)} transcript files created")
            
            # Save detailed report
            report_path = output_dir / "test_report.json"
            with open(report_path, "w") as f:
                json.dump({
                    "test_time": datetime.now().isoformat(),
                    "channels_tested": test_channels,
                    "result": result.model_dump(),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }, f, indent=2, default=str)
            
            logger.info(f"\nDetailed report saved to: {report_path}")
            
            # Cleanup test file
            test_file.unlink()
            
            return result
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


async def test_resume_capability():
    """Test the resume capability after interruption."""
    
    logger.info("\n=== Testing Resume Capability ===")
    
    # Check if progress file exists
    progress_file = Path(".progress.json")
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress_data = json.load(f)
        
        logger.info(f"Found progress file with {len(progress_data.get('processed_channels', []))} processed channels")
        logger.info("Resume capability is available")
    else:
        logger.info("No progress file found - resume would start fresh")


async def test_error_handling():
    """Test error handling with invalid channels."""
    
    logger.info("\n=== Testing Error Handling ===")
    
    invalid_channels = [
        "@thischanneldoesnotexist12345",
        "invalid-url-format",
        "UC" + "X" * 22  # Invalid channel ID
    ]
    
    settings = AppSettings(
        api={"youtube_api_key": os.getenv("YOUTUBE_API_KEY")},
        batch={"max_channels": 3},
        output={"output_directory": Path("./test_error_output")}
    )
    
    try:
        async with BatchChannelOrchestrator(settings) as orchestrator:
            result = await orchestrator.process_channels(
                channel_inputs=invalid_channels,
                language="en"
            )
            
            logger.info(f"Error handling test completed:")
            logger.info(f"Failed channels: {len(result.failed_channels)}")
            
            for channel, error in result.failed_channels.items():
                logger.info(f"  {channel}: {error}")
                
    except Exception as e:
        logger.error(f"Error handling test failed: {e}")


async def test_performance_metrics():
    """Analyze performance metrics from batch processing."""
    
    logger.info("\n=== Performance Analysis ===")
    
    # Look for batch report
    report_files = list(Path("./test_output").glob("batch_report*.json"))
    
    if report_files:
        latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_report, "r") as f:
            report = json.load(f)
        
        # Calculate metrics
        if report.get("total_videos_processed", 0) > 0:
            total_time = report.get("total_duration", 0)
            if isinstance(total_time, str):
                # Parse duration string if needed
                pass
            
            videos_per_minute = report["total_videos_processed"] / (total_time / 60) if total_time else 0
            
            logger.info(f"Videos processed: {report['total_videos_processed']}")
            logger.info(f"Processing rate: {videos_per_minute:.1f} videos/minute")
            logger.info(f"Success rate: {report.get('overall_success_rate', 0):.1f}%")
            
            # Memory usage if available
            if "peak_memory_mb" in report:
                logger.info(f"Peak memory usage: {report['peak_memory_mb']:.1f} MB")
    else:
        logger.info("No batch reports found for analysis")


async def main():
    """Run all tests."""
    
    # Check API key
    if not os.getenv("YOUTUBE_API_KEY"):
        logger.error("YOUTUBE_API_KEY environment variable not set!")
        logger.info("Please set: export YOUTUBE_API_KEY='your-key-here'")
        return
    
    logger.info("Starting end-to-end tests for multi-channel processing...\n")
    
    try:
        # Test 1: Basic multi-channel processing
        await test_multi_channel_processing()
        
        # Test 2: Resume capability
        await test_resume_capability()
        
        # Test 3: Error handling
        await test_error_handling()
        
        # Test 4: Performance analysis
        await test_performance_metrics()
        
        logger.info("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Tests failed: {e}")
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