"""Pytest configuration and shared fixtures."""

import asyncio
from datetime import datetime
from typing import Dict, Generator, List

import pytest
from faker import Faker

from src.models.channel import Channel, ChannelSnippet, ChannelStatistics, ProcessingStatistics
from src.models.transcript import TranscriptData, TranscriptSegment, TranscriptStatus
from src.models.video import Video, VideoPrivacy, VideoStatistics

# Initialize Faker
fake = Faker()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_channel_urls() -> List[str]:
    """Sample YouTube channel URLs for testing."""
    return [
        "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw",  # Linus Tech Tips
        "https://www.youtube.com/@mkbhd",  # MKBHD
        "https://www.youtube.com/c/TechWithTim",  # Tech With Tim
        "https://www.youtube.com/channel/UC-invalid-channel-id",  # Invalid channel
        "https://www.youtube.com/@nonexistent_channel_12345",  # Non-existent channel
    ]


@pytest.fixture
def sample_video_ids() -> List[str]:
    """Sample YouTube video IDs for testing."""
    return [
        "dQw4w9WgXcQ",  # Never Gonna Give You Up
        "jNQXAC9IVRw",  # Me at the zoo
        "invalid_id",   # Invalid video ID
        "private_vid1", # Private video simulation
        "deleted_vid2", # Deleted video simulation
    ]


@pytest.fixture
def mock_channel_snippet() -> ChannelSnippet:
    """Mock channel snippet data."""
    return ChannelSnippet(
        title=fake.company(),
        description=fake.text(max_nb_chars=200),
        custom_url=f"@{fake.user_name()}",
        published_at=fake.date_time_between(start_date="-10y", end_date="now"),
        thumbnail_url="https://example.com/thumb.jpg",
        country="US",
        default_language="en"
    )


@pytest.fixture
def mock_channel_statistics() -> ChannelStatistics:
    """Mock channel statistics data."""
    return ChannelStatistics(
        subscriber_count=fake.random_int(min=1000, max=10000000),
        video_count=fake.random_int(min=10, max=1000),
        view_count=fake.random_int(min=100000, max=1000000000)
    )


@pytest.fixture
def mock_processing_statistics() -> ProcessingStatistics:
    """Mock processing statistics with various scenarios."""
    total = fake.random_int(min=50, max=200)
    processed = fake.random_int(min=0, max=total)
    successful = fake.random_int(min=0, max=processed)
    failed = processed - successful
    
    stats = ProcessingStatistics(
        total_videos=total,
        processed_videos=processed,
        successful_videos=successful,
        failed_videos=failed,
        skipped_videos=fake.random_int(min=0, max=10),
        successful_transcripts=successful,  # Legacy field
        failed_transcripts=failed,  # Legacy field
        processing_start_time=datetime.now(),
        average_processing_time=fake.random.uniform(2.0, 10.0)
    )
    
    # Add some error statistics
    if failed > 0:
        error_types = ["Network Error", "Transcript Error", "Permission Error", "Timeout Error"]
        for _ in range(failed):
            error_type = fake.random_element(error_types)
            stats.update_error_statistics(error_type)
    
    return stats


@pytest.fixture
def mock_video_statistics() -> VideoStatistics:
    """Mock video statistics data."""
    return VideoStatistics(
        view_count=fake.random_int(min=100, max=10000000),
        like_count=fake.random_int(min=10, max=100000),
        comment_count=fake.random_int(min=0, max=50000),
        duration_seconds=fake.random_int(min=30, max=3600)
    )


@pytest.fixture
def mock_transcript_segments() -> List[TranscriptSegment]:
    """Mock transcript segments."""
    segments = []
    start_time = 0.0
    
    for i in range(fake.random_int(min=5, max=20)):
        duration = fake.random.uniform(1.0, 5.0)
        segments.append(
            TranscriptSegment(
                text=fake.sentence(nb_words=10),
                start=start_time,
                duration=duration
            )
        )
        start_time += duration
    
    return segments


@pytest.fixture
def mock_transcript_data(mock_transcript_segments) -> TranscriptData:
    """Mock transcript data."""
    return TranscriptData(
        segments=mock_transcript_segments,
        language=fake.random_element(["en", "ja", "es", "fr", "de"]),
        duration=sum(seg.duration for seg in mock_transcript_segments),
        is_generated=fake.boolean()
    )


