# Cleanup Notes

## Unused Legacy Code (Can be Removed)

The following files are **not imported anywhere** in the codebase and appear to be legacy code that can be safely removed:

### 1. `src/speech_mcp_echo/speech_recognition.py` (138 lines)
- Legacy speech recognition module
- Not imported by any other module
- Functionality replaced by STT adapters

### 2. `src/speech_mcp_echo/streaming_transcriber.py` (219 lines)
- Real-time streaming transcription module
- Not imported by any other module
- Functionality may be reintroduced later if needed

### 3. `src/speech_mcp_echo/state_manager.py` (143 lines)
- Application state management
- Not imported by any other module
- State is now managed directly in the MCP server

**Total removable code**: ~500 lines

## Recommendation

These files can be removed in a future commit to simplify the codebase. If their functionality is needed later, they can be recovered from git history.

```bash
# To remove (after verification):
git rm src/speech_mcp_echo/speech_recognition.py
git rm src/speech_mcp_echo/streaming_transcriber.py
git rm src/speech_mcp_echo/state_manager.py
git commit -m "chore: Remove unused legacy code"
```

## PyPI Package Name

✅ **"speech-mcp-echo" is available on PyPI**

Checked on 2026-02-04. No conflicts found.

Related packages on PyPI:
- `speech-mcp` - Different project (original)
- `voice-mcp` - Different focus
- `echo-mcp-server-for-testing` - Testing tool

Sources:
- [speech-mcp on PyPI](https://pypi.org/project/speech-mcp/)
- [echo-mcp-server-for-testing on PyPI](https://pypi.org/project/echo-mcp-server-for-testing/)
- [voice-mcp on PyPI](https://pypi.org/project/voice-mcp/)
