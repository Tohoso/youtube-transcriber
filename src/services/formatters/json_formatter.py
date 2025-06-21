import json
from typing import Dict, Any, List
from datetime import datetime
from .base_formatter import BaseFormatter
from src.models.channel import Channel
from src.models.video import Video
from src.models.transcript import TranscriptData


class JSONFormatter(BaseFormatter):
    """Format output as JSON files with complete metadata"""
    
    def format_transcript(self, transcript_data: TranscriptData, video: Video) -> str:
        """Format a single transcript as JSON"""
        data = self._video_to_dict(video)
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def format_video(self, video: Video) -> str:
        """Format a single video with its transcript as JSON"""
        return self.format_transcript(video.transcript_data, video)
    
    def format_channel(self, channel: Channel) -> str:
        """Format a channel with all its videos and transcripts as JSON"""
        channel_data = {
            "channel": {
                "id": channel.id,
                "title": channel.snippet.title,
                "description": channel.snippet.description,
                "custom_url": channel.snippet.custom_url,
                "published_at": self._format_datetime(channel.snippet.published_at),
                "country": channel.snippet.country,
                "statistics": {
                    "subscriber_count": channel.statistics.subscriber_count if channel.statistics else None,
                    "video_count": channel.statistics.video_count if channel.statistics else None,
                    "view_count": channel.statistics.view_count if channel.statistics else None,
                },
                "processing_stats": {
                    "total_videos": channel.processing_stats.total_videos,
                    "processed_videos": channel.processing_stats.processed_videos,
                    "successful_transcripts": channel.processing_stats.successful_transcripts,
                    "failed_transcripts": channel.processing_stats.failed_transcripts,
                    "skipped_videos": channel.processing_stats.skipped_videos,
                    "success_rate": channel.processing_stats.success_rate,
                    "completion_rate": channel.processing_stats.completion_rate,
                },
                "last_updated": self._format_datetime(channel.last_updated),
                "processing_started_at": self._format_datetime(channel.processing_started_at),
                "processing_completed_at": self._format_datetime(channel.processing_completed_at),
                "processing_duration": channel.processing_duration,
            },
            "videos": [self._video_to_dict(video) for video in channel.videos if video.transcript_data]
        }
        
        return json.dumps(channel_data, ensure_ascii=False, indent=2)
    
    def get_file_extension(self) -> str:
        """Get the file extension for JSON format"""
        return "json"
    
    def _video_to_dict(self, video: Video) -> Dict[str, Any]:
        """Convert video object to dictionary"""
        video_dict = {
            "id": video.id,
            "title": video.title,
            "url": str(video.url),
            "thumbnail_url": str(video.thumbnail_url) if video.thumbnail_url else None,
            "description": video.description,
            "published_at": self._format_datetime(video.published_at),
            "updated_at": self._format_datetime(video.updated_at),
            "privacy_status": video.privacy_status.value if video.privacy_status else None,
            "statistics": {
                "view_count": video.statistics.view_count if video.statistics else None,
                "like_count": video.statistics.like_count if video.statistics else None,
                "comment_count": video.statistics.comment_count if video.statistics else None,
                "duration_seconds": video.statistics.duration_seconds if video.statistics else None,
                "duration_formatted": video.duration_formatted,
            },
            "transcript_status": video.transcript_status.value,
            "tags": video.tags,
            "category_id": video.category_id,
            "language": video.language,
            "processed_at": self._format_datetime(video.processed_at),
            "processing_duration": video.processing_duration,
        }
        
        if video.transcript_data:
            transcript = video.transcript_data
            video_dict["transcript"] = {
                "language": transcript.language,
                "source": transcript.source.value,
                "auto_generated": transcript.auto_generated,
                "full_text": transcript.full_text,
                "total_duration": transcript.total_duration,
                "word_count": transcript.word_count,
                "character_count": transcript.character_count,
                "extracted_at": self._format_datetime(transcript.extracted_at),
                "metadata": transcript.metadata,
            }
            
            if self.include_timestamps:
                video_dict["transcript"]["segments"] = [
                    {
                        "text": segment.text,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "duration": segment.duration,
                    }
                    for segment in transcript.segments
                ]
        else:
            video_dict["error_message"] = video.error_message
            video_dict["retry_count"] = video.retry_count
        
        return video_dict
    
    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime to ISO string"""
        if dt:
            return dt.isoformat()
        return None