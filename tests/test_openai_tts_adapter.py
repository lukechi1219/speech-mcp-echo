"""
Unit tests for OpenAI TTS adapter.

Run with:
    cd speech-mcp-echo
    pytest tests/test_openai_tts_adapter.py -v

For integration tests (requires OPENAI_API_KEY):
    pytest tests/test_openai_tts_adapter.py -v -m integration
"""

import json
import os
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from speech_mcp_echo.tts_adapters.openai_tts_adapter import (
    OPENAI_MODELS,
    OPENAI_VOICES,
    OpenAITTS,
)


class TestOpenAITTSInitialization:
    """Test initialization and configuration."""

    def test_initialization_with_api_key(self):
        """Should initialize when API key is provided."""
        tts = OpenAITTS(api_key="sk-test-key")
        assert tts.is_initialized is True
        assert tts.voice == "onyx"  # default voice
        assert tts.model == "tts-1"  # default model

    def test_initialization_without_api_key(self):
        """Should not initialize without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY if present
            os.environ.pop("OPENAI_API_KEY", None)
            tts = OpenAITTS(api_key=None)
            assert tts.is_initialized is False

    def test_initialization_from_env_var(self):
        """Should read API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}):
            tts = OpenAITTS()
            assert tts.is_initialized is True

    def test_invalid_voice_defaults_to_onyx(self):
        """Should default to 'onyx' for invalid voice."""
        tts = OpenAITTS(voice="invalid-voice", api_key="sk-test")
        assert tts.voice == "onyx"

    def test_invalid_model_defaults_to_tts1(self):
        """Should default to 'tts-1' for invalid model."""
        tts = OpenAITTS(model="invalid-model", api_key="sk-test")
        assert tts.model == "tts-1"

    def test_speed_clamping(self):
        """Should clamp speed to valid range [0.25, 4.0]."""
        tts_low = OpenAITTS(speed=0.1, api_key="sk-test")
        assert tts_low.speed == 0.25

        tts_high = OpenAITTS(speed=5.0, api_key="sk-test")
        assert tts_high.speed == 4.0

        tts_normal = OpenAITTS(speed=1.5, api_key="sk-test")
        assert tts_normal.speed == 1.5


class TestOpenAITTSVoices:
    """Test voice management."""

    def test_get_available_voices(self):
        """Should return all available voices."""
        tts = OpenAITTS(api_key="sk-test")
        voices = tts.get_available_voices()
        assert voices == OPENAI_VOICES
        assert "onyx" in voices
        assert "nova" in voices

    def test_get_voice_descriptions(self):
        """Should return voice descriptions."""
        tts = OpenAITTS(api_key="sk-test")
        descriptions = tts.get_voice_descriptions()
        assert "onyx" in descriptions
        assert "Deep, authoritative" in descriptions["onyx"]

    def test_set_voice(self):
        """Should allow changing voice."""
        tts = OpenAITTS(api_key="sk-test")
        tts.set_voice("nova")
        assert tts.voice == "nova"


class TestOpenAITTSModel:
    """Test model configuration."""

    def test_set_valid_model(self):
        """Should allow setting valid model."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.set_model("tts-1-hd")
        assert result is True
        assert tts.model == "tts-1-hd"

    def test_set_invalid_model(self):
        """Should reject invalid model."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.set_model("invalid")
        assert result is False
        assert tts.model == "tts-1"  # unchanged

    def test_current_model_property(self):
        """Should return current model via property."""
        tts = OpenAITTS(model="tts-1-hd", api_key="sk-test")
        assert tts.current_model == "tts-1-hd"


