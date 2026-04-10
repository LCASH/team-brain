"""
Memory flush agent - extracts important knowledge from conversation context.

Spawned by session-end.py or pre-compact.py as a background process. Reads
pre-extracted conversation context from a .md file, uses the Claude Agent SDK
to decide what's worth saving, and appends the result to today's daily log.

Usage:
    uv run python flush.py <context_file.md> <session_id>
"""

from __future__ import annotations

# Recursion prevention: set this BEFORE any imports that might trigger Claude
import os
os.environ["CLAUDE_INVOKED_BY"] = "memory_flush"

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
STATE_FILE = SCRIPTS_DIR / "last-flush.json"
LOG_FILE = SCRIPTS_DIR / "flush.log"

# Import after setting ROOT so config can resolve paths
sys.path.insert(0, str(SCRIPTS_DIR))
from config import COMPILE_LOCK_FILE, DEVELOPER, DEVELOPER_DAILY_DIR

# Set up file-based logging so we can verify the background process ran.
# The parent process sends stdout/stderr to DEVNULL (to avoid the inherited
# file handle bug on Windows), so this is our only observability channel.
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_flush_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_flush_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def append_to_daily_log(content: str, section: str = "Session") -> Path:
    """Append content to today's daily log (developer-namespaced)."""
    today = datetime.now(timezone.utc).astimezone()
    log_path = DEVELOPER_DAILY_DIR / f"{today.strftime('%Y-%m-%d')}.md"

    if not log_path.exists():
        DEVELOPER_DAILY_DIR.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            f"# Daily Log: {today.strftime('%Y-%m-%d')} ({DEVELOPER})\n\n## Sessions\n\n## Memory Maintenance\n\n",
            encoding="utf-8",
        )

    time_str = today.strftime("%H:%M")
    entry = f"### {section} ({time_str})\n\n{content}\n\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return log_path


async def run_flush(context: str) -> str:
    """Use Claude Agent SDK to extract important knowledge from conversation context."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    prompt = f"""Review the conversation context below and respond with a concise summary
of important items that should be preserved in the daily log.
Do NOT use any tools — just return plain text.

Format your response as a structured daily log entry with these sections:

**Context:** [One line about what the user was working on]

**Key Exchanges:**
- [Important Q&A or discussions]

**Decisions Made:**
- [Any decisions with rationale]

**Lessons Learned:**
- [Gotchas, patterns, or insights discovered]

**Action Items:**
- [Follow-ups or TODOs mentioned]

Skip anything that is:
- Routine tool calls or file reads
- Content that's trivial or obvious
- Trivial back-and-forth or clarification exchanges

Only include sections that have actual content. If nothing is worth saving,
respond with exactly: FLUSH_OK

## Conversation Context

