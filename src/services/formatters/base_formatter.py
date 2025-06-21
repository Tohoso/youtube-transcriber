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