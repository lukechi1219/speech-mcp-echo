"""
STT adapters for speech-mcp-echo.

Each adapter implements BaseSTTAdapter to provide speech-to-text capabilities.
Supported engines: faster-whisper (local), OpenAI Whisper API, Google Speech.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable


class BaseSTTAdapter(ABC):
    """
    Base class for all STT adapters.

    All STT engines must implement this interface.
    """

    def __init__(
        self,
        model: str = "base",
        language: str = "en",
    ):
        """
        Initialize the STT adapter.

        Args:
            model: Model identifier (engine-specific)
            language: Language code for transcription
        """
        self.model = model
        self.language = language
        self.is_initialized = False

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        pass

    @abstractmethod
    def listen(self) -> str:
        """
        Listen for speech and return transcription.

        This method handles audio capture and transcription.

        Returns:
            Transcribed text
        """
        pass

    def transcribe_stream(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Stream transcription with callbacks for partial results.

        Args:
            on_partial: Callback for partial transcription updates
            on_final: Callback for final transcription

        Returns:
            Final transcribed text
        """
        # Default implementation falls back to non-streaming
        return self.listen()

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """
        Get list of available models.

        Returns:
            List of model identifiers
        """
        pass


# Import available adapters
try:
    from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT
except ImportError:
    pass

try:
    from speech_mcp_echo.stt_adapters.openai_whisper_adapter import OpenAIWhisperSTT
except ImportError:
    pass

try:
    from speech_mcp_echo.stt_adapters.google_speech_adapter import GoogleSpeechSTT
except ImportError:
    pass