{context}"""

    response = ""

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(ROOT),
                allowed_tools=[],
                max_turns=2,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response += block.text
            elif isinstance(message, ResultMessage):
                pass
    except Exception as e:
        import traceback
        logging.error("Agent SDK error: %s\n%s", e, traceback.format_exc())
        response = f"FLUSH_ERROR: {type(e).__name__}: {e}"

    return response


COMPILE_AFTER_HOUR = 18  # 6 PM local time


def maybe_trigger_compilation() -> None:
    """If it's past the compile hour and there are uncompiled team logs, compile.

    Uses a lock file to prevent concurrent compilation across team members.
    Syncs with the shared repo before and after compilation.
    """
    import subprocess as _sp
    from hashlib import sha256

    now = datetime.now(timezone.utc).astimezone()
    if now.hour < COMPILE_AFTER_HOUR:
        return

    compile_script = SCRIPTS_DIR / "compile.py"
    if not compile_script.exists():
        return

    # Sync: push our daily logs, pull team's logs + latest state
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from sync import git_pull, git_push_with_retry
        git_push_with_retry(
            files=[f"daily/{DEVELOPER}/"],
            message=f"daily/{DEVELOPER}: pre-compile sync",
        )
        git_pull()
    except Exception as e:
        logging.warning("Pre-compile sync failed (continuing anyway): %s", e)

    # Check if there are any uncompiled logs across all developers
    compile_state_file = SCRIPTS_DIR / "state.json"
    ingested: dict = {}
    if compile_state_file.exists():
        try:
            compile_state = json.loads(compile_state_file.read_text(encoding="utf-8"))
            ingested = compile_state.get("ingested", {})
        except (json.JSONDecodeError, OSError):
            pass

    # Scan all developer daily dirs for uncompiled logs
    from pathlib import Path as _Path
    daily_dir = ROOT / "daily"
    has_uncompiled = False
    if daily_dir.exists():
        for dev_dir in daily_dir.iterdir():
            if not dev_dir.is_dir():
                continue
            for log_file in dev_dir.glob("*.md"):
                rel_key = f"{dev_dir.name}/{log_file.name}"
                prev = ingested.get(rel_key, {})
                if not prev:
                    has_uncompiled = True
                    break
                current_hash = sha256(log_file.read_bytes()).hexdigest()[:16]
                if prev.get("hash") != current_hash:
                    has_uncompiled = True
                    break
            if has_uncompiled:
                break

    if not has_uncompiled:
        return

    # Compile lock: check if someone else is already compiling
    import time as _time
    if COMPILE_LOCK_FILE.exists():
        try:
            lock_age = _time.time() - COMPILE_LOCK_FILE.stat().st_mtime
            if lock_age < 600:  # 10 min — someone else is compiling
                logging.info("Compile lock held (age %.0fs), skipping", lock_age)
                return
            logging.info("Stale compile lock (age %.0fs), claiming", lock_age)
        except OSError:
            pass

    # Claim the lock and push it
    COMPILE_LOCK_FILE.write_text(
        f"{DEVELOPER} {now.isoformat()}", encoding="utf-8"
    )
    try:
        git_push_with_retry(
            files=[str(COMPILE_LOCK_FILE)],
            message=f"compile: lock claimed by {DEVELOPER}",
        )
    except Exception:
        pass  # lock push failed, but we'll try compiling anyway

    logging.info("End-of-day compilation triggered (after %d:00)", COMPILE_AFTER_HOUR)

    # Run compilation as a background process
    cmd = ["uv", "run", "--directory", str(ROOT), "python", str(compile_script)]

    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = _sp.CREATE_NEW_PROCESS_GROUP | _sp.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True

    try:
        log_handle = open(str(SCRIPTS_DIR / "compile.log"), "a")
        _sp.Popen(cmd, stdout=log_handle, stderr=_sp.STDOUT, cwd=str(ROOT), **kwargs)
    except Exception as e:
        logging.error("Failed to spawn compile.py: %s", e)
        # Clean up lock on failure
        COMPILE_LOCK_FILE.unlink(missing_ok=True)


def main():
    if len(sys.argv) < 3:
        logging.error("Usage: %s <context_file.md> <session_id>", sys.argv[0])
        sys.exit(1)

    context_file = Path(sys.argv[1])
    session_id = sys.argv[2]

    logging.info("flush.py started for session %s, context: %s", session_id, context_file)

    if not context_file.exists():
        logging.error("Context file not found: %s", context_file)
        return

    # Deduplication: skip if same session was flushed within 60 seconds
    state = load_flush_state()
    if (
        state.get("session_id") == session_id
        and time.time() - state.get("timestamp", 0) < 60
    ):
        logging.info("Skipping duplicate flush for session %s", session_id)
        context_file.unlink(missing_ok=True)
        return

    # Read pre-extracted context
    context = context_file.read_text(encoding="utf-8").strip()
    if not context:
        logging.info("Context file is empty, skipping")
        context_file.unlink(missing_ok=True)
        return

    logging.info("Flushing session %s: %d chars", session_id, len(context))

    # Run the LLM extraction
    response = asyncio.run(run_flush(context))

    # Append to daily log
    if "FLUSH_OK" in response:
        logging.info("Result: FLUSH_OK")
        append_to_daily_log(
            "FLUSH_OK - Nothing worth saving from this session", "Memory Flush"
        )
    elif "FLUSH_ERROR" in response:
        logging.error("Result: %s", response)
        append_to_daily_log(response, "Memory Flush")
    else:
        logging.info("Result: saved to daily log (%d chars)", len(response))
        append_to_daily_log(response, "Session")

    # Update dedup state
    save_flush_state({"session_id": session_id, "timestamp": time.time()})

    # Clean up context file
    context_file.unlink(missing_ok=True)

    # End-of-day auto-compilation: if it's past the compile hour and today's
    # log hasn't been compiled yet, trigger compile.py in the background.
    maybe_trigger_compilation()

    logging.info("Flush complete for session %s", session_id)


if __name__ == "__main__":
    main()
