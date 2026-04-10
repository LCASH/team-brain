#!/bin/bash
# setup.sh — Onboard a new team member to the shared knowledge base.
#
# Usage:
#   ./setup.sh <shared-repo-url> <project-dir>
#
# Example:
#   ./setup.sh git@github.com:myorg/project-knowledge.git ~/Documents/my-project
#
# What it does:
#   1. Clones the shared knowledge repo into <project-dir>/claude-memory-compiler/
#   2. Installs Python dependencies via uv
#   3. Creates your developer-namespaced daily log directory
#   4. Configures Claude Code hooks in <project-dir>/.claude/settings.json

set -euo pipefail

REPO_URL="${1:?Usage: ./setup.sh <shared-repo-url> <project-dir>}"
PROJECT_DIR="${2:?Usage: ./setup.sh <shared-repo-url> <project-dir>}"

KB_DIR="$PROJECT_DIR/claude-memory-compiler"

# ── Clone or update the shared repo ──────────────────────────────────
if [ -d "$KB_DIR/.git" ]; then
    echo "Shared repo already exists at $KB_DIR, pulling latest..."
    cd "$KB_DIR" && git pull
else
    echo "Cloning shared knowledge repo..."
    git clone "$REPO_URL" "$KB_DIR"
fi

# ── Install dependencies ─────────────────────────────────────────────
echo "Installing Python dependencies..."
cd "$KB_DIR" && uv sync

# ── Detect developer name ────────────────────────────────────────────
DEV_NAME=$(git config user.name 2>/dev/null | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
if [ -z "$DEV_NAME" ]; then
    echo "Could not detect developer name from git config."
    echo "Set it with: export CLAUDE_KB_USER=your-name"
    echo "Or run: git config --global user.name 'Your Name'"
    exit 1
fi
echo "Developer identity: $DEV_NAME"

# ── Create developer daily log directory ─────────────────────────────
mkdir -p "$KB_DIR/daily/$DEV_NAME"
echo "Created daily log directory: daily/$DEV_NAME/"

# ── Configure Claude Code hooks ──────────────────────────────────────
CLAUDE_DIR="$PROJECT_DIR/.claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

mkdir -p "$CLAUDE_DIR"

if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "WARNING: $SETTINGS_FILE already exists."
    echo "Please manually merge the hook configuration below:"
    echo ""
fi

cat > "$SETTINGS_FILE" << 'SETTINGS_EOF'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory claude-memory-compiler python hooks/session-start.py",
            "timeout": 15
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory claude-memory-compiler python hooks/pre-compact.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory claude-memory-compiler python hooks/session-end.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
SETTINGS_EOF

echo "Configured Claude Code hooks in $SETTINGS_FILE"

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "  Developer:    $DEV_NAME"
echo "  Knowledge:    $KB_DIR/knowledge/"
echo "  Your logs:    $KB_DIR/daily/$DEV_NAME/"
echo "  Hooks:        $SETTINGS_FILE"
echo ""
echo "  Your next Claude Code session in $PROJECT_DIR"
echo "  will automatically sync with the team knowledge base."
echo ""
