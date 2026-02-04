# Speech MCP Echo - Project Instructions

## Project Overview

Speech MCP Echo is a voice interface for multiple AI CLIs using the MCP (Model Context Protocol).

**Key Features:**
- **Universal MCP support**: Single server works with all MCP-compatible CLIs
- Configurable STT (faster-whisper local, OpenAI/Google cloud)
- Configurable TTS (Google Cloud TTS, OpenAI TTS with 6 voices)
- JARVIS-style response summarizer (English + Chinese)
- PyQt5 UI with audio visualization (coming soon)

## Multi-CLI Support (MCP Protocol)

All target CLIs support MCP natively, so we use a **single MCP server** for all:

| CLI | MCP Support | Voice Compatibility | Config Location |
|-----|-------------|---------------------|-----------------|
| Claude Code | Native | ✅ Excellent | `~/.claude.json` mcpServers |
| Goose CLI | Native | ✅ Good | Extension command |
| Gemini CLI | Native | ⚠️ Slow (5+ min/call) | `~/.gemini/settings.json` |
| Codex CLI | Native | 🔲 Untested | `~/.codex/config.toml` |

**Note:** Gemini CLI performs extensive internal processing before/after MCP tool calls, making it unsuitable for real-time voice interactions. Claude Code and Goose CLI are recommended for voice use.

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

**Prerequisites:**
```bash
# Install uv (fast Python package manager - recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv

# Install PortAudio (for PyAudio)
brew install portaudio  # macOS
# Or: apt-get install portaudio19-dev  # Linux
```

**Setup with uv (recommended - 4x faster than pip):**
```bash
cd speech-mcp-echo
uv venv .venv --python 3.13
source .venv/bin/activate
uv pip install -e ".[recommended]"
```

**Or with pip (slower alternative):**
```bash
cd speech-mcp-echo
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
    "device": "cpu",
    "timeout": 45  // Audio recording timeout in seconds (default: 45)
  },
  "tts": {
    "engine": "google",  // Options: "google", "openai"
    "voice": "cmn-TW-Standard-B",  // Google voice or OpenAI: alloy, echo, fable, onyx, nova, shimmer
    "language": "cmn-TW"
  },
  "summarizer": {
    "enabled": true,
    "personality": "jarvis",
    "language": "en"
  }
}
```

### Audio Recording Timeout

The `stt.timeout` setting controls how long the system waits for audio input before timing out:

- **Default: 45 seconds** - Balances CLI constraints with practical audio capture needs
- **For Codex CLI**: Use 45s or less (Codex has ~60s MCP timeout)
- **For Claude Code**: Can use longer (120s+) if needed
- **Can be overridden per-call** in MCP tools via the `timeout` parameter

**Why timeout is needed:** PyAudio's blocking audio capture has no timeout. Without this, MCP tools would block indefinitely, causing CLI timeouts in environments like Codex.

**Configuration examples:**

```bash
# Via config file
echo '{"stt": {"timeout": 30}}' > ~/.config/speech-mcp-echo/config.json

# Via environment variable
export SPEECH_MCP_ECHO_STT_TIMEOUT=30

# Via MCP tool (runtime)
voice_config(stt_timeout=30)

# Override per-call
start_conversation(timeout=60)
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

## OpenAI TTS Configuration

Set your API key via environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

**Available voices:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

**Models:**
- `tts-1`: Fast, standard quality (default)
- `tts-1-hd`: Higher quality, slower

**Example configuration:**
```bash
# Switch to OpenAI TTS with nova voice
export SPEECH_MCP_TTS_ENGINE=openai
export SPEECH_MCP_TTS_VOICE=nova
```

Or use the MCP tool at runtime:
```python
voice_config(tts_engine="openai", tts_voice="nova")
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

# Test TTS - Google Cloud
python -c "
from speech_mcp_echo.tts_adapters.google_tts_adapter import GoogleCloudTTS
tts = GoogleCloudTTS(language='en-GB')
tts.speak('Hello, this is a test.')
"

# Test TTS - OpenAI
python -c "
from speech_mcp_echo.tts_adapters.openai_tts_adapter import OpenAITTS
tts = OpenAITTS(voice='nova')
tts.speak('Hello from OpenAI TTS.')
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

### Quick Setup (Recommended)

Use the setup script to configure any or all CLIs:

```bash
# Interactive menu
./scripts/setup-cli.sh

# Or configure specific CLI
./scripts/setup-cli.sh --claude   # Claude Code
./scripts/setup-cli.sh --gemini   # Gemini CLI
./scripts/setup-cli.sh --codex    # Codex CLI
./scripts/setup-cli.sh --all      # All CLIs

# Check current status
./scripts/setup-cli.sh --status
```

### Manual Configuration

#### Claude Code
Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "speech-mcp-echo": {
      "command": "speech-mcp-echo"
    }
  }
}
```

**Recommended: Auto-allow speech tools** to avoid confirmation prompts during voice conversations.

Add to `~/.claude/settings.json` under `permissions.allow`:
```json
{
  "permissions": {
    "allow": [
      "mcp__speech-mcp-echo__start_conversation",
      "mcp__speech-mcp-echo__voice_listen",
      "mcp__speech-mcp-echo__voice_speak",
      "mcp__speech-mcp-echo__voice_reply",
      "mcp__speech-mcp-echo__voice_config",
      "mcp__speech-mcp-echo__voice_status"
    ]
  }
}
```

Then restart Claude Code.

#### Gemini CLI
Add to `~/.gemini/settings.json`:
```json
{
  "mcpServers": {
    "speech-mcp-echo": {
      "command": "speech-mcp-echo"
    }
  }
}
```
Then restart Gemini CLI.

#### Codex CLI
Add to `~/.codex/config.toml`:
```toml
[mcp.servers.speech-mcp-echo]
command = "speech-mcp-echo"
```
Then restart Codex CLI.

#### Goose CLI
```bash
goose session --with-extension "speech-mcp-echo"
```

## Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `start_conversation` | Start a voice conversation (use when user says "let's talk") | `timeout` (optional, int) |
| `voice_listen` | Listen for voice input and return transcription | `timeout` (optional, int) |
| `voice_speak` | Speak text using TTS (with optional summarization) | `text` (str), `summarize` (bool) |
| `voice_reply` | Speak text and listen for response (for ongoing conversations) | `text` (str), `wait_for_response` (bool), `timeout` (optional, int) |
| `voice_config` | Configure STT, TTS, and summarizer settings | `stt_engine`, `stt_timeout`, `tts_engine`, `tts_voice`, `tts_language`, `summarizer_enabled`, `summarizer_personality` |
| `voice_status` | Get voice system status and detected CLI | None |

**Timeout Parameter:** All listening tools accept an optional `timeout` parameter (in seconds) to override the configured default (45s). This is useful for CLIs with different MCP timeout constraints.

## Voice Conversation Flow

```
User: "Let's have a voice conversation"
                │
                ▼
AI calls: start_conversation()  ──► Returns user's first voice input
                │
                ▼
AI processes, then calls: voice_reply("response", wait=True)
                │
                ├──► Speaks response
                └──► Returns user's next voice input
                │
                ▼
        [Repeat voice_reply() for continued conversation]
                │
                ▼
AI calls: voice_reply("Goodbye!", wait=False)  ──► Ends conversation
```
