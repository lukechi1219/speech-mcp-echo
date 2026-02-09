"""
Shared pytest fixtures for speech-mcp-echo tests.

This module provides reusable fixtures for:
- Mock PyAudio environment (no real audio device access)
- Mock environment variables (API keys, config paths)
- Temporary config file handling
- Sample audio data generation
- Thread-safe mocks for concurrent testing
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, MagicMock, patch
import pytest
import numpy as np


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary configuration directory.

    Yields:
        Path to temporary config directory

    Usage:
        def test_something(temp_config_dir):
            config_file = temp_config_dir / "config.json"
            # ... test code
    """
    config_dir = tmp_path / "speech-mcp-echo-test"
    config_dir.mkdir(parents=True, exist_ok=True)
    yield config_dir
    # Cleanup handled by tmp_path


@pytest.fixture
def temp_config_file(temp_config_dir: Path) -> Generator[Path, None, None]:
    """
    Create a temporary config.json file with default content.

    Yields:
        Path to temporary config.json file

    Usage:
        def test_load_config(temp_config_file):
            with open(temp_config_file) as f:
                config = json.load(f)
    """
    config_file = temp_config_dir / "config.json"

    # Write default config
    default_config = {
        "stt": {
            "engine": "faster-whisper",
            "model": "base",
            "device": "cpu",
            "timeout": 45
        },
        "tts": {
            "engine": "google",
            "voice": "en-US-Journey-D",
            "language": "en-US"
        },
        "summarizer": {
            "enabled": True,
            "personality": "jarvis",
            "language": "en"
        }
    }

    with open(config_file, "w") as f:
        json.dump(default_config, f, indent=2)

    yield config_file


@pytest.fixture
def mock_config_paths(temp_config_dir: Path, monkeypatch) -> Generator[Dict[str, Path], None, None]:
    """
    Mock configuration paths to use temporary directory.

    Patches speech_mcp_echo.config module to use temp paths.

    Yields:
        Dict with 'config_dir' and 'config_file' paths

    Usage:
        def test_config(mock_config_paths):
            # Config functions now use temp_config_paths['config_file']
            from speech_mcp_echo.config import load_config
            config = load_config()
    """
    config_file = temp_config_dir / "config.json"

    # Patch config module paths
    monkeypatch.setattr("speech_mcp_echo.config.CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr("speech_mcp_echo.config.CONFIG_FILE", config_file)

    yield {
        "config_dir": temp_config_dir,
        "config_file": config_file
    }


@pytest.fixture
def clean_env(monkeypatch) -> Generator[None, None, None]:
    """
    Clean environment variables before test.

    Removes all SPEECH_MCP_ECHO_* and API key environment variables.

    Usage:
        def test_no_env_vars(clean_env):
            # All speech-mcp-echo env vars are cleared
            assert "SPEECH_MCP_ECHO_TTS_ENGINE" not in os.environ
    """
    # List of env vars to remove
    env_vars_to_remove = [
        "SPEECH_MCP_ECHO_TTS_ENGINE",
        "SPEECH_MCP_ECHO_TTS_VOICE",
        "SPEECH_MCP_ECHO_STT_ENGINE",
        "SPEECH_MCP_ECHO_STT_TIMEOUT",
        "OPENAI_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
        "GROQ_API_KEY",
        "ELEVENLABS_API_KEY",
    ]

    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)

    yield


@pytest.fixture
def mock_api_keys(monkeypatch) -> Generator[Dict[str, str], None, None]:
    """
    Provide mock API keys for testing.

    Sets dummy API keys in environment variables.

    Yields:
        Dict mapping service names to mock API keys

    Usage:
        def test_api_key(mock_api_keys):
            assert "OPENAI_API_KEY" in os.environ
            assert os.environ["OPENAI_API_KEY"] == mock_api_keys["openai"]
    """
    api_keys = {
        "openai": "sk-test-openai-key-12345",
        "google": "/tmp/test-google-credentials.json",
        "anthropic": "sk-ant-test-key-12345",
        "groq": "gsk-test-groq-key-12345",
        "elevenlabs": "test-elevenlabs-key-12345",
    }

    monkeypatch.setenv("OPENAI_API_KEY", api_keys["openai"])
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", api_keys["google"])
    monkeypatch.setenv("GROQ_API_KEY", api_keys["groq"])
    monkeypatch.setenv("ANTHROPIC_API_KEY", api_keys["anthropic"])
    monkeypatch.setenv("ELEVENLABS_API_KEY", api_keys["elevenlabs"])

    yield api_keys


# =============================================================================
# Audio Fixtures
# =============================================================================

@pytest.fixture
def sample_audio_data() -> np.ndarray:
    """
    Generate sample audio data (silence).

    Returns:
        NumPy array of int16 audio samples (1 second of silence at 16kHz)

    Usage:
        def test_audio_processing(sample_audio_data):
            assert len(sample_audio_data) == 16000  # 1 second at 16kHz
            assert sample_audio_data.dtype == np.int16
    """
    # 1 second of silence at 16kHz
    return np.zeros(16000, dtype=np.int16)


