"""
Unit tests for VoiceEngine (orchestrates STT, TTS, summarization).

Run with:
    cd speech-mcp-echo
    pytest tests/test_voice_engine.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from speech_mcp_echo.core.voice_engine import VoiceEngine


# =============================================================================
# Test Initialization & Configuration
# =============================================================================


class TestVoiceEngineInitialization:
    """Test VoiceEngine initialization."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    def test_init_with_default_config(self, mock_load_config):
        """Should initialize with default configuration."""
        mock_load_config.return_value = {
            "stt": {"engine": "faster-whisper", "timeout": 45},
            "tts": {"engine": "google"},
            "summarizer": {"enabled": True},
        }

        engine = VoiceEngine()

        assert engine.config is not None
        assert engine._stt_engine is None  # Lazy loaded
        assert engine._tts_engine is None  # Lazy loaded
        assert engine._summarizer is None  # Lazy loaded

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    def test_lazy_loading_stt_adapter(self, mock_load_config):
        """Should lazy-load STT adapter on first access."""
        mock_load_config.return_value = {
            "stt": {"engine": "faster-whisper", "model": "base", "device": "cpu"},
            "tts": {"engine": "google"},
            "summarizer": {"enabled": True},
        }

        with patch("speech_mcp_echo.core.voice_engine.get_setting") as mock_get_setting:
            mock_get_setting.side_effect = lambda cat, key, default=None: {
                ("stt", "engine"): "faster-whisper",
                ("stt", "model"): "base",
                ("stt", "device"): "cpu",
                ("stt", "compute_type"): "int8",
                ("stt", "language"): "auto",
            }.get((cat, key), default)

            with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT") as mock_stt:
                mock_stt_instance = MagicMock()
                mock_stt.return_value = mock_stt_instance

                engine = VoiceEngine()

                # STT should not be loaded yet
                assert engine._stt_engine is None

                # Access STT engine
                stt = engine.stt_engine

                # Should be loaded now
                assert engine._stt_engine is not None
                mock_stt.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    def test_lazy_loading_tts_adapter(self, mock_load_config):
        """Should lazy-load TTS adapter on first access."""
        mock_load_config.return_value = {
            "stt": {"engine": "faster-whisper"},
            "tts": {"engine": "google", "voice": "en-US-Journey-D", "language": "en-US"},
            "summarizer": {"enabled": True},
        }

        with patch("speech_mcp_echo.core.voice_engine.get_setting") as mock_get_setting:
            mock_get_setting.side_effect = lambda cat, key, default=None: {
                ("tts", "engine"): "google",
                ("tts", "voice"): "en-US-Journey-D",
                ("tts", "language"): "en-US",
            }.get((cat, key), default)

            with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS") as mock_tts:
                mock_tts_instance = MagicMock()
                mock_tts.return_value = mock_tts_instance

                engine = VoiceEngine()

                # TTS should not be loaded yet
                assert engine._tts_engine is None

                # Access TTS engine
                tts = engine.tts_engine

                # Should be loaded now
                assert engine._tts_engine is not None
                mock_tts.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    def test_lazy_loading_summarizer(self, mock_load_config):
        """Should lazy-load summarizer on first access."""
        mock_load_config.return_value = {
            "stt": {"engine": "faster-whisper"},
            "tts": {"engine": "google"},
            "summarizer": {"enabled": True, "engine": "local", "personality": "jarvis"},
        }

        with patch("speech_mcp_echo.core.voice_engine.get_setting") as mock_get_setting:
            mock_get_setting.side_effect = lambda cat, key, default=None: {
                ("summarizer", "enabled"): True,
                ("summarizer", "engine"): "local",
                ("summarizer", "max_input_length"): 500,
                ("summarizer", "target_length"): 150,
                ("summarizer", "personality"): "jarvis",
                ("summarizer", "language"): "en",
            }.get((cat, key), default)

            with patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer") as mock_summarizer:
                mock_summarizer_instance = MagicMock()
                mock_summarizer.return_value = mock_summarizer_instance

                engine = VoiceEngine()

                # Summarizer should not be loaded yet
                assert engine._summarizer is None

                # Access summarizer
                summ = engine.summarizer

                # Should be loaded now
                assert engine._summarizer is not None
                mock_summarizer.assert_called_once()


