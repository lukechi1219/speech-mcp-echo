# Contributing to Speech MCP Echo

Thank you for your interest in contributing to Speech MCP Echo! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors

## Getting Started

### Prerequisites

- Python 3.10 or higher
- PortAudio for audio capture
- Git for version control

### Development Setup

```bash
# Clone the repository
git clone https://github.com/lukechi1219/speech-mcp-echo.git
cd speech-mcp-echo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Development Workflow

### Branch Strategy

- `main` - Stable, production-ready code
- Feature branches: `feature/your-feature-name`
- Bug fixes: `bugfix/issue-description`
- Documentation: `docs/what-you-changed`

### Making Changes

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   pytest tests/
   ```

4. **Lint your code**
   ```bash
   ruff check src/
   black src/
   ```

5. **Commit your changes**
   - Use clear, descriptive commit messages
   - Follow conventional commit format:
     ```
     type(scope): description

     [optional body]

     [optional footer]
     ```
   - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
   - Example: `feat(tts): add new voice option for Google Cloud TTS`

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Open a Pull Request on GitHub
   - Fill out the PR template
   - Link any related issues

## Coding Standards

### Python Style

- Follow PEP 8
- Use Black for formatting (line length: 100)
- Use Ruff for linting
- Use type hints where appropriate

### Code Organization

```python
# Import order: standard library, third-party, local
import os
import sys

import numpy as np
from mcp.server import Server

from speech_mcp_echo.config import load_config
```

### Documentation

- Docstrings for all public functions/classes
- Use Google-style docstrings:
  ```python
  def function_name(param1: str, param2: int) -> bool:
      """Brief description.

      Longer description if needed.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Description of return value

      Raises:
          ValueError: When param1 is invalid
      """
  ```

### Testing

- Write tests for new functionality
- Aim for 80%+ code coverage
- Use descriptive test names: `test_should_return_error_when_api_key_missing`
- Use pytest fixtures for common setup

## Types of Contributions

### Bug Reports

- Use GitHub Issues
- Include:
  - Clear description of the bug
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment (OS, Python version, etc.)
  - Relevant logs or error messages

### Feature Requests

- Use GitHub Issues with "enhancement" label
- Explain:
  - Use case / problem it solves
  - Proposed solution
  - Alternatives considered

### Code Contributions

We welcome contributions in these areas:

- **New STT/TTS adapters** - Add support for new speech services
- **Bug fixes** - Fix reported issues
- **Performance improvements** - Optimize existing code
- **Documentation** - Improve README, add examples, fix typos
- **Tests** - Increase test coverage

### Areas Needing Help

See issues labeled with:
- `good first issue` - Good for newcomers
- `help wanted` - We'd love community help
- `documentation` - Documentation improvements

## Project Structure

```
speech-mcp-echo/
├── src/speech_mcp_echo/   # Main source code
│   ├── stt_adapters/      # Speech-to-text adapters
│   ├── tts_adapters/      # Text-to-speech adapters
│   ├── summarizer/        # Response summarization
│   └── core/              # Core voice engine
├── tests/                 # Test files
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

## Adding New Adapters

### STT Adapter

```python
from speech_mcp_echo.stt_adapters import BaseSTTAdapter

class MySTTAdapter(BaseSTTAdapter):
    def __init__(self, **kwargs):
        super().__init__()
        # Initialize your adapter

    def listen(self) -> str:
        # Implement audio capture and transcription
        pass

    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

### TTS Adapter

```python
from speech_mcp_echo.tts_adapters import BaseTTSAdapter

class MyTTSAdapter(BaseTTSAdapter):
    def __init__(self, **kwargs):
        super().__init__()
        # Initialize your adapter

    def speak(self, text: str) -> bool:
        # Implement text-to-speech
        pass

    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

## Review Process

1. **Automated Checks** - CI runs tests, linting
2. **Code Review** - Maintainer reviews code
3. **Discussion** - Address feedback, make changes
4. **Approval** - Once approved, will be merged

## Questions?

- Open a GitHub Discussion
- Check existing issues/PRs
- Read the documentation in README.md and CLAUDE.md

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
