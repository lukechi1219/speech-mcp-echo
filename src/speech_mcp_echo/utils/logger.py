"""
Centralized logging for speech-mcp-echo.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Default log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log directory
LOG_DIR = Path.home() / ".config" / "speech-mcp-echo" / "logs"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    component: Optional[str] = None,
) -> None:
    """
    Set up logging configuration.

    Args:
        level: Logging level
        log_file: Optional file path for logging
        component: Optional component name for log file
    """
    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger("speech_mcp_echo")
    root_logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_path = Path(log_file)
    elif component:
        file_path = LOG_DIR / f"{component}.log"
    else:
        file_path = LOG_DIR / "speech-mcp-echo.log"

    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    root_logger.addHandler(file_handler)


def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually __name__)
        component: Optional component identifier

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # Set up basic config if not already configured
    if not logger.handlers and not logging.getLogger().handlers:
        setup_logging(component=component)

    return logger
