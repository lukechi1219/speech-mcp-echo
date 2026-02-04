# Speech MCP Echo - Project Instructions

## Project Overview

Speech MCP Echo is a voice interface for multiple AI CLIs using the MCP (Model Context Protocol).

**Key Features:**
- **Universal MCP support**: Single server works with all MCP-compatible CLIs
- Configurable STT (faster-whisper local, OpenAI/Google cloud)
- Configurable TTS (Google Cloud TTS primary, pyttsx3 fallback)
- JARVIS-style response summarizer (English + Chinese)
- PyQt5 UI with audio visualization (coming soon)

## Multi-CLI Support (MCP Protocol)

All target CLIs support MCP natively, so we use a **single MCP server** for all:

| CLI | MCP Support | Config Location |
|-----|-------------|-----------------|
| Claude Code | Native | `~/.claude.json` mcpServers |
| Gemini CLI | Native | `~/.gemini/settings.json` |
| Codex CLI | Native | `~/.codex/config.toml` |
| Goose CLI | Native | Extension command |

No adapter pattern needed - the same `server.py` serves all CLIs.

## Development Environment

### Virtual Environment
```bash
cd speech-mcp-echo
source .venv/bin/activate
```

### Current Versions (2026-02-04)
| Package | Version |
|---------|---------|
| Python | 3.13 |
| speech-mcp-echo | 0.1.0 (editable) |
| faster-whisper | 1.2.1 |
| mcp | 1.26.0 |
| PyQt5 | 5.15.11 |
| pyttsx3 | 2.99 |
| PyAudio | 0.2.14 |

### Installation
```bash
# Prerequisites
brew install portaudio

# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[recommended]"
```

## Architecture

```
src/speech_mcp_echo/
├── __init__.py              # Main entry point
├── __main__.py              # Module execution
├── server.py                # Unified MCP server with all tools
├── core/                    # Protocol-agnostic core
│   └── voice_engine.py      # STT, TTS, summarization
├── stt_adapters/            # Speech-to-text engines
│   ├── faster_whisper_adapter.py  # Local (recommended)
│   ├── openai_whisper_adapter.py  # Cloud
│   └── google_speech_adapter.py   # Cloud
├── tts_adapters/            # Text-to-speech engines
│   └── google_tts_adapter.py      # Cloud (recommended)
├── summarizer/              # Response summarization
│   ├── local_summarizer.py  # Rule-based with JARVIS personality
│   └── llm_summarizer.py    # LLM-based (placeholder)
├── config/                  # Configuration management
├── utils/                   # Logging utilities
└── ui/                      # PyQt5 UI (coming soon)
```

## Full Voice Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         FULL VOICE FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. LISTEN (STT)                                                │
│     User speaks → Microphone → Audio capture → faster-whisper   │
│     → Transcribed text                                          │
│                                                                 │
│  2. PROCESS (CLI)                                               │
│     Transcribed text → Claude Code / Gemini / Codex / Goose    │
│     → AI response (potentially long)                            │
│                                                                 │
│  3. SUMMARIZE (Optional)                                        │
│     Long response → JARVIS Summarizer → Concise summary         │
│     (with personality: "Done and dusted, boss...")              │
│                                                                 │
│  4. SPEAK (TTS)                                                 │
│     Summary/Response → Google Cloud TTS → Audio playback        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Example Flow

1. **User says**: "What files are in the src directory?"
2. **STT transcribes**: `"What files are in the src directory?"`
3. **Claude Code processes**: Lists files, returns detailed output
4. **Summarizer condenses**: `"Right then, boss. Found 12 Python files in src, mainly adapters and core modules."`
5. **TTS speaks**: Plays the summary aloud

## Key Patterns

### TTS Adapter Pattern
All TTS engines implement `BaseTTSAdapter`:
```python
class BaseTTSAdapter:
    def speak(self, text: str) -> bool: ...
    def save_to_file(self, text: str, path: str) -> bool: ...
    def get_available_voices(self) -> list[str]: ...
    @property
    def is_initialized(self) -> bool: ...
```

### STT Adapter Pattern
All STT engines implement `BaseSTTAdapter`:
```python
class BaseSTTAdapter:
    def listen(self) -> str: ...
    def transcribe(self, audio_path: str) -> str: ...
    def get_available_models(self) -> list[str]: ...
    @property
    def is_initialized(self) -> bool: ...
```

## Configuration

Config file: `~/.config/speech-mcp-echo/config.json`

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

## Google Cloud TTS Authentication

The adapter supports three methods (auto-detected in order):

1. **gcloud CLI** (recommended for developers)
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Service Account** (for servers)
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   ```

3. **Client Library**
   ```bash
   pip install google-cloud-texttospeech
   ```

## Testing

```bash
# Activate venv first
source .venv/bin/activate

# Full voice flow test (recommended)
python tests/test_full_voice_flow.py --skip-stt --lang en  # English, no mic
python tests/test_full_voice_flow.py --skip-stt --lang zh  # Chinese, no mic
python tests/test_full_voice_flow.py --lang en             # With microphone

# Individual component tests:

# Test TTS only
python -c "
from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS
tts = GoogleCloudTTS(language='en-GB')
tts.speak('Hello, this is a test.')
"

# Test STT only (requires microphone)
python -c "
from speech_mcp_echo.stt_adapters.faster_whisper_adapter import FasterWhisperSTT
stt = FasterWhisperSTT()
print('Listening...')
text = stt.listen()
print(f'You said: {text}')
"

# Test summarizer only
python -c "
from speech_mcp_echo.summarizer.local_summarizer import LocalSummarizer
s = LocalSummarizer(personality='jarvis', language='en')
print(s.summarize('Successfully created 5 files in the src directory.'))
"
```

## CLI Integration

### Claude Code
Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "speech": {
      "command": "speech-mcp-echo"
    }
  }
}
```

### Gemini CLI
Add to `~/.gemini/settings.json`:
```json
{
  "mcpServers": {
    "speech": {
      "command": "speech-mcp-echo"
    }
  }
}
```

### Codex CLI
Add to `~/.codex/config.toml`:
```toml
[mcp.servers.speech]
command = "speech-mcp-echo"
```

### Goose CLI
```bash
goose session --with-extension "speech-mcp-echo"
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `voice_listen` | Listen for voice input and return transcription |
| `voice_speak` | Speak text using TTS (with optional summarization) |
| `voice_reply` | Speak text and optionally wait for voice response |
| `voice_config` | Configure STT, TTS, and summarizer settings |
| `voice_status` | Get voice system status and detected CLI |
