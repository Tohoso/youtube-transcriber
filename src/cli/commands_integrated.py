"""Integrated CLI commands with UI-Backend bridge."""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console

from ..models.config import AppSettings, ProcessingConfig
from ..models.batch import BatchConfig
from ..application.batch_orchestrator import BatchChannelOrchestrator
from .ui_backend_bridge import UIBackendBridge
from .multi_channel_interface import MultiChannelInterface
from ..utils.logging import setup_logging


console = Console()


class IntegratedBatchOrchestrator(BatchChannelOrchestrator):
    """Batch orchestrator with UI integration."""
    
    def __init__(self, settings: AppSettings, ui_bridge: UIBackendBridge):
        """Initialize with UI bridge integration."""
        super().__init__(settings)
        self.ui_bridge = ui_bridge
        
    async def process_channels(
        self,
        channel_inputs: List[str],
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        output_format: str = "txt",
        dry_run: bool = False,
        progress_callback: Optional[callable] = None
    ):
        """Process channels with UI feedback."""
        
        # Notify UI of batch start
        processing_config = ProcessingConfig(
            parallel_channels=self.batch_config.max_channels,
            parallel_videos=self.settings.processing.concurrent_limit,
            output_directory=self.settings.output.output_directory
        )
        await self.ui_bridge.on_batch_start(channel_inputs, processing_config)
        
        # Create enhanced progress callback
        async def enhanced_progress_callback(update):
            # Forward to UI bridge
            if update.get('type') == 'channel_validated':
                await self.ui_bridge.on_channel_validated(
                    update['channel_id'], 
                    update['channel']
                )
            elif update.get('type') == 'channel_start':
                await self.ui_bridge.on_channel_start(
                    update['channel_id'],
                    update['total_videos']
                )
            elif update.get('type') == 'video_processed':
                await self.ui_bridge.on_video_processed(
                    update['channel_id'],
                    update['video'],
                    update['success']
                )
            elif update.get('type') == 'channel_complete':
                await self.ui_bridge.on_channel_complete(
                    update['channel_id'],
                    update['stats']
                )
            elif update.get('type') == 'channel_error':
                recovery_action = await self.ui_bridge.on_channel_error(
                    update['channel_id'],
                    update['error']
                )
                update['recovery_action'] = recovery_action
            
            # Also call original callback if provided
            if progress_callback:
                await progress_callback(update)
        
        try:
            # Process with parent implementation
            result = await super().process_channels(
                channel_inputs=channel_inputs,
                language=language,
                date_from=date_from,
                date_to=date_to,
                output_format=output_format,
                dry_run=dry_run,
                progress_callback=enhanced_progress_callback
            )
            
            # Prepare summary
            summary = {
                'total_channels': result.total_channels,
                'successful_channels': len(result.successful_channels),
                'failed_channels': len(result.failed_channels),
                'total_videos': result.total_videos_processed,
                'successful_videos': result.total_videos_successful,
                'failed_videos': result.total_videos_failed,
                'output_dir': str(self.settings.output.output_directory),
                'avg_speed': result.total_videos_processed / ((result.total_duration or 60) / 60)
            }
            
            # Notify UI of completion
            await self.ui_bridge.on_batch_complete(summary)
            
            return result
            
        except Exception as e:
            # Still notify UI even on error
            await self.ui_bridge.on_batch_complete({
                'error': str(e),
                'total_channels': len(channel_inputs),
                'successful_channels': 0,
                'failed_channels': len(channel_inputs)
            })
            raise


