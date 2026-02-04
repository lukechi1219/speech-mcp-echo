# Speech MCP Echo - Future Publish Plan

## Current Status

- **Version**: 0.1.0 (development)
- **Repository**: https://github.com/lukechi1219/speech-mcp-echo
- **License**: MIT

## Pre-Release Checklist

### Documentation
- [x] Update README.md to match actual project structure
- [x] Update CLAUDE.md with complete architecture
- [x] Add Traditional Chinese README (README_zh_TW.md)
- [x] Add CONTRIBUTING.md with contribution guidelines
- [x] Add CHANGELOG.md for version history
- [x] Create GitHub issue templates (bug report, feature request)
- [x] Create GitHub PR template

### Code Quality
- [ ] Add comprehensive unit tests (target: 80% coverage)
- [ ] Add integration tests for STT/TTS adapters
- [x] Set up CI/CD with GitHub Actions
  - [x] Run tests on PR
  - [x] Lint with ruff/black/isort
  - [x] Type check with mypy
  - [x] Build package
  - [x] Multi-OS testing (Ubuntu, macOS, Windows)
  - [x] Multi-Python testing (3.10, 3.11, 3.12)
- [x] Add pre-commit hooks configuration
- [x] Review and clean up unused code
  - Identified unused legacy files: speech_recognition.py, streaming_transcriber.py, state_manager.py (can be removed)

### Package Publishing

#### Phase 1: GitHub Release (v0.1.0)
- [ ] Tag version v0.1.0
- [ ] Create GitHub Release with release notes
- [ ] Test installation from GitHub:
  ```bash
  pip install git+https://github.com/lukechi1219/speech-mcp-echo.git
  ```

#### Phase 2: TestPyPI (v0.2.0)
- [x] Update `pyproject.toml` with complete metadata
  - [x] Verify package name availability on PyPI (✅ "speech-mcp-echo" is available)
  - [x] Add classifiers (Development Status, License, etc.)
  - [x] Add project URLs (Homepage, Documentation, Issues, Changelog)
- [ ] Build distribution:
  ```bash
  python -m build
  ```
- [ ] Upload to TestPyPI:
  ```bash
  twine upload --repository testpypi dist/*
  ```
- [ ] Test installation from TestPyPI:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ speech-mcp-echo
  ```

#### Phase 3: PyPI Release (v1.0.0)
- [ ] Final review of all documentation
- [ ] Ensure all tests pass
- [ ] Upload to PyPI:
  ```bash
  twine upload dist/*
  ```
- [ ] Verify installation:
  ```bash
  pip install speech-mcp-echo
  ```
- [ ] Update README with PyPI badge

### Feature Completion for v1.0.0

#### Must Have
- [x] Unified MCP server for all CLIs
- [x] faster-whisper STT adapter
- [x] Google Cloud TTS adapter
- [x] OpenAI TTS adapter
- [x] JARVIS-style summarizer
- [ ] Robust error handling for all adapters
- [ ] Graceful fallback when services unavailable

#### Nice to Have (Post v1.0.0)
- [ ] Kokoro TTS adapter (local neural TTS)
- [ ] Streaming STT (real-time transcription display)
- [ ] Voice activity detection improvements
- [ ] Custom wake word support
- [ ] Plugin system for custom summarizer personalities

### Marketing & Community

#### Documentation Site
- [ ] Set up GitHub Pages or ReadTheDocs
- [ ] Create quickstart guide with screenshots
- [ ] Add video demo/tutorial
- [ ] API reference documentation

#### Community
- [ ] Submit to MCP community registry
- [ ] Write blog post about the project
- [ ] Create demo video for YouTube
- [ ] Share on relevant forums (Reddit, HN, etc.)

## Version Roadmap

| Version | Target | Focus |
|---------|--------|-------|
| v0.1.0 | Current | Core functionality, documentation |
| v0.2.0 | +2 weeks | Test coverage, CI/CD, TestPyPI |
| v0.3.0 | +4 weeks | Bug fixes, performance improvements |
| v1.0.0 | +6 weeks | Stable release on PyPI |
| v1.1.0 | +8 weeks | Additional TTS engines, streaming STT |

## Dependencies to Monitor

| Package | Current | Notes |
|---------|---------|-------|
| mcp | 1.26.0 | Core protocol - watch for breaking changes |
| faster-whisper | 1.2.1 | STT engine |
| google-cloud-texttospeech | latest | Google TTS |
| openai | latest | OpenAI services |

## Notes

- Priority CLI: **Claude Code** (best voice interaction experience)
- Priority TTS: **Google Cloud TTS** (quality + no heavy deps)
- Priority STT: **faster-whisper** (local, fast, accurate)
- Gemini CLI has slow MCP response times (5+ min), not recommended for voice

---

## Language Migration Analysis

### Current Python Dependency Depth

| Layer | Library | Language | Replaceable? |
|-------|---------|----------|--------------|
| **MCP Protocol** | `mcp` (FastMCP) | Python | ⚠️ TypeScript SDK exists |
| **STT Engine** | `faster-whisper` | Python→C++ (CTranslate2) | ⚠️ whisper.cpp exists |
| **Audio Capture** | `pyaudio` | Python→C (PortAudio) | ✅ PortAudio bindings exist |
| **Audio Processing** | `numpy` | Python→C (BLAS/LAPACK) | ✅ Native arrays in most langs |
| **TTS** | REST APIs | HTTP | ✅ Language agnostic |
| **Config/State** | `json`, `pathlib` | Python stdlib | ✅ Universal |

### Performance Bottlenecks

1. **NOT Python** - The heavy lifting is already in C/C++:
   - Whisper inference: CTranslate2 (C++)
   - Audio capture: PortAudio (C)
   - Numpy operations: BLAS/LAPACK (C/Fortran)

2. **Actual Python overhead** (~5% of total time):
   - MCP message serialization
   - Glue code between components
   - Config file parsing

### Migration Options

#### Option 1: TypeScript/Node.js
| Pros | Cons |
|------|------|
| MCP SDK officially supported | No good local Whisper bindings |
| Easy async/await | Would need cloud STT only |
| npm ecosystem | Audio capture more complex |

**Verdict**: Only viable if willing to use cloud-only STT

#### Option 2: Rust
| Pros | Cons |
|------|------|
| whisper-rs (whisper.cpp bindings) | No official MCP SDK |
| cpal for audio (cross-platform) | Steeper learning curve |
| True performance gains | Would need to implement MCP |
| Single binary distribution | |

**Verdict**: Best for performance, but significant effort

#### Option 3: Go
| Pros | Cons |
|------|------|
| Easy deployment | Poor ML/audio ecosystem |
| Good concurrency | No Whisper bindings |
| Single binary | Would need cloud STT only |

**Verdict**: Not recommended for this use case

### Recommendation

**Stay with Python** because:

1. **Performance is already optimized** - The actual compute (Whisper, audio) runs in C/C++
2. **MCP ecosystem** - Official Python SDK is well-maintained
3. **Rapid iteration** - Voice interface needs tuning, Python enables fast changes
4. **Distribution** - `pip install` is familiar to target users (AI CLI developers)

**If migrating for specific goals:**
- **Single binary distribution** → Rust with whisper-rs
- **Existing TypeScript codebase** → TypeScript with cloud STT
- **Embedded/IoT** → Rust or C++ directly

### Codebase Size After UI Removal

| Metric | Before | After |
|--------|--------|-------|
| Total lines | 8,767 | 4,614 |
| UI code removed | - | 1,877 lines |
| PyQt5 dependency | Yes | No |

The core is now **~4,600 lines** of Python "glue code" orchestrating C/C++ libraries.
