---
title: "V3 Dashboard Live EV Computation Architecture"
aliases: [v3-dashboard, live-picks-computation, mini-pc-devig-endpoint, memoization-poisoning, sse-staleness-mismatch]
tags: [value-betting, dashboard, architecture, devig, v3, performance]
sources:
  - "daily/lcash/2026-05-06.md"
  - "daily/lcash/2026-05-09.md"
  - "daily/lcash/2026-05-11.md"
  - "daily/lcash/2026-05-12.md"
created: 2026-05-06
updated: 2026-05-12
---

# V3 Dashboard Live EV Computation Architecture

The V3 dashboard computes EV picks live from mini PC odds — not from Supabase stored picks. The mini PC runs a DeVig engine against active theories on every `/v1/picks?sport=nba|mlb` request, and the VPS proxies this endpoint to the dashboard. On 2026-05-06, three critical bugs were discovered and fixed during deployment: a case-sensitivity mismatch on sharp book names (`"Pinnacle"` vs `"pinnacle"`), a memoization cache poisoned by stale data, and an SSE staleness threshold fundamentally incompatible with SSE's change-only timestamp semantics.

## Key Points

- **Architecture**: Mini PC computes picks (DataStore markets → DeVig engine → theory filter), VPS proxies, zero Supabase reads for live picks
- **Case sensitivity killer**: `SHARP_BOOKS` list used titlecase (`"Pinnacle"`) while OpticOdds delivers lowercase (`"pinnacle"`) → `_find_sharp_books()` returned empty → zero EV for every market → 0 picks. Fixed with `.lower()` normalization on both sides
- **Memoization poisoning**: Cache primed with 0 picks, cache key used `pulse` counter (server always returns `0`), cache never invalidated → UI permanently stuck. Fixed by using market count as cache key instead of pulse
- **SSE staleness mismatch**: V3 uses OpticOdds SSE which only timestamps on odds *changes*; `MAX_ODDS_AGE_S=600` rejected stable sharp lines untouched for 10+ min. Fixed by increasing to 7200s (2 hours) — correct for SSE architecture where stable = no update, not stale
- **"Default" theory fallback**: When no active `is_active=true` theory rows exist in `nba_optimization_runs`, a Default theory with generic parameters is used
- **Event loop blocking from logging**: Scanner logging `INFO` for every market calc (3000 markets × 6 theories = 162K log lines per request) blocked the asyncio event loop; health endpoint took 39s. Fixed by raising logger level

## Details

### Live Computation vs Stored Picks

The V3 architecture is fundamentally different from V2's dashboard data flow:

| Dimension | V2 | V3 |
|-----------|-----|-----|
| Pick source | Supabase `nba_tracked_picks` table | Mini PC `/v1/picks` computed live |
| Computation location | VPS tracker (5-second polling) | Mini PC DeVig engine (on-request) |
| Data freshness | Last tracker cycle (up to 5s stale) | Real-time against current markets |
| Theory changes | 5-minute TTL refresh | Loaded once at startup |
| Supabase dependency | Required for all pick display | Zero reads for live picks |

The user explicitly corrected the initial architecture: "VPS should ping mini PC API to compute picks live through theories, never read from Supabase picks directly." This means the VPS is a pure proxy — it forwards the dashboard's pick requests to the mini PC and serves the responses.

### Case Sensitivity Bug

The DeVig engine's `_find_sharp_books()` function compared book identifiers from the market data against a configured `SHARP_BOOKS` list. OpticOdds delivers book names in all-lowercase (`"pinnacle"`, `"draftkings"`, `"fanduel"`), but `SHARP_BOOKS` was configured with titlecase (`"Pinnacle"`, `"DraftKings"`, `"FanDuel"`). Since Python string comparison is case-sensitive by default, every sharp book lookup returned empty → no true odds could be computed → every market showed 0 EV → 0 picks.

This is the same class of silent case-sensitivity bug documented in [[connections/silent-type-coercion-data-corruption]] and [[connections/dual-codebase-ev-computation-drift]] (dimension 6: `is_over` case sensitivity). The fix normalizes both sides to lowercase before comparison.

### Memoization Cache Poisoning

The dashboard implemented a memoization cache to avoid recomputing the same picks repeatedly during the 5-second poll interval. The cache key was the server's `pulse` counter. However, the V3 server always returned `pulse=0` (the pulse feature wasn't implemented), so the cache key never changed. Once the cache was primed with the initial result (0 picks due to the case-sensitivity bug), every subsequent request returned the cached 0 picks — even after the case-sensitivity fix was deployed.

