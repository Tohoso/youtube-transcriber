"""Batch orchestrator for processing multiple YouTube channels concurrently."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any
import json

import aiohttp
from loguru import logger

from ..cli.display import DisplayManager
from ..models.batch import BatchProcessingResult, ChannelProgress, BatchConfig
from ..models.channel import Channel, ProcessingStatistics
from ..models.config import AppSettings
from ..models.transcript import TranscriptStatus
from ..repositories.youtube_api import YouTubeAPIRepository
from ..repositories.transcript_api import YouTubeTranscriptAPIRepository
from ..repositories.ytdlp_repository import YtDlpRepository
from ..services import ChannelService, TranscriptService, ExportService
from ..services.multi_channel_processor import MultiChannelProcessor
from ..utils.quota_tracker import QuotaTracker
from ..utils.error_handler_enhanced import ErrorAggregator, ErrorHandler
from .orchestrator import TranscriptOrchestrator


class BatchChannelOrchestrator:
    """Orchestrator for processing multiple YouTube channels."""
    
    def __init__(self, settings: AppSettings):
        """Initialize batch orchestrator.
        
        Args:
            settings: Application settings with batch configuration
        """
        self.settings = settings
        self.batch_config = settings.batch if hasattr(settings, 'batch') else self._default_batch_config()
        
        # Display manager
        self.display = DisplayManager()
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Quota and rate limiting (shared across all channels)
        self.quota_tracker = QuotaTracker(daily_limit=settings.api.quota_limit)
        
        # Channel-level concurrency control
        self.channel_semaphore = asyncio.Semaphore(self.batch_config.max_channels)
        
        # Progress tracking
        self.channel_progress: Dict[str, ChannelProgress] = {}
        self.error_aggregator = ErrorAggregator()
        
        # Progress persistence
        self.progress_file = self.batch_config.progress_file
        self._processed_channels: Set[str] = set()
        
    def _default_batch_config(self) -> BatchConfig:
        """Create default batch configuration."""
        from ..models.batch import BatchConfig
        return BatchConfig()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.setup()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
    
    async def setup(self):
        """Set up async resources."""
        # Create shared aiohttp session
        self._session = aiohttp.ClientSession()
        
        # Initialize repositories
        youtube_repo = YouTubeAPIRepository(
            api_key=self.settings.api.youtube_api_key,
            session=self._session,
            quota_limit=self.settings.api.quota_limit
        )
        youtube_repo.quota_tracker = self.quota_tracker  # Share quota tracker
        
        transcript_api_repo = YouTubeTranscriptAPIRepository()
        ytdlp_repo = YtDlpRepository()
        
        # Initialize services
        self.channel_service = ChannelService(youtube_repo=youtube_repo)
        self.transcript_service = TranscriptService(
            transcript_api_repo=transcript_api_repo,
            ytdlp_repo=ytdlp_repo
        )
        self.export_service = ExportService(output_config=self.settings.output)
        
        # Initialize multi-channel processor
        self.multi_channel_processor = MultiChannelProcessor(
            settings=self.settings,
            channel_service=self.channel_service,
            transcript_service=self.transcript_service,
            export_service=self.export_service,
            quota_tracker=self.quota_tracker
        )
        
        # Load previous progress if exists
        if self.batch_config.save_progress:
            await self._load_progress()
    
    async def cleanup(self):
        """Clean up async resources."""
        # Save final progress
        if self.batch_config.save_progress:
            await self._save_progress()
        
        # Close session
        if self._session:
            await self._session.close()
            self._session = None
    
    async def process_channels(
        self,
        channel_inputs: List[str],
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        output_format: str = "txt",
        dry_run: bool = False
    ) -> BatchProcessingResult:
        """Process multiple channels concurrently.
        
        Args:
            channel_inputs: List of channel URLs, IDs, or @handles
            language: Transcript language code
            date_from: Start date filter (YYYY-MM-DD)
            date_to: End date filter (YYYY-MM-DD)
            output_format: Output format for transcripts
            dry_run: Test run without downloading
            
        Returns:
            BatchProcessingResult with summary of all channels
        """
        start_time = datetime.now()
        
        # Initialize progress for all channels
        for channel_input in channel_inputs:
            if channel_input not in self._processed_channels:
                self.channel_progress[channel_input] = ChannelProgress(
                    channel_id=channel_input,
                    status="pending",
                    processed_videos=0,
                    total_videos=0,
                    last_video_id=None
                )
        
        # Display batch processing header
        self.display.show_info(f"Starting batch processing for {len(channel_inputs)} channels")
        
        # Check available quota
        total_operations = await self._estimate_total_operations(channel_inputs)
        if not await self._check_quota_availability(total_operations):
            logger.warning("Insufficient quota for all channels. Processing will stop when quota is exhausted.")
        
        # Use MultiChannelProcessor for actual processing
        if hasattr(self, 'multi_channel_processor'):
            batch_result = await self.multi_channel_processor.process_channels_batch(
                channel_inputs=channel_inputs,
                language=language,
                date_from=date_from,
                date_to=date_to,
                progress_callback=self._update_display_progress
            )
            
            # Update quota usage in result
            batch_result.quota_usage = self.quota_tracker.get_usage_summary()
            
            return batch_result
        else:
            # Fallback to original implementation
            results = await self._process_channels_concurrent(
                channel_inputs=channel_inputs,
                language=language,
                date_from=date_from,
                date_to=date_to,
                output_format=output_format,
                dry_run=dry_run
            )
        
        # Calculate summary
        successful_channels = []
        failed_channels = {}
        partial_channels = {}
        total_videos_processed = 0
        
        for channel_input, result in results.items():
            if isinstance(result, Channel):
                if result.processing_stats:
                    if result.processing_stats.failed_videos == 0:
                        successful_channels.append(channel_input)
                    else:
                        partial_channels[channel_input] = result.processing_stats
                    total_videos_processed += result.processing_stats.processed_videos
            elif isinstance(result, Exception):
                failed_channels[channel_input] = str(result)
        
        # Create batch result
        batch_result = BatchProcessingResult(
            total_channels=len(channel_inputs),
            successful_channels=successful_channels,
            failed_channels=failed_channels,
            partial_channels=partial_channels,
            total_videos_processed=total_videos_processed,
            total_duration=datetime.now() - start_time,
            quota_usage=self.quota_tracker.get_usage_summary(),
            error_summary=self.error_aggregator.get_user_friendly_summary()
        )
        
        # Display final summary
        self._display_batch_summary(batch_result)
        
        # Save batch report
        await self._save_batch_report(batch_result)
        
        return batch_result
    
    async def _process_channels_concurrent(
        self,
        channel_inputs: List[str],
        **kwargs
    ) -> Dict[str, Union[Channel, Exception]]:
        """Process channels concurrently with semaphore control.
        
        Returns:
            Dictionary mapping channel input to result (Channel or Exception)
        """
        results = {}
        
        async def process_single_channel(channel_input: str):
            """Process a single channel with error isolation."""
            async with self.channel_semaphore:
                try:
                    # Update status
                    self.channel_progress[channel_input].status = "processing"
                    
                    # Create individual orchestrator for channel
                    orchestrator = TranscriptOrchestrator(self.settings)
                    orchestrator._session = self._session  # Share session
                    orchestrator.quota_tracker = self.quota_tracker  # Share quota tracker
                    
                    # Process channel
                    channel = await orchestrator.process_channel(
                        channel_input=channel_input,
                        **kwargs
                    )
                    
                    # Update progress
                    self.channel_progress[channel_input].status = "completed"
                    if channel.processing_stats:
                        self.channel_progress[channel_input].processed_videos = channel.processing_stats.processed_videos
                        self.channel_progress[channel_input].total_videos = channel.processing_stats.total_videos
                    
                    self._processed_channels.add(channel_input)
                    results[channel_input] = channel
                    
                    # Save progress periodically
                    if self.batch_config.save_progress:
                        await self._save_progress()
                    
                except Exception as e:
                    logger.error(f"Failed to process channel {channel_input}: {e}")
                    self.channel_progress[channel_input].status = "failed"
                    self.error_aggregator.add_error(channel_input, e)
                    results[channel_input] = e
        
        # Create tasks for all channels
        tasks = []
        for channel_input in channel_inputs:
            if channel_input not in self._processed_channels:
                task = process_single_channel(channel_input)
                tasks.append(task)
            else:
                logger.info(f"Skipping already processed channel: {channel_input}")
        
        # Execute all tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _estimate_total_operations(self, channel_inputs: List[str]) -> int:
        """Estimate total API operations needed.
        
        Args:
            channel_inputs: List of channels to process
            
        Returns:
            Estimated total operations
        """
        # Rough estimate: 1 for channel info + 50 for video list + 1 per video
        # Assuming average 100 videos per channel
        operations_per_channel = 1 + 50 + 100
        return len(channel_inputs) * operations_per_channel
    
    async def _check_quota_availability(self, estimated_operations: int) -> bool:
        """Check if enough quota is available.
        
        Args:
            estimated_operations: Estimated operations needed
            
        Returns:
            True if enough quota available
        """
        remaining = self.quota_tracker.get_remaining_quota()
        
        if remaining < estimated_operations:
            logger.warning(
                f"Estimated operations ({estimated_operations}) exceed "
                f"remaining quota ({remaining})"
            )
            return False
        
        return True
    
    async def _load_progress(self):
        """Load progress from file."""
        if not self.progress_file.exists():
            return
        
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                
            self._processed_channels = set(data.get('processed_channels', []))
            
            # Restore channel progress
            for channel_id, progress_data in data.get('channel_progress', {}).items():
                self.channel_progress[channel_id] = ChannelProgress(**progress_data)
            
            logger.info(f"Loaded progress: {len(self._processed_channels)} channels already processed")
            
        except Exception as e:
            logger.error(f"Failed to load progress: {e}")
    
    async def _save_progress(self):
        """Save progress to file."""
        try:
            data = {
                'processed_channels': list(self._processed_channels),
                'channel_progress': {
                    channel_id: progress.model_dump()
                    for channel_id, progress in self.channel_progress.items()
                },
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    async def _save_batch_report(self, batch_result: BatchProcessingResult):
        """Save detailed batch processing report."""
        report_path = self.settings.output.output_directory / "batch_report.json"
        
        try:
            with open(report_path, 'w') as f:
                json.dump(batch_result.model_dump(), f, indent=2, default=str)
            
            logger.info(f"Batch report saved to: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to save batch report: {e}")
    
    def _display_batch_summary(self, batch_result: BatchProcessingResult):
        """Display batch processing summary."""
        from rich.panel import Panel
        from rich.table import Table
        
        # Summary statistics
        summary_lines = [
            f"[bold]Total Channels:[/bold] {batch_result.total_channels}",
            f"[green]Successful:[/green] {len(batch_result.successful_channels)}",
            f"[yellow]Partial:[/yellow] {len(batch_result.partial_channels)}",
            f"[red]Failed:[/red] {len(batch_result.failed_channels)}",
            "",
            f"[bold]Total Videos Processed:[/bold] {batch_result.total_videos_processed}",
            f"[bold]Total Duration:[/bold] {batch_result.total_duration}",
            "",
            f"[bold]API Quota Used:[/bold] {batch_result.quota_usage.get('percentage', 0):.1f}%"
        ]
        
        summary_panel = Panel(
            "\n".join(summary_lines),
            title="Batch Processing Complete",
            border_style="green" if not batch_result.failed_channels else "yellow"
        )
        
        self.display.console.print(summary_panel)
        
        # Error summary if any
        if batch_result.failed_channels:
            error_table = Table(title="Failed Channels", show_header=True)
            error_table.add_column("Channel", style="red")
            error_table.add_column("Error", style="white")
            
            for channel, error in batch_result.failed_channels.items():
                error_table.add_row(channel, error[:50] + "..." if len(error) > 50 else error)
            
            self.display.console.print(error_table)
    
    async def _update_display_progress(self, progress_info: Dict[str, Any]):
        """Update display with progress information.
        
        Args:
            progress_info: Progress information dictionary
        """
        # Update channel progress display
        if 'channel' in progress_info:
            self.display.show_info(
                f"[{progress_info['channel']}] "
                f"Progress: {progress_info['progress']:.1f}% "
                f"({progress_info['processed']}/{progress_info['total']} videos)"
            )