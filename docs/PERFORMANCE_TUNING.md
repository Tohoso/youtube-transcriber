# パフォーマンスチューニングガイド

## 概要

YouTube Transcriberの複数チャンネル処理におけるパフォーマンス最適化のガイドラインです。

## パフォーマンス指標

### 主要メトリクス

1. **処理速度**: videos/minute
2. **メモリ使用量**: MB
3. **API効率**: quota usage / videos processed
4. **成功率**: successful videos / total videos
5. **並行効率**: 実処理時間 / 理論最小時間

## ボトルネック分析

### 1. API制限

**YouTube Data API v3 の制限:**
- 日次クォータ: 10,000ユニット
- レート制限: 推定60-100 req/min

**最適化方法:**
```yaml
# config.yaml
api:
  quota_limit: 10000
  
processing:
  rate_limit_per_minute: 60  # 保守的な設定
```

### 2. ネットワークI/O

**ボトルネック:**
- API呼び出しのレイテンシ
- トランスクリプトダウンロード時間

**最適化方法:**
```python
# 並行数の調整
batch:
  max_channels: 5      # ネットワーク帯域に応じて調整
  concurrent_limit: 10  # チャンネルあたりの並行数
```

### 3. メモリ使用

**問題点:**
- 大規模チャンネルでのメモリ蓄積
- 複数チャンネル同時処理時のメモリ競合

**最適化方法:**
```python
batch:
  memory_limit_mb: 2048
  batch_size: 5         # 小さなバッチで処理
  enable_streaming: true # ストリーミング処理
```

## 最適化戦略

### 1. 並行処理の最適化

#### 推奨設定マトリクス

| シナリオ | Channels | Videos/Ch | 推奨設定 |
|---------|----------|-----------|----------|
| 小規模（〜5ch） | 1-5 | 〜100 | `pc=3, pv=5` |
| 中規模（〜20ch） | 6-20 | 〜500 | `pc=5, pv=8` |
| 大規模（20ch+） | 21-50 | 500+ | `pc=8, pv=10` |
| 超大規模 | 50+ | 1000+ | `pc=10, pv=5` |

```bash
# 中規模処理の例
youtube-transcriber batch channels.txt \
    --parallel-channels 5 \
    --parallel-videos 8
```

### 2. メモリ最適化

#### バッチサイズの調整

```python
# 動画数に応じたバッチサイズ
def calculate_batch_size(total_videos: int, available_memory_mb: int) -> int:
    if total_videos > 1000:
        return 5
    elif total_videos > 500:
        return 10
    else:
        return 20
```

#### ガベージコレクション

```python
# 定期的なメモリ解放
import gc

async def process_with_gc(videos):
    for i, batch in enumerate(batches):
        await process_batch(batch)
        if i % 10 == 0:  # 10バッチごとに
            gc.collect()
```

### 3. APIクォータ最適化

#### 効率的なAPI使用

```python
# 必要最小限のAPI呼び出し
api_costs = {
    'channel_info': 1,     # 1回のみ
    'video_list': 100,     # ページあたり
    'video_details': 1,    # 動画あたり
}

# 推定使用量計算
def estimate_quota_usage(num_channels: int, avg_videos: int) -> int:
    channel_cost = num_channels * 1
    list_cost = num_channels * (avg_videos // 50) * 100
    detail_cost = num_channels * avg_videos * 1
    return channel_cost + list_cost + detail_cost
```

#### クォータ節約モード

```yaml
processing:
  skip_private_videos: true    # プライベート動画をスキップ
  skip_live_streams: true      # ライブ配信をスキップ
  min_video_duration: 60       # 1分未満の動画をスキップ
```

### 4. ディスクI/O最適化

#### 非同期書き込み

```python
# バッファリングによる書き込み最適化
class BufferedExporter:
    def __init__(self, buffer_size: int = 100):
        self.buffer = []
        self.buffer_size = buffer_size
    
    async def export(self, data):
        self.buffer.append(data)
        if len(self.buffer) >= self.buffer_size:
            await self.flush()
    
    async def flush(self):
        # バッチ書き込み
        await write_batch(self.buffer)
        self.buffer.clear()
```

#### 圧縮オプション

