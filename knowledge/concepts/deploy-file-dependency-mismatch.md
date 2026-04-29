---
title: "Deploy File Dependency Mismatch"
aliases: [state-py-mismatch, deploy-dependency-gap, coupled-file-deploy, extra-kwarg-crash]
tags: [value-betting, deployment, operations, anti-pattern, windows, reliability]
sources:
  - "daily/lcash/2026-04-28.md"
created: 2026-04-28
updated: 2026-04-28
---

# Deploy File Dependency Mismatch

On 2026-04-28, deploying `main.py` to the mini PC without its matching `state.py` caused an infinite crash loop. `server/main.py` called `state.set_bookie_status(..., extra={...})` but the mini PC's older `state.py` didn't have the `extra` parameter — producing a `TypeError` on every bet365 odds write cycle. The watchdog detected the crash and kept restarting the server, but the same crash occurred deterministically on every restart, making it look like transient infrastructure instability rather than a code bug. The crash was only identified by inspecting logs for the specific `TypeError`.

## Key Points

- `main.py` referenced `state.set_bookie_status(..., extra={...})` but `state.py` on the mini PC was stale and didn't accept the `extra` kwarg — `TypeError` on every bet365 write cycle
- The watchdog masked the root cause by continuously restarting the server — it appeared as infrastructure instability, not a deterministic code bug
- MLB server was in an infinite crash loop for the entire debugging period until `state.py` was deployed
- **Always deploy all dependent files together** — `main.py` and `state.py` are coupled via function signatures; deploying one without the other creates a guaranteed crash
- This is a sixth drift vector beyond manual launch, batch file omission, watchdog stripping, systemd layering, and TAB scraper env var missing (see [[concepts/configuration-drift-manual-launch]])

## Details

### The Failure Pattern

The value betting scanner's deploy process pushes individual files to the mini PC via SCP. When lcash deployed an updated `main.py` that added an `extra` keyword argument to the `set_bookie_status()` call, the corresponding `state.py` (which defines `set_bookie_status()`) was not deployed simultaneously. The mini PC's older `state.py` had the function signature `set_bookie_status(bookie, status, ...)` without the `extra` parameter.

Every time the bet365 game scraper completed a scrape cycle and called `state.set_bookie_status(bookie, status, extra={...})`, Python raised `TypeError: set_bookie_status() got an unexpected keyword argument 'extra'`. This error occurred on every write cycle — deterministically, not intermittently.

### Why Watchdog Restarts Masked the Bug

The Windows watchdog (see [[concepts/watchdog-environment-stripping]]) detected that the server process had exited and automatically restarted it. The restarted process hit the same `TypeError` on its first bet365 write cycle and crashed again. This crash-restart loop repeated indefinitely, producing a pattern that looked like infrastructure instability — the process was "running" (being continuously restarted) but never successfully completing a full cycle.

An operator checking process health would see: process alive (watchdog just restarted it), or process dead (between watchdog cycles). The rapid cycling between these states mimics network connectivity issues, resource exhaustion, or other transient problems. Only inspecting the actual error logs (not just process liveness) revealed the deterministic `TypeError`.

### The Coupled File Problem

`main.py` and `state.py` are coupled via Python function call signatures. When `main.py` passes a keyword argument that `state.py`'s function definition doesn't accept, the call fails at runtime. Python doesn't check function signatures at import time — the error only surfaces when the specific code path executes. This means:

1. The server starts successfully (imports work fine)
2. The OpticOdds poller, push worker, and other non-bet365 components run correctly
3. The crash occurs specifically when the bet365 game scraper writes odds — the only code path that calls the modified function

This partial functionality is deceptive: the server appears partially healthy (some components work) while a specific subsystem crashes repeatedly.

### Documentation vs Code Mismatch

The investigation also revealed that `MINI_PC_CHROME_SETUP.md` documented specific persistent Chrome profile directory paths (`C:\Users\Dell\bet365_nba_profile`, `C:\Users\Dell\bet365_mlb_profile`), but the codebase was not actually using those paths. This is a general problem: operational documentation can diverge from code, and during incident response, following the documentation leads to incorrect assumptions about system state.

### Prevention

Three mitigation strategies:

1. **Deploy script**: A deploy script that pushes all Python files in a module together, not individual files. If `main.py` changes, `state.py` is always included.
2. **Import-time validation**: A lightweight startup check that verifies critical function signatures match expected parameter lists before entering the main loop.
3. **Deploy checklist**: At minimum, a documented list of file dependencies — "if you change `main.py`, also deploy `state.py`, `models.py`, and `tracker.py`."

## Related Concepts

- [[concepts/configuration-drift-manual-launch]] - The broader configuration drift pattern; this is a new variant where the drift is between deployed code files rather than environment variables
- [[concepts/deploy-syntax-validation-gap]] - A related deploy failure: syntax errors kill the tracker silently. Both are cases where `python -m py_compile` or import testing before deploy would catch the issue
- [[concepts/watchdog-environment-stripping]] - The watchdog that masked this bug by continuously restarting the crashed server; watchdog restarts without diagnosing create an illusion of transient instability
- [[connections/operational-compound-failures]] - The crash loop + watchdog masking + no alerting chain follows the established compound failure pattern
- [[concepts/value-betting-operational-assessment]] - Weakness #3 (configuration drift) and #2 (no monitoring) both manifest: the deploy gap is config drift at the code level, and log-based alerting would have caught the TypeError immediately

## Sources

- [[daily/lcash/2026-04-28.md]] - MLB server infinite crash loop from `state.py` not deployed alongside `main.py`; `extra` kwarg TypeError on every bet365 write; watchdog masked the deterministic crash; both NBA and MLB confirmed stable after deploying updated `state.py`; MINI_PC_CHROME_SETUP.md profile paths didn't match code; bet365 allows simultaneous sessions from two Chrome profiles confirmed (Sessions 11:33, 11:36, 12:07)
