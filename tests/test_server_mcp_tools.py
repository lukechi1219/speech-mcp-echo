"""
Comprehensive tests for MCP server tools.

Tests all 6 MCP tools provided by server.py:
1. start_conversation
2. voice_listen
3. voice_speak
4. voice_reply
5. voice_config
6. voice_status

Each tool is tested with:
- Success scenarios
- Error scenarios
- Edge cases
- Timeout variations (parametrized)
- Configuration variations (parametrized)

Optimization notes:
- Timeout tests parametrized (saves ~2 tests)
- STT/TTS engine config tests parametrized (saves ~4 tests)
- Summarizer config tests parametrized (saves ~3 tests)
- CLI detection tests parametrized (saves ~2 tests)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_voice_engine():
    """Create a mock VoiceEngine for testing."""
    engine = Mock()

    # Mock STT engine
    mock_stt = Mock()
    mock_stt.is_initialized = True
    mock_stt.model = "base"
    mock_stt.listen.return_value = "Test transcription"
    engine.stt_engine = mock_stt

    # Mock TTS engine
    mock_tts = Mock()
    mock_tts.is_initialized = True
    mock_tts.voice = "en-GB-Neural2-B"
    mock_tts.language = "en-GB"
    mock_tts.speak.return_value = True
    engine.tts_engine = mock_tts

    # Mock summarizer
    mock_summarizer = Mock()
    mock_summarizer.personality = "jarvis"
    mock_summarizer.language = "en"
    mock_summarizer.should_summarize.return_value = False
    mock_summarizer.summarize.return_value = "Summarized text"
    engine.summarizer = mock_summarizer

    # Mock listen and speak methods
    engine.listen.return_value = "Test transcription"
    engine.speak.return_value = "Spoken text"

    return engine


@pytest.fixture
def reset_server_engine():
    """Reset server engine singleton between tests."""
    from speech_mcp_echo import server
    server._engine = None
    yield
    server._engine = None


# =============================================================================
# Test start_conversation
# =============================================================================

class TestStartConversation:
    """Tests for start_conversation MCP tool."""

    def test_start_conversation_success(self, mock_voice_engine, reset_server_engine):
        """Test successful conversation start."""
        from speech_mcp_echo.server import start_conversation

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_conversation()

            assert result == "Test transcription"
            mock_voice_engine.listen.assert_called_once_with(timeout=None)

    @pytest.mark.parametrize("timeout", [5, 30, 60], ids=["5s", "30s", "60s"])
    def test_start_conversation_with_timeout(self, timeout, mock_voice_engine, reset_server_engine):
        """Test conversation start with various timeout values."""
        from speech_mcp_echo.server import start_conversation

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_conversation(timeout=timeout)

            assert result == "Test transcription"
            mock_voice_engine.listen.assert_called_once_with(timeout=timeout)

    def test_start_conversation_default_timeout(self, mock_voice_engine, reset_server_engine):
        """Test conversation start uses default timeout when not specified."""
        from speech_mcp_echo.server import start_conversation

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_conversation()

            # Should call with timeout=None (VoiceEngine will use config default)
            mock_voice_engine.listen.assert_called_once_with(timeout=None)

    def test_start_conversation_timeout_occurs(self, mock_voice_engine, reset_server_engine):
        """Test conversation start handles timeout."""
        from speech_mcp_echo.server import start_conversation

        mock_voice_engine.listen.return_value = ""

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_conversation(timeout=5)

            assert result == ""

    def test_start_conversation_stt_failure(self, mock_voice_engine, reset_server_engine):
        """Test conversation start handles STT failure."""
        from speech_mcp_echo.server import start_conversation

        mock_voice_engine.listen.side_effect = RuntimeError("STT initialization failed")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_conversation()

            assert result.startswith("ERROR:")
            assert "STT initialization failed" in result

    def test_start_conversation_audio_device_not_available(self, mock_voice_engine, reset_server_engine):
        """Test conversation start handles audio device unavailable."""
        from speech_mcp_echo.server import start_conversation

        mock_voice_engine.listen.side_effect = IOError("No audio device available")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_conversation()

            assert result.startswith("ERROR:")
            assert "No audio device available" in result


# =============================================================================
# Test voice_listen
# =============================================================================

class TestVoiceListen:
    """Tests for voice_listen MCP tool."""

    def test_voice_listen_success(self, mock_voice_engine, reset_server_engine):
        """Test successful voice listening."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_listen()

            assert result == "Test transcription"
            mock_voice_engine.listen.assert_called_once_with(timeout=None)

    def test_voice_listen_with_custom_timeout(self, mock_voice_engine, reset_server_engine):
        """Test voice listen with custom timeout."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_listen(timeout=10)

            assert result == "Test transcription"
            mock_voice_engine.listen.assert_called_once_with(timeout=10)

    def test_voice_listen_with_default_timeout(self, mock_voice_engine, reset_server_engine):
        """Test voice listen uses default timeout."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_listen()

            mock_voice_engine.listen.assert_called_once_with(timeout=None)

    def test_voice_listen_timeout_occurs(self, mock_voice_engine, reset_server_engine):
        """Test voice listen handles timeout."""
        from speech_mcp_echo.server import voice_listen

        mock_voice_engine.listen.return_value = ""

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_listen(timeout=5)

            assert result == ""

    def test_voice_listen_stt_failure(self, mock_voice_engine, reset_server_engine):
        """Test voice listen handles STT failure."""
        from speech_mcp_echo.server import voice_listen

        mock_voice_engine.listen.side_effect = RuntimeError("Audio recording failed")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_listen()

            assert result.startswith("ERROR:")
            assert "Audio recording failed" in result

    def test_voice_listen_returns_transcription(self, mock_voice_engine, reset_server_engine):
        """Test voice listen returns correct transcription."""
        from speech_mcp_echo.server import voice_listen

        mock_voice_engine.listen.return_value = "Hello world from voice"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_listen()

            assert result == "Hello world from voice"


