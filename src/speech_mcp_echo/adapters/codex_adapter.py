"""
Codex CLI adapter for speech-mcp-echo.

TODO: Implement Codex CLI integration.
"""

import logging
from typing import TYPE_CHECKING

from speech_mcp_echo.core.protocol_adapter import ProtocolAdapter

if TYPE_CHECKING:
    from speech_mcp_echo.core.voice_engine import VoiceEngine

logger = logging.getLogger(__name__)


class CodexAdapter(ProtocolAdapter):
    """Codex CLI protocol adapter."""

    @property
    def name(self) -> str:
        return "codex"

    def run(self, engine: "VoiceEngine") -> None:
        """Run the Codex adapter."""
        raise NotImplementedError("Codex adapter not yet implemented")

    def get_capabilities(self) -> dict:
        """Return adapter capabilities."""
        return {
            "name": "speech-mcp-echo",
            "description": "Voice interface for Codex CLI",
            "status": "not implemented",
        }
