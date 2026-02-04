"""
Speech MCP Echo - Voice interface for multiple AI CLIs.

Supports Claude Code, Gemini CLI, Codex CLI, Goose, and all MCP-compatible tools.
Uses a single MCP server since all target CLIs support MCP natively.
"""

__version__ = "0.1.0"

from speech_mcp_echo.server import mcp
from speech_mcp_echo.core.voice_engine import VoiceEngine


def main():
    """Main entry point - starts the MCP server."""
    # Start the unified MCP server (works with all CLIs)
    mcp.run()


__all__ = ["mcp", "VoiceEngine", "main", "__version__"]
