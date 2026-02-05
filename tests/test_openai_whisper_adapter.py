"""
Comprehensive unit tests for OpenAI Whisper API adapter.

Tests cover:
- Initialization with API key handling
- Transcription with different parameters
- API error handling (auth, rate limit, timeout, network)
- Language and response format handling
- File size limits and constraints
"""

import os
import pytest
import tempfile
import wave
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from speech_mcp_echo.stt_adapters.openai_whisper_adapter import OpenAIWhisperSTT

# Check if openai package is available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None


class TestOpenAIWhisperInitialization:
    """Test adapter initialization."""

    def test_init_default_settings(self, mock_api_keys):
        """Initialize with default settings."""
        stt = OpenAIWhisperSTT()

        assert stt.model == "whisper-1"
        assert stt.language == "en"
        assert stt.is_initialized is True
        assert stt.api_key is not None

    def test_init_custom_settings(self, mock_api_keys):
        """Initialize with custom settings."""
        stt = OpenAIWhisperSTT(
            model="whisper-1",
            language="zh"
        )

        assert stt.model == "whisper-1"
        assert stt.language == "zh"
        assert stt.is_initialized is True

    def test_init_without_api_key(self, clean_env):
        """Initialize without API key should fail gracefully."""
        stt = OpenAIWhisperSTT()

        assert stt.is_initialized is False
        assert stt.api_key is None

    def test_init_with_api_key_env_var(self, mock_api_keys):
        """Initialize with API key from environment."""
        stt = OpenAIWhisperSTT()

        assert stt.is_initialized is True
        assert stt.api_key == mock_api_keys["openai"]

    def test_init_uses_get_api_key(self, mock_api_keys):
        """Initialization should use config.get_api_key."""
        with patch('speech_mcp_echo.stt_adapters.openai_whisper_adapter.get_api_key') as mock_get_key:
            mock_get_key.return_value = "test-key-123"

            stt = OpenAIWhisperSTT()

            mock_get_key.assert_called_once_with("openai")
            assert stt.api_key == "test-key-123"


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestOpenAIWhisperTranscription:
    """Test transcription functionality."""

    def test_transcribe_success(self, sample_audio_file, mock_api_keys):
        """Transcribe audio file successfully."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "This is a test transcription from OpenAI."

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "This is a test transcription from OpenAI."
            mock_client.audio.transcriptions.create.assert_called_once()

    def test_transcribe_without_api_key(self, sample_audio_file, clean_env):
        """Transcribe should fail without API key."""
        stt = OpenAIWhisperSTT()

        with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
            stt.transcribe(str(sample_audio_file))

    def test_transcribe_passes_correct_model(self, sample_audio_file, mock_api_keys):
        """Transcribe should pass correct model to API."""
        stt = OpenAIWhisperSTT(model="whisper-1")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stt.transcribe(str(sample_audio_file))

            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['model'] == "whisper-1"

    def test_transcribe_with_language_en(self, sample_audio_file, mock_api_keys):
        """Transcribe English audio with language hint."""
        stt = OpenAIWhisperSTT(language="en")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello world"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "Hello world"

            # Should pass language parameter
            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['language'] == "en"

    def test_transcribe_with_language_zh(self, sample_audio_file, mock_api_keys):
        """Transcribe Chinese audio with language hint."""
        stt = OpenAIWhisperSTT(language="zh")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "你好世界"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "你好世界"

            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['language'] == "zh"

    def test_transcribe_with_language_auto(self, sample_audio_file, mock_api_keys):
        """Transcribe with auto language detection."""
        stt = OpenAIWhisperSTT(language="auto")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Auto detected"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            stt.transcribe(str(sample_audio_file))

            # Should pass None for auto detection
            call_args = mock_client.audio.transcriptions.create.call_args
            assert call_args[1]['language'] is None

    def test_transcribe_opens_file(self, sample_audio_file, mock_api_keys):
        """Transcribe should open and read audio file."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai, \
             patch('builtins.open', create=True) as mock_open:

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Mock file handle
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            stt.transcribe(str(sample_audio_file))

            # Should have opened file in binary read mode
            mock_open.assert_called_once_with(str(sample_audio_file), "rb")

    def test_transcribe_japanese(self, sample_audio_file, mock_api_keys):
        """Transcribe Japanese audio."""
        stt = OpenAIWhisperSTT(language="ja")

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "こんにちは世界"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "こんにちは世界"


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestOpenAIWhisperListen:
    """Test listen functionality."""

    def test_listen_success(self, mock_api_keys):
        """Listen and transcribe successfully."""
        stt = OpenAIWhisperSTT()

        with patch('speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT') as mock_fw:
            # Mock the temporary adapter for recording
            mock_temp_adapter = Mock()
            mock_temp_adapter._record_audio.return_value = "/tmp/test.wav"
            mock_fw.__new__ = Mock(return_value=mock_temp_adapter)

            with patch.object(stt, 'transcribe') as mock_transcribe:
                mock_transcribe.return_value = "Listened text"

                result = stt.listen()

                assert result == "Listened text"
                mock_transcribe.assert_called_once_with("/tmp/test.wav")

    def test_listen_cleans_up_temp_file(self, mock_api_keys):
        """Listen should clean up temporary audio file."""
        stt = OpenAIWhisperSTT()

        # Create actual temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        with patch('speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT') as mock_fw:
            mock_temp_adapter = Mock()
            mock_temp_adapter._record_audio.return_value = temp_path
            mock_fw.__new__ = Mock(return_value=mock_temp_adapter)

            with patch.object(stt, 'transcribe') as mock_transcribe:
                mock_transcribe.return_value = "Test"

                stt.listen()

                # File should be deleted
                assert not os.path.exists(temp_path)

    def test_listen_cleans_up_on_error(self, mock_api_keys):
        """Temp file should be cleaned up even on transcription error."""
        stt = OpenAIWhisperSTT()

        # Create actual temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        with patch('speech_mcp_echo.stt_adapters.faster_whisper_adapter.FasterWhisperSTT') as mock_fw:
            mock_temp_adapter = Mock()
            mock_temp_adapter._record_audio.return_value = temp_path
            mock_fw.__new__ = Mock(return_value=mock_temp_adapter)

            with patch.object(stt, 'transcribe') as mock_transcribe:
                mock_transcribe.side_effect = Exception("Transcription error")

                with pytest.raises(Exception):
                    stt.listen()

                # File should still be deleted
                assert not os.path.exists(temp_path)


