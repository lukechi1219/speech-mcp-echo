"""
Unit tests for speech_mcp_echo.config module.

Tests configuration loading, saving, merging, validation, and environment variable handling.
"""

import os
import json
import pytest
from pathlib import Path
from typing import Dict, Any

from speech_mcp_echo.config import (
    load_config,
    save_config,
    get_setting,
    set_setting,
    get_env,
    set_env_setting,
    get_api_key,
    ensure_config_dir,
    DEFAULT_CONFIG,
    CONFIG_DIR,
    CONFIG_FILE,
    ENV_PREFIX,
)


# =============================================================================
# Config Directory Tests
# =============================================================================

def test_ensure_config_dir_creates_directory(tmp_path, monkeypatch):
    """Test that ensure_config_dir creates the config directory."""
    test_config_dir = tmp_path / "test_config"
    monkeypatch.setattr("speech_mcp_echo.config.CONFIG_DIR", test_config_dir)

    assert not test_config_dir.exists()
    ensure_config_dir()
    assert test_config_dir.exists()
    assert test_config_dir.is_dir()


def test_ensure_config_dir_idempotent(tmp_path, monkeypatch):
    """Test that ensure_config_dir can be called multiple times safely."""
    test_config_dir = tmp_path / "test_config"
    monkeypatch.setattr("speech_mcp_echo.config.CONFIG_DIR", test_config_dir)

    ensure_config_dir()
    ensure_config_dir()
    ensure_config_dir()

    assert test_config_dir.exists()


# =============================================================================
# Config Loading Tests
# =============================================================================

def test_load_config_with_missing_file(mock_config_paths):
    """Test that load_config returns default config when file doesn't exist."""
    config = load_config()

    assert config is not None
    assert "stt" in config
    assert "tts" in config
    assert config["stt"]["engine"] == DEFAULT_CONFIG["stt"]["engine"]


def test_load_config_with_existing_file(mock_config_paths):
    """Test that load_config reads from existing config file."""
    config_file = mock_config_paths["config_file"]

    # Write custom config
    custom_config = {
        "stt": {"engine": "openai", "timeout": 30},
        "tts": {"engine": "openai", "voice": "nova"},
    }

    with open(config_file, "w") as f:
        json.dump(custom_config, f)

    # Load config
    config = load_config()

    assert config["stt"]["engine"] == "openai"
    assert config["stt"]["timeout"] == 30
    assert config["tts"]["engine"] == "openai"
    assert config["tts"]["voice"] == "nova"


def test_load_config_merges_with_defaults(mock_config_paths):
    """Test that load_config merges user config with defaults."""
    config_file = mock_config_paths["config_file"]

    # Write partial config (only override STT engine)
    partial_config = {"stt": {"engine": "google"}}

    with open(config_file, "w") as f:
        json.dump(partial_config, f)

    # Load config
    config = load_config()

    # Should have custom STT engine
    assert config["stt"]["engine"] == "google"

    # Should still have default values for other settings
    assert "tts" in config
    assert "summarizer" in config
    assert config["stt"]["timeout"] == DEFAULT_CONFIG["stt"]["timeout"]


def test_load_config_with_invalid_json(mock_config_paths):
    """Test that load_config handles invalid JSON gracefully."""
    config_file = mock_config_paths["config_file"]

    # Write invalid JSON
    with open(config_file, "w") as f:
        f.write("{ invalid json }")

    # Should return default config
    config = load_config()
    assert config == DEFAULT_CONFIG


def test_load_config_with_io_error(mock_config_paths, monkeypatch):
    """Test that load_config handles IO errors gracefully."""
    config_file = mock_config_paths["config_file"]

    # Create config file
    with open(config_file, "w") as f:
        json.dump({"stt": {"engine": "test"}}, f)

    # Mock open to raise IOError
    original_open = open

    def mock_open_error(*args, **kwargs):
        if str(config_file) in str(args[0]):
            raise IOError("Mock IO error")
        return original_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open_error)

    # Should return default config
    config = load_config()
    assert config == DEFAULT_CONFIG


# =============================================================================
# Config Saving Tests
# =============================================================================

def test_save_config_creates_file(mock_config_paths):
    """Test that save_config creates config file."""
    config_file = mock_config_paths["config_file"]

    config = {"stt": {"engine": "test"}, "tts": {"engine": "test"}}

    result = save_config(config)

    assert result is True
    assert config_file.exists()


def test_save_config_writes_correct_content(mock_config_paths):
    """Test that save_config writes correct JSON content."""
    config_file = mock_config_paths["config_file"]

    config = {
        "stt": {"engine": "faster-whisper", "timeout": 60},
        "tts": {"engine": "google", "voice": "en-US-Journey-D"},
    }

    save_config(config)

    # Read back and verify
    with open(config_file) as f:
        saved_config = json.load(f)

    assert saved_config == config


