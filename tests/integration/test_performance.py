"""Performance tests for the YouTube transcriber."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List

import pytest

from src.models.channel import Channel, ChannelSnippet
from src.models.transcript import TranscriptStatus
from src.models.video import Video


class TestPerformance:
    """Performance and stress tests."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_channel_processing_performance(self):
        """Test performance with large number of videos."""
        # Create channel with 1000 videos
        channel = Channel(
            id="UCperflarge",
            snippet=ChannelSnippet(title="Performance Test Channel")
        )
        
        start_time = time.time()
        
        # Add 1000 videos
        videos = []
        for i in range(1000):
            video = Video(
                id=f"perf{i:04d}",
                title=f"Performance Test Video {i}",
                url=f"https://youtube.com/watch?v=perf{i:04d}"
            )
            videos.append(video)
        
        channel.videos = videos
        
        # Measure statistics update time
        update_start = time.time()
        channel.update_processing_statistics()
        update_duration = time.time() - update_start
        
        # Performance assertions
        total_duration = time.time() - start_time
        assert total_duration < 1.0  # Should complete in under 1 second
        assert update_duration < 0.1  # Statistics update should be fast
        assert channel.processing_stats.total_videos == 1000
    
    @pytest.mark.performance
    async def test_concurrent_processing_scalability(self):
        """Test scalability with concurrent video processing."""
        concurrency_levels = [10, 50, 100]
        results = {}
        
        for concurrency in concurrency_levels:
            channel = Channel(
                id=f"UCconcurrent{concurrency}",
                snippet=ChannelSnippet(title=f"Concurrent Test {concurrency}")
            )
            
            # Create videos
            videos = [
                Video(
                    id=f"conc{concurrency}_{i}",
                    title=f"Concurrent Video {i}",
                    url=f"https://youtube.com/watch?v=conc{concurrency}_{i}"
                )
                for i in range(concurrency * 2)
            ]
            channel.videos = videos
            
            # Simulate concurrent processing
            start_time = time.time()
            
            async def process_batch(batch_videos: List[Video]):
                """Process a batch of videos concurrently."""
                tasks = []
                for video in batch_videos:
                    async def process_single(v):
                        await asyncio.sleep(0.01)  # Simulate API call
                        v.transcript_status = TranscriptStatus.SUCCESS
                        v.processing_duration = 0.01
                    tasks.append(process_single(video))
                await asyncio.gather(*tasks)
            
            # Process in batches
            batch_size = concurrency
            for i in range(0, len(videos), batch_size):
                batch = videos[i:i + batch_size]
                await process_batch(batch)
            
            duration = time.time() - start_time
            results[concurrency] = {
                "duration": duration,
                "videos_processed": len(videos),
                "videos_per_second": len(videos) / duration
            }
        
        # Verify scalability
        # Higher concurrency should have better throughput
        assert results[50]["videos_per_second"] > results[10]["videos_per_second"]
        assert results[100]["videos_per_second"] >= results[50]["videos_per_second"] * 0.8  # Allow some overhead
    
    @pytest.mark.performance
    def test_memory_efficiency_with_large_transcripts(self):
        """Test memory efficiency with large transcript data."""
        import sys
        
        channel = Channel(
            id="UCmemorytest",
            snippet=ChannelSnippet(title="Memory Test Channel")
        )
        
        # Track initial memory
        initial_size = sys.getsizeof(channel)
        
        # Add videos with large transcripts
        videos = []
        for i in range(100):
            video = Video(
                id=f"mem{i}",
                title=f"Memory Test {i}",
                url=f"https://youtube.com/watch?v=mem{i}",
                transcript_status=TranscriptStatus.SUCCESS
            )
            # Simulate large transcript (1000 segments)
            video.metadata["transcript_size"] = 1000
            videos.append(video)
        
        channel.videos = videos
        channel.update_processing_statistics()
        
        # Check memory usage
        final_size = sys.getsizeof(channel)
        memory_per_video = (final_size - initial_size) / len(videos)
        
        # Memory per video should be reasonable (less than 10KB)
        assert memory_per_video < 10000
    
    @pytest.mark.performance
    def test_statistics_calculation_performance(self):
        """Test performance of statistics calculations."""
        stats_times = []
        
        for video_count in [100, 500, 1000, 5000]:
            channel = Channel(
                id=f"UCstats{video_count}",
                snippet=ChannelSnippet(title=f"Stats Test {video_count}")
            )
            
            # Add videos with various statuses
            videos = []
            for i in range(video_count):
                status = [TranscriptStatus.SUCCESS, TranscriptStatus.ERROR, 
                         TranscriptStatus.SKIPPED, TranscriptStatus.PENDING][i % 4]
                
                video = Video(
                    id=f"stat{i}",
                    title=f"Stats Video {i}",
                    url=f"https://youtube.com/watch?v=stat{i}",
                    transcript_status=status
                )
                
                if status == TranscriptStatus.ERROR:
                    video.error_message = ["Network Error", "Timeout Error", 
                                         "Transcript Error"][i % 3] + ": Test"
                
                videos.append(video)
            
            channel.videos = videos
            
            # Measure statistics calculation time
            start_time = time.time()
            channel.update_processing_statistics()
            stats_summary = channel.processing_stats.calculate_statistics_summary()
            duration = time.time() - start_time
            
            stats_times.append({
                "video_count": video_count,
                "duration": duration,
                "time_per_video": duration / video_count
            })
        
        # Verify O(n) complexity - time should scale linearly
        # Time per video should remain relatively constant
        time_ratios = [st["time_per_video"] for st in stats_times]
        max_ratio = max(time_ratios)
        min_ratio = min(time_ratios)
        
        # Time per video shouldn't vary by more than 2x
        assert max_ratio / min_ratio < 2.0
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_stress_test_rapid_updates(self):
        """Stress test with rapid concurrent updates."""
        channel = Channel(
            id="UCstresstest",
            snippet=ChannelSnippet(title="Stress Test Channel")
        )
        
        # Add initial videos
        videos = [
            Video(
                id=f"stress{i}",
                title=f"Stress Test {i}",
                url=f"https://youtube.com/watch?v=stress{i}"
            )
            for i in range(200)
        ]
        channel.videos = videos
        
        # Simulate rapid concurrent updates
        start_time = time.time()
        update_count = 0
        
        while time.time() - start_time < 1.0:  # Run for 1 second
            # Random video status updates
            import random
            video_idx = random.randint(0, len(videos) - 1)
            video = videos[video_idx]
            
            # Update status
            video.transcript_status = random.choice(list(TranscriptStatus))
            if video.transcript_status == TranscriptStatus.ERROR:
                video.error_message = f"Error at update {update_count}"
            
            # Update statistics
            channel.update_processing_statistics()
            update_count += 1
        
        # Verify system stability
        assert update_count > 100  # Should handle many updates per second
        assert channel.processing_stats.total_videos == 200
        
        # Verify statistics integrity
        total_processed = (channel.processing_stats.successful_videos +
                          channel.processing_stats.failed_videos +
                          channel.processing_stats.skipped_videos)
        assert total_processed <= 200
    
    @pytest.mark.performance
    def test_time_estimation_accuracy(self):
        """Test accuracy of time estimation with varying processing speeds."""
        channel = Channel(
            id="UCtimetest",
            snippet=ChannelSnippet(title="Time Estimation Test")
        )
        
        # Add 100 videos
        videos = [
            Video(
                id=f"time{i}",
                title=f"Time Test {i}",
                url=f"https://youtube.com/watch?v=time{i}"
            )
            for i in range(100)
        ]
        channel.videos = videos
        channel.processing_stats.processing_start_time = datetime.now()
        
        # Simulate processing with varying speeds
        processing_times = []
        for i in range(50):  # Process first 50 videos
            # Vary processing time (faster at start, slower later)
            proc_time = 2.0 + (i * 0.1)  # 2s to 7s
            processing_times.append(proc_time)
            
            video = videos[i]
            video.transcript_status = TranscriptStatus.SUCCESS
            video.processing_duration = proc_time
            
            channel.update_processing_statistics()
            channel.processing_stats.update_processing_time(proc_time)
            
            # Check time estimation
            if i > 10:  # After some samples
                estimated_remaining = channel.processing_stats.estimated_time_remaining
                if estimated_remaining:
                    remaining_videos = 100 - (i + 1)
                    expected_time = remaining_videos * channel.processing_stats.average_processing_time
                    
                    # Estimation should be within 20% of expected
                    assert abs(estimated_remaining.total_seconds() - expected_time) / expected_time < 0.2