---
title: "bet365 NBA Fixture Permanent Blacklist Bug"
aliases: [fixture-blacklist, nba-permanent-ban, failed-fixtures-no-expiry, tri-state-classifier-port, wizard-failure-blacklist]
tags: [value-betting, bet365, nba, scraping, bug, reliability, architecture]
sources:
  - "daily/lcash/2026-05-25.md"
created: 2026-05-25
updated: 2026-05-25
---

# bet365 NBA Fixture Permanent Blacklist Bug

On 2026-05-25, the bet365 NBA scraper was discovered stale for 22+ hours because `ws_nba_v4.py:431-439` permanently blacklists any fixture_id whose wizard fetch fails — with no time-gate, no retry, and no expiry. The MLB scraper (`ws_mlb_v4.py:375-382, 720-805`) already had a tri-state classifier (`pregame_active`, `live_or_completed`, `pregame_unverified`) that only permanently skips post-start-time failures and retries pre-game ones. NBA playoffs uniquely exposed this because the same fixture_id persists across discovery cycles for days (unlike MLB's daily fresh slate). The fix ported MLB's tri-state classifier to NBA AND added a 6-hour TTL auto-expiry on blacklisted fixtures.

## Key Points

- `ws_nba_v4.py:431-439` adds fixture_ids to `_failed_fixtures` set on ANY wizard failure — no time-gate, no retry, no expiry; once blacklisted, a fixture is permanently dead for the process lifetime
- NBA was stale for **22.7 hours** (318 markets with 22.7h-old `captured_at`) while MLB was healthy (9.7 min fresh) — the same event_id that failed at 13:06 captured 320k/440 PAs at 08:49 after restart
- MLB already had a **tri-state classifier**: `pregame_active` (retry on failure), `live_or_completed` (permanently skip), `pregame_unverified` (retry with caution) — pre-game failures are transient and should retry
- NBA playoffs expose this because **same fixture_id recycles across discovery cycles** for days (1-2 games/day), unlike MLB's 10-15 fresh fixture_ids daily where permanent bans are harmless
- The wizard failure at 13:06 was **transient/state-dependent**: bet365 returned a 26k post-game body, but the same event_id returned 320k bytes after restart — the blacklist was the real problem, not the wizard endpoint
- Discovery logs showed `+2 new, -0 removed (slate=0)` every 30 min — `add_game()` was called but silently returned at the blacklist check (logged at DEBUG, invisible in production)
- Fix: tri-state classifier ported to NBA + **6h TTL auto-expiry** on `_failed_fixtures`; five state-transition points wired (skip check, empty body, zero-PA, success marker, TTL expiry)

## Details

### The Failure Mechanism

The NBA V4 scraper's `add_game()` method checks a `_failed_fixtures` set before attempting to fetch wizard data for a fixture. If the fixture_id is in this set, the method returns immediately without making any API call. The fixture is added to `_failed_fixtures` whenever the wizard fetch returns an empty body, zero PAs, or throws an error — regardless of whether the failure is transient (CDN cache, session state, rate limiting) or permanent (game completed, market closed).

For MLB, this "never retry" approach works acceptably because each day brings 10-15 completely new fixture_ids. A fixture blacklisted today is never seen again tomorrow — the ban expires naturally as the fixture_id leaves the discovery slate. For NBA playoffs, the same matchup (e.g., OKC vs Indiana) recurs across multiple games in a series, and bet365 may reuse or increment fixture_ids in a way that the blacklist catches returning fixtures.

The 22-hour outage chain:
1. **13:06 May 24**: Wizard fetch for event `25786418` returned a 26k body (post-game or CDN-cached content) → zero PAs extracted → fixture added to `_failed_fixtures`
2. **Every 30 min afterward**: Discovery found the game, called `add_game()`, which checked `_failed_fixtures`, found the ID, and returned at `logger.debug("Skipping blacklisted fixture")` — invisible at production log level
3. **08:49 May 25**: v3 restarted → `_failed_fixtures` cleared → same event_id returned 320k bytes with 440 PAs → NBA immediately healthy

### Why the Tri-State Classifier Is Necessary

The tri-state classifier distinguishes between failures that should retry and failures that should persist:

| State | Trigger | Behavior | Rationale |
|-------|---------|----------|-----------|
| `pregame_active` | Wizard success with PAs | No special handling | Normal operation |
| `live_or_completed` | Wizard failure AFTER game_start time | Permanently skip | Game over, no more data expected |
| `pregame_unverified` | Wizard failure BEFORE game_start time | Retry on next cycle | Pre-game failures are often transient (CDN, session, rate limit) |

The tri-state alone wouldn't have fixed yesterday's specific failure because the failure occurred when the game appeared "post-game" from the wizard's perspective (26k body suggests summary/completed content). The 6-hour TTL auto-expiry provides the safety net: even if the classifier incorrectly stamps a fixture as `live_or_completed`, the expiry clears it after 6 hours, allowing rediscovery to retry.

### The logger.debug Invisibility Problem

The blacklist skip was logged at `logger.debug` level — invisible in production where the log level is typically INFO or WARNING. For 19+ hours, the discovery log showed `+2 new, -0 removed (slate=0)` every 30 minutes — superficially suggesting discovery was working and games existed. The `add_game()` call was being made, but it returned silently at the blacklist check with no visible trace at INFO level.

This is a general anti-pattern: **safety-critical skip paths should log at INFO or WARNING, not DEBUG.** A silent skip that persists for 22 hours is not a debug-level event — it is an operational degradation that should be visible without changing log levels.

### Five State-Transition Points

The deployed fix wires the tri-state classifier at five points in the NBA scraper:

1. **Skip check** (`add_game` entry): Check `_failed_fixtures` expiry before skipping — if entry is older than 6 hours, remove it and proceed
2. **Empty body branch**: When wizard returns empty/small body, classify based on game_start time (pre-game → `pregame_unverified`, post-game → `live_or_completed`)
3. **Zero-PA branch**: When wizard body parses to 0 PAs, same classification logic
4. **Success marker**: On successful capture (PAs > 0), remove from `_failed_fixtures` if present — self-healing
5. **6h TTL expiry**: Periodic sweep or lazy check removes entries older than `FAILED_FIXTURE_TTL_HOURS=6`

## Related Concepts

- [[concepts/mlb-v3-recently-closed-cache-deadlock]] - The MLB equivalent: `_recently_closed` cache with no expiry creates an unrecoverable stuck state; same class of bug (permanent in-memory blacklist without recovery path)
- [[concepts/v3-startup-login-verification-gap]] - Another "process looks alive but produces zero data" bug; the fixture blacklist produces zero data for specific games while the login gap produces zero data for all games
- [[connections/stale-process-state-phantom-liveness]] - The fixture blacklist is another phantom-liveness variant: discovery reports games found, `add_game` is called, but the blacklist silently prevents any action
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native NBA scraper architecture where the blacklist resides; the tri-state classifier was already present in the MLB orchestrator
- [[concepts/worker-status-observability]] - Discovery reporting "slate=0" when games exist is a status observability failure — the health endpoint showed the scraper as running

## Sources

- [[daily/lcash/2026-05-25.md]] - NBA bet365 318 stale markets (22.7h old) while MLB healthy (9.7 min); root cause: `ws_nba_v4.py:431-439` permanently blacklists fixture_ids with no expiry; MLB has tri-state classifier (pregame_active/live_or_completed/pregame_unverified); same event_id 25786418 failed at 13:06 (26k post-game body) but returned 320k/440 PAs after restart; discovery logs "+2 new, -0 removed (slate=0)" with blacklist skip at DEBUG level; fix: ported tri-state + 6h TTL expiry; 5 state-transition points wired; deployed to Eve PID 2505872 (Sessions 08:59, 10:48)
