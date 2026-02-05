"""
Configuration management for speech-mcp-echo.

Supports JSON config files and environment variables.
API keys default to environment variables but can optionally use encrypted storage.
"""

import os
import json
from pathlib import Path
from typing import Any, Optional

# Configuration paths
CONFIG_DIR = Path.home() / ".config" / "speech-mcp-echo"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Environment variable prefix
ENV_PREFIX = "SPEECH_MCP_ECHO_"

# Default configuration
DEFAULT_CONFIG = {
    "stt": {
        "engine": "faster-whisper",  # faster-whisper, openai, google
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "language": "auto",  # Language code: auto, en, zh, ja, etc. "auto" detects language
        "timeout": 45,  # Audio recording timeout in seconds (safe for most CLIs)
        "silence_retry_count": 10,  # Retries when silence timeout (0 = no retry, ~15min tolerance)
        "retry_prompt_type": "beep",  # Prompt on retry: beep, voice, silent
        # API keys read from environment by default
    },
    "tts": {
        "engine": "google",  # kokoro, google, openai, pyttsx3
        "voice": "cmn-TW-Standard-B",
        "language": "cmn-TW",
        "speed": 1.0,
    },
    "summarizer": {
        "enabled": True,
        "engine": "local",  # local, claude, openai
        "max_input_length": 500,
        "target_length": 150,
        "personality": "jarvis",  # jarvis, neutral
        "language": "en",  # en, zh-Hant
    },
    "cli": {
        "adapter": "auto",  # auto, mcp, claude-code, gemini, codex
    },
    "ui": {
        "theme": "dark",
    },
}


def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Load configuration from file, merging with defaults."""
    ensure_config_dir()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                user_config = json.load(f)
            return _deep_merge(DEFAULT_CONFIG.copy(), user_config)
        except (json.JSONDecodeError, IOError):
            pass

    return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> bool:
    """Save configuration to file."""
    ensure_config_dir()

    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def get_setting(section: str, key: str, default: Any = None) -> Any:
    """Get a specific setting from configuration."""
    config = load_config()
    return config.get(section, {}).get(key, default)


def set_setting(section: str, key: str, value: Any) -> bool:
    """Set a specific setting in configuration."""
    config = load_config()
    if section not in config:
        config[section] = {}
    config[section][key] = value
    return save_config(config)


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional prefix."""
    # Try with prefix first
    prefixed = f"{ENV_PREFIX}{name}"
    value = os.environ.get(prefixed)
    if value:
        return value

    # Try without prefix
    return os.environ.get(name, default)


def get_env_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable setting (alias for get_env)."""
    return get_env(name, default)


def set_env_setting(name: str, value: str) -> None:
    """Set environment variable with prefix."""
    prefixed = f"{ENV_PREFIX}{name}"
    os.environ[prefixed] = value


def get_api_key(service: str) -> Optional[str]:
    """
    Get API key for a service.

    Checks in order:
    1. Environment variable: SPEECH_MCP_ECHO_{SERVICE}_API_KEY
    2. Environment variable: {SERVICE}_API_KEY
    3. Config file (if encrypted storage is enabled)
    """
    # Service-specific environment variable names
    env_names = {
        "openai": ["OPENAI_API_KEY"],
        "google": ["GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "elevenlabs": ["ELEVENLABS_API_KEY"],
    }

    # Try prefixed version first
    prefixed_key = get_env(f"{service.upper()}_API_KEY")
    if prefixed_key:
        return prefixed_key

    # Try known environment variable names
    for env_name in env_names.get(service.lower(), []):
        value = os.environ.get(env_name)
        if value:
            return value

    # TODO: Add encrypted config storage support
    return None


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
