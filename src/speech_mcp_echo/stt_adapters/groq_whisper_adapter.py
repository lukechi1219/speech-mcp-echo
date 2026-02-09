"""
Groq Whisper API adapter for speech-mcp-echo.

Uses Groq's OpenAI-compatible API with whisper-large-v3-turbo model.
Provides significantly better accuracy (WER ~12%) than local base model (~23%)
at 216x real-time speed, with a generous free tier.

Groq API is fully OpenAI-compatible, so we reuse the openai SDK
with a different base_url and API key.
"""

import logging
from typing import Optional

from speech_mcp_echo.stt_adapters import BaseSTTAdapter
from speech_mcp_echo.config import get_api_key

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "whisper-large-v3-turbo"


class GroqWhisperSTT(BaseSTTAdapter):
    """
    Groq Whisper API STT adapter.

    Uses Groq's cloud-based Whisper API (OpenAI-compatible) for transcription.
    Requires GROQ_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        language: str = "en",
    ):
        super().__init__(model=model, language=language)

        self._audio_processor = None
        self.api_key = get_api_key("groq")
        self.is_initialized = self.api_key is not None

        if not self.is_initialized:
            logger.warning("Groq API key not found. Set GROQ_API_KEY environment variable.")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file using Groq Whisper API."""
        if not self.is_initialized:
            raise RuntimeError("Groq API key not configured. Set GROQ_API_KEY environment variable.")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, base_url=GROQ_BASE_URL)

            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=self.language if self.language != "auto" else None,
                )

            return response.text
        except ImportError:
            logger.error("openai package not installed. Install: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Groq transcription failed: {e}")
            raise

    def listen(self, timeout: Optional[int] = None) -> str:
        """Listen and transcribe using Groq Whisper."""
        if not self.is_initialized:
            raise RuntimeError("Groq API key not configured. Set GROQ_API_KEY environment variable.")

        audio_path = self._record_audio(timeout=timeout)

        if not audio_path:
            logger.warning("Audio recording timeout - no transcription available")
            return ""

        try:
            return self.transcribe(audio_path)
        finally:
            import os
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def _record_audio(self, timeout: Optional[int] = None) -> Optional[str]:
        """Record audio from microphone until silence detected."""
        if self._audio_processor is None:
            from speech_mcp_echo.audio_processor import AudioProcessor
            self._audio_processor = AudioProcessor()
        return self._audio_processor.record_until_silence(timeout=timeout)

    def get_available_models(self) -> list[str]:
        """Get available Groq Whisper models."""
        return [
            "whisper-large-v3-turbo",
            "whisper-large-v3",
            "distil-whisper-large-v3-en",
        ]
