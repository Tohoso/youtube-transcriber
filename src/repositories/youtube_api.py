"""YouTube Data API v3 repository."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from loguru import logger

from ..models.channel import Channel, ChannelSnippet, ChannelStatistics
from ..models.video import Video, VideoStatistics
from ..utils.rate_limiter import RateLimiter
from ..utils.retry import async_retry


class YouTubeAPIRepository:
    """YouTube Data API v3 client."""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        """Initialize YouTube API repository."""
        self.api_key = api_key
        self.session = session
        self.rate_limiter = RateLimiter(rate=60, per=60.0)
    
    @async_retry(max_attempts=3, delay=1.0)
    async def get_channel_info(self, channel_input: str) -> Optional[Channel]:
        """Get channel information."""
        channel_id = await self._resolve_channel_id(channel_input)
        if not channel_id:
            return None
        
        await self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}/channels"
        params = {
            "part": "snippet,statistics",
            "id": channel_id,
            "key": self.api_key,
        }
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            
            if not data.get("items"):
                logger.error(f"Channel not found: {channel_id}")
                return None
            
            item = data["items"][0]
            
            snippet_data = item["snippet"]
            snippet = ChannelSnippet(
                title=snippet_data["title"],
                description=snippet_data.get("description"),
                custom_url=snippet_data.get("customUrl"),
                published_at=datetime.fromisoformat(
                    snippet_data["publishedAt"].replace("Z", "+00:00")
                ) if "publishedAt" in snippet_data else None,
                thumbnail_url=snippet_data.get("thumbnails", {}).get("high", {}).get("url"),
                country=snippet_data.get("country"),
                default_language=snippet_data.get("defaultLanguage"),
            )
            
            stats_data = item.get("statistics", {})
            statistics = ChannelStatistics(
                subscriber_count=int(stats_data.get("subscriberCount", 0)),
                video_count=int(stats_data.get("videoCount", 0)),
                view_count=int(stats_data.get("viewCount", 0)),
            )
            
            return Channel(
                id=channel_id,
                snippet=snippet,
                statistics=statistics,
            )
    
    async def get_channel_videos(
        self,
        channel_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_results: int = 50,
    ) -> List[Video]:
        """Get all videos from a channel."""
        videos = []
        next_page_token = None
        
        while True:
            await self.rate_limiter.acquire()
            
            url = f"{self.BASE_URL}/search"
            params = {
                "part": "id",
                "channelId": channel_id,
                "type": "video",
                "order": "date",
                "maxResults": min(max_results, 50),
                "key": self.api_key,
            }
            
            if next_page_token:
                params["pageToken"] = next_page_token
            if date_from:
                params["publishedAfter"] = f"{date_from}T00:00:00Z"
            if date_to:
                params["publishedBefore"] = f"{date_to}T23:59:59Z"
            
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if "error" in data:
                    logger.error(f"API error: {data['error']}")
                    break
                
                video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
                
                if video_ids:
                    video_details = await self._get_video_details(video_ids)
                    videos.extend(video_details)
                
                next_page_token = data.get("nextPageToken")
                if not next_page_token or len(videos) >= max_results:
                    break
        
        return videos[:max_results]
    
    async def _get_video_details(self, video_ids: List[str]) -> List[Video]:
        """Get detailed information for videos."""
        await self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}/videos"
        params = {
            "part": "snippet,statistics,contentDetails,status",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            
            videos = []
            for item in data.get("items", []):
                try:
                    video = self._parse_video_item(item)
                    videos.append(video)
                except Exception as e:
                    logger.error(f"Error parsing video {item.get('id')}: {e}")
            
            return videos
    
    def _parse_video_item(self, item: Dict[str, Any]) -> Video:
        """Parse video item from API response."""
        video_id = item["id"]
        snippet = item["snippet"]
        
        statistics = None
        if "statistics" in item:
            stats = item["statistics"]
            statistics = VideoStatistics(
                view_count=int(stats.get("viewCount", 0)),
                like_count=int(stats.get("likeCount", 0)),
                comment_count=int(stats.get("commentCount", 0)),
                duration_seconds=self._parse_duration(
                    item.get("contentDetails", {}).get("duration", "PT0S")
                ),
            )
        
        return Video(
            id=video_id,
            title=snippet["title"],
            url=f"https://www.youtube.com/watch?v={video_id}",
            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
            description=snippet.get("description"),
            published_at=datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            ) if "publishedAt" in snippet else None,
            privacy_status=item.get("status", {}).get("privacyStatus"),
            statistics=statistics,
            tags=snippet.get("tags", []),
            category_id=snippet.get("categoryId"),
            language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
        )
    
    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to seconds."""
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    async def _resolve_channel_id(self, channel_input: str) -> Optional[str]:
        """Resolve channel ID from various input formats."""
        if channel_input.startswith("UC") and len(channel_input) == 24:
            return channel_input
        
        if channel_input.startswith("@"):
            return await self._get_channel_id_from_handle(channel_input)
        
        url_patterns = [
            r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',
            r'youtube\.com/@([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, channel_input)
            if match:
                identifier = match.group(1)
                if pattern.endswith('channel/([a-zA-Z0-9_-]+)'):
                    return identifier
                else:
                    return await self._get_channel_id_from_handle(f"@{identifier}")
        
        return await self._get_channel_id_from_handle(channel_input)
    
    async def _get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """Get channel ID from handle."""
        await self.rate_limiter.acquire()
        
        search_query = handle.lstrip("@")
        url = f"{self.BASE_URL}/search"
        params = {
            "part": "id",
            "q": search_query,
            "type": "channel",
            "maxResults": 1,
            "key": self.api_key,
        }
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            
            if data.get("items"):
                return data["items"][0]["id"]["channelId"]
        
        return None