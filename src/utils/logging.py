"""Logging configuration using Loguru."""

import sys
from typing import Optional

from loguru import logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "500 MB",
    retention: str = "10 days",
    enable_json: bool = False,
) -> None:
    """Set up logging configuration."""
    logger.remove()
    
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    logger.add(
        sys.stderr,
        level=level,
        format=log_format,
        colorize=True,
    )
    
    if log_file:
        file_format = "{time} | {level} | {name}:{function}:{line} | {message}"
        
        logger.add(
            log_file,
            level="DEBUG",
            format=file_format,
            rotation=rotation,
            retention=retention,
            serialize=enable_json,
            encoding="utf-8",
        )
    
    logger.info(f"Logging initialized at {level} level")