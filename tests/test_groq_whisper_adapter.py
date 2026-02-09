"""
Unit tests for Groq Whisper API adapter.

Tests cover:
- Initialization with API key handling
- Transcription with different parameters
- API error handling
- Language handling
- Model listing
"""

import os
import pytest
import tempfile
from unittest.mock import Mock, MagicMock, patch
from speech_mcp_echo.stt_adapters.groq_whisper_adapter import GroqWhisperSTT, GROQ_BASE_URL

# Check if openai package is available (Groq adapter uses it)
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class TestGroqWhisperInitialization:
    """Test adapter initialization."""

    def test_init_default_settings(self, mock_api_keys):
        """Initialize with default settings."""
        stt = GroqWhisperSTT()

        assert stt.model == "whisper-large-v3-turbo"
        assert stt.language == "en"
        assert stt.is_initialized is True
        assert stt.api_key is not None

    def test_init_custom_settings(self, mock_api_keys):
        """Initialize with custom settings."""
        stt = GroqWhisperSTT(
            model="whisper-large-v3",
            language="zh"
        )

        assert stt.model == "whisper-large-v3"
        assert stt.language == "zh"
        assert stt.is_initialized is True

    def test_init_without_api_key(self, clean_env):
        """Initialize without API key should fail gracefully."""
        stt = GroqWhisperSTT()

        assert stt.is_initialized is False
        assert stt.api_key is None

    def test_init_with_api_key_env_var(self, mock_api_keys):
        """Initialize with API key from environment."""
        stt = GroqWhisperSTT()

        assert stt.is_initialized is True
        assert stt.api_key == mock_api_keys["groq"]

    def test_init_uses_get_api_key(self, mock_api_keys):
        """Initialization should use config.get_api_key."""
        with patch('speech_mcp_echo.stt_adapters.groq_whisper_adapter.get_api_key') as mock_get_key:
            mock_get_key.return_value = "gsk-test-key-123"

            stt = GroqWhisperSTT()

            mock_get_key.assert_called_once_with("groq")
            assert stt.api_key == "gsk-test-key-123"

    def test_init_creates_audio_processor_as_none(self, mock_api_keys):
        """Audio processor should be lazily initialized."""
        stt = GroqWhisperSTT()

        assert stt._audio_processor is None


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestGroqWhisperTranscription:
    """Test transcription functionality."""

    def test_transcribe_success(self, sample_audio_file, mock_api_keys):
        """Transcribe audio file successfully."""
        stt = GroqWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "This is a test transcription from Groq."

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "This is a test transcription from Groq."
            mock_client.audio.transcriptions.create.assert_called_once()

    def test_transcribe_uses_groq_base_url(self, sample_audio_file, mock_api_keys):
        """Transcribe should use Groq's base URL."""
        stt = GroqWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stt.transcribe(str(sample_audio_file))

            mock_openai.assert_called_once_with(
                api_key=mock_api_keys["groq"],
                base_url=GROQ_BASE_URL,
            )

    def test_transcribe_without_api_key(self, sample_audio_file, clean_env):
        """Transcribe should fail without API key."""
        stt = GroqWhisperSTT()

        with pytest.raises(RuntimeError, match="Groq API key not configured"):
            stt.transcribe(str(sample_audio_file))

    def test_transcribe_passes_correct_model(self, sample_audio_file, mock_api_keys):
        """Transcribe should pass correct model to API."""
        stt = GroqWhisperSTT(model="whisper-large-v3")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stt.transcribe(str(sample_audio_file))

            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['model'] == "whisper-large-v3"

    def test_transcribe_with_language_en(self, sample_audio_file, mock_api_keys):
        """Transcribe English audio with language hint."""
        stt = GroqWhisperSTT(language="en")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello world"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "Hello world"
            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['language'] == "en"

    def test_transcribe_with_language_auto(self, sample_audio_file, mock_api_keys):
        """Transcribe with auto language detection."""
        stt = GroqWhisperSTT(language="auto")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Auto detected"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stt.transcribe(str(sample_audio_file))

            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['language'] is None

    def test_transcribe_chinese(self, sample_audio_file, mock_api_keys):
        """Transcribe Chinese audio."""
        stt = GroqWhisperSTT(language="zh")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "你好世界"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "你好世界"


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestGroqWhisperListen:
    """Test listen functionality."""

    def test_listen_success(self, mock_api_keys):
        """Listen and transcribe successfully."""
        stt = GroqWhisperSTT()

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:
            mock_record.return_value = "/tmp/test.wav"
            mock_transcribe.return_value = "Listened text"

            result = stt.listen()

            assert result == "Listened text"
            mock_transcribe.assert_called_once_with("/tmp/test.wav")

    def test_listen_returns_empty_on_timeout(self, mock_api_keys):
        """Listen should return empty string on recording timeout."""
        stt = GroqWhisperSTT()

        with patch.object(stt, '_record_audio') as mock_record:
            mock_record.return_value = None

            result = stt.listen()

            assert result == ""

    def test_listen_without_api_key(self, clean_env):
        """Listen should fail without API key."""
        stt = GroqWhisperSTT()

        with pytest.raises(RuntimeError, match="Groq API key not configured"):
            stt.listen()

    def test_listen_cleans_up_temp_file(self, mock_api_keys):
        """Listen should clean up temporary audio file."""
        stt = GroqWhisperSTT()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:
            mock_record.return_value = temp_path
            mock_transcribe.return_value = "Test"

            stt.listen()

            assert not os.path.exists(temp_path)

    def test_listen_cleans_up_on_error(self, mock_api_keys):
        """Temp file should be cleaned up even on transcription error."""
        stt = GroqWhisperSTT()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:
            mock_record.return_value = temp_path
            mock_transcribe.side_effect = Exception("Transcription error")

            with pytest.raises(Exception):
                stt.listen()

            assert not os.path.exists(temp_path)

    def test_listen_passes_timeout(self, mock_api_keys):
        """Listen should pass timeout to record_audio."""
        stt = GroqWhisperSTT()

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:
            mock_record.return_value = "/tmp/test.wav"
            mock_transcribe.return_value = "Test"

            stt.listen(timeout=30)

            mock_record.assert_called_once_with(timeout=30)


