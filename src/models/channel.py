"""Channel data models."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator

from .transcript import TranscriptStatus
from .video import Video


class ChannelStatistics(BaseModel):
    """Channel statistics."""
    
    subscriber_count: Optional[int] = Field(None, description="Subscriber count", ge=0)
    video_count: Optional[int] = Field(None, description="Video count", ge=0)
    view_count: Optional[int] = Field(None, description="Total view count", ge=0)


class ChannelSnippet(BaseModel):
    """Channel basic information."""
    
    title: str = Field(..., description="Channel name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Channel description", max_length=5000)
    custom_url: Optional[str] = Field(None, description="Custom URL")
    published_at: Optional[datetime] = Field(None, description="Creation date")
    thumbnail_url: Optional[AnyHttpUrl] = Field(None, description="Icon URL")
    banner_url: Optional[AnyHttpUrl] = Field(None, description="Banner URL")
    country: Optional[str] = Field(None, description="Country code", pattern=r'^[A-Z]{2}$')
    default_language: Optional[str] = Field(None, description="Default language", pattern=r'^[a-z]{2}$')


class ProcessingStatistics(BaseModel):
    """Processing statistics with enhanced metrics and error tracking."""
    
    total_videos: int = Field(0, description="Total video count", ge=0)
    processed_videos: int = Field(0, description="Processed video count", ge=0)
    successful_videos: int = Field(0, description="Successful video count", ge=0)
    failed_videos: int = Field(0, description="Failed video count", ge=0)
    skipped_videos: int = Field(0, description="Skipped video count", ge=0)
    
    # Legacy fields for backward compatibility
    successful_transcripts: int = Field(0, description="Successful transcript count", ge=0)
    failed_transcripts: int = Field(0, description="Failed transcript count", ge=0)
    
    # Time tracking
    processing_start_time: Optional[datetime] = Field(None, description="Processing start time")
    last_update_time: Optional[datetime] = Field(None, description="Last statistics update time")
    average_processing_time: float = Field(0.0, description="Average processing time per video in seconds", ge=0.0)
    
    # Error statistics
    error_statistics: Dict[str, int] = Field(
        default_factory=dict, 
        description="Error counts by error type"
    )
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_videos == 0:
            return 0.0
        return (self.processed_videos / self.total_videos) * 100
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.processed_videos == 0:
            return 0.0
        return self.successful_videos / self.processed_videos
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion rate."""
        if self.total_videos == 0:
            return 0.0
        return self.processed_videos / self.total_videos
    
    @property
    def estimated_time_remaining(self) -> Optional[timedelta]:
        """Calculate estimated time remaining based on average processing time."""
        if self.processed_videos == 0 or self.average_processing_time == 0:
            return None
        
        remaining_videos = self.total_videos - self.processed_videos
        if remaining_videos <= 0:
            return timedelta(seconds=0)
        
        estimated_seconds = remaining_videos * self.average_processing_time
        return timedelta(seconds=estimated_seconds)
    
    def update_error_statistics(self, error_type: str):
        """Update error statistics with a new error occurrence."""
        if error_type in self.error_statistics:
            self.error_statistics[error_type] += 1
        else:
            self.error_statistics[error_type] = 1
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of error statistics."""
        if not self.error_statistics:
            return {"total_errors": 0, "error_types": {}}
        
        total_errors = sum(self.error_statistics.values())
        error_percentages = {
            error_type: (count / total_errors) * 100
            for error_type, count in self.error_statistics.items()
        }
        
        return {
            "total_errors": total_errors,
            "error_types": self.error_statistics,
            "error_percentages": error_percentages,
            "most_common_error": max(self.error_statistics.items(), key=lambda x: x[1])[0] if self.error_statistics else None
        }
    
    def update_processing_time(self, video_processing_time: float):
        """Update average processing time with a new video processing time."""
        if self.processed_videos == 0:
            self.average_processing_time = video_processing_time
        else:
            # Calculate new average incrementally
            total_time = self.average_processing_time * (self.processed_videos - 1)
            self.average_processing_time = (total_time + video_processing_time) / self.processed_videos
        
        self.last_update_time = datetime.now()
    
    def get_processing_rate(self) -> Optional[float]:
        """Calculate videos processed per hour."""
        if not self.processing_start_time or self.processed_videos == 0:
            return None
        
        elapsed_time = (datetime.now() - self.processing_start_time).total_seconds()
        if elapsed_time <= 0:
            return None
        
        return (self.processed_videos / elapsed_time) * 3600  # videos per hour
    
    def calculate_statistics_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive statistics summary."""
        summary = {
            "progress": {
                "total_videos": self.total_videos,
                "processed_videos": self.processed_videos,
                "successful_videos": self.successful_videos,
                "failed_videos": self.failed_videos,
                "skipped_videos": self.skipped_videos,
                "progress_percentage": self.progress_percentage,
                "completion_rate": self.completion_rate,
                "success_rate": self.success_rate
            },
            "time_metrics": {
                "processing_start_time": self.processing_start_time,
                "last_update_time": self.last_update_time,
                "average_processing_time": self.average_processing_time,
                "estimated_time_remaining": self.estimated_time_remaining,
                "processing_rate": self.get_processing_rate()
            },
            "error_analysis": self.get_error_summary()
        }
        
        return summary


