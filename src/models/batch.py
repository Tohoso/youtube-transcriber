"""Batch processing data models."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any
from pydantic import BaseModel, Field


class BatchConfig(BaseModel):
    """Batch processing configuration."""
    
    max_channels: int = Field(3, ge=1, le=10, description="Maximum concurrent channels")
    channel_timeout_minutes: int = Field(60, ge=10, description="Timeout per channel in minutes")
    save_progress: bool = Field(True, description="Save progress for resume capability")
    progress_file: Path = Field(Path(".progress.json"), description="Progress file path")
    
    # Queue settings
    queue_size: int = Field(100, ge=10, description="Maximum queue size for videos")
    batch_size: int = Field(10, ge=1, description="Videos to process in batch")
    
    # Resource management
    memory_limit_mb: int = Field(1024, ge=256, description="Memory limit in MB")
    enable_streaming: bool = Field(True, description="Enable streaming for large channels")


class ChannelProgress(BaseModel):
    """Individual channel processing progress."""
    
    channel_id: str = Field(..., description="Channel identifier")
    channel_title: Optional[str] = Field(None, description="Channel title")
    status: Literal["pending", "processing", "completed", "failed", "partial"] = Field(
        "pending", 
        description="Processing status"
    )
    
    # Progress metrics
    processed_videos: int = Field(0, ge=0, description="Number of processed videos")
    successful_videos: int = Field(0, ge=0, description="Number of successful videos")
    failed_videos: int = Field(0, ge=0, description="Number of failed videos")
    total_videos: int = Field(0, ge=0, description="Total number of videos")
    
    # Tracking
    last_video_id: Optional[str] = Field(None, description="Last processed video ID")
    last_update: Optional[datetime] = Field(None, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start time")
    completed_at: Optional[datetime] = Field(None, description="Processing completion time")
    
    # Error tracking
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_count: int = Field(0, ge=0, description="Number of errors encountered")
    
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
        return (self.successful_videos / self.processed_videos) * 100
    
    @property
    def processing_duration(self) -> Optional[timedelta]:
        """Calculate processing duration."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.now()
        return end_time - self.started_at
    
    def update_progress(self, video_success: bool, video_id: str):
        """Update progress for a processed video."""
        self.processed_videos += 1
        if video_success:
            self.successful_videos += 1
        else:
            self.failed_videos += 1
        
        self.last_video_id = video_id
        self.last_update = datetime.now()


class BatchProcessingResult(BaseModel):
    """Overall batch processing result."""
    
    # Summary
    total_channels: int = Field(..., description="Total number of channels")
    successful_channels: List[str] = Field(default_factory=list, description="Successfully processed channels")
    failed_channels: Dict[str, str] = Field(default_factory=dict, description="Failed channels with error messages")
    partial_channels: Dict[str, Any] = Field(default_factory=dict, description="Partially processed channels")
    
    # Metrics
    total_videos_processed: int = Field(0, ge=0, description="Total videos processed across all channels")
    total_videos_successful: int = Field(0, ge=0, description="Total successful videos")
    total_videos_failed: int = Field(0, ge=0, description="Total failed videos")
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.now, description="Batch start time")
    completed_at: Optional[datetime] = Field(None, description="Batch completion time")
    total_duration: Optional[timedelta] = Field(None, description="Total processing duration")
    
    # Resource usage
    quota_usage: Dict[str, Any] = Field(default_factory=dict, description="API quota usage details")
    peak_memory_mb: Optional[float] = Field(None, description="Peak memory usage in MB")
    
    # Error summary
    error_summary: Optional[str] = Field(None, description="User-friendly error summary")
    error_categories: Dict[str, int] = Field(default_factory=dict, description="Error counts by category")
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_videos_processed == 0:
            return 0.0
        return (self.total_videos_successful / self.total_videos_processed) * 100
    
    @property
    def channel_success_rate(self) -> float:
        """Calculate channel-level success rate."""
        total = len(self.successful_channels) + len(self.failed_channels) + len(self.partial_channels)
        if total == 0:
            return 0.0
        return (len(self.successful_channels) / total) * 100
    
    def add_channel_result(self, channel_id: str, progress: ChannelProgress):
        """Add a channel result to the batch."""
        if progress.status == "completed" and progress.failed_videos == 0:
            self.successful_channels.append(channel_id)
        elif progress.status == "failed":
            self.failed_channels[channel_id] = progress.error_message or "Unknown error"
        else:
            # Partial success
            self.partial_channels[channel_id] = {
                "processed": progress.processed_videos,
                "successful": progress.successful_videos,
                "failed": progress.failed_videos,
                "total": progress.total_videos,
                "success_rate": progress.success_rate
            }
        
        # Update totals
        self.total_videos_processed += progress.processed_videos
        self.total_videos_successful += progress.successful_videos
        self.total_videos_failed += progress.failed_videos
    
    def finalize(self):
        """Finalize the batch result."""
        self.completed_at = datetime.now()
        if self.started_at:
            self.total_duration = self.completed_at - self.started_at


class ProcessingQueue(BaseModel):
    """Queue for managing video processing tasks."""
    
    channel_id: str = Field(..., description="Channel being processed")
    video_ids: List[str] = Field(default_factory=list, description="Queue of video IDs")
    current_index: int = Field(0, ge=0, description="Current processing index")
    batch_size: int = Field(10, ge=1, description="Batch size for processing")
    
    def get_next_batch(self) -> List[str]:
        """Get next batch of videos to process."""
        start = self.current_index
        end = min(start + self.batch_size, len(self.video_ids))
        batch = self.video_ids[start:end]
        self.current_index = end
        return batch
    
    @property
    def is_complete(self) -> bool:
        """Check if queue is complete."""
        return self.current_index >= len(self.video_ids)
    
    @property
    def remaining_videos(self) -> int:
        """Get number of remaining videos."""
        return max(0, len(self.video_ids) - self.current_index)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate queue progress percentage."""
        if not self.video_ids:
            return 0.0
        return (self.current_index / len(self.video_ids)) * 100