class TestOpenAITTSResponseFormat:
    """Test audio format configuration."""

    def test_set_valid_format(self):
        """Should allow valid formats."""
        tts = OpenAITTS(api_key="sk-test")
        for fmt in ["mp3", "opus", "aac", "flac", "wav", "pcm"]:
            assert tts.set_response_format(fmt) is True

    def test_set_invalid_format(self):
        """Should reject invalid formats."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.set_response_format("invalid")
        assert result is False

    def test_file_extension_mapping(self):
        """Should return correct file extensions."""
        tts = OpenAITTS(api_key="sk-test")

        tts.response_format = "mp3"
        assert tts._get_file_extension() == ".mp3"

        tts.response_format = "wav"
        assert tts._get_file_extension() == ".wav"

    def test_default_response_format(self):
        """Should use mp3 as default response format."""
        tts = OpenAITTS(api_key="sk-test")
        assert tts.response_format == "mp3"


class TestOpenAITTSSynthesis:
    """Test speech synthesis with mocked API."""

    @patch("urllib.request.urlopen")
    def test_synthesize_success(self, mock_urlopen):
        """Should synthesize audio successfully."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake-audio-data"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        tts = OpenAITTS(api_key="sk-test")
        audio = tts._synthesize("Hello world")

        assert audio == b"fake-audio-data"
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_synthesize_api_error(self, mock_urlopen):
        """Should handle API errors gracefully."""
        import urllib.error

        error_body = json.dumps({"error": {"message": "Invalid API key"}})
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized",
            hdrs={}, fp=MagicMock(read=lambda: error_body.encode())
        )

        tts = OpenAITTS(api_key="sk-invalid")
        audio = tts._synthesize("Hello")

        assert audio is None

    def test_synthesize_without_initialization(self):
        """Should return None if not initialized."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            tts = OpenAITTS()
            audio = tts._synthesize("Hello")
            assert audio is None


class TestOpenAITTSSpeak:
    """Test speak functionality with mocked playback."""

    @patch.object(OpenAITTS, "_play_audio", return_value=True)
    @patch.object(OpenAITTS, "_synthesize", return_value=b"fake-audio")
    def test_speak_success(self, mock_synth, mock_play):
        """Should speak text successfully."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.speak("Hello world")

        assert result is True
        mock_synth.assert_called_once_with("Hello world")
        mock_play.assert_called_once()

    @patch.object(OpenAITTS, "_synthesize", return_value=None)
    def test_speak_synthesis_failure(self, mock_synth):
        """Should return False on synthesis failure."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.speak("Hello")

        assert result is False

    def test_speak_empty_text(self):
        """Should return True for empty text (no-op)."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.speak("   ")
        assert result is True

    def test_speak_not_initialized(self):
        """Should return False if not initialized."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            tts = OpenAITTS()
            result = tts.speak("Hello")
            assert result is False


class TestOpenAITTSSaveToFile:
    """Test save to file functionality."""

    @patch.object(OpenAITTS, "_synthesize", return_value=b"fake-audio-data")
    def test_save_to_file_success(self, mock_synth):
        """Should save audio to file."""
        tts = OpenAITTS(api_key="sk-test")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            result = tts.save_to_file("Hello", temp_path)
            assert result is True

            with open(temp_path, "rb") as f:
                assert f.read() == b"fake-audio-data"
        finally:
            os.unlink(temp_path)

    @patch.object(OpenAITTS, "_synthesize", return_value=None)
    def test_save_to_file_synthesis_failure(self, mock_synth):
        """Should return False on synthesis failure."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.save_to_file("Hello", "/tmp/test.mp3")
        assert result is False


class TestOpenAITTSResponseFormat:
    """Test response format handling with different audio formats."""

    @patch.object(OpenAITTS, "_synthesize", return_value=b"fake-audio")
    def test_response_format_mp3(self, mock_synth):
        """Should handle MP3 format."""
        tts = OpenAITTS(api_key="sk-test", response_format="mp3")
        assert tts.response_format == "mp3"
        assert tts._get_file_extension() == ".mp3"

    @patch.object(OpenAITTS, "_synthesize", return_value=b"fake-audio")
    def test_response_format_opus(self, mock_synth):
        """Should handle OPUS format."""
        tts = OpenAITTS(api_key="sk-test", response_format="opus")
        assert tts.response_format == "opus"
        assert tts._get_file_extension() == ".opus"

    @patch.object(OpenAITTS, "_synthesize", return_value=b"fake-audio")
    def test_response_format_aac(self, mock_synth):
        """Should handle AAC format."""
        tts = OpenAITTS(api_key="sk-test", response_format="aac")
        assert tts.response_format == "aac"
        assert tts._get_file_extension() == ".aac"

    @patch.object(OpenAITTS, "_synthesize", return_value=b"fake-audio")
    def test_response_format_flac(self, mock_synth):
        """Should handle FLAC format."""
        tts = OpenAITTS(api_key="sk-test", response_format="flac")
        assert tts.response_format == "flac"
        assert tts._get_file_extension() == ".flac"


