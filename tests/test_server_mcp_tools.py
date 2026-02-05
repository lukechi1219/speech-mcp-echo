"""
Comprehensive tests for MCP server tools.

Tests all 9 MCP tools provided by server.py:

Original (Blocking) Tools:
1. start_conversation
2. voice_listen
3. voice_speak
4. voice_reply
5. voice_config
6. voice_status

New (Non-blocking Start/Poll) Tools:
7. start_listening
8. check_listening
9. cancel_listening

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


@pytest.fixture
def reset_listening_sessions():
    """Reset listening sessions between tests."""
    from speech_mcp_echo import server
    with server._session_lock:
        server._listening_sessions.clear()
    yield
    with server._session_lock:
        server._listening_sessions.clear()


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
# Test start_listening (Start/Poll Mode - Non-blocking)
# =============================================================================

class TestStartListening:
    """Tests for start_listening MCP tool (non-blocking background listening)."""

    def test_start_listening_returns_session_id(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test start_listening returns a session ID immediately."""
        from speech_mcp_echo.server import start_listening

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            assert "Session ID:" in result
            assert "check_listening" in result

    def test_start_listening_creates_session(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test start_listening creates a session in storage."""
        from speech_mcp_echo.server import start_listening, _listening_sessions

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            # Extract session ID from result
            import re
            match = re.search(r"Session ID: (\w+)", result)
            assert match is not None
            session_id = match.group(1)

            # Session should exist
            assert session_id in _listening_sessions

    def test_start_listening_with_custom_retry_count(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test start_listening with custom silence retry count."""
        from speech_mcp_echo.server import start_listening, _listening_sessions

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening(silence_retry_count=5)

            assert "Max retries on silence: 5" in result

    def test_start_listening_uses_config_default_retry(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test start_listening uses config default for silence retry count."""
        from speech_mcp_echo.server import start_listening
        from speech_mcp_echo.config import set_setting

        set_setting("stt", "silence_retry_count", 3)

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            assert "Max retries on silence: 3" in result

    def test_start_listening_is_non_blocking(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test start_listening returns immediately without blocking."""
        from speech_mcp_echo.server import start_listening

        # Make listen block for a long time
        def slow_listen(timeout=None):
            time.sleep(10)
            return "Test"

        mock_voice_engine.listen.side_effect = slow_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            start_time = time.time()
            result = start_listening()
            elapsed = time.time() - start_time

            # Should return immediately (< 1 second)
            assert elapsed < 1.0
            assert "Session ID:" in result


# =============================================================================
# Test check_listening (Start/Poll Mode - Status Check)
# =============================================================================

class TestCheckListening:
    """Tests for check_listening MCP tool (poll for results)."""

    def test_check_listening_session_not_found(self, reset_listening_sessions):
        """Test check_listening with invalid session ID."""
        from speech_mcp_echo.server import check_listening

        result = check_listening("invalid123")

        assert "ERROR" in result
        assert "not found" in result

    def test_check_listening_status_listening(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test check_listening returns 'listening' status while active."""
        from speech_mcp_echo.server import start_listening, check_listening

        # Make listen block indefinitely
        def blocking_listen(timeout=None):
            time.sleep(100)
            return "Test"

        mock_voice_engine.listen.side_effect = blocking_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            import re
            match = re.search(r"Session ID: (\w+)", result)
            session_id = match.group(1)

            # Check immediately - should be listening
            time.sleep(0.1)  # Allow thread to start
            status = check_listening(session_id)

            assert "Status: listening" in status
            assert "attempt" in status

    def test_check_listening_status_completed(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test check_listening returns 'completed' status with result."""
        from speech_mcp_echo.server import start_listening, check_listening

        # Make listen return immediately
        mock_voice_engine.listen.return_value = "Hello from user"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            import re
            match = re.search(r"Session ID: (\w+)", result)
            session_id = match.group(1)

            # Wait for background thread to complete
            time.sleep(0.3)

            status = check_listening(session_id)

            assert "Status: completed" in status
            assert "User said: Hello from user" in status

    def test_check_listening_status_timeout(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test check_listening returns 'timeout' status when retries exhausted."""
        from speech_mcp_echo.server import start_listening, check_listening

        # Make listen return empty (silence timeout)
        mock_voice_engine.listen.return_value = ""

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('speech_mcp_echo.server._play_retry_prompt'):  # Skip beep
                result = start_listening(silence_retry_count=0)  # No retries

                import re
                match = re.search(r"Session ID: (\w+)", result)
                session_id = match.group(1)

                # Wait for background thread to complete
                time.sleep(0.5)

                status = check_listening(session_id)

                assert "Status: timeout" in status

    def test_check_listening_shows_retry_progress(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test check_listening shows retry progress."""
        from speech_mcp_echo.server import start_listening, check_listening, _listening_sessions

        # Make listen take some time
        call_count = [0]

        def slow_listen(timeout=None):
            call_count[0] += 1
            time.sleep(0.5)
            return ""  # Silence

        mock_voice_engine.listen.side_effect = slow_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            with patch('speech_mcp_echo.server._play_retry_prompt'):
                result = start_listening(silence_retry_count=3)

                import re
                match = re.search(r"Session ID: (\w+)", result)
                session_id = match.group(1)

                # Check after first attempt
                time.sleep(0.6)
                status = check_listening(session_id)

                # Should show attempt progress
                assert "attempt" in status


# =============================================================================
# Test cancel_listening (Start/Poll Mode - Cancellation)
# =============================================================================

class TestCancelListening:
    """Tests for cancel_listening MCP tool."""

    def test_cancel_listening_session_not_found(self, reset_listening_sessions):
        """Test cancel_listening with invalid session ID."""
        from speech_mcp_echo.server import cancel_listening

        result = cancel_listening("invalid123")

        assert "ERROR" in result
        assert "not found" in result

    def test_cancel_listening_active_session(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test cancel_listening cancels an active session."""
        from speech_mcp_echo.server import start_listening, cancel_listening, check_listening

        # Make listen block
        def blocking_listen(timeout=None):
            time.sleep(100)
            return "Test"

        mock_voice_engine.listen.side_effect = blocking_listen

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            import re
            match = re.search(r"Session ID: (\w+)", result)
            session_id = match.group(1)

            # Cancel the session
            time.sleep(0.1)
            cancel_result = cancel_listening(session_id)

            assert "cancelled" in cancel_result.lower()

            # Check status should show cancelled
            status = check_listening(session_id)
            assert "cancelled" in status.lower()

    def test_cancel_listening_already_completed(self, mock_voice_engine, reset_server_engine, reset_listening_sessions):
        """Test cancel_listening on already completed session."""
        from speech_mcp_echo.server import start_listening, cancel_listening

        # Make listen return immediately
        mock_voice_engine.listen.return_value = "Hello"

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            result = start_listening()

            import re
            match = re.search(r"Session ID: (\w+)", result)
            session_id = match.group(1)

            # Wait for completion
            time.sleep(0.3)

            # Try to cancel
            cancel_result = cancel_listening(session_id)

            assert "already finished" in cancel_result
            assert "completed" in cancel_result


# =============================================================================
# Test Background Listening Helper Functions
# =============================================================================

class TestBackgroundListeningHelpers:
    """Tests for background listening helper functions."""

    def test_cleanup_expired_sessions(self, reset_listening_sessions):
        """Test expired session cleanup."""
        from speech_mcp_echo.server import (
            _listening_sessions,
            _session_lock,
            _cleanup_expired_sessions,
            ListeningSession,
            _SESSION_TTL_SECONDS,
        )

        # Create an old session
        with _session_lock:
            old_session = ListeningSession(
                id="old123",
                status="completed",
                result="Test",
            )
            # Manually set old timestamp
            old_session.created_at = time.time() - _SESSION_TTL_SECONDS - 100
            _listening_sessions["old123"] = old_session

            # Create a new session
            new_session = ListeningSession(
                id="new456",
                status="completed",
                result="Test",
            )
            _listening_sessions["new456"] = new_session

        # Run cleanup
        removed = _cleanup_expired_sessions()

        assert removed == 1
        assert "old123" not in _listening_sessions
        assert "new456" in _listening_sessions

    def test_play_retry_prompt_silent(self):
        """Test silent retry prompt does nothing."""
        from speech_mcp_echo.server import _play_retry_prompt

        # Should not raise
        _play_retry_prompt("silent")

    def test_play_retry_prompt_beep_macos(self):
        """Test beep retry prompt on macOS."""
        from speech_mcp_echo.server import _play_retry_prompt

        with patch('speech_mcp_echo.server.sys.platform', 'darwin'):
            with patch('speech_mcp_echo.server.subprocess.Popen') as mock_popen:
                _play_retry_prompt("beep")

                mock_popen.assert_called_once()
                args = mock_popen.call_args[0][0]
                assert "afplay" in args
                assert "Tink.aiff" in args[1]

    def test_play_retry_prompt_voice(self, mock_voice_engine, reset_server_engine):
        """Test voice retry prompt uses TTS."""
        from speech_mcp_echo.server import _play_retry_prompt

        with patch('speech_mcp_echo.server.get_engine', return_value=mock_voice_engine):
            _play_retry_prompt("voice")

            mock_voice_engine.speak.assert_called_once()
            args, kwargs = mock_voice_engine.speak.call_args
            assert "listening" in args[0].lower() or kwargs.get('summarize') is False


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
