# YouTube Transcriber ユーザーガイド

## 🎯 はじめに

YouTube Transcriber は、YouTubeチャンネルの動画から字幕（トランスクリプト）を一括でダウンロードするツールです。このガイドでは、初めての方でも簡単に使えるよう、ステップバイステップで説明します。

## 📋 目次

1. [クイックスタート](#クイックスタート)
2. [インストール](#インストール)
3. [初期設定](#初期設定)
4. [基本的な使い方](#基本的な使い方)
5. [複数チャンネルの処理](#複数チャンネルの処理)
6. [高度な機能](#高度な機能)
7. [トラブルシューティング](#トラブルシューティング)
8. [よくある質問](#よくある質問)

## 🚀 クイックスタート

### 3分で始める YouTube Transcriber

```bash
# 1. インストール
pip install youtube-transcriber

# 2. APIキーの設定
youtube-transcriber config --api-key YOUR_API_KEY

# 3. 実行
youtube-transcriber @mkbhd
```

これだけで、MKBHDチャンネルの全動画の字幕がダウンロードされます！

## 💿 インストール

### 必要な環境
- Python 3.9以上
- インターネット接続
- YouTube Data API キー（無料）

### インストール手順

#### 方法1: pip を使用（推奨）
```bash
pip install youtube-transcriber
```

#### 方法2: ソースからインストール
```bash
git clone https://github.com/yourusername/youtube-transcriber.git
cd youtube-transcriber
pip install .
```

### インストールの確認
```bash
youtube-transcriber --version
```

## ⚙️ 初期設定

### YouTube API キーの取得

1. [Google Cloud Console](https://console.cloud.google.com) にアクセス
2. 新しいプロジェクトを作成
3. 「APIとサービス」→「ライブラリ」を選択
4. 「YouTube Data API v3」を検索して有効化
5. 「認証情報」→「認証情報を作成」→「APIキー」
6. 生成されたAPIキーをコピー

### APIキーの設定

```bash
youtube-transcriber config --api-key YOUR_API_KEY_HERE
```

✅ 設定完了！これで使用準備が整いました。

## 📖 基本的な使い方

### 1. 単一チャンネルの処理

#### チャンネルの指定方法

```bash
# @ハンドルを使用
youtube-transcriber @mkbhd

# チャンネルURLを使用
youtube-transcriber https://youtube.com/@LinusTechTips

# チャンネルIDを使用
youtube-transcriber UCBJycsmduvYEL83R_U4JriQ
```

### 2. 基本オプション

```bash
# 出力ディレクトリを指定
youtube-transcriber @mkbhd --output-dir ./transcripts

# 言語を指定（日本語）
youtube-transcriber @mkbhd --language ja

# 出力形式を指定
youtube-transcriber @mkbhd --format markdown
```

### 3. プログレス表示の見方

処理中は以下のような表示が出ます：

```
Channel: Marques Brownlee
Total Videos: 1,234
━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45% 00:05:23

✅ Video Title 1 (1,234 words)
✅ Video Title 2 (2,345 words)
⏳ Video Title 3 (処理中...)
```

## 🎛️ 複数チャンネルの処理

### 対話型モード（初心者におすすめ）

```bash
youtube-transcriber interactive
```

#### ステップ1: チャンネルの追加
```
YouTube Transcriber - Multi-Channel Processing

What would you like to do? add

Add Channels
Enter channel URLs, @handles, or IDs (one per line)
Press Enter twice to finish

[1] @mkbhd
✅ Added: @mkbhd
[2] @LinusTechTips
✅ Added: @LinusTechTips
[3] (Enterを2回押して終了)
```

#### ステップ2: チャンネルの確認と処理開始
```
Channel Selection (2 total)
┌───┬──────────────────┬──────────┬─────────────┬────────┐
│ # │ Channel          │ Status   │ Subscribers │ Videos │
├───┼──────────────────┼──────────┼─────────────┼────────┤
│ 1 │ @mkbhd          │ ✅ Valid │ 15.2M       │ 1,500  │
│ 2 │ @LinusTechTips  │ ✅ Valid │ 14.8M       │ 5,000  │
└───┴──────────────────┴──────────┴─────────────┴────────┘

What would you like to do? proceed
```

### バッチファイルモード（大量処理向け）

#### channels.txt を作成
```
# Tech YouTubers
@mkbhd
@LinusTechTips
@UnboxTherapy

# News Channels
@verge
@techcrunch
```

#### 実行
```bash
youtube-transcriber batch channels.txt --parallel-channels 3
```

### フィルタリング機能

```bash
# 大規模チャンネルのみ（登録者100万人以上）
youtube-transcriber batch channels.txt --filter large

# 最近アクティブなチャンネルのみ
youtube-transcriber batch channels.txt --filter recent
```

## 🔧 高度な機能

### 1. 日付範囲の指定

```bash
# 2024年の動画のみ
youtube-transcriber @mkbhd --date-from 2024-01-01 --date-to 2024-12-31

# 最近30日間の動画のみ
youtube-transcriber @mkbhd --recent-days 30
```

### 2. 並列処理の調整

```bash
# チャンネルの並列処理数（デフォルト: 3）
youtube-transcriber batch channels.txt --parallel-channels 5

# 動画の並列処理数（デフォルト: 5）
youtube-transcriber @mkbhd --parallel-videos 10
```

### 3. 出力形式のカスタマイズ

```bash
# 利用可能な形式: txt, json, csv, markdown
youtube-transcriber @mkbhd --format json

# 複数形式で出力
youtube-transcriber @mkbhd --format json --format markdown
```

### 4. ドライラン（実際にダウンロードせずに確認）

```bash
youtube-transcriber @mkbhd --dry-run
```

## 🔍 トラブルシューティング

### よくあるエラーと対処法

#### 1. API クォータ超過エラー
```
エラー: API使用量の上限に達しました
```
**対処法**:
- 24時間待つ
- 別のAPIキーを使用: `youtube-transcriber config --api-key NEW_KEY`
- 並列数を減らす: `--parallel-videos 1`

#### 2. ネットワークエラー
```
エラー: インターネット接続を確認してください
```
**対処法**:
- インターネット接続を確認
- プロキシ設定を確認
- `--timeout 60` でタイムアウトを延長

#### 3. チャンネルが見つからない
```
エラー: チャンネルが見つかりません
```
**対処法**:
- URLや@ハンドルのスペルを確認
- チャンネルが公開されているか確認
- チャンネルIDを使用してみる

### ログファイルの確認

詳細なエラー情報はログファイルに記録されます：
```bash
# ログファイルの場所
cat ~/.youtube-transcriber/logs/app.log

# リアルタイムでログを確認
tail -f ~/.youtube-transcriber/logs/app.log
```

## ❓ よくある質問

### Q: 無料で使えますか？
A: はい、YouTube Data API の無料枠内（1日10,000クォータ）で使用できます。通常の使用では十分な量です。

### Q: どのくらいの速度で処理できますか？
A: 
- 1チャンネル（100動画）: 約5-10分
- 10チャンネル（1,000動画）: 約30-60分
- ネットワーク速度とAPIレート制限に依存します

### Q: プライベート動画も取得できますか？
A: いいえ、公開されている動画のみ取得可能です。

### Q: 字幕がない動画はどうなりますか？
A: 自動生成字幕があれば取得します。まったく字幕がない場合はスキップされます。

### Q: 出力ファイルはどこに保存されますか？
A: デフォルトでは `./output/チャンネル名/` に保存されます。`--output-dir` で変更可能です。

### Q: 処理を中断したらどうなりますか？
A: 現在処理中の動画は失われますが、完了済みの動画は保存されています。同じコマンドを再実行すると、既存のファイルはスキップされます。

## 💡 使用のコツ

### 1. 効率的な処理
- 夜間に大量処理を実行
- `--skip-existing` で重複を回避
- 定期的な差分取得には `--recent-days` を活用

### 2. ストレージ管理
- JSON形式は検索に便利
- Markdown形式は読みやすい
- CSV形式はExcel分析に最適

### 3. APIクォータ管理
- 1日のクォータ: 10,000ユニット
- 1チャンネル取得: 約100ユニット
- 1動画取得: 約3ユニット

## 🆘 サポート

### 問題が解決しない場合

1. [GitHubイシュー](https://github.com/yourusername/youtube-transcriber/issues)で報告
2. [ディスカッション](https://github.com/yourusername/youtube-transcriber/discussions)で質問
3. [ドキュメント](https://docs.youtube-transcriber.com)を確認

### コミュニティ
- Discord: [参加リンク]
- Reddit: r/YouTubeTranscriber
- Twitter: @yt_transcriber

---

このガイドは継続的に更新されています。最新版は[オンラインドキュメント](https://docs.youtube-transcriber.com)をご確認ください。

Happy Transcribing! 🎉