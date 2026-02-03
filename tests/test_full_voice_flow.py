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
