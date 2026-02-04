#!/bin/bash
# Setup script for speech-mcp-echo across multiple AI CLIs
# Supports: Claude Code, Gemini CLI, Codex CLI, Goose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Determine the command to use
if command -v speech-mcp-echo &> /dev/null; then
    MCP_COMMAND="speech-mcp-echo"
elif [ -f "$PROJECT_DIR/.venv/bin/speech-mcp-echo" ]; then
    MCP_COMMAND="$PROJECT_DIR/.venv/bin/speech-mcp-echo"
else
    MCP_COMMAND="python -m speech_mcp_echo"
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          speech-mcp-echo CLI Setup Script                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "MCP Command: ${GREEN}$MCP_COMMAND${NC}"
echo ""

# Function to setup Claude Code
setup_claude_code() {
    echo -e "${YELLOW}Setting up Claude Code...${NC}"

    CONFIG_FILE="$HOME/.claude.json"

    python3 << EOF
import json
import os

config_path = os.path.expanduser("$CONFIG_FILE")
mcp_command = "$MCP_COMMAND"

# Load existing or create new
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
else:
    config = {}

# Add MCP server
if "mcpServers" not in config:
    config["mcpServers"] = {}

# Handle command with args
if " " in mcp_command:
    parts = mcp_command.split()
    config["mcpServers"]["speech-mcp-echo"] = {
        "command": parts[0],
        "args": parts[1:]
    }
else:
    config["mcpServers"]["speech-mcp-echo"] = {
        "command": mcp_command
    }

# Save with backup
if os.path.exists(config_path):
    import shutil
    shutil.copy(config_path, config_path + ".backup")

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✅ Claude Code configured: {config_path}")
EOF

    echo -e "${GREEN}✅ Claude Code setup complete${NC}"
    echo -e "   Restart Claude Code to load the extension"
}

# Function to setup Gemini CLI
setup_gemini_cli() {
    echo -e "${YELLOW}Setting up Gemini CLI...${NC}"
    echo -e "${RED}⚠️  Warning: Gemini CLI has slow MCP processing (5+ min/call)${NC}"
    echo -e "${RED}   Not recommended for real-time voice interactions${NC}"
    echo ""
    read -p "Continue anyway? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Skipped Gemini CLI setup${NC}"
        return
    fi

    CONFIG_DIR="$HOME/.gemini"
    CONFIG_FILE="$CONFIG_DIR/settings.json"

    # Create directory if needed
    mkdir -p "$CONFIG_DIR"

    python3 << EOF
import json
import os

config_path = os.path.expanduser("$CONFIG_FILE")
mcp_command = "$MCP_COMMAND"

# Load existing or create new
if os.path.exists(config_path):
    with open(config_path) as f:
        config = json.load(f)
else:
    config = {}

# Add MCP server
if "mcpServers" not in config:
    config["mcpServers"] = {}

# Handle command with args
if " " in mcp_command:
    parts = mcp_command.split()
    config["mcpServers"]["speech-mcp-echo"] = {
        "command": parts[0],
        "args": parts[1:]
    }
else:
    config["mcpServers"]["speech-mcp-echo"] = {
        "command": mcp_command
    }

# Save with backup
if os.path.exists(config_path):
    import shutil
    shutil.copy(config_path, config_path + ".backup")

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"✅ Gemini CLI configured: {config_path}")
EOF

    echo -e "${GREEN}✅ Gemini CLI setup complete${NC}"
    echo -e "   Restart Gemini CLI to load the extension"
}

# Function to setup Codex CLI
setup_codex_cli() {
    echo -e "${YELLOW}Setting up Codex CLI...${NC}"

    CONFIG_DIR="$HOME/.codex"
    CONFIG_FILE="$CONFIG_DIR/config.toml"

    # Create directory if needed
    mkdir -p "$CONFIG_DIR"

    # Check if file exists and has mcp section
    if [ -f "$CONFIG_FILE" ]; then
        # Backup existing config
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup"

        # Check if [mcp.servers.speech-mcp-echo] already exists
        if grep -q "\[mcp.servers.speech-mcp-echo\]" "$CONFIG_FILE"; then
            echo -e "${YELLOW}   speech-mcp-echo server already configured in $CONFIG_FILE${NC}"
        else
            # Append the MCP server config
            echo "" >> "$CONFIG_FILE"
            echo "[mcp.servers.speech-mcp-echo]" >> "$CONFIG_FILE"
            echo "command = \"$MCP_COMMAND\"" >> "$CONFIG_FILE"
            echo -e "✅ Codex CLI configured: $CONFIG_FILE"
        fi
    else
        # Create new config file
        cat > "$CONFIG_FILE" << TOML
# Codex CLI Configuration

[mcp.servers.speech-mcp-echo]
command = "$MCP_COMMAND"
TOML
        echo -e "✅ Codex CLI configured: $CONFIG_FILE"
    fi

    echo -e "${GREEN}✅ Codex CLI setup complete${NC}"
    echo -e "   Restart Codex CLI to load the extension"
}

