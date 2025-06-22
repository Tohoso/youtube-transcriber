from abc import ABC, abstractmethod
from typing import List, Union
from pathlib import Path
from src.models.channel import Channel
from src.models.video import Video
from src.models.transcript import TranscriptData


class BaseFormatter(ABC):
    """Base abstract class for all formatters"""
    
    def __init__(self, include_metadata: bool = True, include_timestamps: bool = False):
        self.include_metadata = include_metadata
        self.include_timestamps = include_timestamps
    
    def format(self, video: Video, transcript: TranscriptData, include_metadata: bool = True, include_timestamps: bool = False) -> str:
        """Format a video with its transcript - adapter method for export service"""
        # Update instance settings if provided
        self.include_metadata = include_metadata
        self.include_timestamps = include_timestamps
        
        # Store transcript data in video temporarily
        video.transcript_data = transcript
        
        # Use the format_video method
        return self.format_video(video)
    
    @abstractmethod
    def format_transcript(self, transcript_data: TranscriptData, video: Video) -> str:
        """Format a single transcript"""
        pass
    
    @abstractmethod
    def format_video(self, video: Video) -> str:
        """Format a single video with its transcript"""
        pass
    
    @abstractmethod
    def format_channel(self, channel: Channel) -> str:
        """Format a channel with all its videos and transcripts"""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get the file extension for this format"""
        pass