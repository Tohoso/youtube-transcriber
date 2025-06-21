"""Channel service for managing YouTube channel operations."""

import re
from datetime import datetime
from typing import List, Optional
from loguru import logger

from ..models.channel import Channel, ProcessingStatistics
from ..models.video import Video
from ..models.transcript import TranscriptStatus
from ..repositories.youtube_api import YouTubeAPIRepository
from ..utils.retry import RetryManager


class ChannelService:
    """Service for managing YouTube channel operations."""
    
    def __init__(
        self,
        youtube_repo: Optional[YouTubeAPIRepository] = None,
        retry_manager: Optional[RetryManager] = None
    ):
        """Initialize channel service.
        
        Args:
            youtube_repo: YouTube API repository
            retry_manager: Retry manager for error handling
        """
        self.youtube_repo = youtube_repo or YouTubeAPIRepository()
        self.retry_manager = retry_manager or RetryManager()
    
    async def get_channel_by_input(self, channel_input: str) -> Channel:
        """Get channel information from various input formats.
        
        Args:
            channel_input: Channel URL, ID, or @handle
            
        Returns:
            Channel object with basic information
            
        Raises:
            ValueError: If channel input is invalid
        """
        channel_id = self.extract_channel_id(channel_input)
        
        logger.info(f"Getting channel information for ID: {channel_id}")
        
        channel = await self.retry_manager.execute(
            self.youtube_repo.get_channel_info,
            channel_id=channel_id
        )
        
        # Initialize processing statistics
        channel.processing_stats = ProcessingStatistics(
            processing_start_time=datetime.now()
        )
        
        return channel
    
    def extract_channel_id(self, channel_input: str) -> str:
        """Extract channel ID from various input formats.
        
        Args:
            channel_input: Channel URL, ID, or @handle
            
        Returns:
            Channel ID (UC format)
            
        Raises:
            ValueError: If unable to extract valid channel ID
        """
        # Remove whitespace
        channel_input = channel_input.strip()
        
        # Already a channel ID
        if re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_input):
            return channel_input
        
        # URL patterns
        patterns = [
            # Standard channel URL
            (r'youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', 1),
            # Custom channel URL
            (r'youtube\.com/c/([^/?]+)', 1),
            # Handle URL
            (r'youtube\.com/@([^/?]+)', 1),
            # Mobile URL
            (r'm\.youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})', 1),
            # Short URL
            (r'youtu\.be/channel/(UC[a-zA-Z0-9_-]{22})', 1),
        ]
        
        for pattern, group in patterns:
            match = re.search(pattern, channel_input)
            if match:
                extracted = match.group(group)
                
                # If it's already a channel ID, return it
                if extracted.startswith('UC'):
                    return extracted
                
                # For handles and custom URLs, we need to resolve them
                # This would require an additional API call
                logger.info(f"Found handle/custom URL: {extracted}")
                # In a real implementation, we would resolve this to a channel ID
                # For now, we'll raise an error
                raise ValueError(
                    f"Handle/custom URL resolution not implemented. "
                    f"Please use the channel ID directly. Found: {extracted}"
                )
        
        # Try as @handle
        if channel_input.startswith('@'):
            handle = channel_input[1:]
            logger.info(f"Found handle: {handle}")
            raise ValueError(
                f"Handle resolution not implemented. "
                f"Please use the channel ID directly. Handle: {handle}"
            )
        
        raise ValueError(f"Unable to extract channel ID from: {channel_input}")
    
    async def get_channel_videos(
        self,
        channel_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[Video]:
        """Get videos from a channel with optional filters.
        
        Args:
            channel_id: YouTube channel ID
            date_from: Start date filter (YYYY-MM-DD)
            date_to: End date filter (YYYY-MM-DD)
            max_results: Maximum number of videos to retrieve
            
        Returns:
            List of Video objects
        """
        logger.info(
            f"Getting videos for channel {channel_id} "
            f"(from: {date_from}, to: {date_to}, max: {max_results})"
        )
        
        videos = await self.retry_manager.execute(
            self.youtube_repo.get_channel_videos,
            channel_id=channel_id,
            date_from=date_from,
            date_to=date_to,
            max_results=max_results
        )
        
        logger.info(f"Retrieved {len(videos)} videos from channel {channel_id}")
        
        return videos
    
    async def update_channel_with_videos(
        self,
        channel: Channel,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Channel:
        """Update channel object with video list.
        
        Args:
            channel: Channel object to update
            date_from: Start date filter
            date_to: End date filter
            
        Returns:
            Updated channel object
        """
        videos = await self.get_channel_videos(
            channel_id=channel.id,
            date_from=date_from,
            date_to=date_to
        )
        
        channel.videos = videos
        channel.processing_stats.total_videos = len(videos)
        
        # Update channel statistics from videos if needed
        channel.update_processing_statistics()
        
        return channel
    
    def filter_videos(
        self,
        videos: List[Video],
        skip_private: bool = True,
        skip_live: bool = True,
        skip_shorts: bool = False,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> List[Video]:
        """Filter videos based on criteria.
        
        Args:
            videos: List of videos to filter
            skip_private: Skip private videos
            skip_live: Skip live streams
            skip_shorts: Skip YouTube Shorts
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            
        Returns:
            Filtered list of videos
        """
        filtered = []
        
        for video in videos:
            # Skip private videos
            if skip_private and video.is_private:
                logger.debug(f"Skipping private video: {video.id}")
                video.transcript_status = TranscriptStatus.SKIPPED
                video.error_message = "Private video"
                filtered.append(video)
                continue
            
            # Skip live streams
            if skip_live and video.is_live:
                logger.debug(f"Skipping live stream: {video.id}")
                video.transcript_status = TranscriptStatus.SKIPPED
                video.error_message = "Live stream"
                filtered.append(video)
                continue
            
            # Skip shorts (typically < 60 seconds)
            if skip_shorts and video.is_short:
                logger.debug(f"Skipping YouTube Short: {video.id}")
                video.transcript_status = TranscriptStatus.SKIPPED
                video.error_message = "YouTube Short"
                filtered.append(video)
                continue
            
            # Duration filters
            if video.statistics and video.statistics.duration_seconds:
                duration = video.statistics.duration_seconds
                
                if min_duration and duration < min_duration:
                    logger.debug(f"Skipping video {video.id}: duration {duration}s < {min_duration}s")
                    video.transcript_status = TranscriptStatus.SKIPPED
                    video.error_message = f"Duration too short ({duration}s)"
                    filtered.append(video)
                    continue
                
                if max_duration and duration > max_duration:
                    logger.debug(f"Skipping video {video.id}: duration {duration}s > {max_duration}s")
                    video.transcript_status = TranscriptStatus.SKIPPED
                    video.error_message = f"Duration too long ({duration}s)"
                    filtered.append(video)
                    continue
            
            filtered.append(video)
        
        logger.info(
            f"Filtered {len(videos)} videos to {len([v for v in filtered if v.transcript_status != TranscriptStatus.SKIPPED])} "
            f"({len([v for v in filtered if v.transcript_status == TranscriptStatus.SKIPPED])} skipped)"
        )
        
        return filtered
    
    async def get_channel_statistics_summary(self, channel_id: str) -> dict:
        """Get comprehensive statistics for a channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Statistics summary dictionary
        """
        channel = await self.get_channel_by_input(channel_id)
        videos = await self.get_channel_videos(channel_id)
        
        # Calculate video statistics
        total_duration = 0
        total_views = 0
        total_likes = 0
        total_comments = 0
        
        video_types = {
            "regular": 0,
            "live": 0,
            "shorts": 0,
            "private": 0
        }
        
        for video in videos:
            if video.is_private:
                video_types["private"] += 1
            elif video.is_live:
                video_types["live"] += 1
            elif video.is_short:
                video_types["shorts"] += 1
            else:
                video_types["regular"] += 1
            
            if video.statistics:
                if video.statistics.duration_seconds:
                    total_duration += video.statistics.duration_seconds
                if video.statistics.view_count:
                    total_views += video.statistics.view_count
                if video.statistics.like_count:
                    total_likes += video.statistics.like_count
                if video.statistics.comment_count:
                    total_comments += video.statistics.comment_count
        
        summary = {
            "channel": {
                "id": channel.id,
                "title": channel.snippet.title,
                "subscriber_count": channel.statistics.subscriber_count if channel.statistics else 0,
                "total_videos": channel.statistics.video_count if channel.statistics else len(videos)
            },
            "videos": {
                "total": len(videos),
                "types": video_types,
                "total_duration_hours": total_duration / 3600,
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "avg_views_per_video": total_views / len(videos) if videos else 0,
                "avg_duration_minutes": (total_duration / len(videos) / 60) if videos else 0
            },
            "date_range": {
                "oldest_video": min((v.published_at for v in videos), default=None),
                "newest_video": max((v.published_at for v in videos), default=None)
            }
        }
        
        return summary