class TestOpenAIWhisperAPIErrors:
    """Test API error handling."""

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_authentication_error(self, sample_audio_file, mock_api_keys):
        """Handle authentication error."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()

            # Mock auth error
            from openai import AuthenticationError
            error = AuthenticationError("Invalid API key")

            mock_client.audio.transcriptions.create.side_effect = error
            mock_openai.return_value = mock_client

            with pytest.raises(Exception):  # Should raise auth error
                stt.transcribe(str(sample_audio_file))

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_rate_limit_error(self, sample_audio_file, mock_api_keys):
        """Handle rate limit error."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()

            # Mock rate limit error
            from openai import RateLimitError
            error = RateLimitError("Rate limit exceeded")

            mock_client.audio.transcriptions.create.side_effect = error
            mock_openai.return_value = mock_client

            with pytest.raises(Exception):  # Should raise rate limit error
                stt.transcribe(str(sample_audio_file))

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_timeout_error(self, sample_audio_file, mock_api_keys):
        """Handle timeout error."""
        import requests

        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create.side_effect = requests.Timeout("Request timed out")
            mock_openai.return_value = mock_client

            with pytest.raises(Exception):  # Should raise timeout error
                stt.transcribe(str(sample_audio_file))

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_network_error(self, sample_audio_file, mock_api_keys):
        """Handle network connection error."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create.side_effect = ConnectionError("Network error")
            mock_openai.return_value = mock_client

            with pytest.raises(ConnectionError):
                stt.transcribe(str(sample_audio_file))

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_transcribe_import_error(self, sample_audio_file, mock_api_keys):
        """Handle missing openai package."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI',
                   side_effect=ImportError("No module named 'openai'")):

            with pytest.raises(ImportError):
                stt.transcribe(str(sample_audio_file))


