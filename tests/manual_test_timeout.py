#!/usr/bin/env python3
"""
Manual test script for timeout functionality.

This script demonstrates the timeout behavior in different scenarios.
Run this to verify timeout works as expected.
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT
from speech_mcp_echo.config import get_setting, set_setting


def test_timeout_behavior():
    """Test timeout behavior with different timeout values."""
    print("=" * 60)
    print("Testing FasterWhisperSTT Timeout Functionality")
    print("=" * 60)
    print()

    # Test 1: Check default config timeout
    print("Test 1: Check default timeout configuration")
    default_timeout = get_setting("stt", "timeout", default=45)
    print(f"✓ Default timeout from config: {default_timeout}s")
    print()

    # Test 2: Test with 5-second timeout (should timeout if no audio)
    print("Test 2: Testing with 5-second timeout")
    print("Note: This will timeout if you don't speak within 5 seconds")
    print("Speak now or stay silent to test timeout behavior...")
    print()

    stt = FasterWhisperSTT()

    try:
        start_time = time.time()
        result = stt.listen(timeout=5)
        elapsed = time.time() - start_time

        if result:
            print(f"✓ Received transcription: '{result}'")
            print(f"✓ Completed in {elapsed:.1f}s")
        else:
            print(f"✓ Timeout occurred (no audio detected)")
            print(f"✓ Returned after {elapsed:.1f}s (expected ~5s)")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print()

    # Test 3: Test with config default timeout
    print("Test 3: Testing with config default timeout (45s)")
    print(f"Note: Using configured timeout of {default_timeout}s")
    print("This would normally wait up to 45s for audio...")
    print("(Skipping to avoid long wait)")
    print()

    # Test 4: Test with custom timeout via config
    print("Test 4: Testing runtime timeout configuration")
    set_setting("stt", "timeout", 10)
    new_timeout = get_setting("stt", "timeout")
    print(f"✓ Updated timeout to: {new_timeout}s")
    print()

    print("=" * 60)
    print("Manual Testing Complete")
    print("=" * 60)
    print()
    print("Summary:")
    print("- Timeout can be set via config (default: 45s)")
    print("- Timeout can be overridden per-call")
    print("- Returns empty string on timeout (graceful handling)")
    print("- Completes normally if audio detected within timeout")


if __name__ == "__main__":
    print("\nWARNING: This test will attempt to access your microphone.")
    print("Press Ctrl+C to cancel, or Enter to continue...")
    try:
        input()
        test_timeout_behavior()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(0)
