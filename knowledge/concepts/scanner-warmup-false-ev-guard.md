---
title: "Scanner Warmup False EV Guard"
aliases: [warmup-guard, startup-data-lag, bookie-ramp-up, false-ev-startup, warmup-threshold]
tags: [superwin, racing, operations, reliability, data-quality]
sources:
  - "daily/lcash/2026-04-26.md"
created: 2026-04-26
updated: 2026-04-26
---

# Scanner Warmup False EV Guard

Bookmakers ramp up at different speeds on startup — TAB takes 20-40s for REST discovery, TabTouch needs MQTT connection time, Betfair resubscribes to markets — creating temporary data lag between sources. This lag produces artificial EV gaps that look like real opportunities: one bookie's odds are visible while another's aren't, so the comparison produces phantom +EV from missing data rather than genuine mispricing. The SuperWin racing scanner now won't persist picks to the journal until 2+ bookies have 50+ races each. Opportunities still stream to the TAKEOVER UI during warmup but nothing hits the backtesting database until data is reliable.

## Key Points

- Startup data lag between bookies (TAB: 20-40s REST, TabTouch: MQTT connect, Betfair: resubscribe) creates artificial EV gaps that look like real opportunities
- Warmup guard: 2+ racing bookies must have 50+ races each before picks are persisted to `superwin_edge_picks` journal
- During warmup, opportunities still stream to the TAKEOVER UI (operators can see what's happening) but are NOT persisted (no false journal entries)
- The pattern of "stream to UI but don't persist" lets operators monitor startup health without contaminating the backtesting database
- The 9am cron was changed from DB flag toggle to full `systemctl restart superwin` — fixes the recurring bug where toggling `enabled` in DB doesn't register adapters that weren't loaded at service start

## Details

### The False EV Mechanism

When the SuperWin scanner starts (or restarts), each bookie adapter initializes independently. TAB's REST-based adapter discovers available races via HTTP requests taking 20-40 seconds. TabTouch's MQTT adapter needs to establish a Cognito-authenticated WebSocket connection. Betfair's streaming adapter resubscribes to market channels. During this ramp-up period, the scanner has partial data: one bookie's odds may be fully loaded while another's haven't arrived yet.

The EV calculation compares odds across bookies. If TAB shows 3.50 for a runner but Betfair hasn't loaded yet (so its fair-value estimate is missing or stale), the scanner may compute a large positive EV based on incomplete data. This is not a genuine edge — it's a startup artifact that disappears once all sources are online.

### The Warmup Guard Pattern

The guard uses a simple threshold: the scanner counts how many racing bookies have delivered data for 50+ races. Only when 2 or more bookies pass this threshold does the scanner begin persisting picks to the Supabase `superwin_edge_picks` journal table.

The threshold of 2 bookies × 50 races was chosen to balance speed-to-market (don't wait too long) against data reliability (don't persist garbage). A single bookie could have 50 races but with no comparison source, EV computation is meaningless. Two bookies with 50 races each ensures at least one comparison pair exists with reasonable market coverage.

### Stream vs Persist Separation

During warmup, the scanner's real-time feed to the TAKEOVER frontend continues operating normally — detected opportunities appear on the dashboard with their computed EV values. The only change is that the `_persist_pick()` call is gated behind the warmup check. This gives operators visibility into what the scanner sees during startup (useful for diagnosing startup issues) without creating false historical records that would contaminate profitability analysis.

This separation matters because the backtesting system (see [[concepts/superwin-edge-pick-backtesting]]) uses the journal as its source of truth. False startup picks with 50%+ phantom EV would skew ROI calculations and make the system appear more profitable than it is. The insert-only journal pattern (which preserves first-detection odds) compounds this — a false startup pick can never be corrected, only voided.

### Cron Restart Fix

A related fix changed the 9am racing cron from a simple DB flag toggle to a full service restart (`systemctl restart superwin`). The previous approach toggled `enabled=true` for racing adapters in Supabase, but adapters only register with the scanner at service startup time. If the service started overnight (when racing was disabled), the adapters were never loaded into the running process — flipping the DB flag had no effect. The full restart ensures adapters are loaded fresh with the correct enabled state.

## Related Concepts

- [[concepts/superwin-edge-pick-backtesting]] - The backtesting journal that the warmup guard protects from false picks; insert-only pattern means contamination is permanent
- [[connections/browser-automation-reliability-cost]] - A parallel warmup issue: browser-mediated scrapers take hours to warm up after restart (see the warmup latency section); the racing scanner's bookie ramp-up is the same class of problem at a shorter timescale
- [[concepts/configuration-drift-manual-launch]] - The cron toggle-vs-restart pattern is conceptually related: both are cases where a lightweight operation (toggle flag, restart via batch file) doesn't actually propagate the intended change because the runtime state wasn't reloaded
- [[concepts/worker-status-observability]] - During warmup, the scanner should ideally report a "warming_up" state rather than "streaming" to avoid the false-healthy status pattern

## Sources

- [[daily/lcash/2026-04-26.md]] - Startup data lag between bookies (TAB 20-40s REST, TabTouch MQTT, Betfair resubscribe) creates artificial EV gaps; warmup guard: 2+ bookies with 50+ races before persisting picks; stream to UI during warmup but don't persist to journal; 9am cron changed from DB flag toggle to full systemctl restart; Sandown venue mismatch resolved via fuzzy matching; unsettled picks cleared from 21→0 stuck; -13.1% CLV on 19 picks suggests EV thresholds may need tightening (Session 13:19)
