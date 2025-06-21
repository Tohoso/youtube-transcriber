from typing import List
from datetime import datetime
from .base_formatter import BaseFormatter
from src.models.channel import Channel
from src.models.video import Video
from src.models.transcript import TranscriptData


class TextFormatter(BaseFormatter):
    """Format output as plain text files"""
    
    def format_transcript(self, transcript_data: TranscriptData, video: Video) -> str:
        """Format a single transcript as plain text"""
        lines = []
        
        if self.include_metadata:
            lines.extend([
                f"Title: {video.title}",
                f"Video ID: {video.id}",
                f"URL: {video.url}",
                f"Published: {video.published_at.strftime('%Y-%m-%d %H:%M:%S') if video.published_at else 'Unknown'}",
                f"Duration: {video.duration_formatted or 'Unknown'}",
                f"Language: {transcript_data.language}",
                f"Auto-generated: {'Yes' if transcript_data.auto_generated else 'No'}",
                f"Word count: {transcript_data.word_count}",
                f"Character count: {transcript_data.character_count}",
                "-" * 80,
                ""
            ])
        
        if self.include_timestamps:
            for segment in transcript_data.segments:
                timestamp = self._format_timestamp(segment.start_time)
                lines.append(f"[{timestamp}] {segment.text}")
        else:
            lines.append(transcript_data.full_text)
        
        return "\n".join(lines)
    
    def format_video(self, video: Video) -> str:
        """Format a single video with its transcript"""
        if video.transcript_data:
            return self.format_transcript(video.transcript_data, video)
        else:
            lines = [
                f"Title: {video.title}",
                f"Video ID: {video.id}",
                f"URL: {video.url}",
                f"Status: {video.transcript_status}",
            ]
            if video.error_message:
                lines.append(f"Error: {video.error_message}")
            return "\n".join(lines)
    
    def format_channel(self, channel: Channel) -> str:
        """Format a channel with all its videos and transcripts"""
        lines = [
            f"Channel: {channel.snippet.title}",
            f"Channel ID: {channel.id}",
            f"Total videos: {len(channel.videos)}",
            f"Processed videos: {channel.processing_stats.processed_videos}",
            f"Successful transcripts: {channel.processing_stats.successful_transcripts}",
            f"Success rate: {channel.processing_stats.success_rate:.1%}",
            "=" * 80,
            ""
        ]
        
        for i, video in enumerate(channel.videos, 1):
            if video.transcript_data:
                lines.append(f"\n[Video {i}/{len(channel.videos)}]")
                lines.append(self.format_video(video))
                lines.append("\n" + "=" * 80 + "\n")
        
        return "\n".join(lines)
    
    def get_file_extension(self) -> str:
        """Get the file extension for text format"""
        return "txt"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"