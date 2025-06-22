# 複数チャンネル処理 API仕様書

## 概要

YouTube Transcriberの複数チャンネル処理機能は、複数のYouTubeチャンネルから効率的にトランスクリプトを取得するためのAPIを提供します。

## アーキテクチャ

### コンポーネント構成

```
┌─────────────────────────────────────────────────────────┐
│                    CLI Interface                         │
│  (multi_channel_interface.py)                           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              BatchChannelOrchestrator                    │
│  ・全体制御     ・進捗管理     ・エラー集約            │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│             MultiChannelProcessor                        │
│  ・並行処理制御  ・キューイング  ・リソース管理        │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│ QuotaTracker  │ │ Channel    │ │ Transcript │
│               │ │ Service    │ │ Service    │
└───────────────┘ └────────────┘ └────────────┘
```

## 主要クラス

### 1. BatchChannelOrchestrator

**責務**: 複数チャンネル処理の全体統括

```python
class BatchChannelOrchestrator:
    def __init__(self, settings: AppSettings):
        """
        Args:
            settings: アプリケーション設定
        """
    
    async def process_channels(
        self,
        channel_inputs: List[str],
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        output_format: str = "txt",
        dry_run: bool = False
    ) -> BatchProcessingResult:
        """複数チャンネルの処理
        
        Args:
            channel_inputs: チャンネル識別子のリスト
            language: トランスクリプト言語
            date_from: 開始日フィルター（YYYY-MM-DD）
            date_to: 終了日フィルター（YYYY-MM-DD）
            output_format: 出力形式
            dry_run: テスト実行
            
        Returns:
            BatchProcessingResult: 処理結果
        """
```

### 2. MultiChannelProcessor

**責務**: 効率的な並行処理とリソース管理

```python
class MultiChannelProcessor:
    async def process_channels_batch(
        self,
        channel_inputs: List[str],
        language: str = "ja",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> BatchProcessingResult:
        """バッチ処理の実行
        
        Features:
        - チャンネルレベル並行処理（デフォルト: 3）
        - ビデオレベル並行処理（デフォルト: 5）
        - メモリ使用量監視
        - APIクォータ管理
        """
```

### 3. データモデル

#### BatchConfig
```python
class BatchConfig(BaseModel):
    max_channels: int = 3              # 最大同時処理チャンネル数
    channel_timeout_minutes: int = 60  # チャンネルあたりのタイムアウト
    save_progress: bool = True         # 進捗保存有効化
    progress_file: Path = Path(".progress.json")
    queue_size: int = 100             # ビデオキューサイズ
    batch_size: int = 10              # バッチ処理サイズ
    memory_limit_mb: int = 1024       # メモリ制限
```

#### ChannelProgress
```python
class ChannelProgress(BaseModel):
    channel_id: str
    status: Literal["pending", "processing", "completed", "failed", "partial"]
    processed_videos: int
    successful_videos: int
    failed_videos: int
    total_videos: int
    progress_percentage: float  # 計算プロパティ
    success_rate: float        # 計算プロパティ
```

#### BatchProcessingResult
```python
class BatchProcessingResult(BaseModel):
    total_channels: int
    successful_channels: List[str]
    failed_channels: Dict[str, str]
    partial_channels: Dict[str, Any]
    total_videos_processed: int
    total_videos_successful: int
    total_videos_failed: int
    quota_usage: Dict[str, Any]
    overall_success_rate: float  # 計算プロパティ
```

## CLI コマンド

### 1. バッチ処理

```bash
# 基本的な使用方法
youtube-transcriber batch channels.txt

# 詳細オプション
youtube-transcriber batch channels.txt \
    --output-dir ./output \
    --parallel-channels 5 \
    --parallel-videos 10 \
    --language en \
    --filter large \
    --sort subscribers \
    --resume
```

