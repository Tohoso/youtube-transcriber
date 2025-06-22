"""yt-dlp repository for transcript extraction fallback."""

import asyncio
import json
from pathlib import Path
from typing import Optional
from loguru import logger

from ..models.transcript import TranscriptData, TranscriptSegment, TranscriptSource


class YtDlpRepository:
    """Repository for yt-dlp based transcript extraction."""
    
    def __init__(self, temp_dir: Optional[Path] = None):
        """Initialize yt-dlp repository.
        
        Args:
            temp_dir: Temporary directory for downloads
        """
        self.temp_dir = temp_dir or Path("/tmp/yt-dlp-transcripts")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def get_transcript(
        self,
        video_id: str,
        language: str = "ja"
    ) -> Optional[TranscriptData]:
        """Get transcript using yt-dlp.
        
        Args:
            video_id: YouTube video ID
            language: Preferred language code
            
        Returns:
            TranscriptData if successful, None otherwise
        """
        try:
            # Prepare yt-dlp command
            output_path = self.temp_dir / f"{video_id}_{language}"
            
            cmd = [
                "yt-dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "--skip-download",
                "--write-sub",
                "--write-auto-sub",
                f"--sub-lang={language}",
                "--sub-format=json3",
                "-o", str(output_path),
                "--quiet",
                "--no-warnings"
            ]
            
            # Execute yt-dlp
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"yt-dlp failed for {video_id}: {stderr.decode()}")
                return None
            
            # Find and parse subtitle file
            subtitle_files = list(output_path.parent.glob(f"{video_id}*.{language}.json3"))
            if not subtitle_files:
                # Try auto-generated subtitles
                subtitle_files = list(output_path.parent.glob(f"{video_id}*.{language}.json3"))
            
            if not subtitle_files:
                logger.debug(f"No subtitle files found for {video_id}")
                return None
            
            # Parse the subtitle file
            subtitle_file = subtitle_files[0]
            transcript_data = self._parse_json3_subtitle(subtitle_file, video_id, language)
            
            # Clean up temporary files
            for file in subtitle_files:
                file.unlink()
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error getting transcript with yt-dlp for {video_id}: {e}")
            return None
    
    def _parse_json3_subtitle(
        self,
        subtitle_file: Path,
        video_id: str,
        language: str
    ) -> Optional[TranscriptData]:
        """Parse JSON3 subtitle format.
        
        Args:
            subtitle_file: Path to subtitle file
            video_id: Video ID
            language: Language code
            
        Returns:
            TranscriptData if successful
        """
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            segments = []
            for event in data.get("events", []):
                if "segs" not in event:
                    continue
                
                text_parts = []
                for seg in event["segs"]:
                    if "utf8" in seg:
                        text_parts.append(seg["utf8"])
                
                if text_parts:
                    segment = TranscriptSegment(
                        text=" ".join(text_parts),
                        start_time=event.get("tStartMs", 0) / 1000.0,
                        duration=event.get("dDurationMs", 0) / 1000.0
                    )
                    segments.append(segment)
            
            if not segments:
                return None
            
            # Check if auto-generated
            auto_generated = "auto" in subtitle_file.name.lower()
            
            # Generate full text from segments
            full_text = ' '.join(segment.text for segment in segments)
            
            return TranscriptData(
                video_id=video_id,
                language=language,
                source=TranscriptSource.YT_DLP,
                auto_generated=auto_generated,
                segments=segments,
                full_text=full_text
            )
            
        except Exception as e:
            logger.error(f"Error parsing subtitle file {subtitle_file}: {e}")
            return None
    
    async def check_availability(self) -> bool:
        """Check if yt-dlp is available.
        
        Returns:
            True if yt-dlp is available
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "yt-dlp", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
            
        except FileNotFoundError:
            logger.warning("yt-dlp not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Error checking yt-dlp availability: {e}")
            return False