class TestOpenAIWhisperModels:
    """Test model management."""

    def test_get_available_models(self, mock_api_keys):
        """Get list of available models."""
        stt = OpenAIWhisperSTT()

        models = stt.get_available_models()

        assert isinstance(models, list)
        assert "whisper-1" in models

    def test_only_whisper_1_available(self, mock_api_keys):
        """Only whisper-1 model is currently available."""
        stt = OpenAIWhisperSTT()

        models = stt.get_available_models()

        assert len(models) == 1
        assert models[0] == "whisper-1"


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestOpenAIWhisperResponseFormats:
    """Test different response format handling."""

    def test_default_response_format(self, sample_audio_file, mock_api_keys):
        """Default should use text format."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response text"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            # Should return text attribute
            assert result == "Response text"

    def test_response_text_attribute(self, sample_audio_file, mock_api_keys):
        """Should use .text attribute from response."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Transcribed content"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "Transcribed content"


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestOpenAIWhisperFileHandling:
    """Test file size and format handling."""

    def test_transcribe_small_file(self, tmp_path, mock_api_keys):
        """Transcribe small audio file."""
        import wave
        import numpy as np

        # Create small audio file (1 second)
        audio_file = tmp_path / "small.wav"
        sample_rate = 16000
        duration = 1.0

        audio_data = np.random.randint(-32768, 32767, int(sample_rate * duration), dtype=np.int16)

        with wave.open(str(audio_file), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Small file transcription"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(audio_file))

            assert result == "Small file transcription"

    def test_transcribe_wav_format(self, sample_audio_file, mock_api_keys):
        """Transcribe WAV format file."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "WAV transcription"

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "WAV transcription"

    def test_transcribe_nonexistent_file(self, mock_api_keys):
        """Handle non-existent file."""
        stt = OpenAIWhisperSTT()

        # Test that it tries to open the file (and fails)
        with pytest.raises((FileNotFoundError, OSError)):
            stt.transcribe("/nonexistent/file.wav")


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
class TestOpenAIWhisperEdgeCases:
    """Test edge cases and error scenarios."""

    def test_empty_transcription_result(self, sample_audio_file, mock_api_keys):
        """Handle empty transcription result."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = ""

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == ""

    def test_whitespace_only_transcription(self, sample_audio_file, mock_api_keys):
        """Handle whitespace-only transcription."""
        stt = OpenAIWhisperSTT()

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "   "

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == "   "  # Returns as-is

    def test_very_long_transcription(self, sample_audio_file, mock_api_keys):
        """Handle very long transcription result."""
        stt = OpenAIWhisperSTT()

        long_text = "This is a test. " * 1000  # Very long transcription

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = long_text

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == long_text

    def test_unicode_transcription(self, sample_audio_file, mock_api_keys):
        """Handle Unicode characters in transcription."""
        stt = OpenAIWhisperSTT()

        unicode_text = "Hello 世界 🌍 Привет مرحبا"

        with patch('openai.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = unicode_text

            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            result = stt.transcribe(str(sample_audio_file))

            assert result == unicode_text


class TestOpenAIWhisperConfiguration:
    """Test configuration handling."""

    def test_api_key_from_config(self):
        """API key should come from config module."""
        with patch('speech_mcp_echo.stt_adapters.openai_whisper_adapter.get_api_key') as mock_get_key:
            mock_get_key.return_value = "config-api-key"

            stt = OpenAIWhisperSTT()

            assert stt.api_key == "config-api-key"

    def test_initialization_without_dependencies(self, clean_env):
        """Can initialize even without openai package (fails on use)."""
        stt = OpenAIWhisperSTT()

        # Should initialize
        assert stt.model == "whisper-1"
        assert stt.language == "en"

        # But not ready to use
        assert stt.is_initialized is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
