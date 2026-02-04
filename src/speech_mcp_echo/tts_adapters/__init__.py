"""
TTS adapters for speech-mcp-echo.

Each adapter implements BaseTTSAdapter to provide text-to-speech capabilities.
Supported engines: Google Cloud TTS, OpenAI TTS.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseTTSAdapter(ABC):
    """
    Base class for all TTS adapters.

    All TTS engines must implement this interface.
    """

    def __init__(
        self,
        voice: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0,
    ):
        """
        Initialize the TTS adapter.

        Args:
            voice: Voice identifier (engine-specific)
            language: Language code
            speed: Speaking speed (1.0 = normal)
        """
        self.voice = voice
        self.language = language
        self.speed = speed
        self.is_initialized = False

    @abstractmethod
    def speak(self, text: str) -> bool:
        """
        Speak the given text aloud.

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def save_to_file(self, text: str, file_path: str) -> bool:
        """
        Save speech to an audio file.

        Args:
            text: Text to convert to speech
            file_path: Path to save the audio file

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_available_voices(self) -> list[str]:
        """
        Get list of available voices.

        Returns:
            List of voice identifiers
        """
        pass

    def set_voice(self, voice: str) -> bool:
        """Set the voice to use."""
        self.voice = voice
        return True

    def set_speed(self, speed: float) -> bool:
        """Set the speaking speed."""
        self.speed = speed
        return True


# Import available adapters
try:
    from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS
except ImportError:
    pass

try:
    from speech_mcp_echo.tts_adapters.openai_tts_adapter import OpenAITTS
except ImportError:
    pass