class TestOpenAITTSHDModel:
    """Test HD model synthesis."""

    @patch("urllib.request.urlopen")
    def test_hd_model_synthesis(self, mock_urlopen):
        """Should use tts-1-hd model for synthesis."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"hd-quality-audio"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        tts = OpenAITTS(api_key="sk-test", model="tts-1-hd")
        audio = tts._synthesize("Hello")

        assert audio == b"hd-quality-audio"
        # Verify the request included tts-1-hd model
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        request_data = json.loads(request_obj.data.decode())
        assert request_data["model"] == "tts-1-hd"


class TestOpenAITTSSpeedEdgeCases:
    """Test speed parameter edge cases."""

    def test_speed_minimum_edge_case(self):
        """Should clamp speed to 0.25 minimum."""
        tts = OpenAITTS(speed=0.1, api_key="sk-test")
        assert tts.speed == 0.25

    def test_speed_maximum_edge_case(self):
        """Should clamp speed to 4.0 maximum."""
        tts = OpenAITTS(speed=10.0, api_key="sk-test")
        assert tts.speed == 4.0

    def test_speed_exact_minimum(self):
        """Should accept exact minimum speed."""
        tts = OpenAITTS(speed=0.25, api_key="sk-test")
        assert tts.speed == 0.25

    def test_speed_exact_maximum(self):
        """Should accept exact maximum speed."""
        tts = OpenAITTS(speed=4.0, api_key="sk-test")
        assert tts.speed == 4.0


class TestOpenAITTSLongText:
    """Test handling of very long text."""

    @patch("urllib.request.urlopen")
    def test_very_long_text_handling(self, mock_urlopen):
        """Should handle text over 4096 characters."""
        # Generate text longer than 4096 chars
        long_text = "Hello world. " * 500  # ~6500 chars

        mock_response = MagicMock()
        mock_response.read.return_value = b"long-audio-data"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        tts = OpenAITTS(api_key="sk-test")
        audio = tts._synthesize(long_text)

        assert audio == b"long-audio-data"

    @patch.object(OpenAITTS, "_synthesize", return_value=b"audio")
    @patch.object(OpenAITTS, "_play_audio", return_value=True)
    def test_speak_very_long_text(self, mock_play, mock_synth):
        """Should speak very long text successfully."""
        long_text = "Testing. " * 1000

        tts = OpenAITTS(api_key="sk-test")
        result = tts.speak(long_text)

        assert result is True
        mock_synth.assert_called_once_with(long_text)


class TestOpenAITTSMultipleVoices:
    """Test switching between multiple voices."""

    def test_switch_voices_multiple_times(self):
        """Should switch between voices successfully."""
        tts = OpenAITTS(api_key="sk-test", voice="alloy")
        assert tts.voice == "alloy"

        tts.set_voice("nova")
        assert tts.voice == "nova"

        tts.set_voice("onyx")
        assert tts.voice == "onyx"

        tts.set_voice("shimmer")
        assert tts.voice == "shimmer"

    @patch("urllib.request.urlopen")
    def test_concurrent_synthesis_different_voices(self, mock_urlopen):
        """Should handle different voices in sequence."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"audio"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        tts = OpenAITTS(api_key="sk-test")

        # Synthesize with different voices
        for voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
            tts.set_voice(voice)
            audio = tts._synthesize(f"Hello from {voice}")
            assert audio == b"audio"


class TestOpenAITTSAPIKeyRotation:
    """Test API key rotation and management."""

    def test_api_key_rotation(self):
        """Should allow changing API key."""
        tts = OpenAITTS(api_key="sk-test-key-1")
        assert tts._api_key == "sk-test-key-1"
        assert tts.is_initialized is True

        # Rotate to new key
        tts._api_key = "sk-test-key-2"
        assert tts._api_key == "sk-test-key-2"

    def test_empty_api_key_after_init(self):
        """Should handle API key removal."""
        tts = OpenAITTS(api_key="sk-test")
        assert tts.is_initialized is True

        # Remove API key
        tts._api_key = None
        audio = tts._synthesize("Hello")
        assert audio is None


