"""
MCP adapter for speech-mcp-echo.

Generic MCP adapter for MCP-compatible tools like Goose.
This is the base MCP implementation that other adapters can extend.
"""

import logging
from typing import TYPE_CHECKING

from speech_mcp_echo.core.protocol_adapter import ProtocolAdapter

if TYPE_CHECKING:
    from speech_mcp_echo.core.voice_engine import VoiceEngine

logger = logging.getLogger(__name__)


class MCPAdapter(ProtocolAdapter):
    """
    Generic MCP protocol adapter.

    Provides standard MCP tools for voice interaction.
    Compatible with any MCP client (Goose, etc.).
    """

    @property
    def name(self) -> str:
        return "mcp"

    def run(self, engine: "VoiceEngine") -> None:
        """
        Run the MCP adapter.

        Starts an MCP server with voice tools.

        Args:
            engine: The VoiceEngine instance
        """
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError:
            logger.error("MCP package not installed. Install: pip install mcp")
            raise

        mcp = FastMCP("speech-mcp-echo")

        @mcp.tool()
        def listen() -> str:
            """
            Listen for voice input.

            Returns:
                Transcribed text from speech
            """
            return engine.listen()

        @mcp.tool()
        def speak(text: str) -> str:
            """
            Speak text using TTS.

            Args:
                text: Text to speak

            Returns:
                Confirmation message
            """
            spoken = engine.speak(text)
            return f"Spoke: {spoken}"

        @mcp.tool()
        def reply(text: str, wait_for_response: bool = True) -> str:
            """
            Speak and optionally listen for response.

            Args:
                text: Text to speak
                wait_for_response: Whether to listen after speaking

            Returns:
                User's response or confirmation
            """
            engine.speak(text)
            if wait_for_response:
                import time
                time.sleep(0.5)
                return engine.listen()
            return "OK"

        logger.info("Starting MCP adapter...")
        mcp.run()

    def get_capabilities(self) -> dict:
        """Return adapter capabilities."""
        return {
            "name": "speech-mcp-echo",
            "description": "Voice interface for MCP",
            "tools": ["listen", "speak", "reply"],
        }