class TestVoiceEngineSTTEngineCreation:
    """Test STT engine creation."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT")
    def test_create_faster_whisper_engine(self, mock_stt, mock_get_setting, mock_load_config):
        """Should create faster-whisper STT engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt_instance = MagicMock()
        mock_stt.return_value = mock_stt_instance

        engine = VoiceEngine()
        stt = engine.stt_engine

        mock_stt.assert_called_once_with(
            model="base",
            device="cpu",
            compute_type="int8",
            language="auto",
        )

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.stt_adapters.openai_whisper_adapter.OpenAIWhisperSTT")
    def test_create_openai_whisper_engine(self, mock_stt, mock_get_setting, mock_load_config):
        """Should create OpenAI Whisper STT engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "openai",
        }.get((cat, key), default)

        mock_stt_instance = MagicMock()
        mock_stt.return_value = mock_stt_instance

        engine = VoiceEngine()
        stt = engine.stt_engine

        mock_stt.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.stt_adapters.google_speech_adapter.GoogleSpeechSTT")
    def test_create_google_speech_engine(self, mock_stt, mock_get_setting, mock_load_config):
        """Should create Google Speech STT engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "google",
        }.get((cat, key), default)

        mock_stt_instance = MagicMock()
        mock_stt.return_value = mock_stt_instance

        engine = VoiceEngine()
        stt = engine.stt_engine

        mock_stt.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_create_unknown_stt_engine_raises_error(self, mock_get_setting, mock_load_config):
        """Should raise error for unknown STT engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "unknown-engine",
        }.get((cat, key), default)

        engine = VoiceEngine()

        with pytest.raises(ValueError, match="Unknown STT engine"):
            _ = engine.stt_engine


class TestVoiceEngineTTSEngineCreation:
    """Test TTS engine creation."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS")
    def test_create_google_tts_engine(self, mock_tts, mock_get_setting, mock_load_config):
        """Should create Google Cloud TTS engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
        }.get((cat, key), default)

        mock_tts_instance = MagicMock()
        mock_tts.return_value = mock_tts_instance

        engine = VoiceEngine()
        tts = engine.tts_engine

        mock_tts.assert_called_once_with(
            voice="en-US-Journey-D",
            language="en-US",
        )

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.tts_adapters.openai_tts_adapter.OpenAITTS")
    def test_create_openai_tts_engine(self, mock_tts, mock_get_setting, mock_load_config):
        """Should create OpenAI TTS engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "openai",
            ("tts", "voice"): "alloy",
        }.get((cat, key), default)

        mock_tts_instance = MagicMock()
        mock_tts.return_value = mock_tts_instance

        engine = VoiceEngine()
        tts = engine.tts_engine

        mock_tts.assert_called_once_with(voice="alloy")

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_create_kokoro_tts_raises_error(self, mock_get_setting, mock_load_config):
        """Should raise error for Kokoro TTS (not available)."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "kokoro",
        }.get((cat, key), default)

        engine = VoiceEngine()

        with pytest.raises(ValueError, match="Kokoro TTS is not available"):
            _ = engine.tts_engine

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_create_pyttsx3_tts_raises_error(self, mock_get_setting, mock_load_config):
        """Should raise error for pyttsx3 TTS (not available)."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "pyttsx3",
        }.get((cat, key), default)

        engine = VoiceEngine()

        with pytest.raises(ValueError, match="pyttsx3 TTS is not available"):
            _ = engine.tts_engine

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_create_unknown_tts_engine_raises_error(self, mock_get_setting, mock_load_config):
        """Should raise error for unknown TTS engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "unknown-engine",
        }.get((cat, key), default)

        engine = VoiceEngine()

        with pytest.raises(ValueError, match="Unknown TTS engine"):
            _ = engine.tts_engine


class TestVoiceEngineSummarizerCreation:
    """Test summarizer creation."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer")
    def test_create_local_summarizer(self, mock_summ, mock_get_setting, mock_load_config):
        """Should create LocalSummarizer."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "local",
            ("summarizer", "max_input_length"): 500,
            ("summarizer", "target_length"): 150,
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "en",
        }.get((cat, key), default)

        mock_summ_instance = MagicMock()
        mock_summ.return_value = mock_summ_instance

        engine = VoiceEngine()
        summ = engine.summarizer

        mock_summ.assert_called_once_with(
            max_input_length=500,
            target_length=150,
            personality="jarvis",
            language="en",
        )

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    @patch("speech_mcp_echo.summarizer.llm_summarizer.LLMSummarizer")
    def test_create_llm_summarizer(self, mock_summ, mock_get_setting, mock_load_config):
        """Should create LLMSummarizer."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "llm",
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "en",
        }.get((cat, key), default)

        mock_summ_instance = MagicMock()
        mock_summ.return_value = mock_summ_instance

        engine = VoiceEngine()
        summ = engine.summarizer

        mock_summ.assert_called_once_with(
            personality="jarvis",
            language="en",
        )

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_summarizer_disabled(self, mock_get_setting, mock_load_config):
        """Should return None when summarizer is disabled."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        engine = VoiceEngine()
        summ = engine.summarizer

        assert summ is None

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_summarizer_unknown_engine_returns_none(self, mock_get_setting, mock_load_config):
        """Should return None for unknown summarizer engine."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "unknown",
        }.get((cat, key), default)

        engine = VoiceEngine()
        summ = engine.summarizer

        assert summ is None