def add_integrated_commands(app: typer.Typer):
    """Add integrated multi-channel commands to the CLI app."""
    
    @app.command(name="batch")
    def batch_command(
        channels_file: Path = typer.Argument(
            ...,
            help="Path to file containing channel URLs/IDs (one per line)"
        ),
        output_dir: Optional[Path] = typer.Option(
            None, "--output-dir", "-o",
            help="Output directory for transcripts"
        ),
        parallel_channels: int = typer.Option(
            3, "--parallel-channels", "-pc",
            help="Number of channels to process in parallel"
        ),
        parallel_videos: int = typer.Option(
            5, "--parallel-videos", "-pv",
            help="Number of videos per channel to process in parallel"
        ),
        language: str = typer.Option(
            "ja", "--language", "-l",
            help="Transcript language code"
        ),
        format: str = typer.Option(
            "txt", "--format", "-f",
            help="Output format: txt, json, csv, md"
        ),
        date_from: Optional[str] = typer.Option(
            None, "--date-from",
            help="Start date filter (YYYY-MM-DD)"
        ),
        date_to: Optional[str] = typer.Option(
            None, "--date-to",
            help="End date filter (YYYY-MM-DD)"
        ),
        resume: bool = typer.Option(
            False, "--resume", "-r",
            help="Resume from previous progress"
        ),
        config: Optional[Path] = typer.Option(
            None, "--config",
            help="Configuration file path"
        ),
    ):
        """Process multiple YouTube channels in batch mode with UI feedback."""
        
        # Load settings
        from ..cli.main import load_settings
        settings = load_settings(config)
        
        # Override settings with CLI options
        if output_dir:
            settings.output.output_directory = output_dir
        if format:
            settings.output.default_format = format
            
        # Update batch config
        settings.batch = BatchConfig(
            max_channels=parallel_channels,
            save_progress=True,
            batch_size=5
        )
        settings.processing.concurrent_limit = parallel_videos
        
        # Setup logging
        setup_logging(
            level=settings.logging.level,
            log_file=str(settings.logging.log_file) if settings.logging.log_file else None
        )
        
        # Read channel inputs
        if not channels_file.exists():
            console.print(f"[red]Error: Channel file not found: {channels_file}[/red]")
            raise typer.Exit(1)
            
        channel_inputs = []
        with open(channels_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    channel_inputs.append(line)
        
        if not channel_inputs:
            console.print("[red]Error: No channels found in file[/red]")
            raise typer.Exit(1)
        
        # Run with UI integration
        async def run_batch():
            # Create UI bridge
            ui_bridge = UIBackendBridge(console=console)
            
            # Create integrated orchestrator
            orchestrator = IntegratedBatchOrchestrator(settings, ui_bridge)
            
            # Process channels
            await orchestrator.process_channels(
                channel_inputs=channel_inputs,
                language=language,
                date_from=date_from,
                date_to=date_to,
                output_format=format,
                dry_run=False
            )
        
        try:
            asyncio.run(run_batch())
        except KeyboardInterrupt:
            console.print("\n[yellow]Process interrupted by user[/yellow]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            raise typer.Exit(1)
    
    @app.command(name="interactive")
    def interactive_command(
        config: Optional[Path] = typer.Option(
            None, "--config",
            help="Configuration file path"
        ),
    ):
        """Interactive mode for channel selection and processing with UI."""
        
        # Load settings
        from ..cli.main import load_settings
        settings = load_settings(config)
        
        # Create multi-channel interface
        interface = MultiChannelInterface(console=console)
        
        # Run interactive mode with UI bridge
        async def run_interactive():
            # Get channels interactively
            channels, processing_config = await interface.run_interactive_mode()
            
            if not channels:
                console.print("[yellow]No channels selected. Exiting.[/yellow]")
                return
            
            # Update settings with interactive config
            settings.batch = BatchConfig(
                max_channels=processing_config.parallel_channels,
                save_progress=True
            )
            settings.processing.concurrent_limit = processing_config.parallel_videos
            settings.output.output_directory = processing_config.output_directory
            
            # Create UI bridge
            ui_bridge = UIBackendBridge(console=console)
            
            # Create integrated orchestrator
            orchestrator = IntegratedBatchOrchestrator(settings, ui_bridge)
            
            # Process channels
            await orchestrator.process_channels(
                channel_inputs=[ch.url for ch in channels],
                language=processing_config.language,
                output_format=processing_config.output_format,
                dry_run=False
            )
        
        try:
            asyncio.run(run_interactive())
        except KeyboardInterrupt:
            console.print("\n[yellow]Process interrupted by user[/yellow]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            raise typer.Exit(1)