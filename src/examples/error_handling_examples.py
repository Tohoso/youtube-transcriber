"""
エラーハンドリング統合の実装例
"""
import asyncio
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from src.models import Channel, Video, TranscriptStatus
from src.exceptions import (
    TranscriptNotFoundError,
    RateLimitError,
    NetworkError,
    YouTubeAPIError
)
from src.utils import (
    async_retry,
    API_RETRY_CONFIG,
    NETWORK_RETRY_CONFIG,
    log_error,
    error_handler,
    handle_youtube_errors,
    with_error_handling,
    CircuitBreaker,
    RateLimiter
)


# ============================================
# 例1: 基本的なリトライとエラーハンドリング
# ============================================

class TranscriptServiceExample:
    """トランスクリプトサービスのエラーハンドリング例"""
    
    def __init__(self):
        # CircuitBreakerを各外部サービス用に設定
        self.youtube_api_breaker = error_handler.get_circuit_breaker('youtube_api')
        self.transcript_api_breaker = error_handler.get_circuit_breaker('transcript_api')
        
        # RateLimiterの設定
        self.rate_limiter = RateLimiter(
            max_requests=100,
            quota_limit=10000  # YouTube API daily quota
        )
    
    @async_retry(config=API_RETRY_CONFIG)
    async def get_video_transcript(self, video_id: str) -> Optional[TranscriptData]:
        """動画の文字起こしを取得（エラーハンドリング付き）"""
        try:
            # レート制限チェック
            await self.rate_limiter.acquire(quota_cost=1)
            
            # CircuitBreaker経由でAPI呼び出し
            async with handle_youtube_errors(video_id):
                transcript = await self.transcript_api_breaker.async_call(
                    self._fetch_transcript,
                    video_id
                )
                return transcript
                
        except TranscriptNotFoundError as e:
            # 文字起こしが見つからない場合は正常なケースとして処理
            log_error(
                e,
                context={'operation': 'get_transcript', 'languages': e.available_languages},
                video_id=video_id
            )
            return None
            
        except RateLimitError as e:
            # レート制限エラーは上位に伝播させてリトライ
            logger.warning(f"Rate limit hit, will retry after {e.retry_after}s")
            raise
            
        except Exception as e:
            # その他のエラーはログして上位に伝播
            log_error(
                e,
                context={'operation': 'get_transcript', 'unexpected': True},
                video_id=video_id
            )
            raise
    
    async def _fetch_transcript(self, video_id: str):
        """実際のAPI呼び出し（ダミー実装）"""
        # 実際の実装をここに記述
        pass


# ============================================
# 例2: バッチ処理でのエラーハンドリング
# ============================================

