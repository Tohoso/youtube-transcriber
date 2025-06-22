# YouTube Transcriber 🎥📝

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)
[![日本語](https://img.shields.io/badge/lang-日本語-green.svg)](README.ja.md)

**Extract transcripts from YouTube channels with ease!**

[Features](#-features) • [Quick Start](#-quick-start) • [Installation](#-installation) • [Usage](#-usage) • [Multi-Channel](#-multi-channel-processing-new) • [FAQ](#-faq)

</div>

---

## 🎯 What is YouTube Transcriber?

YouTube Transcriber is a powerful command-line tool that automatically downloads transcripts (subtitles) from YouTube videos. Whether you need to archive a channel's content, analyze video transcripts, or create searchable text databases, this tool makes it simple and efficient.

### 💡 Perfect for:
- 📚 **Researchers** - Analyze video content at scale
- 📰 **Journalists** - Quickly search through video transcripts
- 🎓 **Students** - Create study materials from educational videos
- 🏢 **Businesses** - Archive company YouTube content
- 🌐 **Content Creators** - Backup your channel's transcripts

## ✨ Features

<table>
<tr>
<td>

### 🚀 High Performance
- **Parallel Processing** - Download multiple transcripts simultaneously
- **Smart Caching** - Skip already downloaded content
- **Batch Operations** - Process multiple channels at once

</td>
<td>

### 📊 Flexible Output
- **Multiple Formats** - TXT, JSON, CSV, Markdown
- **Custom Templates** - Configure output structure
- **Metadata Export** - Save video information

</td>
</tr>
<tr>
<td>

### 🛡️ Robust & Reliable
- **Auto-Retry** - Handle network issues gracefully
- **Error Recovery** - Continue from interruptions
- **Rate Limiting** - Respect API quotas

</td>
<td>

### 🌍 International
- **Multi-language** - Extract subtitles in any language
- **Auto-translation** - Fall back to auto-generated captions
- **Unicode Support** - Handle all character sets

</td>
</tr>
</table>

## 🚀 Quick Start

Get up and running in under 5 minutes!

```bash
# 1. Install
pip install youtube-transcriber

# 2. Set your API key
export YOUTUBE_API_KEY="your_api_key_here"

# 3. Download transcripts
youtube-transcriber @mkbhd
```

That's it! Check the `output/` folder for your transcripts.

## 📦 Installation

### Prerequisites

- **Python 3.9+** ([Download Python](https://www.python.org/downloads/))
- **YouTube API Key** ([Get your free key](#-getting-your-youtube-api-key))

### Option 1: Install from PyPI (Recommended)

```bash
pip install youtube-transcriber
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-transcriber.git
cd youtube-transcriber

# Install with pip
pip install -e .
```

### Verify Installation

```bash
youtube-transcriber --version
# Output: YouTube Transcriber v1.0.0
```

## 🔑 Getting Your YouTube API Key

<details>
<summary>📋 Step-by-step guide (click to expand)</summary>

1. **Go to Google Cloud Console**
   - Visit [console.cloud.google.com](https://console.cloud.google.com)
   - Sign in with your Google account

2. **Create a New Project**
   - Click "Select a project" → "New Project"
   - Name it (e.g., "YouTube Transcriber")
   - Click "Create"

3. **Enable YouTube Data API**
   - Go to "APIs & Services" → "Library"
   - Search for "YouTube Data API v3"
   - Click on it and press "Enable"

4. **Create API Key**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy your API key

5. **Set the API Key**
   ```bash
   # Option 1: Environment variable (recommended)
   export YOUTUBE_API_KEY="your_api_key_here"
   
   # Option 2: Create .env file
   echo "YOUTUBE_API_KEY=your_api_key_here" > .env
   ```

</details>

## 📖 Usage

### Basic Usage

```bash
# Using channel handle
youtube-transcriber @channelname

# Using channel URL
youtube-transcriber https://youtube.com/@channelname

# Using channel ID
youtube-transcriber UCxxxxxxxxxxxxxx
```

### Real-time Progress Display

```
Channel: Marques Brownlee
Total Videos: 1,543
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 00:05:23

✅ iPhone 15 Pro Review (2,345 words)
✅ Tesla Model S Plaid (3,456 words)
⏳ Processing: Apple Vision Pro First Look...
```

### Command Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--output-dir` | `-o` | Output directory | `-o ./transcripts` |
| `--format` | `-f` | Output format | `-f json` |
| `--language` | `-l` | Subtitle language | `-l en` |
| `--concurrent` | `-c` | Parallel downloads | `-c 10` |
| `--date-from` | | Start date filter | `--date-from 2024-01-01` |
| `--date-to` | | End date filter | `--date-to 2024-12-31` |

### Examples

#### 📄 Different Output Formats

```bash
# JSON format (structured data)
youtube-transcriber @mkbhd --format json

# Markdown format (readable)
youtube-transcriber @mkbhd --format markdown

# CSV format (for spreadsheets)
youtube-transcriber @mkbhd --format csv
```

#### 🌐 Language Selection

```bash
# English subtitles
youtube-transcriber @mkbhd --language en

# Japanese subtitles
youtube-transcriber @mkbhd --language ja

# Spanish subtitles
youtube-transcriber @mkbhd --language es
```

#### 📅 Date Filtering

```bash
# Videos from 2024 only
youtube-transcriber @mkbhd --date-from 2024-01-01 --date-to 2024-12-31

# Last 30 days
youtube-transcriber @mkbhd --date-from $(date -d '30 days ago' +%Y-%m-%d)
```

## 🎯 Multi-Channel Processing (NEW!)

Process multiple YouTube channels efficiently with our new batch processing feature!

### Interactive Mode

The easiest way to process multiple channels:

```bash
youtube-transcriber interactive
```

<details>
<summary>📸 Interactive Mode Demo (click to expand)</summary>

```
┌─────────────────────────────────────────────────────┐
│ YouTube Transcriber - Multi-Channel Processing      │
│                                                     │
│ Features:                                           │
│ • Add multiple channels at once                     │
│ • Search YouTube for channels                       │
│ • Filter and sort your selection                    │
│ • Validate channels before processing               │
└─────────────────────────────────────────────────────┘

What would you like to do? [add/search/filter/sort/validate/proceed/quit]: add

Add Channels
Enter channel URLs, @handles, or IDs (one per line)
Press Enter twice to finish

[1] @mkbhd
✅ Added: @mkbhd
[2] @LinusTechTips
✅ Added: @LinusTechTips
[3] @UnboxTherapy
✅ Added: @UnboxTherapy
[4] 

Channel Selection (3 total)
┌───┬──────────────────┬──────────┬─────────────┬────────┐
│ # │ Channel          │ Status   │ Subscribers │ Videos │
├───┼──────────────────┼──────────┼─────────────┼────────┤
│ 1 │ @mkbhd          │ ✅ Valid │ 18.1M       │ 1,543  │
│ 2 │ @LinusTechTips  │ ✅ Valid │ 15.4M       │ 5,678  │
│ 3 │ @UnboxTherapy   │ ✅ Valid │ 18.2M       │ 2,345  │
└───┴──────────────────┴──────────┴─────────────┴────────┘

What would you like to do? proceed

Processing 3 channels...
```

</details>

### Batch File Mode

Process channels from a file:

```bash
# Create a file with channel list
cat > channels.txt << EOF
# Tech Channels
@mkbhd
@LinusTechTips
@UnboxTherapy

# News Channels
@verge
@CNBC
EOF

# Process all channels
youtube-transcriber batch channels.txt
```

### Live Progress Display

```
YouTube Transcriber - Multi-Channel Processing

Total Channels: 5
Total Videos: 12,543
Processed: 5,234
Processing Rate: 45.2 videos/min

█████████████████░░░░░░░░░░░░░░░░ 41.7% (5234/12543)

┌─────────────────┬────────────────┬─────────┬─────────┬────────┬──────────┬───────┐
│ Channel         │ Progress       │ Status  │ Success │ Failed │ Rate     │ ETA   │
├─────────────────┼────────────────┼─────────┼─────────┼────────┼──────────┼───────┤
│ MKBHD          │ ██████████ 100%│ ✅ Done │ 1,543   │ 0      │ 32.1 v/h │ -     │
│ Linus Tech Tips │ ████░░░░░░ 42% │ ⚡ Active│ 2,385   │ 12     │ 28.5 v/h │ 3h 2m │
│ Unbox Therapy   │ ░░░░░░░░░░ 0%  │ ⏳ Wait  │ 0       │ 0      │ -        │ -     │
│ The Verge       │ ░░░░░░░░░░ 0%  │ ⏳ Wait  │ 0       │ 0      │ -        │ -     │
│ CNBC           │ ░░░░░░░░░░ 0%  │ ⏳ Wait  │ 0       │ 0      │ -        │ -     │
└─────────────────┴────────────────┴─────────┴─────────┴────────┴──────────┴───────┘
```

### Advanced Multi-Channel Options

```bash
# Process large channels only (>1M subscribers)
youtube-transcriber batch channels.txt --filter large

# Sort by subscriber count
youtube-transcriber batch channels.txt --sort subscribers

# Limit parallel channels
youtube-transcriber batch channels.txt --parallel-channels 2

# Resume interrupted batch
youtube-transcriber batch channels.txt --resume
```

## 📁 Output Structure

```
output/
├── mkbhd/
│   ├── channel_info.json           # Channel metadata
│   ├── processing_stats.json       # Processing statistics
│   ├── videos/
│   │   ├── 2024-01-15_iPhone_15_Review_abc123.txt
│   │   ├── 2024-02-20_Tesla_Update_def456.txt
│   │   └── ...
│   └── metadata/
│       └── video_metadata.json     # All video information
├── LinusTechTips/
│   └── ...
└── summary_report.html            # Visual summary of all channels
```

## ⚙️ Configuration

### Generate Configuration File

```bash
youtube-transcriber config --generate
```

### Example Configuration

```yaml
# config.yaml
api:
  youtube_api_key: ${YOUTUBE_API_KEY}
  quota_limit: 10000                # Daily API quota

processing:
  concurrent_limit: 5               # Parallel video downloads
  retry_attempts: 3                 # Retry failed downloads
  rate_limit_per_minute: 60        # API calls per minute
  
output:
  default_format: txt              # txt, json, csv, md
  output_directory: ./output
  filename_template: "{date}_{title}_{video_id}"
  
# Multi-channel settings
batch:
  max_channels: 5                  # Process 5 channels simultaneously
  channel_delay: 5                 # Seconds between channels
  save_progress: true             # Enable resume feature
```

### Use Configuration

```bash
youtube-transcriber @mkbhd --config config.yaml
```

## 🔧 Advanced Features

### Dry Run Mode

Test without downloading:

```bash
youtube-transcriber @mkbhd --dry-run
# Shows what would be downloaded without actually downloading
```

### Export Formats

<table>
<tr>
<th>TXT (Default)</th>
<th>JSON</th>
</tr>
<tr>
<td>

```text
iPhone 15 Pro Review
2024-01-15

So I've been using the iPhone 15 Pro
for about two weeks now and I have
some thoughts...
```

</td>
<td>

```json
{
  "video_id": "abc123",
  "title": "iPhone 15 Pro Review",
  "date": "2024-01-15",
  "segments": [
    {
      "text": "So I've been using...",
      "start": 0.0,
      "duration": 4.5
    }
  ]
}
```

</td>
</tr>
</table>

### Error Handling

The tool handles errors gracefully:

- **Network Issues** → Automatic retry with exponential backoff
- **Rate Limiting** → Automatic pause and resume
- **No Subtitles** → Skip and log, continue with next video
- **API Quota** → Clear warning with reset time

## 📊 Statistics & Reporting

After processing, view detailed statistics:

```
═══════════════════════════════════════════════════════════
                    Processing Complete
═══════════════════════════════════════════════════════════

Channel: MKBHD
Total Videos: 1,543
Processed: 1,543
Successful: 1,521 (98.6%)
Failed: 22 (1.4%)
Total Words: 2,845,123
Processing Time: 48m 23s
Average Speed: 31.9 videos/min

Error Breakdown:
- No transcript available: 15 videos
- Private videos: 5 videos
- Network errors: 2 videos

Output saved to: ./output/mkbhd/
```

## ❓ FAQ

<details>
<summary><strong>How many videos can I process?</strong></summary>

With the free YouTube API quota (10,000 units/day), you can process approximately:
- Single channel: 500-1000 videos/day
- Checking video info: ~3 units
- Downloading transcript: ~0 units (no API cost)
</details>

<details>
<summary><strong>What if a video has no subtitles?</strong></summary>

The tool will:
1. Try to get manual subtitles
2. Fall back to auto-generated subtitles
3. Skip if none available (logged in report)
</details>

<details>
<summary><strong>Can I resume if interrupted?</strong></summary>

Yes! The tool automatically skips already downloaded transcripts. Just run the same command again.
</details>

<details>
<summary><strong>What languages are supported?</strong></summary>

All YouTube subtitle languages. Use language codes like:
- `en` - English
- `es` - Spanish
- `ja` - Japanese
- `ko` - Korean
- [Full list](https://developers.google.com/youtube/v3/docs/i18nLanguages/list)
</details>

## 🧪 Development

### Setup Development Environment

```bash
# Clone repo
git clone https://github.com/yourusername/youtube-transcriber.git
cd youtube-transcriber

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src tests/

# Specific test file
pytest tests/test_cli.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with these awesome libraries:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube video downloader
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - Transcript extraction
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Beautiful terminal formatting

## 💬 Support & Community

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/yourusername/youtube-transcriber/issues)
- 💡 **Feature Requests**: [Discussions](https://github.com/yourusername/youtube-transcriber/discussions)
- 💬 **Questions**: [Discussions](https://github.com/yourusername/youtube-transcriber/discussions)
- 📧 **Email**: support@youtube-transcriber.com

## 🚨 Disclaimer

This tool is for educational and research purposes. Please:
- Respect YouTube's Terms of Service
- Don't overload the API
- Credit content creators
- Use transcripts responsibly

---

<div align="center">

**Made with ❤️ by the YouTube Transcriber Team**

[⬆ Back to top](#youtube-transcriber-)

</div>