import os
import re
from pathlib import Path
from datetime import datetime
from typing import Union, Optional, Dict, Any
from src.models.channel import Channel
from src.models.video import Video
from src.models.enums import OutputFormat
from src.services.formatters import (
    TextFormatter,
    JSONFormatter,
    CSVFormatter,
    MarkdownFormatter
)


class FileWriter:
    """Handles file writing with template-based naming and directory management"""
    
    def __init__(
        self,
        output_directory: Path = Path("./output"),
        filename_template: str = "{date}_{title}_{video_id}",
        max_filename_length: int = 100,
        encoding: str = "utf-8",
        create_channel_folders: bool = True
    ):
        self.output_directory = Path(output_directory)
        self.filename_template = filename_template
        self.max_filename_length = max_filename_length
        self.encoding = encoding
        self.create_channel_folders = create_channel_folders
        
        # Formatter mapping
        self.formatters = {
            OutputFormat.TXT: TextFormatter,
            OutputFormat.JSON: JSONFormatter,
            OutputFormat.CSV: CSVFormatter,
            OutputFormat.MARKDOWN: MarkdownFormatter
        }
        
        # Ensure output directory exists
        self.output_directory.mkdir(parents=True, exist_ok=True)
    
    def write_video_transcript(
        self,
        video: Video,
        output_format: OutputFormat,
        channel: Optional[Channel] = None,
        include_metadata: bool = True,
        include_timestamps: bool = False
    ) -> Path:
        """Write a single video transcript to file"""
        if not video.transcript_data:
            raise ValueError(f"Video {video.id} has no transcript data")
        
        # Get formatter
        formatter_class = self.formatters.get(output_format)
        if not formatter_class:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        formatter = formatter_class(
            include_metadata=include_metadata,
            include_timestamps=include_timestamps
        )
        
        # Generate filename
        filename = self._generate_filename(
            video=video,
            channel=channel,
            extension=formatter.get_file_extension()
        )
        
        # Determine output path
        if self.create_channel_folders and channel:
            channel_folder = self._sanitize_filename(channel.snippet.title)
            output_path = self.output_directory / channel_folder / filename
        else:
            output_path = self.output_directory / filename
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Format and write content
        content = formatter.format_video(video)
        self._write_file(output_path, content)
        
        return output_path
    
    def write_channel_transcripts(
        self,
        channel: Channel,
        output_format: OutputFormat,
        include_metadata: bool = True,
        include_timestamps: bool = False,
        separate_files: bool = False
    ) -> Union[Path, list[Path]]:
        """Write channel transcripts to file(s)"""
        formatter_class = self.formatters.get(output_format)
        if not formatter_class:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        formatter = formatter_class(
            include_metadata=include_metadata,
            include_timestamps=include_timestamps
        )
        
        if separate_files:
            # Write each video to a separate file
            output_paths = []
            for video in channel.videos:
                if video.transcript_data:
                    try:
                        path = self.write_video_transcript(
                            video=video,
                            output_format=output_format,
                            channel=channel,
                            include_metadata=include_metadata,
                            include_timestamps=include_timestamps
                        )
                        output_paths.append(path)
                    except Exception as e:
                        logger.error(f"Error writing transcript for video {video.id}: {e}")
            return output_paths
        else:
            # Write all transcripts to a single file
            filename = self._generate_channel_filename(
                channel=channel,
                extension=formatter.get_file_extension()
            )
            
            if self.create_channel_folders:
                channel_folder = self._sanitize_filename(channel.snippet.title)
                output_path = self.output_directory / channel_folder / filename
            else:
                output_path = self.output_directory / filename
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = formatter.format_channel(channel)
            self._write_file(output_path, content)
            
            return output_path
    
    def write_metadata(
        self,
        channel: Channel,
        output_format: OutputFormat = OutputFormat.JSON
    ) -> Path:
        """Write channel metadata to file"""
        metadata = {
            "channel_id": channel.id,
            "channel_title": channel.snippet.title,
            "processing_started": channel.processing_started_at.isoformat() if channel.processing_started_at else None,
            "processing_completed": channel.processing_completed_at.isoformat() if channel.processing_completed_at else None,
            "processing_duration_seconds": channel.processing_duration,
            "total_videos": len(channel.videos),
            "processed_videos": channel.processing_stats.processed_videos,
            "successful_transcripts": channel.processing_stats.successful_transcripts,
            "failed_transcripts": channel.processing_stats.failed_transcripts,
            "success_rate": channel.processing_stats.success_rate,
            "videos_summary": []
        }
        
        for video in channel.videos:
            video_summary = {
                "id": video.id,
                "title": video.title,
                "status": video.transcript_status.value,
                "word_count": video.transcript_data.word_count if video.transcript_data else None,
                "error": video.error_message
            }
            metadata["videos_summary"].append(video_summary)
        
        if self.create_channel_folders:
            channel_folder = self._sanitize_filename(channel.snippet.title)
            output_path = self.output_directory / channel_folder / "metadata.json"
        else:
            output_path = self.output_directory / f"{channel.id}_metadata.json"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        content = json.dumps(metadata, ensure_ascii=False, indent=2)
        self._write_file(output_path, content)
        
        return output_path
    
    def _generate_filename(
        self,
        video: Video,
        channel: Optional[Channel] = None,
        extension: str = "txt"
    ) -> str:
        """Generate filename from template"""
        # Available template variables
        template_vars = {
            "video_id": video.id,
            "title": self._sanitize_filename(video.title),
            "channel_id": channel.id if channel else "",
            "channel_name": self._sanitize_filename(channel.snippet.title) if channel else "",
            "date": datetime.now().strftime("%Y%m%d"),
            "datetime": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "published_date": video.published_at.strftime("%Y%m%d") if video.published_at else "",
            "language": video.transcript_data.language if video.transcript_data else "",
            "duration": video.duration_formatted.replace(":", "") if video.duration_formatted else "",
        }
        
        # Format filename
        filename = self.filename_template
        for key, value in template_vars.items():
            filename = filename.replace(f"{{{key}}}", str(value))
        
        # Add extension
        filename = f"{filename}.{extension}"
        
        # Truncate if too long
        if len(filename) > self.max_filename_length:
            base_name = filename[:self.max_filename_length - len(extension) - 1]
            filename = f"{base_name}.{extension}"
        
        return filename
    
    def _generate_channel_filename(
        self,
        channel: Channel,
        extension: str = "txt"
    ) -> str:
        """Generate filename for channel-wide export"""
        template_vars = {
            "channel_id": channel.id,
            "channel_name": self._sanitize_filename(channel.snippet.title),
            "date": datetime.now().strftime("%Y%m%d"),
            "datetime": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "video_count": str(len(channel.videos)),
            "success_count": str(channel.processing_stats.successful_transcripts),
        }
        
        # Use a simplified template for channel files
        filename = "{date}_{channel_name}_all_transcripts"
        for key, value in template_vars.items():
            filename = filename.replace(f"{{{key}}}", str(value))
        
        return f"{filename}.{extension}"
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem-safe"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'[\s]+', '_', filename)  # Replace spaces with underscores
        filename = filename.strip('._')  # Remove leading/trailing dots and underscores
        
        # Limit length
        if len(filename) > 50:
            filename = filename[:50]
        
        return filename or "unnamed"
    
    def _write_file(self, path: Path, content: str) -> None:
        """Write content to file with specified encoding"""
        with open(path, 'w', encoding=self.encoding) as f:
            f.write(content)
        
        logger.info(f"Written: {path}")