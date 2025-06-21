# YouTube Transcriber

YouTube channel transcript extraction CLI application.

## Installation

```bash
pip install -e .
```

## Usage

```bash
youtube-transcriber <channel_url> [options]
```

## Features

- Extract transcripts from all videos in a YouTube channel
- Multiple output formats (TXT, JSON, CSV, Markdown)
- Parallel processing for fast extraction
- Robust error handling and retry mechanisms
- Real-time progress display

## Requirements

- Python 3.9+
- YouTube API key (set as YOUTUBE_API_KEY environment variable)

## Configuration

Create a `.env` file with:
```
YOUTUBE_API_KEY=your_api_key_here
```

Or use a config file:
```bash
youtube-transcriber <channel_url> --config config.yaml
```

## Examples

```bash
# Basic usage
youtube-transcriber https://www.youtube.com/@channel_name

# With options
youtube-transcriber @channel_name --format json --output-dir ./transcripts --concurrent 10

# Generate sample config
youtube-transcriber config --generate
```

## License

MIT