@pytest.fixture
def mock_video(mock_video_statistics, mock_transcript_data) -> Video:
    """Mock video with various states."""
    video_id = fake.lexify(text="???????????", letters="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    
    video = Video(
        id=video_id,
        title=fake.sentence(nb_words=6),
        url=f"https://www.youtube.com/watch?v={video_id}",
        thumbnail_url=f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        description=fake.text(max_nb_chars=500),
        published_at=fake.date_time_between(start_date="-5y", end_date="now"),
        privacy_status=fake.random_element(list(VideoPrivacy)),
        statistics=mock_video_statistics,
        transcript_status=fake.random_element(list(TranscriptStatus)),
        tags=[fake.word() for _ in range(fake.random_int(min=0, max=10))],
        language=fake.random_element(["en", "ja", "es", "fr", "de", None])
    )
    
    # Add transcript data for successful videos
    if video.transcript_status == TranscriptStatus.SUCCESS:
        video.transcript_data = mock_transcript_data
        video.transcript_file_path = f"transcripts/{video_id}.json"
        video.processing_duration = fake.random.uniform(1.0, 30.0)
        video.processed_at = datetime.now()
    elif video.transcript_status == TranscriptStatus.ERROR:
        video.error_message = fake.random_element([
            "Network Error: Connection timeout",
            "Transcript Error: No transcript available",
            "Permission Error: Video is private",
            "Timeout Error: Processing took too long",
            "Format Error: Invalid response format"
        ])
        video.retry_count = fake.random_int(min=0, max=3)
    
    return video


@pytest.fixture
def mock_channel(mock_channel_snippet, mock_channel_statistics, mock_processing_statistics) -> Channel:
    """Mock channel with videos."""
    channel_id = f"UC{fake.lexify(text='??????????????????????', letters='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')}"
    
    # Create videos
    videos = []
    num_videos = fake.random_int(min=5, max=20)
    for _ in range(num_videos):
        videos.append(mock_video(mock_video_statistics(), mock_transcript_data(mock_transcript_segments())))
    
    channel = Channel(
        id=channel_id,
        snippet=mock_channel_snippet,
        statistics=mock_channel_statistics,
        videos=videos,
        processing_stats=mock_processing_statistics,
        processing_started_at=datetime.now()
    )
    
    return channel


@pytest.fixture
def edge_case_scenarios() -> Dict[str, Dict]:
    """Edge case test scenarios."""
    return {
        "empty_channel": {
            "description": "Channel with no videos",
            "total_videos": 0,
            "expected_behavior": "Graceful handling with appropriate message"
        },
        "large_channel": {
            "description": "Channel with many videos (1000+)",
            "total_videos": 1500,
            "expected_behavior": "Efficient processing with pagination"
        },
        "all_private_videos": {
            "description": "Channel where all videos are private",
            "expected_behavior": "Skip all videos with appropriate status"
        },
        "mixed_languages": {
            "description": "Channel with videos in multiple languages",
            "languages": ["en", "ja", "es", "fr", "de", "ko", "zh"],
            "expected_behavior": "Process all languages correctly"
        },
        "network_failures": {
            "description": "Intermittent network failures during processing",
            "failure_rate": 0.3,
            "expected_behavior": "Retry mechanism and graceful degradation"
        },
        "rate_limiting": {
            "description": "API rate limit scenarios",
            "requests_per_minute": 100,
            "expected_behavior": "Respect rate limits with backoff"
        },
        "long_videos": {
            "description": "Videos longer than 3 hours",
            "duration_seconds": 15000,
            "expected_behavior": "Process without timeout"
        },
        "special_characters": {
            "description": "Videos with special characters in titles",
            "titles": ["Test 🎥 Video", "Video with / \\ * : ? \" < > |", "видео тест", "テストビデオ"],
            "expected_behavior": "Handle all characters correctly"
        }
    }


@pytest.fixture
def performance_scenarios() -> Dict[str, Dict]:
    """Performance test scenarios."""
    return {
        "baseline": {
            "videos": 10,
            "avg_duration": 300,  # 5 minutes
            "expected_time": 30  # seconds
        },
        "medium_load": {
            "videos": 100,
            "avg_duration": 600,  # 10 minutes
            "expected_time": 300  # 5 minutes
        },
        "high_load": {
            "videos": 500,
            "avg_duration": 900,  # 15 minutes
            "expected_time": 1800  # 30 minutes
        },
        "stress_test": {
            "videos": 1000,
            "avg_duration": 600,
            "concurrent_requests": 50,
            "expected_behavior": "No memory leaks, stable performance"
        }
    }