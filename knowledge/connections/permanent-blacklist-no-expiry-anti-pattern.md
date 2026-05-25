---
title: "Connection: Permanent In-Memory Blacklists Without Expiry"
connects:
  - "concepts/bet365-nba-fixture-permanent-blacklist-bug"
  - "concepts/mlb-v3-recently-closed-cache-deadlock"
  - "concepts/stale-in-memory-import-writer-leak"
sources:
  - "daily/lcash/2026-05-25.md"
created: 2026-05-25
updated: 2026-05-25
---

# Connection: Permanent In-Memory Blacklists Without Expiry

## The Connection

Two independently discovered bugs in the value betting scanner — the NBA fixture `_failed_fixtures` permanent blacklist (May 25) and the MLB `_recently_closed` cache deadlock (May 2) — share the same root anti-pattern: an in-memory set that grows monotonically with no expiry, recovery path, or reconciliation against external state. Once an item enters the set, it is permanently excluded for the lifetime of the process, even if the condition that caused the exclusion has resolved. Process restart is the only recovery mechanism.

## Key Insight

The non-obvious insight is that **in-memory blacklists designed for one failure cadence become deadlocks under a different cadence.** Both blacklists were reasonable engineering:

- `_recently_closed` prevents tab thrashing: a game page that returned 0 odds three times in a row should not be immediately reopened (wastes Chrome resources)
- `_failed_fixtures` prevents wasted wizard calls: a fixture whose wizard fetch failed should not be retried every 30 seconds (wastes API budget)

Both work correctly when the failure is **permanent** (game completed, market closed). Both become deadlocks when the failure is **transient** (CDN cache stale, session expired, rate limited, wizard returning post-game body for a still-active fixture):

| Blacklist | Designed For | Breaks Under | Impact |
|-----------|-------------|-------------|--------|
| `_recently_closed` | Game ended → don't reopen | Transient API failure → game can never be scraped again | 0 odds for affected games until restart |
| `_failed_fixtures` | Wizard empty → don't retry | CDN/session transient → fixture permanently skipped | 22h stale data across entire sport |

The MLB blacklist was discovered first (May 2) but the NBA blacklist went undetected for another 23 days because NBA's failure cadence was different — NBA only exposed the bug during playoffs when fixture_ids recur across days. Both required process restart as the only recovery.

## The General Pattern

Any in-memory data structure that:
1. Adds items on failure
2. Never removes items (no TTL, no reconciliation, no external verification)
3. Gates a critical operation (skip scraping, skip writing, skip evaluation)

...will eventually deadlock when a transient failure adds an item that should have been retried. The defense is always one of:
- **TTL-based expiry** (items automatically removed after N hours)
- **External reconciliation** (periodically verify against the source of truth)
- **State classification** (distinguish transient from permanent failures, only permanently blacklist permanent failures)

The NBA fix deployed all three: a tri-state classifier (transient vs permanent), a 6h TTL expiry, and a success-marker that removes items on recovery. This is the correct defense-in-depth approach — any single mechanism would suffice, but all three together prevent the class of bug entirely.

## Evidence

**NBA `_failed_fixtures` (2026-05-25):** Event `25786418` failed wizard fetch at 13:06 (26k post-game body) → added to `_failed_fixtures` → discovery found the game every 30 min but `add_game()` silently returned → 22.7 hours stale → restart cleared the set → same event_id returned 320k/440 PAs immediately. The failure was at DEBUG log level, invisible in production.

**MLB `_recently_closed` (2026-05-02):** 3-strike close on 0-record responses (from login wall or CDN issues) → game added to `_recently_closed` → rediscovery skipped the game → 0 MLB odds until restart → 1,000+ picks immediately resumed after cache cleared. The failure looked like "MLB has no games" rather than "MLB games are blacklisted."

Both failures share the diagnostic signature: **the system appears healthy (processes running, discovery cycling) but produces zero data for specific games or sports.** The blacklist is only visible by inspecting the in-memory set or correlating discovery logs with data output.

## Related Concepts

- [[concepts/bet365-nba-fixture-permanent-blacklist-bug]] - The NBA fixture blacklist with 22h stale data; fixed with tri-state classifier + 6h TTL
- [[concepts/mlb-v3-recently-closed-cache-deadlock]] - The MLB recently-closed cache that blocked 1,000+ picks until restart
- [[concepts/stale-in-memory-import-writer-leak]] - A related in-memory state bug: Python's `sys.modules` cache retains old code indefinitely after SCP deploy, producing stale output from a running process
- [[connections/stale-process-state-phantom-liveness]] - Both blacklist bugs produce phantom-liveness: the process appears healthy while producing zero useful output due to corrupted internal state
- [[concepts/tracker-optimistic-id-poisoning]] - Another in-memory state pollution bug: `_tracked_ids.add()` before confirmed INSERT poisons the tracking set permanently

## Sources

- [[daily/lcash/2026-05-25.md]] - NBA `_failed_fixtures` permanent blacklist killed NBA for 22.7h; same event_id worked after restart; fix: tri-state classifier + 6h TTL + success marker (Sessions 08:59, 10:48)
- [[daily/lcash/2026-05-02.md]] - MLB `_recently_closed` cache deadlock from 3-strike close + no expiry; restart cleared cache → 1,000+ picks resumed (Sessions 12:48, 15:23)