**channels.txt の形式:**
```
@mkbhd
https://www.youtube.com/@LinusTechTips
UCXuqSBlHAE6Xw-yeJA0Tunw
# コメント行はスキップされます
@UnboxTherapy
```

### 2. 対話型モード

```bash
youtube-transcriber interactive
```

**機能:**
- チャンネルの対話的追加
- YouTube検索（未実装）
- フィルタリング・ソート
- バリデーション
- 進捗のリアルタイム表示

### 3. 進捗モニタリング（未実装）

```bash
youtube-transcriber monitor [session-id]
```

## 並行処理戦略

### 1. 階層的並行制御

```
Level 1: Channel Concurrency (max_channels = 3)
├── Channel 1 ─┐
├── Channel 2 ─┼─► Global QuotaTracker
└── Channel 3 ─┘   Global RateLimiter
    │
    └── Level 2: Video Concurrency (concurrent_limit = 5)
        ├── Video 1
        ├── Video 2
        ├── Video 3
        ├── Video 4
        └── Video 5
```

### 2. リソース管理

**メモリ管理:**
- 設定可能なメモリ制限（デフォルト: 1024MB）
- メモリ使用量の定期的チェック
- 制限接近時の自動待機

**APIクォータ管理:**
- グローバルQuotaTrackerによる統一管理
- 日次クォータの追跡（デフォルト: 10,000）
- クォータ枯渇時の自動待機

**レート制限:**
- AdaptiveRateLimiterによる動的調整
- エラー率に基づく自動速度調整
- チャンネル間で共有

## エラーハンドリング

### 1. エラー分離

各チャンネルは独立して処理され、一つのチャンネルのエラーが他に影響しません。

```python
# エラー分類
- Network Error: ネットワーク接続問題
- Permission Error: アクセス権限なし
- Quota Exceeded: APIクォータ超過
- Transcript Error: トランスクリプト取得失敗
- Timeout: タイムアウト
```

### 2. リカバリー戦略

```python
ErrorHandler.get_recovery_strategy(error_category) -> {
    "retry": bool,           # リトライ可否
    "retry_count": int,      # リトライ回数
    "retry_delay": float,    # 待機時間
    "fallback": str          # フォールバック方法
}
```

## パフォーマンス最適化

### 1. バッチ処理

ビデオはバッチ単位で処理され、メモリ効率を向上：

```python
ProcessingQueue(
    batch_size=10  # 10ビデオずつ処理
)
```

### 2. ストリーミング処理

大規模チャンネル対応：
- 処理済みデータの即座解放
- 段階的な結果出力

### 3. 進捗永続化

中断/再開対応：
```json
{
  "processed_channels": ["@channel1", "@channel2"],
  "channel_progress": {
    "@channel3": {
      "status": "processing",
      "processed_videos": 45,
      "total_videos": 100
    }
  }
}
```

## 使用例

### Python API（内部使用）

```python
from youtube_transcriber import BatchChannelOrchestrator

async def process_multiple_channels():
    settings = AppSettings(
        api={"youtube_api_key": "YOUR_KEY"},
        batch=BatchConfig(max_channels=5)
    )
    
    async with BatchChannelOrchestrator(settings) as orchestrator:
        result = await orchestrator.process_channels(
            channel_inputs=["@mkbhd", "@LinusTechTips"],
            language="en"
        )
        
        print(f"Success rate: {result.overall_success_rate:.1f}%")
```

## 制限事項

1. **最大同時チャンネル数**: 10（設定可能）
2. **メモリ制限**: システムメモリに依存
3. **APIクォータ**: YouTube API の日次制限に準拠
4. **タイムアウト**: チャンネルあたり60分（設定可能）

## 今後の拡張

1. **YouTube検索統合**: チャンネル検索機能
2. **進捗モニタリング**: 実行中セッションの監視
3. **スケジューリング**: 定期実行対応
4. **クラウド統合**: S3等への直接出力
5. **Webhook通知**: 完了/エラー通知