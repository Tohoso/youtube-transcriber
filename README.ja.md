# YouTube Transcriber

YouTubeチャンネル内の全動画から文字起こし（字幕）を抽出するCLIアプリケーション

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md)
[![テストカバレッジ](https://img.shields.io/badge/coverage-61.2%25-green.svg)](tests/)
[![品質スコア](https://img.shields.io/badge/quality-A-brightgreen.svg)](docs/)

## 📋 概要

YouTube Transcriber は、指定したYouTubeチャンネルの全動画から文字起こし（字幕）を自動的に抽出し、様々な形式で保存するコマンドラインツールです。

### ✨ 主な機能

- 🚀 **高速並列処理** - 複数の動画を同時に処理して時間を短縮
- 🎯 **複数チャンネル対応** - 最大1000チャンネルまでバッチ処理可能
- 📊 **多様な出力形式** - TXT、JSON、CSV、Markdown形式に対応
- 🔄 **自動リトライ機能** - ネットワークエラー時に自動的に再試行
- 📈 **進捗表示** - リアルタイムの処理状況と統計情報
- 🛡️ **堅牢なエラー処理** - 様々なエラーシナリオに対応
- 🌐 **多言語対応** - 任意の言語の字幕を抽出可能
- 📅 **日付フィルタリング** - 期間を指定して動画を絞り込み
- 💾 **進捗保存機能** - 中断した処理を再開可能

## 🚀 クイックスタート

### 前提条件

- Python 3.9以降
- YouTube Data API v3のAPIキー（[取得方法](#youtube-api-キーの取得方法)）

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/Tohoso/youtube-transcriber.git
cd youtube-transcriber

# 依存関係のインストール
pip install -e .
```

### 基本的な使い方

```bash
# 環境変数でAPIキーを設定
export YOUTUBE_API_KEY="your_api_key_here"

# チャンネルの全動画から文字起こしを取得
youtube-transcriber https://www.youtube.com/@channel_name

# または、チャンネルハンドルを直接指定
youtube-transcriber @channel_name
```

## 📖 詳細な使い方

### コマンドラインオプション

```bash
youtube-transcriber [チャンネル入力] [オプション]
```

#### 引数

- `channel_input` - YouTubeチャンネルのURL、ID、または@ハンドル

#### オプション

| オプション | 短縮形 | 説明 | デフォルト |
|----------|--------|------|-----------|
| `--output-dir` | `-o` | 出力ディレクトリ | `./output` |
| `--format` | `-f` | 出力形式 (txt/json/csv/md) | `txt` |
| `--language` | `-l` | 字幕言語コード | `ja` |
| `--concurrent` | `-c` | 並列ダウンロード数 | `5` |
| `--date-from` | - | 開始日 (YYYY-MM-DD) | - |
| `--date-to` | - | 終了日 (YYYY-MM-DD) | - |
| `--config` | - | 設定ファイルパス | - |
| `--dry-run` | - | テスト実行（ダウンロードなし） | `False` |

### 使用例

#### 1. 出力形式を指定

```bash
# JSON形式で出力
youtube-transcriber @channel_name --format json

# Markdown形式で特定のディレクトリに保存
youtube-transcriber @channel_name --format md --output-dir ./transcripts
```

#### 2. 言語を指定

```bash
# 英語字幕を取得
youtube-transcriber @channel_name --language en

# 韓国語字幕を取得
youtube-transcriber @channel_name --language ko
```

#### 3. 期間を指定

```bash
# 2024年の動画のみ
youtube-transcriber @channel_name --date-from 2024-01-01 --date-to 2024-12-31

# 最近1ヶ月の動画
youtube-transcriber @channel_name --date-from 2024-11-01
```

#### 4. 並列処理数を調整

```bash
# 10並列で高速処理
youtube-transcriber @channel_name --concurrent 10

# 1つずつ順番に処理（安定重視）
youtube-transcriber @channel_name --concurrent 1
```

### 設定ファイルの使用

設定ファイル（YAML形式）を作成して、複雑な設定を管理できます。

#### サンプル設定ファイルの生成

```bash
youtube-transcriber config --generate
```

#### config.yaml の例

```yaml
api:
  youtube_api_key: ${YOUTUBE_API_KEY}
  quota_limit: 10000

processing:
  concurrent_limit: 5
  retry_attempts: 3
  retry_delay: 1.0
  rate_limit_per_minute: 60
  timeout_seconds: 30
  skip_private_videos: true
  skip_live_streams: true

output:
  default_format: txt
  output_directory: ./output
  filename_template: "{date}_{title}_{video_id}"
  include_metadata: true
  include_timestamps: false
  max_filename_length: 100

logging:
  level: INFO
  log_file: logs/app.log
  max_file_size: "500 MB"
  retention_days: 10
  enable_json_logging: false
```

設定ファイルを使用した実行：

```bash
youtube-transcriber @channel_name --config config.yaml
```

## 📁 出力ファイル構造

```
output/
└── channel_name/
    ├── channel_info.json          # チャンネル情報
    ├── processing_stats.json      # 処理統計
    ├── videos/
    │   ├── 2024-01-01_video_title_abc123.txt
    │   ├── 2024-01-02_another_video_def456.txt
    │   └── ...
    └── metadata/
        ├── abc123.json           # 動画メタデータ
        ├── def456.json
        └── ...
```

## 🔧 高度な機能

### 処理統計

アプリケーションは詳細な処理統計を提供します：

- 総動画数と処理済み動画数
- 成功率と失敗率
- エラー種別ごとの分析
- 推定残り時間
- 処理速度（動画/時間）

### エラーハンドリング

以下のようなエラーに自動的に対応します：

- ネットワークエラー → 自動リトライ
- レート制限 → 自動待機
- 字幕なし → スキップして続行
- API制限 → 適切なエラーメッセージ

### 出力形式の詳細

#### TXT形式
シンプルなテキスト形式。読みやすく、他のツールでの処理も簡単。

#### JSON形式
完全な構造化データ。タイムスタンプ、メタデータを含む。

```json
{
  "video_id": "abc123",
  "title": "動画タイトル",
  "language": "ja",
  "segments": [
    {
      "text": "こんにちは",
      "start_time": 0.0,
      "duration": 2.5
    }
  ]
}
```

#### CSV形式
スプレッドシートでの分析に最適。

#### Markdown形式
ドキュメント作成やブログ投稿に便利。

## 🔑 YouTube API キーの取得方法

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. 「APIとサービス」→「ライブラリ」から「YouTube Data API v3」を検索
4. APIを有効化
5. 「認証情報」→「認証情報を作成」→「APIキー」
6. 作成されたAPIキーをコピー

### APIキーの設定方法

#### 方法1: 環境変数（推奨）

```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

#### 方法2: .envファイル

プロジェクトルートに`.env`ファイルを作成：

```
YOUTUBE_API_KEY=your_api_key_here
```

#### 方法3: 設定ファイル

`config.yaml`に直接記載（セキュリティに注意）

## 🧪 開発者向け情報

### 開発環境のセットアップ

```bash
# 開発用依存関係のインストール
pip install -e ".[dev]"

# テストの実行
pytest tests/

# カバレッジレポート
pytest --cov=src tests/

# コードフォーマット
black src/ tests/

# リンター
ruff check src/ tests/
```

### アーキテクチャ

```
src/
├── cli/           # CLIインターフェース
├── models/        # Pydanticデータモデル
├── services/      # ビジネスロジック
├── repositories/  # 外部API連携
└── utils/         # ユーティリティ
```

### 貢献方法

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🙏 謝辞

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 強力な動画ダウンロードライブラリ
- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) - YouTubeトランスクリプトAPI
- [Typer](https://typer.tiangolo.com/) - 優れたCLIフレームワーク
- [Rich](https://rich.readthedocs.io/) - 美しいターミナル出力

## 📞 サポート

- バグ報告: [Issues](https://github.com/Tohoso/youtube-transcriber/issues)
- 機能リクエスト: [Discussions](https://github.com/Tohoso/youtube-transcriber/discussions)
- 質問: [Discussions](https://github.com/Tohoso/youtube-transcriber/discussions)

## 🚨 免責事項

このツールは教育・研究目的で作成されています。YouTubeの利用規約を遵守し、著作権を尊重してご使用ください。大量のAPIリクエストは制限される可能性があります。