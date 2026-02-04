"""
Integration test for timeout functionality across the stack.

This test verifies that the timeout parameter flows correctly through:
1. MCP server tools (server.py)
2. VoiceEngine (voice_engine.py)
3. STT adapter (faster_whisper_adapter.py)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time


class TestTimeoutIntegration:
    """Integration tests for timeout functionality."""

    def test_start_conversation_timeout_flow(self):
        """Test timeout flows through start_conversation MCP tool."""
        from speech_mcp_echo.server import start_conversation, get_engine

        # Mock the engine's listen method
        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = ""  # Simulate timeout
            mock_get_engine.return_value = mock_engine

            # Call with timeout
            result = start_conversation(timeout=5)

            # Should have passed timeout to engine
            mock_engine.listen.assert_called_once_with(timeout=5)

    def test_voice_listen_timeout_flow(self):
        """Test timeout flows through voice_listen MCP tool."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = "Test"
            mock_get_engine.return_value = mock_engine

            result = voice_listen(timeout=10)

            mock_engine.listen.assert_called_once_with(timeout=10)

    def test_voice_reply_timeout_flow(self):
        """Test timeout flows through voice_reply MCP tool."""
        from speech_mcp_echo.server import voice_reply

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.speak.return_value = "Spoken"
            mock_engine.listen.return_value = "Response"
            mock_get_engine.return_value = mock_engine

            result = voice_reply("Hello", wait_for_response=True, timeout=15)

            # Should pass timeout to listen
            mock_engine.listen.assert_called_once_with(timeout=15)

    def test_voice_config_timeout_setting(self):
        """Test voice_config can update timeout setting."""
        from speech_mcp_echo.server import voice_config
        from speech_mcp_echo.config import get_setting

        result = voice_config(stt_timeout=20)

        # Should have updated the config
        assert "STT timeout: 20s" in result
        assert get_setting("stt", "timeout") == 20

    def test_engine_uses_config_default(self):
        """Test VoiceEngine uses config default when no timeout specified."""
        from speech_mcp_echo.core.voice_engine import VoiceEngine
        from speech_mcp_echo.config import set_setting

        # Set config
        set_setting("stt", "timeout", 35)

        engine = VoiceEngine()
        mock_stt = Mock()
        mock_stt.listen.return_value = "Test"
        engine._stt_engine = mock_stt

        # Call without timeout
        engine.listen()

        # Should use config value
        mock_stt.listen.assert_called_once_with(timeout=35)

    def test_timeout_prevents_indefinite_blocking(self):
        """Test that timeout prevents indefinite blocking."""
        from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT
        import threading

        stt = FasterWhisperSTT()

        # Mock threading to simulate blocking behavior
        with patch('speech_mcp_echo.stt_adapters.faster_whisper_adapter.threading.Thread') as mock_thread_class:
            mock_thread = MagicMock()
            # Thread still alive after join = timeout
            mock_thread.is_alive.return_value = True
            mock_thread_class.return_value = mock_thread

            start = time.time()
            result = stt._record_audio(timeout=2)
            elapsed = time.time() - start

            # Should return None on timeout
            assert result is None

            # Should have attempted to join with timeout
            mock_thread.join.assert_called_once_with(timeout=2)

            # Should complete quickly (not block indefinitely)
            assert elapsed < 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
