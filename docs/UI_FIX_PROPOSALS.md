# YouTube Transcriber UI修正案 - フロントエンド実装準備

## 1. プログレスバー問題の修正案

### 問題
`orchestrator.py:170`で`with self.display.create_progress() as progress:`として使用されているが、`create_progress()`メソッドは単にProgressオブジェクトを返すだけで、コンテキストマネージャーではない。

### 修正案A: DisplayManagerをコンテキストマネージャーとして実装
```python
# display.py の修正
class ProgressContext:
    """Progress tracking context manager."""
    
    def __init__(self, display_manager: 'DisplayManager'):
        self.display = display_manager
        self.progress = display_manager.progress
        
    def __enter__(self):
        self.display.start()  # Live displayを開始
        return self.progress
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.display.stop()  # Live displayを停止
        return False

# DisplayManagerに追加
def create_progress_context(self) -> ProgressContext:
    """Create a context manager for progress tracking."""
    return ProgressContext(self)
```

### 修正案B: orchestratorの使用方法を変更
```python
# orchestrator.py の修正
async def _process_videos_parallel(self, channel, videos, language):
    """Process videos with proper display management."""
    # Liveディスプレイを明示的に開始
    self.display.start()
    try:
        progress = self.display.create_progress()
        task_id = progress.add_task(f"Processing {len(videos)} videos", total=len(videos))
        # ... 処理続行
    finally:
        # 必ずLiveディスプレイを停止
        self.display.stop()
```

## 2. Live Display開始/停止処理の実装案

### 問題
`DisplayManager`の`start()`と`stop()`メソッドが呼び出されていない。

### 修正案: アプリケーションライフサイクルに統合
```python
# orchestrator.py の修正
class TranscriptOrchestrator:
    async def process_channel(self, channel_input: str, language: str):
        """Process channel with proper display lifecycle."""
        # 処理開始時にディスプレイを開始
        self.display.start()
        
        try:
            # 既存の処理ロジック
            channel = await self._get_channel_info(channel_input)
            # ...
        finally:
            # 必ず停止（エラー時も含む）
            self.display.stop()
```

### 追加改善: 自動リソース管理
```python
# display.py に追加
class DisplayManager:
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False

# 使用例
async with DisplayManager() as display:
    orchestrator = TranscriptOrchestrator(display=display, ...)
    await orchestrator.process_channel(...)
```

## 3. エラーハンドリング改善の実装案

### 問題
Rich console操作でエラーが発生した場合、アプリケーション全体がクラッシュする。

### 修正案: 全表示メソッドにtry-exceptを追加
```python
# display.py の修正例
def show_channel_info(self, channel: Channel):
    """Display channel information with error handling."""
    try:
        info_table = Table(title=f"Channel: {channel.snippet.title}", show_header=False)
        # ... 既存のテーブル構築コード
        self.console.print(info_table)
    except Exception as e:
        # フォールバック: プレーンテキスト表示
        self._fallback_channel_info(channel)
        logger.warning(f"Rich display failed, using fallback: {e}")

def _fallback_channel_info(self, channel: Channel):
    """Fallback display for terminal compatibility issues."""
    print(f"\n=== Channel: {channel.snippet.title} ===")
    print(f"Channel ID: {channel.id}")
    print(f"URL: {channel.url}")
    if channel.statistics:
        print(f"Subscribers: {channel.statistics.subscriber_count:,}")
        print(f"Total Videos: {channel.statistics.video_count:,}")
```

### グローバルエラーハンドラー
```python
# display.py に追加
def _safe_console_operation(self, operation, *args, **kwargs):
    """Execute console operation with error handling."""
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        logger.error(f"Console operation failed: {e}")
        # 基本的なprint()にフォールバック
        self._use_basic_output = True
        return None
```

## 4. 複数チャンネル選択UIのワイヤーフレーム設計

### CLIインターフェース拡張案

#### オプション1: バッチファイル入力
```bash
# channels.txt ファイルから読み込み
youtube-transcriber --batch channels.txt

# channels.txt の形式:
# @mkbhd
# https://youtube.com/@LinusTechTips
# UCBJycsmduvYEL83R_U4JriQ
```

