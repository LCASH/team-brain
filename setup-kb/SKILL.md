---
name: setup-kb
description: Set up the team knowledge base on the current project — finds or clones the shared repo in ~/Documents/, configures hooks with absolute paths
user_invocable: true
---

# /setup-kb — Team Knowledge Base Setup

Sets up the team knowledge base on the current project. The `claude-memory-compiler` repo lives once in `~/Documents/claude-memory-compiler/` (NOT inside each project). This skill finds or installs it there, then configures the current project's hooks to point at it.

## Default Repo
The shared team knowledge repo is: `https://github.com/LCASH/team-brain.git`

## Usage
- `/setup-kb` — find existing installation or clone, configure hooks on this project
- `/setup-kb <github-repo-url>` — use a different repo URL instead of the default

## Steps to Execute

### Step 1: Find or Install claude-memory-compiler

Search for an existing installation. Check these locations in order:
1. `~/Documents/claude-memory-compiler/`
2. If not found, search: `find ~/Documents -maxdepth 3 -type d -name "claude-memory-compiler" 2>/dev/null | head -1`

**If found:** `cd <path> && git pull` to get latest.

**If not found anywhere:** Clone to `~/Documents/`:
```bash
git clone https://github.com/LCASH/team-brain.git ~/Documents/claude-memory-compiler
```

Store the **absolute path** for use in later steps. For example: `/Users/<username>/Documents/claude-memory-compiler`

### Step 2: Install Dependencies

```bash
cd <absolute-path> && uv sync
```

If `uv` is not installed, tell the user to install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Step 3: Detect Developer Identity

```bash
git config user.name
```

Slugify it (lowercase, hyphens for spaces, strip special chars). If empty, ask the user to set `CLAUDE_KB_USER` or run `git config --global user.name "Their Name"`.

### Step 4: Create Developer Daily Directory

```bash
mkdir -p <absolute-path>/daily/<developer-slug>/
```

### Step 5: Configure Hooks

Create or update `.claude/settings.json` in the **current project root**. All hook commands must use the **absolute path** to `claude-memory-compiler`. Do NOT use relative paths.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run --directory <ABSOLUTE-PATH> python hooks/session-start.py",
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
            "command": "uv run --directory <ABSOLUTE-PATH> python hooks/stop.py",
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
            "command": "uv run --directory <ABSOLUTE-PATH> python hooks/pre-compact.py",
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
            "command": "uv run --directory <ABSOLUTE-PATH> python hooks/session-end.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Replace `<ABSOLUTE-PATH>` with the actual path found/created in Step 1 (e.g., `/Users/lukecashman/Documents/claude-memory-compiler`).

**IMPORTANT — Merging with existing settings:**
1. Read `.claude/settings.json` first if it exists
2. If it has a `hooks` key, add/replace only `SessionStart`, `Stop`, `PreCompact`, and `SessionEnd` — preserve any other hook types (e.g., `PreToolUse`, `PostToolUse`)
3. If it has non-hook keys (e.g., `permissions`, `model`), preserve them
4. If the file doesn't exist, create it with just the hooks above
5. Never overwrite the entire file — always merge

### Step 6: Verify

Run the session-start hook to confirm it works:

```bash
uv run --directory <ABSOLUTE-PATH> python hooks/session-start.py
```

It should output valid JSON with `hookSpecificOutput`. If it fails, diagnose and fix.

### Step 7: Report

Print a summary:

```
Installation: <absolute-path>
Developer:    <name>
Your logs:    <absolute-path>/daily/<name>/
Knowledge:    <absolute-path>/knowledge/
Hooks:        .claude/settings.json (this project)

This project is now connected to the team knowledge base.
```

## How the System Works (for reference)

| Hook | When | What |
|------|------|------|
| SessionStart | Every new conversation | Pulls team updates, injects knowledge base index + team activity |
| Stop | After every Claude response | Checks timer — flushes every 30 min of active conversation |
| PreCompact | Before auto-compaction | Captures context before summarization loses it |
| SessionEnd | Session closes (explicit) | Final capture when you quit/close |

After 6 PM local time, the first developer to finish a session triggers compilation — reads all team members' daily logs and builds shared knowledge articles. A nightly GitHub Action runs as a fallback.

## Key Design: One Installation, Many Projects

`claude-memory-compiler` lives ONCE at `~/Documents/claude-memory-compiler/`. Each project just has hooks in its `.claude/settings.json` pointing to that shared installation via absolute paths. This means:
- No duplicate clones in every project
- All projects feed into the same daily logs and knowledge base
- `git pull` in one place updates everything

## Argument Parsing

- `/setup-kb` → find existing installation in ~/Documents/ or clone there, configure hooks on current project
- `/setup-kb <url>` → use a different repo URL instead of the default
