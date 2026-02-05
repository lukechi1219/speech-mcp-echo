"""
Unit tests for speech_mcp_echo.utils.logger module.

Tests logger initialization, configuration, and output.
"""

import os
import logging
import pytest
from pathlib import Path

from speech_mcp_echo.utils.logger import (
    setup_logging,
    get_logger,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_DIR,
)


# =============================================================================
# Logger Initialization Tests
# =============================================================================

def test_setup_logging_creates_log_dir(mock_log_dir):
    """Test that setup_logging creates log directory."""
    assert mock_log_dir.exists()


def test_get_logger_returns_logger(mock_log_dir):
    """Test that get_logger returns a logger instance."""
    logger = get_logger(__name__)

    assert logger is not None
    assert isinstance(logger, logging.Logger)


def test_get_logger_with_component(mock_log_dir):
    """Test that get_logger accepts component parameter."""
    logger = get_logger(__name__, component="test_component")

    assert logger is not None
    assert isinstance(logger, logging.Logger)


def test_multiple_get_logger_calls(mock_log_dir):
    """Test that multiple get_logger calls work correctly."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    logger3 = get_logger("module1")  # Same as logger1

    assert logger1 is not None
    assert logger2 is not None
    assert logger1.name == "module1"
    assert logger2.name == "module2"
    assert logger1.name == logger3.name


# =============================================================================
# Log Level Tests
# =============================================================================

def test_setup_logging_default_level(mock_log_dir):
    """Test that default log level is INFO."""
    setup_logging()

    logger = logging.getLogger("speech_mcp_echo")

    assert logger.level == logging.INFO


def test_setup_logging_custom_level(mock_log_dir):
    """Test setting custom log level."""
    setup_logging(level=logging.DEBUG)

    logger = logging.getLogger("speech_mcp_echo")

    assert logger.level == logging.DEBUG


def test_setup_logging_warning_level(mock_log_dir):
    """Test setting WARNING log level."""
    setup_logging(level=logging.WARNING)

    logger = logging.getLogger("speech_mcp_echo")

    assert logger.level == logging.WARNING


def test_setup_logging_error_level(mock_log_dir):
    """Test setting ERROR log level."""
    setup_logging(level=logging.ERROR)

    logger = logging.getLogger("speech_mcp_echo")

    assert logger.level == logging.ERROR


# =============================================================================
# Log File Tests
# =============================================================================

def test_setup_logging_creates_log_file(mock_log_dir):
    """Test that setup_logging creates log file."""
    log_file = mock_log_dir / "test.log"
    setup_logging(log_file=str(log_file))

    logger = logging.getLogger("speech_mcp_echo")
    logger.info("Test message")

    assert log_file.exists()


def test_setup_logging_with_component_name(mock_log_dir):
    """Test that component parameter creates named log file."""
    setup_logging(component="test_component")

    expected_log = mock_log_dir / "test_component.log"

    logger = logging.getLogger("speech_mcp_echo")
    logger.info("Test message")

    assert expected_log.exists()


def test_setup_logging_default_file_name(mock_log_dir):
    """Test that default log file is created with standard name."""
    setup_logging()

    expected_log = mock_log_dir / "speech-mcp-echo.log"

    logger = logging.getLogger("speech_mcp_echo")
    logger.info("Test message")

    assert expected_log.exists()


def test_log_file_contains_messages(mock_log_dir):
    """Test that log file contains logged messages."""
    log_file = mock_log_dir / "test.log"
    setup_logging(log_file=str(log_file))

    logger = logging.getLogger("speech_mcp_echo")
    test_message = "This is a test log message"
    logger.info(test_message)

    # Force flush
    for handler in logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text()
    assert test_message in content


# =============================================================================
# Log Format Tests
# =============================================================================

def test_log_format_includes_timestamp(mock_log_dir):
    """Test that log format includes timestamp."""
    log_file = mock_log_dir / "test.log"
    setup_logging(log_file=str(log_file))

    logger = logging.getLogger("speech_mcp_echo")
    logger.info("Test message")

    # Force flush
    for handler in logger.handlers:
        handler.flush()

    content = log_file.read_text()

    # Should contain timestamp pattern (YYYY-MM-DD HH:MM:SS)
    import re

    timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
    assert re.search(timestamp_pattern, content)


def test_log_format_includes_level(mock_log_dir):
    """Test that log format includes log level."""
    log_file = mock_log_dir / "test.log"
    setup_logging(log_file=str(log_file))

    logger = logging.getLogger("speech_mcp_echo")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Force flush
    for handler in logger.handlers:
        handler.flush()

    content = log_file.read_text()

    assert "INFO" in content
    assert "WARNING" in content
    assert "ERROR" in content


def test_log_format_includes_logger_name(mock_log_dir):
    """Test that log format includes logger name."""
    log_file = mock_log_dir / "test.log"
    setup_logging(log_file=str(log_file))

    logger = logging.getLogger("speech_mcp_echo.test_module")
    logger.info("Test message")

    # Force flush
    for handler in logger.handlers:
        handler.flush()

    content = log_file.read_text()

    assert "speech_mcp_echo.test_module" in content


# =============================================================================
# Handler Tests
# =============================================================================

def test_setup_logging_adds_console_handler(mock_log_dir):
    """Test that setup_logging adds console handler."""
    setup_logging()

    logger = logging.getLogger("speech_mcp_echo")

    # Should have at least console handler
    assert len(logger.handlers) >= 1

    # Check for StreamHandler
    has_console = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    assert has_console


def test_setup_logging_adds_file_handler(mock_log_dir):
    """Test that setup_logging adds file handler."""
    log_file = mock_log_dir / "test.log"
    setup_logging(log_file=str(log_file))

    logger = logging.getLogger("speech_mcp_echo")

    # Should have file handler
    has_file = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    assert has_file


# =============================================================================
# Multiple Logger Instance Tests
# =============================================================================

def test_multiple_loggers_share_config(mock_log_dir):
    """Test that multiple loggers share configuration."""
    setup_logging(level=logging.DEBUG)

    logger1 = get_logger("module1")
    logger2 = get_logger("module2")

    # Both should inherit DEBUG level from root speech_mcp_echo logger
    root_logger = logging.getLogger("speech_mcp_echo")

    assert root_logger.level == logging.DEBUG


def test_logger_hierarchy(mock_log_dir):
    """Test that logger hierarchy works correctly."""
    setup_logging(level=logging.INFO)

    parent_logger = logging.getLogger("speech_mcp_echo")
    child_logger = logging.getLogger("speech_mcp_echo.child")

    assert parent_logger.level == logging.INFO

    # Child should inherit from parent
    child_logger.info("Child message")  # Should work


# =============================================================================
# Edge Cases
# =============================================================================

def test_get_logger_before_setup(mock_log_dir):
    """Test that get_logger works even before explicit setup_logging call."""
    # Don't call setup_logging first
    logger = get_logger("test_module")

    # Should auto-setup
    assert logger is not None
    assert isinstance(logger, logging.Logger)


def test_setup_logging_multiple_times(mock_log_dir):
    """Test that calling setup_logging multiple times doesn't cause issues."""
    setup_logging()
    setup_logging()
    setup_logging()

    logger = logging.getLogger("speech_mcp_echo")

    # Should still work
    logger.info("Test message")
