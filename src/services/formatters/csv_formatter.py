import csv
import io
from typing import List
from datetime import datetime
from .base_formatter import BaseFormatter
from src.models.channel import Channel
from src.models.video import Video
from src.models.transcript import TranscriptData


class CSVFormatter(BaseFormatter):
    """Format output as CSV files for analysis"""
    
    def format_transcript(self, transcript_data: TranscriptData, video: Video) -> str:
        """Format a single transcript as CSV"""
        output = io.StringIO()
        
        if self.include_timestamps:
            fieldnames = ['timestamp', 'text', 'duration', 'video_id', 'video_title']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for segment in transcript_data.segments:
                writer.writerow({
                    'timestamp': self._format_timestamp(segment.start_time),
                    'text': segment.text,
                    'duration': segment.duration,
                    'video_id': video.id,
                    'video_title': video.title
                })
        else:
            fieldnames = [
                'video_id', 'title', 'url', 'published_at', 'duration_seconds',
                'view_count', 'like_count', 'comment_count', 'language',
                'auto_generated', 'word_count', 'character_count', 'full_text'
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            writer.writerow({
                'video_id': video.id,
                'title': video.title,
                'url': str(video.url),
                'published_at': video.published_at.isoformat() if video.published_at else '',
                'duration_seconds': video.statistics.duration_seconds if video.statistics else '',
                'view_count': video.statistics.view_count if video.statistics else '',
                'like_count': video.statistics.like_count if video.statistics else '',
                'comment_count': video.statistics.comment_count if video.statistics else '',
                'language': transcript_data.language,
                'auto_generated': 'Yes' if transcript_data.auto_generated else 'No',
                'word_count': transcript_data.word_count,
                'character_count': transcript_data.character_count,
                'full_text': transcript_data.full_text
            })
        
        return output.getvalue()
    
    def format_video(self, video: Video) -> str:
        """Format a single video with its transcript as CSV"""
        if video.transcript_data:
            return self.format_transcript(video.transcript_data, video)
        else:
            output = io.StringIO()
            fieldnames = ['video_id', 'title', 'url', 'status', 'error_message']
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            writer.writerow({
                'video_id': video.id,
                'title': video.title,
                'url': str(video.url),
                'status': video.transcript_status.value,
                'error_message': video.error_message or ''
            })
            
            return output.getvalue()
    
    def format_channel(self, channel: Channel) -> str:
        """Format a channel with all its videos and transcripts as CSV"""
        output = io.StringIO()
        
        fieldnames = [
            'channel_id', 'channel_name', 'video_id', 'title', 'url', 
            'published_at', 'duration_seconds', 'view_count', 'like_count', 
            'comment_count', 'transcript_status', 'language', 'auto_generated',
            'word_count', 'character_count', 'error_message'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for video in channel.videos:
            row = {
                'channel_id': channel.id,
                'channel_name': channel.snippet.title,
                'video_id': video.id,
                'title': video.title,
                'url': str(video.url),
                'published_at': video.published_at.isoformat() if video.published_at else '',
                'duration_seconds': video.statistics.duration_seconds if video.statistics else '',
                'view_count': video.statistics.view_count if video.statistics else '',
                'like_count': video.statistics.like_count if video.statistics else '',
                'comment_count': video.statistics.comment_count if video.statistics else '',
                'transcript_status': video.transcript_status.value,
                'error_message': video.error_message or ''
            }
            
            if video.transcript_data:
                row.update({
                    'language': video.transcript_data.language,
                    'auto_generated': 'Yes' if video.transcript_data.auto_generated else 'No',
                    'word_count': video.transcript_data.word_count,
                    'character_count': video.transcript_data.character_count
                })
            
            writer.writerow(row)
        
        summary_output = io.StringIO()
        summary_writer = csv.writer(summary_output)
        summary_writer.writerow(['Channel Summary'])
        summary_writer.writerow(['Total Videos', len(channel.videos)])
        summary_writer.writerow(['Processed Videos', channel.processing_stats.processed_videos])
        summary_writer.writerow(['Successful Transcripts', channel.processing_stats.successful_transcripts])
        summary_writer.writerow(['Failed Transcripts', channel.processing_stats.failed_transcripts])
        summary_writer.writerow(['Success Rate', f"{channel.processing_stats.success_rate:.1%}"])
        summary_writer.writerow([])
        
        return summary_output.getvalue() + output.getvalue()
    
    def get_file_extension(self) -> str:
        """Get the file extension for CSV format"""
        return "csv"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"