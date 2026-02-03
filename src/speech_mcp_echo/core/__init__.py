"""
Core voice engine - protocol-agnostic voice functionality.

This module contains the core voice capabilities that can be used
by any CLI adapter (MCP, Claude Code, Gemini, Codex, etc.)
"""

from speech_mcp_echo.core.voice_engine import VoiceEngine
from speech_mcp_echo.core.protocol_adapter import ProtocolAdapter

__all__ = ["VoiceEngine", "ProtocolAdapter"]
