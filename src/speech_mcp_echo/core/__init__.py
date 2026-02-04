"""
Core voice engine - protocol-agnostic voice functionality.

This module contains the core voice capabilities that are used
directly by the MCP server (server.py) for all CLIs.
"""

from speech_mcp_echo.core.voice_engine import VoiceEngine

__all__ = ["VoiceEngine"]
