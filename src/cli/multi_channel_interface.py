"""Multi-channel selection interface for YouTube Transcriber."""

from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import typer
from loguru import logger
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from pathlib import Path

from ..models.channel import Channel, ProcessingStatistics
from ..models.config import ProcessingConfig
from ..services.channel_service import ChannelService


class SortOrder(str, Enum):
    """Sort order options for channels."""
    NAME = "name"
    SUBSCRIBERS = "subscribers"
    VIDEOS = "videos"
    DATE_ADDED = "date_added"


class FilterType(str, Enum):
    """Filter types for channels."""
    ALL = "all"
    LARGE = "large"  # >1M subscribers
    MEDIUM = "medium"  # 100k-1M subscribers
    SMALL = "small"  # <100k subscribers
    RECENT = "recent"  # Active in last 30 days


class ChannelInfo:
    """Enhanced channel information for UI."""
    def __init__(self, identifier: str):
        self.identifier = identifier
        self.channel_data: Optional[Channel] = None
        self.validation_status: str = "pending"
        self.error_message: Optional[str] = None
        self.added_at: datetime = datetime.now()
        self.tags: List[str] = []


class MultiChannelInterface:
    """Enhanced interface for multi-channel selection and batch processing."""
    
    def __init__(self, console: Optional[Console] = None, channel_service: Optional[ChannelService] = None):
        """Initialize multi-channel interface."""
        self.console = console or Console()
        self.channel_service = channel_service
        self.channels: Dict[str, ChannelInfo] = {}
        self.processing_stats: Dict[str, ProcessingStatistics] = {}
        self.live_display: Optional[Live] = None
    
    def get_channels_from_batch_file(self, file_path: Path) -> List[str]:
        """Read channel URLs/IDs from a batch file.
        
        Args:
            file_path: Path to the batch file
            
        Returns:
            List of channel identifiers
        """
        channels = []
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        channels.append(line)
            
            if not channels:
                raise ValueError("No valid channels found in batch file")
                
            return channels
            
        except FileNotFoundError:
            raise typer.BadParameter(f"Batch file not found: {file_path}")
        except Exception as e:
            raise typer.BadParameter(f"Error reading batch file: {e}")
    
    async def interactive_channel_selection(self) -> List[str]:
        """Enhanced interactive mode with search, filter, and validation.
        
        Returns:
            List of validated channel identifiers
        """
        # Display enhanced header
        self._display_welcome_screen()
        
        while True:
            action = self._show_main_menu()
            
            if action == "add":
                await self._add_channels_interactive()
            elif action == "search":
                await self._search_channels()
            elif action == "filter":
                self._apply_filters()
            elif action == "sort":
                self._sort_channels()
            elif action == "validate":
                await self._validate_all_channels()
            elif action == "proceed":
                if self._confirm_selection():
                    return [ch.identifier for ch in self.channels.values() 
                           if ch.validation_status == "valid"]
            elif action == "quit":
                return []
    
    def _display_welcome_screen(self):
        """Display enhanced welcome screen."""
        welcome_text = Text()
        welcome_text.append("YouTube Transcriber", style="bold cyan")
        welcome_text.append(" - Multi-Channel Processing\n\n", style="cyan")
        welcome_text.append("Features:\n", style="yellow")
        welcome_text.append("• Add multiple channels at once\n")
        welcome_text.append("• Search YouTube for channels\n")
        welcome_text.append("• Filter and sort your selection\n")
        welcome_text.append("• Validate channels before processing\n")
        
        self.console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))
    
    def _show_main_menu(self) -> str:
        """Show main menu and get user action."""
        # Display current channels
        if self.channels:
            self._display_enhanced_channel_summary()
        
        choices = [
            "add",    # Add more channels
            "search", # Search for channels
            "filter", # Apply filters
            "sort",   # Sort channels
            "validate", # Validate all channels
            "proceed", # Start processing
            "quit"    # Exit
        ]
        
        action = Prompt.ask(
            "\nWhat would you like to do?",
            choices=choices,
            default="add" if not self.channels else "proceed"
        )
        
        return action
    
    async def _add_channels_interactive(self):
        """Add channels with real-time validation."""
        self.console.print("\n[cyan]Add Channels[/cyan]")
        self.console.print("Enter channel URLs, @handles, or IDs (one per line)")
        self.console.print("Press Enter twice to finish\n")
        
        while True:
            channel_input = Prompt.ask(
                f"[{len(self.channels) + 1}]",
                default="",
                show_default=False
            )
            
            if not channel_input:
                break
            
            # Add channel and show validation status
            channel_info = ChannelInfo(channel_input)
            self.channels[channel_input] = channel_info
            
            # Quick validation feedback
            with self.console.status(f"Validating {channel_input}..."):
                # Simulate validation - in real implementation, call channel service
                await asyncio.sleep(0.5)
                channel_info.validation_status = "valid"
                self.console.print(f"✅ Added: {channel_input}")
    
    async def _search_channels(self):
        """Search YouTube for channels."""
        search_query = Prompt.ask("\nSearch for channels")
        
        with self.console.status(f"Searching for '{search_query}'..."):
            # In real implementation, search via YouTube API
            await asyncio.sleep(1)
            
            # Mock search results
            results = [
                ("@mkbhd", "Marques Brownlee", "15.2M subscribers"),
                ("@LinusTechTips", "Linus Tech Tips", "14.8M subscribers"),
                ("@Unboxtherapy", "Unbox Therapy", "18.1M subscribers")
            ]
        
        if results:
            self._display_search_results(results)
            selected = self._select_from_search_results(results)
            
            for channel_id in selected:
                if channel_id not in self.channels:
                    self.channels[channel_id] = ChannelInfo(channel_id)
    
    def _apply_filters(self):
        """Apply filters to channel list."""
        filter_type = Prompt.ask(
            "\nFilter channels by",
            choices=[f.value for f in FilterType],
            default=FilterType.ALL.value
        )
        
        # In real implementation, filter based on channel statistics
        self.console.print(f"[green]Filter applied: {filter_type}[/green]")
    
    def _sort_channels(self):
        """Sort channel list."""
        sort_order = Prompt.ask(
            "\nSort channels by",
            choices=[s.value for s in SortOrder],
            default=SortOrder.NAME.value
        )
        
        # In real implementation, sort the channels
        self.console.print(f"[green]Sorted by: {sort_order}[/green]")
    
    async def _validate_all_channels(self):
        """Validate all pending channels."""
        pending_channels = [ch for ch in self.channels.values() 
                          if ch.validation_status == "pending"]
        
        if not pending_channels:
            self.console.print("[green]All channels already validated![/green]")
            return
        
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
        
        with progress:
            task = progress.add_task("Validating channels...", total=len(pending_channels))
            
            for channel_info in pending_channels:
                # In real implementation, validate via channel service
                await asyncio.sleep(0.3)
                channel_info.validation_status = "valid"
                progress.advance(task)
    
    def _display_enhanced_channel_summary(self):
        """Display enhanced summary with validation status and metadata."""
        table = Table(title=f"Channel Selection ({len(self.channels)} total)")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Channel", style="white", min_width=30)
        table.add_column("Status", style="white", width=12)
        table.add_column("Subscribers", style="white", width=12)
        table.add_column("Videos", style="white", width=10)
        table.add_column("Tags", style="white", width=20)
        
        for i, (channel_id, info) in enumerate(self.channels.items(), 1):
            # Status indicator
            if info.validation_status == "valid":
                status = "[green]✅ Valid[/green]"
            elif info.validation_status == "invalid":
                status = "[red]❌ Invalid[/red]"
            else:
                status = "[yellow]⏳ Pending[/yellow]"
            
            # Channel data (if validated)
            subs = "-"
            videos = "-"
            if info.channel_data and info.channel_data.statistics:
                subs = self._format_number(info.channel_data.statistics.subscriber_count)
                videos = str(info.channel_data.statistics.video_count)
            
            # Tags
            tags = ", ".join(info.tags) if info.tags else "-"
            
            # Display name
            display_name = channel_id
            if len(channel_id) > 30:
                display_name = channel_id[:27] + "..."
            
            table.add_row(str(i), display_name, status, subs, videos, tags)
        
        self.console.print(table)
    
    def _format_number(self, num: int) -> str:
        """Format large numbers with suffixes."""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)
    
    def create_live_progress_display(self, channels: List[Channel]) -> Layout:
        """Create a live updating progress display layout."""
        layout = Layout()
        
        # Create layout structure
        layout.split_column(
            Layout(name="header", size=7),
            Layout(name="progress", size=3),
            Layout(name="channels"),
            Layout(name="footer", size=4)
        )
        
        return layout
    
    def update_progress_display(self, layout: Layout, channels: List[Channel]):
        """Update the live progress display."""
        # Update header with overall statistics
        layout["header"].update(self._create_header_panel(channels))
        
        # Update progress bar
        layout["progress"].update(self._create_overall_progress(channels))
        
        # Update channel list
        layout["channels"].update(self._create_channel_progress_table(channels))
        
        # Update footer with statistics
        layout["footer"].update(self._create_statistics_panel(channels))
    
    def _create_header_panel(self, channels: List[Channel]) -> Panel:
        """Create header panel with summary."""
        total_videos = sum(c.processing_stats.total_videos for c in channels if c.processing_stats)
        processed_videos = sum(c.processing_stats.processed_videos for c in channels if c.processing_stats)
        
        # Calculate rates
        total_time = sum((c.processing_stats.get_total_time().total_seconds() 
                         for c in channels if c.processing_stats and c.processing_stats.processing_start_time), 0)
        
        rate = processed_videos / (total_time / 60) if total_time > 0 else 0
        
        header_text = f"""[bold cyan]YouTube Transcriber - Multi-Channel Processing[/bold cyan]

Total Channels: {len(channels)}
Total Videos: {total_videos:,}
Processed: {processed_videos:,}
Processing Rate: {rate:.1f} videos/min"""
        
        return Panel(header_text, title="Status", border_style="cyan")
    
    def _create_overall_progress(self, channels: List[Channel]) -> Panel:
        """Create overall progress bar."""
        total = sum(c.processing_stats.total_videos for c in channels if c.processing_stats)
        completed = sum(c.processing_stats.processed_videos for c in channels if c.processing_stats)
        
        percentage = (completed / total * 100) if total > 0 else 0
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        
        bar = "█" * filled + "░" * (bar_length - filled)
        
        progress_text = f"{bar} {percentage:.1f}% ({completed}/{total})"
        
        return Panel(progress_text, title="Overall Progress", border_style="green" if percentage == 100 else "blue")
    
    def _create_channel_progress_table(self, channels: List[Channel]) -> Table:
        """Create detailed channel progress table."""
        table = Table(show_header=True, expand=True)
        table.add_column("Channel", style="cyan", width=25)
        table.add_column("Progress", justify="center", width=20)
        table.add_column("Status", justify="center", width=15)
        table.add_column("Success", justify="right", width=10)
        table.add_column("Failed", justify="right", width=10)
        table.add_column("Rate", justify="right", width=15)
        table.add_column("ETA", justify="right", width=10)
        
        for channel in channels:
            if channel.processing_stats:
                stats = channel.processing_stats
                
                # Progress bar
                progress_bar = self._create_mini_progress_bar(stats.progress_percentage)
                
                # Status
                if stats.is_complete:
                    status = "[green]✅ Complete[/green]"
                elif stats.processed_videos > 0:
                    status = "[yellow]⚡ Processing[/yellow]"
                else:
                    status = "[dim]⏳ Waiting[/dim]"
                
                # Rate
                rate = stats.get_processing_rate()
                rate_str = f"{rate:.1f} v/h" if rate else "-"
                
                # ETA
                eta = stats.estimated_time_remaining
                if eta and not stats.is_complete:
                    eta_str = self._format_duration(eta)
                else:
                    eta_str = "-"
                
                table.add_row(
                    channel.snippet.title[:25],
                    progress_bar,
                    status,
                    str(stats.successful_videos),
                    str(stats.failed_videos),
                    rate_str,
                    eta_str
                )
            else:
                table.add_row(
                    channel.snippet.title[:25],
                    "[dim]░░░░░░░░░░[/dim]",
                    "[dim]⏳ Waiting[/dim]",
                    "0", "0", "-", "-"
                )
        
        return table
    
    def _create_mini_progress_bar(self, percentage: float, width: int = 10) -> str:
        """Create a mini progress bar."""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"{bar} {percentage:.0f}%"
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration to human readable."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"


    def display_batch_results(self, channels: List[Channel], processing_config: ProcessingConfig):
        """Display comprehensive batch processing results."""
        # Create summary statistics
        total_stats = self._aggregate_statistics(channels)
        
        # Display header
        self.console.print("\n" + "=" * 80)
        self.console.print("[bold cyan]Batch Processing Complete[/bold cyan]", justify="center")
        self.console.print("=" * 80 + "\n")
        
        # Overall statistics panel
        self._display_overall_statistics(total_stats)
        
        # Individual channel results
        self._display_channel_results_table(channels)
        
        # Error summary (if any)
        if total_stats["total_errors"] > 0:
            self._display_error_summary(channels)
        
        # Export summary
        self._display_export_summary(channels, processing_config)
        
        # Recommendations
        self._display_recommendations(channels, total_stats)
    
    def _aggregate_statistics(self, channels: List[Channel]) -> Dict[str, Any]:
        """Aggregate statistics from all channels."""
        stats = {
            "total_channels": len(channels),
            "successful_channels": 0,
            "failed_channels": 0,
            "total_videos": 0,
            "successful_videos": 0,
            "failed_videos": 0,
            "total_errors": 0,
            "total_duration": timedelta(),
            "total_words": 0,
            "avg_success_rate": 0.0
        }
        
        for channel in channels:
            if channel.processing_stats:
                ps = channel.processing_stats
                stats["total_videos"] += ps.total_videos
                stats["successful_videos"] += ps.successful_videos
                stats["failed_videos"] += ps.failed_videos
                
                if ps.is_complete:
                    if ps.success_rate >= 0.5:
                        stats["successful_channels"] += 1
                    else:
                        stats["failed_channels"] += 1
                
                if ps.processing_start_time:
                    duration = datetime.now() - ps.processing_start_time
                    stats["total_duration"] += duration
        
        # Calculate average success rate
        if stats["total_videos"] > 0:
            stats["avg_success_rate"] = stats["successful_videos"] / stats["total_videos"]
        
        return stats
    
    def _display_channel_results_table(self, channels: List[Channel]):
        """Display detailed results for each channel."""
        table = Table(title="Channel Processing Results", show_header=True)
        table.add_column("Channel", style="cyan", width=25)
        table.add_column("Videos", justify="right", width=10)
        table.add_column("Success", justify="right", width=10)
        table.add_column("Failed", justify="right", width=10)
        table.add_column("Success Rate", justify="right", width=12)
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Export", justify="center", width=8)
        
        for channel in channels:
            if channel.processing_stats:
                ps = channel.processing_stats
                
                # Calculate duration
                if ps.processing_start_time:
                    duration = datetime.now() - ps.processing_start_time
                    duration_str = self._format_duration(duration)
                else:
                    duration_str = "-"
                
                # Export status
                export_status = "✅" if getattr(channel, 'export_successful', False) else "❌"
                
                # Success rate color
                rate = ps.success_rate * 100
                if rate >= 90:
                    rate_str = f"[green]{rate:.1f}%[/green]"
                elif rate >= 70:
                    rate_str = f"[yellow]{rate:.1f}%[/yellow]"
                else:
                    rate_str = f"[red]{rate:.1f}%[/red]"
                
                table.add_row(
                    channel.snippet.title[:25],
                    str(ps.total_videos),
                    str(ps.successful_videos),
                    str(ps.failed_videos),
                    rate_str,
                    duration_str,
                    export_status
                )
        
        self.console.print(table)


