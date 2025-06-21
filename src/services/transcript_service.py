"""Transcript service for managing transcript extraction with fallback support."""

import asyncio
from typing import Optional
from loguru import logger

from ..models.transcript import TranscriptData, TranscriptSource, TranscriptStatus
from ..models.video import Video
from ..repositories.transcript_api import YouTubeTranscriptAPIRepository
from ..repositories.ytdlp_repository import YtDlpRepository
from ..utils.retry import RetryManager


class TranscriptService:
    """Service for managing transcript extraction with multiple sources."""
    
    def __init__(
        self,
        transcript_api_repo: Optional[YouTubeTranscriptAPIRepository] = None,
        ytdlp_repo: Optional[YtDlpRepository] = None,
        retry_manager: Optional[RetryManager] = None
    ):
        """Initialize transcript service.
        
        Args:
            transcript_api_repo: YouTube Transcript API repository
            ytdlp_repo: yt-dlp repository for fallback
            retry_manager: Retry manager for error handling
        """
        self.transcript_api_repo = transcript_api_repo or YouTubeTranscriptAPIRepository()
        self.ytdlp_repo = ytdlp_repo or YtDlpRepository()
        self.retry_manager = retry_manager or RetryManager()
    
    async def get_transcript(
        self,
        video: Video,
        language: str = "ja",
        use_fallback: bool = True
    ) -> Optional[TranscriptData]:
        """Get transcript for a video with fallback support.
        
        Args:
            video: Video object to get transcript for
            language: Preferred language code
            use_fallback: Whether to use yt-dlp as fallback
            
        Returns:
            TranscriptData if successful, None otherwise
        """
        logger.info(f"Getting transcript for video {video.id} in language {language}")
        
        # Try primary source: YouTube Transcript API
        try:
            transcript = await self._get_from_transcript_api(video.id, language)
            if transcript:
                logger.info(f"Successfully got transcript from YouTube Transcript API for {video.id}")
                return transcript
        except Exception as e:
            logger.warning(f"YouTube Transcript API failed for {video.id}: {e}")
        
        # Try fallback: yt-dlp
        if use_fallback:
            try:
                transcript = await self._get_from_ytdlp(video.id, language)
                if transcript:
                    logger.info(f"Successfully got transcript from yt-dlp for {video.id}")
                    return transcript
            except Exception as e:
                logger.warning(f"yt-dlp fallback failed for {video.id}: {e}")
        
        logger.warning(f"No transcript available for video {video.id}")
        return None
    
    async def _get_from_transcript_api(
        self,
        video_id: str,
        language: str
    ) -> Optional[TranscriptData]:
        """Get transcript using YouTube Transcript API.
        
        Args:
            video_id: YouTube video ID
            language: Language code
            
        Returns:
            TranscriptData if successful, None otherwise
        """
        return await self.retry_manager.execute(
            self.transcript_api_repo.get_transcript,
            video_id=video_id,
            language=language
        )
    
    async def _get_from_ytdlp(
        self,
        video_id: str,
        language: str
    ) -> Optional[TranscriptData]:
        """Get transcript using yt-dlp as fallback.
        
        Args:
            video_id: YouTube video ID
            language: Language code
            
        Returns:
            TranscriptData if successful, None otherwise
        """
        return await self.retry_manager.execute(
            self.ytdlp_repo.get_transcript,
            video_id=video_id,
            language=language
        )
    
    async def process_video_batch(
        self,
        videos: list[Video],
        language: str = "ja",
        concurrent_limit: int = 5,
        progress_callback=None
    ) -> dict[str, TranscriptData]:
        """Process multiple videos concurrently.
        
        Args:
            videos: List of videos to process
            language: Preferred language code
            concurrent_limit: Maximum concurrent operations
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping video ID to transcript data
        """
        semaphore = asyncio.Semaphore(concurrent_limit)
        results = {}
        
        async def process_single(video: Video):
            async with semaphore:
                try:
                    transcript = await self.get_transcript(video, language)
                    if transcript:
                        results[video.id] = transcript
                        video.transcript = transcript
                        video.transcript_status = TranscriptStatus.SUCCESS
                    else:
                        video.transcript_status = TranscriptStatus.NO_TRANSCRIPT
                except Exception as e:
                    logger.error(f"Failed to process video {video.id}: {e}")
                    video.transcript_status = TranscriptStatus.ERROR
                    video.error_message = str(e)
                finally:
                    if progress_callback:
                        await progress_callback(video)
        
        # Process all videos concurrently
        await asyncio.gather(
            *[process_single(video) for video in videos],
            return_exceptions=True
        )
        
        return results
    
    def validate_transcript(self, transcript: TranscriptData) -> bool:
        """Validate transcript data quality.
        
        Args:
            transcript: Transcript data to validate
            
        Returns:
            True if transcript is valid, False otherwise
        """
        if not transcript or not transcript.segments:
            return False
        
        # Check for minimum content
        if transcript.word_count < 10:
            logger.warning(f"Transcript for {transcript.video_id} has very few words: {transcript.word_count}")
            return False
        
        # Check for reasonable duration
        if transcript.duration < 1:
            logger.warning(f"Transcript for {transcript.video_id} has very short duration: {transcript.duration}s")
            return False
        
        return True
    
    async def get_transcript_statistics(self, video_ids: list[str]) -> dict:
        """Get statistics for multiple video transcripts.
        
        Args:
            video_ids: List of video IDs to analyze
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_videos": len(video_ids),
            "transcripts_found": 0,
            "auto_generated": 0,
            "manual": 0,
            "total_words": 0,
            "total_duration": 0,
            "sources": {
                TranscriptSource.YOUTUBE_TRANSCRIPT_API.value: 0,
                TranscriptSource.YT_DLP.value: 0
            }
        }
        
        for video_id in video_ids:
            # Create temporary video object
            video = Video(id=video_id, title="", url="")
            transcript = await self.get_transcript(video)
            
            if transcript:
                stats["transcripts_found"] += 1
                stats["total_words"] += transcript.word_count
                stats["total_duration"] += transcript.duration
                stats["sources"][transcript.source.value] += 1
                
                if transcript.auto_generated:
                    stats["auto_generated"] += 1
                else:
                    stats["manual"] += 1
        
        # Calculate averages
        if stats["transcripts_found"] > 0:
            stats["avg_words_per_video"] = stats["total_words"] / stats["transcripts_found"]
            stats["avg_duration"] = stats["total_duration"] / stats["transcripts_found"]
        else:
            stats["avg_words_per_video"] = 0
            stats["avg_duration"] = 0
        
        return stats