# YouTube Transcriber トラブルシューティングガイド

## 📋 目次

1. [クイック診断フローチャート](#クイック診断フローチャート)
2. [よくある問題と解決方法](#よくある問題と解決方法)
3. [エラーメッセージ一覧](#エラーメッセージ一覧)
4. [ログの読み方と分析方法](#ログの読み方と分析方法)
5. [パフォーマンス問題の診断](#パフォーマンス問題の診断)
6. [ネットワーク関連の問題](#ネットワーク関連の問題)
7. [API関連の問題](#api関連の問題)
8. [高度なトラブルシューティング](#高度なトラブルシューティング)
9. [問題報告の方法](#問題報告の方法)

## クイック診断フローチャート

```mermaid
graph TD
    A[問題発生] --> B{動作しない?}
    B -->|Yes| C{エラー表示?}
    B -->|No| D{遅い?}
    
    C -->|Yes| E[エラーメッセージ確認]
    C -->|No| F[ログ確認]
    
    D -->|Yes| G[パフォーマンス診断]
    D -->|No| H[その他の問題]
    
    E --> I{APIエラー?}
    I -->|Yes| J[APIセクション参照]
    I -->|No| K[エラー一覧参照]
    
    F --> L{プロセス起動?}
    L -->|No| M[環境設定確認]
    L -->|Yes| N[詳細ログ分析]
    
    G --> O{ネットワーク?}
    O -->|Yes| P[ネットワーク診断]
    O -->|No| Q[リソース確認]
```

## よくある問題と解決方法

### 1. 起動・初期化の問題

#### 問題: アプリケーションが起動しない

**症状**:
- コマンド実行後、何も表示されない
- すぐにプロンプトに戻る

**解決方法**:

```bash
# 1. Python環境確認
python --version  # Python 3.9以上が必要

# 2. 依存関係確認
pip list | grep youtube-transcriber

# 3. 再インストール
pip uninstall youtube-transcriber -y
pip install youtube-transcriber

# 4. 詳細ログで起動
youtube-transcriber --log-level DEBUG transcribe @channel
```

#### 問題: "Module not found" エラー

**症状**:
```
ModuleNotFoundError: No module named 'src'
```

**解決方法**:

```bash
# 1. 正しいディレクトリから実行
cd /path/to/youtube-transcriber
python -m src.cli.main

# 2. PYTHONPATH設定
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 3. 開発モードでインストール
pip install -e .
```

### 2. API関連の問題

#### 問題: APIキーが認識されない

**症状**:
```
Error: YouTube API key not found
```

**解決方法**:

```bash
# 1. 環境変数確認
echo $YOUTUBE_API_KEY

# 2. 環境変数設定
export YOUTUBE_API_KEY="your_api_key_here"

# 3. .envファイル作成
echo "YOUTUBE_API_KEY=your_api_key_here" > .env

# 4. 設定ファイル確認
cat config.yaml | grep youtube_api_key
```

#### 問題: APIクォータ超過

**症状**:
```
Error: quotaExceeded - The request cannot be completed because you have exceeded your quota
```

**解決方法**:

```bash
# 1. 現在のクォータ使用状況確認
youtube-transcriber quota --check

# 2. 処理を制限
youtube-transcriber @channel --concurrent 1 --rate-limit 10

# 3. クォータリセット時間確認
youtube-transcriber quota --reset-time

# 4. バックアップAPIキー使用
export YOUTUBE_API_KEY=$BACKUP_API_KEY
```

### 3. 処理エラー

#### 問題: 文字起こしが取得できない

**症状**:
```
Error: No transcript available for video XYZ
```

**解決方法**:

```bash
# 1. 動画の字幕設定確認
youtube-transcriber check-video <video_url>

# 2. 別の言語で試行
youtube-transcriber @channel --language en

# 3. 自動生成字幕を許可
youtube-transcriber @channel --auto-captions

# 4. スキップして続行
youtube-transcriber @channel --skip-unavailable
```

#### 問題: チャンネルが見つからない

**症状**:
```
Error: Channel not found
```

**解決方法**:

```bash
# 1. URL形式確認
# 正しい: https://youtube.com/@channelname
# 正しい: https://youtube.com/channel/UCxxxxxx

# 2. チャンネル存在確認
youtube-transcriber validate-channel <url>

# 3. 別の形式で試行
youtube-transcriber "channel name"  # 検索
youtube-transcriber @handle         # ハンドル
youtube-transcriber UCxxxxxx        # ID
```

## エラーメッセージ一覧

### APIエラー

| エラーコード | メッセージ | 原因 | 解決方法 |
|-------------|-----------|------|----------|
| 401 | Invalid API key | APIキー無効 | キー再生成・確認 |
| 403 | Access forbidden | 権限不足 | API有効化確認 |
| 404 | Channel/Video not found | リソース不在 | URL確認 |
| 429 | Too many requests | レート制限 | 待機・制限調整 |
| 500 | Internal server error | YouTube側エラー | 時間を置いて再試行 |

### アプリケーションエラー

| エラー | 説明 | 対処法 |
|--------|------|--------|
| ConfigurationError | 設定ファイルエラー | config.yaml確認 |
| NetworkError | ネットワーク接続失敗 | 接続確認・プロキシ設定 |
| FileSystemError | ファイル書き込み失敗 | 権限・容量確認 |
| ParseError | データ解析エラー | ログ確認・再試行 |
| TimeoutError | タイムアウト | タイムアウト値増加 |

### 処理エラー

```python
# エラーコードと対処法の対応表
ERROR_SOLUTIONS = {
    "NO_TRANSCRIPT": {
        "description": "文字起こし利用不可",
        "solutions": [
            "別の言語を試す: --language en",
            "自動字幕を有効化: --auto-captions",
            "動画をスキップ: --skip-unavailable"
        ]
    },
    "CHANNEL_PRIVATE": {
        "description": "非公開チャンネル",
        "solutions": [
            "チャンネル所有者に公開を依頼",
            "別のチャンネルを指定"
        ]
    },
    "VIDEO_UNAVAILABLE": {
        "description": "動画が利用不可",
        "solutions": [
            "動画の公開状態確認",
            "地域制限の確認",
            "削除済みの可能性"
        ]
    }
}
```

## ログの読み方と分析方法

### ログレベルの理解

| レベル | 意味 | 例 |
|--------|------|-----|
| DEBUG | 詳細情報 | API呼び出しの詳細 |
| INFO | 通常動作 | 処理進捗 |
| WARNING | 警告 | リトライ発生 |
| ERROR | エラー | 処理失敗 |
| CRITICAL | 致命的 | アプリ停止 |

### ログ分析コマンド

```bash
# エラーログ抽出
grep -E "ERROR|CRITICAL" logs/app.log | tail -50

# 特定チャンネルのログ
grep "@channelname" logs/app.log

# 時間範囲指定
awk '/2024-12-20 14:00/,/2024-12-20 15:00/' logs/app.log

# エラー頻度分析
grep ERROR logs/app.log | cut -d' ' -f5- | sort | uniq -c | sort -rn

# API呼び出し分析
grep "API call" logs/app.log | grep -o "endpoint:[^ ]*" | sort | uniq -c
```

### ログ可視化

```python
# scripts/analyze_logs.py
import re
from collections import Counter
import matplotlib.pyplot as plt

def analyze_error_patterns(log_file):
    """エラーパターンを分析して可視化"""
    errors = []
    with open(log_file, 'r') as f:
        for line in f:
            if 'ERROR' in line:
                # エラータイプ抽出
                match = re.search(r'ERROR.*?:\s*(\w+)', line)
                if match:
                    errors.append(match.group(1))
    
    # 集計と可視化
    error_counts = Counter(errors)
    plt.bar(error_counts.keys(), error_counts.values())
    plt.xlabel('Error Type')
    plt.ylabel('Count')
    plt.title('Error Distribution')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('error_analysis.png')
```

## パフォーマンス問題の診断

### 処理速度が遅い場合

#### 1. システムリソース確認

```bash
# CPU使用率
top -p $(pgrep -f youtube-transcriber)

# メモリ使用量
ps aux | grep youtube-transcriber

# ディスクI/O
iotop -p $(pgrep -f youtube-transcriber)

# ネットワーク帯域
nethogs
```

#### 2. ボトルネック特定

```bash
# プロファイリング実行
python -m cProfile -o profile.stats src/cli/main.py @channel

# 結果分析
python -m pstats profile.stats
> sort cumtime
> stats 20
```

#### 3. パフォーマンス改善策

| 問題 | 診断方法 | 改善策 |
|------|----------|--------|
| API待機時間長い | ログのAPI response time | 並列数増加 |
| メモリ不足 | `free -h`で確認 | バッチサイズ削減 |
| ディスクI/O遅い | `iostat -x 1` | SSDへ移行/出力圧縮 |
| CPU使用率高い | `top`で確認 | 処理最適化 |

### メモリリーク診断

```python
# メモリ使用量監視
import tracemalloc
import psutil
import os

def monitor_memory():
    """メモリ使用量を監視"""
    process = psutil.Process(os.getpid())
    
    tracemalloc.start()
    
    # 処理実行
    # ...
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")
    
    # トップ10のメモリ使用箇所
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    for stat in top_stats[:10]:
        print(stat)
```

## ネットワーク関連の問題

### 接続エラーの診断

```bash
# 1. 基本的な接続確認
ping youtube.com
nslookup youtube.com

# 2. HTTPSアクセス確認
curl -I https://www.youtube.com

# 3. プロキシ設定確認
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 4. SSL証明書確認
openssl s_client -connect youtube.com:443 -servername youtube.com
```

### プロキシ経由での使用

```bash
# プロキシ設定
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# 認証付きプロキシ
export HTTPS_PROXY=http://username:password@proxy.company.com:8080

# プロキシ除外設定
export NO_PROXY=localhost,127.0.0.1
```

### タイムアウト問題

```yaml
# config.yaml でタイムアウト調整
network:
  connection_timeout: 30  # 接続タイムアウト（秒）
  read_timeout: 60       # 読み取りタイムアウト（秒）
  retry_count: 3         # リトライ回数
  retry_delay: 5         # リトライ間隔（秒）
```

## API関連の問題

### APIキー診断スクリプト

```python
# scripts/diagnose_api.py
import os
import requests
from datetime import datetime

def diagnose_api_key():
    """APIキーの状態を診断"""
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key:
        print("❌ APIキーが設定されていません")
        return
    
    # APIキーの形式確認
    if not api_key.startswith('AIza'):
        print("⚠️ APIキーの形式が正しくない可能性があります")
    
    # API呼び出しテスト
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        'part': 'snippet',
        'id': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',  # Google Developers
        'key': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("✅ APIキーは有効です")
            
            # クォータ情報取得（ヘッダーから推測）
            remaining = response.headers.get('X-RateLimit-Remaining', 'Unknown')
            print(f"📊 残りクォータ: {remaining}")
        else:
            print(f"❌ APIエラー: {response.status_code}")
            print(f"詳細: {response.json()}")
    except Exception as e:
        print(f"❌ 接続エラー: {e}")

if __name__ == "__main__":
    diagnose_api_key()
```

### クォータ管理

```bash
# クォータ使用状況監視
youtube-transcriber quota --monitor

# クォータ使用履歴
youtube-transcriber quota --history --days 7

# クォータ予測
youtube-transcriber quota --estimate @channel
```

## 高度なトラブルシューティング

### デバッグモード実行

```bash
# 完全デバッグモード
youtube-transcriber --debug --verbose transcribe @channel

# 特定モジュールのデバッグ
YOUTUBE_TRANSCRIBER_DEBUG=api,network youtube-transcriber @channel

# ドライラン（実際の処理なし）
youtube-transcriber --dry-run @channel
```

### トレースバック分析

```python
# カスタムエラーハンドラー
import sys
import traceback

def detailed_error_handler(exc_type, exc_value, exc_traceback):
    """詳細なエラー情報を出力"""
    print("="*60)
    print("詳細エラー情報")
    print("="*60)
    
    # 基本情報
    print(f"エラータイプ: {exc_type.__name__}")
    print(f"エラーメッセージ: {exc_value}")
    
    # スタックトレース
    print("\nスタックトレース:")
    for frame in traceback.extract_tb(exc_traceback):
        print(f"  File: {frame.filename}")
        print(f"  Function: {frame.name}")
        print(f"  Line {frame.lineno}: {frame.line}")
    
    # ローカル変数
    print("\nローカル変数:")
    tb_frame = exc_traceback.tb_frame
    for var_name, var_value in tb_frame.f_locals.items():
        print(f"  {var_name} = {repr(var_value)[:100]}")

sys.excepthook = detailed_error_handler
```

### メトリクス収集

```bash
# パフォーマンスメトリクス収集
youtube-transcriber metrics --collect --output metrics.json

# メトリクス分析
youtube-transcriber metrics --analyze metrics.json

# ベンチマーク実行
youtube-transcriber benchmark --iterations 10
```

## 問題報告の方法

### 効果的なバグレポート

**必須情報**:

1. **環境情報**
```bash
youtube-transcriber --version
python --version
pip freeze | grep -E "(youtube|aiohttp|requests)"
uname -a  # OS情報
```

2. **再現手順**
```markdown
1. コマンド: `youtube-transcriber @channel --language ja`
2. 期待される結果: 文字起こしダウンロード
3. 実際の結果: エラー発生
```

3. **エラーログ**
```bash
# 最小限の再現ケース
youtube-transcriber --debug <command> 2>&1 | tee error.log
```

4. **設定ファイル** (機密情報除去)
```bash
cat config.yaml | sed 's/api_key.*/api_key: <REDACTED>/'
```

### 問題報告テンプレート

```markdown
## 問題の概要
[簡潔な説明]

## 環境
- OS: [例: macOS 13.0]
- Python: [例: 3.9.10]
- youtube-transcriber: [例: 1.0.0]

## 再現手順
1. [手順1]
2. [手順2]
3. [手順3]

## 期待される動作
[説明]

## 実際の動作
[説明]

## エラーメッセージ
```
[エラー出力をペースト]
```

## 追加情報
[その他関連情報]
```

### サポートチャンネル

| チャンネル | 用途 | レスポンス時間 |
|-----------|------|----------------|
| GitHub Issues | バグ報告・機能要望 | 1-3営業日 |
| Discussion | 使い方相談 | コミュニティ依存 |
| Email | 緊急サポート | 24時間以内 |

---
最終更新: 2024年12月
サポートチーム