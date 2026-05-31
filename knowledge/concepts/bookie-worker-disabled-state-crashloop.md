---
title: "Bookie Worker Disabled-State Crashloop"
aliases: [bookie-worker-crashloop, sys-exit-restart-always, disabled-state-exit, systemd-crashloop]
tags: [superwin, racing, operations, bug, systemd, deployment]
sources:
  - "daily/lcash/2026-05-29.md"
created: 2026-05-29
updated: 2026-05-29
---

# Bookie Worker Disabled-State Crashloop

On 2026-05-29, lcash discovered that `bookie_worker.py` called `sys.exit(5)` when the database `enabled` flag was `False`. Combined with systemd's `Restart=always` policy, this created a crashloop: the worker starts → checks `db.enabled` → exits → systemd restarts it → repeat. The bug was latent and only exposed when a deploy restart occurred during off-hours (when the racing schedule cron had disabled the workers). It ran 33 restarts before being caught.

## Key Points

- **`sys.exit(5)` on disabled state + systemd `Restart=always`** = crashloop when workers are disabled by the racing schedule cron
- **33 restarts before caught** — latent bug exposed by a deploy restart during off-hours
- **Fix: `while not enabled: sleep(60); re-check` loop** — worker waits quietly and auto-recovers when the cron re-enables it
- **Racing schedule cron** (`racing_schedule.sh`) flips `db.enabled` at 13:00 UTC (stop) / 23:00 UTC (start) — workers need to survive the disabled window gracefully

## Details

### The Latent Bug

The `bookie_worker.py` startup flow checked the database `enabled` flag and called `sys.exit(5)` if the worker was disabled. This was fine when the workers were always started during racing hours (when `enabled=True`). The bug was latent — it never triggered during normal operations because:

1. The racing schedule cron enables workers at 23:00 UTC (09:00 AEST)
2. Workers were typically started manually during active hours
3. Workers that were already running when the cron disabled them would stop naturally

The deploy restart on May 29 happened during off-hours when `enabled=False`. The worker started, checked the flag, exited with code 5, and systemd immediately restarted it. This repeated 33 times in rapid succession.

### The Fix

The fix replaced the fatal exit with a polling loop:

```python
# Before (crashloop)
if not db.enabled:
    sys.exit(5)

# After (graceful wait)
while not db.enabled:
    log.info("Worker disabled, waiting 60s...")
    sleep(60)
    db.refresh()
```

The worker now idles silently during the disabled window and automatically picks up work when the racing schedule cron re-enables it at 23:00 UTC. No manual intervention required after deploy restarts during off-hours.

### Related Discovery: Cron SLUGS Drift

During the same session, lcash discovered that three new bookies (boostbet, neds, pointsbet) were missing from `racing_schedule.sh`'s hardcoded `SLUGS` list. They were added to the platform on 2026-05-26 but nobody updated the cron script. Result: those three bookies polled 24/7 (~28k extra requests/hour) during off-hours instead of being disabled by the cron. This is another instance of [[concepts/configuration-drift-manual-launch]].

## Related Concepts

- [[concepts/configuration-drift-manual-launch]] - Cron SLUGS list drift is the same anti-pattern: adding a bookie to the platform without updating all configuration touchpoints
- [[concepts/superwin-process-isolation-reliability]] - Worker crashloops are one of the reliability problems that per-bookie subprocess isolation would contain

## Sources

- [[daily/lcash/2026-05-29.md]] - `sys.exit(5)` on disabled state + `Restart=always` = 33 restarts; deploy during off-hours exposed latent bug; fix: `while not enabled: sleep(60)` loop; also discovered boostbet/neds/pointsbet missing from cron SLUGS list (24/7 polling); boostbet competitor_id surfaced as runner.bookie_ids.boostbet (Session 08:41)
