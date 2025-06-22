# 複数チャンネルUI詳細機能設計書

## 1. 概要
YouTube Transcriberの複数チャンネル処理機能のUI設計を詳細化します。ユーザビリティと拡張性を重視した設計となっています。

## 2. UIコンポーネント設計

### 2.1 チャンネル入力インターフェース

#### A. バッチファイル処理
```bash
youtube-transcriber batch channels.txt [OPTIONS]
```

**channels.txt フォーマット**:
```
# YouTube Channels to Process
# Format: URL, @handle, or channel ID

# Tech Channels
@mkbhd
https://youtube.com/@LinusTechTips
UCBJycsmduvYEL83R_U4JriQ

# News Channels
@verge
@techcrunch
```

#### B. 対話型インターフェース
```python
class InteractiveChannelSelector:
    def __init__(self):
        self.channels = []
        self.validation_results = {}
    
    async def validate_channel(self, channel_input: str) -> ValidationResult:
        """リアルタイムチャンネル検証"""
        # APIを使用してチャンネルの存在確認
        # チャンネル情報（名前、動画数）を取得
        pass
    
    def display_validation_result(self, result: ValidationResult):
        """検証結果の表示"""
        if result.is_valid:
            # ✅ MKBHD (1,234 videos)
        else:
            # ❌ Invalid channel: {reason}
```

#### C. コマンドライン複数引数
```bash
youtube-transcriber multi @mkbhd @verge @techcrunch --parallel 3
```

### 2.2 進捗表示システム

#### A. 全体進捗ダッシュボード
```
┌─────────────────────────────────────────────────────────────┐
│ YouTube Transcriber - Multi-Channel Processing              │
├─────────────────────────────────────────────────────────────┤
│ Overall Progress: ████████████░░░░░░░ 60% (3/5 channels)    │
│ Time Elapsed: 00:45:30 | ETA: 00:30:20                     │
│ Processing Rate: 42 videos/min | Total Videos: 2,345        │
├─────────────────────────────────────────────────────────────┤
│ Channel Status Overview:                                     │
│ ✅ Complete: 2 | ▶️ Processing: 1 | ⏸️ Waiting: 2          │
└─────────────────────────────────────────────────────────────┘
```

#### B. 個別チャンネル進捗
```python
class ChannelProgressDisplay:
    def render_channel_card(self, channel: Channel) -> Panel:
        """個別チャンネルのカード表示"""
        return Panel(
            f"""
            Channel: {channel.snippet.title}
            Progress: {self._render_progress_bar(channel.processing_stats)}
            Videos: {stats.processed_videos}/{stats.total_videos}
            Success Rate: {stats.success_rate:.1%}
            Status: {self._get_status_emoji(stats)} {status_text}
            
            Recent: {self._get_recent_videos(channel, limit=3)}
            Errors: {stats.failed_videos} ({self._get_error_summary(stats)})
            """,
            title=channel.snippet.title,
            border_style=self._get_border_style(stats)
        )
```

#### C. リアルタイム更新
```python
class LiveMultiChannelDisplay:
    def __init__(self):
        self.layout = Layout()
        self.live = Live(self.layout, refresh_per_second=2)
    
    def setup_layout(self):
        """レイアウト構成"""
        self.layout.split_column(
            Layout(name="header", size=7),  # 全体進捗
            Layout(name="channels"),         # チャンネル一覧
            Layout(name="footer", size=3)    # 統計情報
        )
```

### 2.3 エラー処理とリカバリUI

#### A. エラー集約ビュー
```
┌─────────────────────────────────────────────────────────────┐
│ Error Summary (3 channels affected)                          │
├─────────────────────────────────────────────────────────────┤
│ MKBHD:                                                       │
│   • 5 videos failed: API quota exceeded                     │
│   • Action: Will retry in 1 hour                           │
│                                                             │
│ The Verge:                                                  │
│   • 2 videos failed: No transcript available               │
│   • Action: Skipped (no action needed)                     │
└─────────────────────────────────────────────────────────────┘
```

#### B. インタラクティブリカバリ
```python
class ErrorRecoveryInterface:
    async def handle_channel_error(self, channel: Channel, error: Exception):
        """エラー時の対話的リカバリ"""
        options = self._get_recovery_options(error)
        
        choice = Prompt.ask(
            f"\n[red]Error processing {channel.snippet.title}[/red]\n"
            f"Reason: {error}\n\n"
            "Choose action:",
            choices=options,
            default="skip"
        )
        
        return self._execute_recovery(choice, channel)
```

### 2.4 結果表示とエクスポート

