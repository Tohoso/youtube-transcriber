"""YouTube Transcript API repository."""

from typing import List, Optional

from loguru import logger
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from ..models.transcript import TranscriptData, TranscriptSegment, TranscriptSource
from ..utils.retry import async_retry


class YouTubeTranscriptAPIRepository:
    """YouTube Transcript API client."""
    
    def __init__(self):
        """Initialize transcript API repository."""
        pass
    
    async def get_transcript(
        self,
        video_id: str,
        language: str = "ja",
    ) -> Optional[TranscriptData]:
        """Get transcript using youtube-transcript-api."""
        try:
            transcript_list = await self._fetch_transcript(video_id, language)
            if not transcript_list:
                return None
            
            segments = [
                TranscriptSegment(
                    text=entry["text"],
                    start_time=entry["start"],
                    duration=entry["duration"],
                )
                for entry in transcript_list
            ]
            
            return TranscriptData(
                video_id=video_id,
                language=language,
                source=TranscriptSource.YOUTUBE_TRANSCRIPT_API,
                auto_generated=self._is_auto_generated(transcript_list),
                segments=segments,
            )
            
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
            logger.debug(f"No transcript available for {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching transcript for {video_id}: {e}")
            return None
    
    @async_retry(max_attempts=2, delay=0.5)
    async def _fetch_transcript(
        self,
        video_id: str,
        language: str,
    ) -> Optional[List[dict]]:
        """Fetch transcript data."""
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        try:
            transcript_list = await loop.run_in_executor(
                None,
                YouTubeTranscriptApi.get_transcript,
                video_id,
                [language, "en", "ja"]
            )
            return transcript_list
        except Exception:
            transcript_list = await loop.run_in_executor(
                None,
                YouTubeTranscriptApi.get_transcript,
                video_id
            )
            return transcript_list
    
    def _is_auto_generated(self, transcript_list: List[dict]) -> bool:
        """Check if transcript is auto-generated."""
        if not transcript_list:
            return False
        
        return any(
            entry.get("auto_generated", False)
            for entry in transcript_list
        )