# =============================================================================
# Test STT Operations
# =============================================================================


class TestVoiceEngineSTTOperations:
    """Test STT (speech-to-text) operations."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_listen_successfully(self, mock_get_setting, mock_load_config):
        """Should listen and return transcription."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.return_value = "Hello world"

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()
            result = engine.listen()

            assert result == "Hello world"
            mock_stt.listen.assert_called_once_with(timeout=45)

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_listen_with_custom_timeout(self, mock_get_setting, mock_load_config):
        """Should listen with custom timeout."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.return_value = "Custom timeout test"

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()
            result = engine.listen(timeout=30)

            assert result == "Custom timeout test"
            mock_stt.listen.assert_called_once_with(timeout=30)

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_listen_with_various_timeouts(self, mock_get_setting, mock_load_config):
        """Should handle different timeout values."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.return_value = "Test"

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()

            # Test various timeouts
            for timeout in [5, 30, 60]:
                result = engine.listen(timeout=timeout)
                assert result == "Test"

            # Check all calls used correct timeouts
            calls = mock_stt.listen.call_args_list
            assert calls[0] == call(timeout=5)
            assert calls[1] == call(timeout=30)
            assert calls[2] == call(timeout=60)

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_listen_handles_empty_audio(self, mock_get_setting, mock_load_config):
        """Should handle empty/silent audio."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.return_value = ""

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()
            result = engine.listen()

            assert result == ""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_listen_with_callbacks(self, mock_get_setting, mock_load_config):
        """Should call callbacks during listening."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.return_value = "Test"

        on_listening_start = Mock()
        on_listening_end = Mock()

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()
            engine.set_callbacks(
                on_listening_start=on_listening_start,
                on_listening_end=on_listening_end,
            )

            result = engine.listen()

            on_listening_start.assert_called_once()
            on_listening_end.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_multiple_consecutive_transcriptions(self, mock_get_setting, mock_load_config):
        """Should handle multiple consecutive listen calls."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.side_effect = ["First", "Second", "Third"]

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()

            assert engine.listen() == "First"
            assert engine.listen() == "Second"
            assert engine.listen() == "Third"


# =============================================================================
# Test TTS Operations
# =============================================================================


class TestVoiceEngineTTSOperations:
    """Test TTS (text-to-speech) operations."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_speak_text_successfully(self, mock_get_setting, mock_load_config):
        """Should speak text successfully."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()
            result = engine.speak("Hello world", summarize=False)

            assert result == "Hello world"
            mock_tts.speak.assert_called_once_with("Hello world")

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_speak_with_summarization_disabled(self, mock_get_setting, mock_load_config):
        """Should speak without summarization when disabled."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()
            long_text = "This is a long text. " * 50
            result = engine.speak(long_text, summarize=False)

            # Should speak full text (not summarized)
            assert result == long_text
            mock_tts.speak.assert_called_once_with(long_text)

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_speak_with_summarization_enabled(self, mock_get_setting, mock_load_config):
        """Should summarize long text before speaking."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "local",
            ("summarizer", "max_input_length"): 100,
            ("summarizer", "target_length"): 50,
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "en",
        }.get((cat, key), default)

        mock_tts = MagicMock()
        mock_summarizer = MagicMock()
        mock_summarizer.should_summarize.return_value = True
        mock_summarizer.summarize.return_value = "Summarized text"

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            with patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer", return_value=mock_summarizer):
                engine = VoiceEngine()
                long_text = "This is a very long text. " * 50
                result = engine.speak(long_text, summarize=True)

                # Should speak summarized text
                assert result == "Summarized text"
                mock_summarizer.should_summarize.assert_called_once_with(long_text)
                mock_summarizer.summarize.assert_called_once_with(long_text)
                mock_tts.speak.assert_called_once_with("Summarized text")

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_speak_empty_text(self, mock_get_setting, mock_load_config):
        """Should handle empty text gracefully."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()
            result = engine.speak("", summarize=False)

            assert result == ""
            mock_tts.speak.assert_called_once_with("")

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_speak_with_callbacks(self, mock_get_setting, mock_load_config):
        """Should call callbacks during speaking."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()
        on_speaking_start = Mock()
        on_speaking_end = Mock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()
            engine.set_callbacks(
                on_speaking_start=on_speaking_start,
                on_speaking_end=on_speaking_end,
            )

            engine.speak("Test", summarize=False)

            on_speaking_start.assert_called_once()
            on_speaking_end.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_multiple_consecutive_speeches(self, mock_get_setting, mock_load_config):
        """Should handle multiple consecutive speak calls."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()

            engine.speak("First", summarize=False)
            engine.speak("Second", summarize=False)
            engine.speak("Third", summarize=False)

            assert mock_tts.speak.call_count == 3


