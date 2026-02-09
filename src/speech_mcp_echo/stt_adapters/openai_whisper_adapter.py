"""
OpenAI Whisper API adapter for speech-mcp-echo.

Uses OpenAI's Whisper API for cloud-based STT.
"""

import logging
from typing import Optional

from speech_mcp_echo.stt_adapters import BaseSTTAdapter
from speech_mcp_echo.config import get_api_key

logger = logging.getLogger(__name__)


class OpenAIWhisperSTT(BaseSTTAdapter):
    """
    OpenAI Whisper API STT adapter.

    Uses OpenAI's cloud-based Whisper API for transcription.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(
        self,
        model: str = "whisper-1",
        language: str = "en",
    ):
        super().__init__(model=model, language=language)

        self._audio_processor = None
        self.api_key = get_api_key("openai")
        self.is_initialized = self.api_key is not None

        if not self.is_initialized:
            logger.warning("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file using OpenAI Whisper API."""
        if not self.is_initialized:
            raise RuntimeError("OpenAI API key not configured")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

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
            logger.error(f"OpenAI transcription failed: {e}")
            raise

    def listen(self, timeout: Optional[int] = None) -> str:
        """Listen and transcribe using OpenAI Whisper."""
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
        """Get available OpenAI Whisper models."""
        return ["whisper-1"]
