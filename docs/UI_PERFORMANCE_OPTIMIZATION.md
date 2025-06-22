# UIパフォーマンス最適化ガイド

## 1. 現在の実装の分析

### A. パフォーマンスボトルネック
1. **高頻度更新**
   - 現在: 各動画処理ごとにUIイベント発生
   - 問題: 1000動画で1000回の更新

2. **大量データの表示**
   - 現在: 全チャンネルの全情報を保持
   - 問題: 50チャンネル以上でメモリ増大

3. **Rich ライブラリのオーバーヘッド**
   - 現在: 全更新で完全再描画
   - 問題: CPU使用率の増加

## 2. 最適化戦略

### A. 更新のバッチ処理（実装済み）
```python
class ProgressUpdateBatcher:
    def __init__(self, update_interval: float = 0.1):
        self.update_interval = update_interval  # 100ms
        self.pending_updates: Dict[str, Any] = {}
        
    async def add_update(self, channel_id: str, update: Any):
        # 最新の更新のみ保持（古い更新は上書き）
        self.pending_updates[channel_id] = update
```

**効果**: 
- 更新頻度を10Hz に制限
- 1000更新 → 最大100更新/秒

### B. 差分更新の実装
```python
class DifferentialUpdater:
    def __init__(self):
        self.last_state = {}
    
    def get_changes(self, current_state: Dict) -> Dict:
        """前回との差分のみ返す"""
        changes = {}
        for key, value in current_state.items():
            if key not in self.last_state or self.last_state[key] != value:
                changes[key] = value
        
        self.last_state = current_state.copy()
        return changes
```

**効果**:
- 変更のあった部分のみ再描画
- CPU使用率を50%削減

### C. 仮想スクロール実装
```python
class VirtualChannelList:
    def __init__(self, max_visible: int = 10):
        self.max_visible = max_visible
        self.scroll_offset = 0
    
    def get_visible_channels(self, all_channels: List[Channel]) -> List[Channel]:
        """表示範囲のチャンネルのみ返す"""
        start = self.scroll_offset
        end = start + self.max_visible
        return all_channels[start:end]
```

**効果**:
- 表示チャンネル数を制限
- メモリ使用量を一定に保つ

### D. 非同期レンダリング
```python
class AsyncRenderer:
    def __init__(self):
        self.render_queue = asyncio.Queue()
        self.render_task = None
    
    async def start(self):
        self.render_task = asyncio.create_task(self._render_loop())
    
    async def _render_loop(self):
        while True:
            # バッチで取得
            updates = []
            try:
                # 最大10ms待機して更新を集める
                deadline = asyncio.get_event_loop().time() + 0.01
                while asyncio.get_event_loop().time() < deadline:
                    update = await asyncio.wait_for(
                        self.render_queue.get(), 
                        timeout=0.001
                    )
                    updates.append(update)
            except asyncio.TimeoutError:
                pass
            
            if updates:
                await self._render_batch(updates)
```

**効果**:
- UIブロッキングを完全回避
- スムーズな操作性維持

## 3. メモリ最適化

### A. データ構造の最適化
```python
# Before: 完全なChannelオブジェクト保持
channels: Dict[str, Channel]  # ~1MB per channel

# After: 表示に必要な情報のみ
channel_display_data: Dict[str, ChannelDisplayInfo]  # ~10KB per channel

@dataclass
class ChannelDisplayInfo:
    """軽量な表示用データ"""
    id: str
    title: str
    progress: float
    status: str
    stats: CompactStats
```

### B. 完了チャンネルの圧縮
```python
class CompletedChannelCompressor:
    def compress(self, channel: Channel) -> CompressedChannel:
        """完了チャンネルを圧縮"""
        return CompressedChannel(
            id=channel.id,
            title=channel.snippet.title,
            summary=self._create_summary(channel),
            compressed_at=datetime.now()
        )
    
    def _create_summary(self, channel: Channel) -> str:
        """統計情報を文字列に圧縮"""
        stats = channel.processing_stats
        return f"{stats.successful_videos}/{stats.total_videos}"
```

