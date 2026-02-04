# Full Voice Flow Explained

*A guide for junior engineers to understand how speech-mcp-echo works.*

## The Big Picture: What Are We Building?

Think of this like a **translator between your voice and an AI assistant**:

```
┌─────────┐                              ┌─────────┐
│   YOU   │  ←── voice conversation ───→ │   AI    │
│ (human) │                              │  (CLI)  │
└─────────┘                              └─────────┘
```

But computers don't understand voice directly, so we need components to translate.

---

## The 4 Main Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    speech-mcp-echo                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │     STT     │   │ Summarizer  │   │     TTS     │           │
│  │  (Speech    │   │  (Makes     │   │  (Text      │           │
│  │   to Text)  │   │   it short) │   │   to Speech)│           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│                                                                 │
│  ┌─────────────────────────────────────────────────┐           │
│  │              MCP Server (server.py)              │           │
│  │  Connects everything to AI CLIs                  │           │
│  └─────────────────────────────────────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### What Each Component Does

| Component | Job | Example |
|-----------|-----|---------|
| **STT** (Speech-to-Text) | Listens to your voice → converts to text | "What's the weather?" → `"What's the weather?"` |
| **Summarizer** | Makes long AI responses shorter | 500 words → 2 sentences |
| **TTS** (Text-to-Speech) | Converts text → speaks it aloud | `"It's sunny"` → 🔊 "It's sunny" |
| **MCP Server** | Connects to AI CLIs (Claude, Gemini, etc.) | Exposes tools like `voice_listen` |

---

## Full Voice Flow: Step by Step

```
        YOU                                              AI CLI
         │                                                 │
         │  1. SPEAK                                       │
         ▼                                                 │
    ┌─────────┐                                           │
    │   🎤    │  "List files in src"                      │
    │   Mic   │                                           │
    └────┬────┘                                           │
         │                                                 │
         ▼  2. STT (Speech-to-Text)                       │
    ┌─────────────────────┐                               │
    │   faster-whisper    │                               │
    │   ─────────────────  │                               │
    │   Audio waveform    │                               │
    │   → "List files     │                               │
    │      in src"        │                               │
    └──────────┬──────────┘                               │
               │                                           │
               │  3. SEND TEXT TO AI                       │
               └──────────────────────────────────────────►│
                                                           │
                                          4. AI PROCESSES  │
                                          ┌────────────────┤
                                          │ Claude Code    │
                                          │ reads files,   │
                                          │ generates      │
                                          │ long response  │
                                          └────────────────┤
               ◄───────────────────────────────────────────┘
               │  5. RECEIVE LONG RESPONSE
               │  "I found 15 files: __init__.py contains
               │   the main entry point which imports from
               │   server.py that defines... [500 words]"
               ▼
    ┌─────────────────────┐
    │     Summarizer      │  6. SUMMARIZE (Optional)
    │   ─────────────────  │
    │   JARVIS personality │
    │   "Right then, boss. │
    │    Found 15 Python   │
    │    files in src."    │
    └──────────┬──────────┘
               │
               ▼  7. TTS (Text-to-Speech)
    ┌─────────────────────┐
    │   Google Cloud TTS  │
    │   ─────────────────  │
    │   Text → Audio      │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────┐
    │   🔊    │  8. YOU HEAR THE RESPONSE
    │ Speaker │
    └─────────┘
         │
         ▼
        YOU
```

---

## Simplified Flow Diagram

```
    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │   🎤 Voice In                            🔊 Voice Out  │
    │       │                                       ▲        │
    │       ▼                                       │        │
    │   ┌───────┐    ┌────────┐    ┌───────┐   ┌───────┐   │
    │   │  STT  │───►│   AI   │───►│ SUMM  │──►│  TTS  │   │
    │   └───────┘    └────────┘    └───────┘   └───────┘   │
    │                                                        │
    │   "hello"  →   process   →   shorten  →   speak      │
    │                                                        │
    └────────────────────────────────────────────────────────┘
```

