"""Formatters for various output formats."""

import csv
import json
from abc import ABC, abstractmethod
from io import StringIO
from typing import List, Optional

from ..models.transcript import TranscriptData
from ..models.video import Video


class BaseFormatter(ABC):
    """Base formatter interface."""
    
    @abstractmethod
    def format(
        self,
        video: Video,
        transcript: TranscriptData,
        include_metadata: bool = True,
        include_timestamps: bool = False
    ) -> str:
        """Format transcript data.
        
        Args:
            video: Video object
            transcript: Transcript data
            include_metadata: Whether to include metadata
            include_timestamps: Whether to include timestamps
            
        Returns:
            Formatted string
        """
        pass


class TextFormatter(BaseFormatter):
    """Plain text formatter."""
    
    def format(
        self,
        video: Video,
        transcript: TranscriptData,
        include_metadata: bool = True,
        include_timestamps: bool = False
    ) -> str:
        """Format as plain text."""
        lines = []
        
        if include_metadata:
            lines.extend([
                f"Title: {video.title}",
                f"Video ID: {video.id}",
                f"URL: {video.url}",
                f"Published: {video.published_at.strftime('%Y-%m-%d %H:%M:%S') if video.published_at else 'Unknown'}",
                f"Duration: {transcript.formatted_duration}",
                f"Word Count: {transcript.word_count:,}",
                f"Character Count: {transcript.character_count:,}",
                f"Language: {transcript.language}",
                f"Source: {transcript.source.value}",
                f"Auto-generated: {'Yes' if transcript.auto_generated else 'No'}",
                "",
                "=" * 70,
                ""
            ])
        
        if include_timestamps:
            for segment in transcript.segments:
                lines.append(f"[{segment.formatted_time}] {segment.text}")
        else:
            lines.append(transcript.full_text)
        
        return "\n".join(lines)


class MarkdownFormatter(BaseFormatter):
    """Markdown formatter."""
    
    def format(
        self,
        video: Video,
        transcript: TranscriptData,
        include_metadata: bool = True,
        include_timestamps: bool = False
    ) -> str:
        """Format as markdown."""
        lines = []
        
        # Title
        lines.extend([
            f"# {video.title}",
            ""
        ])
        
        if include_metadata:
            lines.extend([
                "## Video Information",
                "",
                f"- **Video ID**: [{video.id}]({video.url})",
                f"- **Published**: {video.published_at.strftime('%Y-%m-%d %H:%M:%S') if video.published_at else 'Unknown'}",
                f"- **Duration**: {transcript.formatted_duration}",
                f"- **Channel**: {video.channel_title or 'Unknown'}",
                "",
                "## Transcript Information",
                "",
                f"- **Word Count**: {transcript.word_count:,}",
                f"- **Character Count**: {transcript.character_count:,}",
                f"- **Language**: {transcript.language}",
                f"- **Source**: {transcript.source.value}",
                f"- **Auto-generated**: {'Yes' if transcript.auto_generated else 'No'}",
                "",
                "---",
                "",
                "## Transcript",
                ""
            ])
        
        if include_timestamps:
            for segment in transcript.segments:
                # Make timestamp a link to the video at that time
                time_seconds = int(segment.start_time)
                timestamp_url = f"{video.url}&t={time_seconds}s"
                lines.append(f"**[{segment.formatted_time}]({timestamp_url})** {segment.text}")
                lines.append("")
        else:
            # Split into paragraphs for better readability
            paragraphs = transcript.full_text.split('\n\n')
            for paragraph in paragraphs:
                if paragraph.strip():
                    lines.append(paragraph.strip())
                    lines.append("")
        
        return "\n".join(lines)


class JsonFormatter(BaseFormatter):
    """JSON formatter."""
    
    def format(
        self,
        video: Video,
        transcript: TranscriptData,
        include_metadata: bool = True,
        include_timestamps: bool = False
    ) -> str:
        """Format as JSON."""
        data = {}
        
        if include_metadata:
            data["video"] = {
                "id": video.id,
                "title": video.title,
                "url": video.url,
                "published_at": video.published_at.isoformat() if video.published_at else None,
                "channel_id": video.channel_id,
                "channel_title": video.channel_title,
                "duration": video.formatted_duration,
                "statistics": {
                    "view_count": video.statistics.view_count if video.statistics else None,
                    "like_count": video.statistics.like_count if video.statistics else None,
                    "comment_count": video.statistics.comment_count if video.statistics else None
                } if video.statistics else None
            }
            
            data["transcript_info"] = {
                "language": transcript.language,
                "source": transcript.source.value,
                "auto_generated": transcript.auto_generated,
                "duration": transcript.duration,
                "segment_count": len(transcript.segments),
                "word_count": transcript.word_count,
                "character_count": transcript.character_count
            }
        
        if include_timestamps:
            data["segments"] = [
                {
                    "start_time": segment.start_time,
                    "duration": segment.duration,
                    "end_time": segment.end_time,
                    "text": segment.text
                }
                for segment in transcript.segments
            ]
        else:
            data["full_text"] = transcript.full_text
        
        return json.dumps(data, ensure_ascii=False, indent=2)


class CsvFormatter(BaseFormatter):
    """CSV formatter."""
    
    def format(
        self,
        video: Video,
        transcript: TranscriptData,
        include_metadata: bool = True,
        include_timestamps: bool = False
    ) -> str:
        """Format as CSV."""
        output = StringIO()
        
        if include_timestamps:
            # Create CSV with segments
            fieldnames = ['start_time', 'end_time', 'duration', 'text']
            if include_metadata:
                fieldnames = ['video_id', 'video_title'] + fieldnames
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for segment in transcript.segments:
                row = {
                    'start_time': segment.formatted_time,
                    'end_time': segment.formatted_end_time,
                    'duration': f"{segment.duration:.1f}",
                    'text': segment.text
                }
                
                if include_metadata:
                    row.update({
                        'video_id': video.id,
                        'video_title': video.title
                    })
                
                writer.writerow(row)
        else:
            # Create simple CSV with full text
            fieldnames = ['text']
            if include_metadata:
                fieldnames = [
                    'video_id', 'video_title', 'published_at', 'duration',
                    'word_count', 'language', 'source', 'auto_generated'
                ] + fieldnames
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            row = {'text': transcript.full_text}
            
            if include_metadata:
                row.update({
                    'video_id': video.id,
                    'video_title': video.title,
                    'published_at': video.published_at.strftime('%Y-%m-%d') if video.published_at else '',
                    'duration': transcript.formatted_duration,
                    'word_count': transcript.word_count,
                    'language': transcript.language,
                    'source': transcript.source.value,
                    'auto_generated': 'Yes' if transcript.auto_generated else 'No'
                })
            
            writer.writerow(row)
        
        return output.getvalue()


def get_formatter(format_type: str) -> Optional[BaseFormatter]:
    """Get formatter by format type.
    
    Args:
        format_type: Format type (txt, md, json, csv)
        
    Returns:
        Formatter instance or None
    """
    formatters = {
        'txt': TextFormatter(),
        'text': TextFormatter(),
        'md': MarkdownFormatter(),
        'markdown': MarkdownFormatter(),
        'json': JsonFormatter(),
        'csv': CsvFormatter()
    }
    
    return formatters.get(format_type.lower())