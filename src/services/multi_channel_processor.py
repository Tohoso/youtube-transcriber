"""Multi-channel processor with advanced queue and resource management."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil not available, memory monitoring disabled")

from ..models.batch import (
    BatchConfig, 
    ChannelProgress, 
    BatchProcessingResult,
    ProcessingQueue
)
from ..models.channel import Channel
from ..models.config import AppSettings
from ..models.video import Video
from ..utils.quota_tracker import QuotaTracker
from ..utils.error_handler_enhanced import ErrorHandler, ErrorAggregator
from .channel_service import ChannelService
from .transcript_service import TranscriptService
from .export_service import ExportService


class MultiChannelProcessor:
    """Advanced multi-channel processor with queue management and resource optimization."""
    
    def __init__(
        self,
        settings: AppSettings,
        channel_service: ChannelService,
        transcript_service: TranscriptService,
        export_service: ExportService,
        quota_tracker: QuotaTracker
    ):
        """Initialize multi-channel processor.
        
        Args:
            settings: Application settings
            channel_service: Channel service instance
            transcript_service: Transcript service instance  
            export_service: Export service instance
            quota_tracker: Shared quota tracker
        """
        self.settings = settings
        self.batch_config = settings.batch if hasattr(settings, 'batch') else BatchConfig()
        
        # Services
        self.channel_service = channel_service
        self.transcript_service = transcript_service
        self.export_service = export_service
        self.quota_tracker = quota_tracker
        
        # Processing state
        self.channel_queues: Dict[str, ProcessingQueue] = {}
        self.channel_progress: Dict[str, ChannelProgress] = {}
        self.error_aggregator = ErrorAggregator()
        
        # Resource management
        self.memory_monitor = MemoryMonitor(self.batch_config.memory_limit_mb)
        self.processing_lock = asyncio.Lock()
        
        # Channel and video level semaphores
        self.channel_semaphore = asyncio.Semaphore(self.batch_config.max_channels)
        self.video_semaphore = asyncio.Semaphore(self.settings.processing.concurrent_limit)
        
        # Batch result
        self.batch_result = BatchProcessingResult(total_channels=0)
    
    async def process_channels_batch(
        self,
        channel_inputs: List[str],
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        progress_callback: Optional[Any] = None
    ) -> BatchProcessingResult:
        """Process multiple channels with advanced queue management.
        
        Args:
            channel_inputs: List of channel identifiers
            language: Transcript language
            date_from: Start date filter
            date_to: End date filter
            progress_callback: Optional progress callback
            
        Returns:
            Batch processing result
        """
        logger.info(f"Starting batch processing for {len(channel_inputs)} channels")
        
        # Initialize batch result
        self.batch_result = BatchProcessingResult(
            total_channels=len(channel_inputs),
            started_at=datetime.now()
        )
        
        # Pre-flight checks
        await self._preflight_checks(channel_inputs)
        
        # Initialize progress for all channels
        for channel_input in channel_inputs:
            self.channel_progress[channel_input] = ChannelProgress(
                channel_id=channel_input,
                status="pending"
            )
        
        # Process channels concurrently
        try:
            await self._process_channels_concurrent(
                channel_inputs=channel_inputs,
                language=language,
                date_from=date_from,
                date_to=date_to,
                progress_callback=progress_callback
            )
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self.error_aggregator.add_error("batch_processing", e)
        
        # Finalize results
        self.batch_result.finalize()
        self.batch_result.error_summary = self.error_aggregator.get_user_friendly_summary()
        self.batch_result.peak_memory_mb = self.memory_monitor.peak_usage_mb
        
        # Log summary
        self._log_batch_summary()
        
        return self.batch_result
    
    async def _preflight_checks(self, channel_inputs: List[str]):
        """Perform pre-flight checks before processing.
        
        Args:
            channel_inputs: List of channels to process
        """
        # Check quota availability
        estimated_quota = len(channel_inputs) * 150  # Rough estimate
        remaining_quota = self.quota_tracker.get_remaining_quota()
        
        if remaining_quota < estimated_quota:
            logger.warning(
                f"Estimated quota usage ({estimated_quota}) may exceed "
                f"remaining quota ({remaining_quota}). Processing may be interrupted."
            )
        
        # Check memory if psutil available
        if HAS_PSUTIL:
            available_memory = psutil.virtual_memory().available / (1024 * 1024)  # MB
            if available_memory < self.batch_config.memory_limit_mb:
                logger.warning(
                    f"Available memory ({available_memory:.0f}MB) is less than "
                    f"configured limit ({self.batch_config.memory_limit_mb}MB)"
                )
    
    async def _process_channels_concurrent(
        self,
        channel_inputs: List[str],
        language: str,
        date_from: Optional[str],
        date_to: Optional[str],
        progress_callback: Optional[Any]
    ):
        """Process channels concurrently with resource management.
        
        Args:
            channel_inputs: List of channel identifiers
            language: Transcript language
            date_from: Start date filter
            date_to: End date filter
            progress_callback: Optional progress callback
        """
        tasks = []
        
        for channel_input in channel_inputs:
            task = self._process_single_channel_wrapped(
                channel_input=channel_input,
                language=language,
                date_from=date_from,
                date_to=date_to,
                progress_callback=progress_callback
            )
            tasks.append(task)
        
        # Process all channels
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        for channel_input, result in zip(channel_inputs, results):
            if isinstance(result, Exception):
                logger.error(f"Channel {channel_input} processing failed: {result}")
                self.channel_progress[channel_input].status = "failed"
                self.channel_progress[channel_input].error_message = str(result)
                self.error_aggregator.add_error(channel_input, result)
    
    async def _process_single_channel_wrapped(
        self,
        channel_input: str,
        language: str,
        date_from: Optional[str],
        date_to: Optional[str],
        progress_callback: Optional[Any]
    ):
        """Process single channel with error handling wrapper.
        
        Args:
            channel_input: Channel identifier
            language: Transcript language
            date_from: Start date filter
            date_to: End date filter
            progress_callback: Optional progress callback
        """
        async with self.channel_semaphore:
            try:
                await self._process_single_channel(
                    channel_input=channel_input,
                    language=language,
                    date_from=date_from,
                    date_to=date_to,
                    progress_callback=progress_callback
                )
            except Exception as e:
                raise ErrorHandler.create_user_friendly_error(e)
    
    async def _process_single_channel(
        self,
        channel_input: str,
        language: str,
        date_from: Optional[str],
        date_to: Optional[str],
        progress_callback: Optional[Any]
    ):
        """Process a single channel with queue management.
        
        Args:
            channel_input: Channel identifier
            language: Transcript language
            date_from: Start date filter
            date_to: End date filter
            progress_callback: Optional progress callback
        """
        logger.info(f"Processing channel: {channel_input}")
        
        # Update progress
        progress = self.channel_progress[channel_input]
        progress.status = "processing"
        progress.started_at = datetime.now()
        
        try:
            # Get channel info
            channel = await self.channel_service.get_channel_by_input(channel_input)
            if not channel:
                raise ValueError(f"Channel not found: {channel_input}")
            
            progress.channel_title = channel.snippet.title
            
            # Get videos
            videos = await self.channel_service.get_channel_videos(
                channel_id=channel.id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Filter videos
            videos = self.channel_service.filter_videos(
                videos,
                skip_private=self.settings.processing.skip_private_videos,
                skip_live=self.settings.processing.skip_live_streams
            )
            
            progress.total_videos = len(videos)
            logger.info(f"Found {len(videos)} videos for channel {channel.snippet.title}")
            
            if not videos:
                progress.status = "completed"
                progress.completed_at = datetime.now()
                self.batch_result.add_channel_result(channel_input, progress)
                return
            
            # Create processing queue
            queue = ProcessingQueue(
                channel_id=channel.id,
                video_ids=[v.id for v in videos],
                batch_size=self.batch_config.batch_size
            )
            self.channel_queues[channel.id] = queue
            
            # Process videos in batches
            await self._process_channel_queue(
                channel=channel,
                videos=videos,
                queue=queue,
                language=language,
                progress=progress,
                progress_callback=progress_callback
            )
            
            # Finalize channel processing
            progress.completed_at = datetime.now()
            if progress.failed_videos == 0:
                progress.status = "completed"
            else:
                progress.status = "partial"
            
            # Add to batch result
            self.batch_result.add_channel_result(channel_input, progress)
            
            # Export channel summary if configured
            if self.settings.output.output_directory:
                await self._export_channel_summary(channel, progress)
            
        except Exception as e:
            logger.error(f"Failed to process channel {channel_input}: {e}")
            progress.status = "failed"
            progress.error_message = str(e)
            progress.completed_at = datetime.now()
            self.batch_result.add_channel_result(channel_input, progress)
            raise
    
    async def _process_channel_queue(
        self,
        channel: Channel,
        videos: List[Video],
        queue: ProcessingQueue,
        language: str,
        progress: ChannelProgress,
        progress_callback: Optional[Any]
    ):
        """Process channel videos using queue batching.
        
        Args:
            channel: Channel object
            videos: List of videos
            queue: Processing queue
            language: Transcript language
            progress: Channel progress tracker
            progress_callback: Optional progress callback
        """
        video_map = {v.id: v for v in videos}
        
        while not queue.is_complete:
            # Check memory before processing batch
            if not self.memory_monitor.check_memory():
                logger.warning("Memory limit approaching, waiting for cleanup...")
                await asyncio.sleep(5)
                continue
            
            # Get next batch
            batch_ids = queue.get_next_batch()
            if not batch_ids:
                break
            
            # Process batch
            batch_videos = [video_map[vid] for vid in batch_ids if vid in video_map]
            
            await self._process_video_batch(
                videos=batch_videos,
                channel=channel,
                language=language,
                progress=progress
            )
            
            # Update progress callback
            if progress_callback:
                await progress_callback({
                    'channel': channel.snippet.title,
                    'progress': progress.progress_percentage,
                    'processed': progress.processed_videos,
                    'total': progress.total_videos
                })
            
            # Update memory stats
            self.memory_monitor.update_stats()
    
    async def _process_video_batch(
        self,
        videos: List[Video],
        channel: Channel,
        language: str,
        progress: ChannelProgress
    ):
        """Process a batch of videos concurrently.
        
        Args:
            videos: Batch of videos to process
            channel: Channel object
            language: Transcript language
            progress: Progress tracker
        """
        tasks = []
        
        for video in videos:
            task = self._process_single_video(
                video=video,
                channel=channel,
                language=language,
                progress=progress
            )
            tasks.append(task)
        
        # Process batch concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle results
        for video, result in zip(videos, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process video {video.id}: {result}")
                self.error_aggregator.add_error(f"{channel.id}:{video.id}", result)
    
    async def _process_single_video(
        self,
        video: Video,
        channel: Channel,
        language: str,
        progress: ChannelProgress
    ):
        """Process a single video with semaphore control.
        
        Args:
            video: Video to process
            channel: Channel object
            language: Transcript language
            progress: Progress tracker
        """
        async with self.video_semaphore:
            try:
                # Get transcript
                transcript = await self.transcript_service.get_transcript(
                    video=video,
                    language=language,
                    use_fallback=True
                )
                
                success = transcript is not None
                
                if success:
                    video.transcript_data = transcript
                    # Export if configured
                    if self.settings.output.output_directory:
                        await self.export_service.export_transcript(
                            video=video,
                            transcript=transcript,
                            channel_name=channel.snippet.title
                        )
                
                # Update progress
                async with self.processing_lock:
                    progress.update_progress(success, video.id)
                
            except Exception as e:
                logger.error(f"Error processing video {video.id}: {e}")
                async with self.processing_lock:
                    progress.update_progress(False, video.id)
                    progress.error_count += 1
                raise
    
    async def _export_channel_summary(self, channel: Channel, progress: ChannelProgress):
        """Export channel processing summary.
        
        Args:
            channel: Channel object
            progress: Channel progress
        """
        try:
            summary_data = {
                "channel_id": channel.id,
                "channel_title": channel.snippet.title,
                "processing_status": progress.status,
                "total_videos": progress.total_videos,
                "processed_videos": progress.processed_videos,
                "successful_videos": progress.successful_videos,
                "failed_videos": progress.failed_videos,
                "success_rate": progress.success_rate,
                "processing_duration": str(progress.processing_duration) if progress.processing_duration else None,
                "started_at": progress.started_at.isoformat() if progress.started_at else None,
                "completed_at": progress.completed_at.isoformat() if progress.completed_at else None
            }
            
            # Save summary
            output_dir = self.settings.output.output_directory / channel.snippet.title
            output_dir.mkdir(parents=True, exist_ok=True)
            
            summary_path = output_dir / "processing_summary.json"
            
            import json
            with open(summary_path, 'w') as f:
                json.dump(summary_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to export channel summary: {e}")
    
    def _log_batch_summary(self):
        """Log batch processing summary."""
        logger.info(
            f"Batch processing complete: "
            f"{len(self.batch_result.successful_channels)} successful, "
            f"{len(self.batch_result.partial_channels)} partial, "
            f"{len(self.batch_result.failed_channels)} failed"
        )
        logger.info(
            f"Total videos: {self.batch_result.total_videos_processed} processed, "
            f"{self.batch_result.total_videos_successful} successful, "
            f"{self.batch_result.total_videos_failed} failed"
        )
        logger.info(f"Overall success rate: {self.batch_result.overall_success_rate:.1f}%")
        
        if self.batch_result.quota_usage:
            logger.info(f"Quota usage: {self.batch_result.quota_usage}")


class MemoryMonitor:
    """Monitor memory usage for resource management."""
    
    def __init__(self, limit_mb: int):
        """Initialize memory monitor.
        
        Args:
            limit_mb: Memory limit in megabytes
        """
        self.limit_mb = limit_mb
        self.peak_usage_mb = 0.0
    
    def check_memory(self) -> bool:
        """Check if memory usage is within limits.
        
        Returns:
            True if memory usage is acceptable
        """
        current_mb = self.get_current_usage_mb()
        
        if current_mb > self.limit_mb * 0.9:  # 90% threshold
            logger.warning(f"Memory usage high: {current_mb:.1f}MB / {self.limit_mb}MB")
            return False
        
        return True
    
    def get_current_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        if HAS_PSUTIL:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        else:
            # Return a dummy value if psutil not available
            return 0.0
    
    def update_stats(self):
        """Update memory statistics."""
        current_mb = self.get_current_usage_mb()
        self.peak_usage_mb = max(self.peak_usage_mb, current_mb)