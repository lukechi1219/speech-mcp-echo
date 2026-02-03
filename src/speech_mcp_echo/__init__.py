"""
Speech MCP Echo - Voice interface for multiple AI CLIs.

Supports Claude Code, Gemini CLI, Codex CLI, and MCP-compatible tools.
"""

__version__ = "0.1.0"

from speech_mcp_echo.core.voice_engine import VoiceEngine


def main():
    """Main entry point for the CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Speech MCP Echo - Voice interface for AI CLIs"
    )
    parser.add_argument(
        "--adapter",
        choices=["auto", "mcp", "claude-code", "gemini", "codex"],
        default="auto",
        help="CLI adapter to use (default: auto-detect)",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the UI",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )

    args = parser.parse_args()

    if args.ui:
        from speech_mcp_echo.ui import launch_ui
        launch_ui()
    else:
        # Start the voice engine with the specified adapter
        engine = VoiceEngine(adapter=args.adapter, config_path=args.config)
        engine.run()


__all__ = ["VoiceEngine", "main", "__version__"]
