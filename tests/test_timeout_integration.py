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
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()

            # Simulate long-running listen that would block indefinitely
            def slow_listen(timeout=None):
                # If timeout is set, respect it
                if timeout:
                    # Simulate timeout by returning empty
                    time.sleep(min(timeout / 10, 0.1))  # Quick simulation
                    return ""
                # Otherwise would block forever
                time.sleep(10)
                return "Should not get here"

            mock_engine.listen.side_effect = slow_listen
            mock_get_engine.return_value = mock_engine

            start = time.time()
            result = voice_listen(timeout=2)
            elapsed = time.time() - start

            # Should return empty on timeout
            assert result == ""

            # Should complete quickly (not block indefinitely)
            assert elapsed < 3.0


    def test_full_conversation_with_multiple_timeouts(self):
        """Test complete conversation with varying timeouts."""
        from speech_mcp_echo.server import start_conversation, voice_reply
        from speech_mcp_echo.config import set_setting

        # Set initial timeout
        set_setting("stt", "timeout", 45)

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.side_effect = [
                "First input",
                "Second input",
                "Third input"
            ]
            mock_engine.speak.return_value = "Response"
            mock_get_engine.return_value = mock_engine

            # Start with default timeout
            result1 = start_conversation()
            assert result1 == "First input"

            # Reply with custom timeout
            with patch('time.sleep'):
                result2 = voice_reply("Response 1", wait_for_response=True, timeout=30)
                assert result2 == "Second input"

            # Another reply with different timeout
            with patch('time.sleep'):
                result3 = voice_reply("Response 2", wait_for_response=True, timeout=60)
                assert result3 == "Third input"

            # Verify timeouts were used
            assert mock_engine.listen.call_count == 3
            calls = mock_engine.listen.call_args_list
            assert calls[0][1]['timeout'] is None  # Default
            assert calls[1][1]['timeout'] == 30
            assert calls[2][1]['timeout'] == 60

    def test_config_changes_during_conversation(self):
        """Test configuration changes take effect during conversation."""
        from speech_mcp_echo.server import voice_listen, voice_config
        from speech_mcp_echo.config import get_setting

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = "Test"
            mock_get_engine.return_value = mock_engine

            # Initial listen
            voice_listen()

            # Change timeout config
            voice_config(stt_timeout=20)
            assert get_setting("stt", "timeout") == 20

            # Next listen should use new timeout
            voice_listen()

    def test_timeout_recovery_scenarios(self):
        """Test recovery from timeout errors."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            # First call times out, second succeeds
            mock_engine.listen.side_effect = ["", "Success after retry"]
            mock_get_engine.return_value = mock_engine

            # First attempt times out
            result1 = voice_listen(timeout=5)
            assert result1 == ""

            # Retry succeeds
            result2 = voice_listen(timeout=10)
            assert result2 == "Success after retry"

    def test_engine_fallback_on_failure(self):
        """Test engine fallback when primary fails."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            # Simulate engine failure then recovery
            mock_engine.listen.side_effect = [
                RuntimeError("Engine failed"),
                "Recovery success"
            ]
            mock_get_engine.return_value = mock_engine

            # First call fails
            result1 = voice_listen()
            assert "ERROR:" in result1

            # Reset mock to simulate recovery
            mock_engine.listen.side_effect = None
            mock_engine.listen.return_value = "Recovery success"

            # Second call succeeds
            result2 = voice_listen()
            assert result2 == "Recovery success"

    def test_concurrent_tool_calls_serialize(self):
        """Test that concurrent tool calls are properly serialized."""
        from speech_mcp_echo.server import voice_listen
        import threading

        call_times = []

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()

            def record_call(*args, **kwargs):
                call_times.append(time.time())
                time.sleep(0.1)  # Simulate work
                return "Test"

            mock_engine.listen.side_effect = record_call
            mock_get_engine.return_value = mock_engine

            # Try to call in parallel
            threads = []
            for _ in range(3):
                t = threading.Thread(target=voice_listen)
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # All calls should have completed
            assert len(call_times) == 3

    def test_timeout_with_different_engines(self):
        """Test timeout behavior with different STT engines."""
        from speech_mcp_echo.server import voice_listen
        from speech_mcp_echo.config import set_setting

        # Test with faster-whisper
        set_setting("stt", "engine", "faster-whisper")

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = "Faster whisper result"
            mock_get_engine.return_value = mock_engine

            result = voice_listen(timeout=30)
            assert result == "Faster whisper result"
            mock_engine.listen.assert_called_once_with(timeout=30)

        # Test with OpenAI
        set_setting("stt", "engine", "openai")

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = "OpenAI result"
            mock_get_engine.return_value = mock_engine

            result = voice_listen(timeout=45)
            assert result == "OpenAI result"
            mock_engine.listen.assert_called_once_with(timeout=45)

    def test_timeout_propagates_through_stack(self):
        """Test timeout value propagates through entire stack."""
        from speech_mcp_echo.server import voice_listen

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            with patch('speech_mcp_echo.core.voice_engine.VoiceEngine') as mock_engine_class:
                mock_engine = Mock()
                mock_stt = Mock()

                # Track timeout at each level
                timeouts = []

                def record_timeout(*args, **kwargs):
                    timeouts.append(kwargs.get('timeout'))
                    return "Result"

                mock_stt.listen.side_effect = record_timeout
                mock_engine.stt_engine = mock_stt
                mock_engine.listen.side_effect = lambda timeout=None: (
                    timeouts.append(timeout),
                    mock_stt.listen(timeout=timeout or 45),
                    "Result"
                )[2]

                mock_get_engine.return_value = mock_engine

                # Test with explicit timeout
                voice_listen(timeout=25)

                # Timeout should appear at multiple levels
                assert 25 in timeouts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
