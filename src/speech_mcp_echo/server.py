"""
Unified MCP server for speech-mcp-echo.

Provides voice interaction capabilities for any MCP-compatible CLI:
- Claude Code
- Gemini CLI
- Codex CLI
- Goose CLI

All CLIs connect to the same MCP server since they all support MCP natively.
"""

import logging
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from speech_mcp_echo.core.voice_engine import VoiceEngine
from speech_mcp_echo.config import get_setting, set_setting, load_config

logger = logging.getLogger(__name__)

mcp = FastMCP("speech-mcp-echo")

# Lazy-initialized voice engine
_engine: Optional[VoiceEngine] = None


def get_engine() -> VoiceEngine:
    """Get or create the voice engine singleton."""
    global _engine
    if _engine is None:
        _engine = VoiceEngine()
        logger.info("VoiceEngine initialized")
    return _engine


@mcp.tool()
def start_conversation() -> str:
    """
    Start a voice conversation by listening for user speech.

    Use this tool when the user wants to have a voice conversation, such as:
    - "Let's talk using voice"
    - "Can we have a voice conversation?"
    - "I'd like to speak instead of typing"
    - "Start voice mode"

    This tool will:
    1. Initialize the speech recognition system
    2. Start listening for user voice input
    3. Automatically stop when the user finishes speaking (silence detection)
    4. Return the transcribed text

    After receiving the user's voice input, use voice_reply() to respond
    and continue the conversation.

    Returns:
        The transcription of the user's speech.
    """
    engine = get_engine()
    logger.info("Starting voice conversation...")
    try:
        transcription = engine.listen()
        return transcription
    except Exception as e:
        logger.error(f"Start conversation failed: {e}")
        return f"ERROR: Failed to start conversation - {str(e)}"


@mcp.tool()
def voice_listen() -> str:
    """
    Listen for voice input and return the transcription.

    Start listening for speech through the microphone.
    Recording stops automatically after detecting silence.

    Returns:
        The transcribed text from speech.
    """
    engine = get_engine()
    logger.info("Starting voice listening...")
    try:
        transcription = engine.listen()
        return transcription
    except Exception as e:
        logger.error(f"Listen failed: {e}")
        return f"ERROR: Failed to listen - {str(e)}"


@mcp.tool()
def voice_speak(text: str, summarize: bool = True) -> str:
    """
    Speak text using text-to-speech.

    Convert text to speech and play it through speakers.
    Long text is automatically summarized for better listening experience.

    Args:
        text: The text to speak aloud
        summarize: Whether to summarize long text (default: True)

    Returns:
        The text that was actually spoken (may be summarized).
    """
    engine = get_engine()
    logger.info(f"Speaking: {text[:50]}...")
    try:
        spoken_text = engine.speak(text, summarize=summarize)
        return f"Spoke: {spoken_text}"
    except Exception as e:
        logger.error(f"Speak failed: {e}")
        return f"ERROR: Failed to speak - {str(e)}"


@mcp.tool()
def voice_reply(text: str, wait_for_response: bool = True) -> str:
    """
    Speak text and optionally wait for voice response.

    Use this tool during voice conversations to:
    1. Speak your response to the user (with automatic summarization)
    2. Immediately listen for the user's next voice input

    This creates natural turn-taking in voice conversations:
    - AI speaks → User speaks → AI speaks → User speaks...

    Typical workflow:
    1. User says "Let's talk" → Use start_conversation() to get first input
    2. AI processes → Use voice_reply("response", wait=True) to respond and listen
    3. Repeat step 2 for continued conversation
    4. Use voice_reply("goodbye", wait=False) to end without listening

    Args:
        text: The text to speak aloud (long text is automatically summarized)
        wait_for_response: Whether to listen for response after speaking (default: True)

    Returns:
        If wait_for_response=True: the user's spoken response (transcribed text)
        If wait_for_response=False: confirmation that text was spoken
    """
    engine = get_engine()
    logger.info(f"Voice reply: {text[:50]}...")
    try:
        spoken = engine.speak(text, summarize=True)

        if wait_for_response:
            time.sleep(0.5)
            response = engine.listen()
            return response
        else:
            return f"Spoke: {spoken}"
    except Exception as e:
        logger.error(f"Voice reply failed: {e}")
        return f"ERROR: Voice reply failed - {str(e)}"


