# 複数チャンネル処理 使用ガイド

## 🚀 クイックスタート

### 1. 基本的な使い方

```bash
# チャンネルリストファイルから処理
youtube-transcriber batch channels.txt

# 対話型モードで処理
youtube-transcriber interactive
```

### 2. チャンネルリストファイルの作成

`channels.txt`:
```
# YouTubeチャンネルのURL、ID、または@ハンドル（1行に1つ）
@mkbhd
https://www.youtube.com/@LinusTechTips
UCXuqSBlHAE6Xw-yeJA0Tunw
@UnboxTherapy

# コメント行は # で始まります
# 空行は無視されます
```

## 📋 詳細な使用方法

### バッチ処理コマンド

#### 基本構文
```bash
youtube-transcriber batch <channels-file> [OPTIONS]
```

#### オプション一覧

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|------------|
| `--output-dir` | `-o` | 出力ディレクトリ | `./output` |
| `--parallel-channels` | `-pc` | 同時処理チャンネル数 | `3` |
| `--parallel-videos` | `-pv` | チャンネルあたりの同時処理動画数 | `5` |
| `--language` | `-l` | トランスクリプト言語 | `ja` |
| `--format` | `-f` | 出力形式（txt/json/csv/md） | `txt` |
| `--date-from` | - | 開始日（YYYY-MM-DD） | - |
| `--date-to` | - | 終了日（YYYY-MM-DD） | - |
| `--filter` | - | チャンネルフィルター | - |
| `--sort` | - | ソート順 | - |
| `--resume` | `-r` | 前回の続きから再開 | `False` |

#### 使用例

**1. 出力先を指定して処理**
```bash
youtube-transcriber batch channels.txt --output-dir ~/transcripts
```

**2. 並行処理数を増やして高速化**
```bash
youtube-transcriber batch channels.txt --parallel-channels 5 --parallel-videos 10
```

**3. 英語字幕を取得**
```bash
youtube-transcriber batch channels.txt --language en --format json
```

**4. 期間を指定して処理**
```bash
youtube-transcriber batch channels.txt \
    --date-from 2024-01-01 \
    --date-to 2024-12-31
```

**5. 大規模チャンネルのみ処理**
```bash
youtube-transcriber batch channels.txt --filter large --sort subscribers
```

**6. 中断した処理を再開**
```bash
youtube-transcriber batch channels.txt --resume
```

### 対話型モード

```bash
youtube-transcriber interactive
```

#### 機能

1. **チャンネル追加**
   - URL、@ハンドル、チャンネルIDを入力
   - リアルタイムバリデーション
   - 複数チャンネルの一括追加

2. **チャンネル管理**
   - 追加したチャンネルの確認
   - フィルタリング（規模別）
   - ソート（名前、登録者数、動画数）

3. **処理実行**
   - 設定確認
   - 処理開始
   - リアルタイム進捗表示

#### 操作フロー

```
1. YouTube Transcriber - Multi-Channel Mode
   ↓
2. チャンネル追加（Enter×2で終了）
   ↓
3. メインメニュー
   - add: チャンネル追加
   - filter: フィルター適用
   - sort: ソート
   - validate: 検証
   - proceed: 処理開始
   - quit: 終了
   ↓
4. 処理実行
```

## 📊 出力構造

### ディレクトリ構成

```
output/
├── @mkbhd/
│   ├── channel_info.json
│   ├── processing_summary.json
│   ├── videos/
│   │   ├── 2024-01-01_video_title_abc123.txt
│   │   └── ...
│   └── metadata/
│       ├── abc123.json
│       └── ...
├── @LinusTechTips/
│   └── ...
└── batch_report.json
```

### batch_report.json

全体の処理結果サマリー：

```json
{
  "total_channels": 3,
  "successful_channels": ["@mkbhd", "@LinusTechTips"],
  "failed_channels": {
    "@example": "Channel not found"
  },
  "partial_channels": {
    "@UnboxTherapy": {
      "processed": 95,
      "successful": 90,
      "failed": 5,
      "total": 100
    }
  },
  "total_videos_processed": 285,
  "total_videos_successful": 270,
  "total_videos_failed": 15,
  "overall_success_rate": 94.7,
  "quota_usage": {
    "used": 4500,
    "limit": 10000,
    "percentage": 45.0
  }
}
```

