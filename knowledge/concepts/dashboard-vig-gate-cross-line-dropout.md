---
title: "Dashboard Vig Sanity Gate Cross-Line Market Dropout"
aliases: [vig-gate-dropout, cross-line-mismatch, computeEVForTheory-dropout, line-not-in-key, mlb-zero-picks-display, candidate-blend-theories]
tags: [value-betting, dashboard, bug, architecture, devig, data-quality]
sources:
  - "daily/lcash/2026-05-11.md"
  - "daily/lcash/2026-05-12.md"
created: 2026-05-11
updated: 2026-05-12
---

# Dashboard Vig Sanity Gate Cross-Line Market Dropout

On 2026-05-11, the V3 dashboard showed 0 MLB picks despite the server-side `/v1/picks?sport=mlb` endpoint returning 9,522 picks (7,459 above 5% EV). The root cause was `computeEVForTheory()` dropping all 10,491 MLB markets client-side due to a vig sanity gate that rejects markets where the soft book's line differs from the sharp consensus line. Since `market_key` does not include `line`, Bet365 at line 0.5 and sharps at line 1.5 are grouped in the same market key — the vig gate sees mismatched lines within a single key and drops the market. Additionally, only 2-3 of 7 MLB theories run client-side devig; the other 5 are `candidate-blend` theories that execute server-side only and are invisible to the dashboard's `computeEVForTheory()`.

## Key Points

- Server-side picks endpoint returned **9,522 MLB picks** (7,459 above 5%), but dashboard rendered **0** — the disconnect is entirely in the client-side EV computation path
- Root cause: vig sanity gate (commits `0de77c5`, `632627a`, `a560ef9`) rejects markets where soft book line differs from sharp consensus line within the same `market_key`
- `market_key` does not include `line`, so Bet365 at L=0.5 and sharps at L=1.5 coexist in the same key — the devig call sees incompatible lines and drops the market
- **5 of 7 MLB theories are `candidate-blend`** (server-side only, not client-side devig) — the dashboard's `computeEVForTheory()` only evaluates 2-3 traditional theories
- Diagnosed via pipeline health tracing: Eve healthy (12k markets, 2d+ uptime) → VPS healthy (`mini_pc_ok=true`) → SSE flowing (61s to Live) → server picks exist (9,522) → client drops all markets
- Three hypotheses to test: (1) vig gate cross-line mismatch, (2) `findPair(m.market_key)` returning null from naming changes, (3) `softStale` dropping >5s old data

## Details

### The Line-Not-In-Key Design Flaw

The scanner's `market_key` is derived from `(player, prop_type, side)` — it does not include the `line` value. This design was intentional: different sportsbooks may offer the same logical market at slightly different lines (e.g., Points Over 25.5 at one book, Over 26.5 at another), and the system needs to group these for cross-book comparison. The `line` value lives at the per-book level inside `BookOdds`, not at the market level.

This design previously caused the `matched-market-line-null-bug` (see [[concepts/matched-market-line-null-bug]]) where `MatchedMarket.to_dict()` had no top-level `line` field, breaking pick creation. The vig gate bug is a second manifestation of the same architectural decision: when Bet365 offers a player prop at line 0.5 (threshold market format) and the sharp books (Pinnacle, DraftKings) offer the same stat at line 1.5, both entries appear under the same `market_key`. The vig sanity gate — designed to catch devig anomalies — sees the line mismatch and interprets it as a data quality issue, dropping the market.

The specific data example from the investigation: Maikel Garcia Hits Over — Bet365 at L=0.5 while sharps at L=1.5 in the same market key. This is a legitimate cross-line comparison that the interpolation engine handles correctly on the server side, but the client-side vig gate rejects it.

### The Vig Sanity Gate

The vig sanity gate was introduced in three commits (`0de77c5`, `632627a`, `a560ef9`) as a defensive measure to prevent the dashboard from displaying picks with obviously incorrect devig calculations — a response to the repeated phantom EV bugs documented in [[concepts/alt-line-mismatch-poisoned-picks]], [[concepts/soccer-three-way-devig-phantom-ev]], and [[connections/devig-method-market-structure-mismatch]]. The gate performs a sanity check after devigging: if the computed true probability or the input line values appear inconsistent, the market is dropped from the display.

The problem is that the gate is too aggressive: it treats legitimate cross-line markets (Bet365 threshold at 0.5 vs sharp main line at 1.5) as anomalies. On the server side, the tracker handles this through Poisson interpolation and the `max_line_gap` theory parameter. The client-side vig gate has no equivalent interpolation awareness — it sees "lines don't match" and drops.

### Candidate-Blend Theory Architecture

A secondary finding from the same investigation: 5 of 7 active MLB theories use `candidate-blend` mode — a server-side-only devig approach where the EV engine blends odds from multiple candidate books rather than running traditional Over/Under pair devig. These theories produce picks on the server's `/v1/picks` endpoint but are never evaluated by the dashboard's `computeEVForTheory()` JavaScript function, which only handles traditional devig theories.

This means even if the vig gate were fixed, the dashboard would only show picks from 2-3 of 7 MLB theories. The `candidate-blend` picks are available via the stored-picks path (Supabase query for `triggered_by` matching) but not via live client-side computation. This is architecturally similar to the Pinnacle virtual pill rendering pattern documented in [[concepts/pinnacle-prediction-market-pipeline]], where niche league picks are server-tracked-only rather than client-computed.

### Health Pill and Context-Aware Empty States

