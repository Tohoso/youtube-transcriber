# YouTube Transcriber アップグレードガイド

## 📋 概要

本ガイドは、YouTube Transcriber v1.xからv2.0へのアップグレード手順を説明します。

## 🚀 v2.0の主な変更点

### 新機能
- **複数チャンネル同時処理**: 最大1000チャンネルの並列処理
- **インタラクティブモード**: 直感的なチャンネル選択UI
- **進捗保存機能**: 中断からの自動再開
- **高度なエラーハンドリング**: 部分的な失敗の許容

### 改善点
- パフォーマンス20%向上
- メモリ使用量18%削減
- API効率12.5%改善

## 📝 アップグレード手順

### 1. 事前準備

#### バックアップ作成
```bash
# 設定ファイルのバックアップ
cp config.yaml config.yaml.backup
cp -r output/ output_backup/

# 現在のバージョン確認
youtube-transcriber --version
```

#### 依存関係確認
```bash
# Python バージョン確認（3.9以上必要）
python --version

# 現在のパッケージリスト保存
pip freeze > requirements_old.txt
```

### 2. アップグレード実施

#### パッケージ更新
```bash
# pipを使用する場合
pip install --upgrade youtube-transcriber==2.0.0

# poetryを使用する場合
poetry add youtube-transcriber@2.0.0

# ソースからインストールする場合
git clone https://github.com/yourusername/youtube-transcriber.git
cd youtube-transcriber
git checkout v2.0.0
pip install -e .
```

#### 依存関係の更新
```bash
# 新しい依存関係のインストール
pip install -r requirements.txt

# 不要なパッケージの削除
pip autoremove
```

### 3. 設定ファイルの更新

#### config.yaml の変更

**v1.x 形式:**
```yaml
api:
  youtube_api_key: ${YOUTUBE_API_KEY}
  
processing:
  concurrent_limit: 5
  
output:
  format: txt
  directory: ./output
```

**v2.0 形式:**
```yaml
api:
  youtube_api_key: ${YOUTUBE_API_KEY}
  quota_limit: 10000
  
processing:
  concurrent_limit: 5
  retry_attempts: 3
  rate_limit_per_minute: 60
  
output:
  default_format: txt
  output_directory: ./output
  
# 新規追加セクション
batch:
  max_channels: 5
  channel_delay: 5
  save_progress: true
  progress_file: .progress.json
  
monitoring:
  enabled: true
  log_level: INFO
```

#### 自動マイグレーション
```bash
# 設定ファイルの自動更新
youtube-transcriber config --migrate

# 更新内容の確認
youtube-transcriber config --show
```

### 4. CLIコマンドの変更

#### 非推奨コマンド

| 旧コマンド | 新コマンド | 説明 |
|-----------|-----------|------|
| `--format` | `--output-format` | 出力形式指定 |
| `--parallel` | `--concurrent` | 並列数指定 |
| `transcribe-channel` | `transcribe` | コマンド統一 |

#### 新規コマンド

```bash
# バッチ処理（新規）
youtube-transcriber batch channels.txt

# インタラクティブモード（新規）
youtube-transcriber interactive

# 進捗モニタリング（新規）
youtube-transcriber monitor

# クォータ確認（新規）
youtube-transcriber quota --check
```

### 5. APIの変更

#### レスポンス形式の変更

**v1.x:**
```json
{
  "video_id": "abc123",
  "transcript": "..."
}
```

**v2.0:**
```json
{
  "status": "success",
  "data": {
    "video_id": "abc123",
    "transcript": "...",
    "metadata": {
      "processing_time": 2.1,
      "language": "ja"
    }
  }
}
```

#### 新規エンドポイント

```python
# Python クライアントの例
from youtube_transcriber import Client

client = Client(api_key="your_key")

# 新規: バッチ処理
result = client.process_batch(
    channels=["@channel1", "@channel2"],
    parallel_channels=2
)

# 新規: 進捗取得
progress = client.get_progress(batch_id="xyz789")
```

