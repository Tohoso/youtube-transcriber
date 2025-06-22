# YouTube Transcriber API Specification

## Table of Contents

1. [Overview](#overview)
2. [CLI Commands](#cli-commands)
3. [Python API](#python-api)
4. [Service Interfaces](#service-interfaces)
5. [Data Models](#data-models)
6. [Error Codes](#error-codes)
7. [Configuration](#configuration)
8. [Extension Points](#extension-points)
9. [Examples](#examples)
10. [Best Practices](#best-practices)

## Overview

YouTube Transcriber provides both a command-line interface (CLI) and a Python API for downloading YouTube transcripts. This document specifies all public interfaces, data formats, and integration points.

### API Design Principles

- **Consistency**: Uniform naming conventions and parameter patterns
- **Simplicity**: Intuitive interfaces with sensible defaults
- **Extensibility**: Clear extension points for custom functionality
- **Error Handling**: Comprehensive error codes and messages
- **Type Safety**: Full type hints for all public interfaces

## CLI Commands

### Basic Command Structure

```bash
youtube-transcriber [COMMAND] [ARGUMENTS] [OPTIONS]
```

### Commands Reference

#### 1. Single Channel Processing

```bash
youtube-transcriber [CHANNEL] [OPTIONS]
```

**Arguments:**
- `CHANNEL`: Channel identifier (@handle, URL, or channel ID)

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output-dir` | `-o` | PATH | `./output` | Output directory for transcripts |
| `--format` | `-f` | STRING | `txt` | Output format (txt, json, csv, markdown) |
| `--language` | `-l` | STRING | `en` | Preferred subtitle language |
| `--concurrent` | `-c` | INT | `5` | Number of concurrent downloads |
| `--date-from` | | DATE | | Start date filter (YYYY-MM-DD) |
| `--date-to` | | DATE | | End date filter (YYYY-MM-DD) |
| `--recent-days` | | INT | | Download videos from last N days |
| `--max-videos` | | INT | | Maximum number of videos to process |
| `--skip-existing` | | FLAG | `True` | Skip already downloaded transcripts |
| `--dry-run` | | FLAG | `False` | Show what would be downloaded |
| `--verbose` | `-v` | FLAG | `False` | Enable verbose logging |

**Examples:**
```bash
# Basic usage
youtube-transcriber @mkbhd

# With options
youtube-transcriber @mkbhd -o ./transcripts -f json -l ja

# Using channel URL
youtube-transcriber https://youtube.com/@LinusTechTips --recent-days 30

# Dry run with date filter
youtube-transcriber UCxxxxxx --date-from 2024-01-01 --dry-run
```

#### 2. Batch Processing

```bash
youtube-transcriber batch [FILE] [OPTIONS]
```

**Arguments:**
- `FILE`: Path to file containing channel list

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--parallel-channels` | `-pc` | INT | `3` | Channels to process simultaneously |
| `--parallel-videos` | `-pv` | INT | `5` | Videos per channel to process simultaneously |
| `--filter` | | ENUM | | Filter channels (large, medium, small, recent) |
| `--sort` | | ENUM | | Sort channels (name, subscribers, videos, date_added) |
| `--resume` | `-r` | FLAG | `False` | Resume from previous session |
| All single channel options | | | | Inherited from single channel command |

**Examples:**
```bash
# Basic batch processing
youtube-transcriber batch channels.txt

# With advanced options
youtube-transcriber batch channels.txt -pc 5 -pv 10 --filter large --sort subscribers

# Resume interrupted batch
youtube-transcriber batch channels.txt --resume
```

#### 3. Interactive Mode

```bash
youtube-transcriber interactive [OPTIONS]
```

**Options:**
- All options from batch processing

**Interactive Commands:**
- `add` - Add channels to selection
- `search` - Search for channels
- `filter` - Apply filters to channel list
- `sort` - Sort channel list
- `validate` - Validate all channels
- `proceed` - Start processing
- `quit` - Exit without processing

#### 4. Configuration Management

```bash
youtube-transcriber config [SUBCOMMAND] [OPTIONS]
```

**Subcommands:**
- `--generate` - Generate sample configuration file
- `--api-key [KEY]` - Set YouTube API key
- `--show` - Display current configuration
- `--validate` - Validate configuration file

**Examples:**
```bash
# Generate config file
youtube-transcriber config --generate

# Set API key
youtube-transcriber config --api-key AIzaSyxxxxxxxxxxxxxx

# Validate configuration
youtube-transcriber config --validate
```

#### 5. Utility Commands

```bash
# Show version
youtube-transcriber --version

# Show help
youtube-transcriber --help

# Show command-specific help
youtube-transcriber batch --help
```

## Python API

### Installation

```python
# As a library
pip install youtube-transcriber

# Import
from youtube_transcriber import YouTubeTranscriber, ChannelProcessor, BatchProcessor
```

### Core Classes

#### YouTubeTranscriber

```python
class YouTubeTranscriber:
    """Main API entry point for transcript downloading."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        output_dir: Path = Path("./output"),
        config_path: Optional[Path] = None
    ):
        """
        Initialize transcriber.
        
        Args:
            api_key: YouTube API key (defaults to env var)
            output_dir: Base output directory
            config_path: Path to configuration file
        """
    
    async def process_channel(
        self,
        channel_input: str,
        language: str = "en",
        output_format: str = "txt",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_videos: Optional[int] = None,
        concurrent_limit: int = 5
    ) -> ChannelResult:
        """
        Process a single channel.
        
        Args:
            channel_input: Channel identifier (@handle, URL, or ID)
            language: Preferred subtitle language
            output_format: Output format (txt, json, csv, markdown)
            date_from: Start date filter
            date_to: End date filter
            max_videos: Maximum videos to process
            concurrent_limit: Concurrent download limit
            
        Returns:
            ChannelResult: Processing results and statistics
            
        Raises:
            ChannelNotFoundError: Channel doesn't exist
            APIQuotaExceededError: YouTube API quota exceeded
            ProcessingError: General processing error
        """
    
    async def process_batch(
        self,
        channels: List[str],
        parallel_channels: int = 3,
        **channel_kwargs
    ) -> BatchResult:
        """
        Process multiple channels.
        
        Args:
            channels: List of channel identifiers
            parallel_channels: Channels to process simultaneously
            **channel_kwargs: Arguments passed to process_channel
            
        Returns:
            BatchResult: Aggregate results for all channels
        """
```

#### ChannelProcessor

```python
class ChannelProcessor:
    """Lower-level channel processing API."""
    
    async def validate_channel(self, channel_input: str) -> Channel:
        """Validate and fetch channel metadata."""
    
    async def get_video_list(
        self,
        channel: Channel,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Video]:
        """Get filtered video list for channel."""
    
    async def download_transcript(
        self,
        video: Video,
        language: str = "en"
    ) -> Optional[Transcript]:
        """Download transcript for a single video."""
```

#### BatchProcessor

```python
class BatchProcessor:
    """Batch processing coordinator."""
    
    def __init__(self, settings: ProcessingSettings):
        """Initialize with processing settings."""
    
    async def process_channels(
        self,
        channel_inputs: List[str],
        progress_callback: Optional[Callable] = None
    ) -> BatchResult:
        """
        Process multiple channels with progress updates.
        
        Args:
            channel_inputs: List of channel identifiers
            progress_callback: Called with progress updates
            
        Returns:
            BatchResult: Complete processing results
        """
```

### Event Hooks

```python
# Progress callback signature
ProgressCallback = Callable[[ProgressEvent], None]

class ProgressEvent:
    channel_id: str
    video_id: Optional[str]
    event_type: str  # "channel_start", "video_complete", etc.
    progress: float  # 0.0 to 1.0
    message: str

# Example usage
def on_progress(event: ProgressEvent):
    print(f"{event.channel_id}: {event.progress:.1%} - {event.message}")

transcriber = YouTubeTranscriber()
await transcriber.process_batch(
    channels=["@mkbhd", "@LinusTechTips"],
    progress_callback=on_progress
)
```

## Service Interfaces

### Channel Service

```python
class ChannelService:
    """Channel validation and metadata service."""
    
    async def get_channel(self, channel_input: str) -> Channel:
        """Get channel metadata from various input formats."""
    
    async def get_channel_videos(
        self,
        channel_id: str,
        page_token: Optional[str] = None
    ) -> Tuple[List[Video], Optional[str]]:
        """Get paginated video list."""
    
    async def get_channel_statistics(self, channel_id: str) -> ChannelStatistics:
        """Get channel statistics."""
```

### Transcript Service

```python
class TranscriptService:
    """Transcript extraction service."""
    
    async def get_transcript(
        self,
        video_id: str,
        language: str = "en"
    ) -> Optional[Transcript]:
        """Get transcript with language fallback."""
    
    def get_available_languages(self, video_id: str) -> List[str]:
        """Get available transcript languages."""
```

### Export Service

```python
class ExportService:
    """Transcript export and formatting service."""
    
    def export_transcript(
        self,
        video: Video,
        transcript: Transcript,
        output_format: str,
        output_path: Path
    ) -> Path:
        """Export transcript in specified format."""
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
```

## Data Models

### Core Models

```python
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel

class Channel(BaseModel):
    """YouTube channel model."""
    id: str
    title: str
    description: str
    custom_url: Optional[str]
    published_at: datetime
    statistics: ChannelStatistics
    
class ChannelStatistics(BaseModel):
    """Channel statistics."""
    subscriber_count: int
    video_count: int
    view_count: int

class Video(BaseModel):
    """YouTube video model."""
    id: str
    channel_id: str
    title: str
    description: str
    published_at: datetime
    duration: Optional[str]
    tags: List[str]
    
class Transcript(BaseModel):
    """Video transcript model."""
    video_id: str
    language: str
    is_auto_generated: bool
    segments: List[TranscriptSegment]
    
class TranscriptSegment(BaseModel):
    """Transcript segment."""
    text: str
    start: float
    duration: float
```

### Result Models

```python
class ProcessingResult(BaseModel):
    """Base processing result."""
    success: bool
    error: Optional[str]
    timestamp: datetime

class VideoResult(ProcessingResult):
    """Single video processing result."""
    video_id: str
    transcript_saved: bool
    output_path: Optional[Path]
    word_count: Optional[int]

class ChannelResult(ProcessingResult):
    """Channel processing result."""
    channel_id: str
    channel_title: str
    total_videos: int
    processed_videos: int
    successful_videos: int
    failed_videos: int
    video_results: List[VideoResult]
    processing_time: float

class BatchResult(BaseModel):
    """Batch processing result."""
    total_channels: int
    successful_channels: int
    failed_channels: int
    channel_results: List[ChannelResult]
    total_videos_processed: int
    total_processing_time: float
```

## Error Codes

### Error Code Structure

```python
class ErrorCode(Enum):
    """Standard error codes."""
    
    # 1xxx - Input errors
    INVALID_CHANNEL = 1001
    INVALID_FORMAT = 1002
    INVALID_CONFIG = 1003
    
    # 2xxx - API errors
    API_KEY_MISSING = 2001
    API_QUOTA_EXCEEDED = 2002
    API_REQUEST_FAILED = 2003
    
    # 3xxx - Processing errors
    CHANNEL_NOT_FOUND = 3001
    VIDEO_NOT_FOUND = 3002
    TRANSCRIPT_NOT_AVAILABLE = 3003
    
    # 4xxx - System errors
    FILE_WRITE_ERROR = 4001
    NETWORK_ERROR = 4002
    PERMISSION_ERROR = 4003
```

### Error Response Format

```python
class ErrorResponse(BaseModel):
    """Standard error response."""
    code: ErrorCode
    message: str
    details: Optional[Dict]
    timestamp: datetime
    
# Example
{
    "code": 2002,
    "message": "YouTube API quota exceeded",
    "details": {
        "quota_limit": 10000,
        "quota_used": 10000,
        "reset_time": "2024-01-02T00:00:00Z"
    },
    "timestamp": "2024-01-01T15:30:00Z"
}
```

## Configuration

### Configuration Schema

```yaml
# config.yaml
api:
  youtube_api_key: ${YOUTUBE_API_KEY}
  quota_limit: 10000
  quota_reset_hour: 0  # UTC hour

processing:
  concurrent_limit: 5
  retry_attempts: 3
  retry_delay: 1.0
  timeout: 30
  rate_limit_per_minute: 60

output:
  base_directory: ./output
  create_channel_folders: true
  filename_template: "{date}_{title}_{video_id}"
  default_format: txt
  default_language: en
  
batch:
  max_channels: 5
  channel_delay: 5
  save_progress: true
  progress_file: .batch_progress.json

logging:
  level: INFO
  file: ./logs/app.log
  format: "{time} | {level} | {message}"
  rotation: "10 MB"
  retention: "7 days"
```

### Environment Variables

```bash
# Required
YOUTUBE_API_KEY=your_api_key_here

# Optional
YOUTUBE_TRANSCRIBER_OUTPUT_DIR=/path/to/output
YOUTUBE_TRANSCRIBER_CONFIG=/path/to/config.yaml
YOUTUBE_TRANSCRIBER_LOG_LEVEL=DEBUG
```

## Extension Points

### Custom Formatters

```python
from youtube_transcriber.formatters import BaseFormatter

class CustomFormatter(BaseFormatter):
    """Custom transcript formatter."""
    
    def format_transcript(
        self,
        video: Video,
        transcript: Transcript,
        metadata: Dict
    ) -> str:
        """Format transcript for output."""
        # Custom implementation
        return formatted_content
    
    def get_file_extension(self) -> str:
        """Return file extension for this format."""
        return "custom"

# Registration
from youtube_transcriber import register_formatter
register_formatter("custom", CustomFormatter())
```

### Processing Hooks

```python
from youtube_transcriber.hooks import Hook, HookType

@Hook(HookType.PRE_CHANNEL)
async def validate_channel_custom(channel: Channel) -> None:
    """Custom channel validation."""
    if channel.statistics.video_count > 10000:
        raise ValueError("Channel too large")

@Hook(HookType.POST_VIDEO)
async def notify_completion(video: Video, result: VideoResult) -> None:
    """Send notification after video processing."""
    if result.success:
        await send_notification(f"Processed: {video.title}")
```

### Storage Backends

```python
from youtube_transcriber.storage import StorageBackend

class S3StorageBackend(StorageBackend):
    """Amazon S3 storage backend."""
    
    async def save_transcript(
        self,
        path: Path,
        content: str,
        metadata: Dict
    ) -> str:
        """Save transcript to S3."""
        # S3 implementation
        return s3_url
    
    async def exists(self, path: Path) -> bool:
        """Check if transcript exists in S3."""
        # S3 implementation
        return exists

# Registration
from youtube_transcriber import set_storage_backend
set_storage_backend(S3StorageBackend(bucket="my-transcripts"))
```

## Examples

### Example 1: Basic Usage

```python
import asyncio
from youtube_transcriber import YouTubeTranscriber

async def main():
    # Initialize transcriber
    transcriber = YouTubeTranscriber(
        api_key="your_api_key",
        output_dir="./transcripts"
    )
    
    # Process single channel
    result = await transcriber.process_channel(
        "@mkbhd",
        language="en",
        output_format="markdown",
        recent_days=30
    )
    
    print(f"Processed {result.processed_videos} videos")
    print(f"Success rate: {result.successful_videos / result.total_videos:.1%}")

asyncio.run(main())
```

### Example 2: Batch Processing with Progress

```python
import asyncio
from youtube_transcriber import YouTubeTranscriber

async def main():
    transcriber = YouTubeTranscriber()
    
    channels = [
        "@mkbhd",
        "@LinusTechTips",
        "@UnboxTherapy"
    ]
    
    # Progress tracking
    def on_progress(event):
        print(f"[{event.channel_id}] {event.message} ({event.progress:.1%})")
    
    # Process batch
    result = await transcriber.process_batch(
        channels,
        parallel_channels=3,
        language="en",
        output_format="json",
        progress_callback=on_progress
    )
    
    # Summary
    print(f"\nProcessed {result.total_channels} channels")
    print(f"Total videos: {result.total_videos_processed}")
    print(f"Time: {result.total_processing_time:.1f}s")

asyncio.run(main())
```

### Example 3: Custom Processing Pipeline

```python
import asyncio
from youtube_transcriber import ChannelProcessor, ExportService
from youtube_transcriber.formatters import JsonFormatter

async def custom_pipeline():
    processor = ChannelProcessor()
    exporter = ExportService()
    
    # Get channel
    channel = await processor.validate_channel("@mkbhd")
    
    # Get recent videos
    videos = await processor.get_video_list(
        channel,
        date_from=datetime.now() - timedelta(days=7)
    )
    
    # Process each video
    for video in videos:
        try:
            # Download transcript
            transcript = await processor.download_transcript(video, "en")
            
            if transcript:
                # Custom processing
                word_count = sum(len(seg.text.split()) for seg in transcript.segments)
                
                # Export with metadata
                metadata = {
                    "word_count": word_count,
                    "processed_at": datetime.now().isoformat()
                }
                
                exporter.export_transcript(
                    video,
                    transcript,
                    "json",
                    Path(f"./output/{video.id}.json"),
                    metadata=metadata
                )
                
        except Exception as e:
            print(f"Error processing {video.title}: {e}")

asyncio.run(custom_pipeline())
```

## Best Practices

### 1. API Key Management

```python
# Good: Use environment variables
api_key = os.getenv("YOUTUBE_API_KEY")

# Good: Use configuration file
config = load_config("config.yaml")
api_key = config.api.youtube_api_key

# Bad: Hardcode API key
api_key = "AIzaSy..."  # Never do this!
```

### 2. Error Handling

```python
# Good: Specific error handling
try:
    result = await transcriber.process_channel(channel)
except ChannelNotFoundError:
    logger.error(f"Channel not found: {channel}")
except APIQuotaExceededError as e:
    logger.warning(f"Quota exceeded, retry after {e.reset_time}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")

# Good: Graceful degradation
result = await transcriber.process_batch(
    channels,
    continue_on_error=True  # Don't stop batch on single failure
)
```

### 3. Resource Management

```python
# Good: Use context managers
async with YouTubeTranscriber() as transcriber:
    await transcriber.process_channel("@mkbhd")

# Good: Configure limits
transcriber = YouTubeTranscriber(
    concurrent_limit=5,  # Limit concurrent operations
    memory_limit_mb=500  # Limit memory usage
)
```

### 4. Performance Optimization

```python
# Good: Batch operations
channels = ["@ch1", "@ch2", "@ch3"]
await transcriber.process_batch(channels, parallel_channels=3)

# Good: Skip existing
await transcriber.process_channel(
    channel,
    skip_existing=True  # Don't redownload
)

# Good: Filter early
videos = await processor.get_video_list(
    channel,
    date_from=datetime.now() - timedelta(days=30),
    max_videos=100  # Limit API calls
)
```

### 5. Monitoring

```python
# Good: Structured logging
logger.info(
    "Channel processed",
    channel_id=channel.id,
    videos_processed=result.processed_videos,
    success_rate=result.successful_videos / result.total_videos,
    duration=result.processing_time
)

# Good: Progress tracking
async def progress_handler(event):
    metrics.record(
        "video_processed",
        channel=event.channel_id,
        success=event.success
    )
```

## API Versioning

The YouTube Transcriber API follows semantic versioning:

- **Major version**: Breaking changes
- **Minor version**: New features, backward compatible
- **Patch version**: Bug fixes

Current version: 1.0.0

### Deprecation Policy

- Deprecated features are marked with warnings
- Minimum 6 months before removal
- Migration guides provided

### Version Compatibility

| API Version | Python Version | YouTube API |
|-------------|----------------|-------------|
| 1.0.x | 3.9+ | v3 |
| 0.9.x | 3.8+ | v3 |

---

For the latest updates and more examples, visit the [GitHub repository](https://github.com/yourusername/youtube-transcriber).