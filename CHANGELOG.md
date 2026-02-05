# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-05

### Added
- Initial MCP server implementation
- faster-whisper STT adapter (local, recommended)
- OpenAI Whisper STT adapter (cloud)
- Google Speech STT adapter (cloud)
- Google Cloud TTS adapter (cloud, recommended)
- OpenAI TTS adapter (cloud)
- JARVIS-style response summarizer
- Bilingual support (English, Chinese Traditional/Simplified)
- Audio cue system (start/stop listening sounds)
- Configuration management via JSON
- Comprehensive documentation (README, CLAUDE.md, README_zh_TW.md)
- Core voice engine implementation
- Multi-CLI support (Claude Code, Gemini CLI, Codex CLI, Goose)

### Changed
- Simplified architecture to single unified MCP server
- Removed PyQt5 UI (not needed for MCP-based interface)

### Fixed
- Audio timeout handling for MCP tool calls
- Documentation accuracy (removed references to non-existent files)

[Unreleased]: https://github.com/lukechi1219/speech-mcp-echo/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lukechi1219/speech-mcp-echo/releases/tag/v0.1.0
