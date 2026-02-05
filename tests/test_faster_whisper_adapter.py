"""
Comprehensive unit tests for faster-whisper STT adapter.

Tests cover:
- Initialization with various configurations
- Transcription with different settings
- Error handling and edge cases
- Timeout functionality
- Model management
- Streaming transcription
"""

import os
import pytest
import tempfile
import wave
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT


class TestFasterWhisperInitialization:
    """Test adapter initialization."""

    def test_init_default_settings(self):
        """Initialize with default settings."""
        stt = FasterWhisperSTT()

        assert stt.model == "base"
        assert stt.device == "cpu"
        assert stt.compute_type == "int8"
        assert stt.language == "auto"
        assert stt.is_initialized is False
        assert stt._whisper_model is None

    def test_init_custom_settings(self):
        """Initialize with custom settings."""
        stt = FasterWhisperSTT(
            model="small",
            device="cuda",
            compute_type="float16",
            language="en"
        )

        assert stt.model == "small"
        assert stt.device == "cuda"
        assert stt.compute_type == "float16"
        assert stt.language == "en"
        assert stt.is_initialized is False

    def test_init_all_model_sizes(self):
        """Test initialization with all supported model sizes."""
        models = ["tiny", "tiny.en", "base", "base.en", "small",
                  "small.en", "medium", "medium.en", "large-v2", "large-v3"]

        for model in models:
            stt = FasterWhisperSTT(model=model)
            assert stt.model == model

    def test_lazy_initialization(self):
        """Model should not load until first use."""
        stt = FasterWhisperSTT()

        # Model should not be loaded yet
        assert stt._whisper_model is None
        assert stt.is_initialized is False

    def test_ensure_initialized_loads_model(self):
        """Test that _ensure_initialized loads the model."""
        stt = FasterWhisperSTT(model="base")

        # Mock WhisperModel inside faster_whisper module (imported in method)
        with patch('faster_whisper.WhisperModel') as mock_whisper:
            mock_model = MagicMock()
            mock_whisper.return_value = mock_model

            stt._ensure_initialized()

            # Should have loaded model
            assert stt._whisper_model == mock_model
            assert stt.is_initialized is True

            # Should have called WhisperModel with correct params
            mock_whisper.assert_called_once_with(
                "base",
                device="cpu",
                compute_type="int8"
            )

    def test_ensure_initialized_only_loads_once(self):
        """Ensure model is only loaded once."""
        stt = FasterWhisperSTT()

        with patch('faster_whisper.WhisperModel') as mock_whisper:
            mock_model = MagicMock()
            mock_whisper.return_value = mock_model

            # Call multiple times
            stt._ensure_initialized()
            stt._ensure_initialized()
            stt._ensure_initialized()

            # Should only be called once
            mock_whisper.assert_called_once()

    def test_ensure_initialized_import_error(self):
        """Test handling when faster-whisper not installed."""
        stt = FasterWhisperSTT()

        # Mock the import to fail
        import sys
        with patch.dict('sys.modules', {'faster_whisper': None}):
            with pytest.raises(ImportError):
                stt._ensure_initialized()