# =============================================================================
# Test Summarization Integration
# =============================================================================


class TestVoiceEngineSummarizationIntegration:
    """Test summarization integration in voice flow."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_summarize_before_speaking_when_enabled(self, mock_get_setting, mock_load_config):
        """Should summarize before speaking when enabled."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "local",
            ("summarizer", "max_input_length"): 100,
            ("summarizer", "target_length"): 50,
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "en",
        }.get((cat, key), default)

        mock_tts = MagicMock()
        mock_summarizer = MagicMock()
        mock_summarizer.should_summarize.return_value = True
        mock_summarizer.summarize.return_value = "Short summary"

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            with patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer", return_value=mock_summarizer):
                engine = VoiceEngine()
                long_text = "Long text " * 100
                result = engine.speak(long_text, summarize=True)

                assert result == "Short summary"
                mock_summarizer.summarize.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_skip_summarization_when_disabled(self, mock_get_setting, mock_load_config):
        """Should skip summarization when disabled."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()
            long_text = "Long text " * 100
            result = engine.speak(long_text, summarize=True)

            # Should speak full text (no summarizer available)
            assert result == long_text

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_pass_through_short_responses(self, mock_get_setting, mock_load_config):
        """Should pass through short responses without summarizing."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "local",
            ("summarizer", "max_input_length"): 500,
            ("summarizer", "target_length"): 150,
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "en",
        }.get((cat, key), default)

        mock_tts = MagicMock()
        mock_summarizer = MagicMock()
        mock_summarizer.should_summarize.return_value = False

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            with patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer", return_value=mock_summarizer):
                engine = VoiceEngine()
                short_text = "Short message"
                result = engine.speak(short_text, summarize=True)

                # Should not summarize
                assert result == short_text
                mock_summarizer.should_summarize.assert_called_once_with(short_text)
                mock_summarizer.summarize.assert_not_called()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_summarize_with_english_personality(self, mock_get_setting, mock_load_config):
        """Should use English JARVIS personality."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "local",
            ("summarizer", "max_input_length"): 100,
            ("summarizer", "target_length"): 50,
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "en",
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            with patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer") as mock_summ_class:
                engine = VoiceEngine()
                _ = engine.summarizer

                mock_summ_class.assert_called_once_with(
                    max_input_length=100,
                    target_length=50,
                    personality="jarvis",
                    language="en",
                )

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_summarize_with_chinese_personality(self, mock_get_setting, mock_load_config):
        """Should use Chinese JARVIS personality."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "cmn-TW-Standard-B",
            ("tts", "language"): "cmn-TW",
            ("summarizer", "enabled"): True,
            ("summarizer", "engine"): "local",
            ("summarizer", "max_input_length"): 100,
            ("summarizer", "target_length"): 50,
            ("summarizer", "personality"): "jarvis",
            ("summarizer", "language"): "zh-Hant",
        }.get((cat, key), default)

        mock_tts = MagicMock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            with patch("speech_mcp_echo.summarizer.local_summarizer.LocalSummarizer") as mock_summ_class:
                engine = VoiceEngine()
                _ = engine.summarizer

                mock_summ_class.assert_called_once_with(
                    max_input_length=100,
                    target_length=50,
                    personality="jarvis",
                    language="zh-Hant",
                )