### C. 循環参照の回避
```python
# 弱参照を使用
import weakref

class UIEventHandler:
    def __init__(self, bridge: 'UIBackendBridge'):
        self.bridge_ref = weakref.ref(bridge)
    
    @property
    def bridge(self):
        return self.bridge_ref()
```

## 4. レンダリング最適化

### A. レイアウトキャッシング
```python
class LayoutCache:
    def __init__(self):
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_or_create(self, key: str, factory):
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]
        
        self.cache_misses += 1
        layout = factory()
        self.cache[key] = layout
        return layout
```

### B. 条件付きレンダリング
```python
class ConditionalRenderer:
    def should_update(self, channel: Channel) -> bool:
        """更新が必要か判定"""
        # 変化がない場合はスキップ
        if channel.last_update_time < self.last_render_time:
            return False
        
        # 表示範囲外はスキップ
        if not self.is_visible(channel):
            return False
        
        return True
```

## 5. プロファイリングと計測

### A. パフォーマンスメトリクス
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'update_count': 0,
            'render_time': [],
            'memory_usage': [],
            'cpu_usage': []
        }
    
    @contextmanager
    def measure(self, operation: str):
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        yield
        
        elapsed = time.perf_counter() - start_time
        memory_delta = self._get_memory_usage() - start_memory
        
        self.metrics[f'{operation}_time'].append(elapsed)
        self.metrics[f'{operation}_memory'].append(memory_delta)
```

### B. デバッグモード
```python
# 環境変数で有効化
if os.getenv('UI_PERFORMANCE_DEBUG'):
    monitor = PerformanceMonitor()
    # 定期的にメトリクスを出力
```

## 6. 実装優先順位

### 高優先度（即効性あり）
1. ✅ バッチ更新（実装済み）
2. ⏳ 差分更新の実装
3. ⏳ 表示データの軽量化

### 中優先度（大規模処理で効果）
4. ⏳ 仮想スクロール
5. ⏳ 完了データの圧縮
6. ⏳ レイアウトキャッシング

### 低優先度（将来の拡張）
7. ⏳ WebSocket による別プロセス表示
8. ⏳ 分散レンダリング
9. ⏳ GPU アクセラレーション

## 7. ベンチマーク結果（期待値）

### Before（最適化前）
- 50チャンネル処理: CPU 80%, Memory 500MB
- 更新レート: 1000 updates/sec
- UI応答性: 100ms遅延

### After（最適化後）
- 50チャンネル処理: CPU 30%, Memory 200MB
- 更新レート: 100 updates/sec（バッチ）
- UI応答性: 10ms遅延

### 改善率
- CPU使用率: 62.5%削減
- メモリ使用量: 60%削減
- 応答性: 10倍向上

## 8. 実装例

### 最適化されたupdate_display_batch
```python
async def update_display_batch_optimized(self, updates: List[Dict]):
    """最適化された表示更新"""
    # 1. 差分計算
    changes = self.differential_updater.get_changes(updates)
    if not changes:
        return
    
    # 2. 表示範囲チェック
    visible_updates = [
        u for u in changes 
        if self.is_channel_visible(u['channel_id'])
    ]
    
    # 3. レイアウトキャッシュ使用
    layout = self.layout_cache.get_or_create(
        'main_layout',
        lambda: self._create_layout()
    )
    
    # 4. 部分更新のみ実行
    for update in visible_updates:
        section = self._get_layout_section(update['type'])
        if section:
            layout[section].update(self._render_update(update))
    
    # 5. メトリクス記録
    if self.performance_monitor:
        self.performance_monitor.record_update(len(updates))
```

この最適化により、大規模な複数チャンネル処理でもスムーズなUI表示を維持できます。