---
title: "Betfair Streaming Subscription Cap and Tiered Eviction"
aliases: [betfair-200-cap, betfair-subscription-limit, betfair-market-cap, tiered-eviction, cloth-number-scratching-bug]
tags: [superwin, racing, betfair, streaming, architecture, infrastructure, bug]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# Betfair Streaming Subscription Cap and Tiered Eviction

Betfair's streaming API enforces a hard cap of **200 markets per connection**, with **8 connections available** (1,600 total capacity). The SuperWin scanner used a single connection, meaning only 200 WIN+PLACE market pairs could be monitored simultaneously. When morning races that hadn't formally CLOSED held their slots into the afternoon, late-arriving races were blocked from subscribing — producing 1-3 unsettled races per day. A tiered eviction strategy (SUSPENDED never evicted → imminent ±90min → upcoming → stale evicted) was designed to maximize coverage within the 200-slot constraint. Simultaneously, a `_cloth_number()` runner-mapping bug was discovered: `sortPriority` compresses to sequential indices when greyhound runners scratch, causing BSP/LTP/CLV to be attributed to the wrong runner.

## Key Points

- **Hard cap: 200 markets per streaming connection** — confirmed via live test: `SUBSCRIPTION_LIMIT_EXCEEDED, max allowed: 200`
- **8 connections available** (`connectionsAvailable: 8` in auth response) — total capacity 1,600 markets via multi-connection sharding (not yet implemented)
- **Tiered eviction within single connection** (Option B chosen over multi-connection sharding): SUSPENDED (Tier 0, never evicted) → imminent ±90min (Tier 1) → upcoming → stale evicted; re-subscribe threshold of 3 prevents churn
- **Morning races hold slots**: Races that haven't formally CLOSED (Betfair lifecycle event) maintain their subscription even when their data value is zero, blocking afternoon races
- **Cloth-number bug**: `_cloth_number()` fallback to `sortPriority` breaks when greyhound scratchings compress the sequence — runner 5 might get `sortPriority=3` if runners 2 and 4 scratched. **Runner NAME is the reliable source** ("5. Lady Nova" → parse 5)
- **PnL is correct, BSP/CLV are wrong** on races with scratchings (~42% of historical races) — PnL derives from WIN/LOSE status (immune to mapping), BSP/CLV derive from runner-number lookup (vulnerable)
- **Audit trap**: Comparing `pick.bsp` to `race_results.runner_map[number].bsp` gives false 200/200 pass because both sides have the SAME wrong number — must compare on NAME not number

## Details

### The Subscription Slot Problem

The scanner's `_build_subscription_list` function sorts available races by `start_time ASC` and fills the first 200 WIN+PLACE pairs (100 races × 2 markets each). Once filled, no new races can subscribe until existing ones free their slots by transitioning to CLOSED status.

The problem: Betfair's CLOSED lifecycle event fires when all bets are settled and the market result is finalized. For Australian racing, this can take 10-30 minutes after the race finishes (protest review, photo finish, official result). A race that jumped at 10:00 AM might not CLOSE until 10:30 AM, occupying subscription slots while an afternoon race starting at 2:00 PM cannot subscribe. Over a full day's card (200+ AU/NZ races), the 200-slot cap means ~25-50% of races are subscription-blocked at any given time.

### Tiered Eviction Strategy

The designed eviction strategy assigns priority tiers:

| Tier | Criteria | Eviction Policy |
|------|----------|-----------------|
| 0 (SUSPENDED) | Race jumped, awaiting result | Never evicted — result data critical for settlement |
| 1 (Imminent) | Start time within ±90 min | Highest priority for subscription slots |
| 2 (Upcoming) | Start time >90 min away | Subscribe if slots available |
| 3 (Stale) | Start time >90 min ago and not SUSPENDED | Evicted to free slots |

A re-subscribe threshold of 3 (only re-subscribe a market if it has been evicted 3+ times without being needed) prevents churn from rapid tier transitions at the ±90 min boundary.

### Multi-Connection Sharding (Deferred)

Option A — multi-connection sharding (8 × 200 = 1,600 markets) — provides the raw capacity to cover the entire AU/NZ daily card without eviction. The implementation would create 2+ Betfair streaming connections, each subscribing to a disjoint set of markets. This was deferred in favor of Option B (smarter eviction within single connection) because:

1. Multi-connection adds complexity (connection lifecycle management, market-to-connection routing)
2. The eviction strategy handles the symptom with ~15 lines of code
3. If daily markets routinely exceed 400, multi-connection becomes necessary

### Cloth-Number Runner Mapping Bug

A separate but related finding: `_cloth_number()` in `server/bookies/betfair.py:359-365` falls back to `sortPriority` when the cloth number isn't explicitly available. For greyhounds with scratchings, `sortPriority` assigns sequential indices that don't match the actual box/trap number:

| Runner | Actual Box | sortPriority (with 2,4 scratched) |
|--------|-----------|----------------------------------|
| Runner 1 | Box 1 | 1 |
| Runner 3 | Box 3 | 2 ← wrong |
| Runner 5 | Box 5 | 3 ← wrong |
| Runner 6 | Box 6 | 4 ← wrong |

The fix parses the saddle/cloth number from the runner name prefix — Betfair formats names as "5. Lady Nova" where the number before the period is the cloth/box number. This is reliable regardless of scratchings.

The audit that initially gave 200/200 PASS was comparing `pick.bsp` against `race_results.runner_map[number].bsp` — but both sides used the same wrong number (from `sortPriority`), so they matched. The correct audit compares on runner NAME to detect the mapping error.

**Impact**: PnL fields (result, profit) are immune because they derive from WIN/LOSE status flags, not runner-number lookups. BSP, LTP, and CLV fields are all wrong for races with scratchings (~42% of historical races) because they require looking up the correct runner by number in `race_results`.

## Related Concepts

- [[concepts/settlement-queue-starvation-ordering]] - The ASC+LIMIT queue starvation bug compounds with the subscription cap — orphan picks from missed settlements (subscription gaps) filled the resolver queue
- [[concepts/superwin-edge-pick-backtesting]] - BSP/CLV are the primary backtesting metrics; the cloth-number bug corrupts ~42% of historical BSP/CLV values (PnL still correct)
- [[concepts/bet365-coupon-pm-id-mismatch]] - A parallel ID-mapping bug: bet365 coupon IDs ≠ PM subscription IDs, solved with barrier-number fallback. Betfair's bug uses name-parsing instead
- [[connections/silent-type-coercion-data-corruption]] - The cloth-number bug produces plausible wrong BSP/CLV with zero error signal; the audit false-pass (same wrong number on both sides) is a meta-validation failure

## Sources

- [[daily/lcash/2026-05-26.md]] - Betfair hard cap confirmed: `SUBSCRIPTION_LIMIT_EXCEEDED, max allowed: 200`; `connectionsAvailable: 8`; tiered eviction: SUSPENDED→imminent→upcoming→stale; Option B chosen over multi-connection; cloth-number bug: sortPriority compresses on scratchings, parse from runner name instead; PnL correct but BSP/LTP/CLV wrong on ~42% of races; audit compared on number (false pass) not name; backfill Phase A: fix race_results rows, Phase B: re-resolve ~10k picks (Session 14:20)
