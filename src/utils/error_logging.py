"""
Structured error logging system with categorization and aggregation
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from collections import defaultdict
from loguru import logger
from enum import Enum

from src.exceptions import (
    TranscriberError,
    APIError,
    TranscriptNotFoundError,
    ConfigurationError,
    RateLimitError,
    NetworkError,
    YouTubeAPIError,
    ValidationError,
    FileWriteError,
    ProcessingError
)


class ErrorCategory(str, Enum):
    """Error categorization for logging and analysis"""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    TRANSCRIPT_ERROR = "transcript_error"
    CONFIG_ERROR = "config_error"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    PROCESSING_ERROR = "processing_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorLogger:
    """Structured error logging with categorization and aggregation"""
    
    def __init__(
        self,
        log_dir: Path = Path("logs"),
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        json_logs: bool = True,
        max_file_size: str = "100 MB",
        retention_days: int = 30
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.json_logs = json_logs
        
        # Error statistics
        self.error_stats = defaultdict(lambda: {
            'count': 0,
            'first_seen': None,
            'last_seen': None,
            'examples': []
        })
        
        # Configure loguru
        self._configure_logger(max_file_size, retention_days)
    
    def _configure_logger(self, max_file_size: str, retention_days: int):
        """Configure loguru logger with structured output"""
        # Remove default handler
        logger.remove()
        
        # Add console handler
        if self.enable_console_logging:
            logger.add(
                sys.stderr,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                       "<level>{level: <8}</level> | "
                       "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                       "<level>{message}</level>",
                level="INFO"
            )
        
        # Add file handlers
        if self.enable_file_logging:
            # General error log
            logger.add(
                self.log_dir / "errors.log",
                rotation=max_file_size,
                retention=f"{retention_days} days",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
                level="ERROR",
                backtrace=True,
                diagnose=True
            )
            
            # Structured JSON log for analysis
            if self.json_logs:
                logger.add(
                    self.log_dir / "errors.json",
                    rotation=max_file_size,
                    retention=f"{retention_days} days",
                    format="{message}",
                    level="ERROR",
                    serialize=True
                )
            
            # Category-specific logs
            for category in ErrorCategory:
                logger.add(
                    self.log_dir / f"{category.value}.log",
                    rotation="50 MB",
                    retention=f"{retention_days} days",
                    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                    level="ERROR",
                    filter=lambda record, cat=category: record["extra"].get("error_category") == cat.value
                )
    
    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        video_id: Optional[str] = None,
        channel_id: Optional[str] = None
    ):
        """Log an error with structured information"""
        error_category = self._categorize_error(error)
        error_data = self._build_error_data(error, context, video_id, channel_id)
        
        # Update statistics
        self._update_error_stats(error_category, error_data)
        
        # Log with appropriate level and context
        log_level = self._determine_log_level(error)
        
        logger.bind(
            error_category=error_category.value,
            error_type=type(error).__name__,
            video_id=video_id,
            channel_id=channel_id,
            **error_data
        ).log(
            log_level,
            f"{error_category.value}: {str(error)}"
        )
        
        # Log to specific handler if TranscriberError
        if isinstance(error, TranscriberError):
            self._log_structured_error(error, error_category, error_data)
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error for proper handling and logging"""
        if isinstance(error, (APIError, YouTubeAPIError)):
            return ErrorCategory.API_ERROR
        elif isinstance(error, NetworkError):
            return ErrorCategory.NETWORK_ERROR
        elif isinstance(error, TranscriptNotFoundError):
            return ErrorCategory.TRANSCRIPT_ERROR
        elif isinstance(error, ConfigurationError):
            return ErrorCategory.CONFIG_ERROR
        elif isinstance(error, ValidationError):
            return ErrorCategory.VALIDATION_ERROR
        elif isinstance(error, FileWriteError):
            return ErrorCategory.FILE_ERROR
        elif isinstance(error, ProcessingError):
            return ErrorCategory.PROCESSING_ERROR
        else:
            return ErrorCategory.UNKNOWN_ERROR
    
    def _determine_log_level(self, error: Exception) -> str:
        """Determine appropriate log level based on error type"""
        if isinstance(error, (ConfigurationError, ValidationError)):
            return "ERROR"
        elif isinstance(error, RateLimitError):
            return "WARNING"
        elif isinstance(error, TranscriptNotFoundError):
            return "INFO"
        elif isinstance(error, (NetworkError, APIError)):
            return "ERROR"
        else:
            return "ERROR"
    
    def _build_error_data(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        video_id: Optional[str] = None,
        channel_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build structured error data for logging"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'video_id': video_id,
            'channel_id': channel_id,
            'context': context or {}
        }
        
        # Add TranscriberError specific data
        if isinstance(error, TranscriberError):
            error_data.update({
                'error_code': error.error_code,
                'details': error.details,
                'retry_after': error.retry_after
            })
        
        # Add traceback for non-TranscriberError exceptions
        if not isinstance(error, TranscriberError):
            import traceback
            error_data['traceback'] = traceback.format_exc()
        
        return error_data
    
    def _log_structured_error(
        self,
        error: TranscriberError,
        category: ErrorCategory,
        error_data: Dict[str, Any]
    ):
        """Log structured error for analysis"""
        structured_log = {
            'category': category.value,
            'error': error.to_dict(),
            'metadata': error_data
        }
        
        logger.bind(structured=True).error(json.dumps(structured_log))
    
    def _update_error_stats(self, category: ErrorCategory, error_data: Dict[str, Any]):
        """Update error statistics"""
        stats = self.error_stats[category]
        stats['count'] += 1
        
        now = datetime.now()
        if stats['first_seen'] is None:
            stats['first_seen'] = now
        stats['last_seen'] = now
        
        # Keep last 10 examples
        if len(stats['examples']) < 10:
            stats['examples'].append({
                'timestamp': error_data['timestamp'],
                'message': error_data['error_message'],
                'video_id': error_data.get('video_id'),
                'channel_id': error_data.get('channel_id')
            })
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors"""
        summary = {
            'total_errors': sum(stats['count'] for stats in self.error_stats.values()),
            'categories': {}
        }
        
        for category, stats in self.error_stats.items():
            summary['categories'][category.value] = {
                'count': stats['count'],
                'first_seen': stats['first_seen'].isoformat() if stats['first_seen'] else None,
                'last_seen': stats['last_seen'].isoformat() if stats['last_seen'] else None,
                'recent_examples': stats['examples'][-5:]  # Last 5 examples
            }
        
        return summary
    
    def export_error_report(self, output_path: Path):
        """Export detailed error report"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_error_summary(),
            'detailed_stats': {}
        }
        
        for category, stats in self.error_stats.items():
            report['detailed_stats'][category.value] = {
                'count': stats['count'],
                'first_seen': stats['first_seen'].isoformat() if stats['first_seen'] else None,
                'last_seen': stats['last_seen'].isoformat() if stats['last_seen'] else None,
                'examples': stats['examples']
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Error report exported to {output_path}")


class ErrorAggregator:
    """Aggregate and analyze errors for patterns"""
    
    def __init__(self):
        self.errors_by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.errors_by_video: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.errors_by_time: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def add_error(self, error_data: Dict[str, Any]):
        """Add error to aggregator"""
        error_type = error_data.get('error_type', 'Unknown')
        video_id = error_data.get('video_id')
        timestamp = error_data.get('timestamp', datetime.now().isoformat())
        
        # Group by error type
        self.errors_by_type[error_type].append(error_data)
        
        # Group by video if available
        if video_id:
            self.errors_by_video[video_id].append(error_data)
        
        # Group by hour
        hour_key = timestamp[:13]  # YYYY-MM-DDTHH
        self.errors_by_time[hour_key].append(error_data)
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common error types"""
        error_counts = [
            {
                'error_type': error_type,
                'count': len(errors),
                'percentage': len(errors) / sum(len(e) for e in self.errors_by_type.values()) * 100
            }
            for error_type, errors in self.errors_by_type.items()
        ]
        
        return sorted(error_counts, key=lambda x: x['count'], reverse=True)[:limit]
    
    def get_problematic_videos(self, threshold: int = 3) -> List[Dict[str, Any]]:
        """Get videos with multiple errors"""
        problematic = [
            {
                'video_id': video_id,
                'error_count': len(errors),
                'error_types': list(set(e.get('error_type', 'Unknown') for e in errors))
            }
            for video_id, errors in self.errors_by_video.items()
            if len(errors) >= threshold
        ]
        
        return sorted(problematic, key=lambda x: x['error_count'], reverse=True)
    
    def get_error_timeline(self) -> Dict[str, int]:
        """Get error count by hour"""
        return {
            hour: len(errors)
            for hour, errors in sorted(self.errors_by_time.items())
        }


# Global error logger instance
error_logger = ErrorLogger()


# Convenience functions
def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    video_id: Optional[str] = None,
    channel_id: Optional[str] = None
):
    """Convenience function to log errors"""
    error_logger.log_error(error, context, video_id, channel_id)


def get_error_summary() -> Dict[str, Any]:
    """Convenience function to get error summary"""
    return error_logger.get_error_summary()