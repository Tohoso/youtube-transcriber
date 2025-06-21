"""Main CLI entry point."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ..application.orchestrator import TranscriptOrchestrator
from ..models.config import AppSettings
from ..utils.logging import setup_logging

app = typer.Typer(
    name="youtube-transcriber",
    help="YouTube channel transcript extraction CLI application",
    add_completion=True,
)
console = Console()


@app.command()
def transcribe(
    channel_input: str = typer.Argument(
        ...,
        help="YouTube channel URL, ID, or @handle"
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir", "-o",
        help="Output directory for transcripts"
    ),
    format: Optional[str] = typer.Option(
        None,
        "--format", "-f",
        help="Output format: txt, json, csv, md"
    ),
    language: str = typer.Option(
        "ja",
        "--language", "-l",
        help="Transcript language code (e.g., ja, en)"
    ),
    concurrent: Optional[int] = typer.Option(
        None,
        "--concurrent", "-c",
        help="Number of concurrent downloads"
    ),
    date_from: Optional[str] = typer.Option(
        None,
        "--date-from",
        help="Start date (YYYY-MM-DD)"
    ),
    date_to: Optional[str] = typer.Option(
        None,
        "--date-to",
        help="End date (YYYY-MM-DD)"
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Configuration file path"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Test run without downloading"
    ),
):
    """Extract transcripts from a YouTube channel."""
    try:
        console.print(Panel.fit(
            f"[bold green]YouTube Transcriber[/bold green]\n"
            f"Starting transcript extraction for: {channel_input}",
            border_style="green"
        ))
        
        settings = load_settings(config)
        
        if output_dir:
            settings.output.output_directory = output_dir
        if format:
            settings.output.default_format = format
        if concurrent:
            settings.processing.concurrent_limit = concurrent
            
        setup_logging(
            level=settings.logging.level,
            log_file=str(settings.logging.log_file) if settings.logging.log_file else None
        )
        
        orchestrator = TranscriptOrchestrator(settings)
        
        asyncio.run(orchestrator.process_channel(
            channel_input=channel_input,
            language=language,
            date_from=date_from,
            date_to=date_to,
            dry_run=dry_run
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Process interrupted by user[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    from .. import __version__
    console.print(f"YouTube Transcriber v{__version__}")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    generate: bool = typer.Option(False, "--generate", help="Generate sample config file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path for config"),
):
    """Manage configuration."""
    if generate:
        sample_config = generate_sample_config()
        output_path = output or Path("config.yaml")
        output_path.write_text(sample_config)
        console.print(f"[green]Sample configuration saved to: {output_path}[/green]")
    elif show:
        settings = load_settings()
        console.print(settings.model_dump_json(indent=2))
    else:
        console.print("Use --show to display config or --generate to create sample config")


def load_settings(config_path: Optional[Path] = None) -> AppSettings:
    """Load application settings."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if config_path and config_path.exists():
        import yaml
        config_data = yaml.safe_load(config_path.read_text())
        
        if "api" not in config_data:
            config_data["api"] = {}
        if "youtube_api_key" not in config_data["api"]:
            config_data["api"]["youtube_api_key"] = os.getenv("YOUTUBE_API_KEY", "")
            
        return AppSettings(**config_data)
    else:
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError(
                "YouTube API key not found. "
                "Set YOUTUBE_API_KEY environment variable or use --config"
            )
        return AppSettings(api={"youtube_api_key": api_key})


def generate_sample_config() -> str:
    """Generate sample configuration."""
    return """# YouTube Transcriber Configuration

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
"""


if __name__ == "__main__":
    app()