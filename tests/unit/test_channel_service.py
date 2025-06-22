"""Unit tests for channel service - Core functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import aiohttp

from src.services.channel_service import ChannelService
from src.models.channel import Channel, ChannelSnippet, ChannelStatistics
from src.models.video import Video, VideoStatistics
from src.models.config import AppSettings


class TestChannelService:
    """Test channel service core functionality."""
    
    @pytest.fixture
    def mock_youtube_api(self):
        """Create mock YouTube API repository."""
        mock = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_ytdlp_repo(self):
        """Create mock yt-dlp repository."""
        mock = AsyncMock()
        return mock
    
    @pytest.fixture
    def channel_service(self, mock_youtube_api, mock_ytdlp_repo):
        """Create channel service instance with mocks."""
        settings = AppSettings(api={"youtube_api_key": "test_key"})
        service = ChannelService(
            youtube_api=mock_youtube_api,
            ytdlp_repository=mock_ytdlp_repo,
            settings=settings
        )
        return service
    
    @pytest.fixture
    def sample_channel(self):
        """Create sample channel data."""
        return Channel(
            id="UC123456",
            title="Test Channel",
            description="Test channel description",
            handle="@testchannel",
            custom_url="https://youtube.com/@testchannel",
            published_at=datetime.now(timezone.utc),
            snippet=ChannelSnippet(
                title="Test Channel",
                description="Test channel description",
                custom_url="https://youtube.com/@testchannel",
                published_at=datetime.now(timezone.utc),
                thumbnails={},
                country="US"
            ),
            statistics=ChannelStatistics(
                view_count=1000000,
                subscriber_count=10000,
                video_count=100
            ),
            videos=[]
        )
    
    @pytest.mark.asyncio
    async def test_get_channel_by_url(self, channel_service, mock_youtube_api, sample_channel):
        """Test getting channel by URL."""
        mock_youtube_api.get_channel_info.return_value = sample_channel
        
        # Test with full URL
        result = await channel_service.get_channel_by_input("https://youtube.com/@testchannel")
        
        assert result.id == "UC123456"
        assert result.title == "Test Channel"
        mock_youtube_api.get_channel_info.assert_called_once_with("https://youtube.com/@testchannel")
    
    @pytest.mark.asyncio
    async def test_get_channel_by_handle(self, channel_service, mock_youtube_api, sample_channel):
        """Test getting channel by handle."""
        mock_youtube_api.get_channel_info.return_value = sample_channel
        
        # Test with handle
        result = await channel_service.get_channel_by_input("@testchannel")
        
        assert result.id == "UC123456"
        assert result.handle == "@testchannel"
    
    @pytest.mark.asyncio
    async def test_get_channel_by_id(self, channel_service, mock_youtube_api, sample_channel):
        """Test getting channel by ID."""
        mock_youtube_api.get_channel_info.return_value = sample_channel
        
        # Test with channel ID
        result = await channel_service.get_channel_by_input("UC123456")
        
        assert result.id == "UC123456"
    
    @pytest.mark.asyncio
    async def test_channel_not_found(self, channel_service, mock_youtube_api):
        """Test handling when channel is not found."""
        mock_youtube_api.get_channel_info.return_value = None
        
        with pytest.raises(ValueError, match="Channel not found"):
            await channel_service.get_channel_by_input("@nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_channel_videos_with_date_filter(self, channel_service, mock_youtube_api):
        """Test getting channel videos with date filtering."""
        # Create sample videos with different dates
        videos = [
            Video(
                id="video1",
                title="Old Video",
                published_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                channel_id="UC123456",
                duration=300
            ),
            Video(
                id="video2",
                title="Recent Video",
                published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                channel_id="UC123456",
                duration=600
            ),
            Video(
                id="video3",
                title="New Video",
                published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
                channel_id="UC123456",
                duration=450
            ),
        ]
        
        mock_youtube_api.get_channel_videos.return_value = videos
        
        # Test with date range
        result = await channel_service.get_channel_videos(
            channel_id="UC123456",
            date_from="2024-01-01",
            date_to="2024-12-31"
        )
        
        assert len(result) == 2
        assert result[0].id == "video2"
        assert result[1].id == "video3"
    
    @pytest.mark.asyncio
    async def test_get_channel_videos_pagination(self, channel_service, mock_youtube_api):
        """Test video pagination handling."""
        # Create 150 videos to test pagination
        videos = [
            Video(
                id=f"video{i}",
                title=f"Video {i}",
                published_at=datetime.now(timezone.utc),
                channel_id="UC123456",
                duration=300
            )
            for i in range(150)
        ]
        
        mock_youtube_api.get_channel_videos.return_value = videos
        
        result = await channel_service.get_channel_videos(
            channel_id="UC123456",
            max_results=100
        )
        
        assert len(result) == 100
        mock_youtube_api.get_channel_videos.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_filter_private_videos(self, channel_service):
        """Test filtering of private/unavailable videos."""
        videos = [
            Video(id="video1", title="Public Video", duration=300, channel_id="UC123456"),
            Video(id="video2", title="Private Video", duration=0, channel_id="UC123456"),  # Duration 0 indicates private
            Video(id="video3", title="Deleted Video", duration=None, channel_id="UC123456"),
            Video(id="video4", title="Live Stream", duration=-1, channel_id="UC123456", is_live=True),
        ]
        
        # Filter based on settings
        channel_service.settings.processing.skip_private_videos = True
        channel_service.settings.processing.skip_live_streams = True
        
        filtered = channel_service._filter_videos(videos)
        
        assert len(filtered) == 1
        assert filtered[0].id == "video1"
    
    @pytest.mark.asyncio
    async def test_channel_with_no_videos(self, channel_service, mock_youtube_api, sample_channel):
        """Test handling channel with no videos."""
        mock_youtube_api.get_channel_info.return_value = sample_channel
        mock_youtube_api.get_channel_videos.return_value = []
        
        channel = await channel_service.get_channel_by_input("@testchannel")
        videos = await channel_service.get_channel_videos(channel.id)
        
        assert channel.id == "UC123456"
        assert len(videos) == 0
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, channel_service, mock_youtube_api):
        """Test handling of API errors."""
        # Test quota exceeded
        mock_youtube_api.get_channel_info.side_effect = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=403,
            message="quotaExceeded"
        )
        
        with pytest.raises(aiohttp.ClientResponseError):
            await channel_service.get_channel_by_input("@testchannel")
        
        # Test network error with retry
        mock_youtube_api.get_channel_info.side_effect = [
            aiohttp.ClientConnectionError("Network error"),
            sample_channel  # Success on retry
        ]
        
        # This should succeed after retry (if retry is implemented in service)
        # For now, it will raise the error
        with pytest.raises(aiohttp.ClientConnectionError):
            await channel_service.get_channel_by_input("@testchannel")
    
    @pytest.mark.asyncio
    async def test_channel_statistics_calculation(self, channel_service):
        """Test channel statistics aggregation."""
        videos = [
            Video(
                id=f"video{i}",
                title=f"Video {i}",
                duration=300 + i * 60,  # Varying durations
                statistics=VideoStatistics(
                    view_count=1000 * (i + 1),
                    like_count=100 * (i + 1),
                    comment_count=10 * (i + 1)
                ),
                channel_id="UC123456"
            )
            for i in range(5)
        ]
        
        stats = channel_service._calculate_channel_stats(videos)
        
        assert stats["total_videos"] == 5
        assert stats["total_duration"] == 300 * 5 + sum(i * 60 for i in range(5))
        assert stats["total_views"] == sum(1000 * (i + 1) for i in range(5))
        assert stats["average_views"] == stats["total_views"] / 5
    
    @pytest.mark.asyncio
    async def test_handle_invalid_channel_inputs(self, channel_service, mock_youtube_api):
        """Test handling of various invalid channel inputs."""
        invalid_inputs = [
            "",  # Empty string
            " ",  # Whitespace
            "not_a_url",  # Invalid format
            "https://youtube.com/",  # URL without channel
            "https://notyt.com/@channel",  # Wrong domain
        ]
        
        mock_youtube_api.get_channel_info.return_value = None
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                await channel_service.get_channel_by_input(invalid_input)
    
    @pytest.mark.asyncio
    async def test_channel_cache_behavior(self, channel_service, mock_youtube_api, sample_channel):
        """Test channel caching behavior if implemented."""
        mock_youtube_api.get_channel_info.return_value = sample_channel
        
        # First call
        result1 = await channel_service.get_channel_by_input("@testchannel")
        assert mock_youtube_api.get_channel_info.call_count == 1
        
        # Second call - should use cache if implemented
        result2 = await channel_service.get_channel_by_input("@testchannel")
        # Without cache, it will call API again
        assert mock_youtube_api.get_channel_info.call_count == 2
        
        assert result1.id == result2.id


class TestChannelServiceIntegration:
    """Integration tests for channel service with multiple components."""
    
    @pytest.mark.asyncio
    async def test_full_channel_processing_flow(self):
        """Test complete channel processing workflow."""
        # This would test the full flow from channel input to video list
        # Including error handling, retries, and data transformation
        pass  # Placeholder for integration test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])