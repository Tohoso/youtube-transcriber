# ProcessingStatistics API Documentation

## Overview

The `ProcessingStatistics` model provides comprehensive tracking and analysis of YouTube channel transcript processing. It includes real-time progress monitoring, error analysis, and performance metrics.

## Model Structure

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_videos` | int | Total number of videos in the channel |
| `processed_videos` | int | Number of videos that have been processed |
| `successful_videos` | int | Number of successfully processed videos |
| `failed_videos` | int | Number of videos that failed processing |
| `skipped_videos` | int | Number of videos that were skipped |
| `successful_transcripts` | int | Legacy: Same as successful_videos |
| `failed_transcripts` | int | Legacy: Same as failed_videos |
| `processing_start_time` | datetime | When processing started |
| `last_update_time` | datetime | Last statistics update timestamp |
| `average_processing_time` | float | Average time to process each video (seconds) |
| `error_statistics` | Dict[str, int] | Count of errors by error type |

### Computed Properties

#### `progress_percentage`
- **Type**: float
- **Description**: Processing progress as percentage (0-100)
- **Formula**: `(processed_videos / total_videos) * 100`

#### `success_rate`
- **Type**: float
- **Description**: Success rate of processed videos (0-1)
- **Formula**: `successful_videos / processed_videos`

#### `completion_rate`
- **Type**: float
- **Description**: Completion rate of all videos (0-1)
- **Formula**: `processed_videos / total_videos`

#### `estimated_time_remaining`
- **Type**: Optional[timedelta]
- **Description**: Estimated time to complete processing
- **Formula**: `(total_videos - processed_videos) * average_processing_time`

## Methods

### `update_error_statistics(error_type: str)`
Update error count for a specific error type.

```python
stats.update_error_statistics("Network Error")
```

### `get_error_summary() -> Dict[str, Any]`
Get comprehensive error analysis.

**Returns:**
```python
{
    "total_errors": 45,
    "error_types": {
        "Network Error": 25,
        "Transcript Error": 15,
        "Permission Error": 5
    },
    "error_percentages": {
        "Network Error": 55.6,
        "Transcript Error": 33.3,
        "Permission Error": 11.1
    },
    "most_common_error": "Network Error"
}
```

### `update_processing_time(video_processing_time: float)`
Update average processing time with a new measurement.

```python
stats.update_processing_time(5.5)  # Video took 5.5 seconds
```

### `get_processing_rate() -> Optional[float]`
Calculate videos processed per hour.

**Returns:** Videos per hour as float, or None if not enough data

### `calculate_statistics_summary() -> Dict[str, Any]`
Generate comprehensive statistics summary.

**Returns:**
```python
{
    "progress": {
        "total_videos": 500,
        "processed_videos": 450,
        "successful_videos": 400,
        "failed_videos": 40,
        "skipped_videos": 10,
        "progress_percentage": 90.0,
        "completion_rate": 0.9,
        "success_rate": 0.889
    },
    "time_metrics": {
        "processing_start_time": datetime(2024, 1, 1, 10, 0, 0),
        "last_update_time": datetime(2024, 1, 1, 11, 30, 0),
        "average_processing_time": 5.2,
        "estimated_time_remaining": timedelta(minutes=4, seconds=20),
        "processing_rate": 300.0  # videos per hour
    },
    "error_analysis": {
        "total_errors": 40,
        "error_types": {...},
        "error_percentages": {...},
        "most_common_error": "Network Error"
    }
}
```

## Integration with Channel Model

### Automatic Updates

The `Channel` model automatically updates `ProcessingStatistics` when the videos list changes:

```python
channel = Channel(id="UC123", snippet=snippet)
channel.videos = [video1, video2, video3]  # Stats auto-update
```

### Manual Update

Force statistics recalculation:

```python
channel.update_processing_statistics()
```

### Statistics Report

Generate a formatted text report:

```python
report = channel.get_statistics_report()
print(report)
```

Output:
```
Processing Statistics for Channel Name
==================================================
Total Videos: 100
Processed: 85 (85.0%)
Successful: 75
Failed: 8
Skipped: 2
Success Rate: 88.2%
Estimated Time Remaining: 00:15:30