class Channel(BaseModel):
    """Channel information."""
    
    id: str = Field(..., description="Channel ID", pattern=r'^UC[a-zA-Z0-9_-]{22}$')
    snippet: ChannelSnippet = Field(..., description="Basic information")
    statistics: Optional[ChannelStatistics] = Field(None, description="Statistics")
    
    videos: List[Video] = Field(default_factory=list, description="Video list")
    
    processing_stats: ProcessingStatistics = Field(
        default_factory=ProcessingStatistics, 
        description="Processing statistics"
    )
    
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update time")
    processing_started_at: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")
    
    @field_validator('videos')
    @classmethod
    def update_processing_stats(cls, v: List[Video], info) -> List[Video]:
        """Update processing statistics from video list."""
        if 'processing_stats' in info.data:
            stats = info.data['processing_stats']
            stats.total_videos = len(v)
            stats.processed_videos = len([vid for vid in v if vid.transcript_status != TranscriptStatus.PENDING])
            
            # Update both new and legacy fields for backward compatibility
            stats.successful_videos = len([vid for vid in v if vid.transcript_status == TranscriptStatus.SUCCESS])
            stats.successful_transcripts = stats.successful_videos
            
            stats.failed_videos = len([vid for vid in v if vid.transcript_status == TranscriptStatus.ERROR])
            stats.failed_transcripts = stats.failed_videos
            
            stats.skipped_videos = len([vid for vid in v if vid.transcript_status == TranscriptStatus.SKIPPED])
            
            # Update error statistics from failed videos
            for video in v:
                if video.transcript_status == TranscriptStatus.ERROR and video.error_message:
                    # Extract error type from error message
                    error_type = video.error_message.split(':')[0] if ':' in video.error_message else 'Unknown Error'
                    stats.update_error_statistics(error_type)
            
            # Update processing time if videos have processing_duration
            for video in v:
                if video.processing_duration and video.processing_duration > 0:
                    stats.update_processing_time(video.processing_duration)
        return v
    
    @property
    def url(self) -> str:
        """Generate channel URL."""
        return f"https://www.youtube.com/channel/{self.id}"
    
    @property
    def processing_duration(self) -> Optional[float]:
        """Calculate processing duration."""
        if not self.processing_started_at or not self.processing_completed_at:
            return None
        return (self.processing_completed_at - self.processing_started_at).total_seconds()
    
    def get_videos_by_status(self, status: TranscriptStatus) -> List[Video]:
        """Get videos by status."""
        return [video for video in self.videos if video.transcript_status == status]
    
    def update_processing_statistics(self):
        """Manually trigger processing statistics update."""
        # Force the field validator to run by reassigning videos
        self.videos = self.videos
    
    def get_statistics_report(self) -> str:
        """Generate a formatted statistics report."""
        stats = self.processing_stats
        report = []
        
        report.append(f"Processing Statistics for {self.snippet.title}")
        report.append("=" * 50)
        report.append(f"Total Videos: {stats.total_videos}")
        report.append(f"Processed: {stats.processed_videos} ({stats.progress_percentage:.1f}%)")
        report.append(f"Successful: {stats.successful_videos}")
        report.append(f"Failed: {stats.failed_videos}")
        report.append(f"Skipped: {stats.skipped_videos}")
        report.append(f"Success Rate: {stats.success_rate:.1%}")
        
        if stats.estimated_time_remaining:
            remaining = stats.estimated_time_remaining
            hours, remainder = divmod(remaining.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            report.append(f"Estimated Time Remaining: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        
        if stats.error_statistics:
            report.append("\nError Analysis:")
            error_summary = stats.get_error_summary()
            for error_type, count in error_summary['error_types'].items():
                percentage = error_summary['error_percentages'][error_type]
                report.append(f"  - {error_type}: {count} ({percentage:.1f}%)")
        
        return "\n".join(report)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "UCXuqSBlHAE6Xw-yeJA0Tunw",
                "snippet": {
                    "title": "Example Channel",
                    "description": "This is an example channel",
                    "published_at": "2020-01-01T00:00:00Z"
                },
                "statistics": {
                    "subscriber_count": 1000000,
                    "video_count": 500
                },
                "processing_stats": {
                    "total_videos": 500,
                    "processed_videos": 450,
                    "successful_videos": 400,
                    "failed_videos": 40,
                    "skipped_videos": 10,
                    "successful_transcripts": 400,
                    "failed_transcripts": 40,
                    "average_processing_time": 5.2,
                    "error_statistics": {
                        "Network Error": 25,
                        "Transcript Error": 15
                    }
                }
            }
        }
    }