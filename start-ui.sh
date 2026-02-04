#!/usr/bin/env bash
# Speech MCP Echo - UI Launcher
# Quick script to start the PyQt5 UI

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Speech MCP Echo - Starting UI...${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}Error: Virtual environment not found.${NC}"
    echo "Please run: uv venv .venv --python 3.13 && source .venv/bin/activate && uv pip install -e '.[recommended]'"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if package is installed
if ! python -c "import speech_mcp_echo" 2>/dev/null; then
    echo -e "${RED}Error: speech-mcp-echo not installed.${NC}"
    echo "Please run: uv pip install -e '.[recommended]'"
    exit 1
fi

# Launch the UI
echo -e "${GREEN}Launching PyQt5 UI...${NC}"
echo ""
python -m speech_mcp_echo.ui.pyqt
