# Test Infrastructure

This document describes the comprehensive test infrastructure created for speech-mcp-echo.

## Overview

The test infrastructure provides shared fixtures, mocks, and utilities for testing the speech-mcp-echo project without requiring real audio devices or API access.

## Files Created

### 1. Core Infrastructure

#### `tests/conftest.py` (427 lines)
Shared pytest fixtures providing:

**Configuration Fixtures:**
- `temp_config_dir` - Temporary configuration directory
- `temp_config_file` - Temporary config.json with defaults
- `mock_config_paths` - Mock config paths for testing
- `clean_env` - Clean environment variables
- `mock_api_keys` - Mock API keys for all services

**Audio Fixtures:**
- `sample_audio_data` - 1 second of silence (16kHz, int16)
- `sample_audio_tone` - 1 second of 440Hz tone
- `sample_audio_file` - Temporary WAV file
- `mock_pyaudio` - Complete PyAudio mock (thread-safe)
- `mock_audio_stream` - Mock audio stream with sample data

**Logging Fixtures:**
- `temp_log_dir` - Temporary log directory
- `mock_log_dir` - Mock LOG_DIR for testing

**Utility Fixtures:**
- `reset_singletons` - Reset singleton instances between tests

### 2. Sample Configurations

#### `tests/fixtures/sample_configs.py` (468 lines)
Pre-configured test scenarios:

**Default Configurations:**
- `DEFAULT_CONFIG` - Standard configuration
- `MINIMAL_CONFIG` - Minimal required config
- `EMPTY_CONFIG` - Empty configuration
- `INVALID_ENGINE_CONFIG` - Invalid engine names

**STT Engine Variations:**
- `STT_FASTER_WHISPER_CONFIG` - faster-whisper (local)
- `STT_OPENAI_CONFIG` - OpenAI Whisper API
- `STT_GOOGLE_CONFIG` - Google Speech-to-Text

**TTS Engine Variations:**
- `TTS_GOOGLE_CONFIG` - Google Cloud TTS
- `TTS_OPENAI_CONFIG` - OpenAI TTS (tts-1)
- `TTS_OPENAI_HD_CONFIG` - OpenAI TTS HD (tts-1-hd)

**Timeout Variations:**
- `TIMEOUT_5_SECONDS_CONFIG` - 5s timeout (very short)
- `TIMEOUT_30_SECONDS_CONFIG` - 30s timeout (Codex-friendly)
- `TIMEOUT_60_SECONDS_CONFIG` - 60s timeout (medium)
- `TIMEOUT_120_SECONDS_CONFIG` - 120s timeout (Claude Code-friendly)

**Summarizer Variations:**
- `SUMMARIZER_ENABLED_JARVIS_CONFIG` - JARVIS personality
- `SUMMARIZER_ENABLED_NEUTRAL_CONFIG` - Neutral personality
- `SUMMARIZER_DISABLED_CONFIG` - Summarizer disabled

**Language Variations:**
- `ENGLISH_CONFIG` - English (en-US)
- `CHINESE_TRADITIONAL_CONFIG` - Traditional Chinese (cmn-TW)
- `JAPANESE_CONFIG` - Japanese (ja-JP)

**Helper Function:**
- `get_config(name: str)` - Get deep copy of any configuration

### 3. Mock Audio Implementation

#### `tests/helpers/mock_audio.py` (400 lines)
Thread-safe PyAudio mocks:

**Classes:**
- `MockAudioStream` - Thread-safe audio stream
  - Supports read/write operations
  - Customizable data generators
  - Active state management
  - Call counting for verification

- `MockPyAudio` - Complete PyAudio mock
  - Mock device enumeration (3 devices)
  - Mock device info
  - Stream creation
  - Thread-safe operations

**Data Generators:**
- `create_tone_generator(frequency, sample_rate)` - Sine wave generator
- `create_noise_generator(amplitude, sample_rate)` - White noise
- `create_timeout_generator(timeout_after)` - Timeout after N calls
- `create_pattern_generator(pattern, sample_rate)` - Repeating pattern

### 4. Mock API Responses

#### `tests/helpers/mock_apis.py` (371 lines)
Mock API clients for all external services:

**OpenAI Whisper (STT):**
- `create_mock_openai_whisper_success()` - Successful transcription
- `create_mock_openai_whisper_auth_error()` - Authentication error
- `create_mock_openai_whisper_rate_limit()` - Rate limit error
- `create_mock_openai_whisper_timeout()` - Timeout error

**OpenAI TTS:**
- `create_mock_openai_tts_success()` - Successful audio generation
- `create_mock_openai_tts_auth_error()` - Authentication error
- `create_mock_openai_tts_rate_limit()` - Rate limit error

**Google Speech-to-Text:**
- `create_mock_google_stt_success()` - Successful transcription
- `create_mock_google_stt_auth_error()` - Authentication error
- `create_mock_google_stt_quota_error()` - Quota exceeded

