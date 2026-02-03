"""
Google Cloud TTS adapter.

Supports multiple authentication methods:
1. gcloud CLI (recommended for developers)
2. Service Account JSON key file (for production/servers)
3. google-cloud-texttospeech library (if installed)
"""

import base64
import json
import logging
import os
import platform
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

    Authentication methods (in order of preference):
    1. gcloud CLI - if installed, uses `gcloud auth print-access-token`
    2. Service Account - if GOOGLE_APPLICATION_CREDENTIALS is set
    3. Client Library - if google-cloud-texttospeech is installed

    Setup Options:
    --------------
    Option A: gcloud CLI (easiest for developers)
        brew install google-cloud-sdk
        gcloud auth login
        gcloud config set project YOUR_PROJECT_ID

    Option B: Service Account (for servers/production)
        1. Create service account in Google Cloud Console
        2. Download JSON key file
        3. Set environment variable:
           export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
        4. Optionally set project ID:
           export GOOGLE_CLOUD_PROJECT="your-project-id"

    Option C: Client Library (most Pythonic)
        pip install google-cloud-texttospeech
        # Then use Option A or B for authentication
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

        # Determine authentication method
        self._auth_method = None
        self._gcloud_path = None
        self._client = None  # For google-cloud-texttospeech library
        self._credentials = None
        self._project_id = None

        self._initialize_auth()

    def _initialize_auth(self):
        """Initialize authentication using available methods."""
        # Try Method 1: gcloud CLI
        self._gcloud_path = self._find_gcloud()
        if self._gcloud_path:
            self._auth_method = "gcloud"
            self.is_initialized = True
            logger.info("Using gcloud CLI for authentication")
            return

        # Try Method 2: Service Account credentials
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and os.path.isfile(creds_path):
            try:
                self._load_service_account(creds_path)
                self._auth_method = "service_account"
                self.is_initialized = True
                logger.info("Using service account for authentication")
                return
            except Exception as e:
                logger.warning(f"Failed to load service account: {e}")

        # Try Method 3: google-cloud-texttospeech library
        try:
            from google.cloud import texttospeech

            self._client = texttospeech.TextToSpeechClient()
            self._auth_method = "client_library"
            self.is_initialized = True
            logger.info("Using google-cloud-texttospeech library")
            return
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to initialize client library: {e}")

        # No authentication method available
        self.is_initialized = False
        logger.error(
            "Google Cloud TTS not initialized. Options:\n"
            "  1. Install gcloud CLI: brew install google-cloud-sdk\n"
            "  2. Set GOOGLE_APPLICATION_CREDENTIALS to service account JSON\n"
            "  3. Install: pip install google-cloud-texttospeech"
        )

    def _find_gcloud(self) -> Optional[str]:
        """Find the gcloud CLI path."""
        if shutil.which("gcloud"):
            return "gcloud"

        # Common installation paths
        paths = [
            "/opt/homebrew/bin/gcloud",
            "/usr/local/bin/gcloud",
            os.path.expanduser("~/google-cloud-sdk/bin/gcloud"),
            "/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin/gcloud",
            # Windows paths
            os.path.expanduser("~/AppData/Local/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd"),
            "C:/Program Files (x86)/Google/Cloud SDK/google-cloud-sdk/bin/gcloud.cmd",
        ]

        for path in paths:
            if os.path.isfile(path):
                return path

        return None

    def _load_service_account(self, creds_path: str):
        """Load service account credentials from JSON file."""
        with open(creds_path) as f:
            self._credentials = json.load(f)

        # Get project ID from credentials or environment
        self._project_id = (
            os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
            or self._credentials.get("project_id")
        )

        if not self._project_id:
            raise ValueError("Project ID not found. Set GOOGLE_CLOUD_PROJECT environment variable.")

    def _get_access_token_gcloud(self) -> Optional[str]:
        """Get access token from gcloud CLI."""
        try:
            result = subprocess.run(
                [self._gcloud_path, "auth", "print-access-token"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get access token from gcloud: {e}")
            return None

    def _get_access_token_service_account(self) -> Optional[str]:
        """Get access token using service account credentials."""
        try:
            import time
            import hashlib
            import hmac

            # For service accounts, we need to generate a JWT and exchange it for an access token
            # This is a simplified implementation - for production, use google-auth library

            # Try using google-auth library if available
            try:
                from google.oauth2 import service_account
                from google.auth.transport.requests import Request

                credentials = service_account.Credentials.from_service_account_file(
                    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                credentials.refresh(Request())
                return credentials.token
            except ImportError:
                pass

            # Fallback: Manual JWT generation (requires PyJWT)
            try:
                import jwt

                now = int(time.time())
                payload = {
                    "iss": self._credentials["client_email"],
                    "sub": self._credentials["client_email"],
                    "aud": "https://oauth2.googleapis.com/token",
                    "iat": now,
                    "exp": now + 3600,
                    "scope": "https://www.googleapis.com/auth/cloud-platform",
                }

                signed_jwt = jwt.encode(
                    payload,
                    self._credentials["private_key"],
                    algorithm="RS256",
                )

                # Exchange JWT for access token
                token_request = urllib.request.Request(
                    "https://oauth2.googleapis.com/token",
                    data=urllib.parse.urlencode({
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": signed_jwt,
                    }).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                with urllib.request.urlopen(token_request) as response:
                    token_data = json.loads(response.read().decode())
                    return token_data["access_token"]

            except ImportError:
                logger.error(
                    "Service account auth requires google-auth or PyJWT. "
                    "Install: pip install google-auth google-auth-httplib2"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to get access token from service account: {e}")
            return None

    def _get_project_id_gcloud(self) -> Optional[str]:
        """Get project ID from gcloud config."""
        # First check environment variables
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
        if project_id:
            return project_id

        try:
            result = subprocess.run(
                [self._gcloud_path, "config", "get-value", "project"],
                capture_output=True,
                text=True,
                check=True,
            )
            project_id = result.stdout.strip()
            if project_id:
                return project_id
        except subprocess.CalledProcessError:
            pass

        logger.error(
            "No GCP project set. Either:\n"
            "  - Run: gcloud config set project YOUR_PROJECT_ID\n"
            "  - Set: export GOOGLE_CLOUD_PROJECT=your-project-id"
        )
        return None

    def _synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech using the configured authentication method."""
        if self._auth_method == "client_library":
            return self._synthesize_with_library(text)
        else:
            return self._synthesize_with_rest_api(text)

    def _synthesize_with_library(self, text: str) -> Optional[bytes]:
        """Synthesize using google-cloud-texttospeech library."""
        try:
            from google.cloud import texttospeech

            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language,
                name=self.voice,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=24000,
                speaking_rate=self.speed,
            )

            response = self._client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            return response.audio_content

        except Exception as e:
            logger.error(f"Client library synthesis failed: {e}")
            return None

    def _synthesize_with_rest_api(self, text: str) -> Optional[bytes]:
        """Synthesize using REST API with token authentication."""
        # Get access token based on auth method
        if self._auth_method == "gcloud":
            token = self._get_access_token_gcloud()
            project_id = self._get_project_id_gcloud()
        elif self._auth_method == "service_account":
            token = self._get_access_token_service_account()
            project_id = self._project_id
        else:
            logger.error("No valid authentication method")
            return None

        if not token or not project_id:
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

    def _play_audio(self, audio_path: str) -> bool:
        """Play audio file using platform-appropriate method."""
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                subprocess.run(["afplay", audio_path], check=True)
            elif system == "Linux":
                # Try aplay (ALSA), then paplay (PulseAudio), then ffplay
                for player in ["aplay", "paplay", "ffplay -nodisp -autoexit"]:
                    if shutil.which(player.split()[0]):
                        subprocess.run(player.split() + [audio_path], check=True)
                        break
                else:
                    logger.error("No audio player found. Install: sudo apt install alsa-utils")
                    return False
            elif system == "Windows":
                # Use Windows Media Player or PowerShell
                subprocess.run(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()"],
                    check=True,
                )
            else:
                logger.error(f"Unsupported platform: {system}")
                return False

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to play audio: {e}")
            return False

    def speak(self, text: str) -> bool:
        """Speak the given text."""
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

            result = self._play_audio(temp_path)

            # Clean up
            os.unlink(temp_path)
            return result

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False

    def save_to_file(self, text: str, file_path: str) -> bool:
        """Save speech to an audio file."""
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
        """Get list of available voices."""
        return [
            # Chinese
            "cmn-TW-Standard-A", "cmn-TW-Standard-B", "cmn-TW-Standard-C",
            "cmn-TW-Wavenet-A", "cmn-TW-Wavenet-B", "cmn-TW-Wavenet-C",
            "cmn-CN-Standard-A", "cmn-CN-Standard-B",
            "cmn-CN-Wavenet-A", "cmn-CN-Wavenet-B",
            # English
            "en-US-Standard-A", "en-US-Standard-B", "en-US-Standard-C", "en-US-Standard-D",
            "en-US-Wavenet-A", "en-US-Wavenet-B",
            "en-GB-Standard-A", "en-GB-Standard-B",
            "en-GB-Wavenet-A", "en-GB-Wavenet-B",
            # Japanese
            "ja-JP-Standard-A", "ja-JP-Standard-B",
            "ja-JP-Wavenet-A", "ja-JP-Wavenet-B",
        ]

    def set_language(self, language: str) -> bool:
        """Set the language and update voice to match."""
        self.language = language
        if language in VOICE_PRESETS:
            self.voice = VOICE_PRESETS[language]
        return True

    @property
    def auth_method(self) -> Optional[str]:
        """Return the current authentication method being used."""
        return self._auth_method
