"""
Faster-Whisper STT adapter.

Uses faster-whisper for local speech-to-text transcription.
Audio recording is delegated to AudioProcessor for consistent behavior
(including audio cue playback).
"""

import logging
from typing import Callable, Optional

from speech_mcp_echo.stt_adapters import BaseSTTAdapter

logger = logging.getLogger(__name__)


class FasterWhisperSTT(BaseSTTAdapter):
    """
    Faster-Whisper local STT adapter.

    Uses faster-whisper for efficient local transcription.
    Audio recording is handled by AudioProcessor for consistent behavior.
    """

    def __init__(
        self,
        model: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "auto",
    ):
        """
        Initialize faster-whisper STT.

        Args:
            model: Model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to use (cpu, cuda)
            compute_type: Compute type (int8, float16, float32)
            language: Language code for transcription
        """
        super().__init__(model=model, language=language)

        self.device = device
        self.compute_type = compute_type
        self._whisper_model = None
        self._audio_processor = None

        # Lazy initialization
        self.is_initialized = False

    def _get_audio_processor(self):
        """Get or create the AudioProcessor instance."""
        if self._audio_processor is None:
            from speech_mcp_echo.audio_processor import AudioProcessor
            self._audio_processor = AudioProcessor()
        return self._audio_processor

    def _ensure_initialized(self):
        """Lazy initialize the whisper model."""
        if self._whisper_model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading faster-whisper model: {self.model}")
            self._whisper_model = WhisperModel(
                self.model,
                device=self.device,
                compute_type=self.compute_type,
            )
            self.is_initialized = True
            logger.info("Faster-whisper model loaded successfully")
        except ImportError:
            logger.error("faster-whisper not installed. Install: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            raise

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        self._ensure_initialized()

        try:
            segments, info = self._whisper_model.transcribe(
                audio_path,
                language=self.language if self.language != "auto" else None,
                task="transcribe",  # Keep original language, don't translate to English
                beam_size=5,
                vad_filter=True,
            )

            # Combine all segments
            transcription = " ".join(segment.text for segment in segments)
            transcription = transcription.strip()

            logger.info(f"Transcription complete: {transcription[:50]}...")
            return transcription

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def listen(self, timeout: Optional[int] = None) -> str:
        """
        Listen for speech and return transcription.

        Args:
            timeout: Maximum seconds to wait for audio (None = wait indefinitely)

        Returns:
            Transcribed text or empty string if timeout
        """
        self._ensure_initialized()

        # Record audio with timeout
        audio_path = self._record_audio(timeout=timeout)

        # Return empty string if timeout occurred
        if not audio_path:
            logger.warning("Audio recording timeout - no transcription available")
            return ""

        try:
            # Transcribe
            return self.transcribe(audio_path)
        finally:
            # Clean up temp file
            import os
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def _record_audio(self, timeout: Optional[int] = None) -> Optional[str]:
        """
        Record audio from microphone until silence detected.

        Delegates to AudioProcessor for consistent behavior including:
        - Audio cue playback (start/stop listening sounds)
        - Device selection
        - Silence detection

        Args:
            timeout: Maximum seconds to wait for audio (None = wait indefinitely)

        Returns:
            Path to temporary audio file, or None if timeout occurred
        """
        logger.info(
            f"Starting audio recording (timeout: {timeout}s)..."
            if timeout
            else "Starting audio recording..."
        )

        audio_processor = self._get_audio_processor()
        return audio_processor.record_until_silence(timeout=timeout)

    def transcribe_stream(
        self,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Stream transcription with callbacks.

        Note: faster-whisper doesn't support true streaming,
        so this simulates it with periodic transcription.

        Args:
            on_partial: Callback for partial transcription updates
            on_final: Callback for final transcription

        Returns:
            Final transcribed text
        """
        self._ensure_initialized()

        # For now, fall back to non-streaming
        # TODO: Implement pseudo-streaming with chunked audio
        result = self.listen()

        if on_final:
            on_final(result)

        return result

    def get_available_models(self) -> list[str]:
        """Get list of available faster-whisper models."""
        return [
            "tiny",
            "tiny.en",
            "base",
            "base.en",
            "small",
            "small.en",
            "medium",
            "medium.en",
            "large-v2",
            "large-v3",
        ]