#### A. 統合サマリー表示
```python
class MultiChannelSummaryDisplay:
    def render_final_summary(self, channels: List[Channel]):
        """最終結果のサマリー表示"""
        # 全体統計
        total_stats = self._aggregate_statistics(channels)
        
        # チャンネル別サマリーテーブル
        table = Table(title="Processing Summary")
        table.add_column("Channel")
        table.add_column("Videos", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Export", justify="center")
        
        for channel in channels:
            table.add_row(
                channel.snippet.title,
                str(channel.processing_stats.total_videos),
                f"{channel.processing_stats.success_rate:.1%}",
                str(channel.processing_stats.failed_videos),
                self._format_duration(channel.processing_duration),
                "✅" if channel.export_successful else "❌"
            )
```

#### B. エクスポートオプション
```python
class ExportOptionsInterface:
    def get_export_preferences(self) -> ExportConfig:
        """エクスポート設定の対話的取得"""
        config = ExportConfig()
        
        # 出力形式
        config.format = Prompt.ask(
            "Export format",
            choices=["json", "markdown", "csv", "all"],
            default="json"
        )
        
        # 構造オプション
        config.structure = Prompt.ask(
            "Directory structure",
            choices=["flat", "by-channel", "by-date"],
            default="by-channel"
        )
        
        # 統合オプション
        if Confirm.ask("Create combined summary?"):
            config.create_summary = True
            config.summary_format = Prompt.ask(
                "Summary format",
                choices=["markdown", "html"],
                default="markdown"
            )
        
        return config
```

## 3. 状態管理とデータフロー

### 3.1 チャンネル処理状態
```python
@dataclass
class ChannelProcessingState:
    channel_id: str
    status: ChannelStatus  # PENDING, VALIDATING, PROCESSING, COMPLETE, ERROR
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[Exception]
    retry_count: int = 0
    
class MultiChannelStateManager:
    def __init__(self):
        self.states: Dict[str, ChannelProcessingState] = {}
        self.listeners: List[StateChangeListener] = []
    
    def update_state(self, channel_id: str, status: ChannelStatus):
        """状態更新と通知"""
        self.states[channel_id].status = status
        self._notify_listeners(channel_id, status)
```

### 3.2 UIイベントシステム
```python
class UIEventBus:
    """UI更新のためのイベントバス"""
    
    async def emit(self, event: UIEvent):
        """イベント発行"""
        if event.type == EventType.CHANNEL_PROGRESS:
            await self.display.update_channel_progress(event.data)
        elif event.type == EventType.ERROR_OCCURRED:
            await self.display.show_error_notification(event.data)
```

## 4. パフォーマンス最適化

### 4.1 表示更新の最適化
- バッチ更新: 100ms間隔で更新をバッチ処理
- 差分更新: 変更があった部分のみ再描画
- スクロール対応: 大量チャンネル時の仮想スクロール

### 4.2 メモリ効率
- 表示データのキャッシュ制限
- 完了チャンネルの表示データ圧縮
- ストリーミング表示（一度に全データを保持しない）

## 5. アクセシビリティ

### 5.1 スクリーンリーダー対応
```python
class AccessibleDisplay:
    def __init__(self, screen_reader_mode: bool = False):
        self.screen_reader_mode = screen_reader_mode
    
    def show_progress(self, channel: Channel):
        if self.screen_reader_mode:
            # テキストのみの進捗表示
            print(f"Processing {channel.snippet.title}: "
                  f"{channel.processing_stats.progress_percentage}% complete")
        else:
            # Rich UIでの表示
            self._show_rich_progress(channel)
```

### 5.2 キーボードナビゲーション
- Tab: 次のチャンネルへフォーカス
- Space: チャンネル詳細の展開/折りたたみ
- R: 失敗したチャンネルのリトライ
- S: 処理の一時停止/再開

## 6. 統合ポイント

### 6.1 バックエンドとの連携
```python
class UIBackendBridge:
    """UIとバックエンドの連携インターフェース"""
    
    async def on_channel_start(self, channel_id: str):
        await self.ui.mark_channel_processing(channel_id)
    
    async def on_video_complete(self, channel_id: str, video: Video):
        await self.ui.update_channel_progress(channel_id, video)
    
    async def on_channel_complete(self, channel_id: str, stats: ProcessingStatistics):
        await self.ui.mark_channel_complete(channel_id, stats)
```

### 6.2 設定管理
```python
class MultiChannelUIConfig:
    """UI設定"""
    refresh_rate: int = 2  # Hz
    max_channels_display: int = 10
    show_detailed_progress: bool = True
    enable_animations: bool = True
    color_scheme: str = "auto"  # auto, light, dark
```

## 7. 実装優先順位

1. **Phase 1**: 基本的な複数チャンネル表示
2. **Phase 2**: リアルタイム進捗更新
3. **Phase 3**: エラー処理とリカバリUI
4. **Phase 4**: 高度な機能（アクセシビリティ、アニメーション）