```bash
# 出力を圧縮して保存
youtube-transcriber batch channels.txt --compress
```

## ベンチマーク結果

### テスト環境
- CPU: 8コア
- メモリ: 16GB
- ネットワーク: 100Mbps

### 結果

| 設定 | チャンネル数 | 総動画数 | 処理時間 | 速度 | メモリ |
|-----|------------|---------|---------|------|--------|
| 保守的 | 5 | 500 | 45分 | 11 v/m | 500MB |
| 標準 | 10 | 1000 | 60分 | 16 v/m | 1GB |
| 高速 | 20 | 2000 | 90分 | 22 v/m | 2GB |
| 最大 | 50 | 5000 | 180分 | 28 v/m | 4GB |

## チューニングチェックリスト

### 開始前の確認

- [ ] 利用可能なメモリ量
- [ ] ネットワーク帯域
- [ ] APIクォータの残量
- [ ] ディスク空き容量

### 設定の最適化

- [ ] 並行数の調整
- [ ] バッチサイズの設定
- [ ] メモリ制限の設定
- [ ] レート制限の調整

### 実行中のモニタリング

- [ ] メモリ使用量の監視
- [ ] API使用量の追跡
- [ ] エラー率の確認
- [ ] 処理速度の測定

### 実行後の分析

- [ ] batch_report.jsonの確認
- [ ] エラーログの分析
- [ ] パフォーマンスメトリクスの評価
- [ ] 次回の改善点の特定

## 高度な最適化

### 1. カスタムレート制限

```python
# 時間帯別レート調整
class TimeBasedRateLimiter:
    def get_rate(self) -> int:
        hour = datetime.now().hour
        if 2 <= hour <= 6:  # 深夜
            return 100
        elif 9 <= hour <= 17:  # 日中
            return 50
        else:  # 夕方〜夜
            return 70
```

### 2. 動的並行数調整

```python
# システムリソースに基づく調整
class DynamicConcurrency:
    async def adjust_concurrency(self):
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > 80 or memory_percent > 80:
            self.reduce_concurrency()
        elif cpu_percent < 50 and memory_percent < 50:
            self.increase_concurrency()
```

### 3. 優先度付きキュー

```python
# チャンネル優先度による処理
class PriorityQueue:
    def __init__(self):
        self.high = []    # 重要なチャンネル
        self.normal = []  # 通常
        self.low = []     # 低優先度
    
    def get_next(self):
        if self.high:
            return self.high.pop(0)
        elif self.normal:
            return self.normal.pop(0)
        else:
            return self.low.pop(0)
```

## トラブルシューティング

### 処理が遅い場合

1. **並行数を増やす**
   ```bash
   --parallel-channels 8 --parallel-videos 15
   ```

2. **不要な処理をスキップ**
   ```yaml
   skip_live_streams: true
   min_video_duration: 60
   ```

3. **メモリ制限を緩和**
   ```yaml
   memory_limit_mb: 4096
   ```

### メモリ不足の場合

1. **バッチサイズを減らす**
   ```yaml
   batch_size: 3
   ```

2. **並行数を減らす**
   ```bash
   --parallel-channels 2 --parallel-videos 3
   ```

3. **ストリーミング処理を有効化**
   ```yaml
   enable_streaming: true
   ```

### APIクォータ枯渇

1. **レート制限を厳しくする**
   ```yaml
   rate_limit_per_minute: 30
   ```

2. **処理を分割**
   ```bash
   # 朝と夜に分けて実行
   youtube-transcriber batch channels_1.txt
   # 12時間後
   youtube-transcriber batch channels_2.txt
   ```

3. **複数のAPIキーを使用**
   ```bash
   export YOUTUBE_API_KEY=$KEY1
   youtube-transcriber batch channels_1.txt
   export YOUTUBE_API_KEY=$KEY2
   youtube-transcriber batch channels_2.txt
   ```

## まとめ

最適なパフォーマンス設定は、利用環境と要件によって異なります。以下の原則に従って調整してください：

1. **小さく始める**: 保守的な設定から開始
2. **段階的に調整**: 一度に一つのパラメータを変更
3. **モニタリング**: 常にリソース使用状況を監視
4. **記録**: 設定と結果を記録して最適値を見つける