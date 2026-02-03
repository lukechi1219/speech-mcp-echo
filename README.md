# Speech MCP Echo

Voice interface for multiple AI CLIs - Claude Code, Gemini CLI, Codex CLI, and MCP-compatible tools.

## Features

- **Multi-CLI Support**: Works with Claude Code, Gemini CLI, Codex CLI, and any MCP-compatible tool
- **Configurable STT**: Local (faster-whisper) or cloud (OpenAI Whisper, Google Speech)
- **Configurable TTS**: Local (pyttsx3) or cloud (Google Cloud TTS, OpenAI TTS)
- **Bilingual Support**: English and Chinese (Traditional/Simplified) text processing
- **JARVIS Summarizer**: Condenses long responses into concise, entertaining summaries
- **PyQt5 UI**: Audio visualization and status display (coming soon)

## Why These Technology Choices?

### STT: faster-whisper (Recommended)

We chose **faster-whisper** as the primary STT engine because:

- **Lightweight**: ~150MB vs ~1.5GB for OpenAI's original whisper
- **Fast**: 4x faster than original whisper using CTranslate2 optimization
- **Offline**: Works completely offline, no API costs
- **Accurate**: Same accuracy as OpenAI Whisper (it uses the same models)
- **CPU-friendly**: Runs well on CPU with int8 quantization

### TTS: Google Cloud TTS (Recommended)

We chose **Google Cloud TTS** as the primary TTS engine because:

- **No heavy dependencies**: Unlike Kokoro which requires PyTorch (~2GB), Google Cloud TTS uses a simple REST API
- **High quality**: Neural voices with natural prosody
- **Multilingual**: Excellent support for English, Chinese (Traditional/Simplified), and 40+ languages
- **Flexible auth**: Multiple authentication methods (see below)
- **Cost-effective**: Free tier includes 4 million characters/month
- **Cross-platform**: Works on macOS, Linux, and Windows

#### Google Cloud TTS Authentication Options

Choose the method that works best for your setup:

**Option A: gcloud CLI (Recommended for developers)**
```bash
# Install gcloud CLI
brew install google-cloud-sdk  # macOS
# or: https://cloud.google.com/sdk/docs/install

# Login and configure
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**Option B: Service Account (Recommended for servers/production)**
```bash
# 1. Create service account in Google Cloud Console
#    - Go to IAM & Admin > Service Accounts
#    - Create account with "Cloud Text-to-Speech API User" role
#    - Download JSON key file

# 2. Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# 3. Optionally set project ID (if not in key file)
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

**Option C: Python Client Library**
```bash
# Install the library
pip install google-cloud-texttospeech

# Then use Option A or B for authentication
# The library will auto-detect credentials
```

The adapter automatically tries these methods in order and uses the first one that works.

#### Why Not Kokoro?

Kokoro is an excellent local TTS engine, but it requires:
- PyTorch (~2GB download)
- CUDA for optimal performance
- Additional language models (misaki)

For most users, Google Cloud TTS provides better quality with simpler setup. Kokoro remains available as an optional local alternative for users who prefer fully offline operation.

## Installation

### Prerequisites

```bash
# macOS - Install PortAudio for audio capture
brew install portaudio

# For Google Cloud TTS - Install and configure gcloud CLI
brew install google-cloud-sdk
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Recommended Installation

We recommend installing **without** Kokoro/PyTorch to keep the installation lightweight:

```bash
# Clone the repository
git clone https://github.com/lukechi1219/speech-mcp-echo.git
cd speech-mcp-echo

# Install core dependencies (recommended)
pip install -e .

# Or install specific features
pip install -e ".[local-stt]"  # Add faster-whisper
pip install -e ".[cloud]"      # Add cloud API clients
pip install -e ".[ui]"         # Add PyQt5 UI
```

### Manual Installation (Core packages only)

```bash
# Essential packages
pip install pyaudio numpy soundfile psutil

# STT: faster-whisper (recommended)
pip install faster-whisper numba

# MCP support
pip install "mcp[cli]>=1.2.0" "pydantic>=2.7.2,<3.0.0"

# Optional: PyQt5 UI
pip install PyQt5

# Optional: Cloud API clients (if using OpenAI services)
pip install openai
```

### Optional: Local TTS with Kokoro

Only install if you need fully offline TTS:

```bash
# Warning: This downloads ~2GB of PyTorch
pip install torch kokoro pyttsx3

# Language support
pip install "misaki[en]"  # English
pip install "misaki[zh]"  # Chinese
pip install "misaki[ja]"  # Japanese
```

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
    "device": "cpu",
    "compute_type": "int8"
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

### Supported Languages

| Language | STT (faster-whisper) | TTS (Google Cloud) |
|----------|---------------------|-------------------|
| English | ✅ | ✅ en-US, en-GB |
| Chinese (Traditional) | ✅ | ✅ cmn-TW |
| Chinese (Simplified) | ✅ | ✅ cmn-CN |
| Japanese | ✅ | ✅ ja-JP |

### Environment Variables

API keys are read from environment variables:

- `OPENAI_API_KEY` - For OpenAI Whisper STT and TTS
- `GOOGLE_APPLICATION_CREDENTIALS` - For Google Cloud services (optional if using gcloud CLI)
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
pip install -e ".[dev]"

# Run tests
pytest tests/
```

## License

MIT

## Credits

Adapted from [speech-mcp](https://github.com/lukechi1219/speech-mcp) with multi-CLI support.