# =============================================================================
# Test Callbacks
# =============================================================================


class TestVoiceEngineCallbacks:
    """Test callback functionality."""

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    def test_set_callbacks(self, mock_load_config):
        """Should set callbacks successfully."""
        mock_load_config.return_value = {}

        on_listening_start = Mock()
        on_listening_end = Mock()
        on_speaking_start = Mock()
        on_speaking_end = Mock()

        engine = VoiceEngine()
        engine.set_callbacks(
            on_listening_start=on_listening_start,
            on_listening_end=on_listening_end,
            on_speaking_start=on_speaking_start,
            on_speaking_end=on_speaking_end,
        )

        assert engine._on_listening_start == on_listening_start
        assert engine._on_listening_end == on_listening_end
        assert engine._on_speaking_start == on_speaking_start
        assert engine._on_speaking_end == on_speaking_end

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_callbacks_called_during_listen(self, mock_get_setting, mock_load_config):
        """Should call listening callbacks."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.return_value = "Test"

        on_listening_start = Mock()
        on_listening_end = Mock()

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()
            engine.set_callbacks(
                on_listening_start=on_listening_start,
                on_listening_end=on_listening_end,
            )

            engine.listen()

            on_listening_start.assert_called_once()
            on_listening_end.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_callbacks_called_during_speak(self, mock_get_setting, mock_load_config):
        """Should call speaking callbacks."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("tts", "engine"): "google",
            ("tts", "voice"): "en-US-Journey-D",
            ("tts", "language"): "en-US",
            ("summarizer", "enabled"): False,
        }.get((cat, key), default)

        mock_tts = MagicMock()

        on_speaking_start = Mock()
        on_speaking_end = Mock()

        with patch("speech_mcp_echo.tts_adapters.google_tts_adapter.GoogleCloudTTS", return_value=mock_tts):
            engine = VoiceEngine()
            engine.set_callbacks(
                on_speaking_start=on_speaking_start,
                on_speaking_end=on_speaking_end,
            )

            engine.speak("Test", summarize=False)

            on_speaking_start.assert_called_once()
            on_speaking_end.assert_called_once()

    @patch("speech_mcp_echo.core.voice_engine.load_config")
    @patch("speech_mcp_echo.core.voice_engine.get_setting")
    def test_callbacks_called_even_on_error(self, mock_get_setting, mock_load_config):
        """Should call end callbacks even if operation fails."""
        mock_load_config.return_value = {}
        mock_get_setting.side_effect = lambda cat, key, default=None: {
            ("stt", "engine"): "faster-whisper",
            ("stt", "timeout"): 45,
            ("stt", "model"): "base",
            ("stt", "device"): "cpu",
            ("stt", "compute_type"): "int8",
            ("stt", "language"): "auto",
        }.get((cat, key), default)

        mock_stt = MagicMock()
        mock_stt.listen.side_effect = Exception("Test error")

        on_listening_start = Mock()
        on_listening_end = Mock()

        with patch("speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT", return_value=mock_stt):
            engine = VoiceEngine()
            engine.set_callbacks(
                on_listening_start=on_listening_start,
                on_listening_end=on_listening_end,
            )

            with pytest.raises(Exception, match="Test error"):
                engine.listen()

            # Callbacks should still be called
            on_listening_start.assert_called_once()
            on_listening_end.assert_called_once()
