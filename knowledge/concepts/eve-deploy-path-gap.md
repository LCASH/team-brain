---
title: "Eve Deploy Path Gap"
aliases: [eve-deploy-gap, eve-scp-drift, resolver-stale-on-eve, deploy-script-wrong-host, eve-deployment-drift]
tags: [value-betting, deployment, operations, reliability, eve, drift]
sources:
  - "daily/lcash/2026-05-18.md"
created: 2026-05-18
updated: 2026-05-18
---

# Eve Deploy Path Gap

On 2026-05-18, lcash discovered Eve's `server/resolver.py` was from May 2 — **16 days stale** — missing the anchored closing bundle, `closing_source` column writes, and `synthetic_clv_pct` computation. Other critical files (tracker, CO parsers, pitcher EVs) were current from May 15. The root cause: `scripts/deploy.sh` was configured to target the decommissioned Windows mini PC (`Dell@100.67.233.95`), not Eve (`the-fellowship@192.168.0.92`). A friend's commit `0c02c16` fixed the mini PC deploy path but Eve's deploy path was never updated.

## Key Points

- Eve's `resolver.py` was **16 days stale** (May 2 vs May 18) — missing 3 critical features: anchored closing bundle, `closing_source` column, `synthetic_clv_pct`
- Other files (tracker.py, CO parsers, pitcher EV mappings) were current (May 15) — selective staleness from different deploy events
- Root cause: `deploy.sh` targets decommissioned Windows mini PC, not Eve — Eve gets files via manual SCP with no automated deploy script
- `MINI_PC_URL` env var is legacy — now points to Eve (`100.69.199.85:8900`), not the decommissioned Windows mini PC
- Eve uses SCP-based deploys, not git pull — no automated deploy script covers all files for Eve
- This is a **recurring risk** every time resolver.py changes: the deploy process doesn't include Eve automatically

## Details

### The Selective Staleness Pattern

Eve had a mix of current and stale files because different files were deployed at different times via manual SCP:

| File | Version on Eve | Expected | Status |
|------|---------------|----------|--------|
| `server/tracker.py` | May 15 | May 15 | Current |
| CO parser files | May 15 | May 15 | Current |
| Pitcher EV mappings | May 15 | May 15 | Current |
| `server/resolver.py` | **May 2** | May 18 | **16 days stale** |

The tracker was updated on May 15 during the Phase 9 position-consistency fix (see [[concepts/tracker-pipeline-7-phase-audit]]). The resolver was apparently never included in that SCP deploy. This selective staleness is harder to detect than a fully stale deployment because most components work correctly — only the resolver's output is silently degraded.

### Deploy Script Architecture

The deploy workflow has two target hosts with different mechanisms:

1. **VPS** (`170.64.213.223`): `deploy.sh vps` works correctly — git-based deploy
2. **Eve** (`192.168.0.92`): No automated deploy script — files are manually SCP'd on a per-need basis

A friend's commit `0c02c16` fixed the mini PC deploy path in `deploy.sh`, but this fix was specific to the Windows mini PC (now decommissioned). Eve was never added as a deploy target, creating a permanent gap where Eve must be manually remembered and SCP'd after every code change.

### Impact on Resolver Output

The stale resolver on Eve was missing:
- **Anchored closing bundle**: The `anchored_bundle()` helper (see [[concepts/trail-anchored-bundle-read-layer-fix]]) that enforces temporal alignment between soft and sharp trail data
- **`closing_source` column**: Writes that indicate where closing odds came from (trail entry vs opening snapshot)
- **`synthetic_clv_pct`**: Computed CLV from the anchored bundle, stored per pick

This means all resolver output on Eve for the 16-day window used the old methodology: potentially misaligned soft/sharp closing odds, no closing source audit trail, and no synthetic CLV computation. The picks themselves were resolved (win/loss/push) correctly because that logic existed in the May 2 code — the missing features affected analytics quality, not resolution accuracy.

### Fix and Verification

The fix was a direct SCP of `resolver.py` to Eve, followed by syntax verification under Eve's venv and a v3 restart. The resolver fired cleanly at 09:18 with 18 code sentinels confirmed matching the expected version. Post-deploy verification included checking both VPS and Eve resolvers were current before proceeding.

### Recurring Risk

This gap will recur every time `server/resolver.py` is changed on main. Without an automated Eve deploy path (either in `deploy.sh` or a CI/CD hook), Eve's resolver will silently drift from main until someone manually notices and SCP's the file. This is the same class of deployment drift documented in [[concepts/deploy-file-dependency-mismatch]] (deploying one file without its dependencies) and [[concepts/configuration-drift-manual-launch]] (configuration not matching deployment scripts), applied specifically to Eve's file-level deploy gap.

## Related Concepts

- [[concepts/deploy-file-dependency-mismatch]] - A related deploy failure pattern: deploying one file without its dependency. Eve's gap is about a file never being deployed at all
- [[concepts/tracker-pipeline-7-phase-audit]] - Phase 9 position consistency detected Eve's deploy drift (8 commits behind) on May 15; the resolver gap on May 18 is a continuation of the same pattern
- [[concepts/trail-anchored-bundle-read-layer-fix]] - The anchored_bundle() feature missing from Eve's stale resolver; analytics quality degraded but resolution accuracy unaffected
- [[concepts/configuration-drift-manual-launch]] - The broader drift pattern: deployment state diverging from intended state; Eve's SCP-only deploy process is inherently drift-prone

## Sources

- [[daily/lcash/2026-05-18.md]] - Eve resolver.py from May 2 (16 days stale); deploy.sh targets decommissioned Windows mini PC not Eve; friend's commit 0c02c16 fixed mini PC but not Eve; SCP'd resolver, verified 18 sentinels, restarted v3; MINI_PC_URL is legacy pointing to Eve not mini PC; AdsPower zombie port caused initial NBA failure after deploy (Session 10:08)
