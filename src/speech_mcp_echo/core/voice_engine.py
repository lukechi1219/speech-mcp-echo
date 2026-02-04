"""
VoiceEngine - Protocol-agnostic core voice functionality.

Handles STT, TTS, and summarization without being tied to any specific CLI protocol.
The MCP server (server.py) uses this class directly for voice operations.
"""

import logging
from typing import Optional, Callable

from speech_mcp_echo.config import load_config, get_setting

logger = logging.getLogger(__name__)


class VoiceEngine:
    """
    Core voice engine that provides STT, TTS, and summarization.

    This class is protocol-agnostic and used directly by the MCP server.
    """

    def __init__(self):
        """Initialize the voice engine."""
        self.config = load_config()

        # Lazy-loaded components
        self._stt_engine = None
        self._tts_engine = None
        self._summarizer = None

        # Callbacks for state changes (useful for UI updates)
        self._on_listening_start: Optional[Callable] = None
        self._on_listening_end: Optional[Callable] = None
        self._on_speaking_start: Optional[Callable] = None
        self._on_speaking_end: Optional[Callable] = None

        logger.info("VoiceEngine initialized")

    @property
    def stt_engine(self):
        """Lazy-load STT engine based on configuration."""
        if self._stt_engine is None:
            self._stt_engine = self._create_stt_engine()
        return self._stt_engine

    @property
    def tts_engine(self):
        """Lazy-load TTS engine based on configuration."""
        if self._tts_engine is None:
            self._tts_engine = self._create_tts_engine()
        return self._tts_engine

    @property
    def summarizer(self):
        """Lazy-load summarizer based on configuration."""
        if self._summarizer is None:
            self._summarizer = self._create_summarizer()
        return self._summarizer

    def _create_stt_engine(self):
        """Create STT engine based on configuration."""
        engine_name = get_setting("stt", "engine", "faster-whisper")
        logger.info(f"Creating STT engine: {engine_name}")

        if engine_name == "faster-whisper":
            from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT
            return FasterWhisperSTT(
                model=get_setting("stt", "model", "base"),
                device=get_setting("stt", "device", "cpu"),
                compute_type=get_setting("stt", "compute_type", "int8"),
            )
        elif engine_name == "openai":
            from speech_mcp_echo.stt_adapters.openai_whisper_adapter import OpenAIWhisperSTT
            return OpenAIWhisperSTT()
        elif engine_name == "google":
            from speech_mcp_echo.stt_adapters.google_speech_adapter import GoogleSpeechSTT
            return GoogleSpeechSTT()
        else:
            raise ValueError(f"Unknown STT engine: {engine_name}")

    def _create_tts_engine(self):
        """Create TTS engine based on configuration."""
        engine_name = get_setting("tts", "engine", "google")
        logger.info(f"Creating TTS engine: {engine_name}")

        if engine_name == "google":
            from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS
            return GoogleCloudTTS(
                voice=get_setting("tts", "voice", "cmn-TW-Standard-B"),
                language=get_setting("tts", "language", "cmn-TW"),
            )
        elif engine_name == "kokoro":
            from speech_mcp_echo.tts_adapters.kokoro_adapter import KokoroTTS
            return KokoroTTS(
                voice=get_setting("tts", "voice", "af_heart"),
            )
        elif engine_name == "openai":
            from speech_mcp_echo.tts_adapters.openai_tts_adapter import OpenAITTS
            return OpenAITTS(
                voice=get_setting("tts", "voice", "alloy"),
            )
        elif engine_name == "pyttsx3":
            from speech_mcp_echo.tts_adapters.pyttsx3_adapter import Pyttsx3TTS
            return Pyttsx3TTS()
        else:
            raise ValueError(f"Unknown TTS engine: {engine_name}")

    def _create_summarizer(self):
        """Create summarizer based on configuration."""
        if not get_setting("summarizer", "enabled", True):
            return None

        engine_name = get_setting("summarizer", "engine", "local")
        logger.info(f"Creating summarizer: {engine_name}")

        if engine_name == "local":
            from speech_mcp_echo.summarizer.local_summarizer import LocalSummarizer
            return LocalSummarizer(
                max_input_length=get_setting("summarizer", "max_input_length", 500),
                target_length=get_setting("summarizer", "target_length", 150),
                personality=get_setting("summarizer", "personality", "jarvis"),
                language=get_setting("summarizer", "language", "en"),
            )
        elif engine_name == "llm":
            from speech_mcp_echo.summarizer.llm_summarizer import LLMSummarizer
            return LLMSummarizer(
                personality=get_setting("summarizer", "personality", "jarvis"),
                language=get_setting("summarizer", "language", "en"),
            )
        else:
            return None

    def listen(self, timeout: Optional[int] = None) -> str:
        """
        Listen for speech and return transcription.

        Args:
            timeout: Optional timeout in seconds (overrides config default)

        Returns:
            Transcribed text from speech
        """
        if self._on_listening_start:
            self._on_listening_start()

        try:
            # Get timeout from parameter or config
            if timeout is None:
                timeout = get_setting("stt", "timeout", default=45)

            logger.info(f"Starting voice listening (timeout: {timeout}s)...")
            transcription = self.stt_engine.listen(timeout=timeout)

            if not transcription:
                logger.warning("No speech detected within timeout")
                return ""

            logger.info(f"Transcription: {transcription[:50]}...")
            return transcription
        finally:
            if self._on_listening_end:
                self._on_listening_end()

    def speak(self, text: str, summarize: bool = True) -> str:
        """
        Speak text using TTS, optionally summarizing first.

        Args:
            text: Text to speak
            summarize: Whether to summarize long text first

        Returns:
            The text that was actually spoken (may be summarized)
        """
        if self._on_speaking_start:
            self._on_speaking_start()

        try:
            # Summarize if enabled and text is long
            spoken_text = text
            if summarize and self.summarizer:
                if self.summarizer.should_summarize(text):
                    spoken_text = self.summarizer.summarize(text)
                    logger.info(f"Summarized text from {len(text)} to {len(spoken_text)} chars")

            # Speak the text
            self.tts_engine.speak(spoken_text)
            return spoken_text
        finally:
            if self._on_speaking_end:
                self._on_speaking_end()

    def set_callbacks(
        self,
        on_listening_start: Optional[Callable] = None,
        on_listening_end: Optional[Callable] = None,
        on_speaking_start: Optional[Callable] = None,
        on_speaking_end: Optional[Callable] = None,
    ):
        """Set callbacks for state changes (useful for UI updates)."""
        self._on_listening_start = on_listening_start
        self._on_listening_end = on_listening_end
        self._on_speaking_start = on_speaking_start
        self._on_speaking_end = on_speaking_end