@mcp.tool()
def voice_config(
    stt_engine: Optional[str] = None,
    tts_engine: Optional[str] = None,
    tts_voice: Optional[str] = None,
    tts_language: Optional[str] = None,
    summarizer_enabled: Optional[bool] = None,
    summarizer_personality: Optional[str] = None,
) -> str:
    """
    Configure voice settings.

    Allows runtime configuration of STT, TTS, and summarizer settings.

    Args:
        stt_engine: STT engine (faster-whisper, openai, google)
        tts_engine: TTS engine (google, kokoro, openai, pyttsx3)
        tts_voice: TTS voice name
        tts_language: TTS language code
        summarizer_enabled: Enable/disable summarization
        summarizer_personality: Summarizer personality (jarvis, neutral)

    Returns:
        Current configuration after changes
    """
    changes = []

    if stt_engine is not None:
        set_setting("stt", "engine", stt_engine)
        changes.append(f"STT engine: {stt_engine}")

    if tts_engine is not None:
        set_setting("tts", "engine", tts_engine)
        changes.append(f"TTS engine: {tts_engine}")

    if tts_voice is not None:
        set_setting("tts", "voice", tts_voice)
        changes.append(f"TTS voice: {tts_voice}")

    if tts_language is not None:
        set_setting("tts", "language", tts_language)
        changes.append(f"TTS language: {tts_language}")

    if summarizer_enabled is not None:
        set_setting("summarizer", "enabled", summarizer_enabled)
        changes.append(f"Summarizer: {'enabled' if summarizer_enabled else 'disabled'}")

    if summarizer_personality is not None:
        set_setting("summarizer", "personality", summarizer_personality)
        changes.append(f"Summarizer personality: {summarizer_personality}")

    config_summary = {
        "stt_engine": get_setting("stt", "engine"),
        "tts_engine": get_setting("tts", "engine"),
        "tts_voice": get_setting("tts", "voice"),
        "tts_language": get_setting("tts", "language"),
        "summarizer_enabled": get_setting("summarizer", "enabled"),
        "summarizer_personality": get_setting("summarizer", "personality"),
    }

    if changes:
        return f"Updated: {', '.join(changes)}\n\nCurrent config: {config_summary}"
    else:
        return f"Current config: {config_summary}"


@mcp.tool()
def voice_status() -> str:
    """
    Get voice system status.

    Returns information about the current state of the voice system,
    including initialized engines and available features.

    Returns:
        Status information as a formatted string
    """
    engine = get_engine()
    status_lines = ["Voice System Status:", ""]

    # STT status
    try:
        stt = engine.stt_engine
        status_lines.append(f"STT Engine: {get_setting('stt', 'engine')}")
        if hasattr(stt, 'model'):
            status_lines.append(f"  Model: {stt.model}")
        status_lines.append(f"  Initialized: {stt.is_initialized}")
    except Exception as e:
        status_lines.append(f"STT Engine: Error - {e}")

    status_lines.append("")

    # TTS status
    try:
        tts = engine.tts_engine
        status_lines.append(f"TTS Engine: {get_setting('tts', 'engine')}")
        if hasattr(tts, 'voice'):
            status_lines.append(f"  Voice: {tts.voice}")
        if hasattr(tts, 'language'):
            status_lines.append(f"  Language: {tts.language}")
        status_lines.append(f"  Initialized: {tts.is_initialized}")
    except Exception as e:
        status_lines.append(f"TTS Engine: Error - {e}")

    status_lines.append("")

    # Summarizer status
    if engine.summarizer:
        status_lines.append("Summarizer: Enabled")
        if hasattr(engine.summarizer, 'personality'):
            status_lines.append(f"  Personality: {engine.summarizer.personality}")
        if hasattr(engine.summarizer, 'language'):
            status_lines.append(f"  Language: {engine.summarizer.language}")
    else:
        status_lines.append("Summarizer: Disabled")

    # CLI detection
    status_lines.append("")
    status_lines.append(f"Detected CLI: {detect_cli()}")

    return "\n".join(status_lines)


def detect_cli() -> str:
    """Detect which CLI is running for informational purposes."""
    import os

    if os.environ.get("CLAUDE_CODE"):
        return "claude-code"
    elif os.environ.get("GEMINI_CLI"):
        return "gemini"
    elif os.environ.get("CODEX_CLI"):
        return "codex"
    return "generic"


def main():
    """Run the MCP server."""
    logger.info("Starting speech-mcp-echo MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
