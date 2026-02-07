"""
Unified MCP server for speech-mcp-echo.

Provides voice interaction capabilities for any MCP-compatible CLI:
- Claude Code
- Gemini CLI
- Codex CLI
- Goose CLI

All CLIs connect to the same MCP server since they all support MCP natively.

Continuous Listening Feature (v0.2.0):
- Start/Poll mode for non-blocking voice conversations
- Automatic retry on silence with configurable prompts
- Session-based background listening
"""

import logging
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from mcp.server.fastmcp import FastMCP

from speech_mcp_echo.core.voice_engine import VoiceEngine
from speech_mcp_echo.config import get_setting, set_setting, load_config
from speech_mcp_echo.utils.logger import setup_logging

# Initialize file logging before any logger is created
setup_logging(level=logging.INFO)

logger = logging.getLogger(__name__)

mcp = FastMCP("speech-mcp-echo")

# Lazy-initialized voice engine
_engine: Optional[VoiceEngine] = None


# =============================================================================
# Background Listening Session Management (Start/Poll Mode)
# =============================================================================


@dataclass
class ListeningSession:
    """Represents a background listening session."""

    id: str
    status: str  # "listening", "completed", "timeout", "error", "cancelled"
    result: str = ""
    retry_count: int = 0
    max_retries: int = 10
    error_message: str = ""
    created_at: float = field(default_factory=time.time)


# Global session storage with thread safety
_listening_sessions: dict[str, ListeningSession] = {}
_session_lock = threading.Lock()

# Session cleanup threshold (30 minutes)
_SESSION_TTL_SECONDS = 1800


def get_engine() -> VoiceEngine:
    """Get or create the voice engine singleton."""
    global _engine
    if _engine is None:
        _engine = VoiceEngine()
        logger.info("VoiceEngine initialized")
    return _engine


def _cleanup_expired_sessions() -> int:
    """Remove sessions older than TTL. Returns count of removed sessions."""
    now = time.time()
    expired = []
    with _session_lock:
        for session_id, session in _listening_sessions.items():
            if now - session.created_at > _SESSION_TTL_SECONDS:
                expired.append(session_id)
        for session_id in expired:
            del _listening_sessions[session_id]
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired listening sessions")
    return len(expired)


def _play_retry_prompt(prompt_type: str) -> None:
    """Play a retry prompt to indicate the system is still listening."""
    if prompt_type == "silent":
        return

    if prompt_type == "beep" and sys.platform == "darwin":
        # macOS system sound - non-blocking
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Tink.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif prompt_type == "voice":
        # Use TTS for voice prompt (blocking but short)
        try:
            engine = get_engine()
            engine.speak("Still listening...", summarize=False)
        except Exception as e:
            logger.warning(f"Voice prompt failed: {e}")


def _background_listen(session_id: str, timeout: Optional[int]) -> None:
    """Background thread: listen with automatic retry on silence."""
    engine = get_engine()
    prompt_type = get_setting("stt", "retry_prompt_type", default="beep")

    with _session_lock:
        session = _listening_sessions.get(session_id)
        if not session:
            return

    for attempt in range(session.max_retries + 1):
        # Check if session was cancelled
        with _session_lock:
            current_session = _listening_sessions.get(session_id)
            if not current_session or current_session.status == "cancelled":
                logger.info(f"Session {session_id} was cancelled")
                return

        # Update retry count
        with _session_lock:
            if session_id in _listening_sessions:
                _listening_sessions[session_id].retry_count = attempt

        # Listen for speech
        try:
            result = engine.listen(timeout=timeout)

            if result and result.strip():
                with _session_lock:
                    if session_id in _listening_sessions:
                        _listening_sessions[session_id].status = "completed"
                        _listening_sessions[session_id].result = result
                logger.info(f"Session {session_id}: got speech on attempt {attempt + 1}")
                return
        except Exception as e:
            logger.error(f"Session {session_id}: listen error - {e}")
            with _session_lock:
                if session_id in _listening_sessions:
                    _listening_sessions[session_id].status = "error"
                    _listening_sessions[session_id].error_message = str(e)
            return

        # No speech detected, play prompt and retry
        if attempt < session.max_retries:
            logger.info(
                f"Session {session_id}: silence timeout, retry {attempt + 1}/{session.max_retries}"
            )
            _play_retry_prompt(prompt_type)
            time.sleep(0.3)  # Brief pause before retry

    # All retries exhausted
    with _session_lock:
        if session_id in _listening_sessions:
            _listening_sessions[session_id].status = "timeout"
    logger.info(f"Session {session_id}: all retries exhausted")