The investigation prompted deployment of two dashboard UX improvements:

**4-segment health pill** (`● VPS ● Eve ● mkts ● picks`): A persistent color-coded indicator showing per-layer health status — green for healthy, yellow for degraded, red for down. Each segment maps to a specific pipeline component, enabling immediate visual diagnosis of which layer is failing. This was committed as `35d8bfe`.

**Context-aware empty-state messages**: Previously, every empty state showed the same generic "Waiting for soft book + sharp book data" message, whether the cause was SSE disconnection, data loading, Eve being down, or the vig gate dropping all markets. After the fix, each failure mode shows a distinct message: "Loading data from Eve..." (first load), "VPS not reachable" (proxy failure), "Eve is offline" (mini PC down), or "No picks match current filters" (vig gate or legitimate market efficiency). Committed as `7e53b6b`.

### Diagnostic Methodology

The investigation established a systematic diagnostic order for "0 picks on dashboard":

1. **Eve health**: Check `/v1/health` — uptime, markets count, pulse counter, RSS memory
2. **VPS proxy**: Check `/api/v1/health` — `mini_pc_ok`, `mini_pc_markets`, proxy latency
3. **SSE chain**: Browser console → SSE connection status, time-to-Live state
4. **Server-side picks**: `curl /v1/picks?sport=mlb` — if non-zero, the bug is client-side
5. **Client-side dropout**: Browser console `[EV] dropout` log from `computeEVForTheory` (line ~2370) reveals which gate kills markets
6. **Theory compatibility**: Check how many theories are `candidate-blend` (server-only) vs traditional (client-evaluable)

Steps 1-4 all passed cleanly on 2026-05-11. The failure was isolated to step 5 (vig gate dropping all markets) compounded by step 6 (most theories not evaluable client-side).

### VB-V3-Healthcheck Skill

The investigation led to creation of a `/VB-V3-Healthcheck` Claude Code skill with three operating modes:

- **Full sweep**: Checks Eve scraper, Tailscale link, VPS proxy, dashboard SPA routes, cache performance, and recent fix markers
- **Quick**: Eve + VPS status only — 30-second check
- **Cache-only**: Tests `/api/v1/odds` response time and single-flight dedup behavior

This follows the self-evolving operational skill pattern documented in [[concepts/self-evolving-operational-skill]], specialized for the V3 architecture's specific health check surface.

### Vig Gate as Contributing Factor, Not Primary Cause (2026-05-12)

On 2026-05-12, the vig gate was confirmed as a **contributing factor but not the primary cause** of the 0-pick issue. The dominant cause was stale `game_start` dates from a market_key cross-day collision bug — 93% of markets were filtered by `isGameLive()` before the vig gate could even evaluate them. The vig gate commits (0de77c5, 632627a, a560ef9) were initially suspected as the root cause but turned out to be a red herring. See [[concepts/market-key-cross-day-game-start-staleness]] for the actual root cause.

## Related Concepts

- [[concepts/matched-market-line-null-bug]] - First manifestation of the `line`-not-in-key design: MatchedMarket had no top-level `line`, breaking pick creation. This bug is the second manifestation: cross-line markets grouped under one key are rejected by the vig gate
- [[concepts/dashboard-client-server-ev-divergence]] - The 11th documented manifestation of dashboard-vs-server divergence; previous instances include loadTheories field dropping, theory name exclusion, 6-dimension computation drift, computeTrueProb math bug, team name mapping, data.json staleness
- [[concepts/alt-line-mismatch-poisoned-picks]] - The phantom EV bugs that motivated creating the vig sanity gate; the gate was a defensive measure against interpolation noise but is now too aggressive for legitimate cross-line markets
- [[concepts/v3-dashboard-ev-computation-architecture]] - The V3 live EV computation architecture where this bug manifests; the vig gate operates within the client-side `computeEVForTheory()` function
- [[concepts/pinnacle-prediction-market-pipeline]] - The Pinnacle virtual pill rendering pattern where server-tracked picks bypass client computation — architecturally analogous to how `candidate-blend` theories are invisible to the dashboard
- [[concepts/self-evolving-operational-skill]] - The /checkup skill pattern; the new /VB-V3-Healthcheck skill is a V3-specific instance with full/quick/cache modes
- [[concepts/worker-status-observability]] - The health pill addresses the "false healthy" status pattern by exposing per-layer health at the UI level

## Sources

- [[daily/lcash/2026-05-11.md]] - Full pipeline health confirmed healthy (Eve 2d14h uptime, 12k markets, VPS mini_pc_ok=true); server `/v1/picks?sport=mlb` returns 9,522 picks but dashboard shows 0; root cause: vig sanity gate commits (0de77c5, 632627a, a560ef9) reject cross-line markets where Bet365 L=0.5 vs sharps L=1.5 in same market_key; 5/7 MLB theories are candidate-blend (server-only); 4-segment health pill deployed (35d8bfe); context-aware empty states deployed (7e53b6b); URL/SSE sport routing fixed; /VB-V3-Healthcheck skill created with full/quick/cache modes (Sessions 08:49, 08:50, 09:42)
- [[daily/lcash/2026-05-12.md]] - Vig gate confirmed as contributing factor but not primary cause of 0-pick issue; dominant cause was stale game_start dates from market_key cross-day collision — 93% of markets filtered by isGameLive() before vig gate evaluation; vig gate commits (0de77c5, 632627a, a560ef9) were a red herring