class BatchProcessorExample:
    """バッチ処理でのエラーハンドリング例"""
    
    def __init__(self):
        self.error_handler = error_handler
        self.max_retries = 3
    
    async def process_videos_batch(
        self,
        videos: List[Video],
        concurrent_limit: int = 5
    ) -> List[Video]:
        """動画のバッチ処理（個別エラーハンドリング）"""
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def process_single_video(video: Video) -> Video:
            async with semaphore:
                for attempt in range(self.max_retries):
                    try:
                        # 動画処理
                        transcript = await self._process_video(video)
                        video.transcript_data = transcript
                        video.transcript_status = TranscriptStatus.SUCCESS
                        return video
                        
                    except TranscriptNotFoundError as e:
                        # リトライ不要なエラー
                        video.transcript_status = TranscriptStatus.NO_TRANSCRIPT
                        video.error_message = f"No transcript available: {e.available_languages}"
                        return video
                        
                    except (NetworkError, YouTubeAPIError) as e:
                        # リトライ可能なエラー
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt  # Exponential backoff
                            logger.warning(
                                f"Retrying video {video.id} after {wait_time}s "
                                f"(attempt {attempt + 1}/{self.max_retries})"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            # 最終試行失敗
                            video.transcript_status = TranscriptStatus.ERROR
                            video.error_message = str(e)
                            video.retry_count = self.max_retries
                            log_error(e, video_id=video.id)
                            return video
                    
                    except Exception as e:
                        # 予期しないエラー
                        video.transcript_status = TranscriptStatus.ERROR
                        video.error_message = f"Unexpected error: {type(e).__name__}"
                        log_error(
                            e,
                            context={'unexpected': True, 'attempt': attempt},
                            video_id=video.id
                        )
                        return video
        
        # 並列処理実行
        tasks = [process_single_video(video) for video in videos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果の処理
        processed_videos = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # gather内での例外
                videos[i].transcript_status = TranscriptStatus.ERROR
                videos[i].error_message = f"Processing failed: {result}"
                log_error(result, video_id=videos[i].id)
                processed_videos.append(videos[i])
            else:
                processed_videos.append(result)
        
        return processed_videos
    
    async def _process_video(self, video: Video):
        """実際の動画処理（ダミー実装）"""
        pass


# ============================================
# 例3: エラー集計とレポート生成
# ============================================

class ErrorReportingExample:
    """エラーレポート生成の例"""
    
    def __init__(self):
        from src.utils import ErrorAggregator, error_logger
        self.error_aggregator = ErrorAggregator()
        self.error_logger = error_logger
    
    async def process_channel_with_reporting(
        self,
        channel: Channel
    ) -> Channel:
        """チャンネル処理とエラーレポート生成"""
        start_time = datetime.now()
        
        try:
            # 処理実行
            processed_videos = await self._process_all_videos(channel.videos)
            channel.videos = processed_videos
            
            # エラー集計
            for video in processed_videos:
                if video.transcript_status == TranscriptStatus.ERROR:
                    self.error_aggregator.add_error({
                        'video_id': video.id,
                        'error_type': 'TranscriptError',
                        'error_message': video.error_message,
                        'timestamp': datetime.now().isoformat()
                    })
            
            # 処理統計
            success_count = sum(
                1 for v in processed_videos 
                if v.transcript_status == TranscriptStatus.SUCCESS
            )
            error_count = sum(
                1 for v in processed_videos 
                if v.transcript_status == TranscriptStatus.ERROR
            )
            
            # レポート生成
            if error_count > 0:
                self._generate_error_report(channel, start_time)
            
            logger.info(
                f"Channel processing completed: "
                f"{success_count} success, {error_count} errors",
                extra={
                    'channel_id': channel.id,
                    'total_videos': len(channel.videos),
                    'success_count': success_count,
                    'error_count': error_count,
                    'duration': (datetime.now() - start_time).total_seconds()
                }
            )
            
            return channel
            
        except Exception as e:
            log_error(
                e,
                context={'stage': 'channel_processing'},
                channel_id=channel.id
            )
            raise
    
    def _generate_error_report(self, channel: Channel, start_time: datetime):
        """エラーレポート生成"""
        # エラーサマリー取得
        error_summary = self.error_logger.get_error_summary()
        
        # 問題のある動画リスト
        problematic_videos = self.error_aggregator.get_problematic_videos()
        
        # エラータイムライン
        error_timeline = self.error_aggregator.get_error_timeline()
        
        # レポート作成
        report = {
            'channel_id': channel.id,
            'channel_name': channel.snippet.title,
            'processing_started': start_time.isoformat(),
            'processing_completed': datetime.now().isoformat(),
            'error_summary': error_summary,
            'problematic_videos': problematic_videos,
            'error_timeline': error_timeline,
            'top_errors': self.error_aggregator.get_top_errors()
        }
        
        # ファイル出力
        report_path = Path('output') / 'error_reports' / f'{channel.id}'
        report_path.mkdir(parents=True, exist_ok=True)
        
        report_file = report_path / f'error_report_{datetime.now():%Y%m%d_%H%M%S}.json'
        self.error_logger.export_error_report(report_file)
        
        logger.info(f"Error report generated: {report_file}")
    
    async def _process_all_videos(self, videos: List[Video]) -> List[Video]:
        """実際の動画処理（ダミー実装）"""
        pass


# ============================================
# 例4: カスタムエラーハンドリング戦略
# ============================================

class CustomErrorStrategyExample:
    """カスタムエラーハンドリング戦略の例"""
    
    def __init__(self):
        self.consecutive_errors = 0
        self.error_threshold = 5
    
    @with_error_handling(
        fallback_value=None,
        error_types=(NetworkError, YouTubeAPIError)
    )
    async def safe_api_call(self, endpoint: str, params: dict):
        """エラー時にNoneを返すAPI呼び出し"""
        # エラーが発生した場合、デコレーターがNoneを返す
        return await self._make_api_call(endpoint, params)
    
    async def adaptive_error_handling(self, video_id: str):
        """適応的エラーハンドリング（連続エラー時に戦略変更）"""
        try:
            result = await self._process_with_monitoring(video_id)
            self.consecutive_errors = 0  # 成功時はリセット
            return result
            
        except NetworkError as e:
            self.consecutive_errors += 1
            
            if self.consecutive_errors >= self.error_threshold:
                # 連続エラーが閾値を超えた場合
                logger.error(
                    f"Too many consecutive errors ({self.consecutive_errors}), "
                    "switching to degraded mode"
                )
                # より保守的な戦略に切り替え
                return await self._process_degraded_mode(video_id)
            else:
                # 通常のリトライ
                raise
    
    async def _make_api_call(self, endpoint: str, params: dict):
        """実際のAPI呼び出し（ダミー実装）"""
        pass
    
    async def _process_with_monitoring(self, video_id: str):
        """監視付き処理（ダミー実装）"""
        pass
    
    async def _process_degraded_mode(self, video_id: str):
        """劣化モードでの処理（ダミー実装）"""
        pass


# ============================================
# 使用例
# ============================================

async def main():
    """エラーハンドリングの使用例"""
    # 例1: 基本的な使用
    transcript_service = TranscriptServiceExample()
    try:
        transcript = await transcript_service.get_video_transcript("video123")
        if transcript:
            print(f"Transcript obtained: {len(transcript.full_text)} characters")
        else:
            print("No transcript available")
    except Exception as e:
        print(f"Failed to get transcript: {e}")
    
    # 例2: バッチ処理
    batch_processor = BatchProcessorExample()
    videos = [Video(id=f"video{i}", title=f"Video {i}") for i in range(10)]
    processed = await batch_processor.process_videos_batch(videos)
    
    success_count = sum(1 for v in processed if v.transcript_status == TranscriptStatus.SUCCESS)
    print(f"Batch processing: {success_count}/{len(videos)} successful")
    
    # 例3: エラーレポート
    reporter = ErrorReportingExample()
    channel = Channel(id="channel123", snippet=ChannelSnippet(title="Test Channel"))
    channel.videos = processed
    await reporter.process_channel_with_reporting(channel)


if __name__ == "__main__":
    asyncio.run(main())