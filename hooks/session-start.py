"""
SessionStart hook - injects team knowledge base context into every conversation.

Syncs with the shared repo (pull team updates, push pending local logs),
then injects the knowledge base index, your recent activity, and a summary
of what your teammates have been working on.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paths relative to project root
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
KNOWLEDGE_DIR = ROOT / "knowledge"
DAILY_DIR = ROOT / "daily"
INDEX_FILE = KNOWLEDGE_DIR / "index.md"

# Import config for developer identity
sys.path.insert(0, str(SCRIPTS_DIR))
from config import DEVELOPER, DEVELOPER_DAILY_DIR

MAX_CONTEXT_CHARS = 20_000
MAX_LOG_LINES = 30
MAX_TEAM_CHARS_PER_DEV = 500


def sync_with_team() -> None:
    """Pull team updates, push any pending local daily logs."""
    try:
        from sync import sync_before_session
        sync_before_session()
    except Exception:
        pass  # sync failure shouldn't block session start


def get_recent_log(daily_dir: Path) -> str:
    """Read the most recent daily log from a given directory (today or yesterday)."""
    today = datetime.now(timezone.utc).astimezone()

    for offset in range(2):
        date = today - timedelta(days=offset)
        log_path = daily_dir / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8").splitlines()
            recent = lines[-MAX_LOG_LINES:] if len(lines) > MAX_LOG_LINES else lines
            return "\n".join(recent)

    return "(no recent activity)"


def get_team_recent_activity() -> str:
    """Summarize what other team members did recently."""
    if not DAILY_DIR.exists():
        return "(no team activity)"

    lines = []
    for dev_dir in sorted(DAILY_DIR.iterdir()):
        if not dev_dir.is_dir() or dev_dir.name == DEVELOPER:
            continue

        # Find most recent log
        logs = sorted(dev_dir.glob("*.md"), reverse=True)
        if not logs:
            continue

        content = logs[0].read_text(encoding="utf-8")
        # Trim to keep context small
        trimmed = content[:MAX_TEAM_CHARS_PER_DEV]
        if len(content) > MAX_TEAM_CHARS_PER_DEV:
            trimmed += "\n...(truncated)"

        lines.append(f"### {dev_dir.name} ({logs[0].stem})")
        lines.append(trimmed)

    return "\n\n".join(lines) if lines else "(no team activity)"


def build_context() -> str:
    """Assemble the context to inject into the conversation."""
    parts = []

    # Today's date + developer identity
    today = datetime.now(timezone.utc).astimezone()
    parts.append(f"## Today\n{today.strftime('%A, %B %d, %Y')}\n\n**Developer:** {DEVELOPER}")

    # Knowledge base index (compiled from ALL team members)
    if INDEX_FILE.exists():
        index_content = INDEX_FILE.read_text(encoding="utf-8")
        parts.append(f"## Knowledge Base Index\n\n{index_content}")
    else:
        parts.append("## Knowledge Base Index\n\n(empty - no articles compiled yet)")

    # Your recent daily log
    recent_log = get_recent_log(DEVELOPER_DAILY_DIR)
    parts.append(f"## Your Recent Activity\n\n{recent_log}")

    # Team recent activity
    team_activity = get_team_recent_activity()
    parts.append(f"## Team Recent Activity\n\n{team_activity}")

    context = "\n\n---\n\n".join(parts)

    # Truncate if too long
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

    return context


def main():
    # Sync with shared repo before building context
    sync_with_team()

    context = build_context()

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
