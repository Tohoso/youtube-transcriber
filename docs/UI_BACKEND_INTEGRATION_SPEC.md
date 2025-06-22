# UI-バックエンド統合仕様書

## 1. 概要
複数チャンネル処理機能におけるUIとバックエンドの統合ポイントを定義します。

## 2. インターフェース定義

### 2.1 UIBackendBridge クラス

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from datetime import datetime

class UIBackendBridge(ABC):
    """UIとバックエンドの通信を仲介する抽象クラス"""
    
    @abstractmethod
    async def on_batch_start(self, channels: List[str], config: ProcessingConfig):
        """バッチ処理開始時のコールバック"""
        pass
    
    @abstractmethod
    async def on_channel_validated(self, channel_id: str, channel_info: ChannelInfo):
        """チャンネル検証完了時のコールバック"""
        pass
    
    @abstractmethod
    async def on_channel_start(self, channel_id: str, total_videos: int):
        """チャンネル処理開始時のコールバック"""
        pass
    
    @abstractmethod
    async def on_video_processed(self, channel_id: str, video: Video, success: bool):
        """動画処理完了時のコールバック"""
        pass
    
    @abstractmethod
    async def on_channel_complete(self, channel_id: str, stats: ProcessingStatistics):
        """チャンネル処理完了時のコールバック"""
        pass
    
    @abstractmethod
    async def on_channel_error(self, channel_id: str, error: Exception) -> RecoveryAction:
        """エラー発生時のコールバック（リカバリアクション選択）"""
        pass
    
    @abstractmethod
    async def on_batch_complete(self, summary: BatchProcessingSummary):
        """バッチ処理完了時のコールバック"""
        pass
```

### 2.2 UI側の実装

```python
class UIBackendBridgeImpl(UIBackendBridge):
    """UI側のブリッジ実装"""
    
    def __init__(self, display_manager: DisplayManager):
        self.display = display_manager
        self.state_manager = MultiChannelStateManager()
        self.live_display = LiveMultiChannelDisplay()
    
    async def on_batch_start(self, channels: List[str], config: ProcessingConfig):
        """バッチ開始時: 全体進捗UIを初期化"""
        self.live_display.initialize(channels, config)
        self.live_display.start()
        
        for channel in channels:
            self.state_manager.set_state(channel, ChannelStatus.PENDING)
    
    async def on_channel_validated(self, channel_id: str, channel_info: ChannelInfo):
        """検証完了: チャンネル情報を表示"""
        self.state_manager.set_channel_info(channel_id, channel_info)
        self.live_display.update_channel_card(channel_id, channel_info)
    
    async def on_video_processed(self, channel_id: str, video: Video, success: bool):
        """動画処理完了: 進捗を更新"""
        self.state_manager.increment_progress(channel_id)
        
        # リアルタイム更新（バッチング対応）
        await self.live_display.update_channel_progress(
            channel_id,
            self.state_manager.get_progress(channel_id)
        )
        
        # 最近の処理結果を表示
        if self.display.should_show_recent_results():
            self.display.show_video_result(video)
```

### 2.3 バックエンド側の要件

```python
class BatchOrchestrator:
    """バックエンド側のバッチ処理オーケストレーター"""
    
    def __init__(self, ui_bridge: UIBackendBridge):
        self.ui_bridge = ui_bridge
        self.channel_semaphore = asyncio.Semaphore(3)  # 並列チャンネル数
        self.video_semaphore = asyncio.Semaphore(5)    # 並列動画数
    
    async def process_batch(self, channel_inputs: List[str], config: ProcessingConfig):
        """バッチ処理のメインループ"""
        # UIに開始を通知
        await self.ui_bridge.on_batch_start(channel_inputs, config)
        
        # チャンネル検証
        channels = await self._validate_channels(channel_inputs)
        
        # 並列処理
        tasks = []
        for channel in channels:
            task = self._process_channel_with_ui(channel)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 完了通知
        summary = self._create_summary(results)
        await self.ui_bridge.on_batch_complete(summary)
    
    async def _process_channel_with_ui(self, channel: Channel):
        """UI通知を含むチャンネル処理"""
        async with self.channel_semaphore:
            try:
                # 開始通知
                await self.ui_bridge.on_channel_start(
                    channel.id,
                    len(channel.videos)
                )
                
                # 動画を処理
                for video in channel.videos:
                    success = await self._process_video(video)
                    
                    # 各動画の完了を通知
                    await self.ui_bridge.on_video_processed(
                        channel.id,
                        video,
                        success
                    )
                
                # 完了通知
                await self.ui_bridge.on_channel_complete(
                    channel.id,
                    channel.processing_stats
                )
                
            except Exception as e:
                # エラー処理とリカバリ
                action = await self.ui_bridge.on_channel_error(channel.id, e)
                await self._handle_recovery(channel, action)
```

## 3. データモデル

### 3.1 共有データ構造

```python
@dataclass
class ChannelInfo:
    """チャンネル基本情報"""
    id: str
    title: str
    subscriber_count: int
    video_count: int
    thumbnail_url: str

@dataclass
class ProcessingConfig:
    """処理設定"""
    parallel_channels: int = 3
    parallel_videos: int = 5
    output_format: str = "json"
    output_directory: Path = Path("./output")
    skip_existing: bool = True
    language: str = "en"

