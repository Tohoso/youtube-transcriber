# YouTube Transcriber 技術調査レポート - バックエンド・API関連

## エグゼクティブサマリー

YouTube Transcriberのバックエンド・API関連の技術調査を実施した結果、以下の重要な問題点と改善提案を報告します。

### 主要な発見事項

1. **複数チャンネル処理機能の欠如**
   - 現在のシステムは単一チャンネルのみを処理する設計
   - CLIインターフェースが複数チャンネルの入力を受け付けない

2. **エラーハンドリングの問題**
   - Video オブジェクトの属性アクセスエラー
   - 型チェックエラー（NoneType比較）
   - トランスクリプトAPI呼び出しの失敗

3. **API利用制限への対応**
   - レート制限機能は実装済み（60リクエスト/分）
   - クォータ管理機能が設定はあるが未使用

## 詳細分析

### 1. エラーログ分析

#### 1.1 主要なエラーパターン

**属性エラー（AttributeError）**
```
- 'DisplayManager' object has no attribute 'show_status'
- 'Video' object has no attribute 'is_private' 
- "Video" object has no field "transcript"
```

**型比較エラー**
```
'<' not supported between instances of 'int' and 'NoneType'
```

**トランスクリプト取得エラー**
```
Could not retrieve a transcript for the video
```

#### 1.2 エラー発生頻度
- トランスクリプト取得失敗: 高頻度（複数の動画で発生）
- 属性エラー: 中頻度（コードの不整合により発生）
- 型エラー: 低頻度（特定条件下で発生）

### 2. アーキテクチャ分析

#### 2.1 システム構成
```
src/
├── application/     # オーケストレーター層
├── cli/            # コマンドラインインターフェース
├── models/         # データモデル（Pydantic）
├── repositories/   # 外部API連携層
├── services/       # ビジネスロジック層
└── utils/          # ユーティリティ
```

#### 2.2 データフロー
1. CLI → Orchestrator → Services → Repositories
2. 非同期処理（asyncio）による並列実行
3. セマフォによる同時実行数制御（デフォルト5）

### 3. YouTube API統合

#### 3.1 実装済み機能
- YouTube Data API v3 統合
- チャンネル情報取得
- 動画リスト取得（ページネーション対応）
- 動画詳細情報取得

#### 3.2 レート制限対応
```python
# RateLimiter実装
- TokenBucket方式: 60リクエスト/分
- SlidingWindow方式: 時間窓での制限
- 自動待機機能
```

#### 3.3 エラーハンドリング
- リトライ機能（@async_retry デコレーター）
- 最大3回のリトライ
- 1秒の遅延

### 4. 複数チャンネル処理の現状

#### 4.1 現在の制限
- CLIは単一の`channel_input`引数のみ受付
- Orchestratorは`process_channel`メソッドで単一チャンネル処理
- バッチ処理機能なし

#### 4.2 必要な改修点
1. CLI引数の拡張（複数チャンネル対応）
2. Orchestratorへのバッチ処理機能追加
3. 進捗管理の拡張
4. エラーハンドリングの強化

### 5. API利用制限への対応状況

#### 5.1 実装済み機能
- **レート制限**: 60リクエスト/分（設定可能）
- **リトライ機能**: 失敗時の自動再試行
- **非同期処理**: 効率的なAPI呼び出し

#### 5.2 未実装/改善が必要な機能
- **クォータ管理**: 設定はあるが実際の追跡なし
- **エラー時の待機**: 429エラー時の適切な待機時間
- **バックオフ戦略**: 段階的な待機時間増加

## 改善提案

### 1. 緊急対応（バグ修正）

#### 1.1 属性エラーの修正
```python
# Video モデルの属性名統一
- transcript → transcript_data
- is_private プロパティの実装確認
```

#### 1.2 型エラーの修正
```python
# None チェックの追加
if value is not None and value < threshold:
    # 処理
```

### 2. 複数チャンネル処理の実装

#### 2.1 CLI拡張案
```bash
# 複数チャンネル対応
youtube-transcriber @channel1 @channel2 @channel3
# またはファイル入力
youtube-transcriber --channels-file channels.txt
```

#### 2.2 Orchestrator拡張案
```python
async def process_channels(
    self,
    channel_inputs: List[str],
    **kwargs
) -> List[Channel]:
    """複数チャンネルの処理"""
    results = []
    for channel in channel_inputs:
        try:
            result = await self.process_channel(channel, **kwargs)
            results.append(result)
        except Exception as e:
            logger.error(f"Channel {channel} failed: {e}")
    return results
```

### 3. API制限対応の強化

#### 3.1 クォータトラッキング
```python
class QuotaTracker:
    def __init__(self, daily_limit: int):
        self.limit = daily_limit
        self.used = 0
        self.reset_time = self._next_reset()
    
    async def track(self, cost: int):
        if self.used + cost > self.limit:
            raise QuotaExceededException()
        self.used += cost
```

#### 3.2 適応的レート制限
```python
class AdaptiveRateLimiter:
    def adjust_rate(self, error_rate: float):
        if error_rate > 0.1:
            self.rate *= 0.8  # 20%減速
        elif error_rate < 0.01:
            self.rate *= 1.1  # 10%加速
```

## 結論

YouTube Transcriberは基本的な機能は実装されているが、複数チャンネル処理とエラーハンドリングに改善の余地があります。特に以下の点が重要です：

1. **属性エラーの即時修正**が必要
2. **複数チャンネル処理**の実装で利便性向上
3. **API制限対応**の強化で安定性向上

これらの改善により、より堅牢で使いやすいツールになることが期待されます。

## 付録：エラー発生箇所

- `src/cli/display.py`: show_status メソッドの実装確認
- `src/models/video.py`: transcript_data フィールドの確認
- `src/application/orchestrator.py`: 型チェックの追加