"""
Git sync operations for the shared team knowledge repo.

Handles pull/push with retry logic. Since each developer writes to their
own daily/<name>/ directory, merge conflicts on push are avoided by design.
The only shared-write path (knowledge/) is compiled locally by one developer
at a time, protected by a lock file.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from config import DEVELOPER, DEVELOPER_DAILY_DIR, ROOT_DIR

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

log = logging.getLogger(__name__)


def _git(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command in the shared repo root."""
    return subprocess.run(
        ["git", *args],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def git_pull() -> bool:
    """Pull latest from shared repo. Returns True on success."""
    try:
        result = _git("pull", "--rebase", "--autostash")
        if result.returncode != 0:
            log.warning("git pull failed: %s", result.stderr.strip())
            return False
        return True
    except subprocess.TimeoutExpired:
        log.warning("git pull timed out")
        return False
    except Exception as e:
        log.warning("git pull error: %s", e)
        return False


def has_pending_changes(path: str = "") -> bool:
    """Check if there are uncommitted changes in the given path."""
    args = ["status", "--porcelain"]
    if path:
        args.append(path)
    result = _git(*args)
    return bool(result.stdout.strip())


def git_push_with_retry(files: list[str], message: str) -> bool:
    """Stage, commit, and push with retry on conflict.

    If push fails (someone else pushed), pulls with rebase and retries.
    Since each dev writes to their own daily/ subdir, rebase always
    auto-resolves.
    """
    # Stage files
    _git("add", *files)

    # Check if there's anything to commit
    result = _git("diff", "--cached", "--quiet")
    if result.returncode == 0:
        return True  # nothing staged

    # Commit
    _git("commit", "-m", message)

    # Push with retry
    for attempt in range(MAX_RETRIES):
        result = _git("push")
        if result.returncode == 0:
            return True

        log.info(
            "Push failed (attempt %d/%d): %s",
            attempt + 1,
            MAX_RETRIES,
            result.stderr.strip(),
        )
        git_pull()
        time.sleep(RETRY_DELAY)

    log.error("Push failed after %d retries", MAX_RETRIES)
    return False


def sync_before_session() -> bool:
    """Pull team updates, push any pending local daily logs.

    Called by session-start.py. Does a single round trip:
    1. Stage + commit any local daily log changes
    2. Pull with rebase (gets team knowledge + other devs' logs)
    3. Push our commits
    """
    # Ensure developer daily dir exists
    DEVELOPER_DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # Commit any pending daily log changes
    daily_path = f"daily/{DEVELOPER}/"
    if has_pending_changes(daily_path):
        _git("add", daily_path)
        result = _git("diff", "--cached", "--quiet")
        if result.returncode != 0:
            _git("commit", "-m", f"daily/{DEVELOPER}: batch sync")

    # Pull (rebases our local commits on top of remote)
    git_pull()

    # Push if we have commits ahead of remote
    result = _git("rev-list", "--count", "@{u}..HEAD")
    if result.returncode == 0 and result.stdout.strip() not in ("0", ""):
        _git("push")

    return True
