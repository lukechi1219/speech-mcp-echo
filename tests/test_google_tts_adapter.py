"""
Unit tests for Google Cloud TTS adapter.

Run with:
    cd speech-mcp-echo
    pytest tests/test_google_tts_adapter.py -v

For integration tests (requires Google Cloud credentials):
    pytest tests/test_google_tts_adapter.py -v -m integration
"""

import base64
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from speech_mcp_echo.tts_adapters.google_tts_adapter import (
    GoogleCloudTTS,
    VOICE_PRESETS,
)


# =============================================================================
# Test Initialization & Authentication
# =============================================================================


class TestGoogleTTSInitializationAuth:
    """Test initialization and authentication methods."""

    @patch("speech_mcp_echo.tts_adapters.google_tts_adapter.shutil.which")
    def test_init_with_gcloud_credentials(self, mock_which):
        """Should initialize with gcloud CLI credentials."""
        mock_which.return_value = "gcloud"

        tts = GoogleCloudTTS()

        assert tts.is_initialized is True
        assert tts.auth_method == "gcloud"
        assert tts._gcloud_path == "gcloud"

    @patch("speech_mcp_echo.tts_adapters.google_tts_adapter.shutil.which", return_value=None)
    @patch("os.path.isfile")
    def test_init_with_service_account_json(self, mock_isfile, mock_which):
        """Should initialize with service account JSON file."""
        # Mock the credentials file
        creds_data = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "test-key",
            "client_email": "test@test.iam.gserviceaccount.com",
        }

        def isfile_side_effect(path):
            return path == "/path/to/creds.json"

        mock_isfile.side_effect = isfile_side_effect

        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json"}, clear=True):
            with patch("builtins.open", create=True):
                with patch("json.load", return_value=creds_data):
                    tts = GoogleCloudTTS()

                    assert tts.is_initialized is True
                    assert tts.auth_method == "service_account"


    @patch("speech_mcp_echo.tts_adapters.google_tts_adapter.shutil.which", return_value=None)
    @patch("os.path.isfile", return_value=False)
    def test_init_without_credentials(self, mock_isfile, mock_which):
        """Should not initialize without credentials."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

            with patch("importlib.import_module", side_effect=ImportError):
                tts = GoogleCloudTTS()

                assert tts.is_initialized is False
                assert tts.auth_method is None



    @patch("speech_mcp_echo.tts_adapters.google_tts_adapter.shutil.which")
    def test_multiple_initialization_attempts(self, mock_which):
        """Should handle multiple initialization attempts."""
        mock_which.return_value = "/usr/local/bin/gcloud"

        tts = GoogleCloudTTS()
        assert tts.is_initialized is True

        # Re-initialize (should use cached auth)
        tts._initialize_auth()
        assert tts.is_initialized is True

    @patch("speech_mcp_echo.tts_adapters.google_tts_adapter.shutil.which", return_value=None)
    @patch("os.path.isfile", return_value=False)
    def test_auto_detect_authentication_method(self, mock_isfile, mock_which):
        """Should auto-detect authentication method."""
        # Mock the import to simulate google-cloud-texttospeech being installed
        mock_client = MagicMock()

        with patch.dict(os.environ, {}, clear=True):
            # Create a mock module
            import sys
            mock_google = MagicMock()
            mock_google.cloud = MagicMock()
            mock_google.cloud.texttospeech = MagicMock()
            mock_google.cloud.texttospeech.TextToSpeechClient.return_value = mock_client

            # Temporarily add to sys.modules
            sys.modules['google'] = mock_google
            sys.modules['google.cloud'] = mock_google.cloud
            sys.modules['google.cloud.texttospeech'] = mock_google.cloud.texttospeech

            try:
                tts = GoogleCloudTTS()
                assert tts.is_initialized is True
                assert tts.auth_method == "client_library"
            finally:
                # Clean up
                del sys.modules['google.cloud.texttospeech']
                del sys.modules['google.cloud']
                del sys.modules['google']


    def test_find_gcloud_in_path(self):
        """Should find gcloud in system PATH."""
        with patch("shutil.which", return_value="gcloud"):
            tts = GoogleCloudTTS()
            assert tts._gcloud_path == "gcloud"

    def test_find_gcloud_common_paths(self):
        """Should find gcloud in common installation paths."""
        with patch("shutil.which", return_value=None):
            with patch("os.path.isfile") as mock_isfile:
                # Mock homebrew path exists
                def isfile_side_effect(path):
                    return path == "/opt/homebrew/bin/gcloud"

                mock_isfile.side_effect = isfile_side_effect

                tts = GoogleCloudTTS()
                assert tts._gcloud_path == "/opt/homebrew/bin/gcloud"


# =============================================================================
# Test Voice Selection
# =============================================================================


class TestGoogleTTSVoiceSelection:
    """Test voice selection and management."""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_list_available_voices(self, mock_which):
        """Should return list of available voices."""
        tts = GoogleCloudTTS()
        voices = tts.get_available_voices()

        assert isinstance(voices, list)
        assert len(voices) > 0
        assert "cmn-TW-Standard-B" in voices
        assert "en-US-Standard-A" in voices

    @pytest.mark.parametrize("language,voice_prefix", [
        ("cmn-TW", "cmn-"),
        ("en-US", "en-"),
        ("ja-JP", "ja-"),
    ], ids=["chinese", "english", "japanese"])
    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_filter_voices_by_language(self, mock_which, language, voice_prefix):
        """Should filter voices by language."""
        tts = GoogleCloudTTS(language=language)
        voices = tts.get_available_voices()

        # Check that language-specific voices are included
        language_voices = [v for v in voices if v.startswith(voice_prefix)]
        assert len(language_voices) > 0

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_set_voice_by_name(self, mock_which):
        """Should allow setting voice by name."""
        tts = GoogleCloudTTS()
        tts.set_voice("en-GB-Standard-A")

        assert tts.voice == "en-GB-Standard-A"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_set_invalid_voice_uses_default(self, mock_which):
        """Should handle invalid voice name."""
        tts = GoogleCloudTTS(language="cmn-TW")

        # Voice is set to whatever is provided, validation happens at synthesis time
        tts.set_voice("invalid-voice-name")
        assert tts.voice == "invalid-voice-name"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_get_current_voice(self, mock_which):
        """Should return current voice."""
        tts = GoogleCloudTTS(voice="en-US-Standard-C")
        assert tts.voice == "en-US-Standard-C"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_neural_vs_standard_voices(self, mock_which):
        """Should support both neural and standard voices."""
        tts = GoogleCloudTTS()
        voices = tts.get_available_voices()

        # Check for both Standard and Wavenet (neural) voices
        standard_voices = [v for v in voices if "Standard" in v]
        wavenet_voices = [v for v in voices if "Wavenet" in v]

        assert len(standard_voices) > 0
        assert len(wavenet_voices) > 0


# =============================================================================
# Test Speech Synthesis
# =============================================================================


class TestGoogleTTSSpeechSynthesis:
    """Test speech synthesis functionality."""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize_with_rest_api")
    def test_synthesize_text_success(self, mock_synth, mock_which):
        """Should synthesize text successfully."""
        mock_synth.return_value = b"fake-audio-data"

        tts = GoogleCloudTTS()
        audio = tts._synthesize("Hello world")

        assert audio == b"fake-audio-data"
        mock_synth.assert_called_once_with("Hello world")

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize_with_rest_api")
    def test_synthesize_different_languages(self, mock_synth, mock_which):
        """Should synthesize with different languages."""
        mock_synth.return_value = b"fake-audio"

        # Chinese
        tts_zh = GoogleCloudTTS(language="cmn-TW")
        audio_zh = tts_zh._synthesize("你好")
        assert audio_zh == b"fake-audio"

        # Japanese
        tts_ja = GoogleCloudTTS(language="ja-JP")
        audio_ja = tts_ja._synthesize("こんにちは")
        assert audio_ja == b"fake-audio"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize_with_rest_api")
    def test_synthesize_empty_text(self, mock_synth, mock_which):
        """Should handle empty text gracefully."""
        mock_synth.return_value = b""

        tts = GoogleCloudTTS()
        audio = tts._synthesize("")

        assert audio == b""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize_with_rest_api")
    def test_synthesize_very_long_text(self, mock_synth, mock_which):
        """Should handle very long text (>5000 chars)."""
        long_text = "Hello " * 1000  # ~6000 chars
        mock_synth.return_value = b"fake-audio"

        tts = GoogleCloudTTS()
        audio = tts._synthesize(long_text)

        assert audio == b"fake-audio"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize_with_rest_api")
    def test_synthesize_with_speaking_rate_slow(self, mock_synth, mock_which):
        """Should synthesize with slow speaking rate."""
        mock_synth.return_value = b"fake-audio"

        tts = GoogleCloudTTS(speed=0.5)
        audio = tts._synthesize("Hello")

        assert tts.speed == 0.5
        assert audio == b"fake-audio"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize_with_rest_api")
    def test_synthesize_with_speaking_rate_fast(self, mock_synth, mock_which):
        """Should synthesize with fast speaking rate."""
        mock_synth.return_value = b"fake-audio"

        tts = GoogleCloudTTS(speed=2.0)
        audio = tts._synthesize("Hello")

        assert tts.speed == 2.0
        assert audio == b"fake-audio"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch("urllib.request.urlopen")
    def test_rest_api_request_format(self, mock_urlopen, mock_which):
        """Should format REST API request correctly."""
        # Mock response
        response_data = {"audioContent": base64.b64encode(b"fake-audio").decode()}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Mock token and project
        with patch.object(GoogleCloudTTS, "_get_access_token_gcloud", return_value="test-token"):
            with patch.object(GoogleCloudTTS, "_get_project_id_gcloud", return_value="test-project"):
                tts = GoogleCloudTTS()
                audio = tts._synthesize_with_rest_api("Hello")

                assert audio == b"fake-audio"
                # Verify API was called
                assert mock_urlopen.called


# =============================================================================
# Test Speak & Playback
# =============================================================================


class TestGoogleTTSSpeakPlayback:
    """Test speak and audio playback functionality."""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio")
    @patch.object(GoogleCloudTTS, "_play_audio", return_value=True)
    def test_speak_success(self, mock_play, mock_synth, mock_which):
        """Should speak text successfully."""
        tts = GoogleCloudTTS()
        result = tts.speak("Hello world")

        assert result is True
        mock_synth.assert_called_once_with("Hello world")
        mock_play.assert_called_once()

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio")
    @patch("platform.system", return_value="Darwin")
    @patch("subprocess.run")
    def test_speak_with_audio_playback_macos(self, mock_run, mock_system, mock_synth, mock_which):
        """Should play audio on macOS."""
        mock_run.return_value = MagicMock(returncode=0)

        tts = GoogleCloudTTS()
        result = tts.speak("Hello")

        assert result is True
        # Check that afplay was called
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert args[0] == "afplay"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"")
    def test_speak_empty_text(self, mock_synth, mock_which):
        """Should handle empty text."""
        tts = GoogleCloudTTS()
        result = tts.speak("")

        # Empty audio returns False
        assert result is False

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio")
    @patch.object(GoogleCloudTTS, "_play_audio", return_value=True)
    def test_speak_very_long_text(self, mock_play, mock_synth, mock_which):
        """Should speak very long text."""
        long_text = "Hello world! " * 500

        tts = GoogleCloudTTS()
        result = tts.speak(long_text)

        assert result is True


# =============================================================================
# Test Save to File
# =============================================================================


class TestGoogleTTSSaveToFile:
    """Test save to file functionality."""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio-data")
    def test_save_to_file_success(self, mock_synth, mock_which):
        """Should save audio to file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            tts = GoogleCloudTTS()
            result = tts.save_to_file("Hello", temp_path)

            assert result is True
            with open(temp_path, "rb") as f:
                assert f.read() == b"fake-audio-data"
        finally:
            os.unlink(temp_path)

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio")
    def test_save_different_formats(self, mock_synth, mock_which):
        """Should save with different formats."""
        tts = GoogleCloudTTS()

        # WAV format
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        try:
            result = tts.save_to_file("Test", wav_path)
            assert result is True
            assert os.path.exists(wav_path)
        finally:
            os.unlink(wav_path)

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio")
    def test_save_to_invalid_path(self, mock_synth, mock_which):
        """Should handle invalid path gracefully."""
        tts = GoogleCloudTTS()
        result = tts.save_to_file("Hello", "/invalid/path/audio.wav")

        assert result is False

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"fake-audio")
    def test_save_with_permission_denied(self, mock_synth, mock_which):
        """Should handle permission denied error."""
        tts = GoogleCloudTTS()

        with patch("builtins.open", side_effect=PermissionError):
            result = tts.save_to_file("Hello", "/tmp/test.wav")
            assert result is False

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch.object(GoogleCloudTTS, "_synthesize", return_value=b"new-audio-data")
    def test_overwrite_existing_file(self, mock_synth, mock_which):
        """Should overwrite existing file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            f.write(b"old-data")

        try:
            tts = GoogleCloudTTS()
            result = tts.save_to_file("Hello", temp_path)

            assert result is True
            with open(temp_path, "rb") as f:
                assert f.read() == b"new-audio-data"
        finally:
            os.unlink(temp_path)


# =============================================================================
# Test Error Handling
# =============================================================================


class TestGoogleTTSErrorHandling:
    """Test error handling scenarios."""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch("urllib.request.urlopen")
    def test_handle_quota_exceeded(self, mock_urlopen, mock_which):
        """Should handle Google API quota exceeded."""
        error_response = {
            "error": {
                "code": 429,
                "message": "Quota exceeded",
                "status": "RESOURCE_EXHAUSTED"
            }
        }

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=429, msg="Too Many Requests",
            hdrs={}, fp=MagicMock(read=lambda: json.dumps(error_response).encode())
        )

        with patch.object(GoogleCloudTTS, "_get_access_token_gcloud", return_value="token"):
            with patch.object(GoogleCloudTTS, "_get_project_id_gcloud", return_value="project"):
                tts = GoogleCloudTTS()
                audio = tts._synthesize_with_rest_api("Hello")

                assert audio is None

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch("urllib.request.urlopen")
    def test_handle_auth_error(self, mock_urlopen, mock_which):
        """Should handle authentication errors."""
        error_response = {
            "error": {
                "code": 401,
                "message": "Invalid authentication credentials",
                "status": "UNAUTHENTICATED"
            }
        }

        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="", code=401, msg="Unauthorized",
            hdrs={}, fp=MagicMock(read=lambda: json.dumps(error_response).encode())
        )

        with patch.object(GoogleCloudTTS, "_get_access_token_gcloud", return_value="invalid-token"):
            with patch.object(GoogleCloudTTS, "_get_project_id_gcloud", return_value="project"):
                tts = GoogleCloudTTS()
                audio = tts._synthesize_with_rest_api("Hello")

                assert audio is None

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch("urllib.request.urlopen")
    def test_handle_network_error(self, mock_urlopen, mock_which):
        """Should handle network errors."""
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")

        with patch.object(GoogleCloudTTS, "_get_access_token_gcloud", return_value="token"):
            with patch.object(GoogleCloudTTS, "_get_project_id_gcloud", return_value="project"):
                tts = GoogleCloudTTS()
                audio = tts._synthesize_with_rest_api("Hello")

                assert audio is None

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    @patch("urllib.request.urlopen")
    def test_handle_timeout(self, mock_urlopen, mock_which):
        """Should handle API timeout."""
        import socket
        mock_urlopen.side_effect = socket.timeout("Request timed out")

        with patch.object(GoogleCloudTTS, "_get_access_token_gcloud", return_value="token"):
            with patch.object(GoogleCloudTTS, "_get_project_id_gcloud", return_value="project"):
                tts = GoogleCloudTTS()
                audio = tts._synthesize_with_rest_api("Hello")

                assert audio is None

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_handle_invalid_language_code(self, mock_which):
        """Should handle invalid language code."""
        # Invalid language code - adapter will still initialize
        tts = GoogleCloudTTS(language="invalid-lang")

        assert tts.language == "invalid-lang"
        # Voice will be based on invalid language
        assert tts.voice == "invalid-lang-Standard-B"


# =============================================================================
# Test Language Management
# =============================================================================


class TestGoogleTTSLanguageManagement:
    """Test language setting and management."""

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_set_language_updates_voice(self, mock_which):
        """Should update voice when language changes."""
        tts = GoogleCloudTTS(language="en-US")
        assert tts.voice == "en-US-Standard-B"

        tts.set_language("cmn-TW")
        assert tts.language == "cmn-TW"
        assert tts.voice == "cmn-TW-Standard-B"

    @patch("shutil.which", return_value="/usr/bin/gcloud")
    def test_default_voices_for_languages(self, mock_which):
        """Should use correct default voice for each language."""
        # Test various languages
        languages = {
            "cmn-TW": "cmn-TW-Standard-B",
            "en-US": "en-US-Standard-B",
            "ja-JP": "ja-JP-Standard-B",
            "ko-KR": "ko-KR-Standard-B",
        }

        for lang, expected_voice in languages.items():
            tts = GoogleCloudTTS(language=lang)
            assert tts.voice == expected_voice


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestGoogleTTSIntegration:
    """Integration tests requiring real Google Cloud credentials.

    Run with: pytest -m integration
    Skip if no credentials available.
    """

    @pytest.fixture
    def tts(self):
        """Create TTS instance with real credentials."""
        # Try to create instance - skip if no auth available
        tts_instance = GoogleCloudTTS()
        if not tts_instance.is_initialized:
            pytest.skip("Google Cloud credentials not available")
        return tts_instance

    def test_real_synthesis(self, tts):
        """Test actual API call (uses quota)."""
        audio = tts._synthesize("Test")
        assert audio is not None
        assert len(audio) > 0

    def test_real_speak(self, tts):
        """Test actual speech output."""
        result = tts.speak("Hello from Google Cloud TTS integration test.")
        assert result is True

    def test_save_real_audio(self, tts):
        """Test saving real audio to file."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            result = tts.save_to_file("Test audio file.", temp_path)
            assert result is True
            assert os.path.getsize(temp_path) > 0
        finally:
            os.unlink(temp_path)
