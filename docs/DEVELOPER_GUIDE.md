# YouTube Transcriber Developer Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Contributing](#contributing)
7. [Architecture Overview](#architecture-overview)
8. [Extension Development](#extension-development)
9. [Debugging](#debugging)
10. [Performance Optimization](#performance-optimization)
11. [Release Process](#release-process)

## Getting Started

Welcome to the YouTube Transcriber development team! This guide will help you set up your development environment and understand our development practices.

### Prerequisites

Before you begin, ensure you have:

- Python 3.9 or higher
- Git
- A YouTube Data API key
- Basic knowledge of async Python programming
- Familiarity with terminal/command line

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/youtube-transcriber.git
cd youtube-transcriber

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Run tests to verify setup
pytest
```

## Development Environment Setup

### 1. Virtual Environment

Always use a virtual environment to isolate dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Verify activation
which python  # Should point to venv/bin/python
```

### 2. Install Dependencies

We use Poetry for dependency management:

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install all dependencies
poetry install

# Install with development dependencies
poetry install --with dev

# Or using pip with editable install
pip install -e ".[dev]"
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
# .env
YOUTUBE_API_KEY=your_api_key_here
YOUTUBE_TRANSCRIBER_LOG_LEVEL=DEBUG
YOUTUBE_TRANSCRIBER_OUTPUT_DIR=./test_output
```

### 4. IDE Setup

#### VS Code
```json
// .vscode/settings.json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestArgs": ["tests"],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

#### PyCharm
1. Set Project Interpreter to your virtual environment
2. Enable pytest as the test runner
3. Configure Black as the code formatter
4. Enable type checking with mypy

### 5. Pre-commit Hooks

We use pre-commit hooks to maintain code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Configuration (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

## Project Structure

```
youtube-transcriber/
├── src/                      # Source code
│   ├── __init__.py
│   ├── application/         # Application layer (orchestration)
│   │   ├── orchestrator.py
│   │   └── batch_orchestrator.py
│   ├── cli/                 # CLI interface
│   │   ├── main.py         # Entry point
│   │   ├── display.py      # UI components
│   │   └── multi_channel_interface.py
│   ├── models/             # Data models
│   │   ├── channel.py
│   │   ├── video.py
│   │   └── transcript.py
│   ├── repositories/       # Data access layer
│   │   ├── youtube_api.py
│   │   └── transcript_api.py
│   ├── services/          # Business logic
│   │   ├── channel_service.py
│   │   ├── transcript_service.py
│   │   └── export_service.py
│   └── utils/            # Utilities
│       ├── logging.py
│       ├── retry.py
│       └── error_handlers.py
├── tests/                # Test files
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/            # End-to-end tests
├── docs/               # Documentation
├── scripts/            # Utility scripts
├── pyproject.toml      # Project configuration
├── poetry.lock         # Locked dependencies
└── README.md          # Project readme
```

### Key Directories

- **`src/application/`**: High-level orchestration logic
- **`src/cli/`**: Command-line interface and display components
- **`src/models/`**: Pydantic models for data validation
- **`src/repositories/`**: External API interactions
- **`src/services/`**: Core business logic
- **`src/utils/`**: Shared utilities and helpers

## Coding Standards

### 1. Python Style Guide

We follow PEP 8 with some modifications:

```python
# Good: Clear variable names
channel_videos = await get_channel_videos(channel_id)

# Bad: Unclear abbreviations
ch_vids = await get_ch_vids(ch_id)

# Good: Type hints
def process_transcript(
    video_id: str,
    language: str = "en"
) -> Optional[Transcript]:
    ...

# Good: Docstrings
def calculate_statistics(videos: List[Video]) -> Statistics:
    """
    Calculate aggregate statistics for a list of videos.
    
    Args:
        videos: List of Video objects to analyze
        
    Returns:
        Statistics object containing aggregated data
        
    Raises:
        ValueError: If videos list is empty
    """
    ...
```

### 2. Async/Await Best Practices

```python
# Good: Concurrent operations
async def process_videos(video_ids: List[str]) -> List[Result]:
    tasks = [process_video(vid) for vid in video_ids]
    return await asyncio.gather(*tasks)

# Good: Proper cleanup
async def download_with_timeout(url: str, timeout: int = 30):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=timeout) as response:
            return await response.text()

# Good: Error handling in async
async def safe_process(video_id: str) -> Optional[Result]:
    try:
        return await process_video(video_id)
    except Exception as e:
        logger.error(f"Error processing {video_id}: {e}")
        return None
```

### 3. Type Hints

Always use type hints for better code clarity:

```python
from typing import List, Optional, Dict, Tuple, Union
from pathlib import Path

# Function signatures
async def get_transcripts(
    video_ids: List[str],
    language: str = "en"
) -> Dict[str, Optional[Transcript]]:
    ...

# Class attributes
class ChannelProcessor:
    channel: Channel
    videos: List[Video]
    config: ProcessingConfig
    _cache: Dict[str, Any]
```

### 4. Error Handling

```python
# Good: Specific exceptions
class ChannelNotFoundError(Exception):
    """Raised when a YouTube channel cannot be found."""
    pass

class TranscriptNotAvailableError(Exception):
    """Raised when no transcript is available for a video."""
    def __init__(self, video_id: str, available_languages: List[str]):
        self.video_id = video_id
        self.available_languages = available_languages
        super().__init__(
            f"No transcript for video {video_id}. "
            f"Available: {', '.join(available_languages)}"
        )

# Good: Error context
try:
    transcript = await get_transcript(video_id)
except TranscriptNotAvailableError as e:
    logger.warning(f"Transcript not available: {e}")
    # Graceful fallback
    return None
```

### 5. Logging Best Practices

```python
from loguru import logger

# Good: Structured logging
logger.info(
    "Channel processed",
    channel_id=channel.id,
    channel_title=channel.title,
    video_count=len(videos),
    duration=processing_time
)

# Good: Appropriate log levels
logger.debug("Starting video download", video_id=video.id)
logger.info("Video processed successfully", video_id=video.id)
logger.warning("Retry attempt", attempt=retry_count, max_attempts=3)
logger.error("Processing failed", error=str(e), traceback=True)
```

## Testing Guidelines

### 1. Test Structure

```python
# tests/unit/test_channel_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.services.channel_service import ChannelService

class TestChannelService:
    """Test cases for ChannelService."""
    
    @pytest.fixture
    def channel_service(self):
        """Create ChannelService instance with mocked dependencies."""
        youtube_api = Mock()
        return ChannelService(youtube_api)
    
    async def test_get_channel_by_handle(self, channel_service):
        """Test getting channel by @handle."""
        # Arrange
        channel_service.youtube_api.get_channel = AsyncMock(
            return_value={"id": "123", "title": "Test Channel"}
        )
        
        # Act
        channel = await channel_service.get_channel("@testchannel")
        
        # Assert
        assert channel.id == "123"
        assert channel.title == "Test Channel"
```

### 2. Test Categories

#### Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Fast execution
- Location: `tests/unit/`

```python
# Example unit test
async def test_format_transcript():
    formatter = TextFormatter()
    transcript = create_mock_transcript()
    
    result = formatter.format(transcript)
    
    assert "Test Video Title" in result
    assert len(result.split('\n')) > 10
```

#### Integration Tests
- Test component interactions
- Use real dependencies where possible
- Location: `tests/integration/`

```python
# Example integration test
@pytest.mark.integration
async def test_channel_video_download():
    service = ChannelService()
    videos = await service.get_channel_videos("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    
    assert len(videos) > 0
    assert all(v.channel_id == "UC_x5XG1OV2P6uZZ5FSM9Ttw" for v in videos)
```

#### End-to-End Tests
- Test complete workflows
- Simulate real user scenarios
- Location: `tests/e2e/`

```python
# Example E2E test
@pytest.mark.e2e
async def test_complete_channel_processing(tmp_path):
    """Test processing a channel from start to finish."""
    transcriber = YouTubeTranscriber(output_dir=tmp_path)
    
    result = await transcriber.process_channel(
        "@testchannel",
        max_videos=5
    )
    
    assert result.successful_videos >= 3
    assert (tmp_path / "testchannel").exists()
```

### 3. Test Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir

@pytest.fixture
def mock_youtube_api():
    """Create mock YouTube API client."""
    api = Mock()
    api.get_channel.return_value = {
        "id": "test123",
        "snippet": {"title": "Test Channel"}
    }
    return api

@pytest.fixture
async def sample_transcript():
    """Create sample transcript for testing."""
    return Transcript(
        video_id="abc123",
        language="en",
        segments=[
            TranscriptSegment(text="Hello", start=0.0, duration=1.0),
            TranscriptSegment(text="World", start=1.0, duration=1.0)
        ]
    )
```

### 4. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_channel_service.py

# Run specific test
pytest tests/unit/test_channel_service.py::test_get_channel

# Run by marker
pytest -m "not integration"  # Skip integration tests
pytest -m e2e  # Only E2E tests

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

## Contributing

### 1. Development Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/add-new-formatter

# 2. Make changes and test
# ... edit files ...
pytest tests/

# 3. Commit with descriptive message
git add .
git commit -m "feat: Add XML formatter for transcript export"

# 4. Push and create PR
git push origin feature/add-new-formatter
```

### 2. Commit Message Convention

We follow Conventional Commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

Examples:
```bash
feat(formatter): Add XML export format
fix(api): Handle rate limit errors gracefully
docs(readme): Update installation instructions
test(channel): Add edge case tests for channel validation
```

### 3. Pull Request Guidelines

#### PR Title
Follow the same convention as commit messages

#### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings
```

### 4. Code Review Process

1. **Self-review** before requesting review
2. **Automated checks** must pass
3. **At least one approval** required
4. **Address all feedback** or discuss
5. **Squash and merge** when approved

## Architecture Overview

### Layered Architecture

```
┌─────────────────┐
│   CLI Layer     │  User interaction
├─────────────────┤
│ Application     │  Orchestration
├─────────────────┤
│   Service       │  Business logic
├─────────────────┤
│  Repository     │  Data access
└─────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**: Each layer has specific responsibilities
2. **Dependency Injection**: Services receive dependencies via constructor
3. **Interface Segregation**: Small, focused interfaces
4. **Single Responsibility**: Each class has one reason to change

### Adding New Features

#### Example: Adding a New Export Format

1. **Create Formatter Class**
```python
# src/services/formatters/xml_formatter.py
from .base_formatter import BaseFormatter

class XmlFormatter(BaseFormatter):
    def format_transcript(self, video: Video, transcript: Transcript) -> str:
        # Implementation
        ...
    
    def get_file_extension(self) -> str:
        return "xml"
```

2. **Register Formatter**
```python
# src/services/export_service.py
self.formatters = {
    'txt': TextFormatter(),
    'json': JsonFormatter(),
    'xml': XmlFormatter(),  # Add new formatter
}
```

3. **Add Tests**
```python
# tests/unit/test_xml_formatter.py
def test_xml_formatter():
    formatter = XmlFormatter()
    result = formatter.format_transcript(video, transcript)
    
    assert result.startswith('<?xml')
    assert '<transcript>' in result
```

4. **Update Documentation**
- Add to README.md
- Update API documentation
- Add usage example

## Extension Development

### Creating a Plugin

```python
# my_plugin.py
from youtube_transcriber.plugins import Plugin, hook

class MyPlugin(Plugin):
    """Custom plugin for YouTube Transcriber."""
    
    @hook('pre_channel_process')
    async def validate_channel(self, channel):
        """Called before processing a channel."""
        if channel.video_count > 1000:
            self.logger.warning(f"Large channel: {channel.title}")
    
    @hook('post_video_process')
    async def notify_completion(self, video, result):
        """Called after processing each video."""
        if result.success:
            await self.send_notification(f"Completed: {video.title}")
```

### Plugin Registration

```python
# In your code or config
from youtube_transcriber import register_plugin
from my_plugin import MyPlugin

register_plugin(MyPlugin())
```

## Debugging

### 1. Debug Logging

```python
# Enable debug logging
export YOUTUBE_TRANSCRIBER_LOG_LEVEL=DEBUG

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Using Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or with IPython
import IPython; IPython.embed()

# VS Code debugger config
{
    "name": "Debug CLI",
    "type": "python",
    "request": "launch",
    "module": "src.cli.main",
    "args": ["@channelname", "--verbose"]
}
```

### 3. Performance Profiling

```python
# Using cProfile
python -m cProfile -o profile.stats src/cli/main.py @channel

# Analyze results
import pstats
stats = pstats.Stats('profile.stats')
stats.sort_stats('cumulative').print_stats(20)
```

### 4. Memory Profiling

```python
# Using memory_profiler
from memory_profiler import profile

@profile
def process_large_channel():
    # Your code here
    pass

# Run with: python -m memory_profiler script.py
```

## Performance Optimization

### 1. Async Best Practices

```python
# Good: Concurrent processing
videos = await asyncio.gather(*[
    process_video(v) for v in video_list
])

# Good: Semaphore for rate limiting
semaphore = asyncio.Semaphore(5)
async def limited_process(video):
    async with semaphore:
        return await process_video(video)
```

### 2. Memory Optimization

```python
# Good: Generator for large datasets
def read_large_file(path):
    with open(path) as f:
        for line in f:
            yield line.strip()

# Good: Cleanup large objects
def process_batch(videos):
    results = []
    for video in videos:
        result = process_video(video)
        results.append(result.summary)  # Keep only summary
        del result  # Free memory
    return results
```

### 3. Caching Strategies

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_channel_metadata(channel_id: str):
    # Expensive operation cached
    return fetch_from_api(channel_id)

# TTL cache for time-sensitive data
from cachetools import TTLCache

channel_cache = TTLCache(maxsize=100, ttl=3600)  # 1 hour
```

## Release Process

### 1. Version Bumping

```bash
# Update version in pyproject.toml
poetry version patch  # 1.0.0 -> 1.0.1
poetry version minor  # 1.0.0 -> 1.1.0
poetry version major  # 1.0.0 -> 2.0.0
```

### 2. Changelog Update

Update `CHANGELOG.md`:
```markdown
## [1.1.0] - 2024-01-15
### Added
- Multi-channel batch processing
- Interactive channel selection

### Fixed
- Memory leak in large channel processing

### Changed
- Improved error messages
```

### 3. Release Checklist

```bash
# 1. Ensure all tests pass
pytest

# 2. Update version
poetry version minor

# 3. Update changelog
# Edit CHANGELOG.md

# 4. Commit changes
git add .
git commit -m "chore: Release v1.1.0"

# 5. Tag release
git tag -a v1.1.0 -m "Release version 1.1.0"

# 6. Push to GitHub
git push origin main --tags

# 7. Build and publish
poetry build
poetry publish
```

### 4. Post-Release

1. Create GitHub release with changelog
2. Update documentation if needed
3. Announce in community channels
4. Monitor for issues

## Development Tools

### Useful Commands

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/

# Run security checks
bandit -r src/

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree

# Clean build artifacts
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### VS Code Extensions

- Python
- Pylance
- Black Formatter
- Ruff
- GitLens
- Python Test Explorer
- Python Docstring Generator

### Development Resources

- [Python AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [Typer Documentation](https://typer.tiangolo.com/)
- [Rich Documentation](https://rich.readthedocs.io/)
- [YouTube Data API Reference](https://developers.google.com/youtube/v3/docs)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

Happy coding! If you have questions, please check our [discussions](https://github.com/yourusername/youtube-transcriber/discussions) or create an issue.