**Google Text-to-Speech:**
- `create_mock_google_tts_success()` - Successful audio generation
- `create_mock_google_tts_auth_error()` - Authentication error
- `create_mock_google_tts_quota_error()` - Quota exceeded

**Network Scenarios:**
- `create_mock_api_network_error()` - Connection error
- `create_mock_api_timeout()` - Request timeout
- `create_mock_api_slow_response(delay_seconds)` - Slow response
- `create_mock_api_flaky(success_after)` - Intermittent failures

**Helper:**
- `get_mock_api(service, scenario)` - Get any mock by name

## Tests Created

### 5. Config Module Tests

#### `tests/test_config.py` (35 tests, 98% coverage)

**Config Directory Tests (2 tests):**
- Directory creation
- Idempotent directory creation

**Config Loading Tests (5 tests):**
- Missing file (defaults)
- Existing file
- Merge with defaults
- Invalid JSON handling
- IO error handling

**Config Saving Tests (4 tests):**
- File creation
- Correct content
- Overwrite existing
- IO error handling

**Get/Set Setting Tests (6 tests):**
- Get existing setting
- Missing section
- Missing key
- Set in new section
- Set in existing section
- Overwrite existing value

**Environment Variable Tests (5 tests):**
- Get with prefix
- Get without prefix
- Prefer prefixed
- Return default
- Set with prefix

**API Key Tests (7 tests):**
- OpenAI (with/without prefix)
- Google credentials
- Anthropic
- ElevenLabs
- Not found
- Unknown service

**Deep Merge Tests (1 test):**
- Preserve nested values

**Timeout Configuration Tests (3 tests):**
- Default timeout value (45s)
- Custom timeout from file
- Timeout from env var

**Config Validation Tests (2 tests):**
- All engine combinations
- Empty config

**Coverage:** 98% of config module (64/65 lines)

### 6. Logger Module Tests

#### `tests/test_logger.py` (21 tests, 97% coverage)

**Logger Initialization Tests (3 tests):**
- Returns logger instance
- With component parameter
- Multiple get_logger calls

**Log Level Tests (4 tests):**
- Default level (INFO)
- Custom level (DEBUG)
- WARNING level
- ERROR level

**Log File Tests (4 tests):**
- Creates log file
- Component-named file
- Default file name
- Contains messages

**Log Format Tests (3 tests):**
- Includes timestamp
- Includes log level
- Includes logger name

**Handler Tests (2 tests):**
- Console handler added
- File handler added

**Multiple Logger Tests (2 tests):**
- Share configuration
- Logger hierarchy

**Edge Cases (2 tests):**
- Get logger before setup
- Setup multiple times

**Coverage:** 97% of logger module (28/29 lines)

## Usage Examples

### Using Configuration Fixtures

```python
def test_config_loading(mock_config_paths):
    """Test loads from mocked config directory."""
    from speech_mcp_echo.config import load_config
    config = load_config()
    # Config uses temp directory, no pollution
    assert config is not None
```

### Using Sample Configs

```python
from tests.fixtures.sample_configs import get_config

def test_with_openai_config():
    config = get_config("stt_openai")
    assert config["stt"]["engine"] == "openai"
```

### Using Mock Audio

```python
def test_audio_capture(mock_pyaudio):
    from unittest.mock import patch

    with patch('module.pyaudio', mock_pyaudio):
        # Test code that uses PyAudio
        # No real audio devices accessed
        pass
```

### Using Mock APIs

```python
from tests.helpers.mock_apis import get_mock_api

def test_stt_api():
    mock_client = get_mock_api("openai_whisper", "success")
    # Use mock_client in tests
```

## Test Statistics

**Total New Tests:** 56
- Config tests: 35
- Logger tests: 21

**Total Project Tests:** 97
- New tests: 56
- Existing tests: 41 (38 passing, 3 pre-existing failures)

**Code Coverage:**
- Config module: 98% (up from 0%)
- Logger module: 97% (up from 0%)
- Overall project: 55% (up from ~8%)

## Thread Safety

All mocks are thread-safe:
- `MockAudioStream` uses threading.Lock
- `MockPyAudio` uses threading.Lock
- Safe for concurrent test execution
- Safe for testing audio recording (which uses threads)

## Best Practices

1. **Always use fixtures** - Don't create temp files/dirs manually
2. **Use mock_config_paths** - Prevents config file pollution
3. **Use clean_env** - Ensures no env var leakage between tests
4. **No real audio devices** - All audio tests use mocks
5. **No real API calls** - All API tests use mocks
6. **Descriptive test names** - Follow pattern: test_<what>_<when>_<expected>

## Next Steps

Future test infrastructure to add:
- Mock STT adapters
- Mock TTS adapters
- Mock summarizer
- Audio processor tests
- Voice engine integration tests
- Server MCP tool tests
