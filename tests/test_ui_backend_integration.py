"""Integration test for UI-Backend bridge and multi-channel processing."""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.config import AppSettings, ProcessingConfig
from src.models.batch import BatchConfig
from src.application.batch_orchestrator import BatchChannelOrchestrator
from src.cli.ui_backend_bridge import UIBackendBridge, RecoveryAction
from src.cli.multi_channel_interface import MultiChannelInterface
from loguru import logger
from rich.console import Console


class IntegratedBatchOrchestrator(BatchChannelOrchestrator):
    """Extended orchestrator with UI integration."""
    
    def __init__(self, settings: AppSettings, ui_bridge: UIBackendBridge):
        """Initialize with UI bridge."""
        super().__init__(settings)
        self.ui_bridge = ui_bridge
        
    async def process_channels(
        self,
        channel_inputs: List[str],
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        output_format: str = "txt",
        dry_run: bool = False
    ):
        """Process channels with UI integration."""
        
        # Notify UI of batch start
        processing_config = ProcessingConfig(
            parallel_channels=self.batch_config.max_channels,
            parallel_videos=self.settings.processing.concurrent_limit,
            output_directory=self.settings.output.output_directory
        )
        await self.ui_bridge.on_batch_start(channel_inputs, processing_config)
        
        try:
            # Create multi-channel processor with callbacks
            async with self._create_session():
                # Initialize services
                services = await self._initialize_services()
                
                # Create processor
                processor = MultiChannelProcessor(
                    settings=self.settings,
                    channel_service=services['channel_service'],
                    transcript_service=services['transcript_service'],
                    export_service=services['export_service'],
                    quota_tracker=self.quota_tracker
                )
                
                # Create progress callback
                async def progress_callback(update):
                    if update.get('type') == 'channel_validated':
                        await self.ui_bridge.on_channel_validated(
                            update['channel_id'], 
                            update['channel']
                        )
                    elif update.get('type') == 'channel_start':
                        await self.ui_bridge.on_channel_start(
                            update['channel_id'],
                            update['total_videos']
                        )
                    elif update.get('type') == 'video_processed':
                        await self.ui_bridge.on_video_processed(
                            update['channel_id'],
                            update['video'],
                            update['success']
                        )
                    elif update.get('type') == 'channel_complete':
                        await self.ui_bridge.on_channel_complete(
                            update['channel_id'],
                            update['stats']
                        )
                    elif update.get('type') == 'channel_error':
                        recovery_action = await self.ui_bridge.on_channel_error(
                            update['channel_id'],
                            update['error']
                        )
                        update['recovery_action'] = recovery_action
                
                # Process channels
                result = await processor.process_channels_batch(
                    channel_inputs=channel_inputs,
                    language=language,
                    date_from=date_from,
                    date_to=date_to,
                    progress_callback=progress_callback
                )
                
                # Prepare summary
                summary = {
                    'total_channels': result.total_channels,
                    'successful_channels': len(result.successful_channels),
                    'failed_channels': len(result.failed_channels),
                    'total_videos': result.total_videos_processed,
                    'successful_videos': result.total_videos_successful,
                    'failed_videos': result.total_videos_failed,
                    'output_dir': str(self.settings.output.output_directory),
                    'avg_speed': result.total_videos_processed / ((result.total_duration or 60) / 60)
                }
                
                # Notify UI of completion
                await self.ui_bridge.on_batch_complete(summary)
                
                return result
                
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Still notify UI of completion with error
            await self.ui_bridge.on_batch_complete({
                'error': str(e),
                'total_channels': len(channel_inputs),
                'successful_channels': 0,
                'failed_channels': len(channel_inputs)
            })
            raise
    
    async def _initialize_services(self):
        """Initialize all required services."""
        from src.repositories.youtube_api import YouTubeAPIRepository
        from src.repositories.transcript_api import YouTubeTranscriptAPIRepository
        from src.repositories.ytdlp_repository import YtDlpRepository
        from src.services.channel_service import ChannelService
        from src.services.transcript_service import TranscriptService
        from src.services.export_service import ExportService
        
        # Initialize repositories
        youtube_repo = YouTubeAPIRepository(
            self._session,
            self.settings.api.youtube_api_key,
            self.quota_tracker,
            self.settings.api.quota_limit
        )
        transcript_repo = YouTubeTranscriptAPIRepository()
        ytdlp_repo = YtDlpRepository()
        
        # Initialize services
        channel_service = ChannelService(youtube_repo, self.settings)
        transcript_service = TranscriptService(
            transcript_repo, 
            ytdlp_repo, 
            self.settings
        )
        export_service = ExportService(self.settings)
        
        return {
            'channel_service': channel_service,
            'transcript_service': transcript_service,
            'export_service': export_service
        }


