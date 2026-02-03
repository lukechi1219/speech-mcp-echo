"""
Google Cloud Speech-to-Text adapter for speech-mcp-echo.

Uses Google Cloud Speech API for cloud-based STT.
"""

import logging
from typing import Optional

from speech_mcp_echo.stt_adapters import BaseSTTAdapter

logger = logging.getLogger(__name__)


class GoogleSpeechSTT(BaseSTTAdapter):
    """
    Google Cloud Speech-to-Text adapter.

    Uses Google Cloud Speech API for transcription.
    Requires gcloud CLI to be configured (similar to TTS).
    """

    def __init__(
        self,
        model: str = "default",
        language: str = "en-US",
    ):
        super().__init__(model=model, language=language)

        # Check for gcloud
        import shutil
        self.is_initialized = shutil.which("gcloud") is not None

        if not self.is_initialized:
            logger.warning("gcloud CLI not found. Install: brew install google-cloud-sdk")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file using Google Cloud Speech API."""
        if not self.is_initialized:
            raise RuntimeError("gcloud CLI not configured")

        # TODO: Implement Google Cloud Speech API transcription
        # For now, fall back to faster-whisper
        logger.warning("Google Speech STT not fully implemented, using faster-whisper fallback")

        from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT

        fallback = FasterWhisperSTT(model="base", language=self.language[:2])
        return fallback.transcribe(audio_path)

    def listen(self) -> str:
        """Listen and transcribe using Google Cloud Speech."""
        from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT

        # Use faster-whisper for recording
        temp_adapter = FasterWhisperSTT.__new__(FasterWhisperSTT)
        temp_adapter.is_initialized = True
        audio_path = temp_adapter._record_audio()

        try:
            return self.transcribe(audio_path)
        finally:
            import os
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def get_available_models(self) -> list[str]:
        """Get available Google Speech models."""
        return [
            "default",
            "phone_call",
            "video",
            "command_and_search",
        ]
