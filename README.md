# Speech MCP Echo

Voice interface for multiple AI CLIs - Claude Code, Gemini CLI, Codex CLI, and MCP-compatible tools.

## Features

- **Multi-CLI Support**: Works with Claude Code, Gemini CLI, Codex CLI, and any MCP-compatible tool
- **Configurable STT**: Local (faster-whisper) or cloud (OpenAI Whisper, Google Speech)
- **Configurable TTS**: Local (Kokoro) or cloud (Google Cloud TTS, OpenAI TTS)
- **JARVIS Summarizer**: Condenses long responses into concise, entertaining summaries
- **PyQt5 UI**: Audio visualization and status display (coming soon)

## Installation

```bash
# Basic installation
pip install speech-mcp-echo

# With local STT/TTS
pip install speech-mcp-echo[local-stt,local-tts]

# With cloud services
pip install speech-mcp-echo[cloud]

# Everything
pip install speech-mcp-echo[all]
```

### Prerequisites

- Python 3.10+
- PortAudio: `brew install portaudio` (macOS)
- For Google Cloud TTS: `gcloud` CLI configured with a project

## Quick Start

### With Claude Code

Add to your Claude Code MCP configuration (`~/.claude.json`):

```json
{
  "mcpServers": {
    "speech-mcp-echo": {
      "command": "python",
      "args": ["-m", "speech_mcp_echo", "--adapter", "claude-code"]
    }
  }
}
```

Then in Claude Code, you can use:
- `voice_listen` - Listen for voice input
- `voice_speak` - Speak text using TTS
- `voice_reply` - Speak and wait for response
- `voice_config` - Configure voice settings
- `voice_status` - Check voice system status

### Standalone

```bash
# Run as MCP server (for Goose, etc.)
speech-mcp-echo

# Run with specific adapter
speech-mcp-echo --adapter claude-code

# Launch UI
speech-mcp-echo --ui
```

## Configuration

Configuration is stored at `~/.config/speech-mcp-echo/config.json`:

```json
{
  "stt": {
    "engine": "faster-whisper",
    "model": "base",
    "device": "cpu"
  },
  "tts": {
    "engine": "google",
    "voice": "cmn-TW-Standard-B",
    "language": "cmn-TW"
  },
  "summarizer": {
    "enabled": true,
    "personality": "jarvis",
    "language": "en"
  }
}
```

### Environment Variables

API keys are read from environment variables:

- `OPENAI_API_KEY` - For OpenAI Whisper STT and TTS
- `GOOGLE_APPLICATION_CREDENTIALS` - For Google Cloud services
- `ANTHROPIC_API_KEY` - For Claude-based summarization

## Architecture

```
speech_mcp_echo/
├── core/                    # Protocol-agnostic core
│   ├── voice_engine.py      # Main voice functionality
│   └── protocol_adapter.py  # Base adapter interface
├── adapters/                # CLI protocol adapters
│   ├── claude_code_adapter.py
│   ├── mcp_adapter.py
│   ├── gemini_adapter.py
│   └── codex_adapter.py
├── stt_adapters/            # Speech-to-text engines
│   ├── faster_whisper_adapter.py
│   ├── openai_whisper_adapter.py
│   └── google_speech_adapter.py
├── tts_adapters/            # Text-to-speech engines
│   ├── google_tts_adapter.py
│   ├── kokoro_adapter.py
│   └── openai_tts_adapter.py
├── summarizer/              # Response summarization
│   ├── local_summarizer.py  # Rule-based with JARVIS personality
│   └── llm_summarizer.py    # LLM-based summarization
└── config/                  # Configuration management
```

## Development

```bash
# Clone and install in development mode
git clone https://github.com/lukechi1219/speech-mcp-echo.git
cd speech-mcp-echo
pip install -e .[all]

# Run tests
pytest tests/
```

## License

MIT

## Credits

Adapted from [speech-mcp](https://github.com/lukechi1219/speech-mcp) with multi-CLI support.
