"""Configuration models."""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from enum import Enum


class OutputFormat(str, Enum):
    """Output format."""
    
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "md"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class APIConfig(BaseModel):
    """API configuration."""
    
    youtube_api_key: str = Field(..., description="YouTube Data API key")
    quota_limit: int = Field(10000, description="Daily quota limit")
    quota_used: int = Field(0, description="Used quota")
    
    @field_validator('youtube_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key."""
        if not v or len(v) < 20:
            raise ValueError('Invalid YouTube API key')
        return v


class ProcessingConfig(BaseModel):
    """Processing configuration."""
    
    concurrent_limit: int = Field(5, ge=1, le=50, description="Concurrent processing limit")
    retry_attempts: int = Field(3, ge=0, le=10, description="Retry attempts")
    retry_delay: float = Field(1.0, ge=0.1, le=60.0, description="Retry delay in seconds")
    rate_limit_per_minute: int = Field(60, ge=1, le=300, description="Rate limit per minute")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Timeout in seconds")
    
    min_video_duration: Optional[int] = Field(None, ge=0, description="Minimum video duration in seconds")
    max_video_duration: Optional[int] = Field(None, ge=0, description="Maximum video duration in seconds")
    skip_private_videos: bool = Field(True, description="Skip private videos")
    skip_live_streams: bool = Field(True, description="Skip live streams")


class OutputConfig(BaseModel):
    """Output configuration."""
    
    default_format: OutputFormat = Field(OutputFormat.TXT, description="Default output format")
    output_directory: Path = Field(Path("./output"), description="Output directory")
    filename_template: str = Field(
        "{date}_{title}_{video_id}", 
        description="Filename template"
    )
    include_metadata: bool = Field(True, description="Generate metadata file")
    include_timestamps: bool = Field(False, description="Include timestamps")
    max_filename_length: int = Field(100, ge=10, le=255, description="Maximum filename length")
    
    encoding: str = Field("utf-8", description="File encoding")
    line_separator: str = Field("\n", description="Line separator")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: LogLevel = Field("INFO", description="Log level")
    log_file: Optional[Path] = Field(Path("logs/app.log"), description="Log file path")
    max_file_size: str = Field("500 MB", description="Maximum log file size")
    retention_days: int = Field(10, ge=1, le=365, description="Log retention days")
    format_template: str = Field(
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        description="Log format"
    )
    enable_json_logging: bool = Field(False, description="Enable JSON logging")


class AppSettings(BaseSettings):
    """Application settings."""
    
    api: APIConfig
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    app_name: str = Field("YouTube Transcriber", description="Application name")
    app_version: str = Field("1.0.0", description="Version")
    debug_mode: bool = Field(False, description="Debug mode")
    
    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local"],
        env_prefix="YT_TRANSCRIBER_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )
    
    @field_validator('output')
    @classmethod
    def create_output_directory(cls, v: OutputConfig) -> OutputConfig:
        """Create output directory automatically."""
        v.output_directory.mkdir(parents=True, exist_ok=True)
        return v