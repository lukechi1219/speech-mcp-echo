"""
Faster-Whisper STT adapter.

Uses faster-whisper for local speech-to-text transcription.
"""

import logging
import tempfile
import threading
import time
from typing import Callable, Optional

from speech_mcp_echo.stt_adapters import BaseSTTAdapter

logger = logging.getLogger(__name__)

# Audio parameters for recording
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 0.02
MAX_SILENCE_DURATION = 3.0  # seconds


class FasterWhisperSTT(BaseSTTAdapter):
    """
    Faster-Whisper local STT adapter.

    Uses faster-whisper for efficient local transcription.
    """

    def __init__(
        self,
        model: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "en",
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

        # Lazy initialization
        self.is_initialized = False

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

    def listen(self) -> str:
        """
        Listen for speech and return transcription.

        Returns:
            Transcribed text
        """
        self._ensure_initialized()

        # Record audio
        audio_path = self._record_audio()

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

    def _record_audio(self) -> str:
        """
        Record audio from microphone until silence detected.

        Returns:
            Path to temporary audio file
        """
        import pyaudio
        import numpy as np
        import wave

        logger.info("Starting audio recording...")

        audio = pyaudio.PyAudio()

        # Open stream
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )

        frames = []
        silence_start = None
        has_speech = False

        try:
            while True:
                # Read audio chunk
                data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)

                # Convert to numpy for analysis
                audio_data = np.frombuffer(data, dtype=np.int16)
                audio_float = audio_data.astype(np.float32) / 32768.0

                # Calculate RMS amplitude
                rms = np.sqrt(np.mean(audio_float**2))

                # Detect speech/silence
                if rms > SILENCE_THRESHOLD:
                    has_speech = True
                    silence_start = None
                else:
                    if has_speech and silence_start is None:
                        silence_start = time.time()
                    elif silence_start is not None:
                        silence_duration = time.time() - silence_start
                        if silence_duration >= MAX_SILENCE_DURATION:
                            logger.info("Silence detected, stopping recording")
                            break

        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))

        logger.info(f"Audio saved to: {temp_path}")
        return temp_path

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