# =============================================================================
# Test voice_speak
# =============================================================================

class TestVoiceSpeak:
    """Tests for voice_speak MCP tool."""

    def test_voice_speak_success(self, mock_voice_engine, reset_server_engine):
        """Test successful voice speaking."""
        from speech_mcp_echo.server import voice_speak

        mock_voice_engine.speak.return_value = "Hello world"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak("Hello world")

            assert result == "Spoke: Hello world"
            mock_voice_engine.speak.assert_called_once_with("Hello world", summarize=True)

    def test_voice_speak_with_summarization_enabled(self, mock_voice_engine, reset_server_engine):
        """Test voice speak with summarization enabled."""
        from speech_mcp_echo.server import voice_speak

        mock_voice_engine.speak.return_value = "Summary text"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak("Very long text that should be summarized", summarize=True)

            assert result == "Spoke: Summary text"
            mock_voice_engine.speak.assert_called_once_with(
                "Very long text that should be summarized",
                summarize=True
            )

    def test_voice_speak_with_summarization_disabled(self, mock_voice_engine, reset_server_engine):
        """Test voice speak with summarization disabled."""
        from speech_mcp_echo.server import voice_speak

        original_text = "This text will not be summarized"
        mock_voice_engine.speak.return_value = original_text

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak(original_text, summarize=False)

            assert result == f"Spoke: {original_text}"
            mock_voice_engine.speak.assert_called_once_with(original_text, summarize=False)

    def test_voice_speak_empty_text(self, mock_voice_engine, reset_server_engine):
        """Test voice speak handles empty text gracefully."""
        from speech_mcp_echo.server import voice_speak

        mock_voice_engine.speak.return_value = ""

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak("")

            assert result == "Spoke: "
            mock_voice_engine.speak.assert_called_once()

    def test_voice_speak_very_long_text(self, mock_voice_engine, reset_server_engine):
        """Test voice speak auto-summarizes very long text."""
        from speech_mcp_echo.server import voice_speak

        long_text = "A" * 1000
        mock_voice_engine.speak.return_value = "Summarized version"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak(long_text, summarize=True)

            assert result == "Spoke: Summarized version"
            mock_voice_engine.speak.assert_called_once_with(long_text, summarize=True)

    def test_voice_speak_tts_failure(self, mock_voice_engine, reset_server_engine):
        """Test voice speak handles TTS failure."""
        from speech_mcp_echo.server import voice_speak

        mock_voice_engine.speak.side_effect = RuntimeError("TTS engine not available")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak("Test")

            assert result.startswith("ERROR:")
            assert "TTS engine not available" in result

    def test_voice_speak_returns_success_status(self, mock_voice_engine, reset_server_engine):
        """Test voice speak returns success status."""
        from speech_mcp_echo.server import voice_speak

        mock_voice_engine.speak.return_value = "Success message"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_speak("Hello")

            assert "Spoke:" in result