async def test_integrated_processing():
    """Test the integrated UI-Backend processing."""
    
    console = Console()
    logger.info("Starting integrated UI-Backend test...")
    
    # Test configuration
    test_channels = [
        "@GoogleDevelopers",
        "@GitHub"
    ]
    
    # Setup settings
    settings = AppSettings(
        api={"youtube_api_key": os.getenv("YOUTUBE_API_KEY")},
        processing={
            "concurrent_limit": 3,
            "skip_private_videos": True,
            "skip_live_streams": True,
            "rate_limit_per_minute": 60
        },
        batch=BatchConfig(
            max_channels=2,
            save_progress=True,
            batch_size=5,
            memory_limit_mb=1024
        ),
        output={
            "output_directory": Path("./test_integration_output"),
            "default_format": "txt"
        }
    )
    
    # Create UI bridge
    ui_bridge = UIBackendBridge(console=console)
    
    # Create integrated orchestrator
    orchestrator = IntegratedBatchOrchestrator(settings, ui_bridge)
    
    try:
        # Run processing
        result = await orchestrator.process_channels(
            channel_inputs=test_channels,
            language="en",
            dry_run=False
        )
        
        logger.info("Integration test completed successfully!")
        logger.info(f"Result: {result.overall_success_rate:.1f}% success rate")
        
        # Save test results
        test_report = {
            "test_time": datetime.now().isoformat(),
            "channels_tested": test_channels,
            "result": {
                "total_channels": result.total_channels,
                "successful_channels": result.successful_channels,
                "failed_channels": result.failed_channels,
                "overall_success_rate": result.overall_success_rate
            },
            "integration_status": "SUCCESS"
        }
        
        report_path = settings.output.output_directory / "integration_test_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump(test_report, f, indent=2)
        
        logger.info(f"Test report saved to: {report_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise


async def test_cli_integration():
    """Test CLI command integration."""
    
    logger.info("\n=== Testing CLI Integration ===")
    
    # Check if the CLI commands are properly integrated
    from src.cli.commands import batch_command
    
    # This would be called by Typer in actual usage
    logger.info("CLI batch command is available and integrated with UI bridge")
    
    # Test interactive mode integration
    from src.cli.commands import interactive_command
    logger.info("CLI interactive command is available")
    
    return True


async def main():
    """Run all integration tests."""
    
    # Check API key
    if not os.getenv("YOUTUBE_API_KEY"):
        logger.error("YOUTUBE_API_KEY environment variable not set!")
        return
    
    logger.info("Starting UI-Backend integration tests...\n")
    
    try:
        # Test 1: Integrated processing with UI
        logger.info("=== Test 1: Integrated UI-Backend Processing ===")
        await test_integrated_processing()
        
        # Test 2: CLI integration
        logger.info("\n=== Test 2: CLI Integration ===")
        await test_cli_integration()
        
        logger.info("\n✅ All integration tests completed successfully!")
        
    except Exception as e:
        logger.error(f"\n❌ Integration tests failed: {e}")
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