@dataclass
class BatchProcessingSummary:
    """バッチ処理サマリー"""
    total_channels: int
    successful_channels: int
    failed_channels: int
    total_videos: int
    successful_videos: int
    total_duration: timedelta
    export_results: Dict[str, bool]

class RecoveryAction(Enum):
    """エラー時のリカバリアクション"""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    RETRY_LATER = "retry_later"
```

### 3.2 イベントシステム

```python
@dataclass
class ProcessingEvent:
    """処理イベント"""
    type: EventType
    channel_id: str
    timestamp: datetime
    data: Dict[str, Any]

class EventType(Enum):
    """イベントタイプ"""
    CHANNEL_QUEUED = "channel_queued"
    CHANNEL_STARTED = "channel_started"
    CHANNEL_PROGRESS = "channel_progress"
    CHANNEL_COMPLETED = "channel_completed"
    CHANNEL_FAILED = "channel_failed"
    VIDEO_PROCESSED = "video_processed"
    BATCH_COMPLETED = "batch_completed"
```

## 4. 非同期通信パターン

### 4.1 プログレス更新の最適化

```python
class ProgressUpdateBatcher:
    """進捗更新をバッチ処理"""
    
    def __init__(self, update_interval: float = 0.1):
        self.update_interval = update_interval
        self.pending_updates: Dict[str, ProgressUpdate] = {}
        self._update_task = None
    
    async def add_update(self, channel_id: str, update: ProgressUpdate):
        """更新をキューに追加"""
        self.pending_updates[channel_id] = update
        
        if not self._update_task:
            self._update_task = asyncio.create_task(self._batch_update())
    
    async def _batch_update(self):
        """バッチ更新の実行"""
        await asyncio.sleep(self.update_interval)
        
        if self.pending_updates:
            updates = list(self.pending_updates.values())
            self.pending_updates.clear()
            
            # UIに一括更新
            await self.ui.batch_update_progress(updates)
        
        self._update_task = None
```

### 4.2 エラーハンドリングとリトライ

```python
class ErrorHandler:
    """エラーハンドリングとリトライロジック"""
    
    def __init__(self, ui_bridge: UIBackendBridge):
        self.ui_bridge = ui_bridge
        self.retry_configs = {
            APIQuotaError: RetryConfig(max_attempts=3, delay=3600),
            NetworkError: RetryConfig(max_attempts=5, delay=30),
            TranscriptNotAvailable: RetryConfig(max_attempts=1, delay=0)
        }
    
    async def handle_error(self, channel_id: str, error: Exception) -> RecoveryAction:
        """エラーハンドリング"""
        retry_config = self.retry_configs.get(type(error))
        
        if retry_config and retry_config.should_retry():
            # UIにリトライ確認
            return await self.ui_bridge.on_channel_error(channel_id, error)
        else:
            # リトライ不可
            return RecoveryAction.SKIP
```

## 5. パフォーマンス考慮事項

### 5.1 メモリ管理

```python
class MemoryEfficientChannelProcessor:
    """メモリ効率的なチャンネル処理"""
    
    def __init__(self, max_videos_in_memory: int = 100):
        self.max_videos_in_memory = max_videos_in_memory
    
    async def process_channel_streaming(self, channel: Channel):
        """ストリーミング処理"""
        # 動画リストを分割
        for video_batch in self._batch_videos(channel.videos):
            # バッチごとに処理
            await self._process_video_batch(video_batch)
            
            # 処理済みデータをクリア
            self._clear_processed_data(video_batch)
```

### 5.2 並列度の動的調整

```python
class DynamicConcurrencyManager:
    """動的な並列度管理"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
        self.current_limits = {
            'channels': 3,
            'videos': 5
        }
    
    async def adjust_concurrency(self):
        """パフォーマンスに基づいて並列度を調整"""
        metrics = await self.performance_monitor.get_metrics()
        
        if metrics.cpu_usage < 50 and metrics.memory_usage < 70:
            # リソースに余裕がある場合は増やす
            self.current_limits['videos'] = min(10, self.current_limits['videos'] + 1)
        elif metrics.cpu_usage > 80 or metrics.memory_usage > 85:
            # リソースが逼迫している場合は減らす
            self.current_limits['videos'] = max(2, self.current_limits['videos'] - 1)
```

## 6. テスト戦略

### 6.1 統合テストシナリオ

1. **正常系フロー**
   - 3チャンネルの並列処理
   - 進捗更新の確認
   - 完了通知の確認

2. **エラー処理**
   - APIクォータエラー時のリトライ
   - ネットワークエラー時の処理
   - 部分的失敗の処理

3. **パフォーマンス**
   - 大量チャンネル（10+）の処理
   - メモリ使用量の監視
   - UI更新のレスポンス

### 6.2 モックとスタブ

```python
class MockUIBridge(UIBackendBridge):
    """テスト用モックUIブリッジ"""
    
    def __init__(self):
        self.events = []
        self.recovery_actions = {}
    
    async def on_channel_error(self, channel_id: str, error: Exception) -> RecoveryAction:
        self.events.append(('error', channel_id, error))
        return self.recovery_actions.get(channel_id, RecoveryAction.SKIP)
```

## 7. 実装スケジュール

1. **Phase 1**: 基本的な通信インターフェース（UIBackendBridge）
2. **Phase 2**: イベントシステムと状態管理
3. **Phase 3**: エラーハンドリングとリカバリ
4. **Phase 4**: パフォーマンス最適化とモニタリング