# =============================================================================
# MCP Tools - Start/Poll Mode (Non-blocking for Claude Code)
# =============================================================================


@mcp.tool()
def start_listening(
    timeout: Optional[int] = None,
    silence_retry_count: Optional[int] = None,
) -> str:
    """
    Start background listening and return immediately with a session ID.

    ⚡ NON-BLOCKING: This tool returns immediately while listening continues
    in the background. Use check_listening() to poll for results.

    Recommended workflow:
    1. Call start_listening() → get session_id
    2. Continue other tasks (respond to user, process code, etc.)
    3. Periodically call check_listening(session_id) to check status
    4. When status is "completed", process the user's speech

    The system automatically retries when silence is detected, playing a
    subtle beep to indicate it's still listening. This allows continuous
    voice conversations without blocking the CLI.

    Args:
        timeout: Timeout per listen attempt in seconds (default: 45)
        silence_retry_count: Number of silence retries (default: 10, ~7.5 min tolerance)

    Returns:
        A message containing the session_id for use with check_listening()
    """
    # Cleanup old sessions periodically
    _cleanup_expired_sessions()

    session_id = str(uuid.uuid4())[:8]

    if silence_retry_count is None:
        silence_retry_count = get_setting("stt", "silence_retry_count", default=10)

    session = ListeningSession(
        id=session_id,
        status="listening",
        max_retries=silence_retry_count,
    )

    with _session_lock:
        _listening_sessions[session_id] = session

    # Start background listening thread
    thread = threading.Thread(
        target=_background_listen,
        args=(session_id, timeout),
        daemon=True,
    )
    thread.start()

    logger.info(f"Started listening session {session_id} with {silence_retry_count} retries")

    return (
        f"Listening started. Session ID: {session_id}\n"
        f"Use check_listening('{session_id}') to get results.\n"
        f"Max retries on silence: {silence_retry_count}"
    )


@mcp.tool()
def check_listening(session_id: str) -> str:
    """
    Check the status and result of a background listening session.

    Status meanings:
    - "listening": Still listening, check again later
    - "completed": Speech detected! The result contains the transcription
    - "timeout": All retries exhausted, no speech detected
    - "error": An error occurred during listening
    - "cancelled": Session was cancelled

    Recommended actions based on status:
    - "listening" → Continue other tasks, check again in a few seconds
    - "completed" → Parse "User said: ..." and respond to the user
    - "timeout" → Ask if user is still there, or end conversation
    - "error" → Handle the error, possibly restart listening

    Args:
        session_id: The session ID from start_listening()

    Returns:
        Status and result of the listening session
    """
    with _session_lock:
        session = _listening_sessions.get(session_id)

    if not session:
        return f"ERROR: Session '{session_id}' not found. It may have expired or never existed."

    if session.status == "listening":
        return (
            f"Status: listening (attempt {session.retry_count + 1}/{session.max_retries + 1})\n"
            "Still waiting for speech..."
        )
    elif session.status == "completed":
        return f"Status: completed\nUser said: {session.result}"
    elif session.status == "timeout":
        return (
            "Status: timeout\n"
            f"No speech detected after {session.max_retries + 1} attempts.\n"
            "The user may have left or is thinking."
        )
    elif session.status == "error":
        return f"Status: error\nError: {session.error_message}"
    elif session.status == "cancelled":
        return "Status: cancelled\nThe session was cancelled."
    else:
        return f"Status: {session.status}"


@mcp.tool()
def cancel_listening(session_id: str) -> str:
    """
    Cancel a background listening session.

    Use this to stop a listening session before it completes,
    for example when the user types instead of speaking.

    Args:
        session_id: The session ID from start_listening()

    Returns:
        Confirmation of cancellation
    """
    with _session_lock:
        session = _listening_sessions.get(session_id)
        if not session:
            return f"ERROR: Session '{session_id}' not found."

        if session.status == "listening":
            session.status = "cancelled"
            logger.info(f"Session {session_id} cancelled by user")
            return f"Session {session_id} cancelled."
        else:
            return f"Session {session_id} already finished with status: {session.status}"


