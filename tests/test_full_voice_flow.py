#!/usr/bin/env python3
"""
Integration test for full voice flow: STT → Summarize → TTS

Usage:
    python tests/test_full_voice_flow.py [--skip-stt] [--lang en|zh]

This test will:
1. Listen for voice input (or use sample text if --skip-stt)
2. Summarize the response with JARVIS personality
3. Speak the summary using Google Cloud TTS
"""

import argparse
import sys


def test_full_flow(skip_stt: bool = False, language: str = "en"):
    """Test the complete voice flow."""

    # Sample responses for testing without STT
    sample_responses = {
        "en": """
The src folder contains 12 Python files organized into modules:
- core/ has voice_engine.py and protocol_adapter.py
- adapters/ has claude_code_adapter.py for MCP integration
- stt_adapters/ has faster_whisper_adapter.py for local transcription
- tts_adapters/ has google_tts_adapter.py for cloud TTS
All files follow the adapter pattern for extensibility.
""",
        "zh": """
成功完成檔案分析，發現以下結構：
- src/speech_mcp_echo/ 包含核心模組
- core/ 目錄有語音引擎和協定轉接器
- adapters/ 目錄支援 Claude Code 整合
- tts_adapters/ 目錄提供 Google Cloud TTS
總共有 12 個 Python 檔案。
""",
    }

    # Step 1: Get input (STT or sample)
    print("=" * 50)
    print("Step 1: Input (STT)")
    print("=" * 50)

    if skip_stt:
        print("Skipping STT, using sample response...")
        user_input = sample_responses.get(language, sample_responses["en"])
        print(f"Sample: {user_input[:100]}...")
    else:
        print("Initializing STT (faster-whisper)...")
        from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT

        stt = FasterWhisperSTT(model="base", device="cpu")
        print("Speak now (stop for 3 seconds to end)...")
        user_input = stt.listen()
        print(f"Transcribed: {user_input}")

    # Step 2: Summarize with JARVIS
    print()
    print("=" * 50)
    print("Step 2: Summarize (JARVIS)")
    print("=" * 50)

    from speech_mcp_echo.summarizer.local_summarizer import LocalSummarizer

    lang_code = "zh-Hant" if language == "zh" else "en"
    summarizer = LocalSummarizer(personality="jarvis", language=lang_code)
    summary = summarizer.summarize(user_input)
    print(f"Summary: {summary}")

    # Step 3: Speak with TTS
    print()
    print("=" * 50)
    print("Step 3: Speak (TTS)")
    print("=" * 50)

    from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS

    tts_config = {
        "en": {"language": "en-GB", "voice": "en-GB-Neural2-B"},
        "zh": {"language": "cmn-TW", "voice": "cmn-TW-Standard-B"},
    }
    config = tts_config.get(language, tts_config["en"])

    print(f"Initializing TTS ({config['voice']})...")
    tts = GoogleCloudTTS(**config)

    if tts.is_initialized:
        print("Speaking...")
        tts.speak(summary)
        print("Done!")
    else:
        print("ERROR: TTS not initialized. Check Google Cloud credentials.")
        return False

    print()
    print("=" * 50)
    print("Full voice flow completed successfully!")
    print("=" * 50)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test full voice flow: STT → Summarize → TTS"
    )
    parser.add_argument(
        "--skip-stt",
        action="store_true",
        help="Skip STT and use sample text instead",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Language for summarization and TTS (default: en)",
    )

    args = parser.parse_args()

    try:
        success = test_full_flow(skip_stt=args.skip_stt, language=args.lang)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# =============================================================================