Error Analysis:
  - Network Error: 5 (62.5%)
  - Timeout Error: 3 (37.5%)
```

## Integration with Video Model

### Error Classification

Videos can classify their errors:

```python
error_type = video.get_error_classification()
# Returns: "Network Error", "Transcript Error", etc.
```

### Retry Recommendation

Check if a video should be retried:

```python
if video.is_retry_recommended():
    # Retry the video
    pass
```

### Processing Efficiency

Calculate processing efficiency:

```python
efficiency = video.calculate_processing_efficiency()
# Returns ratio of video duration to processing time
```

## Display Integration

### Basic Statistics Display

```python
display_manager.show_processing_stats(channel.processing_stats)
```

### Enhanced Statistics Display

```python
display_manager.show_enhanced_statistics(channel)
```

This shows:
- Progress metrics panel
- Time metrics panel
- Error analysis panel

## Usage Examples

### Basic Usage

```python
from src.models.channel import Channel, ChannelSnippet

# Create channel
channel = Channel(
    id="UCXuqSBlHAE6Xw-yeJA0Tunw",
    snippet=ChannelSnippet(title="Tech Channel")
)

# Add videos and process
channel.videos = fetch_channel_videos(channel.id)
channel.processing_stats.processing_start_time = datetime.now()

# Process videos
for video in channel.videos:
    start_time = time.time()
    result = process_video(video)
    processing_time = time.time() - start_time
    
    if result.success:
        video.transcript_status = TranscriptStatus.SUCCESS
        channel.processing_stats.update_processing_time(processing_time)
    else:
        video.transcript_status = TranscriptStatus.ERROR
        video.error_message = result.error
        channel.processing_stats.update_error_statistics(
            video.get_error_classification()
        )

# Update and display statistics
channel.update_processing_statistics()
print(channel.get_statistics_report())
```

### Real-time Progress Monitoring

```python
async def process_channel_with_progress(channel: Channel):
    """Process channel with real-time progress updates."""
    
    with display_manager.live:
        task_id = display_manager.add_task(
            "Processing videos", 
            total=len(channel.videos)
        )
        
        for video in channel.videos:
            # Process video
            await process_video_async(video)
            
            # Update statistics
            channel.update_processing_statistics()
            
            # Update display
            display_manager.update_task(task_id, advance=1)
            display_manager.show_processing_stats(
                channel.processing_stats
            )
            
            # Show time estimate
            if channel.processing_stats.estimated_time_remaining:
                remaining = channel.processing_stats.estimated_time_remaining
                print(f"Estimated time remaining: {remaining}")
```

### Error Analysis and Reporting

```python
# After processing
error_summary = channel.processing_stats.get_error_summary()

if error_summary['total_errors'] > 0:
    print(f"Total Errors: {error_summary['total_errors']}")
    print(f"Most Common: {error_summary['most_common_error']}")
    
    # Identify videos for retry
    for video in channel.videos:
        if video.is_retry_recommended():
            print(f"Retry recommended: {video.title}")
```

## Performance Considerations

1. **Automatic Updates**: The field validator runs on every video list assignment. For large lists, consider batching updates.

2. **Error Statistics**: Error statistics are stored in memory. For very long-running processes, consider periodic persistence.

3. **Time Estimation**: Accuracy improves with more processed videos. Early estimates may be less reliable.

## Best Practices

1. **Initialize Start Time**: Always set `processing_start_time` before beginning processing
2. **Regular Updates**: Call `update_processing_statistics()` periodically for accurate tracking
3. **Error Classification**: Use consistent error type names for meaningful analysis
4. **Progress Display**: Update display frequently for better user experience
5. **Batch Processing**: For large channels, process in batches and update statistics between batches