"""
Mock PyAudio implementation for testing.

Provides thread-safe mocks for PyAudio functionality without requiring
actual audio devices. Useful for testing audio capture and playback logic.
"""

import threading
import time
from typing import Optional, Callable, List, Dict, Any
from unittest.mock import MagicMock
import numpy as np


class MockAudioStream:
    """
    Thread-safe mock audio stream.

    Simulates PyAudio stream behavior for testing audio capture/playback
    without accessing real audio devices.
    """

    def __init__(
        self,
        format: int,
        channels: int,
        rate: int,
        input: bool = False,
        output: bool = False,
        frames_per_buffer: int = 1024,
        input_device_index: Optional[int] = None,
        output_device_index: Optional[int] = None,
    ):
        """
        Initialize mock audio stream.

        Args:
            format: Audio format (e.g., pyaudio.paInt16)
            channels: Number of audio channels
            rate: Sample rate in Hz
            input: Whether stream is for input (recording)
            output: Whether stream is for output (playback)
            frames_per_buffer: Number of frames per buffer
            input_device_index: Input device index
            output_device_index: Output device index
        """
        self.format = format
        self.channels = channels
        self.rate = rate
        self.is_input = input
        self.is_output = output
        self.frames_per_buffer = frames_per_buffer
        self.input_device_index = input_device_index
        self.output_device_index = output_device_index

        self._active = False
        self._lock = threading.Lock()
        self._data_generator: Optional[Callable] = None
        self._read_count = 0
        self._write_count = 0

        # Default: generate silence
        self.set_input_data_generator(self._generate_silence)

    def _generate_silence(self, num_frames: int) -> bytes:
        """Generate silent audio data."""
        silence = np.zeros(num_frames * self.channels, dtype=np.int16)
        return silence.tobytes()

    def set_input_data_generator(self, generator: Callable[[int], bytes]) -> None:
        """
        Set custom input data generator.

        Args:
            generator: Function that takes num_frames and returns bytes
        """
        with self._lock:
            self._data_generator = generator

    def read(self, num_frames: int, exception_on_overflow: bool = True) -> bytes:
        """
        Read audio data from stream.

        Args:
            num_frames: Number of frames to read
            exception_on_overflow: Whether to raise on buffer overflow

        Returns:
            Audio data as bytes
        """
        with self._lock:
            if not self.is_input:
                raise IOError("Not an input stream")

            if not self._active:
                raise IOError("Stream not active")

            self._read_count += 1

            if self._data_generator:
                return self._data_generator(num_frames)
            else:
                return self._generate_silence(num_frames)

    def write(self, frames: bytes, num_frames: Optional[int] = None) -> None:
        """
        Write audio data to stream.

        Args:
            frames: Audio data as bytes
            num_frames: Number of frames (optional)
        """
        with self._lock:
            if not self.is_output:
                raise IOError("Not an output stream")

            if not self._active:
                raise IOError("Stream not active")

            self._write_count += 1

    def start_stream(self) -> None:
        """Start the audio stream."""
        with self._lock:
            self._active = True

    def stop_stream(self) -> None:
        """Stop the audio stream."""
        with self._lock:
            self._active = False

    def close(self) -> None:
        """Close the audio stream."""
        with self._lock:
            self._active = False

    def is_active(self) -> bool:
        """Check if stream is active."""
        with self._lock:
            return self._active

    def get_read_count(self) -> int:
        """Get number of read() calls made."""
        with self._lock:
            return self._read_count

    def get_write_count(self) -> int:
        """Get number of write() calls made."""
        with self._lock:
            return self._write_count