---

## How the Code Maps to This Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     server.py                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  @mcp.tool()                                          │ │
│  │  def voice_listen():     ←── Calls STT               │ │
│  │      return engine.listen()                           │ │
│  │                                                       │ │
│  │  @mcp.tool()                                          │ │
│  │  def voice_speak(text):  ←── Calls Summarizer + TTS  │ │
│  │      return engine.speak(text)                        │ │
│  │                                                       │ │
│  │  @mcp.tool()                                          │ │
│  │  def voice_reply(text):  ←── Speak, then Listen      │ │
│  │      engine.speak(text)                               │ │
│  │      return engine.listen()                           │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   VoiceEngine                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ stt_engine  │  │ summarizer  │  │ tts_engine  │        │
│  │ (lazy load) │  │ (lazy load) │  │ (lazy load) │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┘
          │                │                │
          ▼                ▼                ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │ faster-   │   │  local_   │   │  google_  │
    │ whisper   │   │summarizer │   │tts_adapter│
    └───────────┘   └───────────┘   └───────────┘
```

---

## Real Example Walkthrough

Let's trace what happens when you say **"What files are in src?"**:

| Step | Component | Input | Output |
|------|-----------|-------|--------|
| 1 | Microphone | Sound waves | Audio data (bytes) |
| 2 | STT (faster-whisper) | Audio data | `"What files are in src?"` |
| 3 | MCP Server | Text | Sends to Claude Code |
| 4 | Claude Code | Question | Long answer (200 words) |
| 5 | Summarizer | 200 words | `"Found 15 Python files, boss."` |
| 6 | TTS (Google) | Short text | Audio data |
| 7 | Speaker | Audio data | Sound waves 🔊 |

---

## Why Do We Need the Summarizer?

```
Without Summarizer:                    With Summarizer:
─────────────────────                  ─────────────────────

AI says: "I found the                  AI says: "Found 15
following files in the                 Python files in src,
src directory: First,                  boss. Mostly adapters
there's __init__.py                    and core modules."
which serves as the main
entry point for the                    ✓ 3 seconds to speak
package. Then we have                  ✓ Easy to understand
server.py which contains               ✓ Conversational
the FastMCP server
definition with all the
MCP tools registered at
module level..."

✗ 45 seconds to speak
✗ Hard to follow
✗ Boring to listen to
```

---

## Key Takeaway for Junior Engineers

The voice flow is like a **pipeline**:

```
Sound → Text → AI → Text → Sound
        ↑              ↑
       STT            TTS
```

Each component has ONE job:
- **STT**: Sound → Text
- **AI**: Process the question
- **Summarizer**: Long text → Short text
- **TTS**: Text → Sound

This separation makes the code **modular** - you can swap out any component (use OpenAI instead of Google TTS) without changing the others.

---

## MCP Tools Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `start_conversation()` | Begin voice mode | User says "let's talk using voice" |
| `voice_listen()` | Listen for speech | Need voice input without speaking first |
| `voice_speak(text)` | Speak text | Need to say something without listening |
| `voice_reply(text, wait=True)` | Speak then listen | During ongoing voice conversations |
| `voice_config(...)` | Change settings | User wants to adjust voice/language |
| `voice_status()` | Check system | Debugging or status check |

---

## File Locations

| Component | File Path |
|-----------|-----------|
| MCP Server | `src/speech_mcp_echo/server.py` |
| VoiceEngine | `src/speech_mcp_echo/core/voice_engine.py` |
| STT (faster-whisper) | `src/speech_mcp_echo/stt_adapters/faster_whisper_adapter.py` |
| TTS (Google Cloud) | `src/speech_mcp_echo/tts_adapters/google_tts_adapter.py` |
| Summarizer | `src/speech_mcp_echo/summarizer/local_summarizer.py` |
| Configuration | `src/speech_mcp_echo/config/` |