## 🎯 使用シナリオ

### シナリオ1: 複数の技術系チャンネルを一括処理

```bash
# channels_tech.txt を作成
echo "@mkbhd
@LinusTechTips
@UnboxTherapy
@MKBHD
@iJustine" > channels_tech.txt

# 英語字幕をJSON形式で取得
youtube-transcriber batch channels_tech.txt \
    --language en \
    --format json \
    --output-dir ./tech_transcripts \
    --parallel-channels 5
```

### シナリオ2: 大規模チャンネルの最新動画のみ処理

```bash
# 2024年の動画のみ、大規模チャンネルを優先
youtube-transcriber batch all_channels.txt \
    --date-from 2024-01-01 \
    --filter large \
    --sort subscribers \
    --parallel-channels 3
```

### シナリオ3: 定期的な更新処理

```bash
# 前回の続きから処理（cronジョブに最適）
youtube-transcriber batch channels.txt --resume

# 実行例（crontab）
0 2 * * * cd /path/to/project && youtube-transcriber batch channels.txt --resume
```

## ⚙️ パフォーマンスチューニング

### 並行処理の最適化

**推奨設定:**

| チャンネル数 | parallel-channels | parallel-videos | 想定時間 |
|------------|------------------|-----------------|----------|
| 1-5 | 3 | 5 | 標準 |
| 6-20 | 5 | 8 | やや長い |
| 21-50 | 8 | 10 | 長い |
| 50+ | 10 | 10 | 非常に長い |

**注意事項:**
- APIクォータ（日次10,000）を考慮
- メモリ使用量は並行数に比例
- ネットワーク帯域も考慮

### メモリ管理

大規模処理時の推奨事項：

1. **設定ファイルでメモリ制限を調整**
```yaml
batch:
  memory_limit_mb: 2048  # 2GB
  enable_streaming: true
```

2. **バッチサイズの調整**
```yaml
batch:
  batch_size: 5  # 少なめに設定
```

## 🚨 トラブルシューティング

### よくある問題

#### 1. APIクォータ超過
```
Error: Quota exceeded. Daily limit reached.
```
**対策:**
- 翌日まで待つ
- 別のAPIキーを使用
- parallel設定を下げる

#### 2. メモリ不足
```
Warning: Memory limit approaching
```
**対策:**
- parallel設定を下げる
- メモリ制限を上げる
- バッチサイズを小さくする

#### 3. タイムアウト
```
Error: Channel processing timeout
```
**対策:**
- channel_timeout_minutesを増やす
- 動画数の多いチャンネルは個別処理

#### 4. 権限エラー
```
Error: Access denied to this resource
```
**対策:**
- プライベート動画はスキップされる
- 地域制限のある動画も同様

### ログの確認

```bash
# アプリケーションログ
tail -f logs/app.log

# 特定チャンネルのエラーを確認
grep "@channelname" logs/app.log | grep ERROR
```

### 進捗の確認

```bash
# 進捗ファイルの内容を確認
cat .progress.json | jq .

# 処理済みチャンネル数を確認
cat .progress.json | jq '.processed_channels | length'
```

## 💡 ベストプラクティス

1. **チャンネルリストの管理**
   - カテゴリ別にファイルを分ける
   - コメントで説明を追加
   - 定期的に更新

2. **処理の分割**
   - 大量のチャンネルは複数回に分けて処理
   - 重要度の高いチャンネルを優先

3. **エラー対策**
   - `--resume`オプションを活用
   - ログを定期的に確認
   - 失敗したチャンネルは個別に再処理

4. **リソース管理**
   - 夜間など負荷の低い時間に実行
   - 適切な並行数の設定
   - ディスク容量の事前確認

## 🔗 関連ドキュメント

- [MULTI_CHANNEL_API.md](./MULTI_CHANNEL_API.md) - API仕様
- [README.md](../README.md) - プロジェクト概要
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - テストガイド