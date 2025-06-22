"""UI-Backend bridge implementation for multi-channel processing."""

from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

from ..models.channel import Channel, ProcessingStatistics
from ..models.video import Video
from ..models.config import ProcessingConfig
from .multi_channel_interface import MultiChannelInterface
from .display import DisplayManager


class RecoveryAction(Enum):
    """Recovery actions for error handling."""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    RETRY_LATER = "retry_later"


class ChannelStatus(Enum):
    """Channel processing status."""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class UIBackendBridge:
    """Bridge between UI and backend for multi-channel processing."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the UI backend bridge."""
        self.console = console or Console()
        self.display = DisplayManager(console=self.console)
        self.multi_interface = MultiChannelInterface(console=self.console)
        
        # State management
        self.channel_states: Dict[str, ChannelStatus] = {}
        self.channel_info: Dict[str, Channel] = {}
        self.processing_start_time: Optional[datetime] = None
        
        # Live display
        self.live_layout: Optional[Layout] = None
        self.live_display: Optional[Live] = None
        self.update_lock = asyncio.Lock()
        
        # Progress tracking
        self.progress_updates_queue: List[Dict[str, Any]] = []
        self.update_task: Optional[asyncio.Task] = None
    
    async def on_batch_start(self, channel_inputs: List[str], config: ProcessingConfig):
        """Called when batch processing starts."""
        self.processing_start_time = datetime.now()
        
        # Initialize states
        for channel_input in channel_inputs:
            self.channel_states[channel_input] = ChannelStatus.PENDING
        
        # Create and start live display
        self.live_layout = self._create_batch_layout(len(channel_inputs))
        self.live_display = Live(
            self.live_layout,
            console=self.console,
            refresh_per_second=2,
            transient=False
        )
        
        # Show initial status
        self.console.print(Panel(
            f"[bold cyan]Starting Batch Processing[/bold cyan]\n\n"
            f"Channels: {len(channel_inputs)}\n"
            f"Parallel Channels: {config.parallel_channels}\n"
            f"Parallel Videos: {config.parallel_videos}\n"
            f"Output: {config.output_directory}",
            title="Batch Configuration",
            border_style="cyan"
        ))
        
        # Start live display
        self.live_display.start()
        
        # Start update task
        self.update_task = asyncio.create_task(self._process_updates())
    
    async def on_channel_validated(self, channel_id: str, channel: Channel):
        """Called when a channel is validated."""
        self.channel_states[channel_id] = ChannelStatus.VALIDATING
        self.channel_info[channel_id] = channel
        
        # Queue update
        await self._queue_update({
            'type': 'channel_validated',
            'channel_id': channel_id,
            'channel': channel
        })
    
    async def on_channel_start(self, channel_id: str, total_videos: int):
        """Called when channel processing starts."""
        self.channel_states[channel_id] = ChannelStatus.PROCESSING
        
        if channel_id in self.channel_info:
            channel = self.channel_info[channel_id]
            channel.processing_stats = ProcessingStatistics(
                processing_start_time=datetime.now(),
                total_videos=total_videos
            )
        
        await self._queue_update({
            'type': 'channel_start',
            'channel_id': channel_id,
            'total_videos': total_videos
        })
    
    async def on_video_processed(self, channel_id: str, video: Video, success: bool):
        """Called when a video is processed."""
        if channel_id in self.channel_info:
            channel = self.channel_info[channel_id]
            if channel.processing_stats:
                channel.processing_stats.processed_videos += 1
                if success:
                    channel.processing_stats.successful_videos += 1
                else:
                    channel.processing_stats.failed_videos += 1
        
        # Batch updates for performance
        await self._queue_update({
            'type': 'video_processed',
            'channel_id': channel_id,
            'video': video,
            'success': success
        })
    
    async def on_channel_complete(self, channel_id: str, stats: ProcessingStatistics):
        """Called when channel processing completes."""
        self.channel_states[channel_id] = ChannelStatus.COMPLETE
        
        if channel_id in self.channel_info:
            self.channel_info[channel_id].processing_stats = stats
        
        await self._queue_update({
            'type': 'channel_complete',
            'channel_id': channel_id,
            'stats': stats
        })
    
    async def on_channel_error(self, channel_id: str, error: Exception) -> RecoveryAction:
        """Called when an error occurs during channel processing."""
        self.channel_states[channel_id] = ChannelStatus.ERROR
        
        # Update display immediately for errors
        await self._update_display_immediate({
            'type': 'channel_error',
            'channel_id': channel_id,
            'error': error
        })
        
        # Determine recovery action based on error type
        if "quota" in str(error).lower():
            self.console.print(f"\n[yellow]API Quota exceeded for {channel_id}[/yellow]")
            return RecoveryAction.RETRY_LATER
        elif "network" in str(error).lower():
            self.console.print(f"\n[yellow]Network error for {channel_id}, retrying...[/yellow]")
            return RecoveryAction.RETRY
        else:
            self.console.print(f"\n[red]Error processing {channel_id}: {error}[/red]")
            return RecoveryAction.SKIP
    
    async def on_batch_complete(self, summary: Dict[str, Any]):
        """Called when batch processing completes."""
        # Stop live display
        if self.live_display:
            self.live_display.stop()
        
        # Cancel update task
        if self.update_task:
            self.update_task.cancel()
        
        # Display final results
        channels = list(self.channel_info.values())
        processing_config = ProcessingConfig()  # Use default for display
        
        self.multi_interface.display_batch_results(channels, processing_config)
        
        # Show summary statistics
        self._display_final_summary(summary)
    
    def _create_batch_layout(self, total_channels: int) -> Layout:
        """Create the layout for batch processing display."""
        layout = Layout()
        
        # Create layout structure
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="progress", size=3),
            Layout(name="channels", size=max(10, min(total_channels * 3, 20))),
            Layout(name="details", size=5)
        )
        
        # Initialize with placeholders
        layout["header"].update(Panel("Initializing...", title="Status"))
        layout["progress"].update(Panel("", title="Progress"))
        layout["channels"].update(Panel("", title="Channels"))
        layout["details"].update(Panel("", title="Current Activity"))
        
        return layout
    
    async def _queue_update(self, update: Dict[str, Any]):
        """Queue an update for batch processing."""
        async with self.update_lock:
            self.progress_updates_queue.append(update)
    
    async def _process_updates(self):
        """Process queued updates in batches."""
        while True:
            try:
                await asyncio.sleep(0.1)  # Update every 100ms
                
                if self.progress_updates_queue:
                    async with self.update_lock:
                        updates = self.progress_updates_queue.copy()
                        self.progress_updates_queue.clear()
                    
                    await self._update_display_batch(updates)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.console.print(f"[red]Update error: {e}[/red]")
    
    async def _update_display_batch(self, updates: List[Dict[str, Any]]):
        """Update display with batched updates."""
        if not self.live_layout:
            return
        
        # Process all updates
        for update in updates:
            # Update internal state based on update type
            pass
        
        # Update all layout sections
        channels = list(self.channel_info.values())
        
        if channels:
            # Update header
            self.live_layout["header"].update(
                self.multi_interface._create_header_panel(channels)
            )
            
            # Update progress
            self.live_layout["progress"].update(
                self.multi_interface._create_overall_progress(channels)
            )
            
            # Update channel table
            self.live_layout["channels"].update(
                self.multi_interface._create_channel_progress_table(channels)
            )
            
            # Update details with recent activity
            if updates:
                last_update = updates[-1]
                details_text = self._format_activity(last_update)
                self.live_layout["details"].update(
                    Panel(details_text, title="Recent Activity", border_style="blue")
                )
    
    async def _update_display_immediate(self, update: Dict[str, Any]):
        """Update display immediately for critical updates."""
        await self._update_display_batch([update])
    
    def _format_activity(self, update: Dict[str, Any]) -> str:
        """Format activity update for display."""
        update_type = update.get('type', 'unknown')
        
        if update_type == 'channel_validated':
            channel = update['channel']
            return f"✅ Validated: {channel.snippet.title}\n   Videos: {channel.statistics.video_count}"
        
        elif update_type == 'channel_start':
            return f"▶️  Started: Channel processing\n   Total videos: {update['total_videos']}"
        
        elif update_type == 'video_processed':
            video = update['video']
            status = "✅" if update['success'] else "❌"
            return f"{status} Video: {video.title[:50]}..."
        
        elif update_type == 'channel_complete':
            stats = update['stats']
            return f"✅ Completed: Channel processing\n   Success rate: {stats.success_rate:.1%}"
        
        elif update_type == 'channel_error':
            return f"❌ Error: {update['error']}"
        
        return "Processing..."
    
    def _display_final_summary(self, summary: Dict[str, Any]):
        """Display final summary panel."""
        duration = datetime.now() - self.processing_start_time
        
        summary_text = f"""
[bold green]Batch Processing Complete![/bold green]

Total Channels: {summary.get('total_channels', 0)}
Successful: {summary.get('successful_channels', 0)}
Failed: {summary.get('failed_channels', 0)}

Total Videos: {summary.get('total_videos', 0)}
Processed: {summary.get('successful_videos', 0)}
Failed: {summary.get('failed_videos', 0)}

Duration: {self._format_duration(duration)}
Average Speed: {summary.get('avg_speed', 0):.1f} videos/min

Output Directory: {summary.get('output_dir', 'N/A')}
"""
        
        self.console.print(Panel(
            summary_text,
            title="Final Summary",
            border_style="green",
            expand=False
        ))
    
    def _format_duration(self, duration) -> str:
        """Format duration for display."""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"