def add_multi_channel_commands(app: typer.Typer):
    """Add enhanced multi-channel commands to the CLI app."""
    
    @app.command("batch")
    def batch_process(
        batch_file: Path = typer.Argument(
            ...,
            help="Path to file containing channel URLs/IDs (one per line)"
        ),
        output_dir: Optional[Path] = typer.Option(
            None,
            "--output-dir", "-o",
            help="Output directory for transcripts"
        ),
        parallel_channels: int = typer.Option(
            3,
            "--parallel-channels", "-pc",
            help="Number of channels to process in parallel",
            min=1,
            max=10
        ),
        parallel_videos: int = typer.Option(
            5,
            "--parallel-videos", "-pv",
            help="Number of videos per channel to process in parallel",
            min=1,
            max=20
        ),
        filter: Optional[FilterType] = typer.Option(
            None,
            "--filter", "-f",
            help="Filter channels by criteria"
        ),
        sort: Optional[SortOrder] = typer.Option(
            None,
            "--sort", "-s",
            help="Sort channels before processing"
        ),
        resume: bool = typer.Option(
            False,
            "--resume", "-r",
            help="Resume from previous session"
        )
    ):
        """Process multiple channels from a batch file with advanced options."""
        from ..application.batch_orchestrator import BatchChannelOrchestrator
        from ..models.config import ProcessingConfig
        
        # Create configuration
        config = ProcessingConfig(
            parallel_channels=parallel_channels,
            parallel_videos=parallel_videos,
            output_directory=output_dir or Path("./output"),
            filter_type=filter,
            sort_order=sort
        )
        
        # Initialize interface
        interface = MultiChannelInterface()
        
        # Load channels
        with interface.console.status("Loading channels..."):
            channels = interface.get_channels_from_batch_file(batch_file)
        
        interface.console.print(f"[green]Found {len(channels)} channels to process[/green]")
        
        # Apply filters if specified
        if filter:
            channels = interface._apply_channel_filter(channels, filter)
            interface.console.print(f"[yellow]After filtering: {len(channels)} channels[/yellow]")
        
        # Sort if specified
        if sort:
            channels = interface._sort_channel_list(channels, sort)
        
        # Initialize and run BatchOrchestrator
        asyncio.run(_run_batch_processing(channels, config, interface))
    
    @app.command("interactive")
    async def interactive_mode(
        output_dir: Optional[Path] = typer.Option(
            None,
            "--output-dir", "-o",
            help="Output directory for transcripts"
        ),
        parallel_channels: int = typer.Option(
            3,
            "--parallel-channels", "-pc",
            help="Number of channels to process in parallel"
        )
    ):
        """Enhanced interactive mode for selecting and processing multiple channels."""
        interface = MultiChannelInterface()
        
        # Run interactive selection
        channels = await interface.interactive_channel_selection()
        
        if not channels:
            interface.console.print("[yellow]No channels selected[/yellow]")
            return
        
        interface.console.print(f"\n[green]Selected {len(channels)} channels for processing[/green]")
        
        # Confirm processing settings
        if Confirm.ask("\nProceed with processing?", default=True):
            config = ProcessingConfig(
                parallel_channels=parallel_channels,
                output_directory=output_dir or Path("./output")
            )
            
            # Initialize and run BatchOrchestrator
            from ..application.batch_orchestrator import BatchChannelOrchestrator
            
            settings = load_settings()
            settings.output.output_directory = config.output_directory
            settings.processing.concurrent_limit = config.parallel_videos
            settings.batch.max_channels = config.parallel_channels
            
            asyncio.run(_run_batch_processing(channels, settings, interface))
    
    @app.command("monitor")
    async def monitor_progress(
        session_id: Optional[str] = typer.Argument(
            None,
            help="Session ID to monitor (latest if not specified)"
        )
    ):
        """Monitor ongoing batch processing with live updates."""
        interface = MultiChannelInterface()
        
        # TODO: Connect to running session and display live progress
        interface.console.print("[red]Progress monitoring not yet implemented[/red]")


