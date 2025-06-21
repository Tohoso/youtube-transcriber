"""Transcript orchestrator for managing the main processing flow."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
from loguru import logger

from ..cli.display import DisplayManager
from ..models.channel import Channel, ProcessingStatistics
from ..models.config import AppSettings
from ..models.transcript import TranscriptData, TranscriptStatus
from ..models.video import Video
from ..services import ChannelService, TranscriptService, ExportService
from ..utils.retry import RetryManager


class TranscriptOrchestrator:
    """Main orchestrator for transcript extraction process."""
    
    def __init__(self, settings: AppSettings):
        """Initialize orchestrator with settings.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.display = DisplayManager()
        
        # Initialize services
        self.channel_service = ChannelService()
        self.transcript_service = TranscriptService()
        self.export_service = ExportService(output_config=settings.output)
        
        self._semaphore = asyncio.Semaphore(settings.processing.concurrent_limit)
        self._processed_videos: Set[str] = set()
    
    async def process_channel(
        self,
        channel_input: str,
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        dry_run: bool = False
    ) -> Channel:
        """Process a YouTube channel and extract transcripts.
        
        Args:
            channel_input: Channel URL, ID, or @handle
            language: Transcript language code
            date_from: Start date filter (YYYY-MM-DD)
            date_to: End date filter (YYYY-MM-DD)
            dry_run: Test run without downloading
            
        Returns:
            Channel object with processing results
        """
        try:
            # Get channel information
            self.display.show_status("Getting channel information...")
            channel = await self.channel_service.get_channel_by_input(channel_input)
            
            # Initialize processing statistics
            channel.processing_stats = ProcessingStatistics(
                processing_start_time=datetime.now()
            )
            
            # Display channel info
            self.display.show_channel_info(channel)
            
            # Get video list
            self.display.show_status("Fetching video list...")
            videos = await self.channel_service.get_channel_videos(
                channel_id=channel.id,
                date_from=date_from,
                date_to=date_to
            )
            
            # Filter videos based on settings
            videos = self.channel_service.filter_videos(
                videos,
                skip_private=self.settings.processing.skip_private_videos,
                skip_live=self.settings.processing.skip_live_streams
            )
            
            # Update channel with video list
            channel.videos = videos
            channel.processing_stats.total_videos = len(videos)
            
            logger.info(f"Found {len(videos)} videos to process")
            
            if dry_run:
                self.display.show_status("[yellow]Dry run mode - skipping transcript download[/yellow]")
                return channel
            
            # Process videos with parallel control
            await self._process_videos_parallel(
                channel=channel,
                videos=videos,
                language=language
            )
            
            # Display summary
            self.display.show_summary(channel)
            
            # Export results if output is configured
            if self.settings.output.output_directory:
                await self.export_service.export_channel_transcripts(
                    channel=channel,
                    create_summary=True
                )
            
            return channel
            
        except Exception as e:
            logger.error(f"Channel processing failed: {e}")
            raise
    
    async def _process_videos_parallel(
        self,
        channel: Channel,
        videos: List[Video],
        language: str
    ):
        """Process videos in parallel with semaphore control.
        
        Args:
            channel: Channel object
            videos: List of videos to process
            language: Transcript language code
        """
        # Create progress tracking
        with self.display.create_progress() as progress:
            task_id = progress.add_task(
                f"Processing {len(videos)} videos",
                total=len(videos)
            )
            
            # Create tasks for all videos
            tasks = []
            for video in videos:
                if video.transcript_status == TranscriptStatus.SKIPPED:
                    progress.advance(task_id)
                    continue
                
                task = self._process_single_video(
                    video=video,
                    language=language,
                    progress=progress,
                    task_id=task_id,
                    channel=channel
                )
                tasks.append(task)
            
            # Execute all tasks concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_video(
        self,
        video: Video,
        language: str,
        progress,
        task_id: int,
        channel: Channel
    ):
        """Process a single video with semaphore control.
        
        Args:
            video: Video to process
            language: Transcript language code
            progress: Progress tracker
            task_id: Progress task ID
            channel: Parent channel object
        """
        async with self._semaphore:
            start_time = datetime.now()
            
            try:
                # Update status
                video.transcript_status = TranscriptStatus.IN_PROGRESS
                
                # Get transcript using service
                transcript = await self.transcript_service.get_transcript(
                    video=video,
                    language=language,
                    use_fallback=True
                )
                
                if transcript:
                    video.transcript = transcript
                    video.transcript_status = TranscriptStatus.SUCCESS
                    channel.processing_stats.successful_videos += 1
                    
                    # Export transcript if output is configured
                    if self.settings.output.output_directory:
                        await self.export_service.export_transcript(
                            video=video,
                            transcript=transcript
                        )
                else:
                    video.transcript_status = TranscriptStatus.ERROR
                    video.error_message = "No transcript available"
                    channel.processing_stats.failed_videos += 1
                
            except Exception as e:
                logger.error(f"Failed to process video {video.id}: {e}")
                video.transcript_status = TranscriptStatus.ERROR
                video.error_message = str(e)
                channel.processing_stats.failed_videos += 1
                channel.processing_stats.update_error_statistics(type(e).__name__)
            
            finally:
                # Update processing time
                processing_duration = (datetime.now() - start_time).total_seconds()
                video.processing_duration = processing_duration
                channel.processing_stats.update_processing_time(processing_duration)
                
                # Update progress
                channel.processing_stats.processed_videos += 1
                channel.processing_stats.last_update_time = datetime.now()
                
                # Display result
                self.display.show_video_result(video)
                
                # Update progress bar
                progress.advance(task_id)
                
                # Update live statistics
                if channel.processing_stats.processed_videos % 10 == 0:
                    self.display.show_processing_stats(channel.processing_stats)