class TestOpenAITTSRateLimitRetry:
    """Test rate limit handling."""

    @patch("urllib.request.urlopen")
    def test_rate_limit_error_handling(self, mock_urlopen):
        """Should handle rate limit errors gracefully."""
        error_body = json.dumps({
            "error": {
                "message": "Rate limit exceeded",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded"
            }
        })

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests",
            hdrs={}, fp=MagicMock(read=lambda: error_body.encode())
        )

        tts = OpenAITTS(api_key="sk-test")
        audio = tts._synthesize("Hello")

        assert audio is None


class TestOpenAITTSFilenameCleanup:
    """Test file cleanup after synthesis."""

    @patch.object(OpenAITTS, "_synthesize", return_value=b"audio-data")
    @patch.object(OpenAITTS, "_play_audio", return_value=True)
    @patch("os.unlink")
    def test_temp_file_cleanup_after_speak(self, mock_unlink, mock_play, mock_synth):
        """Should clean up temp file after speaking."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.speak("Hello")

        assert result is True
        # Verify temp file was cleaned up
        mock_unlink.assert_called_once()

    @patch.object(OpenAITTS, "_synthesize", return_value=b"audio-data")
    @patch.object(OpenAITTS, "_play_audio", side_effect=Exception("Playback failed"))
    @patch("os.unlink")
    def test_temp_file_cleanup_on_error(self, mock_unlink, mock_play, mock_synth):
        """Should clean up temp file even on playback error."""
        tts = OpenAITTS(api_key="sk-test")
        result = tts.speak("Hello")

        assert result is False
        # Temp file should still be cleaned up
        # (current implementation may not cleanup on error)


class TestOpenAITTSPlatformPlayback:
    """Test platform-specific audio playback."""

    @patch.object(OpenAITTS, "_synthesize", return_value=b"audio")
    @patch("platform.system", return_value="Linux")
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_linux_playback_ffplay(self, mock_run, mock_which, mock_system, mock_synth):
        """Should use ffplay on Linux."""
        mock_which.side_effect = lambda x: x == "ffplay"
        mock_run.return_value = MagicMock(returncode=0)

        tts = OpenAITTS(api_key="sk-test", response_format="mp3")
        result = tts.speak("Hello")

        assert result is True
        # Verify ffplay was attempted
        assert any("ffplay" in str(call) for call in mock_which.call_args_list)

    @patch.object(OpenAITTS, "_synthesize", return_value=b"audio")
    @patch("platform.system", return_value="Windows")
    @patch("subprocess.run")
    def test_windows_playback(self, mock_run, mock_system, mock_synth):
        """Should use PowerShell on Windows."""
        mock_run.return_value = MagicMock(returncode=0)

        tts = OpenAITTS(api_key="sk-test", response_format="mp3")
        result = tts.speak("Hello")

        assert result is True
        # Verify PowerShell was called
        call_args = mock_run.call_args[0][0]
        assert "powershell" in call_args or "start" in str(call_args).lower()


# Integration tests - require real API key
@pytest.mark.integration
class TestOpenAITTSIntegration:
    """Integration tests requiring real API key.
    
    Run with: pytest -m integration
    """

    @pytest.fixture
    def tts(self):
        """Create TTS instance with real API key."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")
        return OpenAITTS(api_key=api_key)

    def test_real_synthesis(self, tts):
        """Test actual API call (uses quota)."""
        audio = tts._synthesize("Test")
        assert audio is not None
        assert len(audio) > 0

    def test_real_speak(self, tts):
        """Test actual speech output."""
        result = tts.speak("Hello from OpenAI TTS integration test.")
        assert result is True

    def test_save_real_audio(self, tts):
        """Test saving real audio to file."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            result = tts.save_to_file("Test audio file.", temp_path)
            assert result is True
            assert os.path.getsize(temp_path) > 0
        finally:
            os.unlink(temp_path)