The fix changed the cache key from `pulse` to market count — a value that actually changes when new data arrives, ensuring cache invalidation on meaningful data updates.

### SSE Staleness Semantics

V3 ingests sharp book data from OpticOdds via SSE (Server-Sent Events), which only sends updates when odds change. This means `captured_at` reflects the last *change* time, not the last *observation* time. A sharp book line that was set 2 hours ago and hasn't moved (e.g., Pinnacle NBA player props set well before game time) has a `captured_at` of 2 hours ago — but the line is still valid and current.

The `MAX_ODDS_AGE_S=600` threshold (from V2's polling architecture) rejected these stable lines as "stale," even though they were the most accurate available data. The fix increased the threshold to 7200 seconds (2 hours), which is appropriate for SSE's change-only semantics where "no update" means "no change" rather than "data is stale."

This is a permanent architectural difference between SSE-based and polling-based ingestion that affects any age-gated filter in the codebase.

### Dashboard Visual Alignment

The V3 dashboard went through extensive iteration to match the V2 visual design. Key differences identified through multiple screenshot comparisons:

- Background: V2 uses `#060609` (near-black), not V2's dark blue `#0f172a`
- Stat cards: V2 uses 4px **left** border (colored accent stripe), not top border
- Primary accent: V2 uses `#00ff88` (neon green), not muted emerald
- Header: "Value Betting" title with "Advanced EV Detection System · lcash" subtitle, pulsing live dot inline
- Table columns: `PLAYER | PROP | LINE | BOOK | EV% | TRUE PROB | THEORY | SHARPS` — no GAME column

### Sport Routing Bug and Thin Trail Data (2026-05-09)

On 2026-05-09, two additional dashboard issues were discovered:

**Sport routing bug:** Non-localhost paths hardcoded `currentSport = 'nba'`, meaning navigating to `/mlb` loaded the MLB page layout but fetched NBA data. The fix reads `window.location.pathname` and matches against `SPORT_INSTANCES` to determine the active sport. This affected all non-NBA sport pages on the VPS dashboard.

**Thin trail data empty state:** ~5% of picks have only a single trail snapshot (timestamp span < 30 seconds). The trail chart rendered these as a near-empty canvas with a single dot, which looked like a broken feature. The fix detects thin data and shows an explainer message instead of the chart. This edge case was particularly confusing during debugging because the first several picks tested all had single snapshots, creating a false impression of systemic failure.

Additionally, the VPS proxy's `/api/v1/odds` endpoint was causing 21-second timeouts from re-serializing 8.7 MB payloads. A byte-level cache with 2s TTL reduced this to 97ms. See [[concepts/vps-proxy-byte-cache-optimization]] for the full pattern.

## Related Concepts

- [[concepts/v3-scanner-centralized-architecture]] - The V3 query-response architecture where the mini PC serves `/v1/picks`; this article documents the dashboard consumption layer
- [[concepts/opticodds-sse-reconnect-state-loss]] - SSE reconnect state loss is a related SSE architectural issue; both articles highlight that SSE-based ingestion has fundamentally different freshness semantics than polling
- [[concepts/dashboard-client-server-ev-divergence]] - The V2 dashboard's EV divergence chronicle; V3 eliminates the dual-codebase problem by computing server-side only, but introduces new bugs (case sensitivity, memoization, SSE staleness)
- [[connections/silent-type-coercion-data-corruption]] - Case-sensitive book name comparison producing zero output is another instance of the plausible-wrong-output pattern
- [[connections/dual-codebase-ev-computation-drift]] - V3 eliminates the dual-codebase EV drift by computing in one place (mini PC Python); the case-sensitivity bug is a configuration drift, not algorithmic drift
- [[concepts/vps-proxy-byte-cache-optimization]] - VPS proxy byte cache deployed on 2026-05-09 alongside the sport routing fix; addresses the 21s→97ms proxy latency
- [[concepts/dashboard-sport-scoped-sse-routing]] - Sport-scoped SSE and pathname routing fixes deployed on 2026-05-09
- [[concepts/dashboard-vig-gate-cross-line-dropout]] - Vig sanity gate dropping all MLB markets because line-not-in-key causes cross-line mismatch; 5/7 theories are candidate-blend (server-only)

### Vig Sanity Gate and Candidate-Blend Theories (2026-05-11)

On 2026-05-11, the V3 dashboard showed 0 MLB picks despite the server returning 9,522. Two compounding causes:

1. **Vig sanity gate**: Commits `0de77c5`, `632627a`, `a560ef9` added a defensive check that rejects markets where the devig inputs have incompatible lines. Since `market_key` doesn't include `line`, Bet365's threshold props (L=0.5) and sharps' main lines (L=1.5) are grouped together and then rejected by the gate.

2. **Candidate-blend theories invisible client-side**: 5 of 7 MLB theories use `candidate-blend` mode — a server-side-only EV computation that blends odds from multiple candidate books. The dashboard's `computeEVForTheory()` only handles traditional Over/Under pair devig and never evaluates candidate-blend theories. Even fixing the vig gate would only surface picks from 2-3 theories.

A **4-segment health pill** (`● VPS ● Eve ● mkts ● picks`) was deployed (commit `35d8bfe`) showing per-layer color-coded status. **Context-aware empty states** (commit `7e53b6b`) replaced the generic "Waiting for data" message with specific diagnostics: loading, VPS down, Eve offline, or no picks matching filters.

The URL/SSE routing fix from 2026-05-09 was verified working: `switchSport()` now updates URL slug, resets markets, reconnects SSE with `?sport=` param, and supports `popstate` for browser back/forward navigation.

### Coverage Dashboard, Game Start Staleness Fix, and Bet365 Gaps (2026-05-12)

On 2026-05-12, several discoveries and fixes were made:

**Coverage dashboard**: A coverage dashboard was built on Eve at `/dashboard/coverage.html`, providing visibility into scraper coverage per book.

**game_start staleness fix**: `server/state.py:285-290` was updated with chronological refresh logic — `game_start` is now always updated to the latest value rather than being frozen on first observation. Additionally, `cleanup_stale_markets()` was wired into v3's `startup.py` to periodically purge markets with outdated game_start dates. Previously, `cleanup_stale_markets()` existed but was never called from v3's startup path.

**Bet365 coverage gap**: The coverage dashboard revealed Bet365 at 59.7% coverage while Pinnacle was at only ~2% — a major gap. 13 missing Bet365 NBA markets were identified in the wizard but not present in `EV_NAME_MAP`, meaning those markets were scraped but never matched for EV computation.

**`_bet365_push_loop` captured_at overwrite bug**: The Bet365 push loop stamps `time.time()` every 5 seconds regardless of actual data refresh, making all Bet365 data appear 5 seconds old even when the underlying odds haven't changed. This masks actual data staleness.

## Sources

- [[daily/lcash/2026-05-06.md]] - Case sensitivity: `"Pinnacle"` vs `"pinnacle"` returned 0 sharp books → 0 picks; fixed with `.lower()` normalization. Memoization: `pulse=0` constant as cache key → cache never invalidated; fixed with market count key. SSE staleness: `MAX_ODDS_AGE_S=600` rejected stable lines; fixed to 7200s for SSE semantics (Session 14:26). Event loop blocking: 3000×6 theory matrix = 162K log lines per request; raised logger level, ping dropped to 42ms (Session 01:56). Architecture: mini PC computes picks, VPS proxies, zero Supabase reads; 5s auto-refresh with stale-data preservation (Session 00:20). Dashboard visual alignment: multiple iteration passes matching V2 design tokens (Sessions 01:07, 01:08)
- [[daily/lcash/2026-05-09.md]] - Sport routing bug: `currentSport = 'nba'` hardcoded for non-localhost; fix: read `window.location.pathname` against `SPORT_INSTANCES`. Thin trail data: ~5% of picks with single snapshot; show explainer when span < 30s. VPS proxy byte cache: 21s→97ms (200×). Browser fetch queue contention delayed trail fetch 20+ seconds (Sessions 11:15, 13:30)
- [[daily/lcash/2026-05-11.md]] - Vig sanity gate dropping all 10,491 MLB markets client-side while server returns 9,522 picks; Bet365 L=0.5 vs sharps L=1.5 in same market_key; 5/7 MLB theories are candidate-blend (server-only); 4-segment health pill (35d8bfe) + context-aware empty states (7e53b6b) deployed; URL/SSE switchSport verified with popstate support (Sessions 08:49, 08:50, 09:42)
- [[daily/lcash/2026-05-12.md]] - Coverage dashboard built on Eve at /dashboard/coverage.html; game_start staleness fix in server/state.py:285-290 with chronological refresh + cleanup_stale_markets() wired in startup.py; Bet365 coverage 59.7% vs Pinnacle ~2%; _bet365_push_loop captured_at overwrite bug (stamps time.time() every 5s); 13 missing bet365 NBA markets in wizard but not in EV_NAME_MAP
