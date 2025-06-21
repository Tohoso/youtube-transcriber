from typing import List
from datetime import datetime
from .base_formatter import BaseFormatter
from src.models.channel import Channel
from src.models.video import Video
from src.models.transcript import TranscriptData


class MarkdownFormatter(BaseFormatter):
    """Format output as Markdown documents"""
    
    def format_transcript(self, transcript_data: TranscriptData, video: Video) -> str:
        """Format a single transcript as Markdown"""
        lines = []
        
        # Video title as header
        lines.append(f"# {video.title}\n")
        
        # Metadata section
        if self.include_metadata:
            lines.extend([
                "## Video Information\n",
                f"- **Video ID**: `{video.id}`",
                f"- **URL**: [{video.url}]({video.url})",
                f"- **Published**: {video.published_at.strftime('%Y-%m-%d %H:%M:%S') if video.published_at else 'Unknown'}",
                f"- **Duration**: {video.duration_formatted or 'Unknown'}",
                ""
            ])
            
            if video.description:
                lines.extend([
                    "### Description\n",
                    f"{video.description}\n"
                ])
            
            if video.statistics:
                lines.extend([
                    "### Statistics\n",
                    f"- **Views**: {video.statistics.view_count:,}" if video.statistics.view_count else "- **Views**: N/A",
                    f"- **Likes**: {video.statistics.like_count:,}" if video.statistics.like_count else "- **Likes**: N/A",
                    f"- **Comments**: {video.statistics.comment_count:,}" if video.statistics.comment_count else "- **Comments**: N/A",
                    ""
                ])
            
            lines.extend([
                "## Transcript Information\n",
                f"- **Language**: {transcript_data.language}",
                f"- **Auto-generated**: {'Yes' if transcript_data.auto_generated else 'No'}",
                f"- **Source**: {transcript_data.source.value}",
                f"- **Word count**: {transcript_data.word_count:,}",
                f"- **Character count**: {transcript_data.character_count:,}",
                f"- **Extracted at**: {transcript_data.extracted_at.strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ])
        
        # Transcript content
        lines.append("## Transcript\n")
        
        if self.include_timestamps:
            for segment in transcript_data.segments:
                timestamp = self._format_timestamp(segment.start_time)
                lines.append(f"**[{timestamp}]** {segment.text}\n")
        else:
            # Format text into paragraphs
            text_parts = transcript_data.full_text.split('. ')
            paragraph = []
            
            for part in text_parts:
                paragraph.append(part + '.')
                if len(paragraph) >= 3:  # Create paragraph every 3 sentences
                    lines.append(' '.join(paragraph) + '\n')
                    paragraph = []
            
            if paragraph:
                lines.append(' '.join(paragraph))
        
        return "\n".join(lines)
    
    def format_video(self, video: Video) -> str:
        """Format a single video with its transcript as Markdown"""
        if video.transcript_data:
            return self.format_transcript(video.transcript_data, video)
        else:
            lines = [
                f"# {video.title}\n",
                "## Video Information\n",
                f"- **Video ID**: `{video.id}`",
                f"- **URL**: [{video.url}]({video.url})",
                f"- **Status**: {video.transcript_status.value}",
            ]
            
            if video.error_message:
                lines.extend([
                    "",
                    "### Error\n",
                    f"```\n{video.error_message}\n```"
                ])
            
            return "\n".join(lines)
    
    def format_channel(self, channel: Channel) -> str:
        """Format a channel with all its videos and transcripts as Markdown"""
        lines = [
            f"# {channel.snippet.title} - Transcript Collection\n",
            "## Channel Information\n",
            f"- **Channel ID**: `{channel.id}`",
            f"- **Channel URL**: [Visit Channel](https://www.youtube.com/channel/{channel.id})",
        ]
        
        if channel.snippet.description:
            lines.extend([
                f"- **Description**: {channel.snippet.description[:200]}..." if len(channel.snippet.description) > 200 else f"- **Description**: {channel.snippet.description}"
            ])
        
        if channel.statistics:
            lines.extend([
                "",
                "### Channel Statistics\n",
                f"- **Subscribers**: {channel.statistics.subscriber_count:,}" if channel.statistics.subscriber_count else "- **Subscribers**: N/A",
                f"- **Total Videos**: {channel.statistics.video_count:,}" if channel.statistics.video_count else "- **Total Videos**: N/A",
                f"- **Total Views**: {channel.statistics.view_count:,}" if channel.statistics.view_count else "- **Total Views**: N/A",
            ])
        
        lines.extend([
            "",
            "## Processing Summary\n",
            f"- **Total videos processed**: {channel.processing_stats.processed_videos}/{len(channel.videos)}",
            f"- **Successful transcripts**: {channel.processing_stats.successful_transcripts}",
            f"- **Failed transcripts**: {channel.processing_stats.failed_transcripts}",
            f"- **Success rate**: {channel.processing_stats.success_rate:.1%}",
            f"- **Last updated**: {channel.last_updated.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ])
        
        if channel.processing_duration:
            duration_mins = channel.processing_duration / 60
            lines.append(f"- **Processing duration**: {duration_mins:.1f} minutes\n")
        
        # Table of contents
        lines.extend([
            "## Table of Contents\n"
        ])
        
        videos_with_transcripts = [v for v in channel.videos if v.transcript_data]
        for i, video in enumerate(videos_with_transcripts, 1):
            lines.append(f"{i}. [{video.title}](#{self._slugify(video.title)})")
        
        lines.extend(["", "---", ""])
        
        # Individual video transcripts
        for i, video in enumerate(videos_with_transcripts, 1):
            lines.extend([
                f"<a name=\"{self._slugify(video.title)}\"></a>",
                self.format_video(video),
                "",
                "---",
                ""
            ])
        
        return "\n".join(lines)
    
    def get_file_extension(self) -> str:
        """Get the file extension for Markdown format"""
        return "md"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text[:50]  # Limit length for anchor links