def test_save_config_overwrites_existing(mock_config_paths):
    """Test that save_config overwrites existing config file."""
    config_file = mock_config_paths["config_file"]

    # Save first config
    config1 = {"stt": {"engine": "openai"}}
    save_config(config1)

    # Save second config
    config2 = {"stt": {"engine": "google"}}
    save_config(config2)

    # Read back and verify
    with open(config_file) as f:
        saved_config = json.load(f)

    assert saved_config["stt"]["engine"] == "google"


def test_save_config_handles_io_error(mock_config_paths, monkeypatch):
    """Test that save_config handles IO errors gracefully."""

    # Mock open to raise IOError
    def mock_open_error(*args, **kwargs):
        if "config.json" in str(args[0]):
            raise IOError("Mock IO error")
        return open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open_error)

    config = {"stt": {"engine": "test"}}
    result = save_config(config)

    assert result is False


# =============================================================================
# Get/Set Setting Tests
# =============================================================================

def test_get_setting_existing(mock_config_paths):
    """Test getting an existing setting."""
    config_file = mock_config_paths["config_file"]

    config = {"stt": {"engine": "faster-whisper", "timeout": 30}}
    with open(config_file, "w") as f:
        json.dump(config, f)

    engine = get_setting("stt", "engine")
    timeout = get_setting("stt", "timeout")

    assert engine == "faster-whisper"
    assert timeout == 30


def test_get_setting_missing_section(mock_config_paths):
    """Test getting setting from missing section returns default."""
    value = get_setting("nonexistent_section", "key", default="default_value")

    assert value == "default_value"


def test_get_setting_missing_key(mock_config_paths):
    """Test getting missing key returns default."""
    config_file = mock_config_paths["config_file"]

    config = {"stt": {"engine": "faster-whisper"}}
    with open(config_file, "w") as f:
        json.dump(config, f)

    value = get_setting("stt", "nonexistent_key", default="default_value")

    assert value == "default_value"


def test_set_setting_new_section(mock_config_paths):
    """Test setting a value in a new section."""
    result = set_setting("new_section", "new_key", "new_value")

    assert result is True

    config = load_config()
    assert config["new_section"]["new_key"] == "new_value"


def test_set_setting_existing_section(mock_config_paths):
    """Test setting a value in an existing section."""
    config_file = mock_config_paths["config_file"]

    config = {"stt": {"engine": "faster-whisper"}}
    with open(config_file, "w") as f:
        json.dump(config, f)

    result = set_setting("stt", "timeout", 60)

    assert result is True

    config = load_config()
    assert config["stt"]["timeout"] == 60
    assert config["stt"]["engine"] == "faster-whisper"  # Existing value preserved


def test_set_setting_overwrites_existing(mock_config_paths):
    """Test that set_setting overwrites existing values."""
    config_file = mock_config_paths["config_file"]

    config = {"stt": {"engine": "faster-whisper", "timeout": 30}}
    with open(config_file, "w") as f:
        json.dump(config, f)

    set_setting("stt", "timeout", 60)

    config = load_config()
    assert config["stt"]["timeout"] == 60


# =============================================================================
# Environment Variable Tests
# =============================================================================

def test_get_env_with_prefix(clean_env, monkeypatch):
    """Test getting environment variable with prefix."""
    monkeypatch.setenv("SPEECH_MCP_ECHO_TEST_VAR", "test_value")

    value = get_env("TEST_VAR")

    assert value == "test_value"


def test_get_env_without_prefix(clean_env, monkeypatch):
    """Test getting environment variable without prefix."""
    monkeypatch.setenv("TEST_VAR", "test_value")

    value = get_env("TEST_VAR")

    assert value == "test_value"


def test_get_env_prefers_prefixed(clean_env, monkeypatch):
    """Test that get_env prefers prefixed version."""
    monkeypatch.setenv("SPEECH_MCP_ECHO_TEST_VAR", "prefixed_value")
    monkeypatch.setenv("TEST_VAR", "unprefixed_value")

    value = get_env("TEST_VAR")

    assert value == "prefixed_value"


def test_get_env_returns_default(clean_env):
    """Test that get_env returns default when not found."""
    value = get_env("NONEXISTENT_VAR", default="default_value")

    assert value == "default_value"


def test_set_env_setting_adds_prefix(clean_env):
    """Test that set_env_setting adds prefix."""
    set_env_setting("TEST_VAR", "test_value")

    assert os.environ["SPEECH_MCP_ECHO_TEST_VAR"] == "test_value"


# =============================================================================
# API Key Tests
# =============================================================================

