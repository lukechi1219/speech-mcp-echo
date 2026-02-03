"""
Gemini CLI adapter for speech-mcp-echo.

TODO: Implement Gemini CLI integration.
"""

import logging
from typing import TYPE_CHECKING

from speech_mcp_echo.core.protocol_adapter import ProtocolAdapter

if TYPE_CHECKING:
    from speech_mcp_echo.core.voice_engine import VoiceEngine

logger = logging.getLogger(__name__)


class GeminiAdapter(ProtocolAdapter):
    """Gemini CLI protocol adapter."""

    @property
    def name(self) -> str:
        return "gemini"

    def run(self, engine: "VoiceEngine") -> None:
        """Run the Gemini adapter."""
        raise NotImplementedError("Gemini adapter not yet implemented")

    def get_capabilities(self) -> dict:
        """Return adapter capabilities."""
        return {
            "name": "speech-mcp-echo",
            "description": "Voice interface for Gemini CLI",
            "status": "not implemented",
        }
