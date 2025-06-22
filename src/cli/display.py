"""Display and progress management using Rich."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from ..models.channel import Channel, ProcessingStatistics
from ..models.transcript import TranscriptStatus
from ..models.video import Video


class DisplayManager:
    """Manage display output using Rich."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize display manager."""
        self.console = console or Console()
        self.progress = self._create_progress()
        self.live = Live(self.progress, console=self.console, refresh_per_second=2)
        
    def _create_progress(self) -> Progress:
        """Create progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=True,
        )
    
    def start(self):
        """Start live display."""
        self.live.start()
    
    def stop(self):
        """Stop live display."""
        self.live.stop()
    
    def add_task(self, description: str, total: int) -> int:
        """Add a new task to progress."""
        return self.progress.add_task(description, total=total)
    
    def update_task(self, task_id: int, advance: int = 1, **kwargs):
        """Update task progress."""
        self.progress.update(task_id, advance=advance, **kwargs)
    
    def show_channel_info(self, channel: Channel):
        """Display channel information."""
        try:
            info_table = Table(title=f"Channel: {channel.snippet.title}", show_header=False)
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="white")
            
            info_table.add_row("Channel ID", channel.id)
            info_table.add_row("URL", channel.url)
            
            if channel.statistics:
                info_table.add_row("Subscribers", f"{channel.statistics.subscriber_count:,}")
                info_table.add_row("Total Videos", f"{channel.statistics.video_count:,}")
                info_table.add_row("Total Views", f"{channel.statistics.view_count:,}")
            
            if channel.snippet.published_at:
                info_table.add_row("Created", channel.snippet.published_at.strftime("%Y-%m-%d"))
            
            self.console.print(info_table)
        except Exception as e:
            # Fallback to basic display
            self._fallback_channel_info(channel)
    
    def show_processing_stats(self, stats: ProcessingStatistics):
        """Display processing statistics."""
        try:
            self._show_processing_stats_rich(stats)
        except Exception:
            self._fallback_processing_stats(stats)
    
    def _show_processing_stats_rich(self, stats: ProcessingStatistics):
        """Display processing statistics using Rich."""
        # Main statistics table
        stats_table = Table(title="Processing Statistics", show_header=True)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white", justify="right")
        
        stats_table.add_row("Total Videos", f"{stats.total_videos}")
        stats_table.add_row("Processed", f"{stats.processed_videos}")
        stats_table.add_row("Successful", f"{stats.successful_videos}")
        stats_table.add_row("Failed", f"{stats.failed_videos}")
        stats_table.add_row("Skipped", f"{stats.skipped_videos}")
        stats_table.add_row("Progress", f"{stats.progress_percentage:.1f}%")
        stats_table.add_row("Success Rate", f"{stats.success_rate:.1%}")
        stats_table.add_row("Completion Rate", f"{stats.completion_rate:.1%}")
        
        # Add time metrics if available
        if stats.average_processing_time > 0:
            stats_table.add_row("Avg Processing Time", f"{stats.average_processing_time:.1f}s")
        
        if stats.estimated_time_remaining:
            remaining = stats.estimated_time_remaining
            hours, remainder = divmod(remaining.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
            stats_table.add_row("Est. Time Remaining", time_str)
        
        processing_rate = stats.get_processing_rate()
        if processing_rate:
            stats_table.add_row("Processing Rate", f"{processing_rate:.1f} videos/hour")
        
        self.console.print(stats_table)
        
        # Show error statistics if any errors occurred
        if stats.error_statistics:
            self.console.print()  # Add spacing
            error_summary = stats.get_error_summary()
            error_table = Table(title="Error Analysis", show_header=True)
            error_table.add_column("Error Type", style="red")
            error_table.add_column("Count", style="white", justify="right")
            error_table.add_column("Percentage", style="yellow", justify="right")
            
            for error_type, count in error_summary['error_types'].items():
                percentage = error_summary['error_percentages'][error_type]
                error_table.add_row(error_type, str(count), f"{percentage:.1f}%")
            
            if error_summary['most_common_error']:
                error_table.add_row(
                    "[bold]Most Common[/bold]", 
                    error_summary['most_common_error'], 
                    ""
                )
            
            self.console.print(error_table)
    
    def _fallback_processing_stats(self, stats: ProcessingStatistics):
        """Fallback display for processing stats when Rich fails."""
        print("\n=== Processing Statistics ===")
        print(f"Total Videos: {stats.total_videos}")
        print(f"Processed: {stats.processed_videos}")
        print(f"Successful: {stats.successful_videos}")
        print(f"Failed: {stats.failed_videos}")
        print(f"Skipped: {stats.skipped_videos}")
        print(f"Progress: {stats.progress_percentage:.1f}%")
        print(f"Success Rate: {stats.success_rate:.1%}")
        print()
    
    def show_video_result(self, video: Video):
        """Display single video result."""
        try:
            self._show_video_result_rich(video)
        except Exception:
            self._fallback_video_result(video)
    
    def _show_video_result_rich(self, video: Video):
        """Display video result using Rich."""
        status_colors = {
            TranscriptStatus.SUCCESS: "green",
            TranscriptStatus.ERROR: "red",
            TranscriptStatus.NO_TRANSCRIPT: "yellow",
            TranscriptStatus.SKIPPED: "dim",
            TranscriptStatus.PENDING: "blue",
            TranscriptStatus.IN_PROGRESS: "cyan",
        }
        
        color = status_colors.get(video.transcript_status, "white")
        status_text = f"[{color}]{video.transcript_status.value}[/{color}]"
        
        if video.transcript_status == TranscriptStatus.SUCCESS and video.transcript_data:
            details = f"({video.transcript_data.word_count} words)"
        elif video.transcript_status == TranscriptStatus.ERROR:
            details = f"({video.error_message})"
        else:
            details = ""
        
        self.console.print(f"  • {video.title[:60]}... {status_text} {details}")
    
    def _fallback_video_result(self, video: Video):
        """Fallback display for video result when Rich fails."""
        status = video.transcript_status.value.upper()
        title = video.title[:60] + "..." if len(video.title) > 60 else video.title
        if video.transcript_status == TranscriptStatus.SUCCESS and video.transcript_data:
            details = f"({video.transcript_data.word_count} words)"
        elif video.transcript_status == TranscriptStatus.ERROR:
            details = f"({video.error_message})"
        else:
            details = ""
        print(f"  • {title} [{status}] {details}")
    
    def show_summary(self, channel: Channel, start_time: Optional[datetime] = None):
        """Display final summary."""
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
        else:
            # Use processing start time from stats if available
            if channel.processing_stats and channel.processing_stats.processing_start_time:
                duration = (datetime.now() - channel.processing_stats.processing_start_time).total_seconds()
            else:
                duration = 0
        
        stats = channel.processing_stats
        
        summary_text = [
            f"[bold green]Processing Complete[/bold green]\n",
            f"Channel: {channel.snippet.title}",
            f"Total Videos: {stats.total_videos}",
            f"Processed: {stats.processed_videos}",
            f"Successful: {stats.successful_videos}",
            f"Failed: {stats.failed_videos}",
            f"Skipped: {stats.skipped_videos}",
            f"Success Rate: {stats.success_rate:.1%}",
            f"Progress: {stats.progress_percentage:.1f}%",
            f"Duration: {duration:.1f} seconds"
        ]
        
        # Add error summary if errors occurred
        if stats.error_statistics:
            error_summary = stats.get_error_summary()
            summary_text.append(f"\nTotal Errors: {error_summary['total_errors']}")
            if error_summary['most_common_error']:
                summary_text.append(f"Most Common Error: {error_summary['most_common_error']}")
        
        summary = Panel.fit(
            "\n".join(summary_text),
            border_style="green",
        )
        
        self.console.print(summary)
    
    def show_enhanced_statistics(self, channel: Channel):
        """Display enhanced statistics with all metrics."""
        stats = channel.processing_stats
        stats_summary = stats.calculate_statistics_summary()
        
        # Progress Panel
        progress_text = []
        for key, value in stats_summary['progress'].items():
            if isinstance(value, float):
                progress_text.append(f"{key.replace('_', ' ').title()}: {value:.1f}%")
            else:
                progress_text.append(f"{key.replace('_', ' ').title()}: {value}")
        
        progress_panel = Panel(
            "\n".join(progress_text),
            title="Progress Metrics",
            border_style="blue"
        )
        self.console.print(progress_panel)
        
        # Time Metrics Panel
        time_text = []
        time_metrics = stats_summary['time_metrics']
        
        if time_metrics['processing_start_time']:
            time_text.append(f"Started: {time_metrics['processing_start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if time_metrics['last_update_time']:
            time_text.append(f"Last Update: {time_metrics['last_update_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        if time_metrics['average_processing_time']:
            time_text.append(f"Avg Processing Time: {time_metrics['average_processing_time']:.1f}s")
        if time_metrics['estimated_time_remaining']:
            remaining = time_metrics['estimated_time_remaining']
            hours, remainder = divmod(remaining.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            time_text.append(f"Est. Time Remaining: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")
        if time_metrics['processing_rate']:
            time_text.append(f"Processing Rate: {time_metrics['processing_rate']:.1f} videos/hour")
        
        if time_text:
            time_panel = Panel(
                "\n".join(time_text),
                title="Time Metrics",
                border_style="cyan"
            )
            self.console.print(time_panel)
        
        # Error Analysis Panel
        error_analysis = stats_summary['error_analysis']
        if error_analysis['total_errors'] > 0:
            error_text = [f"Total Errors: {error_analysis['total_errors']}"]
            
            if error_analysis['most_common_error']:
                error_text.append(f"Most Common: {error_analysis['most_common_error']}")
            
            error_text.append("\nError Breakdown:")
            for error_type, count in error_analysis['error_types'].items():
                percentage = error_analysis['error_percentages'][error_type]
                error_text.append(f"  • {error_type}: {count} ({percentage:.1f}%)")
            
            error_panel = Panel(
                "\n".join(error_text),
                title="Error Analysis",
                border_style="red"
            )
            self.console.print(error_panel)
    
    def _fallback_channel_info(self, channel: Channel):
        """Fallback display for channel info when Rich fails."""
        print(f"\n=== Channel: {channel.snippet.title} ===")
        print(f"Channel ID: {channel.id}")
        print(f"URL: {channel.url}")
        if channel.statistics:
            print(f"Subscribers: {channel.statistics.subscriber_count:,}")
            print(f"Total Videos: {channel.statistics.video_count:,}")
            print(f"Total Views: {channel.statistics.view_count:,}")
        if channel.snippet.published_at:
            print(f"Created: {channel.snippet.published_at.strftime('%Y-%m-%d')}")
        print()
    
    def show_error(self, error: str):
        """Display error message."""
        try:
            self.console.print(f"[bold red]Error:[/bold red] {error}")
        except Exception:
            # Fallback to basic print
            print(f"ERROR: {error}")
    
    def show_warning(self, warning: str):
        """Display warning message."""
        try:
            self.console.print(f"[bold yellow]Warning:[/bold yellow] {warning}")
        except Exception:
            print(f"WARNING: {warning}")
    
    def show_info(self, info: str):
        """Display info message."""
        try:
            self.console.print(f"[cyan]Info:[/cyan] {info}")
        except Exception:
            print(f"INFO: {info}")
    
    def show_status(self, status: str):
        """Display status message."""
        try:
            self.console.print(f"[blue]{status}[/blue]")
        except Exception:
            print(f"STATUS: {status}")
    
    def create_progress(self):
        """Create a context manager for progress tracking."""
        from contextlib import contextmanager
        
        @contextmanager
        def progress_context():
            """Context manager that manages the Live display lifecycle."""
            # Start the Live display if not already started
            if not self.live.is_started:
                self.start()
                should_stop = True
            else:
                should_stop = False
            
            try:
                yield self.progress
            finally:
                # Only stop if we started it
                if should_stop:
                    self.stop()
        
        return progress_context()