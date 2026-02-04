"""
OpenAI TTS adapter.

Uses the OpenAI Audio API for text-to-speech.
Requires an OpenAI API key set via OPENAI_API_KEY environment variable.

API Reference: https://platform.openai.com/docs/api-reference/audio/createSpeech
"""

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

# Available voices
OPENAI_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

# Available models
OPENAI_MODELS = ["tts-1", "tts-1-hd"]

# Voice characteristics for selection guidance
VOICE_DESCRIPTIONS = {
    "alloy": "Neutral, balanced",
    "echo": "Warm, conversational",
    "fable": "Expressive, storytelling",
    "onyx": "Deep, authoritative",
    "nova": "Friendly, upbeat",
    "shimmer": "Clear, professional",
}


class OpenAITTS(BaseTTSAdapter):
    """
    OpenAI Text-to-Speech adapter.

    Uses the OpenAI Audio API (tts-1 or tts-1-hd models).

    Setup:
    ------
    Set your OpenAI API key:
        export OPENAI_API_KEY="sk-..."

    Or pass it directly:
        tts = OpenAITTS(api_key="sk-...")

    Available Voices:
    -----------------
    - alloy: Neutral, balanced
    - echo: Warm, conversational
    - fable: Expressive, storytelling
    - onyx: Deep, authoritative (good for JARVIS-style)
    - nova: Friendly, upbeat
    - shimmer: Clear, professional

    Models:
    -------
    - tts-1: Optimized for speed (lower latency)
    - tts-1-hd: Optimized for quality (higher fidelity)
    """

    def __init__(
        self,
        voice: Optional[str] = "onyx",
        language: str = "en",
        speed: float = 1.0,
        model: str = "tts-1",
        api_key: Optional[str] = None,
        response_format: str = "mp3",
    ):
        """
        Initialize OpenAI TTS.

        Args:
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            language: Language code (OpenAI auto-detects, this is for compatibility)
            speed: Speaking speed (0.25 to 4.0, default 1.0)
            model: Model to use (tts-1 for speed, tts-1-hd for quality)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
        """
        super().__init__(voice=voice, language=language, speed=speed)

        self.model = model
        self.response_format = response_format
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")

        # Validate voice
        if self.voice not in OPENAI_VOICES:
            logger.warning(f"Unknown voice '{self.voice}', defaulting to 'onyx'")
            self.voice = "onyx"

        # Validate model
        if self.model not in OPENAI_MODELS:
            logger.warning(f"Unknown model '{self.model}', defaulting to 'tts-1'")
            self.model = "tts-1"

        # Validate speed (OpenAI supports 0.25 to 4.0)
        if not 0.25 <= self.speed <= 4.0:
            logger.warning(f"Speed {self.speed} out of range [0.25, 4.0], clamping")
            self.speed = max(0.25, min(4.0, self.speed))

        self._initialize()

    def _initialize(self):
        """Check if API key is available."""
        if self._api_key:
            self.is_initialized = True
            logger.info(f"OpenAI TTS initialized (model={self.model}, voice={self.voice})")
        else:
            self.is_initialized = False
            logger.error(
                "OpenAI TTS not initialized. Set OPENAI_API_KEY environment variable:\n"
                "  export OPENAI_API_KEY='sk-...'"
            )

    def _synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize speech using OpenAI API."""
        if not self._api_key:
            logger.error("No API key available")
            return None

        request_body = {
            "model": self.model,
            "input": text,
            "voice": self.voice,
            "speed": self.speed,
            "response_format": self.response_format,
        }

        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/audio/speech",
                data=json.dumps(request_body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )

            with urllib.request.urlopen(req) as response:
                return response.read()

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get("error", {}).get("message", error_body)
            except json.JSONDecodeError:
                error_msg = error_body
            logger.error(f"OpenAI API error ({e.code}): {error_msg}")
            return None
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None

    def _get_file_extension(self) -> str:
        """Get file extension for current response format."""
        format_extensions = {
            "mp3": ".mp3",
            "opus": ".opus",
            "aac": ".aac",
            "flac": ".flac",
            "wav": ".wav",
            "pcm": ".pcm",
        }
        return format_extensions.get(self.response_format, ".mp3")

    def _play_audio(self, audio_path: str) -> bool:
        """Play audio file using platform-appropriate method."""
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                # afplay supports mp3, wav, aac, etc.
                subprocess.run(["afplay", audio_path], check=True)
            elif system == "Linux":
                # Try different players based on format
                if self.response_format in ["mp3", "opus", "aac", "flac"]:
                    # Use ffplay for compressed formats
                    players = ["ffplay -nodisp -autoexit", "mpv --no-video", "cvlc --play-and-exit"]
                else:
                    # Use aplay for wav/pcm
                    players = ["aplay", "paplay", "ffplay -nodisp -autoexit"]

                for player in players:
                    if shutil.which(player.split()[0]):
                        subprocess.run(player.split() + [audio_path], check=True)
                        return True

                logger.error("No audio player found. Install: sudo apt install ffmpeg")
                return False
            elif system == "Windows":
                # Windows Media Player handles most formats
                if self.response_format == "mp3":
                    subprocess.run(
                        ["powershell", "-c", f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()"],
                        check=True,
                    )
                else:
                    # Use start command for other formats
                    subprocess.run(["start", "", audio_path], shell=True, check=True)
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
            logger.error("OpenAI TTS not initialized")
            return False

        if not text.strip():
            logger.warning("Empty text provided")
            return True

        audio_content = self._synthesize(text)
        if audio_content is None:
            return False

        # Save to temp file and play
        try:
            suffix = self._get_file_extension()
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
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
            logger.error("OpenAI TTS not initialized")
            return False

        audio_content = self._synthesize(text)
        if audio_content is None:
            return False

        try:
            with open(file_path, "wb") as f:
                f.write(audio_content)
            logger.info(f"Audio saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return False

    def get_available_voices(self) -> list[str]:
        """Get list of available voices."""
        return OPENAI_VOICES.copy()

    def get_voice_descriptions(self) -> dict[str, str]:
        """Get descriptions for each voice."""
        return VOICE_DESCRIPTIONS.copy()

    def set_model(self, model: str) -> bool:
        """Set the model (tts-1 or tts-1-hd)."""
        if model not in OPENAI_MODELS:
            logger.error(f"Invalid model: {model}. Use 'tts-1' or 'tts-1-hd'")
            return False
        self.model = model
        logger.info(f"Model set to {model}")
        return True

    def set_response_format(self, fmt: str) -> bool:
        """Set the audio response format."""
        valid_formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]
        if fmt not in valid_formats:
            logger.error(f"Invalid format: {fmt}. Use one of {valid_formats}")
            return False
        self.response_format = fmt
        logger.info(f"Response format set to {fmt}")
        return True

    @property
    def current_model(self) -> str:
        """Return the current model being used."""
        return self.model
