# UI-バックエンド統合テストシナリオ

## 1. 結合テスト準備チェックリスト

### A. UI側の準備状況 ✅
- [x] MultiChannelInterface の実装完了
- [x] UIBackendBridge の実装完了
- [x] リアルタイム進捗表示の実装
- [x] エラーハンドリングUIの実装
- [x] バッチ処理結果表示の実装

### B. バックエンド側の確認事項（dev2）
- [ ] BatchChannelOrchestrator の実装確認
- [ ] MultiChannelProcessor の実装確認
- [ ] UIBackendBridge インターフェースの実装確認
- [ ] 非同期イベント発行の実装確認

### C. 統合ポイント
- [ ] UIBackendBridge のメソッドシグネチャ一致確認
- [ ] イベントデータ構造の整合性確認
- [ ] エラー型とリカバリアクションの一致確認

## 2. エンドツーエンドユーザーフロー

### シナリオ1: 対話型チャンネル選択フロー
```
1. ユーザーが `youtube-transcriber interactive` を実行
2. Welcome画面が表示される
3. メインメニューから "add" を選択
4. チャンネルURLを3つ入力
   - @mkbhd
   - @LinusTechTips
   - 無効なURL（エラーテスト用）
5. "validate" で一括検証
   - 2つ成功、1つ失敗の表示確認
6. "filter" で large channels のみ表示
7. "proceed" で処理開始
8. リアルタイム進捗表示
   - ヘッダーの統計情報更新
   - プログレスバーのアニメーション
   - 個別チャンネルの進捗表示
9. 処理完了後の結果表示
   - 成功/失敗のサマリー
   - エラー詳細
   - エクスポート結果
```

### シナリオ2: バッチファイル処理フロー
```
1. channels.txt を作成（5チャンネル）
2. `youtube-transcriber batch channels.txt --parallel-channels 2` を実行
3. 初期化表示の確認
4. ライブ進捗表示の開始
5. 並列処理の視覚的確認（2チャンネル同時）
6. エラー発生時のリカバリ表示
7. 完了後の統計表示
```

### シナリオ3: エラーハンドリングフロー
```
1. APIクォータ超過シミュレーション
   - エラー表示の確認
   - RETRY_LATER アクションの動作
2. ネットワークエラーシミュレーション
   - 自動リトライの表示
   - リトライカウントの表示
3. 無効なチャンネルエラー
   - SKIP アクションの動作
   - エラーサマリーへの反映
```

## 3. UIパフォーマンステスト

### A. 大量チャンネル処理（50チャンネル）
- UI更新のレスポンシブ性
- メモリ使用量の監視
- CPU使用率の確認

### B. 高頻度更新シナリオ
- 10チャンネル × 100動画の並列処理
- 更新頻度: 100ms
- スムーズな表示更新の確認

### C. エラー大量発生シナリオ
- 50%のエラー率でのテスト
- エラー表示のパフォーマンス
- UI の応答性維持

## 4. ユーザビリティチェックリスト

### A. 視覚的フィードバック
- [ ] 状態変化が明確に分かる（色、アイコン）
- [ ] プログレスバーが滑らかに更新
- [ ] エラーが目立つように表示
- [ ] 成功/失敗が一目で分かる

### B. 情報の可読性
- [ ] 長いチャンネル名の適切な省略
- [ ] 数値のフォーマット（1.2M, 45.3%）
- [ ] 時間表示の人間的表現（2h 15m）
- [ ] テーブルの整列と間隔

### C. 操作性
- [ ] メニュー選択の直感性
- [ ] エラー時の次のアクション明確性
- [ ] キャンセル/中断の方法
- [ ] ヘルプ情報のアクセシビリティ

### D. エラー処理
- [ ] エラーメッセージの分かりやすさ
- [ ] リカバリ方法の提示
- [ ] 部分的成功の適切な表現
- [ ] ログファイルへの誘導

## 5. 統合時の注意点

### A. 非同期処理
- UIブロッキングの回避
- イベントループの適切な管理
- タスクキャンセレーションの処理

### B. データ整合性
- チャンネル状態の同期
- 進捗情報の正確性
- エラー情報の完全性

### C. リソース管理
- メモリリークの防止
- ファイルハンドルの適切なクローズ
- 非同期タスクのクリーンアップ

## 6. デバッグ用ツール

### A. ログ出力
```python
# UIイベントログ
logger.debug(f"UI Event: {event_type} for channel {channel_id}")

# パフォーマンスログ
logger.info(f"Update batch processed: {len(updates)} updates in {elapsed}ms")

# エラーログ
logger.error(f"UI update failed: {error}", exc_info=True)
```

### B. デバッグモード
```bash
# 詳細ログ付き実行
YOUTUBE_TRANSCRIBER_DEBUG=true youtube-transcriber interactive

# UI更新の可視化
YOUTUBE_TRANSCRIBER_UI_DEBUG=true youtube-transcriber batch channels.txt
```

### C. パフォーマンスプロファイリング
```python
# cProfile を使用したプロファイリング
python -m cProfile -o ui_profile.stats src/cli/main.py interactive
```

## 7. 期待される結果

### A. 機能面
- すべてのUIコンポーネントが正しく動作
- バックエンドとの通信が正常
- エラー処理が適切に機能

### B. パフォーマンス面
- 50チャンネルまでスムーズに処理
- UI更新による遅延なし
- メモリ使用量が適切な範囲内

### C. ユーザビリティ面
- 直感的な操作フロー
- 明確なフィードバック
- エラー時の適切なガイダンス

## 8. 修正が必要な場合の対応

### A. UI側の修正
1. `multi_channel_interface.py` の該当メソッド修正
2. `ui_backend_bridge.py` のイベントハンドラ調整
3. 表示フォーマットの最適化

### B. 統合部分の修正
1. データ構造の調整
2. イベントタイミングの同期
3. エラー型のマッピング

### C. パフォーマンス改善
1. 更新頻度の調整
2. バッチサイズの最適化
3. 不要な再描画の削減