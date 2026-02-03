"""
Google Cloud TTS adapter.

Uses Google Cloud Text-to-Speech API via gcloud CLI for authentication.
Adapted from ~/.local/bin/google_tts wrapper script.
"""

import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from typing import Optional

from speech_mcp_echo.tts_adapters import BaseTTSAdapter

logger = logging.getLogger(__name__)

# Voice presets by language
VOICE_PRESETS = {
    "cmn-TW": "cmn-TW-Standard-B",  # Chinese (Traditional)
    "cmn-CN": "cmn-CN-Standard-B",  # Chinese (Simplified)
    "en-US": "en-US-Standard-B",
    "en-GB": "en-GB-Standard-B",
    "ja-JP": "ja-JP-Standard-B",
    "ko-KR": "ko-KR-Standard-B",
    "fr-FR": "fr-FR-Standard-B",
    "de-DE": "de-DE-Standard-B",
    "es-ES": "es-ES-Standard-B",
}


class GoogleCloudTTS(BaseTTSAdapter):
    """
    Google Cloud Text-to-Speech adapter.

    Uses gcloud CLI for authentication, no API key management required.
    """

    def __init__(
        self,
        voice: Optional[str] = None,
        language: str = "cmn-TW",
        speed: float = 1.0,
    ):
        """
        Initialize Google Cloud TTS.

        Args:
            voice: Voice name (e.g., "cmn-TW-Standard-B")
            language: Language code (e.g., "cmn-TW", "en-GB")
            speed: Speaking speed (1.0 = normal)
        """
        super().__init__(voice=voice, language=language, speed=speed)

        # Set default voice based on language if not specified
        if self.voice is None:
            self.voice = VOICE_PRESETS.get(language, f"{language}-Standard-B")

        # Find gcloud path
        self.gcloud_path = self._find_gcloud()
        self.is_initialized = self.gcloud_path is not None

        if not self.is_initialized:
            logger.error("gcloud CLI not found. Install: brew install google-cloud-sdk")

    def _find_gcloud(self) -> Optional[str]:
        """Find the gcloud CLI path."""
        # Check if gcloud is in PATH
        if shutil.which("gcloud"):
            return "gcloud"

        # Common installation paths
        paths = [
            "/opt/homebrew/bin/gcloud",
            "/usr/local/bin/gcloud",
            os.path.expanduser("~/google-cloud-sdk/bin/gcloud"),
            "/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gcloud",
        ]

        for path in paths:
            if os.path.isfile(path):
                return path

        return None

    def _get_access_token(self) -> Optional[str]:
        """Get access token from gcloud."""
        try:
            result = subprocess.run(
                [self.gcloud_path, "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get access token: {e}")
            return None

    def _get_project_id(self) -> Optional[str]:
        """Get project ID from gcloud config."""
        try:
            result = subprocess.run(
                [self.gcloud_path, "config", "get-value", "project"],
                capture_output=True,
                text=True,
                check=True,
            )
            project_id = result.stdout.strip()
            if not project_id:
                logger.error("No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID")
                return None
            return project_id
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get project ID: {e}")
            return None

    def _synthesize(self, text: str) -> Optional[bytes]:
        """
        Call Google Cloud TTS API to synthesize speech.

        Args:
            text: Text to synthesize

        Returns:
            Audio content as bytes, or None on failure
        """
        token = self._get_access_token()
        if not token:
            return None

        project_id = self._get_project_id()
        if not project_id:
            return None

        # Prepare request body
        request_body = {
            "input": {"text": text},
            "voice": {
                "languageCode": self.language,
                "name": self.voice,
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 24000,
                "speakingRate": self.speed,
            },
        }

        # Make API request
        try:
            req = urllib.request.Request(
                "https://texttospeech.googleapis.com/v1/text:synthesize",
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "x-goog-user-project": project_id,
                    "Content-Type": "application/json; charset=utf-8",
                },
            )

            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))

            return base64.b64decode(result["audioContent"])

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.error(f"API error ({e.code}): {error_body}")
            return None
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None

    def speak(self, text: str) -> bool:
        """
        Speak the given text.

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized:
            logger.error("Google Cloud TTS not initialized")
            return False

        audio_content = self._synthesize(text)
        if audio_content is None:
            return False

        # Save to temp file and play
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_content)
                temp_path = f.name

            # Play audio using afplay (macOS)
            subprocess.run(["afplay", temp_path], check=True)

            # Clean up
            os.unlink(temp_path)
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to play audio: {e}")
            return False
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False

    def save_to_file(self, text: str, file_path: str) -> bool:
        """
        Save speech to an audio file.

        Args:
            text: Text to convert to speech
            file_path: Path to save the audio file

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized:
            logger.error("Google Cloud TTS not initialized")
            return False

        audio_content = self._synthesize(text)
        if audio_content is None:
            return False

        try:
            with open(file_path, "wb") as f:
                f.write(audio_content)
            return True
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return False

    def get_available_voices(self) -> list[str]:
        """
        Get list of available voices.

        Returns a subset of commonly used voices.
        Full list available at: https://cloud.google.com/text-to-speech/docs/voices
        """
        return [
            # Chinese
            "cmn-TW-Standard-A",
            "cmn-TW-Standard-B",
            "cmn-TW-Standard-C",
            "cmn-TW-Wavenet-A",
            "cmn-TW-Wavenet-B",
            "cmn-TW-Wavenet-C",
            "cmn-CN-Standard-A",
            "cmn-CN-Standard-B",
            "cmn-CN-Wavenet-A",
            "cmn-CN-Wavenet-B",
            # English
            "en-US-Standard-A",
            "en-US-Standard-B",
            "en-US-Standard-C",
            "en-US-Standard-D",
            "en-US-Wavenet-A",
            "en-US-Wavenet-B",
            "en-GB-Standard-A",
            "en-GB-Standard-B",
            "en-GB-Wavenet-A",
            "en-GB-Wavenet-B",
            # Japanese
            "ja-JP-Standard-A",
            "ja-JP-Standard-B",
            "ja-JP-Wavenet-A",
            "ja-JP-Wavenet-B",
        ]

    def set_language(self, language: str) -> bool:
        """
        Set the language and update voice to match.

        Args:
            language: Language code (e.g., "cmn-TW", "en-GB")

        Returns:
            True if successful
        """
        self.language = language
        # Update voice to match language if using default
        if language in VOICE_PRESETS:
            self.voice = VOICE_PRESETS[language]
        return True