class MockPyAudio:
    """
    Thread-safe mock PyAudio implementation.

    Simulates PyAudio API for testing without requiring actual audio hardware.
    """

    # PyAudio format constants
    paInt16 = 8
    paFloat32 = 1

    def __init__(self):
        """Initialize mock PyAudio."""
        self._lock = threading.Lock()
        self._streams: List[MockAudioStream] = []
        self._terminated = False

        # Mock device list
        self._devices = [
            {
                "index": 0,
                "name": "Mock Microphone",
                "maxInputChannels": 2,
                "maxOutputChannels": 0,
                "defaultSampleRate": 16000.0,
                "hostApi": 0,
            },
            {
                "index": 1,
                "name": "Mock Speaker",
                "maxInputChannels": 0,
                "maxOutputChannels": 2,
                "defaultSampleRate": 44100.0,
                "hostApi": 0,
            },
            {
                "index": 2,
                "name": "Mock USB Headset",
                "maxInputChannels": 1,
                "maxOutputChannels": 2,
                "defaultSampleRate": 48000.0,
                "hostApi": 0,
            },
        ]

    def get_device_count(self) -> int:
        """Get number of audio devices."""
        with self._lock:
            return len(self._devices)

    def get_device_info_by_index(self, index: int) -> Dict[str, Any]:
        """
        Get device info by index.

        Args:
            index: Device index

        Returns:
            Device info dictionary

        Raises:
            IOError: If index is invalid
        """
        with self._lock:
            if index < 0 or index >= len(self._devices):
                raise IOError(f"Invalid device index: {index}")
            return self._devices[index].copy()

    def get_default_input_device_info(self) -> Dict[str, Any]:
        """Get default input device info."""
        with self._lock:
            # Return first device with input channels
            for device in self._devices:
                if device["maxInputChannels"] > 0:
                    return device.copy()
            raise IOError("No input devices available")

    def get_default_output_device_info(self) -> Dict[str, Any]:
        """Get default output device info."""
        with self._lock:
            # Return first device with output channels
            for device in self._devices:
                if device["maxOutputChannels"] > 0:
                    return device.copy()
            raise IOError("No output devices available")

    def get_host_api_info_by_index(self, index: int) -> Dict[str, Any]:
        """Get host API info by index."""
        with self._lock:
            if index != 0:
                raise IOError(f"Invalid host API index: {index}")
            return {
                "index": 0,
                "name": "Mock Audio API",
                "deviceCount": len(self._devices),
                "defaultInputDevice": 0,
                "defaultOutputDevice": 1,
            }

    def get_device_info_by_host_api_device_index(self, host_api_index: int, device_index: int) -> Dict[str, Any]:
        """Get device info by host API device index."""
        with self._lock:
            if host_api_index != 0:
                raise IOError(f"Invalid host API index: {host_api_index}")
            if device_index < 0 or device_index >= len(self._devices):
                raise IOError(f"Invalid device index: {device_index}")
            return self._devices[device_index].copy()

    def get_sample_size(self, format: int) -> int:
        """Get sample size for given format."""
        if format == self.paInt16:
            return 2  # 16-bit = 2 bytes
        elif format == self.paFloat32:
            return 4  # 32-bit = 4 bytes
        return 2  # Default to 16-bit

    def open(
        self,
        format: int,
        channels: int,
        rate: int,
        input: bool = False,
        output: bool = False,
        frames_per_buffer: int = 1024,
        input_device_index: Optional[int] = None,
        output_device_index: Optional[int] = None,
        **kwargs,
    ) -> MockAudioStream:
        """
        Open an audio stream.

        Args:
            format: Audio format
            channels: Number of channels
            rate: Sample rate
            input: Input stream flag
            output: Output stream flag
            frames_per_buffer: Buffer size
            input_device_index: Input device index
            output_device_index: Output device index

        Returns:
            MockAudioStream instance
        """
        with self._lock:
            if self._terminated:
                raise IOError("PyAudio instance terminated")

            stream = MockAudioStream(
                format=format,
                channels=channels,
                rate=rate,
                input=input,
                output=output,
                frames_per_buffer=frames_per_buffer,
                input_device_index=input_device_index,
                output_device_index=output_device_index,
            )

            self._streams.append(stream)
            return stream

    def terminate(self) -> None:
        """Terminate PyAudio instance."""
        with self._lock:
            self._terminated = True
            for stream in self._streams:
                stream.close()


def create_tone_generator(frequency: float = 440.0, sample_rate: int = 16000) -> Callable:
    """
    Create a tone generator function.

    Args:
        frequency: Tone frequency in Hz
        sample_rate: Sample rate in Hz

    Returns:
        Generator function that produces tone data
    """
    phase = [0.0]  # Use list to maintain state across calls

    def generate(num_frames: int) -> bytes:
        """Generate tone audio data."""
        t = np.arange(num_frames) / sample_rate
        tone = np.sin(2 * np.pi * frequency * (t + phase[0]))
        phase[0] = (phase[0] + num_frames / sample_rate) % 1.0

        # Scale to int16 range
        audio_data = (tone * 16384).astype(np.int16)
        return audio_data.tobytes()

    return generate


def create_noise_generator(amplitude: float = 0.1, sample_rate: int = 16000) -> Callable:
    """
    Create a white noise generator function.

    Args:
        amplitude: Noise amplitude (0.0 to 1.0)
        sample_rate: Sample rate in Hz

    Returns:
        Generator function that produces noise data
    """

    def generate(num_frames: int) -> bytes:
        """Generate white noise audio data."""
        noise = np.random.normal(0, amplitude, num_frames)
        # Scale to int16 range
        audio_data = (noise * 32767).astype(np.int16)
        return audio_data.tobytes()

    return generate


def create_timeout_generator(timeout_after: int = 5) -> Callable:
    """
    Create a generator that times out after N calls.

    Args:
        timeout_after: Number of calls before timing out

    Returns:
        Generator function that times out
    """
    call_count = [0]  # Use list to maintain state

    def generate(num_frames: int) -> bytes:
        """Generate data or raise timeout."""
        call_count[0] += 1

        if call_count[0] > timeout_after:
            raise IOError("Stream timeout")

        # Return silence
        silence = np.zeros(num_frames, dtype=np.int16)
        return silence.tobytes()

    return generate


def create_pattern_generator(pattern: List[float], sample_rate: int = 16000) -> Callable:
    """
    Create a generator from a repeating pattern.

    Args:
        pattern: List of sample values (-1.0 to 1.0)
        sample_rate: Sample rate in Hz

    Returns:
        Generator function that repeats pattern
    """
    pattern_array = np.array(pattern, dtype=np.float32)
    position = [0]  # Use list to maintain state

    def generate(num_frames: int) -> bytes:
        """Generate audio from repeating pattern."""
        samples = []
        for _ in range(num_frames):
            samples.append(pattern_array[position[0] % len(pattern_array)])
            position[0] += 1

        # Scale to int16 range
        audio_data = (np.array(samples) * 32767).astype(np.int16)
        return audio_data.tobytes()

    return generate
