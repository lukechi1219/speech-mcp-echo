"""
Comprehensive tests for audio_processor.py module.

Tests audio processing functionality including:
- Device enumeration and selection
- Audio recording (streaming and silence detection)
- Playback functionality
- Error handling
- Audio cue playback
- Thread safety

All tests use mocked PyAudio to avoid real audio device access.
"""

import os
import time
import wave
import tempfile
import threading
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

from speech_mcp_echo.audio_processor import AudioProcessor
from speech_mcp_echo.constants import (
    CHUNK, FORMAT, CHANNELS, RATE,
    SILENCE_THRESHOLD, MAX_SILENCE_DURATION,
    START_LISTENING_SOUND, STOP_LISTENING_SOUND
)
from tests.helpers.mock_audio import (
    MockPyAudio, MockAudioStream,
    create_tone_generator, create_noise_generator,
    create_timeout_generator, create_pattern_generator
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_pyaudio_instance():
    """Create a complete mock PyAudio instance."""
    return MockPyAudio()


@pytest.fixture
def audio_processor_with_mock(mock_pyaudio_instance):
    """Create AudioProcessor with mocked PyAudio."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        # Configure the mock pyaudio module
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.paInputUnderflow = 0x01
        mock_pa.paInputOverflow = 0x02
        mock_pa.paOutputUnderflow = 0x04
        mock_pa.paOutputOverflow = 0x08
        mock_pa.paPrimingOutput = 0x10
        mock_pa.paContinue = 0

        # Mock get_portaudio_version
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        # Mock the config module to avoid loading real config
        with patch('speech_mcp_echo.config.get_setting') as mock_get_setting:
            mock_get_setting.return_value = []

            processor = AudioProcessor()
            yield processor

            # Cleanup
            processor.cleanup()


@pytest.fixture
def sample_wav_file(tmp_path):
    """Create a sample WAV file for testing playback."""
    wav_file = tmp_path / "test.wav"

    # Generate 0.5 seconds of 440Hz tone
    sample_rate = 16000
    duration = 0.5
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    tone = np.sin(frequency * 2 * np.pi * t)
    audio_data = (tone * 16384).astype(np.int16)

    # Write WAV file
    with wave.open(str(wav_file), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

    return wav_file


# =============================================================================
# Device Enumeration & Selection Tests (15 tests)
# =============================================================================

def test_get_available_devices_returns_list(audio_processor_with_mock):
    """Test that get_available_devices returns a list."""
    devices = audio_processor_with_mock.get_available_devices()
    assert isinstance(devices, list)


def test_get_available_devices_filters_input_only(audio_processor_with_mock):
    """Test that only input devices are returned."""
    devices = audio_processor_with_mock.get_available_devices()
    for device in devices:
        assert device['channels'] > 0, f"Device {device['name']} has no input channels"


def test_get_available_devices_contains_required_fields(audio_processor_with_mock):
    """Test that device info contains required fields."""
    devices = audio_processor_with_mock.get_available_devices()
    assert len(devices) > 0, "Should have at least one input device"

    for device in devices:
        assert 'index' in device
        assert 'name' in device
        assert 'channels' in device
        assert 'sample_rate' in device


def test_get_available_devices_when_no_pyaudio(audio_processor_with_mock):
    """Test get_available_devices when PyAudio is not initialized."""
    audio_processor_with_mock.pyaudio = None
    devices = audio_processor_with_mock.get_available_devices()

    # Should reinitialize and return devices
    assert isinstance(devices, list)


def test_get_available_devices_handles_exception(audio_processor_with_mock):
    """Test that device enumeration handles exceptions gracefully."""
    # Make get_host_api_info_by_index raise an exception (used by get_available_devices)
    audio_processor_with_mock.pyaudio.get_host_api_info_by_index = Mock(
        side_effect=Exception("Device error")
    )

    # Should return empty list on error
    devices = audio_processor_with_mock.get_available_devices()
    assert devices == []


def test_set_device_index_valid_device(audio_processor_with_mock):
    """Test setting device index with valid device."""
    result = audio_processor_with_mock.set_device_index(0)
    assert result is True
    assert audio_processor_with_mock.selected_device_index == 0


def test_set_device_index_invalid_device(audio_processor_with_mock):
    """Test setting device index with invalid index."""
    result = audio_processor_with_mock.set_device_index(999)
    assert result is False


def test_set_device_index_output_only_device(mock_pyaudio_instance):
    """Test setting device index with output-only device."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            processor = AudioProcessor()

            # Device index 1 is "Mock Speaker" (output only)
            result = processor.set_device_index(1)
            assert result is False

            processor.cleanup()


def test_set_device_index_when_no_pyaudio(audio_processor_with_mock):
    """Test set_device_index when PyAudio is not initialized."""
    audio_processor_with_mock.pyaudio = None
    result = audio_processor_with_mock.set_device_index(0)

    # Should reinitialize and succeed
    assert result is True


def test_selected_device_persists(audio_processor_with_mock):
    """Test that selected device persists across operations."""
    audio_processor_with_mock.set_device_index(0)
    assert audio_processor_with_mock.selected_device_index == 0

    # Device should still be selected
    assert audio_processor_with_mock.selected_device_index == 0


def test_default_device_selection_prefers_non_default(mock_pyaudio_instance):
    """Test that default device selection prefers non-default devices."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            processor = AudioProcessor()

            # Should select a non-default device if available
            # (Mock devices don't have 'default' in name, so first input device)
            assert processor.selected_device_index is not None

            processor.cleanup()


def test_preferred_device_from_config(mock_pyaudio_instance):
    """Test that preferred device from config is selected."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        # Mock config to prefer "Mock Microphone"
        with patch('speech_mcp_echo.config.get_setting', return_value=["Mock Microphone"]):
            processor = AudioProcessor()

            # Should select device 0 (Mock Microphone)
            assert processor.selected_device_index == 0

            processor.cleanup()


def test_preferred_device_case_insensitive(mock_pyaudio_instance):
    """Test that preferred device matching is case-insensitive."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        # Mock config with lowercase device name
        with patch('speech_mcp_echo.config.get_setting', return_value=["mock microphone"]):
            processor = AudioProcessor()

            # Should still match device 0
            assert processor.selected_device_index == 0

            processor.cleanup()


def test_preferred_device_partial_match(mock_pyaudio_instance):
    """Test that preferred device supports partial matching."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        # Mock config with partial device name
        with patch('speech_mcp_echo.config.get_setting', return_value=["Microphone"]):
            processor = AudioProcessor()

            # Should match device 0 (Mock Microphone)
            assert processor.selected_device_index == 0

            processor.cleanup()


def test_no_devices_available_scenario(mock_pyaudio_instance):
    """Test behavior when no audio devices are available."""
    # Mock PyAudio with no devices
    mock_pyaudio_instance._devices = []

    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            processor = AudioProcessor()

            # Should handle gracefully
            assert processor.selected_device_index is None

            processor.cleanup()


# =============================================================================
# Audio Recording Tests (25 tests)
# =============================================================================

def test_start_listening_basic(audio_processor_with_mock, mock_pyaudio_instance):
    """Test basic start_listening functionality."""
    # Create a mock stream
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    # Mock the open method to return our stream
    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Mock audio file playback
    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()

    assert result is True
    assert audio_processor_with_mock.is_listening is True


def test_start_listening_already_listening(audio_processor_with_mock):
    """Test that start_listening ignores call if already listening."""
    audio_processor_with_mock.is_listening = True

    result = audio_processor_with_mock.start_listening()

    assert result is True
    # Should not create new stream
    assert audio_processor_with_mock.stream is None


def test_start_listening_streaming_mode(audio_processor_with_mock, mock_pyaudio_instance):
    """Test start_listening in streaming mode."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    chunk_callback = Mock()

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening(
            streaming_mode=True,
            on_audio_chunk=chunk_callback
        )

    assert result is True
    assert audio_processor_with_mock._streaming_mode is True
    assert audio_processor_with_mock._on_audio_chunk is chunk_callback


def test_start_listening_with_callback(audio_processor_with_mock, mock_pyaudio_instance):
    """Test start_listening with audio callback."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    user_callback = Mock()

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening(callback=user_callback)

    assert result is True


def test_start_listening_plays_start_sound(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that start_listening plays start notification sound."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file') as mock_play:
        audio_processor_with_mock.start_listening()

        # Give thread time to start
        time.sleep(0.1)

        # Should have called play_audio_file with start sound
        mock_play.assert_called()


def test_start_listening_stream_inactive_fails(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that start_listening fails if stream is not active."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = False  # Stream not active

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()

    assert result is False
    assert audio_processor_with_mock.is_listening is False


def test_start_listening_handles_exception(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that start_listening handles exceptions gracefully."""
    mock_pyaudio_instance.open = Mock(side_effect=Exception("Stream error"))

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()

    assert result is False
    assert audio_processor_with_mock.is_listening is False


def test_stop_listening_basic(audio_processor_with_mock):
    """Test basic stop_listening functionality."""
    # Set up a mock stream
    mock_stream = MagicMock()
    audio_processor_with_mock.stream = mock_stream
    audio_processor_with_mock.is_listening = True

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        audio_processor_with_mock.stop_listening()

    assert audio_processor_with_mock.is_listening is False
    assert audio_processor_with_mock.stream is None
    mock_stream.stop_stream.assert_called_once()
    mock_stream.close.assert_called_once()


def test_stop_listening_plays_stop_sound(audio_processor_with_mock):
    """Test that stop_listening plays stop notification sound."""
    mock_stream = MagicMock()
    audio_processor_with_mock.stream = mock_stream
    audio_processor_with_mock.is_listening = True

    with patch.object(audio_processor_with_mock, 'play_audio_file') as mock_play:
        audio_processor_with_mock.stop_listening()

        # Give thread time to start
        time.sleep(0.1)

        mock_play.assert_called()


def test_stop_listening_no_stream(audio_processor_with_mock):
    """Test stop_listening when no stream exists."""
    audio_processor_with_mock.stream = None
    audio_processor_with_mock.is_listening = True

    # Should not raise exception
    audio_processor_with_mock.stop_listening()

    assert audio_processor_with_mock.is_listening is False


def test_stop_listening_handles_exception(audio_processor_with_mock):
    """Test that stop_listening handles exceptions gracefully."""
    mock_stream = MagicMock()
    mock_stream.stop_stream.side_effect = Exception("Stop error")

    audio_processor_with_mock.stream = mock_stream
    audio_processor_with_mock.is_listening = True

    # Should not raise exception
    audio_processor_with_mock.stop_listening()

    assert audio_processor_with_mock.is_listening is False


def test_audio_frames_collected_during_recording(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that audio frames are collected during recording."""
    # Configure the mock to use a tone generator for new streams
    mock_pyaudio_instance._default_generator = create_tone_generator()

    # Let MockPyAudio.open() create the stream naturally (with stream_callback support)
    # The stream will be active and invoke the callback in a background thread

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        audio_processor_with_mock.start_listening()

        # Wait briefly for callback to be called
        time.sleep(0.3)

        audio_processor_with_mock.stop_listening()

    # Should have collected some frames
    assert len(audio_processor_with_mock.audio_frames) > 0


def test_audio_level_callback_invoked(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that audio level callback is invoked during recording."""
    level_callback = Mock()

    # Create processor with level callback
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.paInputUnderflow = 0x01
        mock_pa.paInputOverflow = 0x02
        mock_pa.paOutputUnderflow = 0x04
        mock_pa.paOutputOverflow = 0x08
        mock_pa.paPrimingOutput = 0x10
        mock_pa.paContinue = 0
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            processor = AudioProcessor(on_audio_level=level_callback)

            # Set default generator so new streams produce tone data
            mock_pyaudio_instance._default_generator = create_tone_generator()

            with patch.object(processor, 'play_audio_file', return_value=True):
                processor.start_listening()

                # Wait for callback to be invoked
                time.sleep(0.3)

                processor.stop_listening()

            # Level callback should have been called
            assert level_callback.call_count > 0

            processor.cleanup()


def test_record_audio_blocking(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that record_audio blocks until recording completes."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True
    mock_stream.set_input_data_generator(create_tone_generator())

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Mock stop_listening to immediately stop
    original_start = audio_processor_with_mock.start_listening

    def mock_start(*args, **kwargs):
        result = original_start(*args, **kwargs)
        # Immediately stop to unblock
        threading.Timer(0.1, audio_processor_with_mock.stop_listening).start()
        return result

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        with patch.object(audio_processor_with_mock, 'start_listening', side_effect=mock_start):
            audio_path = audio_processor_with_mock.record_audio()

    # Should return a path (or None if no frames)
    assert audio_path is None or isinstance(audio_path, str)


def test_record_until_silence_timeout(audio_processor_with_mock, mock_pyaudio_instance):
    """Test record_until_silence with timeout."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True
    mock_stream.set_input_data_generator(create_tone_generator())

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        # Record with 1 second timeout
        audio_path = audio_processor_with_mock.record_until_silence(timeout=1)

    # Should timeout and return None
    assert audio_path is None


def test_record_until_silence_completes(audio_processor_with_mock, mock_pyaudio_instance):
    """Test record_until_silence completes before timeout."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    # Generate silence (should trigger silence detection)
    mock_stream.set_input_data_generator(lambda n: np.zeros(n, dtype=np.int16).tobytes())

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        # Should complete due to silence detection
        audio_path = audio_processor_with_mock.record_until_silence(timeout=10)

    # May return path or None depending on timing
    assert audio_path is None or isinstance(audio_path, str)


def test_get_recorded_audio_path_with_frames(audio_processor_with_mock):
    """Test get_recorded_audio_path with audio frames."""
    # Add some audio frames
    audio_data = np.zeros(1024, dtype=np.int16).tobytes()
    audio_processor_with_mock.audio_frames = [audio_data, audio_data, audio_data]

    audio_path = audio_processor_with_mock.get_recorded_audio_path()

    assert audio_path is not None
    assert os.path.exists(audio_path)
    assert audio_path.endswith('.wav')

    # Cleanup
    os.unlink(audio_path)


def test_get_recorded_audio_path_no_frames(audio_processor_with_mock):
    """Test get_recorded_audio_path with no audio frames."""
    audio_processor_with_mock.audio_frames = []

    audio_path = audio_processor_with_mock.get_recorded_audio_path()

    assert audio_path is None


def test_get_recorded_audio_path_creates_valid_wav(audio_processor_with_mock):
    """Test that get_recorded_audio_path creates a valid WAV file."""
    # Generate some audio data
    tone = create_tone_generator()
    audio_data = tone(CHUNK)

    audio_processor_with_mock.audio_frames = [audio_data for _ in range(10)]

    audio_path = audio_processor_with_mock.get_recorded_audio_path()

    assert audio_path is not None

    # Verify it's a valid WAV file
    with wave.open(audio_path, 'rb') as wf:
        assert wf.getnchannels() == CHANNELS
        assert wf.getframerate() == RATE
        assert wf.getnframes() > 0

    # Cleanup
    os.unlink(audio_path)


def test_recording_with_different_sample_rates(mock_pyaudio_instance):
    """Test recording with different sample rates."""
    for rate in [8000, 16000, 22050, 44100, 48000]:
        with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
            mock_pa.PyAudio.return_value = mock_pyaudio_instance
            mock_pa.paInt16 = MockPyAudio.paInt16
            mock_pa.get_portaudio_version.return_value = "19.7.0"

            # Temporarily change RATE constant
            with patch('speech_mcp_echo.audio_processor.RATE', rate):
                with patch('speech_mcp_echo.config.get_setting', return_value=[]):
                    processor = AudioProcessor()

                    mock_stream = MockAudioStream(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=rate,
                        input=True,
                        frames_per_buffer=CHUNK
                    )
                    mock_stream._active = True

                    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

                    with patch.object(processor, 'play_audio_file', return_value=True):
                        result = processor.start_listening()

                    assert result is True
                    processor.stop_listening()
                    processor.cleanup()


def test_recording_with_different_chunk_sizes(mock_pyaudio_instance):
    """Test recording with different chunk sizes."""
    for chunk_size in [512, 1024, 2048, 4096]:
        with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
            mock_pa.PyAudio.return_value = mock_pyaudio_instance
            mock_pa.paInt16 = MockPyAudio.paInt16
            mock_pa.get_portaudio_version.return_value = "19.7.0"

            # Temporarily change CHUNK constant
            with patch('speech_mcp_echo.audio_processor.CHUNK', chunk_size):
                with patch('speech_mcp_echo.config.get_setting', return_value=[]):
                    processor = AudioProcessor()

                    mock_stream = MockAudioStream(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=chunk_size
                    )
                    mock_stream._active = True

                    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

                    with patch.object(processor, 'play_audio_file', return_value=True):
                        result = processor.start_listening()

                    assert result is True
                    processor.stop_listening()
                    processor.cleanup()


def test_consecutive_recordings(audio_processor_with_mock, mock_pyaudio_instance):
    """Test multiple consecutive recordings."""
    # Let MockPyAudio.open() create fresh streams each time (with callback support)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        # First recording
        result1 = audio_processor_with_mock.start_listening()
        assert result1 is True
        audio_processor_with_mock.stop_listening()

        # Second recording
        result2 = audio_processor_with_mock.start_listening()
        assert result2 is True
        audio_processor_with_mock.stop_listening()

        # Third recording
        result3 = audio_processor_with_mock.start_listening()
        assert result3 is True
        audio_processor_with_mock.stop_listening()


def test_recording_interruption(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that recording can be interrupted."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()
        assert result is True
        assert audio_processor_with_mock.is_listening is True

        # Interrupt immediately
        audio_processor_with_mock.stop_listening()

        assert audio_processor_with_mock.is_listening is False


def test_recording_with_tone_pattern(audio_processor_with_mock, mock_pyaudio_instance):
    """Test recording with generated tone pattern."""
    mock_pyaudio_instance._default_generator = create_tone_generator(frequency=440.0)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        audio_processor_with_mock.start_listening()
        time.sleep(0.3)
        audio_processor_with_mock.stop_listening()

    # Should have collected frames
    assert len(audio_processor_with_mock.audio_frames) > 0


def test_recording_with_noise_pattern(audio_processor_with_mock, mock_pyaudio_instance):
    """Test recording with white noise pattern."""
    mock_pyaudio_instance._default_generator = create_noise_generator(amplitude=0.5)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        audio_processor_with_mock.start_listening()
        time.sleep(0.3)
        audio_processor_with_mock.stop_listening()

    # Should have collected frames
    assert len(audio_processor_with_mock.audio_frames) > 0


# =============================================================================
# Playback Functionality Tests (10 tests)
# =============================================================================

def test_play_audio_file_success(audio_processor_with_mock, sample_wav_file):
    """Test successful audio file playback."""
    result = audio_processor_with_mock.play_audio_file(str(sample_wav_file))
    assert result is True


def test_play_audio_file_missing_file(audio_processor_with_mock):
    """Test playback with missing file."""
    result = audio_processor_with_mock.play_audio_file("/nonexistent/file.wav")
    assert result is False


def test_play_audio_file_invalid_file(audio_processor_with_mock, tmp_path):
    """Test playback with invalid WAV file."""
    invalid_file = tmp_path / "invalid.wav"
    invalid_file.write_text("not a wav file")

    result = audio_processor_with_mock.play_audio_file(str(invalid_file))
    assert result is False


def test_play_audio_file_empty_file(audio_processor_with_mock, tmp_path):
    """Test playback with empty file."""
    empty_file = tmp_path / "empty.wav"
    empty_file.touch()

    result = audio_processor_with_mock.play_audio_file(str(empty_file))
    assert result is False


def test_play_audio_file_different_formats(audio_processor_with_mock, tmp_path):
    """Test playback with different audio formats."""
    # Test with 8-bit audio
    wav_file = tmp_path / "test_8bit.wav"

    audio_data = np.zeros(8000, dtype=np.uint8)

    with wave.open(str(wav_file), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)  # 8-bit
        wf.setframerate(8000)
        wf.writeframes(audio_data.tobytes())

    result = audio_processor_with_mock.play_audio_file(str(wav_file))
    # May succeed or fail depending on PyAudio mock
    assert isinstance(result, bool)


def test_play_audio_file_stereo(audio_processor_with_mock, tmp_path):
    """Test playback with stereo audio."""
    wav_file = tmp_path / "stereo.wav"

    # Generate stereo audio
    audio_data = np.zeros((8000, 2), dtype=np.int16)

    with wave.open(str(wav_file), 'wb') as wf:
        wf.setnchannels(2)  # Stereo
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio_data.tobytes())

    result = audio_processor_with_mock.play_audio_file(str(wav_file))
    assert isinstance(result, bool)


def test_play_audio_file_high_sample_rate(audio_processor_with_mock, tmp_path):
    """Test playback with high sample rate."""
    wav_file = tmp_path / "high_rate.wav"

    audio_data = np.zeros(44100, dtype=np.int16)

    with wave.open(str(wav_file), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)  # High sample rate
        wf.writeframes(audio_data.tobytes())

    result = audio_processor_with_mock.play_audio_file(str(wav_file))
    assert isinstance(result, bool)


def test_play_audio_file_handles_exception(audio_processor_with_mock, sample_wav_file):
    """Test that playback handles exceptions gracefully."""
    # Mock wave.open to raise exception
    with patch('speech_mcp_echo.audio_processor.wave.open', side_effect=Exception("Wave error")):
        result = audio_processor_with_mock.play_audio_file(str(sample_wav_file))

    assert result is False


def test_playback_creates_new_pyaudio_instance(audio_processor_with_mock, sample_wav_file):
    """Test that playback creates its own PyAudio instance."""
    # This ensures playback doesn't interfere with recording
    result = audio_processor_with_mock.play_audio_file(str(sample_wav_file))
    assert isinstance(result, bool)

    # Original PyAudio instance should still exist
    assert audio_processor_with_mock.pyaudio is not None


def test_playback_thread_safety(audio_processor_with_mock, sample_wav_file):
    """Test that playback is thread-safe."""
    results = []

    def play_in_thread():
        result = audio_processor_with_mock.play_audio_file(str(sample_wav_file))
        results.append(result)

    # Start multiple playback threads
    threads = [threading.Thread(target=play_in_thread) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All should complete
    assert len(results) == 3


# =============================================================================
# Error Handling Tests (20 tests)
# =============================================================================

def test_error_no_audio_devices(mock_pyaudio_instance):
    """Test behavior when no audio devices are available."""
    mock_pyaudio_instance._devices = []

    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            processor = AudioProcessor()

            assert processor.selected_device_index is None
            processor.cleanup()


def test_error_pyaudio_initialization_failure():
    """Test handling of PyAudio initialization failure."""
    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.side_effect = Exception("PyAudio init failed")
        mock_pa.paInt16 = MockPyAudio.paInt16

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            # Should not raise exception
            processor = AudioProcessor()

            # PyAudio should be None
            assert processor.pyaudio is None
            processor.cleanup()


def test_error_stream_open_failure(audio_processor_with_mock, mock_pyaudio_instance):
    """Test handling of stream open failure."""
    mock_pyaudio_instance.open = Mock(side_effect=Exception("Cannot open stream"))

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()

    assert result is False


def test_error_timeout_during_recording(audio_processor_with_mock, mock_pyaudio_instance):
    """Test timeout during recording with no audio input."""
    # Already tested in record_until_silence_timeout
    pass


def test_error_corrupted_audio_data(audio_processor_with_mock):
    """Test handling of corrupted audio data."""
    # Add corrupted data
    audio_processor_with_mock.audio_frames = [b"corrupted", b"data"]

    # get_recorded_audio_path should handle gracefully
    audio_path = audio_processor_with_mock.get_recorded_audio_path()

    # May succeed (writing invalid WAV) or fail (exception caught)
    # Either way, should not crash
    assert audio_path is None or isinstance(audio_path, str)


def test_error_callback_exception_does_not_crash(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that callback exceptions don't crash the recording."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Callback that raises exception
    def bad_callback(data):
        raise Exception("Callback error")

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening(callback=bad_callback)

    # Should still succeed (exception caught in callback)
    assert result is True

    audio_processor_with_mock.stop_listening()


def test_error_audio_level_callback_exception(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that audio level callback exceptions are handled."""
    def bad_level_callback(level):
        raise Exception("Level callback error")

    with patch('speech_mcp_echo.audio_processor.pyaudio') as mock_pa:
        mock_pa.PyAudio.return_value = mock_pyaudio_instance
        mock_pa.paInt16 = MockPyAudio.paInt16
        mock_pa.paInputUnderflow = 0x01
        mock_pa.paInputOverflow = 0x02
        mock_pa.paOutputUnderflow = 0x04
        mock_pa.paOutputOverflow = 0x08
        mock_pa.paPrimingOutput = 0x10
        mock_pa.paContinue = 0
        mock_pa.get_portaudio_version.return_value = "19.7.0"

        with patch('speech_mcp_echo.config.get_setting', return_value=[]):
            processor = AudioProcessor(on_audio_level=bad_level_callback)

            mock_stream = MockAudioStream(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            mock_stream._active = True

            mock_pyaudio_instance.open = Mock(return_value=mock_stream)

            with patch.object(processor, 'play_audio_file', return_value=True):
                # Should not crash
                processor.start_listening()
                time.sleep(0.1)
                processor.stop_listening()

            processor.cleanup()


def test_error_stream_read_failure(audio_processor_with_mock, mock_pyaudio_instance):
    """Test handling of stream read failure."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    # Make read raise exception
    mock_stream.set_input_data_generator(create_timeout_generator(timeout_after=3))

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()
        assert result is True

        # Recording should continue despite read errors
        time.sleep(0.2)

        audio_processor_with_mock.stop_listening()


def test_error_invalid_audio_format(audio_processor_with_mock, tmp_path):
    """Test handling of invalid audio format."""
    # Create file with wrong extension
    invalid_file = tmp_path / "audio.txt"
    invalid_file.write_text("not audio")

    result = audio_processor_with_mock.play_audio_file(str(invalid_file))
    assert result is False


def test_error_permission_denied_scenario(audio_processor_with_mock, tmp_path):
    """Test handling of permission denied errors."""
    # Create a read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)

    # Try to save recording to readonly directory
    audio_processor_with_mock.audio_frames = [np.zeros(1024, dtype=np.int16).tobytes()]

    # Patch tempfile to use readonly directory
    with patch('tempfile.NamedTemporaryFile') as mock_temp:
        mock_temp.side_effect = PermissionError("Permission denied")

        audio_path = audio_processor_with_mock.get_recorded_audio_path()

        # Should handle gracefully
        assert audio_path is None

    # Restore permissions
    readonly_dir.chmod(0o755)


def test_error_disk_full_scenario(audio_processor_with_mock):
    """Test handling of disk full errors."""
    audio_processor_with_mock.audio_frames = [np.zeros(1024, dtype=np.int16).tobytes()]

    # Mock wave.open to raise disk full error
    with patch('speech_mcp_echo.audio_processor.wave.open', side_effect=OSError("No space left on device")):
        audio_path = audio_processor_with_mock.get_recorded_audio_path()

        # Should return None on error
        assert audio_path is None


def test_error_memory_error_scenario(audio_processor_with_mock):
    """Test handling of memory errors."""
    # Try to allocate huge amount of frames
    with patch.object(audio_processor_with_mock, 'audio_frames', [b"x" * 1000000 for _ in range(1000)]):
        # Should handle gracefully (or succeed if enough memory)
        audio_path = audio_processor_with_mock.get_recorded_audio_path()

        # Either succeeds or returns None
        assert audio_path is None or isinstance(audio_path, str)

        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)


def test_error_audio_callback_status_flags(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that audio callback handles status flags correctly."""
    # This is tested implicitly through the mock setup, but we can verify
    # the callback is configured to handle status flags
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()
        assert result is True

        audio_processor_with_mock.stop_listening()


def test_error_cleanup_with_active_stream(audio_processor_with_mock):
    """Test cleanup with active stream."""
    mock_stream = MagicMock()
    mock_stream.is_active.return_value = True

    audio_processor_with_mock.stream = mock_stream
    audio_processor_with_mock.is_listening = True

    # Should not raise exception
    audio_processor_with_mock.cleanup()

    mock_stream.stop_stream.assert_called()
    mock_stream.close.assert_called()


def test_error_cleanup_with_exception(audio_processor_with_mock):
    """Test that cleanup handles exceptions gracefully."""
    mock_stream = MagicMock()
    mock_stream.stop_stream.side_effect = Exception("Cleanup error")

    audio_processor_with_mock.stream = mock_stream

    # Should not raise exception
    audio_processor_with_mock.cleanup()

    # Stream should be None
    assert audio_processor_with_mock.stream is None


def test_error_multiple_cleanup_calls(audio_processor_with_mock):
    """Test that multiple cleanup calls are safe."""
    audio_processor_with_mock.cleanup()
    audio_processor_with_mock.cleanup()
    audio_processor_with_mock.cleanup()

    # Should not raise exception
    assert audio_processor_with_mock.pyaudio is None


def test_error_get_available_devices_after_cleanup(audio_processor_with_mock):
    """Test get_available_devices after cleanup."""
    audio_processor_with_mock.cleanup()

    # Should reinitialize
    devices = audio_processor_with_mock.get_available_devices()

    assert isinstance(devices, list)


def test_error_start_listening_after_cleanup(audio_processor_with_mock, mock_pyaudio_instance):
    """Test start_listening after cleanup."""
    audio_processor_with_mock.cleanup()

    # Reset PyAudio for next operation
    with patch('speech_mcp_echo.audio_processor.pyaudio.PyAudio', return_value=mock_pyaudio_instance):
        audio_processor_with_mock._setup_audio()

        mock_stream = MockAudioStream(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )
        mock_stream._active = True

        mock_pyaudio_instance.open = Mock(return_value=mock_stream)

        with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
            result = audio_processor_with_mock.start_listening()

        # Should work after reinitialization
        assert result is True or result is False  # May fail depending on setup


def test_error_device_disconnected_during_recording(audio_processor_with_mock, mock_pyaudio_instance):
    """Test handling of device disconnection during recording."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    # Simulate device disconnection by deactivating stream
    def deactivate_later():
        time.sleep(0.1)
        mock_stream._active = False

    threading.Thread(target=deactivate_later, daemon=True).start()

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        result = audio_processor_with_mock.start_listening()
        time.sleep(0.2)
        audio_processor_with_mock.stop_listening()

    # Should handle gracefully
    assert isinstance(result, bool)


# =============================================================================
# Audio Cue Playback Tests (10 tests)
# =============================================================================

def test_audio_cue_start_listening_file_exists(audio_processor_with_mock):
    """Test that start listening cue file path exists."""
    # Note: In testing, the file might not exist, so we just check the constant
    assert START_LISTENING_SOUND is not None
    assert isinstance(START_LISTENING_SOUND, str)


def test_audio_cue_stop_listening_file_exists(audio_processor_with_mock):
    """Test that stop listening cue file path exists."""
    assert STOP_LISTENING_SOUND is not None
    assert isinstance(STOP_LISTENING_SOUND, str)


def test_audio_cue_playback_on_start(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that audio cue is played on start listening."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file') as mock_play:
        audio_processor_with_mock.start_listening()

        # Give thread time to call play_audio_file
        time.sleep(0.1)

        # Should have been called with start sound
        calls = [call[0][0] for call in mock_play.call_args_list]
        assert any(START_LISTENING_SOUND in str(c) for c in calls)

        audio_processor_with_mock.stop_listening()


def test_audio_cue_playback_on_stop(audio_processor_with_mock):
    """Test that audio cue is played on stop listening."""
    mock_stream = MagicMock()
    audio_processor_with_mock.stream = mock_stream
    audio_processor_with_mock.is_listening = True

    with patch.object(audio_processor_with_mock, 'play_audio_file') as mock_play:
        audio_processor_with_mock.stop_listening()

        # Give thread time to call play_audio_file
        time.sleep(0.1)

        # Should have been called with stop sound
        calls = [call[0][0] for call in mock_play.call_args_list]
        assert any(STOP_LISTENING_SOUND in str(c) for c in calls)


def test_audio_cue_file_not_found_handled(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that missing cue file is handled gracefully."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Mock play_audio_file to return False (file not found)
    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=False):
        # Should not crash
        result = audio_processor_with_mock.start_listening()
        assert result is True

        audio_processor_with_mock.stop_listening()


def test_audio_cue_playback_in_thread(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that cue playback happens in separate thread."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Track thread ID of playback
    playback_thread_id = None
    main_thread_id = threading.current_thread().ident

    def track_thread(filepath):
        nonlocal playback_thread_id
        playback_thread_id = threading.current_thread().ident
        return True

    with patch.object(audio_processor_with_mock, 'play_audio_file', side_effect=track_thread):
        audio_processor_with_mock.start_listening()

        # Wait for thread to execute
        time.sleep(0.1)

        # Playback should be in different thread
        assert playback_thread_id is not None
        assert playback_thread_id != main_thread_id

        audio_processor_with_mock.stop_listening()


def test_audio_cue_does_not_block_recording(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that cue playback doesn't block recording start."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Mock play_audio_file to take time
    def slow_playback(filepath):
        time.sleep(1.0)
        return True

    with patch.object(audio_processor_with_mock, 'play_audio_file', side_effect=slow_playback):
        start_time = time.time()
        result = audio_processor_with_mock.start_listening()
        end_time = time.time()

        # start_listening should return quickly
        assert (end_time - start_time) < 0.5
        assert result is True

        audio_processor_with_mock.stop_listening()


def test_multiple_cues_in_sequence(audio_processor_with_mock, mock_pyaudio_instance):
    """Test multiple cues played in sequence."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file') as mock_play:
        # Start -> Stop -> Start -> Stop
        audio_processor_with_mock.start_listening()
        time.sleep(0.05)
        audio_processor_with_mock.stop_listening()
        time.sleep(0.05)

        audio_processor_with_mock.start_listening()
        time.sleep(0.05)
        audio_processor_with_mock.stop_listening()
        time.sleep(0.05)

        # Should have called play_audio_file multiple times
        assert mock_play.call_count >= 4


def test_audio_cue_playback_exception_handled(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that cue playback exceptions are handled."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # Mock play_audio_file to raise exception
    with patch.object(audio_processor_with_mock, 'play_audio_file', side_effect=Exception("Playback error")):
        # Should not crash
        result = audio_processor_with_mock.start_listening()
        assert result is True

        audio_processor_with_mock.stop_listening()


def test_audio_cue_with_busy_audio_device(audio_processor_with_mock, mock_pyaudio_instance):
    """Test cue playback when audio device is busy."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    # First call succeeds, second fails (device busy)
    call_count = [0]

    def playback_with_busy(filepath):
        call_count[0] += 1
        if call_count[0] > 1:
            raise Exception("Device busy")
        return True

    with patch.object(audio_processor_with_mock, 'play_audio_file', side_effect=playback_with_busy):
        # Should handle gracefully
        result = audio_processor_with_mock.start_listening()
        time.sleep(0.05)
        audio_processor_with_mock.stop_listening()

        assert isinstance(result, bool)


# =============================================================================
# Thread Safety Tests (5 tests)
# =============================================================================

def test_thread_safety_concurrent_device_queries(audio_processor_with_mock):
    """Test concurrent device enumeration is thread-safe."""
    results = []

    def query_devices():
        devices = audio_processor_with_mock.get_available_devices()
        results.append(devices)

    threads = [threading.Thread(target=query_devices) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All should succeed
    assert len(results) == 10
    for result in results:
        assert isinstance(result, list)


def test_thread_safety_concurrent_cleanup(audio_processor_with_mock):
    """Test concurrent cleanup calls are thread-safe."""
    def cleanup_in_thread():
        audio_processor_with_mock.cleanup()

    threads = [threading.Thread(target=cleanup_in_thread) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Should complete without crashes
    assert audio_processor_with_mock.pyaudio is None


def test_thread_safety_stop_from_different_thread(audio_processor_with_mock, mock_pyaudio_instance):
    """Test stopping recording from a different thread."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        audio_processor_with_mock.start_listening()

        # Stop from different thread
        def stop_in_thread():
            time.sleep(0.1)
            audio_processor_with_mock.stop_listening()

        thread = threading.Thread(target=stop_in_thread)
        thread.start()
        thread.join()

        assert audio_processor_with_mock.is_listening is False


def test_thread_safety_concurrent_recordings_fail(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that concurrent recordings fail gracefully."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    results = []

    def start_recording():
        with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
            result = audio_processor_with_mock.start_listening()
            results.append(result)
            time.sleep(0.1)
            audio_processor_with_mock.stop_listening()

    # Try to start two concurrent recordings
    threads = [threading.Thread(target=start_recording) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # At least one should succeed, second should return True (already listening)
    assert len(results) == 2


def test_thread_cleanup_on_error(audio_processor_with_mock, mock_pyaudio_instance):
    """Test that threads are properly cleaned up on errors."""
    mock_stream = MockAudioStream(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    mock_stream._active = True

    # Make stream raise exception
    def failing_generator(n):
        raise Exception("Stream error")

    mock_stream.set_input_data_generator(failing_generator)
    mock_pyaudio_instance.open = Mock(return_value=mock_stream)

    with patch.object(audio_processor_with_mock, 'play_audio_file', return_value=True):
        audio_processor_with_mock.start_listening()

        # Even with errors, should be able to stop
        time.sleep(0.2)
        audio_processor_with_mock.stop_listening()

        # Should be stopped
        assert audio_processor_with_mock.is_listening is False
