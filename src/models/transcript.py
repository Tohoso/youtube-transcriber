"""Transcript data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TranscriptStatus(str, Enum):
    """Transcript retrieval status."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    NO_TRANSCRIPT = "no_transcript"
    ERROR = "error"
    SKIPPED = "skipped"


class TranscriptSource(str, Enum):
    """Transcript source."""
    
    YOUTUBE_TRANSCRIPT_API = "youtube_transcript_api"
    YT_DLP = "yt_dlp"
    MANUAL = "manual"


class TranscriptSegment(BaseModel):
    """Individual transcript segment."""
    
    text: str = Field(..., description="Segment text", min_length=1)
    start_time: float = Field(..., description="Start time in seconds", ge=0.0)
    duration: float = Field(..., description="Duration in seconds", gt=0.0)
    end_time: Optional[float] = Field(None, description="End time in seconds")
    
    @field_validator('end_time', mode='before')
    @classmethod
    def set_end_time(cls, v: Optional[float], info) -> Optional[float]:
        """Calculate end time automatically."""
        if v is None and 'start_time' in info.data and 'duration' in info.data:
            return info.data['start_time'] + info.data['duration']
        return v
    
    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: Optional[float], info) -> Optional[float]:
        """Validate end time."""
        if v is not None and 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be greater than start_time')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Hello, world!",
                "start_time": 10.5,
                "duration": 3.2,
                "end_time": 13.7
            }
        }
    }


class TranscriptData(BaseModel):
    """Video transcript data."""
    
    video_id: str = Field(..., description="Video ID", pattern=r'^[a-zA-Z0-9_-]{11}$')
    language: str = Field(..., description="Language code", pattern=r'^[a-z]{2}$')
    source: TranscriptSource = Field(..., description="Source")
    auto_generated: bool = Field(False, description="Auto-generated flag")
    full_text: str = Field("", description="Full transcript text")
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Segment list")
    total_duration: Optional[float] = Field(None, description="Total duration in seconds", ge=0.0)
    word_count: Optional[int] = Field(None, description="Word count", ge=0)
    character_count: Optional[int] = Field(None, description="Character count", ge=0)
    extracted_at: datetime = Field(default_factory=datetime.now, description="Extraction time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    
    @field_validator('full_text', mode='before')
    @classmethod
    def set_full_text(cls, v: str, info) -> str:
        """Generate full text from segments."""
        if not v and 'segments' in info.data and info.data['segments']:
            segments = info.data['segments']
            if segments and len(segments) > 0:
                # Handle both dict and TranscriptSegment objects
                if isinstance(segments[0], dict):
                    return ' '.join(segment['text'] for segment in segments if 'text' in segment)
                else:
                    return ' '.join(segment.text for segment in segments)
        return v
    
    @field_validator('total_duration', mode='before')
    @classmethod
    def set_total_duration(cls, v: Optional[float], info) -> Optional[float]:
        """Calculate total duration."""
        if v is None and 'segments' in info.data and info.data['segments']:
            segments = info.data['segments']
            if segments and len(segments) > 0:
                # Handle both dict and TranscriptSegment objects
                if isinstance(segments[0], dict):
                    last_segment = segments[-1]
                    return last_segment.get('start_time', 0) + last_segment.get('duration', 0)
                else:
                    return max((segment.end_time or (segment.start_time + segment.duration)) for segment in segments)
        return v
    
    @field_validator('word_count', mode='before')
    @classmethod
    def set_word_count(cls, v: Optional[int], info) -> Optional[int]:
        """Calculate word count."""
        if v is None and 'full_text' in info.data and info.data['full_text']:
            return len(info.data['full_text'].split())
        return v
    
    @field_validator('character_count', mode='before')
    @classmethod
    def set_character_count(cls, v: Optional[int], info) -> Optional[int]:
        """Calculate character count."""
        if v is None and 'full_text' in info.data and info.data['full_text']:
            return len(info.data['full_text'])
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "language": "ja",
                "source": "youtube_transcript_api",
                "auto_generated": True,
                "full_text": "Hello, world! This is a test.",
                "segments": [
                    {
                        "text": "Hello, world!",
                        "start_time": 0.0,
                        "duration": 2.0
                    }
                ],
                "word_count": 5,
                "character_count": 27
            }
        }
    }