class TestFasterWhisperTranscription:
    """Test transcription functionality."""

    def test_transcribe_success(self, sample_audio_file):
        """Transcribe audio file successfully."""
        stt = FasterWhisperSTT()

        # Mock whisper model
        mock_model = MagicMock()
        mock_segment1 = MagicMock()
        mock_segment1.text = "Hello"
        mock_segment2 = MagicMock()
        mock_segment2.text = "world"

        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment1, mock_segment2], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        result = stt.transcribe(str(sample_audio_file))

        assert result == "Hello world"
        mock_model.transcribe.assert_called_once()

    def test_transcribe_with_language_auto(self, sample_audio_file):
        """Transcribe with auto language detection."""
        stt = FasterWhisperSTT(language="auto")

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Test"
        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        stt.transcribe(str(sample_audio_file))

        # Should pass None for language when auto
        call_args = mock_model.transcribe.call_args
        assert call_args[1]['language'] is None

    def test_transcribe_with_specific_language(self, sample_audio_file):
        """Transcribe with specific language code."""
        stt = FasterWhisperSTT(language="en")

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Test"
        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        stt.transcribe(str(sample_audio_file))

        # Should pass language code
        call_args = mock_model.transcribe.call_args
        assert call_args[1]['language'] == "en"

    def test_transcribe_chinese(self, sample_audio_file):
        """Transcribe Chinese audio."""
        stt = FasterWhisperSTT(language="zh")

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "你好世界"
        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        result = stt.transcribe(str(sample_audio_file))

        assert result == "你好世界"

    def test_transcribe_empty_audio(self, tmp_path):
        """Transcribe empty audio file."""
        # Create empty audio file
        audio_file = tmp_path / "empty.wav"
        with wave.open(str(audio_file), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b'')

        stt = FasterWhisperSTT()

        mock_model = MagicMock()
        mock_info = MagicMock()
        # Empty segments
        mock_model.transcribe.return_value = ([], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        result = stt.transcribe(str(audio_file))

        assert result == ""

    def test_transcribe_strips_whitespace(self, sample_audio_file):
        """Transcription should strip leading/trailing whitespace."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "  Test with spaces  "
        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        result = stt.transcribe(str(sample_audio_file))

        assert result == "Test with spaces"

    def test_transcribe_vad_filter_enabled(self, sample_audio_file):
        """VAD filter should be enabled by default."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Test"
        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        stt.transcribe(str(sample_audio_file))

        # Check VAD filter is enabled
        call_args = mock_model.transcribe.call_args
        assert call_args[1]['vad_filter'] is True

    def test_transcribe_task_is_transcribe(self, sample_audio_file):
        """Task should be 'transcribe' not 'translate'."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Test"
        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        stt.transcribe(str(sample_audio_file))

        # Should use transcribe task
        call_args = mock_model.transcribe.call_args
        assert call_args[1]['task'] == "transcribe"

    def test_transcribe_error_handling(self, sample_audio_file):
        """Test error handling during transcription."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Transcription failed")

        stt._whisper_model = mock_model
        stt.is_initialized = True

        with pytest.raises(Exception, match="Transcription failed"):
            stt.transcribe(str(sample_audio_file))


class TestFasterWhisperListen:
    """Test listen functionality."""

    def test_listen_success(self):
        """Listen and transcribe successfully."""
        stt = FasterWhisperSTT()

        stt._ensure_initialized = Mock()
        stt.is_initialized = True

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:

            mock_record.return_value = "/tmp/test.wav"
            mock_transcribe.return_value = "Test transcription"

            result = stt.listen()

            assert result == "Test transcription"
            mock_record.assert_called_once_with(timeout=None)
            mock_transcribe.assert_called_once_with("/tmp/test.wav")

    def test_listen_with_timeout(self):
        """Listen with timeout parameter."""
        stt = FasterWhisperSTT()

        stt._ensure_initialized = Mock()
        stt.is_initialized = True

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:

            mock_record.return_value = "/tmp/test.wav"
            mock_transcribe.return_value = "Test"

            result = stt.listen(timeout=30)

            assert result == "Test"
            mock_record.assert_called_once_with(timeout=30)

    def test_listen_timeout_returns_empty_string(self):
        """Listen should return empty string on timeout."""
        stt = FasterWhisperSTT()

        stt._ensure_initialized = Mock()
        stt.is_initialized = True

        with patch.object(stt, '_record_audio') as mock_record:
            mock_record.return_value = None  # Timeout

            result = stt.listen(timeout=5)

            assert result == ""

    def test_listen_cleans_up_temp_file(self):
        """Listen should clean up temporary audio file."""
        stt = FasterWhisperSTT()

        stt._ensure_initialized = Mock()
        stt.is_initialized = True

        # Create actual temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:

            mock_record.return_value = temp_path
            mock_transcribe.return_value = "Test"

            stt.listen()

            # File should be deleted
            assert not os.path.exists(temp_path)

    def test_listen_cleans_up_even_on_error(self):
        """Temp file should be cleaned up even if transcription fails."""
        stt = FasterWhisperSTT()

        stt._ensure_initialized = Mock()
        stt.is_initialized = True

        # Create actual temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            temp_path = f.name

        with patch.object(stt, '_record_audio') as mock_record, \
             patch.object(stt, 'transcribe') as mock_transcribe:

            mock_record.return_value = temp_path
            mock_transcribe.side_effect = Exception("Error")

            with pytest.raises(Exception):
                stt.listen()

            # File should still be deleted
            assert not os.path.exists(temp_path)