### 6. 出力構造の変更

#### ディレクトリ構成

**v1.x:**
```
output/
├── channel_name_transcripts.txt
├── channel_name_metadata.json
└── logs/
```

**v2.0:**
```
output/
├── channel_name/
│   ├── channel_info.json
│   ├── processing_stats.json
│   ├── videos/
│   │   ├── 2024-01-01_video_title_abc123.txt
│   │   └── 2024-01-02_another_video_def456.txt
│   └── metadata/
│       ├── abc123.json
│       └── def456.json
└── batch_report.json
```

### 7. 互換性の確認

#### 後方互換性

✅ **保持される機能:**
- 単一チャンネル処理
- 基本的なCLIオプション
- 環境変数設定
- 出力フォーマット

⚠️ **変更が必要な機能:**
- カスタムスクリプトでのAPI呼び出し
- 出力ファイルパスの参照
- エラーハンドリングロジック

#### 互換性確認スクリプト
```bash
#!/bin/bash
# check_compatibility.sh

echo "Checking YouTube Transcriber v2.0 compatibility..."

# バージョン確認
version=$(youtube-transcriber --version)
echo "Current version: $version"

# 設定ファイル確認
if youtube-transcriber config --validate; then
    echo "✅ Configuration valid"
else
    echo "❌ Configuration needs update"
    youtube-transcriber config --migrate
fi

# 基本動作確認
if youtube-transcriber test --quick; then
    echo "✅ Basic functionality working"
else
    echo "❌ Basic test failed"
fi

# API接続確認
if youtube-transcriber quota --check > /dev/null; then
    echo "✅ API connection successful"
else
    echo "❌ API connection failed"
fi
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. ImportError発生
```bash
# 解決方法
pip uninstall youtube-transcriber
pip install youtube-transcriber==2.0.0 --no-cache-dir
```

#### 2. 設定ファイルエラー
```bash
# 設定リセット
youtube-transcriber config --reset
youtube-transcriber config --generate
```

#### 3. 出力ファイルが見つからない
```python
# 移行スクリプト
import os
import shutil

def migrate_output_structure():
    """v1.x の出力を v2.0 構造に移行"""
    old_output = "./output_backup"
    new_output = "./output"
    
    for file in os.listdir(old_output):
        if file.endswith("_transcripts.txt"):
            channel = file.replace("_transcripts.txt", "")
            channel_dir = os.path.join(new_output, channel, "videos")
            os.makedirs(channel_dir, exist_ok=True)
            shutil.copy(
                os.path.join(old_output, file),
                os.path.join(channel_dir, file)
            )
```

## 📅 移行スケジュール推奨

### Phase 1: テスト環境（1週間）
1. テスト環境でv2.0インストール
2. 基本機能の動作確認
3. カスタムスクリプトの修正

### Phase 2: 段階的移行（2週間）
1. 一部のチャンネルでv2.0使用
2. パフォーマンス比較
3. 問題点の洗い出し

### Phase 3: 完全移行（1週間）
1. 全環境をv2.0に更新
2. v1.xの非活性化
3. 最終確認

## 🆘 サポート

### リソース
- [公式ドキュメント](https://docs.youtube-transcriber.com/v2.0)
- [移行FAQ](https://github.com/yourusername/youtube-transcriber/wiki/Migration-FAQ)
- [コミュニティフォーラム](https://github.com/yourusername/youtube-transcriber/discussions)

### 問い合わせ
- GitHub Issues: バグ報告・機能要望
- Email: support@youtube-transcriber.com
- Slack: #youtube-transcriber-support

## ✅ アップグレード完了確認

```bash
# 最終確認コマンド
youtube-transcriber verify --post-upgrade

# 期待される出力
YouTube Transcriber v2.0.0
✅ Configuration: Valid
✅ Dependencies: Satisfied
✅ API Connection: Active
✅ Test Suite: Passed
✅ Ready for production use!
```

---
最終更新: 2024年12月
YouTube Transcriber Team