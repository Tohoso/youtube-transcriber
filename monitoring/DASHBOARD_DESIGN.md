# YouTube Transcriber 監視ダッシュボード設計書

## 📊 概要

本ドキュメントは、YouTube Transcriberの本番環境監視ダッシュボードの設計仕様を定義します。

## 🎯 ダッシュボード構成

### 1. メインダッシュボード（Overview）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    YouTube Transcriber Monitor                       │
│                                                                     │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐      │
│ │   Availability  │ │  Active Jobs    │ │  Error Rate     │      │
│ │    99.95%       │ │      42         │ │    0.12%        │      │
│ │    ▲ 0.05%      │ │    ▲ +15        │ │    ▼ -0.08%     │      │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘      │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │                    Processing Throughput                      │   │
│ │  600 ┤                                          ╭─╮          │   │
│ │  400 ┤                               ╭─────────╯  ╰──       │   │
│ │  200 ┤          ╭───────────────────╯                       │   │
│ │    0 └──────────┴───────────────────────────────────────    │   │
│ │        00:00    04:00    08:00    12:00    16:00    20:00   │   │
│ └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ ┌──────────────────────┐ ┌────────────────────────────────────┐   │
│ │   System Resources   │ │         API Quota Usage            │   │
│ │ CPU:    45% ████░   │ │  Used: 7,234 / 10,000             │   │
│ │ Memory: 62% ██████░ │ │  Rate: 120 calls/min              │   │
│ │ Disk:   34% ███░░░  │ │  Reset: 14:32:00                  │   │
│ │ Network: 12 MB/s    │ │  ████████████████░░░░ 72%         │   │
│ └──────────────────────┘ └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. 詳細パフォーマンスダッシュボード

#### 2.1 処理メトリクス

| パネル名 | メトリクス | 可視化タイプ | 更新頻度 |
|---------|-----------|-------------|----------|
| Video Processing Rate | videos_processed/min | Line Graph | 30s |
| Channel Distribution | videos by channel | Pie Chart | 60s |
| Processing Time | p50, p95, p99 latency | Multi-line | 30s |
| Queue Status | queue_size, processing, waiting | Stacked Bar | 10s |

#### 2.2 リソース使用状況

```yaml
panels:
  - name: "CPU Usage by Process"
    query: "sum by (process) (rate(process_cpu_seconds_total[5m]))"
    type: "stacked_area"
    
  - name: "Memory Allocation"
    query: "process_resident_memory_bytes / 1024 / 1024"
    type: "gauge"
    thresholds:
      - value: 1024
        color: green
      - value: 2048
        color: yellow
      - value: 3072
        color: red
        
  - name: "Goroutine Count"
    query: "go_goroutines"
    type: "line"
    alert_threshold: 1000
```

### 3. エラー分析ダッシュボード

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Error Analysis Dashboard                      │
│                                                                     │
│ ┌─────────────────────────────┐ ┌─────────────────────────────┐   │
│ │    Error Rate Timeline       │ │    Error Distribution        │   │
│ │ 10 ┤                  ╱╲    │ │                              │   │
│ │  5 ┤         ╱╲      ╱  ╲   │ │  API Error     45% ████████ │   │
│ │  0 └────────╱──╲────╱────╲  │ │  Network       25% █████    │   │
│ │     00:00  06:00  12:00  18:00│ │  Timeout       20% ████     │   │
│ └─────────────────────────────┘ │  Other         10% ██       │   │
│                                  └─────────────────────────────┘   │
│                                                                     │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │                    Recent Errors (Last 10)                   │   │
│ ├───────────────┬──────────────────────┬──────────┬──────────┤   │
│ │ Timestamp     │ Error Type           │ Channel  │ Video ID │   │
│ ├───────────────┼──────────────────────┼──────────┼──────────┤   │
│ │ 14:32:15     │ NO_TRANSCRIPT        │ @tech    │ abc123   │   │
│ │ 14:28:42     │ QUOTA_EXCEEDED       │ -        │ -        │   │
│ │ 14:15:03     │ NETWORK_TIMEOUT      │ @news    │ def456   │   │
│ └───────────────┴──────────────────────┴──────────┴──────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 4. チャンネル別ダッシュボード

```yaml
channel_dashboard:
  filters:
    - channel_name
    - date_range
    - status
    
  panels:
    - title: "Channel Processing Status"
      type: table
      columns:
        - channel
        - total_videos
        - processed
        - failed
        - success_rate
        - avg_processing_time
        - last_processed
        
    - title: "Top 10 Channels by Volume"
      type: horizontal_bar
      metric: "sum by (channel) (videos_processed)"
      
    - title: "Channel Error Rates"
      type: heatmap
      x_axis: time
      y_axis: channel
      value: error_rate
```