def test_get_api_key_openai_with_prefix(clean_env, monkeypatch):
    """Test getting OpenAI API key with prefix."""
    monkeypatch.setenv("SPEECH_MCP_ECHO_OPENAI_API_KEY", "sk-prefixed-key")

    key = get_api_key("openai")

    assert key == "sk-prefixed-key"


def test_get_api_key_openai_without_prefix(clean_env, monkeypatch):
    """Test getting OpenAI API key without prefix."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-standard-key")

    key = get_api_key("openai")

    assert key == "sk-standard-key"


def test_get_api_key_google_credentials(clean_env, monkeypatch):
    """Test getting Google credentials path."""
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/credentials.json")

    key = get_api_key("google")

    assert key == "/path/to/credentials.json"


def test_get_api_key_anthropic(clean_env, monkeypatch):
    """Test getting Anthropic API key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

    key = get_api_key("anthropic")

    assert key == "sk-ant-test-key"


def test_get_api_key_elevenlabs(clean_env, monkeypatch):
    """Test getting ElevenLabs API key."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "elevenlabs-test-key")

    key = get_api_key("elevenlabs")

    assert key == "elevenlabs-test-key"


def test_get_api_key_not_found(clean_env):
    """Test that get_api_key returns None when not found."""
    key = get_api_key("openai")

    assert key is None


def test_get_api_key_unknown_service(clean_env, monkeypatch):
    """Test getting API key for unknown service."""
    monkeypatch.setenv("SPEECH_MCP_ECHO_UNKNOWN_API_KEY", "test-key")

    key = get_api_key("unknown")

    assert key == "test-key"


# =============================================================================
# Deep Merge Tests
# =============================================================================

def test_deep_merge_preserves_nested_values(mock_config_paths):
    """Test that deep merge preserves nested values correctly."""
    config_file = mock_config_paths["config_file"]

    # User config only overrides specific values
    user_config = {"stt": {"timeout": 120}, "tts": {"voice": "nova"}}

    with open(config_file, "w") as f:
        json.dump(user_config, f)

    config = load_config()

    # User overrides should be applied
    assert config["stt"]["timeout"] == 120
    assert config["tts"]["voice"] == "nova"

    # Defaults should be preserved
    assert config["stt"]["engine"] == DEFAULT_CONFIG["stt"]["engine"]
    assert config["stt"]["model"] == DEFAULT_CONFIG["stt"]["model"]
    assert "summarizer" in config


# =============================================================================
# Timeout Configuration Tests
# =============================================================================

def test_default_timeout_value(mock_config_paths):
    """Test that default timeout is 45 seconds."""
    config = load_config()

    assert config["stt"]["timeout"] == 45


def test_custom_timeout_from_file(mock_config_paths):
    """Test loading custom timeout from config file."""
    config_file = mock_config_paths["config_file"]

    custom_config = {"stt": {"timeout": 120}}
    with open(config_file, "w") as f:
        json.dump(custom_config, f)

    config = load_config()

    assert config["stt"]["timeout"] == 120


def test_timeout_from_env_var(mock_config_paths, monkeypatch):
    """Test that timeout can be set via environment variable."""
    # Note: This tests the pattern, actual env var integration
    # would be in the VoiceEngine or adapter level
    monkeypatch.setenv("SPEECH_MCP_ECHO_STT_TIMEOUT", "90")

    timeout = get_env("STT_TIMEOUT")

    assert timeout == "90"


# =============================================================================
# Config Validation Tests (Implicit)
# =============================================================================

def test_config_with_all_engines(mock_config_paths):
    """Test config with different engine combinations."""
    from tests.fixtures.sample_configs import (
        STT_FASTER_WHISPER_CONFIG,
        STT_OPENAI_CONFIG,
        TTS_GOOGLE_CONFIG,
        TTS_OPENAI_CONFIG,
    )

    # Test each config can be loaded
    for test_config in [
        STT_FASTER_WHISPER_CONFIG,
        STT_OPENAI_CONFIG,
        TTS_GOOGLE_CONFIG,
        TTS_OPENAI_CONFIG,
    ]:
        config_file = mock_config_paths["config_file"]
        with open(config_file, "w") as f:
            json.dump(test_config, f)

        config = load_config()
        assert config is not None


def test_config_with_empty_dict(mock_config_paths):
    """Test that empty config merges with defaults."""
    config_file = mock_config_paths["config_file"]

    with open(config_file, "w") as f:
        json.dump({}, f)

    config = load_config()

    # Should get all defaults
    assert config["stt"]["engine"] == DEFAULT_CONFIG["stt"]["engine"]
    assert config["tts"]["engine"] == DEFAULT_CONFIG["tts"]["engine"]
