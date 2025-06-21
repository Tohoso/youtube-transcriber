"""Integration tests for ProcessingStatistics functionality."""

import asyncio
from datetime import datetime, timedelta

import pytest

from src.models.channel import Channel, ChannelSnippet, ProcessingStatistics
from src.models.transcript import TranscriptStatus
from src.models.video import Video


class TestProcessingStatisticsIntegration:
    """Test ProcessingStatistics integration with Channel and Video models."""
    
    @pytest.mark.integration
    def test_statistics_auto_update_on_video_addition(self, mock_channel_snippet):
        """Test that statistics automatically update when videos are added."""
        # Create channel with no videos
        channel = Channel(
            id="UCXuqSBlHAE6Xw-yeJA0Tunw",
            snippet=mock_channel_snippet,
            videos=[]
        )
        
        assert channel.processing_stats.total_videos == 0
        assert channel.processing_stats.processed_videos == 0
        
        # Add videos with different statuses
        videos = [
            Video(id="video1", title="Test 1", url="https://youtube.com/watch?v=1", 
                  transcript_status=TranscriptStatus.SUCCESS),
            Video(id="video2", title="Test 2", url="https://youtube.com/watch?v=2", 
                  transcript_status=TranscriptStatus.ERROR, error_message="Network Error: Timeout"),
            Video(id="video3", title="Test 3", url="https://youtube.com/watch?v=3", 
                  transcript_status=TranscriptStatus.PENDING),
            Video(id="video4", title="Test 4", url="https://youtube.com/watch?v=4", 
                  transcript_status=TranscriptStatus.SKIPPED),
        ]
        
        channel.videos = videos
        
        # Verify statistics updated correctly
        assert channel.processing_stats.total_videos == 4
        assert channel.processing_stats.processed_videos == 3  # All except PENDING
        assert channel.processing_stats.successful_videos == 1
        assert channel.processing_stats.failed_videos == 1
        assert channel.processing_stats.skipped_videos == 1
        assert channel.processing_stats.progress_percentage == 75.0
    
    @pytest.mark.integration
    def test_error_statistics_aggregation(self, mock_channel_snippet):
        """Test error statistics aggregation from failed videos."""
        channel = Channel(
            id="UCXuqSBlHAE6Xw-yeJA0Tunw",
            snippet=mock_channel_snippet,
            videos=[]
        )
        
        # Add videos with various error types
        error_videos = [
            Video(id=f"err{i}", title=f"Error {i}", url=f"https://youtube.com/watch?v=err{i}",
                  transcript_status=TranscriptStatus.ERROR, error_message=error)
            for i, error in enumerate([
                "Network Error: Connection failed",
                "Network Error: Timeout",
                "Transcript Error: No captions available",
                "Permission Error: Video is private",
                "Network Error: DNS resolution failed"
            ])
        ]
        
        channel.videos = error_videos
        
        # Verify error statistics
        error_summary = channel.processing_stats.get_error_summary()
        assert error_summary['total_errors'] == 5
        assert error_summary['error_types']['Network Error'] == 3
        assert error_summary['error_types']['Transcript Error'] == 1
        assert error_summary['error_types']['Permission Error'] == 1
        assert error_summary['most_common_error'] == 'Network Error'
    
    @pytest.mark.integration
    def test_time_estimation_calculation(self):
        """Test estimated time remaining calculation."""
        stats = ProcessingStatistics(
            total_videos=100,
            processed_videos=25,
            successful_videos=20,
            failed_videos=5,
            average_processing_time=5.0,  # 5 seconds per video
            processing_start_time=datetime.now()
        )
        
        # 75 videos remaining * 5 seconds = 375 seconds
        estimated = stats.estimated_time_remaining
        assert estimated is not None
        assert abs(estimated.total_seconds() - 375) < 1  # Allow small float precision difference
    
    @pytest.mark.integration
    def test_processing_rate_calculation(self):
        """Test processing rate calculation."""
        start_time = datetime.now() - timedelta(hours=1)
        stats = ProcessingStatistics(
            total_videos=100,
            processed_videos=60,
            processing_start_time=start_time
        )
        
        # Processed 60 videos in 1 hour = 60 videos/hour
        rate = stats.get_processing_rate()
        assert rate is not None
        assert 59 <= rate <= 61  # Allow small time calculation differences
    
    @pytest.mark.integration
    async def test_concurrent_statistics_update(self, mock_channel_snippet):
        """Test statistics updates with concurrent video processing."""
        channel = Channel(
            id="UCXuqSBlHAE6Xw-yeJA0Tunw",
            snippet=mock_channel_snippet,
            videos=[
                Video(id=f"vid{i}", title=f"Video {i}", url=f"https://youtube.com/watch?v={i}")
                for i in range(50)
            ]
        )
        
        # Simulate concurrent processing
        async def process_video(video: Video, success_rate: float = 0.8):
            """Simulate video processing."""
            await asyncio.sleep(0.01)  # Simulate processing time
            
            if hash(video.id) % 100 / 100 < success_rate:
                video.transcript_status = TranscriptStatus.SUCCESS
                video.processing_duration = 5.0
            else:
                video.transcript_status = TranscriptStatus.ERROR
                video.error_message = "Simulated error"
        
        # Process videos concurrently
        tasks = [process_video(video) for video in channel.videos]
        await asyncio.gather(*tasks)
        
        # Update statistics
        channel.update_processing_statistics()
        
        # Verify statistics integrity
        assert channel.processing_stats.total_videos == 50
        assert channel.processing_stats.processed_videos == 50
        assert (channel.processing_stats.successful_videos + 
                channel.processing_stats.failed_videos) == 50
    
    @pytest.mark.integration
    def test_statistics_report_generation(self, mock_channel):
        """Test comprehensive statistics report generation."""
        # Set specific statistics for testing
        mock_channel.processing_stats = ProcessingStatistics(
            total_videos=100,
            processed_videos=85,
            successful_videos=75,
            failed_videos=8,
            skipped_videos=2,
            processing_start_time=datetime.now() - timedelta(minutes=30),
            average_processing_time=10.0
        )
        
        # Add error statistics
        for error_type in ["Network Error"] * 5 + ["Timeout Error"] * 3:
            mock_channel.processing_stats.update_error_statistics(error_type)
        
        # Generate report
        report = mock_channel.get_statistics_report()
        
        # Verify report contains key information
        assert "Processing Statistics for" in report
        assert "Total Videos: 100" in report
        assert "Processed: 85 (85.0%)" in report
        assert "Success Rate: 88.2%" in report
        assert "Error Analysis:" in report
        assert "Network Error: 5" in report
        assert "Timeout Error: 3" in report
    
    @pytest.mark.integration
    def test_legacy_field_compatibility(self):
        """Test backward compatibility with legacy transcript fields."""
        stats = ProcessingStatistics(
            total_videos=50,
            processed_videos=40,
            successful_videos=35,
            failed_videos=5
        )
        
        # Legacy fields should mirror new fields
        assert stats.successful_transcripts == stats.successful_videos
        assert stats.failed_transcripts == stats.failed_videos
        
        # Update via channel should maintain compatibility
        channel = Channel(
            id="UCtest",
            snippet=ChannelSnippet(title="Test Channel"),
            processing_stats=stats
        )
        
        channel.videos = [
            Video(id=f"v{i}", title=f"Video {i}", url=f"https://youtube.com/watch?v={i}",
                  transcript_status=TranscriptStatus.SUCCESS if i < 10 else TranscriptStatus.PENDING)
            for i in range(20)
        ]
        
        assert channel.processing_stats.successful_transcripts == channel.processing_stats.successful_videos