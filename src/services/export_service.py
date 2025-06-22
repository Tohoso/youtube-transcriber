"""Export service for managing transcript output in various formats."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from loguru import logger

from ..models.channel import Channel
from ..models.transcript import TranscriptData
from ..models.video import Video
from ..models.config import OutputConfig
from ..services.formatters import (
    TextFormatter,
    MarkdownFormatter,
    JSONFormatter as JsonFormatter,
    CSVFormatter as CsvFormatter
)
from ..repositories.file_repository import FileRepository


class ExportService:
    """Service for exporting transcripts in various formats."""
    
    def __init__(
        self,
        output_config: Optional[OutputConfig] = None,
        file_repo: Optional[FileRepository] = None
    ):
        """Initialize export service.
        
        Args:
            output_config: Output configuration
            file_repo: File repository for saving files
        """
        self.output_config = output_config or OutputConfig()
        self.file_repo = file_repo or FileRepository(base_path=Path(self.output_config.output_directory))
        
        # Initialize formatters
        self.formatters = {
            'txt': TextFormatter(),
            'text': TextFormatter(),
            'md': MarkdownFormatter(),
            'markdown': MarkdownFormatter(),
            'json': JsonFormatter(),
            'csv': CsvFormatter()
        }
    
    async def export_transcript(
        self,
        video: Video,
        transcript: TranscriptData,
        format_type: Optional[str] = None,
        output_dir: Optional[Path] = None
    ) -> Path:
        """Export a single transcript.
        
        Args:
            video: Video object
            transcript: Transcript data
            format_type: Output format (defaults to config)
            output_dir: Output directory (defaults to config)
            
        Returns:
            Path to the exported file
        """
        format_type = format_type or self.output_config.default_format
        output_dir = output_dir or Path(self.output_config.output_directory)
        
        # Get formatter
        formatter = self.formatters.get(format_type.lower())
        if not formatter:
            logger.warning(f"Unknown format {format_type}, using text format")
            formatter = self.formatters['txt']
        
        # Format content
        content = formatter.format(
            video=video,
            transcript=transcript,
            include_metadata=self.output_config.include_metadata,
            include_timestamps=self.output_config.include_timestamps
        )
        
        # Generate filename
        filename = self.generate_filename(video, format_type)
        
        # Save file
        file_path = await self.file_repo.save_content(
            content=content,
            filename=filename,
            subdirectory=output_dir
        )
        
        logger.info(f"Exported transcript to {file_path}")
        return file_path
    
    async def export_channel_transcripts(
        self,
        channel: Channel,
        format_type: Optional[str] = None,
        output_dir: Optional[Path] = None,
        create_summary: bool = True
    ) -> Dict[str, Path]:
        """Export all transcripts for a channel.
        
        Args:
            channel: Channel object with videos
            format_type: Output format
            output_dir: Output directory
            create_summary: Whether to create a summary file
            
        Returns:
            Dictionary mapping video IDs to exported file paths
        """
        format_type = format_type or self.output_config.default_format
        output_dir = output_dir or Path(self.output_config.output_directory)
        
        # Create channel subdirectory
        channel_dir = output_dir / self._sanitize_filename(channel.snippet.title)
        channel_dir.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        # Export individual transcripts
        for video in channel.videos:
            if video.transcript_data and video.has_transcript:
                try:
                    file_path = await self.export_transcript(
                        video=video,
                        transcript=video.transcript_data,
                        format_type=format_type,
                        output_dir=channel_dir
                    )
                    exported_files[video.id] = file_path
                except Exception as e:
                    logger.error(f"Failed to export transcript for {video.id}: {e}")
        
        # Create summary if requested
        if create_summary:
            summary_path = await self.export_channel_summary(
                channel=channel,
                exported_files=exported_files,
                output_dir=channel_dir
            )
            exported_files['_summary'] = summary_path
        
        logger.info(f"Exported {len(exported_files)} files for channel {channel.snippet.title}")
        return exported_files
    
    async def export_channel_summary(
        self,
        channel: Channel,
        exported_files: Dict[str, Path],
        output_dir: Path
    ) -> Path:
        """Export channel processing summary.
        
        Args:
            channel: Channel object
            exported_files: Dictionary of exported files
            output_dir: Output directory
            
        Returns:
            Path to summary file
        """
        # Generate summary data
        summary = {
            "channel": {
                "id": channel.id,
                "title": channel.snippet.title,
                "url": channel.url,
                "description": channel.snippet.description[:500] if channel.snippet.description else None,
                "subscriber_count": channel.statistics.subscriber_count if channel.statistics else None,
                "video_count": channel.statistics.video_count if channel.statistics else None
            },
            "processing": {
                "started_at": channel.processing_stats.processing_start_time.isoformat() if channel.processing_stats.processing_start_time else None,
                "completed_at": datetime.now().isoformat(),
                "statistics": channel.processing_stats.calculate_statistics_summary() if channel.processing_stats else {},
            },
            "videos": []
        }
        
        # Add video details
        for video in channel.videos:
            video_data = {
                "id": video.id,
                "title": video.title,
                "url": video.url,
                "published_at": video.published_at.isoformat() if video.published_at else None,
                "duration": video.duration_formatted,
                "transcript_status": video.transcript_status.value,
                "error_message": video.error_message,
                "exported_file": str(exported_files.get(video.id, ""))
            }
            
            if video.transcript_data:
                video_data.update({
                    "word_count": video.transcript_data.word_count,
                    "character_count": video.transcript_data.character_count,
                    "transcript_source": video.transcript_data.source.value,
                    "auto_generated": video.transcript_data.auto_generated
                })
            
            summary["videos"].append(video_data)
        
        # Save summary
        summary_filename = f"summary_{channel.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        summary_path = await self.file_repo.save_json(
            data=summary,
            filename=summary_filename,
            subdirectory=output_dir
        )
        
        logger.info(f"Created channel summary at {summary_path}")
        return summary_path
    
    def generate_filename(self, video: Video, format_type: str) -> str:
        """Generate filename based on template.
        
        Args:
            video: Video object
            format_type: File format
            
        Returns:
            Generated filename
        """
        template = self.output_config.filename_template
        
        # Replace template variables
        replacements = {
            "{video_id}": video.id,
            "{title}": self._sanitize_filename(video.title),
            "{date}": video.published_at.strftime("%Y%m%d") if video.published_at else "unknown",
            "{channel_id}": video.channel_id or "unknown",
            "{duration}": str(video.statistics.duration_seconds) if video.statistics and video.statistics.duration_seconds else "0"
        }
        
        filename = template
        for key, value in replacements.items():
            filename = filename.replace(key, value)
        
        # Add extension
        if format_type.lower() in ['md', 'markdown']:
            ext = 'md'
        elif format_type.lower() in ['txt', 'text']:
            ext = 'txt'
        else:
            ext = format_type.lower()
        
        filename = f"{filename}.{ext}"
        
        # Truncate if too long
        max_length = self.output_config.max_filename_length
        if len(filename) > max_length:
            base = filename[:max_length - len(ext) - 1]
            filename = f"{base}.{ext}"
        
        return filename
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filename.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        import re
        
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')
        
        # Replace spaces with underscores
        text = text.replace(' ', '_')
        
        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)
        
        # Remove leading/trailing underscores
        text = text.strip('_')
        
        # Limit length
        return text[:50]
    
    async def export_batch(
        self,
        videos_with_transcripts: List[tuple[Video, TranscriptData]],
        format_type: Optional[str] = None,
        output_dir: Optional[Path] = None,
        group_by_date: bool = False
    ) -> Dict[str, Path]:
        """Export multiple transcripts in batch.
        
        Args:
            videos_with_transcripts: List of (video, transcript) tuples
            format_type: Output format
            output_dir: Output directory
            group_by_date: Whether to group files by date
            
        Returns:
            Dictionary mapping video IDs to file paths
        """
        format_type = format_type or self.output_config.default_format
        output_dir = output_dir or Path(self.output_config.output_directory)
        
        exported_files = {}
        
        for video, transcript in videos_with_transcripts:
            try:
                # Determine subdirectory
                if group_by_date and video.published_at:
                    sub_dir = output_dir / video.published_at.strftime("%Y-%m")
                else:
                    sub_dir = output_dir
                
                # Export transcript
                file_path = await self.export_transcript(
                    video=video,
                    transcript=transcript,
                    format_type=format_type,
                    output_dir=sub_dir
                )
                
                exported_files[video.id] = file_path
                
            except Exception as e:
                logger.error(f"Failed to export transcript for {video.id}: {e}")
        
        logger.info(f"Exported {len(exported_files)} transcripts in batch")
        return exported_files
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats.
        
        Returns:
            List of format names
        """
        return list(self.formatters.keys())