@pytest.fixture
def sample_audio_tone() -> np.ndarray:
    """
    Generate sample audio data (440Hz tone).

    Returns:
        NumPy array of int16 audio samples (1 second of 440Hz at 16kHz)

    Usage:
        def test_audio_tone(sample_audio_tone):
            # Tone has non-zero values
            assert np.any(sample_audio_tone != 0)
    """
    # 1 second of 440Hz tone at 16kHz
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(frequency * 2 * np.pi * t)

    # Scale to int16 range
    tone = (tone * 32767 / 2).astype(np.int16)

    return tone


@pytest.fixture
def sample_audio_file(tmp_path: Path, sample_audio_tone: np.ndarray) -> Generator[Path, None, None]:
    """
    Create a temporary WAV file with sample audio.

    Args:
        tmp_path: Pytest temporary path fixture
        sample_audio_tone: Sample audio data

    Yields:
        Path to temporary WAV file

    Usage:
        def test_audio_file(sample_audio_file):
            import wave
            with wave.open(str(sample_audio_file), 'rb') as wf:
                assert wf.getnchannels() == 1
                assert wf.getframerate() == 16000
    """
    import wave

    audio_file = tmp_path / "test_audio.wav"

    with wave.open(str(audio_file), 'wb') as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(16000)  # 16kHz
        wf.writeframes(sample_audio_tone.tobytes())

    yield audio_file


# =============================================================================
# Mock PyAudio Fixtures
# =============================================================================

@pytest.fixture
def mock_pyaudio():
    """
    Mock PyAudio module for tests that don't need real audio devices.

    Provides a thread-safe mock of PyAudio with:
    - Mock audio device enumeration
    - Mock audio stream (read/write)
    - No actual audio device access

    Returns:
        Mock PyAudio class

    Usage:
        def test_audio_capture(mock_pyaudio):
            with patch('speech_mcp_echo.audio_processor.pyaudio', mock_pyaudio):
                # Test code that uses PyAudio
                pass
    """
    mock_pa = MagicMock()

    # Mock PyAudio instance
    mock_instance = MagicMock()
    mock_pa.PyAudio.return_value = mock_instance

    # Mock format constant
    mock_pa.paInt16 = 8  # Real PyAudio constant

    # Mock get_device_count
    mock_instance.get_device_count.return_value = 2

    # Mock get_device_info_by_index
    def mock_get_device_info(index):
        devices = [
            {
                "name": "Test Microphone",
                "maxInputChannels": 2,
                "maxOutputChannels": 0,
                "defaultSampleRate": 16000.0,
            },
            {
                "name": "Test Speaker",
                "maxInputChannels": 0,
                "maxOutputChannels": 2,
                "defaultSampleRate": 44100.0,
            },
        ]
        return devices[index % len(devices)]

    mock_instance.get_device_info_by_index.side_effect = mock_get_device_info

    # Mock open stream
    mock_stream = MagicMock()
    mock_stream.is_active.return_value = True
    mock_stream.read.return_value = np.zeros(1024, dtype=np.int16).tobytes()
    mock_instance.open.return_value = mock_stream

    return mock_pa


@pytest.fixture
def mock_audio_stream(sample_audio_data: np.ndarray):
    """
    Create a mock audio stream with sample data.

    Returns:
        Mock stream object that returns sample audio when read()

    Usage:
        def test_stream_read(mock_audio_stream):
            data = mock_audio_stream.read(1024)
            assert len(data) == 1024 * 2  # 2 bytes per int16 sample
    """
    mock_stream = MagicMock()

    # Return chunks of sample audio data
    chunk_size = 1024

    def read_audio(num_frames, exception_on_overflow=True):
        # Return chunk_size samples as bytes
        chunk = sample_audio_data[:num_frames]
        if len(chunk) < num_frames:
            # Pad with zeros if needed
            chunk = np.pad(chunk, (0, num_frames - len(chunk)), 'constant')
        return chunk.tobytes()

    mock_stream.read.side_effect = read_audio
    mock_stream.is_active.return_value = True
    mock_stream.start_stream.return_value = None
    mock_stream.stop_stream.return_value = None
    mock_stream.close.return_value = None

    return mock_stream


# =============================================================================
# Logging Fixtures
# =============================================================================

@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary log directory.

    Yields:
        Path to temporary log directory

    Usage:
        def test_logging(temp_log_dir):
            log_file = temp_log_dir / "test.log"
            # ... logging code
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    yield log_dir


@pytest.fixture
def mock_log_dir(temp_log_dir: Path, monkeypatch) -> Generator[Path, None, None]:
    """
    Mock LOG_DIR to use temporary directory.

    Patches speech_mcp_echo.utils.logger module.

    Yields:
        Path to temporary log directory

    Usage:
        def test_logger(mock_log_dir):
            from speech_mcp_echo.utils.logger import get_logger
            logger = get_logger(__name__)
            # Logs go to mock_log_dir
    """
    monkeypatch.setattr("speech_mcp_echo.utils.logger.LOG_DIR", temp_log_dir)
    yield temp_log_dir


# =============================================================================
# Utility Fixtures
# =============================================================================

@pytest.fixture
def reset_singletons():
    """
    Reset any singleton instances between tests.

    Useful for testing modules that use singleton pattern.

    Usage:
        def test_singleton(reset_singletons):
            # Any singletons are reset before this test
            pass
    """
    # Add singleton reset logic here if needed
    yield
    # Cleanup after test
