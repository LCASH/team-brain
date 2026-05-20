---
title: "Stale In-Memory Import Writer Leak"
aliases: [v1-hash-leak, stale-import-bug, in-memory-code-drift, scp-without-restart, parallel-writer-race]
tags: [value-betting, deployment, bug, architecture, operations, tracker]
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# Stale In-Memory Import Writer Leak

On 2026-05-18, lcash discovered that the VPS legacy `value-betting.service` (PID 920843) had been writing v1-format pick hashes for 3+ days because it was started **8 minutes before** the position-model commit was authored. The running Python process loaded the old `tracker.py` into memory at import time and never re-imported it — even after the new `tracker.py` was SCP'd to disk. This produced 661 interleaved v1/v2 duplicate rows in Supabase, invisible until the Phase 10 hash version monitor detected the leak.

## Key Points

- **SCP'ing new code to disk does NOT update a running Python process's imports** — the old code remains in `sys.modules` until the process restarts
- VPS legacy service PID 920843 started at `2026-05-15T06:31:01Z`, position-model commit authored at `2026-05-15T06:39:09Z` — process loaded v1 tracker 8 minutes before v2 existed on disk
- The service ran for **3+ days** writing v1 picks alongside the v3 process writing v2 picks — interleaved rows seconds apart in Supabase
- **Process start time vs commit author time** is the diagnostic tool: if `process_start < commit_time`, the process has stale code
- Post-SIGTERM batch drain: 1 minute 39 seconds of additional v1 writes after `systemctl stop` — account for this drain window when verifying fixes
- Phase 10 monitor (`scripts/tracker_audit/10_hash_version.py`) built and permanently wired into `run_all.sh` to catch v1 leaks going forward
- Fix: `systemctl stop && disable value-betting` on VPS — the legacy service was documented as relay-only for the decommissioned Windows mini PC

## Details

### The Stale Import Mechanism

Python loads modules into memory at import time and caches them in `sys.modules`. When a running process imports `server.tracker`, the tracker module's code is read from disk, compiled to bytecode, and stored in memory. Subsequent references to `tracker` use the in-memory cached version, never re-reading the disk. This is a fundamental Python design — imports are not live-linked to the filesystem.

When code is deployed via SCP (copying new files to disk), the running process continues executing the old in-memory version. The new code on disk is only loaded when a new Python process starts and imports the module fresh. This means any deploy that doesn't include a process restart leaves the old code running.

In the May 18 incident, the sequence was:
1. `value-betting.service` started on VPS, importing v1 `tracker.py` into memory
2. 8 minutes later, the position-model commit updated `tracker.py` on disk (via SCP from a deploy)
3. The running service continued using v1 `tracker.py` from memory
4. For 3+ days, both the v1 service and the v3 process wrote picks to Supabase concurrently

### The Parallel Writer Race

The concurrent v1 and v2 writers produced interleaved rows in Supabase that were separated by only seconds. For the same market, the v1 writer generated a pick with the old hash (including `line` in the hash, producing a new row when the line moved), while the v2 writer generated a pick with the new position-based hash. This created duplicate position groups — the same logical bet tracked twice under different pick IDs.

The interleaving made the duplicates look like a data race or a tracker bug rather than a deployment artifact. Only comparing process start times against commit timestamps revealed that two independent processes were writing with different code versions.

### The Post-SIGTERM Drain Window

When `systemctl stop value-betting` sent SIGTERM to the legacy service, the process began its shutdown sequence. However, any in-flight tracker cycle that had already started continued to completion — writing its final batch of picks before the process exited. In this case, one "drain" v1 pick appeared 1 minute 39 seconds after the stop signal. This drain window means that verifying "the leak is plugged" requires waiting several minutes after the stop signal before checking for new v1 rows.

### Phase 10 Hash Version Monitor

A permanent Phase 10 audit (`scripts/tracker_audit/10_hash_version.py`) was built to detect this class of bug. The monitor computes the expected v2 hash for recent picks and compares against the stored `pick_id`. Any mismatch indicates a v1 writer is active. This was wired into `run_all.sh` alongside the existing 9-phase audit suite (see [[concepts/tracker-pipeline-7-phase-audit]]).

### General Anti-Pattern: Deploy Without Restart

This bug represents a general class of deployment failure: **deploying code without restarting the process that consumes it.** The anti-pattern is particularly dangerous when:

1. The deploy mechanism (SCP) operates at the filesystem level, not the process level
2. Multiple processes consume the same code files (v3 process + legacy service)
3. The old process produces valid-looking output (v1 picks are structurally correct, just using the wrong hash)
4. No monitoring exists to detect the version mismatch

The fix is either: always restart all writers after deploying tracker code, or use a deployment mechanism that inherently restarts processes (like `systemctl restart` or container redeployment).

## Related Concepts

- [[concepts/deploy-file-dependency-mismatch]] - A related deploy failure: deploying one file without its dependency; this bug deploys the right file but doesn't restart the process consuming it
- [[concepts/tracker-pipeline-7-phase-audit]] - Phase 10 hash version monitor added to the audit suite to permanently detect this class of leak
- [[connections/silent-type-coercion-data-corruption]] - The v1 picks are "plausible wrong output" — structurally valid rows that use the wrong hash version, invisible without version-aware monitoring
- [[concepts/configuration-drift-manual-launch]] - A parallel deployment drift pattern: env vars drifting from intended state; this is code drifting from intended version within a running process
- [[connections/stale-process-state-phantom-liveness]] - The broader pattern: the legacy service appeared healthy (writing picks, Supabase INSERT succeeding) while running stale code

## Sources

- [[daily/lcash/2026-05-18.md]] - VPS legacy `value-betting.service` PID 920843 started 8 min before position-model commit; loaded v1 tracker.py into memory, wrote v1 picks for 3+ days; 661 interleaved v1/v2 duplicates; fix: systemctl stop && disable; Phase 10 monitor built; post-SIGTERM drain window 1m39s; news agent confirmed intentionally writing negative-EV picks (pre-sharp prediction); process start time vs commit author time as diagnostic tool (Session 12:04)