class TestGroqWhisperAPIErrors:
    """Test API error handling."""

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_network_error(self, sample_audio_file, mock_api_keys):
        """Handle network connection error."""
        stt = GroqWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create.side_effect = ConnectionError("Network error")
            mock_openai.return_value = mock_client

            with pytest.raises(ConnectionError):
                stt.transcribe(str(sample_audio_file))

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_nonexistent_file(self, mock_api_keys):
        """Handle non-existent file."""
        stt = GroqWhisperSTT()

        with pytest.raises((FileNotFoundError, OSError)):
            stt.transcribe("/nonexistent/file.wav")


class TestGroqWhisperModels:
    """Test model management."""

    def test_get_available_models(self, mock_api_keys):
        """Get list of available models."""
        stt = GroqWhisperSTT()

        models = stt.get_available_models()

        assert isinstance(models, list)
        assert "whisper-large-v3-turbo" in models
        assert "whisper-large-v3" in models
        assert "distil-whisper-large-v3-en" in models

    def test_default_model_is_turbo(self, mock_api_keys):
        """Default model should be whisper-large-v3-turbo."""
        stt = GroqWhisperSTT()

        assert stt.model == "whisper-large-v3-turbo"


class TestGroqWhisperRecordAudio:
    """Test audio recording delegation."""

    def test_record_audio_creates_audio_processor(self, mock_api_keys):
        """_record_audio should lazily create AudioProcessor."""
        stt = GroqWhisperSTT()

        with patch('speech_mcp_echo.audio_processor.AudioProcessor') as mock_ap_class:
            mock_ap = MagicMock()
            mock_ap.record_until_silence.return_value = "/tmp/test.wav"
            mock_ap_class.return_value = mock_ap

            stt._record_audio(timeout=30)

            mock_ap_class.assert_called_once()
            mock_ap.record_until_silence.assert_called_once_with(timeout=30)

    def test_record_audio_reuses_audio_processor(self, mock_api_keys):
        """_record_audio should reuse existing AudioProcessor."""
        stt = GroqWhisperSTT()
        mock_ap = MagicMock()
        mock_ap.record_until_silence.return_value = "/tmp/test.wav"
        stt._audio_processor = mock_ap

        stt._record_audio(timeout=30)

        mock_ap.record_until_silence.assert_called_once_with(timeout=30)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
