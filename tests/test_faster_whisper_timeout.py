"""
Unit tests for faster-whisper adapter timeout functionality.
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT


class TestFasterWhisperTimeout:
    """Test timeout functionality in faster-whisper adapter."""

    def test_listen_respects_timeout(self):
        """Test that listen() respects the timeout parameter."""
        stt = FasterWhisperSTT()

        # Mock _ensure_initialized to avoid loading actual model
        stt._ensure_initialized = Mock()
        stt._whisper_model = Mock()
        stt.is_initialized = True

        # Mock _record_audio to simulate timeout
        with patch.object(stt, '_record_audio') as mock_record:
            mock_record.return_value = None  # Simulate timeout

            start_time = time.time()
            result = stt.listen(timeout=2)
            elapsed = time.time() - start_time

            # Should return empty string on timeout
            assert result == ""

            # Should complete within timeout + small buffer
            assert elapsed < 3.0

            # Should have called _record_audio with timeout
            mock_record.assert_called_once_with(timeout=2)

    def test_listen_without_timeout(self):
        """Test that listen() works without timeout (backward compatibility)."""
        stt = FasterWhisperSTT()

        # Mock dependencies
        stt._ensure_initialized = Mock()
        stt._whisper_model = Mock()
        stt.is_initialized = True

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:

            mock_record.return_value = "/tmp/audio.wav"
            mock_transcribe.return_value = "Test transcription"

            result = stt.listen(timeout=None)

            # Should transcribe normally
            assert result == "Test transcription"
            mock_record.assert_called_once_with(timeout=None)

    def test_record_audio_timeout_returns_none(self):
        """Test that _record_audio returns None on timeout."""
        stt = FasterWhisperSTT()

        # Mock the AudioProcessor that _record_audio delegates to
        mock_audio_processor = MagicMock()
        mock_audio_processor.record_until_silence.return_value = None
        stt._audio_processor = mock_audio_processor

        result = stt._record_audio(timeout=1)

        # Should return None on timeout
        assert result is None

        # Should have called record_until_silence with timeout
        mock_audio_processor.record_until_silence.assert_called_once_with(timeout=1)

    def test_record_audio_completes_before_timeout(self):
        """Test that _record_audio returns path when completing before timeout."""
        stt = FasterWhisperSTT()

        # This would require mocking the entire PyAudio stack
        # For now, we test the timeout logic in integration tests
        # Unit test focuses on the timeout wrapper behavior
        pass

    def test_config_default_timeout(self):
        """Test that configuration provides default timeout."""
        from speech_mcp_echo.config import DEFAULT_CONFIG

        # Check the default in DEFAULT_CONFIG constant
        assert DEFAULT_CONFIG["stt"]["timeout"] == 45

    def test_voice_engine_uses_config_timeout(self):
        """Test that VoiceEngine uses configured timeout."""
        from speech_mcp_echo.core.voice_engine import VoiceEngine
        from speech_mcp_echo.config import set_setting

        # Set custom timeout
        set_setting("stt", "timeout", 30)

        engine = VoiceEngine()

        # Mock the STT engine
        mock_stt = Mock()
        mock_stt.listen.return_value = "Test transcription"
        engine._stt_engine = mock_stt

        # Call listen without timeout parameter
        result = engine.listen()

        # Should use configured timeout
        mock_stt.listen.assert_called_once_with(timeout=30)
        assert result == "Test transcription"

    def test_voice_engine_timeout_override(self):
        """Test that VoiceEngine allows timeout override."""
        from speech_mcp_echo.core.voice_engine import VoiceEngine

        engine = VoiceEngine()

        # Mock the STT engine
        mock_stt = Mock()
        mock_stt.listen.return_value = "Override test"
        engine._stt_engine = mock_stt

        # Call with explicit timeout
        result = engine.listen(timeout=60)

        # Should use provided timeout, not config
        mock_stt.listen.assert_called_once_with(timeout=60)
        assert result == "Override test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
