"""
Protocol adapters for speech-mcp-echo.

Each adapter connects the VoiceEngine to a specific CLI protocol.
Supported: MCP (Goose), Claude Code, Gemini CLI, Codex CLI.
"""

# Import available adapters
try:
    from speech_mcp_echo.adapters.mcp_adapter import MCPAdapter
except ImportError:
    pass

try:
    from speech_mcp_echo.adapters.claude_code_adapter import ClaudeCodeAdapter
except ImportError:
    pass

try:
    from speech_mcp_echo.adapters.gemini_adapter import GeminiAdapter
except ImportError:
    pass

try:
    from speech_mcp_echo.adapters.codex_adapter import CodexAdapter
except ImportError:
    pass
