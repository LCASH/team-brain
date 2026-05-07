---
title: "Deployment Verification Automation"
aliases: [verify-mini-pc-sync, sync-and-verify, deployment-scripts, three-tier-verification]
tags: [value-betting, deployment, operations, automation, reliability]
sources:
  - "daily/lcash/2026-05-03.md"
created: 2026-05-03
updated: 2026-05-03
---

# Deployment Verification Automation

After a multi-day silent outage where the bet365 scraper was dead since April 27 and the push worker since April 30 with zero notification, lcash created a three-tier deployment verification system on 2026-05-03. The system addresses the recurring pattern where services crash on the mini PC and nobody is notified because alerting infrastructure (Discord webhook) was not configured, stale processes persist with old code, and `__pycache__` directories serve cached bytecode from pre-fix versions.

## Key Points

- **Three tiers**: `verify_mini_pc_sync.sh` (check-only), `verify_mini_pc_sync.sh --fix` (auto-cleanup), `sync_and_verify.sh` (full deployment with verification)
- Created after discovering bet365 scraper dead since Apr 27 and push worker dead since Apr 30 — a 6-day and 3-day silent outage respectively
- Performs full process cleanup during redeployment: kills stale Python processes holding old code, clears `__pycache__` directories
- Includes post-deploy health endpoint verification (`curl http://100.67.233.95:8800/api/v1/health`) to confirm services actually started
- Discord webhook URL was added to `.env` and login failure detection wired to alerts in both `bet365_nba_v3.py` and `bet365_mlb_v3.py` as part of the same fix session

## Details

### The Silent Outage That Triggered Automation

On 2026-05-03 (Session 08:10), lcash discovered two independent service deaths on the mini PC:

1. **bet365 scraper subprocess**: Dead since April 27 (6 days) — the same date the NBA scraper death was first documented in [[concepts/bet365-session-login-detection-gap]]
2. **Push worker**: Dead since April 30 (3 days) — no data flowing from mini PC to VPS

Neither failure triggered a notification because `ALERT_WEBHOOK_URL` was not set in the mini PC's `.env` file — the Discord alerting system deployed on 2026-05-02 (see [[concepts/vps-monitoring-log-noise-elimination]]) was non-functional on the mini PC despite being configured on the VPS.

### Three-Tier Verification Strategy

**Tier 1 — Check-only (`verify_mini_pc_sync.sh`)**:
Compares file hashes between the local repo and the mini PC, identifies stale processes, checks for orphaned `__pycache__` directories, and reports discrepancies without making changes. Intended for daily health monitoring.

**Tier 2 — Auto-cleanup (`verify_mini_pc_sync.sh --fix`)**:
Everything Tier 1 does, plus automatically kills stale Python processes, clears `__pycache__`, and removes orphaned files. Intended for weekly maintenance to prevent bytecode drift and process accumulation.

**Tier 3 — Full deploy (`sync_and_verify.sh`)**:
Syncs all code files to the mini PC, kills all stale processes, clears all caches, restarts services via their scheduled tasks, and verifies data flow via the health endpoint. Intended for use before any deployment to guarantee a clean state.

### Why `__pycache__` Cleanup Matters

Python's `__pycache__` directory stores compiled `.pyc` bytecode files. When source code is updated via SCP/rsync but `__pycache__` is not cleared, the Python interpreter may load the cached bytecode from the previous version instead of recompiling the updated source. This produces a failure mode where the deployed code is correct on disk but the running process executes the old cached code — the same deployment artifact documented for the news agent in [[concepts/news-agent-classifier-vocabulary-gaps]].

The verification scripts clear `__pycache__` on every deployment to ensure fresh bytecode compilation.

### Recommended Operational Cadence

- **Daily**: `curl http://100.67.233.95:8800/api/v1/health` — verify services are alive
- **Weekly**: `./scripts/verify_mini_pc_sync.sh --fix` — cleanup orphaned processes and stale caches
- **Before any deploy**: `./scripts/sync_and_verify.sh` — full clean deployment with verification

### Discord Webhook Deployment

In the same session, `ALERT_WEBHOOK_URL` was added to the mini PC's `.env` and login failure detection was wired to Discord alerts in both `bet365_nba_v3.py` and `bet365_mlb_v3.py`. This closes the alerting gap documented in [[concepts/bet365-session-login-detection-gap]] where login failures were not wired to the Discord alert function. After this deployment, both task death and login expiry produce immediate Discord notifications.

## Related Concepts

- [[concepts/configuration-drift-manual-launch]] - The deployment drift pattern that verification scripts prevent; batch files missing flags, stale processes, and cached bytecode are all forms of deployment state divergence
- [[concepts/bet365-session-login-detection-gap]] - The login detection gap that was simultaneously fixed by wiring Discord alerts; the 6-day scraper death was the same incident
- [[concepts/vps-monitoring-log-noise-elimination]] - The Discord alerting infrastructure (deployed 2026-05-02 on VPS) that was missing from the mini PC until this fix
- [[concepts/deploy-file-dependency-mismatch]] - A related deployment failure: deploying one file without its dependency; the verification scripts catch this class of mismatch
- [[concepts/news-agent-classifier-vocabulary-gaps]] - Stale `.pyc` files from `__pycache__` caused the same failure pattern in the news agent; verification scripts prevent recurrence
- [[connections/operational-compound-failures]] - The multi-day silent outage is another instance of the compound failure chain: drift + silent failure + no monitoring

## Sources

- [[daily/lcash/2026-05-03.md]] - bet365 scraper dead since Apr 27, push worker dead since Apr 30 — no Discord webhook configured; three-tier verification strategy created; `ALERT_WEBHOOK_URL` added to `.env`; login failure detection wired to alerts in both v3 scrapers; full sync and deployment performed with stale process cleanup (Session 08:10)