### 5. SLO/SLIダッシュボード

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SLO Compliance Dashboard                     │
│                                                                     │
│ ┌───────────────────────────────────────────────────────────────┐  │
│ │                    28-Day Error Budget Status                  │  │
│ │                                                                │  │
│ │  Availability SLO: 99.5%     Current: 99.87%    ✅            │  │
│ │  Error Budget: 216 min       Used: 56 min (25.9%)            │  │
│ │  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                  │  │
│ │                                                                │  │
│ │  Latency SLO: p95 < 30s      Current: 24.3s     ✅           │  │
│ │  Budget Remaining: 75%                                        │  │
│ │  ████████████████████░░░░░░░░░░░░░░░░░░░░░                   │  │
│ │                                                                │  │
│ │  Error Rate SLO: < 5%        Current: 2.1%      ✅           │  │
│ │  Budget Remaining: 58%                                        │  │
│ │  ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░                   │  │
│ └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│ ┌───────────────────────────────────────────────────────────────┐  │
│ │                    SLI Trends (7 Days)                        │  │
│ │  100% ┤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │  │
│ │   99% ┤        ╱╲                  ╱╲                         │  │
│ │   98% ┤───────╱──╲────────────────╱──╲───────────────────    │  │
│ │   97% ┤                                                       │  │
│ │        Mon    Tue    Wed    Thu    Fri    Sat    Sun         │  │
│ └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🚨 アラート統合

### アラート表示パネル

```yaml
alert_panel:
  position: top_right
  style: floating
  
  display:
    - alert_name
    - severity_icon
    - duration
    - affected_service
    
  actions:
    - acknowledge
    - silence
    - escalate
    - view_details
    
  color_coding:
    critical: "#FF0000"
    warning: "#FFA500"
    info: "#0000FF"
```

### 通知履歴パネル

| 時刻 | アラート名 | 重要度 | 状態 | 担当者 | アクション |
|------|-----------|--------|------|--------|-----------|
| 14:32 | High CPU | Warning | Active | - | [確認] |
| 13:15 | API Quota | Warning | Resolved | @john | [詳細] |
| 12:00 | Error Rate | Critical | Silenced | @jane | [履歴] |

## 📱 モバイル対応ダッシュボード

### モバイル用簡易ビュー

```
┌─────────────────────┐
│   YT Transcriber    │
│                     │
│ Status: ✅ Healthy  │
│                     │
│ Jobs:      42       │
│ Errors:    2        │
│ CPU:       45%      │
│ API:       7.2k/10k │
│                     │
│ ┌─────────────────┐ │
│ │ 📊 Throughput   │ │
│ │ ████████░░ 423  │ │
│ │ videos/hour     │ │
│ └─────────────────┘ │
│                     │
│ Recent Alerts:      │
│ ⚠️ Queue size high  │
│ ✅ Resolved 5m ago  │
│                     │
│ [Refresh] [Details] │
└─────────────────────┘
```

## 🔧 カスタマイズ機能

### ユーザー設定可能項目

1. **表示メトリクス選択**
   - 表示/非表示の切り替え
   - 順序のカスタマイズ
   - グループ化設定

2. **アラート設定**
   - 通知先のカスタマイズ
   - 閾値の調整
   - 通知頻度の設定

3. **ダッシュボードレイアウト**
   - パネルサイズ変更
   - 配置のドラッグ&ドロップ
   - テーマ選択（ライト/ダーク）

## 🔌 統合先

### Grafana設定

```json
{
  "dashboard": {
    "title": "YouTube Transcriber Production",
    "timezone": "Asia/Tokyo",
    "refresh": "30s",
    "panels": [
      {
        "id": 1,
        "title": "Processing Rate",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "rate(videos_processed_total[5m])",
            "legendFormat": "{{channel}}"
          }
        ]
      }
    ]
  }
}
```

### Datadog設定

```yaml
monitors:
  - name: "YouTube Transcriber Health"
    type: composite
    query: |
      avg(last_5m):avg:youtube.transcriber.availability{*} < 0.995
    message: |
      Availability dropped below SLO threshold
      Current: {{value}}
      Threshold: 99.5%
```

## 📊 レポート生成

### 自動レポート設定

```yaml
reports:
  daily:
    schedule: "0 9 * * *"
    recipients: ["team@company.com"]
    sections:
      - executive_summary
      - key_metrics
      - incidents
      - slo_compliance
      
  weekly:
    schedule: "0 9 * * MON"
    recipients: ["management@company.com"]
    sections:
      - performance_trends
      - capacity_planning
      - cost_analysis
      - improvement_recommendations
```

---
最終更新: 2024年12月  
監視チーム