class TestFasterWhisperRecordAudio:
    """Test audio recording functionality."""

    def test_record_audio_delegates_to_audio_processor(self):
        """Recording should delegate to AudioProcessor."""
        stt = FasterWhisperSTT()

        mock_audio_processor = Mock()
        mock_audio_processor.record_until_silence.return_value = "/tmp/audio.wav"

        with patch.object(stt, '_get_audio_processor', return_value=mock_audio_processor):
            result = stt._record_audio(timeout=30)

            assert result == "/tmp/audio.wav"
            mock_audio_processor.record_until_silence.assert_called_once_with(timeout=30)

    def test_record_audio_creates_audio_processor(self):
        """Should create AudioProcessor on first use."""
        stt = FasterWhisperSTT()

        assert stt._audio_processor is None

        # Mock AudioProcessor class (imported inside method)
        with patch('speech_mcp_echo.audio_processor.AudioProcessor') as mock_ap_class:
            mock_ap = Mock()
            mock_ap.record_until_silence.return_value = "/tmp/test.wav"
            mock_ap_class.return_value = mock_ap

            result = stt._record_audio()

            # Should have created AudioProcessor
            mock_ap_class.assert_called_once()
            assert stt._audio_processor is not None


class TestFasterWhisperStreaming:
    """Test streaming transcription."""

    def test_transcribe_stream_falls_back_to_listen(self):
        """Streaming should fall back to non-streaming for now."""
        stt = FasterWhisperSTT()

        with patch.object(stt, 'listen') as mock_listen:
            mock_listen.return_value = "Streamed text"

            result = stt.transcribe_stream()

            assert result == "Streamed text"
            mock_listen.assert_called_once()

    def test_transcribe_stream_with_final_callback(self):
        """Streaming should call final callback."""
        stt = FasterWhisperSTT()

        final_callback = Mock()

        with patch.object(stt, 'listen') as mock_listen:
            mock_listen.return_value = "Final text"

            result = stt.transcribe_stream(on_final=final_callback)

            assert result == "Final text"
            final_callback.assert_called_once_with("Final text")

    def test_transcribe_stream_partial_callback_not_used(self):
        """Partial callback not used in fallback implementation."""
        stt = FasterWhisperSTT()

        partial_callback = Mock()

        with patch.object(stt, 'listen') as mock_listen:
            mock_listen.return_value = "Text"

            stt.transcribe_stream(on_partial=partial_callback)

            # Partial callback not used in current implementation
            partial_callback.assert_not_called()


class TestFasterWhisperModels:
    """Test model management."""

    def test_get_available_models(self):
        """Get list of available models."""
        stt = FasterWhisperSTT()

        models = stt.get_available_models()

        assert isinstance(models, list)
        assert "tiny" in models
        assert "base" in models
        assert "small" in models
        assert "medium" in models
        assert "large-v2" in models
        assert "large-v3" in models

    def test_get_available_models_includes_english_variants(self):
        """Available models should include .en variants."""
        stt = FasterWhisperSTT()

        models = stt.get_available_models()

        assert "tiny.en" in models
        assert "base.en" in models
        assert "small.en" in models
        assert "medium.en" in models

    def test_different_compute_types(self):
        """Test different compute type settings."""
        compute_types = ["int8", "float16", "float32"]

        for compute_type in compute_types:
            stt = FasterWhisperSTT(compute_type=compute_type)
            assert stt.compute_type == compute_type

    def test_different_devices(self):
        """Test different device settings."""
        devices = ["cpu", "cuda"]

        for device in devices:
            stt = FasterWhisperSTT(device=device)
            assert stt.device == device


class TestFasterWhisperEdgeCases:
    """Test edge cases and error scenarios."""

    def test_transcribe_nonexistent_file(self):
        """Transcribe non-existent audio file."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()
        mock_model.transcribe.side_effect = FileNotFoundError("File not found")

        stt._whisper_model = mock_model
        stt.is_initialized = True

        with pytest.raises(FileNotFoundError):
            stt.transcribe("/nonexistent/file.wav")

    def test_multiple_segments_combined(self, sample_audio_file):
        """Multiple segments should be combined with spaces."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()

        # Multiple segments
        segments = []
        for text in ["This", "is", "a", "test"]:
            seg = MagicMock()
            seg.text = text
            segments.append(seg)

        mock_info = MagicMock()
        mock_model.transcribe.return_value = (segments, mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        result = stt.transcribe(str(sample_audio_file))

        assert result == "This is a test"

    def test_segment_with_extra_whitespace(self, sample_audio_file):
        """Segments with extra whitespace should be handled."""
        stt = FasterWhisperSTT()

        mock_model = MagicMock()

        seg1 = MagicMock()
        seg1.text = "  Hello  "
        seg2 = MagicMock()
        seg2.text = "  world  "

        mock_info = MagicMock()
        mock_model.transcribe.return_value = ([seg1, seg2], mock_info)

        stt._whisper_model = mock_model
        stt.is_initialized = True

        result = stt.transcribe(str(sample_audio_file))

        # Should strip outer whitespace but preserve space between segments
        assert "Hello" in result
        assert "world" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
