# YouTube Transcriber

A CLI application for extracting transcripts from all videos in a YouTube channel

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![日本語](https://img.shields.io/badge/lang-日本語-green.svg)](README.ja.md)

## 📋 Overview

YouTube Transcriber is a command-line tool that automatically extracts transcripts (subtitles) from all videos in a specified YouTube channel and saves them in various formats.

### ✨ Key Features

- 🚀 **Fast Parallel Processing** - Download multiple video transcripts simultaneously
- 📊 **Multiple Output Formats** - Support for TXT, JSON, CSV, and Markdown
- 🔄 **Automatic Retry** - Auto-retry on network errors
- 📈 **Progress Display** - Real-time processing status and statistics
- 🛡️ **Robust Error Handling** - Handle various error scenarios gracefully
- 🌐 **Multi-language Support** - Extract subtitles in any language
- 📅 **Date Filtering** - Filter videos by date range

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- YouTube Data API v3 key ([How to obtain](#obtaining-youtube-api-key))

### Installation

```bash
# Clone the repository
git clone https://github.com/Tohoso/youtube-transcriber.git
cd youtube-transcriber

# Install dependencies
pip install -e .
```

### Basic Usage

```bash
# Set API key as environment variable
export YOUTUBE_API_KEY="your_api_key_here"

# Extract transcripts from all videos in a channel
youtube-transcriber https://www.youtube.com/@channel_name

# Or use channel handle directly
youtube-transcriber @channel_name
```

## 📖 Detailed Usage

### Command Line Options

```bash
youtube-transcriber [CHANNEL_INPUT] [OPTIONS]
```

#### Arguments

- `channel_input` - YouTube channel URL, ID, or @handle

#### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output-dir` | `-o` | Output directory | `./output` |
| `--format` | `-f` | Output format (txt/json/csv/md) | `txt` |
| `--language` | `-l` | Transcript language code | `ja` |
| `--concurrent` | `-c` | Number of concurrent downloads | `5` |
| `--date-from` | - | Start date (YYYY-MM-DD) | - |
| `--date-to` | - | End date (YYYY-MM-DD) | - |
| `--config` | - | Configuration file path | - |
| `--dry-run` | - | Test run without downloading | `False` |

### Examples

#### 1. Specify Output Format

```bash
# Output in JSON format
youtube-transcriber @channel_name --format json

# Save as Markdown in specific directory
youtube-transcriber @channel_name --format md --output-dir ./transcripts
```

#### 2. Specify Language

```bash
# Get English subtitles
youtube-transcriber @channel_name --language en

# Get Korean subtitles
youtube-transcriber @channel_name --language ko
```

#### 3. Filter by Date

```bash
# Only videos from 2024
youtube-transcriber @channel_name --date-from 2024-01-01 --date-to 2024-12-31

# Recent month's videos
youtube-transcriber @channel_name --date-from 2024-11-01
```

#### 4. Adjust Concurrency

```bash
# Fast processing with 10 parallel downloads
youtube-transcriber @channel_name --concurrent 10

# Sequential processing (stable)
youtube-transcriber @channel_name --concurrent 1
```

### Configuration File

Create a YAML configuration file for complex settings.

#### Generate Sample Config

```bash
youtube-transcriber config --generate
```

#### Example config.yaml

```yaml
api:
  youtube_api_key: ${YOUTUBE_API_KEY}
  quota_limit: 10000

processing:
  concurrent_limit: 5
  retry_attempts: 3
  retry_delay: 1.0
  rate_limit_per_minute: 60
  timeout_seconds: 30
  skip_private_videos: true
  skip_live_streams: true

output:
  default_format: txt
  output_directory: ./output
  filename_template: "{date}_{title}_{video_id}"
  include_metadata: true
  include_timestamps: false
  max_filename_length: 100

logging:
  level: INFO
  log_file: logs/app.log
  max_file_size: "500 MB"
  retention_days: 10
  enable_json_logging: false
```

Run with config file:

```bash
youtube-transcriber @channel_name --config config.yaml
```

## 📁 Output File Structure

```
output/
└── channel_name/
    ├── channel_info.json          # Channel information
    ├── processing_stats.json      # Processing statistics
    ├── videos/
    │   ├── 2024-01-01_video_title_abc123.txt
    │   ├── 2024-01-02_another_video_def456.txt
    │   └── ...
    └── metadata/
        ├── abc123.json           # Video metadata
        ├── def456.json
        └── ...
```

## 🔧 Advanced Features

### Processing Statistics

The application provides detailed processing statistics:

- Total and processed video counts
- Success and failure rates
- Error analysis by type
- Estimated time remaining
- Processing rate (videos/hour)

### Error Handling

Automatic handling of common errors:

- Network errors → Automatic retry
- Rate limiting → Automatic wait
- No subtitles → Skip and continue
- API limits → Appropriate error messages

## 🔑 Obtaining YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Navigate to "APIs & Services" → "Library"
4. Search for "YouTube Data API v3"
5. Enable the API
6. Go to "Credentials" → "Create Credentials" → "API Key"
7. Copy the generated API key

### Setting the API Key

#### Method 1: Environment Variable (Recommended)

```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

#### Method 2: .env File

Create `.env` file in project root:

```
YOUTUBE_API_KEY=your_api_key_here
```

#### Method 3: Config File

Add directly to `config.yaml` (be careful with security)

## 🧪 Development

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Coverage report
pytest --cov=src tests/

# Code formatting
black src/ tests/

# Linting
ruff check src/ tests/
```

### Architecture

```
src/
├── cli/           # CLI interface
├── models/        # Pydantic data models
├── services/      # Business logic
├── repositories/  # External API integration
└── utils/         # Utilities
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Powerful video download library
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - YouTube transcript API
- [Typer](https://typer.tiangolo.com/) - Excellent CLI framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal output

## 📞 Support

- Bug Reports: [Issues](https://github.com/Tohoso/youtube-transcriber/issues)
- Feature Requests: [Discussions](https://github.com/Tohoso/youtube-transcriber/discussions)
- Questions: [Discussions](https://github.com/Tohoso/youtube-transcriber/discussions)

## 🚨 Disclaimer

This tool is created for educational and research purposes. Please comply with YouTube's Terms of Service and respect copyright. Excessive API requests may be rate limited.