# YouTube Transcriber デプロイメントガイド

## 目次
1. [概要](#概要)
2. [前提条件](#前提条件)
3. [デプロイメント方法](#デプロイメント方法)
4. [設定](#設定)
5. [監視とアラート](#監視とアラート)
6. [トラブルシューティング](#トラブルシューティング)

## 概要

YouTube Transcriberは以下の3つの方法でデプロイ可能です：
- Docker Compose（開発・小規模環境）
- Kubernetes（本番環境）
- 直接実行（開発環境）

## 前提条件

### 必須要件
- Docker 20.10+
- Docker Compose 2.0+（Docker Compose利用時）
- Kubernetes 1.24+（Kubernetes利用時）
- YouTube Data API v3のAPIキー

### 推奨要件
- 2 CPU cores
- 2GB RAM
- 10GB ストレージ

## デプロイメント方法

### 1. Docker Composeでのデプロイ

#### 開発環境
```bash
# 環境変数の設定
cp .env.example .env.local
# .env.localを編集してYOUTUBE_API_KEYを設定

# 起動
docker-compose -f docker-compose.dev.yml up -d

# ログ確認
docker-compose -f docker-compose.dev.yml logs -f
```

#### 本番環境
```bash
# 環境変数の設定
cp .env.example .env.production
# .env.productionを編集

# 起動
docker-compose up -d

# ヘルスチェック
curl http://localhost:8080/health
```

### 2. Kubernetesでのデプロイ

```bash
# Namespace作成
kubectl create namespace youtube-transcriber

# Secretの作成
kubectl create secret generic youtube-transcriber-secrets \
  --from-literal=youtube-api-key="YOUR_API_KEY" \
  -n youtube-transcriber

# ConfigMapとDeploymentの適用
kubectl apply -f deployment/k8s/ -n youtube-transcriber

# 状態確認
kubectl get pods -n youtube-transcriber
kubectl get svc -n youtube-transcriber
```

### 3. 自動デプロイメント

```bash
# 本番環境へのデプロイ
./deployment/deploy.sh \
  --environment production \
  --target kubernetes \
  --build \
  --push

# Docker Composeでのデプロイ
./deployment/deploy.sh \
  --environment production \
  --target docker-compose
```

## 設定

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| YOUTUBE_API_KEY | YouTube Data API v3のキー | 必須 |
| CONCURRENT_LIMIT | 同時処理数 | 10 |
| RATE_LIMIT_PER_MINUTE | 分あたりのAPI呼び出し数 | 60 |
| OUTPUT_DIRECTORY | 出力ディレクトリ | /app/output |
| MEMORY_LIMIT_MB | メモリ制限（MB） | 2048 |

### 設定ファイル

`config.yaml`で詳細な設定が可能：

```yaml
api:
  quota_limit: 10000

processing:
  concurrent_limit: 10
  skip_private_videos: true
  skip_live_streams: true

output:
  default_format: txt
  include_metadata: true

batch:
  max_channels: 5
  save_progress: true
```

## 監視とアラート

### Prometheusメトリクス

メトリクスエンドポイント: `http://localhost:9090/metrics`

主要メトリクス：
- `youtube_transcriber_requests_total` - リクエスト数
- `youtube_transcriber_memory_usage_bytes` - メモリ使用量
- `youtube_transcriber_cpu_usage_percent` - CPU使用率
- `youtube_transcriber_api_quota_used` - API使用量

### Grafanaダッシュボード

Grafanaは`http://localhost:3000`でアクセス可能（デフォルト認証: admin/admin）

### アラート設定

以下のアラートが設定済み：
- 高メモリ使用率（>1.5GB）
- 高CPU使用率（>80%）
- サービスダウン
- 高エラー率（>10%）
- APIクォータ枯渇（>80%）

## トラブルシューティング

### ヘルスチェックが失敗する

```bash
# ヘルスエンドポイントの確認
curl -v http://localhost:8080/health

# ログの確認
docker logs youtube-transcriber

# Kubernetesの場合
kubectl logs -n youtube-transcriber deployment/youtube-transcriber
```

### APIキーエラー

```bash
# 環境変数の確認
docker exec youtube-transcriber env | grep YOUTUBE_API_KEY

# Kubernetesの場合
kubectl get secret youtube-transcriber-secrets -n youtube-transcriber -o yaml
```

### メモリ不足

```yaml
# docker-compose.ymlで制限を増やす
services:
  youtube-transcriber:
    deploy:
      resources:
        limits:
          memory: 4G

# Kubernetesの場合、deployment.yamlを編集
resources:
  limits:
    memory: "4Gi"
```

### ディスク容量不足

```bash
# 使用状況確認
docker exec youtube-transcriber df -h

# 古い出力ファイルの削除
docker exec youtube-transcriber find /app/output -mtime +30 -delete
```

## CI/CDパイプライン

### GitHub Actions

プッシュ時に自動的に以下が実行されます：
1. コード品質チェック（Black, Flake8, MyPy）
2. セキュリティスキャン（Bandit, Safety）
3. テスト実行（60%カバレッジ必須）
4. Dockerイメージビルド
5. 脆弱性スキャン（Trivy）
6. デプロイ（環境による）

### 手動リリース

```bash
# GitHub Actionsからリリース実行
# version: 1.2.0, release_type: minor
```

## セキュリティ考慮事項

1. **APIキー管理**
   - 環境変数またはSecretで管理
   - コードにハードコードしない

2. **ネットワークセキュリティ**
   - 必要なポートのみ公開
   - TLS/SSL終端の設定推奨

3. **リソース制限**
   - CPU/メモリ制限の設定
   - ディスククォータの設定

4. **監査ログ**
   - すべてのAPIアクセスをログ記録
   - 定期的なログレビュー

## メンテナンス

### バックアップ

```bash
# 出力データのバックアップ
docker exec youtube-transcriber tar -czf /tmp/backup.tar.gz /app/output
docker cp youtube-transcriber:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
```

### アップデート

```bash
# 最新イメージの取得
docker-compose pull

# ローリングアップデート
docker-compose up -d --no-deps --build youtube-transcriber

# Kubernetesの場合
kubectl set image deployment/youtube-transcriber \
  youtube-transcriber=youtube-transcriber:new-version \
  -n youtube-transcriber
```

### ログローテーション

```yaml
# docker-compose.ymlに追加
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "10"
```

---

問題が解決しない場合は、[GitHubのIssue](https://github.com/youtube-transcriber/issues)でお問い合わせください。