#### オプション2: 対話型選択モード
```bash
youtube-transcriber --interactive

# 表示例:
┌─────────────────────────────────────────────┐
│ YouTube Transcriber - Multi-Channel Mode    │
├─────────────────────────────────────────────┤
│ Enter channel URLs/IDs (one per line):      │
│ Press Enter twice to start processing       │
│                                             │
│ > @mkbhd                                    │
│ > @LinusTechTips                           │
│ > _                                         │
└─────────────────────────────────────────────┘

# 確認画面
┌─────────────────────────────────────────────┐
│ Channels to Process (3 total)               │
├─────────────────────────────────────────────┤
│ 1. MKBHD (15M subscribers)                  │
│ 2. Linus Tech Tips (15.4M subscribers)      │
│ 3. ...                                      │
├─────────────────────────────────────────────┤
│ [P]roceed  [E]dit  [C]ancel                │
└─────────────────────────────────────────────┘
```

#### オプション3: 複数引数サポート
```bash
youtube-transcriber @mkbhd @LinusTechTips @verge --parallel 3
```

### 進捗表示の拡張
```
┌─────────────────────────────────────────────────────┐
│ Multi-Channel Processing Progress                    │
├─────────────────────────────────────────────────────┤
│ Overall: ████████░░░░░░░░░░░░ 40% (2/5 channels)   │
├─────────────────────────────────────────────────────┤
│ ✓ MKBHD          [████████████] 100% (350/350)     │
│ ✓ LinusTechTips  [████████████] 100% (500/500)     │
│ ▶ The Verge      [███░░░░░░░░░]  25% (125/500)     │
│ ⏸ TechCrunch     Waiting...                         │
│ ⏸ Wired          Waiting...                         │
├─────────────────────────────────────────────────────┤
│ Time: 00:15:30 | ETA: 00:23:15 | Rate: 45 vid/min  │
└─────────────────────────────────────────────────────┘
```

## 5. ユーザビリティ改善の追加提案

### A. 初回セットアップウィザード
```bash
youtube-transcriber init

# ウィザード画面
Welcome to YouTube Transcriber Setup!

Step 1: YouTube API Key
Do you have a YouTube Data API key? (y/n): n

Let me guide you through getting one:
1. Visit: https://console.cloud.google.com
2. Create a new project...
[詳細な手順を表示]

Enter your API key: **********************
✓ API key validated successfully!

Step 2: Default Settings
Choose default output format:
1) JSON (structured data)
2) Markdown (human-readable)
3) Plain text
Selection [1-3]: 2

Step 3: Performance Settings
Maximum concurrent downloads [1-10, default: 5]: 3

Setup complete! Configuration saved to ~/.youtube-transcriber/config.json
```

### B. エラーメッセージの改善
```python
# 現在のエラー表示
ERROR: 'NoneType' object has no attribute 'get'

# 改善後
ERROR: Unable to fetch channel information
Possible causes:
  • Invalid channel URL or ID
  • Network connection issues
  • YouTube API quota exceeded

Try:
  • Check the channel URL: youtube-transcriber "@channelname"
  • Verify your internet connection
  • Wait 24 hours if quota exceeded
  
For more help: youtube-transcriber --help
```

### C. 進捗の永続化と再開機能
```python
# セッション保存
{
    "session_id": "2024-01-20-mkbhd-abc123",
    "channel_id": "UCBJycsmduvYEL83R_U4JriQ",
    "total_videos": 500,
    "processed_videos": 250,
    "last_processed_video_id": "dQw4w9WgXcQ",
    "timestamp": "2024-01-20T15:30:00Z"
}

# 再開コマンド
youtube-transcriber --resume 2024-01-20-mkbhd-abc123
# または
youtube-transcriber @mkbhd --resume-last
```

## 実装優先順位

1. **即座に実装すべき修正（Phase 3開始時）**
   - プログレスバーのコンテキストマネージャー修正
   - Live Display の start/stop 呼び出し追加
   - 基本的なエラーハンドリング

2. **次の反復で実装**
   - 複数チャンネルバッチ処理
   - エラーメッセージの改善
   - 進捗の永続化

3. **将来の機能拡張**
   - 対話型セットアップウィザード
   - Web UIオプション
   - プラグインシステム