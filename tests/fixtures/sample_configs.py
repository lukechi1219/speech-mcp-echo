"""
Sample configuration variations for testing.

Provides different configuration scenarios to test:
- Different STT engines (faster-whisper, openai, google)
- Different TTS engines (google, openai)
- Different timeout values
- Summarizer enabled/disabled
- Language variations
"""

from typing import Dict, Any


# =============================================================================
# Default Configuration
# =============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "language": "auto",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "cmn-TW-Standard-B",
        "language": "cmn-TW",
        "speed": 1.0,
    },
    "summarizer": {
        "enabled": True,
        "engine": "local",
        "max_input_length": 500,
        "target_length": 150,
        "personality": "jarvis",
        "language": "en",
    },
    "cli": {
        "adapter": "auto",
    },
    "ui": {
        "theme": "dark",
    },
}


# =============================================================================
# STT Engine Variations
# =============================================================================

STT_FASTER_WHISPER_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "device": "cpu",
        "compute_type": "int8",
        "language": "auto",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
    },
}

STT_OPENAI_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "openai",
        "model": "whisper-1",
        "language": "en",
        "timeout": 30,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
    },
}

STT_GOOGLE_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "google",
        "model": "default",
        "language": "en-US",
        "timeout": 60,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
    },
}


# =============================================================================
# TTS Engine Variations
# =============================================================================

TTS_GOOGLE_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
        "speed": 1.0,
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
    },
}

TTS_OPENAI_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 45,
    },
    "tts": {
        "engine": "openai",
        "voice": "nova",
        "model": "tts-1",
        "speed": 1.0,
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
    },
}

TTS_OPENAI_HD_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 45,
    },
    "tts": {
        "engine": "openai",
        "voice": "alloy",
        "model": "tts-1-hd",
        "speed": 1.0,
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
    },
}


# =============================================================================
# Timeout Variations
# =============================================================================

TIMEOUT_5_SECONDS_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 5,  # Very short timeout
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
    },
}

TIMEOUT_30_SECONDS_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 30,  # Short timeout (good for Codex)
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
    },
}

TIMEOUT_60_SECONDS_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 60,  # Medium timeout
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
    },
}

TIMEOUT_120_SECONDS_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 120,  # Long timeout (good for Claude Code)
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
    },
}


# =============================================================================
# Summarizer Variations
# =============================================================================

SUMMARIZER_ENABLED_JARVIS_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
        "engine": "local",
        "personality": "jarvis",
        "language": "en",
        "max_input_length": 500,
        "target_length": 150,
    },
}

SUMMARIZER_ENABLED_NEUTRAL_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
        "engine": "local",
        "personality": "neutral",
        "language": "en",
        "max_input_length": 500,
        "target_length": 150,
    },
}

SUMMARIZER_DISABLED_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": False,
    },
}


# =============================================================================
# Language Variations
# =============================================================================

ENGLISH_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "language": "en",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "en-US-Journey-D",
        "language": "en-US",
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
        "language": "en",
    },
}

CHINESE_TRADITIONAL_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "language": "zh",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "cmn-TW-Standard-B",
        "language": "cmn-TW",
    },
    "summarizer": {
        "enabled": True,
        "personality": "jarvis",
        "language": "zh-Hant",
    },
}

JAPANESE_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
        "model": "base",
        "language": "ja",
        "timeout": 45,
    },
    "tts": {
        "engine": "google",
        "voice": "ja-JP-Standard-A",
        "language": "ja-JP",
    },
    "summarizer": {
        "enabled": True,
        "personality": "neutral",
        "language": "ja",
    },
}


# =============================================================================
# Minimal/Invalid Configurations
# =============================================================================

MINIMAL_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "faster-whisper",
    },
    "tts": {
        "engine": "google",
    },
}

EMPTY_CONFIG: Dict[str, Any] = {}

INVALID_ENGINE_CONFIG: Dict[str, Any] = {
    "stt": {
        "engine": "nonexistent-engine",
        "timeout": 45,
    },
    "tts": {
        "engine": "invalid-tts-engine",
    },
}


# =============================================================================
# Configuration Registry
# =============================================================================

ALL_CONFIGS: Dict[str, Dict[str, Any]] = {
    # Base
    "default": DEFAULT_CONFIG,
    "minimal": MINIMAL_CONFIG,
    "empty": EMPTY_CONFIG,
    "invalid_engine": INVALID_ENGINE_CONFIG,

    # STT variations
    "stt_faster_whisper": STT_FASTER_WHISPER_CONFIG,
    "stt_openai": STT_OPENAI_CONFIG,
    "stt_google": STT_GOOGLE_CONFIG,

    # TTS variations
    "tts_google": TTS_GOOGLE_CONFIG,
    "tts_openai": TTS_OPENAI_CONFIG,
    "tts_openai_hd": TTS_OPENAI_HD_CONFIG,

    # Timeout variations
    "timeout_5s": TIMEOUT_5_SECONDS_CONFIG,
    "timeout_30s": TIMEOUT_30_SECONDS_CONFIG,
    "timeout_60s": TIMEOUT_60_SECONDS_CONFIG,
    "timeout_120s": TIMEOUT_120_SECONDS_CONFIG,

    # Summarizer variations
    "summarizer_jarvis": SUMMARIZER_ENABLED_JARVIS_CONFIG,
    "summarizer_neutral": SUMMARIZER_ENABLED_NEUTRAL_CONFIG,
    "summarizer_disabled": SUMMARIZER_DISABLED_CONFIG,

    # Language variations
    "lang_english": ENGLISH_CONFIG,
    "lang_chinese": CHINESE_TRADITIONAL_CONFIG,
    "lang_japanese": JAPANESE_CONFIG,
}


def get_config(name: str) -> Dict[str, Any]:
    """
    Get a configuration by name.

    Args:
        name: Configuration name from ALL_CONFIGS

    Returns:
        Deep copy of the requested configuration

    Raises:
        KeyError: If configuration name not found
    """
    import copy

    if name not in ALL_CONFIGS:
        raise KeyError(f"Configuration '{name}' not found. Available: {list(ALL_CONFIGS.keys())}")

    return copy.deepcopy(ALL_CONFIGS[name])