# =============================================================================
# MCP Tools - Original Blocking Mode (Preserved for Compatibility)
# =============================================================================


@mcp.tool()
def start_conversation(timeout: Optional[int] = None) -> str:
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

    Args:
        timeout: Optional timeout in seconds (overrides config default of 45s)

    Returns:
        The transcription of the user's speech.
    """
    engine = get_engine()
    timeout_msg = f" (timeout: {timeout}s)" if timeout else ""
    logger.info(f"Starting voice conversation{timeout_msg}...")
    try:
        transcription = engine.listen(timeout=timeout)
        return transcription
    except Exception as e:
        logger.error(f"Start conversation failed: {e}")
        return f"ERROR: Failed to start conversation - {str(e)}"


@mcp.tool()
def voice_listen(timeout: Optional[int] = None) -> str:
    """
    Listen for voice input and return the transcription.

    Start listening for speech through the microphone.
    Recording stops automatically after detecting silence.

    Args:
        timeout: Optional timeout in seconds (overrides config default of 45s)

    Returns:
        The transcribed text from speech.
    """
    engine = get_engine()
    timeout_msg = f" (timeout: {timeout}s)" if timeout else ""
    logger.info(f"Starting voice listening{timeout_msg}...")
    try:
        transcription = engine.listen(timeout=timeout)
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
def voice_reply(text: str, wait_for_response: bool = True, timeout: Optional[int] = None) -> str:
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
        timeout: Optional timeout in seconds for listening (overrides config default of 45s)

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
            response = engine.listen(timeout=timeout)
            return response
        else:
            return f"Spoke: {spoken}"
    except Exception as e:
        logger.error(f"Voice reply failed: {e}")
        return f"ERROR: Voice reply failed - {str(e)}"


@mcp.tool()
def voice_config(
    stt_engine: Optional[str] = None,
    stt_timeout: Optional[int] = None,
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
        stt_timeout: STT timeout in seconds (default: 45)
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
        if _engine is not None:
            _engine.reset_stt()

    if stt_timeout is not None:
        set_setting("stt", "timeout", stt_timeout)
        changes.append(f"STT timeout: {stt_timeout}s")

    if tts_engine is not None:
        set_setting("tts", "engine", tts_engine)
        changes.append(f"TTS engine: {tts_engine}")
        if _engine is not None:
            _engine.reset_tts()

    if tts_voice is not None:
        set_setting("tts", "voice", tts_voice)
        changes.append(f"TTS voice: {tts_voice}")
        # Auto-sync language from voice (e.g., "en-US-Standard-B" -> "en-US")
        if "-" in tts_voice:
            voice_lang = "-".join(tts_voice.split("-")[:2])
            current_lang = get_setting("tts", "language")
            if current_lang != voice_lang:
                set_setting("tts", "language", voice_lang)
                changes.append(f"TTS language auto-synced: {voice_lang}")
        if _engine is not None:
            _engine.reset_tts()

    if tts_language is not None:
        set_setting("tts", "language", tts_language)
        changes.append(f"TTS language: {tts_language}")
        # Auto-sync voice to match language (use Standard-B as default)
        current_voice = get_setting("tts", "voice", "")
        if not current_voice.startswith(tts_language):
            default_voice = f"{tts_language}-Standard-B"
            set_setting("tts", "voice", default_voice)
            changes.append(f"TTS voice auto-synced: {default_voice}")
        if _engine is not None:
            _engine.reset_tts()

    if summarizer_enabled is not None:
        set_setting("summarizer", "enabled", summarizer_enabled)
        changes.append(f"Summarizer: {'enabled' if summarizer_enabled else 'disabled'}")
        if _engine is not None:
            _engine.reset_summarizer()

    if summarizer_personality is not None:
        set_setting("summarizer", "personality", summarizer_personality)
        changes.append(f"Summarizer personality: {summarizer_personality}")
        if _engine is not None:
            _engine.reset_summarizer()

    config_summary = {
        "stt_engine": get_setting("stt", "engine"),
        "stt_timeout": get_setting("stt", "timeout"),
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
