"""
Entry point for running speech-mcp-echo as a module.

Usage:
    python -m speech_mcp_echo [--ui]

Starts the MCP server that works with all MCP-compatible CLIs:
- Claude Code
- Gemini CLI
- Codex CLI
- Goose CLI
"""

from speech_mcp_echo import main

if __name__ == "__main__":
    main()