# Pytest Integration Tests
# =============================================================================

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestFullVoiceFlowIntegration:
    """Integration tests for complete voice flow."""

    def test_complete_stt_summarize_tts_flow(self):
        """Test complete STT → Summarize → TTS flow."""
        from speech_mcp_echo.core.voice_engine import VoiceEngine

        # Mock all components
        with patch('speech_mcp_echo.core.voice_engine.VoiceEngine._create_stt_engine') as mock_create_stt:
            with patch('speech_mcp_echo.core.voice_engine.VoiceEngine._create_tts_engine') as mock_create_tts:
                with patch('speech_mcp_echo.core.voice_engine.VoiceEngine._create_summarizer') as mock_create_summarizer:

                    # Setup STT mock
                    mock_stt = Mock()
                    mock_stt.listen.return_value = "Long text response from user"
                    mock_create_stt.return_value = mock_stt

                    # Setup TTS mock
                    mock_tts = Mock()
                    mock_tts.speak.return_value = True
                    mock_create_tts.return_value = mock_tts

                    # Setup summarizer mock
                    mock_summarizer = Mock()
                    mock_summarizer.should_summarize.return_value = True
                    mock_summarizer.summarize.return_value = "Summarized response"
                    mock_create_summarizer.return_value = mock_summarizer

                    # Execute flow
                    engine = VoiceEngine()

                    # Listen
                    transcription = engine.listen()
                    assert transcription == "Long text response from user"

                    # Speak with summarization
                    spoken = engine.speak("Long text response from user", summarize=True)
                    assert spoken == "Summarized response"

                    # Verify flow
                    mock_stt.listen.assert_called_once()
                    mock_summarizer.should_summarize.assert_called_once()
                    mock_summarizer.summarize.assert_called_once()
                    mock_tts.speak.assert_called_once_with("Summarized response")

    def test_multi_turn_conversation(self):
        """Test multi-turn conversation flow."""
        from speech_mcp_echo.server import start_conversation, voice_reply

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()

            # Simulate multi-turn conversation
            mock_engine.listen.side_effect = [
                "Hello, how are you?",
                "What's the weather?",
                "Thank you, goodbye"
            ]
            mock_engine.speak.return_value = "Response"

            mock_get_engine.return_value = mock_engine

            # Turn 1
            user_input_1 = start_conversation()
            assert user_input_1 == "Hello, how are you?"

            # Turn 2
            with patch('time.sleep'):
                user_input_2 = voice_reply("I'm doing well!", wait_for_response=True)
                assert user_input_2 == "What's the weather?"

            # Turn 3
            with patch('time.sleep'):
                user_input_3 = voice_reply("It's sunny!", wait_for_response=True)
                assert user_input_3 == "Thank you, goodbye"

            # End without listening
            result = voice_reply("Goodbye!", wait_for_response=False)
            assert "Spoke:" in result

    def test_language_switching_mid_conversation(self):
        """Test switching language during conversation."""
        from speech_mcp_echo.server import voice_config, voice_speak
        from speech_mcp_echo.config import get_setting

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.speak.return_value = "Spoken"
            mock_get_engine.return_value = mock_engine

            # Start in English
            voice_config(tts_language="en-GB")
            voice_speak("Hello in English")

            assert get_setting("tts", "language") == "en-GB"

            # Switch to Chinese
            voice_config(tts_language="cmn-TW")
            voice_speak("你好")

            assert get_setting("tts", "language") == "cmn-TW"

    def test_engine_switching_mid_conversation(self):
        """Test switching engines during conversation."""
        from speech_mcp_echo.server import voice_config, voice_listen
        from speech_mcp_echo.config import get_setting

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = "Test"
            mock_get_engine.return_value = mock_engine

            # Start with faster-whisper
            voice_config(stt_engine="faster-whisper")
            assert get_setting("stt", "engine") == "faster-whisper"

            # Switch to OpenAI
            voice_config(stt_engine="openai")
            assert get_setting("stt", "engine") == "openai"

            # Config should persist
            voice_listen()
            assert get_setting("stt", "engine") == "openai"

    def test_error_recovery_in_conversation(self):
        """Test error recovery during conversation."""
        from speech_mcp_echo.server import voice_listen, voice_speak

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()

            # Simulate error then recovery
            mock_engine.listen.side_effect = [
                RuntimeError("Temporary error"),
                "Success after error"
            ]
            mock_engine.speak.return_value = "Spoken"

            mock_get_engine.return_value = mock_engine

            # First listen fails
            result1 = voice_listen()
            assert "ERROR:" in result1

            # Speak still works
            result2 = voice_speak("Error occurred")
            assert "Spoke:" in result2

            # Next listen recovers
            mock_engine.listen.side_effect = None
            mock_engine.listen.return_value = "Success after error"
            result3 = voice_listen()
            assert result3 == "Success after error"

    def test_audio_cue_integration_in_flow(self):
        """Test audio cues are played during flow."""
        from speech_mcp_echo.core.voice_engine import VoiceEngine

        with patch('speech_mcp_echo.core.voice_engine.VoiceEngine._create_stt_engine') as mock_create_stt:
            with patch('speech_mcp_echo.core.voice_engine.VoiceEngine._create_tts_engine') as mock_create_tts:
                with patch('speech_mcp_echo.core.voice_engine.VoiceEngine._create_summarizer') as mock_create_summarizer:

                    mock_stt = Mock()
                    mock_stt.listen.return_value = "Test"
                    mock_create_stt.return_value = mock_stt

                    mock_tts = Mock()
                    mock_create_tts.return_value = mock_tts

                    mock_create_summarizer.return_value = None

                    engine = VoiceEngine()

                    # Test callbacks are called
                    listen_start_called = [False]
                    listen_end_called = [False]
                    speak_start_called = [False]
                    speak_end_called = [False]

                    def on_listen_start():
                        listen_start_called[0] = True

                    def on_listen_end():
                        listen_end_called[0] = True

                    def on_speak_start():
                        speak_start_called[0] = True

                    def on_speak_end():
                        speak_end_called[0] = True

                    engine.set_callbacks(
                        on_listening_start=on_listen_start,
                        on_listening_end=on_listen_end,
                        on_speaking_start=on_speak_start,
                        on_speaking_end=on_speak_end
                    )

                    # Listen triggers callbacks
                    engine.listen()
                    assert listen_start_called[0]
                    assert listen_end_called[0]

                    # Speak triggers callbacks
                    engine.speak("Test")
                    assert speak_start_called[0]
                    assert speak_end_called[0]

    def test_timeout_variations_across_flow(self):
        """Test different timeouts at different stages of flow."""
        from speech_mcp_echo.server import start_conversation, voice_reply

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.listen.return_value = "Input"
            mock_engine.speak.return_value = "Spoken"
            mock_get_engine.return_value = mock_engine

            # Start with short timeout
            start_conversation(timeout=10)
            mock_engine.listen.assert_called_with(timeout=10)

            # Middle of conversation with longer timeout
            with patch('time.sleep'):
                voice_reply("Response", wait_for_response=True, timeout=60)
                mock_engine.listen.assert_called_with(timeout=60)

            # End with medium timeout
            with patch('time.sleep'):
                voice_reply("Final", wait_for_response=True, timeout=30)
                mock_engine.listen.assert_called_with(timeout=30)

    def test_summarization_toggle_in_flow(self):
        """Test enabling/disabling summarization during flow."""
        from speech_mcp_echo.server import voice_speak, voice_config

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.speak.return_value = "Spoken"
            mock_get_engine.return_value = mock_engine

            # With summarization
            voice_speak("Long text", summarize=True)
            mock_engine.speak.assert_called_with("Long text", summarize=True)

            # Without summarization
            voice_speak("Short text", summarize=False)
            mock_engine.speak.assert_called_with("Short text", summarize=False)

    def test_complete_flow_with_all_languages(self):
        """Test complete flow with English and Chinese."""
        from speech_mcp_echo.server import voice_config, voice_speak
        from speech_mcp_echo.config import get_setting

        with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_engine.speak.return_value = "Spoken"
            mock_get_engine.return_value = mock_engine

            # English
            voice_config(tts_language="en-GB", summarizer_personality="jarvis")
            voice_speak("Test in English")
            assert get_setting("tts", "language") == "en-GB"

            # Traditional Chinese
            voice_config(tts_language="cmn-TW", summarizer_personality="jarvis")
            voice_speak("繁體中文測試")
            assert get_setting("tts", "language") == "cmn-TW"

            # Simplified Chinese
            voice_config(tts_language="cmn-CN")
            voice_speak("简体中文测试")
            assert get_setting("tts", "language") == "cmn-CN"

    def test_all_cli_scenarios(self):
        """Test flow works with all CLI types."""
        from speech_mcp_echo.server import voice_status, detect_cli

        cli_envs = [
            ("CLAUDE_CODE", "1", "claude-code"),
            ("GEMINI_CLI", "1", "gemini"),
            ("CODEX_CLI", "1", "codex"),
        ]

        for env_var, env_value, expected_cli in cli_envs:
            with patch('speech_mcp_echo.server.get_engine') as mock_get_engine:
                mock_engine = Mock()
                mock_engine.stt_engine = Mock(is_initialized=True)
                mock_engine.tts_engine = Mock(is_initialized=True)
                mock_engine.summarizer = None
                mock_get_engine.return_value = mock_engine

                # Set environment
                import os
                old_value = os.environ.get(env_var)
                os.environ[env_var] = env_value

                try:
                    # Should detect correct CLI
                    assert detect_cli() == expected_cli

                    # Status should include CLI
                    status = voice_status()
                    assert expected_cli in status
                finally:
                    # Restore environment
                    if old_value is None:
                        os.environ.pop(env_var, None)
                    else:
                        os.environ[env_var] = old_value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