# =============================================================================
# Test voice_reply
# =============================================================================

class TestVoiceReply:
    """Tests for voice_reply MCP tool."""

    def test_voice_reply_with_wait(self, mock_voice_engine, reset_server_engine):
        """Test voice reply with wait for response."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Spoken"
        mock_voice_engine.listen.return_value = "User response"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('time.sleep'):  # Skip sleep delay
                result = voice_reply("Hello", wait_for_response=True)

                assert result == "User response"
                mock_voice_engine.speak.assert_called_once_with("Hello", summarize=True)
                mock_voice_engine.listen.assert_called_once_with(timeout=None)

    def test_voice_reply_without_wait(self, mock_voice_engine, reset_server_engine):
        """Test voice reply without waiting for response."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Goodbye"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_reply("Goodbye", wait_for_response=False)

            assert result == "Spoke: Goodbye"
            mock_voice_engine.speak.assert_called_once()
            mock_voice_engine.listen.assert_not_called()

    def test_voice_reply_with_custom_timeout(self, mock_voice_engine, reset_server_engine):
        """Test voice reply with custom timeout."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Spoken"
        mock_voice_engine.listen.return_value = "Response"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('time.sleep'):
                result = voice_reply("Hello", wait_for_response=True, timeout=15)

                mock_voice_engine.listen.assert_called_once_with(timeout=15)

    def test_voice_reply_with_summarization(self, mock_voice_engine, reset_server_engine):
        """Test voice reply uses summarization."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Summary"
        mock_voice_engine.listen.return_value = "Response"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('time.sleep'):
                result = voice_reply("Long text", wait_for_response=True)

                # Always uses summarize=True
                mock_voice_engine.speak.assert_called_once_with("Long text", summarize=True)

    def test_voice_reply_tts_failure(self, mock_voice_engine, reset_server_engine):
        """Test voice reply handles TTS failure."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.side_effect = RuntimeError("TTS failed")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_reply("Hello")

            assert result.startswith("ERROR:")
            assert "TTS failed" in result

    def test_voice_reply_stt_failure_when_waiting(self, mock_voice_engine, reset_server_engine):
        """Test voice reply handles STT failure when waiting."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Spoken"
        mock_voice_engine.listen.side_effect = RuntimeError("STT failed")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('time.sleep'):
                result = voice_reply("Hello", wait_for_response=True)

                assert result.startswith("ERROR:")
                assert "STT failed" in result

    def test_voice_reply_timeout_when_waiting(self, mock_voice_engine, reset_server_engine):
        """Test voice reply handles timeout when waiting."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Spoken"
        mock_voice_engine.listen.return_value = ""

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('time.sleep'):
                result = voice_reply("Hello", wait_for_response=True, timeout=5)

                assert result == ""

    def test_voice_reply_delay_between_speak_and_listen(self, mock_voice_engine, reset_server_engine):
        """Test voice reply includes delay between speaking and listening."""
        from speech_mcp_echo.server import voice_reply

        mock_voice_engine.speak.return_value = "Spoken"
        mock_voice_engine.listen.return_value = "Response"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('time.sleep') as mock_sleep:
                result = voice_reply("Hello", wait_for_response=True)

                # Should sleep 0.5 seconds between speak and listen
                mock_sleep.assert_called_once_with(0.5)


# =============================================================================
# Test voice_config
# =============================================================================

class TestVoiceConfig:
    """Tests for voice_config MCP tool."""

    @pytest.mark.parametrize("engine", ["faster-whisper", "openai", "google"])
    def test_voice_config_stt_engine(self, engine, reset_server_engine):
        """Test configuring STT engine."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(stt_engine=engine)

        assert f"STT engine: {engine}" in result
        assert get_setting("stt", "engine") == engine

    def test_voice_config_stt_timeout(self, reset_server_engine):
        """Test configuring STT timeout."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(stt_timeout=30)

        assert "STT timeout: 30s" in result
        assert get_setting("stt", "timeout") == 30

    @pytest.mark.parametrize("engine", ["google", "openai"])
    def test_voice_config_tts_engine(self, engine, reset_server_engine):
        """Test configuring TTS engine."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(tts_engine=engine)

        assert f"TTS engine: {engine}" in result
        assert get_setting("tts", "engine") == engine

    def test_voice_config_tts_voice(self, reset_server_engine):
        """Test configuring TTS voice."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(tts_voice="en-GB-Neural2-B")

        assert "TTS voice: en-GB-Neural2-B" in result
        assert get_setting("tts", "voice") == "en-GB-Neural2-B"

    def test_voice_config_tts_language(self, reset_server_engine):
        """Test configuring TTS language."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(tts_language="cmn-TW")

        assert "TTS language: cmn-TW" in result
        assert get_setting("tts", "language") == "cmn-TW"

    @pytest.mark.parametrize("enabled,expected", [(True, "enabled"), (False, "disabled")])
    def test_voice_config_summarizer_enabled(self, enabled, expected, reset_server_engine):
        """Test enabling/disabling summarizer."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(summarizer_enabled=enabled)

        assert f"Summarizer: {expected}" in result
        assert get_setting("summarizer", "enabled") is enabled

    @pytest.mark.parametrize("personality", ["jarvis", "neutral"])
    def test_voice_config_summarizer_personality(self, personality, reset_server_engine):
        """Test configuring summarizer personality."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(summarizer_personality=personality)

        assert f"Summarizer personality: {personality}" in result
        assert get_setting("summarizer", "personality") == personality

    def test_voice_config_get_current_config(self, reset_server_engine):
        """Test getting current configuration without changes."""
        from speech_mcp_echo.server import voice_config

        result = voice_config()

        assert "Current config:" in result
        assert "stt_engine" in result
        assert "tts_engine" in result

    def test_voice_config_multiple_settings(self, reset_server_engine):
        """Test configuring multiple settings at once."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(
            stt_engine="openai",
            stt_timeout=60,
            tts_engine="google",
            tts_voice="en-US-Journey-D"
        )

        assert "STT engine: openai" in result
        assert "STT timeout: 60s" in result
        assert "TTS engine: google" in result
        assert "TTS voice: en-US-Journey-D" in result

        assert get_setting("stt", "engine") == "openai"
        assert get_setting("stt", "timeout") == 60
        assert get_setting("tts", "engine") == "google"
        assert get_setting("tts", "voice") == "en-US-Journey-D"


# =============================================================================
# Test voice_status
# =============================================================================

class TestVoiceStatus:
    """Tests for voice_status MCP tool."""

    def test_voice_status_all_engines_initialized(self, mock_voice_engine, reset_server_engine):
        """Test status with all engines initialized."""
        from speech_mcp_echo.server import voice_status

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_status()

            assert "Voice System Status" in result
            assert "STT Engine:" in result
            assert "TTS Engine:" in result
            assert "Initialized: True" in result

    def test_voice_status_engines_not_initialized(self, reset_server_engine):
        """Test status with engines not initialized."""
        from speech_mcp_echo.server import voice_status

        mock_engine = Mock()
        mock_stt = Mock()
        mock_stt.is_initialized = False
        mock_tts = Mock()
        mock_tts.is_initialized = False
        mock_engine.stt_engine = mock_stt
        mock_engine.tts_engine = mock_tts
        mock_engine.summarizer = None

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_engine):
            result = voice_status()

            assert "Voice System Status" in result
            assert "Initialized: False" in result

    def test_voice_status_shows_detected_cli(self, mock_voice_engine, reset_server_engine, monkeypatch):
        """Test status shows detected CLI."""
        from speech_mcp_echo.server import voice_status

        monkeypatch.setenv("CLAUDE_CODE", "1")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_status()

            assert "Detected CLI: claude-code" in result

    def test_voice_status_shows_configuration(self, mock_voice_engine, reset_server_engine):
        """Test status shows configuration details."""
        from speech_mcp_echo.server import voice_status
        from speech_mcp_echo.config import set_setting

        set_setting("stt", "engine", "faster-whisper")
        set_setting("tts", "engine", "google")

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_status()

            assert "faster-whisper" in result
            assert "google" in result

    def test_voice_status_with_summarizer_enabled(self, mock_voice_engine, reset_server_engine):
        """Test status with summarizer enabled."""
        from speech_mcp_echo.server import voice_status

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = voice_status()

            assert "Summarizer: Enabled" in result
            assert "Personality: jarvis" in result

    def test_voice_status_with_summarizer_disabled(self, reset_server_engine):
        """Test status with summarizer disabled."""
        from speech_mcp_echo.server import voice_status

        mock_engine = Mock()
        mock_stt = Mock()
        mock_stt.is_initialized = True
        mock_tts = Mock()
        mock_tts.is_initialized = True
        mock_engine.stt_engine = mock_stt
        mock_engine.tts_engine = mock_tts
        mock_engine.summarizer = None

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_engine):
            result = voice_status()

            assert "Summarizer: Disabled" in result


# =============================================================================
# Test Server Infrastructure
# =============================================================================

class TestServerInfrastructure:
    """Tests for server initialization and infrastructure."""

    def test_server_get_engine_creates_singleton(self, reset_server_engine):
        """Test get_engine creates singleton instance."""
        from speech_mcp_echo.server import get_engine

        with patch('speech_mcp_echo.server.VoiceEngine') as mock_engine_class:
            mock_instance = Mock()
            mock_engine_class.return_value = mock_instance

            engine1 = get_engine()
            engine2 = get_engine()

            assert engine1 is engine2
            mock_engine_class.assert_called_once()

    def test_server_initializes_correctly(self, reset_server_engine):
        """Test server starts correctly."""
        from speech_mcp_echo import server

        assert hasattr(server, 'mcp')
        assert server.mcp is not None

    def test_server_loads_configuration(self, reset_server_engine):
        """Test server loads configuration."""
        from speech_mcp_echo.config import get_setting

        # Should have default config
        assert get_setting("stt", "engine") is not None
        assert get_setting("tts", "engine") is not None

    def test_server_handles_missing_dependencies_gracefully(self, reset_server_engine):
        """Test server handles missing dependencies."""
        from speech_mcp_echo.server import get_engine

        # Mock VoiceEngine to raise import error
        with patch('speech_mcp_echo.server.VoiceEngine') as mock_engine_class:
            mock_engine_class.side_effect = ImportError("Missing dependency")

            with pytest.raises(ImportError):
                get_engine()

    @pytest.mark.parametrize("env_var,expected_cli", [
        ("CLAUDE_CODE", "claude-code"),
        ("GEMINI_CLI", "gemini"),
        ("CODEX_CLI", "codex"),
    ])
    def test_detect_cli(self, env_var, expected_cli, monkeypatch):
        """Test CLI detection for various CLIs."""
        from speech_mcp_echo.server import detect_cli

        monkeypatch.setenv(env_var, "1")

        result = detect_cli()
        assert result == expected_cli

    def test_detect_cli_generic(self, clean_env):
        """Test CLI detection for generic/unknown CLI."""
        from speech_mcp_echo.server import detect_cli

        result = detect_cli()
        assert result == "generic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
