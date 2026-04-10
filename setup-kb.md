---
name: setup-kb
description: Set up the team knowledge base (claude-memory-compiler) on the current project — clones shared repo, installs deps, configures hooks
user_invocable: true
---

# /setup-kb — Team Knowledge Base Setup

Sets up the claude-memory-compiler on the current project so conversations are automatically captured into daily logs, compiled into a shared knowledge base, and injected into future sessions.

## Default Repo
The shared team knowledge repo is: `https://github.com/LCASH/team-brain.git`

## Usage
- `/setup-kb` — full setup (clone from default repo, install, configure hooks)
- `/setup-kb <github-repo-url>` — use a different repo URL instead of the default

## What This Does

1. Clones the shared knowledge repo into `<project>/claude-memory-compiler/`
2. Installs Python dependencies via `uv sync`
3. Detects developer name from `git config user.name` (or `CLAUDE_KB_USER` env var)
4. Creates the developer's namespaced daily log directory: `daily/<developer-name>/`
5. Configures Claude Code hooks in `<project>/.claude/settings.json`
6. Verifies the session-start hook runs correctly

## Steps to Execute

### Step 1: Clone or Update

Use the default repo URL `https://github.com/LCASH/team-brain.git` unless the user provides a different one as an argument.

- If `claude-memory-compiler/` doesn't exist: `git clone <url> claude-memory-compiler`
- If `claude-memory-compiler/` already exists: `cd claude-memory-compiler && git pull`

### Step 2: Install Dependencies

```bash
cd claude-memory-compiler && uv sync
```

If `uv` is not installed, tell the user to install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Step 3: Detect Developer Identity

```bash
git config user.name
```

Slugify it (lowercase, hyphens for spaces, strip special chars). If empty, ask the user to set `CLAUDE_KB_USER` or run `git config --global user.name "Their Name"`.

### Step 4: Create Developer Daily Directory

```bash
mkdir -p claude-memory-compiler/daily/<developer-slug>/
```

### Step 5: Configure Hooks

Create or update `.claude/settings.json` in the **current project root** (NOT inside claude-memory-compiler). The hooks must point into the claude-memory-compiler subdirectory:

```json
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
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory claude-memory-compiler python hooks/stop.py",
            "timeout": 10
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
```

**IMPORTANT:** If `.claude/settings.json` already exists with other hooks or settings, MERGE the hook configuration — do NOT overwrite the entire file. Read the existing file first, add the four hooks (SessionStart, Stop, PreCompact, SessionEnd), and preserve any existing hooks or settings.

### Step 6: Verify

Run the session-start hook to confirm it works:

```bash
uv run --directory claude-memory-compiler python hooks/session-start.py
```

It should output valid JSON with `hookSpecificOutput`. If it fails, diagnose and fix.

### Step 7: Report

Print a summary:

```
Developer:    <name>
Your logs:    claude-memory-compiler/daily/<name>/
Knowledge:    claude-memory-compiler/knowledge/
Hooks:        .claude/settings.json

Your next Claude Code session in this project will automatically
sync with the team knowledge base.
```

## How the System Works (for reference)

| Hook | When | What |
|------|------|------|
| SessionStart | Every new conversation | Pulls team updates, injects knowledge base index + team activity |
| Stop | After every Claude response | Checks timer — flushes every 30 min of active conversation |
| PreCompact | Before auto-compaction | Captures context before summarization loses it |
| SessionEnd | Session closes (explicit) | Final capture when you quit/close |

After 6 PM local time, the first developer to finish a session triggers compilation — reads all team members' daily logs and builds shared knowledge articles. A nightly GitHub Action runs as a fallback.

## Argument Parsing

- `/setup-kb` → clone from `https://github.com/LCASH/team-brain.git` (or pull if already exists)
- `/setup-kb <url>` → clone from the given URL instead of the default
