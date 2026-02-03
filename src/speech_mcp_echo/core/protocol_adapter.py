"""
Protocol Adapter - Base class for CLI protocol adapters.

Each CLI (MCP, Claude Code, Gemini, Codex) has its own adapter
that implements this interface to provide voice capabilities.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speech_mcp_echo.core.voice_engine import VoiceEngine


class ProtocolAdapter(ABC):
    """
    Base class for CLI protocol adapters.

    Each adapter translates between the CLI's protocol and the VoiceEngine.
    """

    @abstractmethod
    def run(self, engine: "VoiceEngine") -> None:
        """
        Run the adapter with the given voice engine.

        This is the main entry point that starts the adapter's event loop
        or server, depending on the protocol.

        Args:
            engine: The VoiceEngine instance to use
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> dict:
        """
        Return the capabilities this adapter provides.

        Returns:
            Dictionary describing available tools/commands
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the adapter name."""
        pass
