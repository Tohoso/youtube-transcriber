"""Video data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator

from .transcript import TranscriptData, TranscriptStatus


class VideoPrivacy(str, Enum):
    """Video privacy setting."""
    
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class VideoStatistics(BaseModel):
    """Video statistics."""
    
    view_count: Optional[int] = Field(None, description="View count", ge=0)
    like_count: Optional[int] = Field(None, description="Like count", ge=0)
    comment_count: Optional[int] = Field(None, description="Comment count", ge=0)
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds", ge=0)


class Video(BaseModel):
    """Video information."""
    
    id: str = Field(..., description="Video ID", pattern=r'^[a-zA-Z0-9_-]{11}$')
    title: str = Field(..., description="Video title", min_length=1, max_length=500)
    url: AnyHttpUrl = Field(..., description="Video URL")
    thumbnail_url: Optional[AnyHttpUrl] = Field(None, description="Thumbnail URL")
    description: Optional[str] = Field(None, description="Video description", max_length=5000)
    published_at: Optional[datetime] = Field(None, description="Published date")
    updated_at: Optional[datetime] = Field(None, description="Updated date")
    privacy_status: Optional[VideoPrivacy] = Field(None, description="Privacy setting")
    
    statistics: Optional[VideoStatistics] = Field(None, description="Statistics")
    
    transcript_status: TranscriptStatus = Field(
        TranscriptStatus.PENDING, 
        description="Transcript status"
    )
    transcript_data: Optional[TranscriptData] = Field(None, description="Transcript data")
    transcript_file_path: Optional[str] = Field(None, description="Transcript file path")
    
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(0, description="Retry count", ge=0)
    
    tags: List[str] = Field(default_factory=list, description="Tag list")
    category_id: Optional[str] = Field(None, description="Category ID")
    language: Optional[str] = Field(None, description="Video language")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    processed_at: Optional[datetime] = Field(None, description="Processing date")
    processing_duration: Optional[float] = Field(None, description="Processing duration in seconds", ge=0.0)
    
    @field_validator('url', mode='before')
    @classmethod
    def convert_url(cls, v: Any) -> Any:
        """Standardize YouTube URL."""
        if isinstance(v, str):
            if not v.startswith(('http://', 'https://')):
                return f"https://www.youtube.com/watch?v={v}"
        return v
    
    @property
    def has_transcript(self) -> bool:
        """Check if transcript data exists."""
        return self.transcript_data is not None
    
    @property
    def duration_formatted(self) -> Optional[str]:
        """Format video duration."""
        if not self.statistics or not self.statistics.duration_seconds:
            return None
        
        seconds = self.statistics.duration_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def get_processing_status_summary(self) -> Dict[str, Any]:
        """Get a summary of video processing status."""
        summary = {
            "video_id": self.id,
            "title": self.title,
            "status": self.transcript_status.value,
            "has_transcript": self.has_transcript,
            "retry_count": self.retry_count,
            "processing_duration": self.processing_duration,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "error_message": self.error_message
        }
        
        # Add transcript statistics if available
        if self.transcript_data:
            summary["transcript_stats"] = {
                "segment_count": len(self.transcript_data.segments),
                "duration": self.transcript_data.duration,
                "language": self.transcript_data.language
            }
        
        return summary
    
    def calculate_processing_efficiency(self) -> Optional[float]:
        """Calculate processing efficiency (ratio of video duration to processing time)."""
        if not self.processing_duration or not self.statistics or not self.statistics.duration_seconds:
            return None
        
        if self.processing_duration == 0:
            return None
        
        # Higher efficiency means faster processing relative to video length
        return self.statistics.duration_seconds / self.processing_duration
    
    def get_error_classification(self) -> Optional[str]:
        """Classify error type from error message."""
        if not self.error_message:
            return None
        
        error_lower = self.error_message.lower()
        
        if 'network' in error_lower or 'connection' in error_lower:
            return 'Network Error'
        elif 'permission' in error_lower or 'forbidden' in error_lower:
            return 'Permission Error'
        elif 'not found' in error_lower or '404' in error_lower:
            return 'Not Found Error'
        elif 'timeout' in error_lower:
            return 'Timeout Error'
        elif 'language' in error_lower or 'transcript' in error_lower:
            return 'Transcript Error'
        elif 'format' in error_lower or 'parse' in error_lower:
            return 'Format Error'
        else:
            return 'Unknown Error'
    
    def is_retry_recommended(self) -> bool:
        """Determine if retry is recommended based on error type and retry count."""
        if self.transcript_status != TranscriptStatus.ERROR:
            return False
        
        if self.retry_count >= 3:
            return False
        
        error_type = self.get_error_classification()
        
        # Retry for temporary errors
        retryable_errors = ['Network Error', 'Timeout Error', 'Unknown Error']
        return error_type in retryable_errors
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "published_at": "2009-10-25T06:57:33Z",
                "statistics": {
                    "view_count": 1000000,
                    "like_count": 50000,
                    "duration_seconds": 212
                },
                "transcript_status": "success"
            }
        }
    }