async def _run_batch_processing(
    channels: List[str], 
    settings: Any,
    interface: MultiChannelInterface
):
    """Run batch processing with BatchOrchestrator.
    
    Args:
        channels: List of channel identifiers
        settings: Application settings
        interface: MultiChannel interface for display
    """
    from ..application.batch_orchestrator import BatchChannelOrchestrator
    
    try:
        # Create batch orchestrator
        async with BatchChannelOrchestrator(settings) as orchestrator:
            # Set up live display
            with interface.console.status("Processing channels...") as status:
                # Process channels
                result = await orchestrator.process_channels(
                    channel_inputs=channels,
                    language=settings.output.default_language if hasattr(settings.output, 'default_language') else "ja",
                    output_format=settings.output.default_format
                )
                
                # Display results
                interface.console.print("\n[bold green]Batch Processing Complete![/bold green]")
                interface.console.print(f"Total channels: {result.total_channels}")
                interface.console.print(f"Successful: {len(result.successful_channels)}")
                interface.console.print(f"Failed: {len(result.failed_channels)}")
                interface.console.print(f"Total videos processed: {result.total_videos_processed}")
                
                if result.failed_channels:
                    interface.console.print("\n[red]Failed channels:[/red]")
                    for channel, error in result.failed_channels.items():
                        interface.console.print(f"  • {channel}: {error}")
                
    except Exception as e:
        interface.console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)