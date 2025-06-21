"""End-to-end test scenarios for the YouTube transcriber."""

import pytest
from datetime import datetime

from src.models.channel import Channel, ChannelSnippet, ProcessingStatistics
from src.models.transcript import TranscriptStatus
from src.models.video import Video, VideoPrivacy


class TestE2EScenarios:
    """End-to-end test scenarios covering complete workflows."""
    
    @pytest.mark.e2e
    def test_successful_channel_processing_flow(self):
        """Test complete successful channel processing workflow."""
        # 1. Initialize channel
        channel = Channel(
            id="UCXuqSBlHAE6Xw-yeJA0Tunw",
            snippet=ChannelSnippet(title="Test Tech Channel"),
            processing_started_at=datetime.now()
        )
        
        # 2. Add videos to process
        videos = []
        for i in range(10):
            video = Video(
                id=f"video{i}",
                title=f"Tech Tutorial {i}",
                url=f"https://youtube.com/watch?v=video{i}",
                privacy_status=VideoPrivacy.PUBLIC
            )
            videos.append(video)
        
        channel.videos = videos
        channel.processing_stats.processing_start_time = datetime.now()
        
        # 3. Simulate processing each video
        for i, video in enumerate(channel.videos):
            # Simulate 80% success rate
            if i < 8:
                video.transcript_status = TranscriptStatus.SUCCESS
                video.processing_duration = 5.5
                video.processed_at = datetime.now()
                channel.processing_stats.update_processing_time(5.5)
            else:
                video.transcript_status = TranscriptStatus.ERROR
                video.error_message = "Network Error: Connection timeout"
                video.retry_count = 1
        
        # 4. Update statistics
        channel.update_processing_statistics()
        
        # 5. Verify results
        assert channel.processing_stats.total_videos == 10
        assert channel.processing_stats.successful_videos == 8
        assert channel.processing_stats.failed_videos == 2
        assert channel.processing_stats.success_rate == 0.8
        assert channel.processing_stats.progress_percentage == 100.0
        assert channel.processing_stats.average_processing_time == 5.5
    
    @pytest.mark.e2e
    def test_error_recovery_workflow(self):
        """Test error handling and recovery workflow."""
        channel = Channel(
            id="UCerrortest",
            snippet=ChannelSnippet(title="Error Test Channel")
        )
        
        # Create videos that will fail
        videos = [
            Video(id="fail1", title="Private Video", url="https://youtube.com/watch?v=fail1",
                  privacy_status=VideoPrivacy.PRIVATE),
            Video(id="fail2", title="No Transcript", url="https://youtube.com/watch?v=fail2"),
            Video(id="fail3", title="Network Issue", url="https://youtube.com/watch?v=fail3"),
        ]
        
        channel.videos = videos
        
        # First processing attempt
        for video in channel.videos:
            if video.privacy_status == VideoPrivacy.PRIVATE:
                video.transcript_status = TranscriptStatus.SKIPPED
                video.error_message = "Video is private"
            else:
                video.transcript_status = TranscriptStatus.ERROR
                video.error_message = "Network Error: Connection failed"
                video.retry_count = 1
        
        channel.update_processing_statistics()
        
        # Verify initial failure state
        assert channel.processing_stats.failed_videos == 2
        assert channel.processing_stats.skipped_videos == 1
        
        # Retry failed videos
        for video in channel.videos:
            if video.transcript_status == TranscriptStatus.ERROR and video.is_retry_recommended():
                # Simulate successful retry for one video
                if video.id == "fail2":
                    video.transcript_status = TranscriptStatus.SUCCESS
                    video.processing_duration = 8.0
                    video.error_message = None
                else:
                    video.retry_count += 1
        
        channel.update_processing_statistics()
        
        # Verify recovery
        assert channel.processing_stats.successful_videos == 1
        assert channel.processing_stats.failed_videos == 1
    
    @pytest.mark.e2e
    def test_large_channel_pagination_workflow(self):
        """Test handling of large channels with pagination."""
        channel = Channel(
            id="UClargechannel",
            snippet=ChannelSnippet(title="Large Content Creator")
        )
        
        # Simulate large channel with 500 videos
        batch_size = 50
        total_videos = 500
        
        # Process in batches
        for batch_num in range(total_videos // batch_size):
            batch_videos = []
            
            for i in range(batch_size):
                video_idx = batch_num * batch_size + i
                video = Video(
                    id=f"vid{video_idx}",
                    title=f"Video {video_idx}",
                    url=f"https://youtube.com/watch?v=vid{video_idx}"
                )
                
                # Simulate processing with decreasing success rate for later videos
                success_probability = 0.9 - (batch_num * 0.05)
                if video_idx % 10 < (success_probability * 10):
                    video.transcript_status = TranscriptStatus.SUCCESS
                    video.processing_duration = 4.0
                else:
                    video.transcript_status = TranscriptStatus.ERROR
                    video.error_message = "Transcript Error: Not available"
                
                batch_videos.append(video)
            
            # Add batch to channel
            channel.videos.extend(batch_videos)
            channel.update_processing_statistics()
            
            # Verify incremental progress
            expected_total = (batch_num + 1) * batch_size
            assert channel.processing_stats.total_videos == expected_total
            assert channel.processing_stats.progress_percentage == 100.0
        
        # Final verification
        assert channel.processing_stats.total_videos == total_videos
        assert channel.processing_stats.processed_videos == total_videos
        assert channel.processing_stats.successful_videos > 350  # At least 70% success
    
    @pytest.mark.e2e
    def test_mixed_language_channel_workflow(self):
        """Test processing channel with videos in multiple languages."""
        channel = Channel(
            id="UCmultilang",
            snippet=ChannelSnippet(title="International Channel", default_language="en")
        )
        
        # Create videos in different languages
        languages = ["en", "es", "ja", "fr", "de"]
        videos = []
        
        for i, lang in enumerate(languages * 3):  # 15 videos, 3 per language
            video = Video(
                id=f"lang_{lang}_{i}",
                title=f"Video in {lang} #{i}",
                url=f"https://youtube.com/watch?v=lang_{lang}_{i}",
                language=lang
            )
            
            # Language-specific success rates
            if lang in ["en", "es"]:
                video.transcript_status = TranscriptStatus.SUCCESS
            elif lang == "ja":
                video.transcript_status = TranscriptStatus.SUCCESS if i % 2 == 0 else TranscriptStatus.ERROR
                if video.transcript_status == TranscriptStatus.ERROR:
                    video.error_message = "Transcript Error: Japanese captions not available"
            else:
                video.transcript_status = TranscriptStatus.SKIPPED
            
            videos.append(video)
        
        channel.videos = videos
        channel.update_processing_statistics()
        
        # Analyze language distribution
        success_by_language = {}
        for video in channel.videos:
            if video.language:
                if video.language not in success_by_language:
                    success_by_language[video.language] = {"total": 0, "success": 0}
                success_by_language[video.language]["total"] += 1
                if video.transcript_status == TranscriptStatus.SUCCESS:
                    success_by_language[video.language]["success"] += 1
        
        # Verify language-specific results
        assert success_by_language["en"]["success"] == 3
        assert success_by_language["es"]["success"] == 3
        assert success_by_language["ja"]["success"] < success_by_language["ja"]["total"]
    
    @pytest.mark.e2e
    def test_performance_monitoring_workflow(self):
        """Test performance monitoring during processing."""
        channel = Channel(
            id="UCperftest",
            snippet=ChannelSnippet(title="Performance Test Channel")
        )
        
        # Add videos with varying processing times
        videos = []
        processing_times = [2.0, 3.5, 15.0, 4.0, 2.5, 30.0, 3.0, 2.8, 4.5, 3.2]
        
        for i, proc_time in enumerate(processing_times):
            video = Video(
                id=f"perf{i}",
                title=f"Performance Test {i}",
                url=f"https://youtube.com/watch?v=perf{i}"
            )
            
            # Simulate processing
            video.transcript_status = TranscriptStatus.SUCCESS
            video.processing_duration = proc_time
            video.statistics = {"duration_seconds": proc_time * 60}  # Assume 1:60 ratio
            
            videos.append(video)
            channel.videos = videos[:i+1]  # Add videos incrementally
            channel.update_processing_statistics()
            
            # Update processing time
            channel.processing_stats.update_processing_time(proc_time)
        
        # Calculate performance metrics
        total_processing_time = sum(processing_times)
        avg_processing_time = total_processing_time / len(processing_times)
        
        # Verify performance tracking
        assert abs(channel.processing_stats.average_processing_time - avg_processing_time) < 0.1
        
        # Check efficiency for each video
        for video in channel.videos:
            efficiency = video.calculate_processing_efficiency()
            assert efficiency is not None
            assert efficiency > 0