# Function to show Goose instructions
setup_goose() {
    echo -e "${YELLOW}Goose CLI Setup Options:${NC}"
    echo ""
    echo -e "  ${BLUE}Option 1: Direct command${NC}"
    echo -e "    goose session --with-extension \"$MCP_COMMAND\""
    echo ""
    echo -e "  ${BLUE}Option 2: Interactive setup${NC}"
    echo -e "    1. Run: goose configure"
    echo -e "    2. Select 'Add Extension'"
    echo -e "    3. Choose 'Command-line Extension'"
    echo -e "    4. Name: speech-mcp-echo"
    echo -e "    5. Command: $MCP_COMMAND"
    echo ""
    echo -e "${GREEN}✅ Goose instructions displayed${NC}"
}

# Function to show current status
show_status() {
    echo -e "${BLUE}Configuration & Voice Compatibility Status:${NC}"
    echo ""

    # Claude Code
    if [ -f "$HOME/.claude.json" ]; then
        if grep -q "speech-mcp-echo" "$HOME/.claude.json" 2>/dev/null; then
            echo -e "  Claude Code:  ${GREEN}✅ Configured${NC}    | Voice: ${GREEN}✅ Excellent${NC}"
        else
            echo -e "  Claude Code:  ${YELLOW}⚠️  Config exists, speech-mcp-echo not added${NC}"
        fi
    else
        echo -e "  Claude Code:  ${RED}❌ Not configured${NC}"
    fi

    # Gemini CLI
    if [ -f "$HOME/.gemini/settings.json" ]; then
        if grep -q "speech-mcp-echo" "$HOME/.gemini/settings.json" 2>/dev/null; then
            echo -e "  Gemini CLI:   ${GREEN}✅ Configured${NC}    | Voice: ${RED}⚠️  Slow (5+ min/call)${NC}"
        else
            echo -e "  Gemini CLI:   ${YELLOW}⚠️  Config exists, speech-mcp-echo not added${NC}"
        fi
    else
        echo -e "  Gemini CLI:   ${RED}❌ Not configured${NC}"
    fi

    # Codex CLI
    if [ -f "$HOME/.codex/config.toml" ]; then
        if grep -q "speech-mcp-echo" "$HOME/.codex/config.toml" 2>/dev/null; then
            echo -e "  Codex CLI:    ${GREEN}✅ Configured${NC}    | Voice: ${YELLOW}🔲 Untested${NC}"
        else
            echo -e "  Codex CLI:    ${YELLOW}⚠️  Config exists, speech-mcp-echo not added${NC}"
        fi
    else
        echo -e "  Codex CLI:    ${RED}❌ Not configured${NC}"
    fi

    # Goose CLI (no config file to check)
    echo -e "  Goose CLI:    ${BLUE}ℹ️  Run with --with-extension${NC}  | Voice: ${GREEN}✅ Good${NC}"

    echo ""
}

# Main menu
show_menu() {
    echo -e "${BLUE}Select CLI to configure:${NC}"
    echo ""
    echo "  1) Claude Code    (~/.claude.json)              ✅ Recommended for voice"
    echo "  2) Gemini CLI     (~/.gemini/settings.json)     ⚠️  Slow for voice (5+ min)"
    echo "  3) Codex CLI      (~/.codex/config.toml)        🔲 Untested"
    echo "  4) Goose CLI      (show instructions)           ✅ Good for voice"
    echo "  5) All CLIs       (configure all)"
    echo "  6) Show status    (check current config)"
    echo "  0) Exit"
    echo ""
}

# Parse command line arguments
if [ $# -gt 0 ]; then
    case "$1" in
        --claude|claude)
            setup_claude_code
            exit 0
            ;;
        --gemini|gemini)
            setup_gemini_cli
            exit 0
            ;;
        --codex|codex)
            setup_codex_cli
            exit 0
            ;;
        --goose|goose)
            setup_goose
            exit 0
            ;;
        --all|all)
            setup_claude_code
            echo ""
            setup_gemini_cli
            echo ""
            setup_codex_cli
            echo ""
            setup_goose
            exit 0
            ;;
        --status|status)
            show_status
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  --claude, claude    Setup Claude Code"
            echo "  --gemini, gemini    Setup Gemini CLI"
            echo "  --codex, codex      Setup Codex CLI"
            echo "  --goose, goose      Show Goose instructions"
            echo "  --all, all          Setup all CLIs"
            echo "  --status, status    Show current configuration status"
            echo "  --help, -h          Show this help"
            echo ""
            echo "Without arguments, runs interactive menu."
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
fi

# Interactive mode
while true; do
    show_menu
    read -p "Enter choice [0-6]: " choice
    echo ""

    case $choice in
        1) setup_claude_code ;;
        2) setup_gemini_cli ;;
        3) setup_codex_cli ;;
        4) setup_goose ;;
        5)
            setup_claude_code
            echo ""
            setup_gemini_cli
            echo ""
            setup_codex_cli
            echo ""
            setup_goose
            ;;
        6) show_status ;;
        0)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
    echo ""
done
