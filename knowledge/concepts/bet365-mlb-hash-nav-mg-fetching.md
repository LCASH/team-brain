---
title: "bet365 MLB Hash-Nav Market Group Fetching"
aliases: [hash-nav-mg, mlb-g-id, direct-url-i0, bet365-mg-discovery, partial-hashnav, sub-tab-architecture]
tags: [bet365, mlb, scraping, reverse-engineering, architecture, value-betting]
sources:
  - "daily/lcash/2026-04-29.md"
created: 2026-04-29
updated: 2026-04-29
---

# bet365 MLB Hash-Nav Market Group Fetching

On 2026-04-29, lcash discovered two major URL navigation shortcuts for the bet365 MLB prop scraper. First, the `/I0/` URL suffix enables direct game page loading without SPA boot or team-click navigation (~15s→instant). Second, deterministic hash-nav URLs (`/AC/B16/{league}/D19/E{event}/{tab}/G{gid}/S^1/`) trigger SPA partial responses for specific market groups — enabling fetching of all 25 MLB market groups per game via URL manipulation instead of DOM clicks. This replaces the click-expand architecture with a deterministic, URL-driven fetcher that produces ~1.3s/fetch with no DOM interaction needed.

## Key Points

- **`/I0/` suffix** in bet365 game URLs specifies the active tab — without it, SPA doesn't load game content; with it, direct `page.goto(url)` works like NBA's Bet Builder approach
- **Hash-nav pattern**: `/AC/B16/{league}/D19/E{event}/{tab}/G{gid}/S^1/` triggers SPA partial HTTP responses containing market group data — no clicks needed
- **25 market groups** brute-forced by G-id: 24 use `partial_hashnav` strategy, 1 (Pitcher Strikeouts CO milestone, G163122) requires `tab_root_coupon` as it's the default I5 view
- **`S^1` URL segment** is critical — triggers SPA partial rendering; without it, the SPA doesn't fire HTTP requests for the market group data
- WS streaming **definitively ruled out** for pre-game player props: zero prop participant matches across 700+ WS frames tested on three surfaces (NBA per-game, MLB per-game, MLB games-list sub-tabs)
- **Games-list sub-tabs** cover only 4 of 25 market types (Hits, Pitcher K's, HR, Total Bases) + 2 alt lines — useful as supplementary bulk fetch but cannot replace per-game depth
- **RBIs name mismatch**: bet365 renamed "Runs Batted In" → "RBIs" — production had been silently dropping ~109 RBI records per game until map patch

## Details

### The `/I0/` Direct Navigation Discovery

The MLB scraper previously required a multi-step SPA boot sequence to load game pages: navigate to the games list → wait for sidebar render → click team name → wait for game page load → click props tab. This took ~15-30 seconds per game. On 2026-04-29, the user hypothesized that direct URL navigation with the `/I0/` tab suffix would work — and testing confirmed it: a single `page.goto(game_url_with_I0)` loaded the game page with full prop content (22 market groups, 106 participant entries).

The `/I0/` suffix tells the bet365 SPA which tab to render by default. Without it, the SPA loads the game page structure but doesn't populate the prop content area. This mirrors the NBA scraper's Bet Builder direct URL approach — both sports' prop data can be loaded by specifying the correct tab identifier in the URL.

This discovery eliminated the need for the games-list-boot + team-click flow, reducing per-game setup from ~15s to the time of a single page navigation (~3-5s). Combined with the hash-nav MG fetching below, the entire MLB scraper architecture was simplified from DOM-interaction-heavy to URL-manipulation-only.

### Hash-Nav Market Group Architecture

Each of bet365's 25 MLB market groups (MGs) has a unique G-id that can be targeted via hash navigation. The URL pattern is:

```
/AC/B16/{league_id}/D19/E{event_id}/{tab_code}/G{g_id}/S^1/
```

Where:
- `B16` = Baseball sport code
- `D19` = Market display context
- `E{event_id}` = Specific game (e.g., `E25587341`)
- `{tab_code}` = I0 (main), I2 (batter props), I5 (pitcher props)
- `G{g_id}` = Specific market group
- `S^1` = Critical trigger for SPA partial rendering

Navigating to this URL via `window.location.hash` triggers the SPA to fire an HTTP partial response containing only the targeted market group's data. This is dramatically more efficient than the click-expand approach (which required clicking each MG header in the DOM and waiting for expansion animation + data load).

### Market Group Discovery

All 25 MG G-ids were discovered through brute-force probing. The MGs cover the complete MLB prop surface:

**Batter props (I2 tab):** Hits, Total Bases, RBIs, Home Runs, Runs, Stolen Bases, Doubles, Walks, and their CO milestone variants (e.g., "20+ Points" threshold format)

**Pitcher props (I5 tab):** Strikeouts, Earned Runs, Pitcher Hits Allowed, Pitcher to Record First Strikeout (named-option format), and their CO milestone variants

**Game-level (I0 tab):** Alt Game Total, Alt Run Line, and other game-level markets

24 of 25 MGs respond to the `partial_hashnav` strategy. The exception is Pitcher Strikeouts CO milestone (G163122), which is the default I5 tab view — the SPA serves it inline in the tab root coupon response rather than as a separate partial. This single MG uses a `tab_root_coupon` fetch strategy where the I5 tab URL itself returns the data.

### Games-List Sub-Tab Analysis

Before arriving at the per-game hash-nav architecture, lcash tested a games-list sub-tab approach — clicking Hits/HR/Strikeouts/etc. sub-tabs on the MLB games-list page to capture data for all games simultaneously. This approach was partially viable: sub-tabs fetch data in ~7 HTTP calls (vs ~225 per-game calls). However, only 4 of 25 market types exist on the games-list surface (Hits, Pitcher K's, HR, Total Bases) plus 2 alt line types (Alt Game Total, Alt Run Line).

The remaining 19 market types — including RBIs, Runs, Stolen Bases, Doubles, Earned Runs, and all CO milestone variants — are only available on per-game tabs. Since many edges exist in these deeper markets (CO milestones represent threshold-style props where Poisson interpolation finds value), the sub-tab-only architecture was abandoned as incomplete. The final architecture uses per-game hash-nav for full prop coverage, with games-list sub-tabs as an optional supplementary bulk fetch for alt lines.

### bet365 CDN Caching Behavior

bet365's CDN caching is extremely sticky — identical 32,241-byte responses were observed 30 minutes apart on the same endpoint. This means the effective refresh rate for MLB props is limited by bet365's cache TTL, not the scraper's polling interval. The bet365 UI itself polls HTTP autonomously every ~6-7 seconds when idle on a game tab, with most responses being tiny "no-change" 57-byte payloads. Only when the CDN cache invalidates does a fresh full response arrive.

### RBIs Name Mismatch

During hash-nav probing, lcash discovered that bet365 renamed the market group from "Runs Batted In" to "RBIs" in their API responses. The production scraper's market name mapping had the old name, silently dropping ~109 RBI records per game. This is a recurring pattern in the scanner: data format changes at the source that silently drop data without errors (see [[connections/silent-type-coercion-data-corruption]]).

### WS Streaming Definitively Ruled Out

Three separate WebSocket probing tests confirmed that bet365 does NOT expose pre-game player props via WS:

1. NBA per-game: zero prop participant matches in WS frames
2. MLB per-game: zero prop participant matches
3. MLB games-list Hits sub-tab: zero prop participant matches across 700+ frames total

WS carries only in-play/live market data. Pre-game prop odds update via HTTP polling — the bet365 UI does the same thing. This definitively confirms the HTTP-only architecture documented in [[connections/ws-viability-sport-rendering-divergence]].

## Related Concepts

- [[concepts/spa-navigation-state-api-access]] - The `/I0/` suffix discovery extends the SPA navigation patterns; hash-nav adds a new URL-manipulation technique beyond the navigate-away trick
- [[concepts/bet365-mlb-batch-api-co-format]] - The batch API's MG→MA→CO→PA segment format is what the hash-nav fetcher captures; hash-nav provides a more efficient way to trigger these responses than DOM clicks
- [[concepts/bet365-mlb-lazy-subscribe-migration]] - The MLB scraper evolution: v1 BB wizard → v2 lazy-subscribe → v3 hybrid → v4 batch API → v5 hash-nav MG fetching (this article represents the latest architectural milestone)
- [[concepts/mlb-parallel-scraper-workers]] - The MLB scraper's per-game architecture that hash-nav MG fetching enhances; direct URL nav eliminates the SPA boot bottleneck
- [[connections/anti-scraping-driven-architecture]] - `fetch()` via `Runtime.evaluate` returns 200-but-empty (bet365 validates request context); must use `page.goto()` + response capture. The hash-nav approach works because it triggers the SPA's own HTTP requests, not programmatic fetch calls
- [[connections/ws-viability-sport-rendering-divergence]] - WS streaming confirmed non-viable for pre-game props on all three tested surfaces; HTTP polling is the permanent architecture

## Sources

- [[daily/lcash/2026-04-29.md]] - `/I0/` direct URL navigation tested and confirmed: 22 MGs, 106 PAs loaded directly; user challenged assumption → tested → worked (Session 10:29). In-play detection: pages with 0 odds (live games) detected and closed immediately; event_id length filter doesn't work for MLB (8-digit IDs vs NBA 10+) (Sessions 10:29, 10:59). Hash-nav MG discovery: `/AC/B16/{league}/D19/E{event}/{tab}/G{gid}/S^1/` triggers SPA partials; 25 MGs brute-forced; G163122 Pitcher K's CO uses tab_root_coupon; `S^1` critical for triggering partials (Session 18:02). Games-list sub-tabs: only 4/25 MG types available (Hits, K's, HR, Total Bases); per-game hash-nav needed for full coverage; two formats per stat (CO milestones vs O/U) (Session 16:07). RBIs name mismatch: "Runs Batted In" → "RBIs" silently dropping ~109 records/game (Session 18:02). WS definitively ruled out: zero prop matches across 700+ frames on three surfaces; bet365 UI polls HTTP at ~6-7s; CDN cache very sticky (32,241-byte identical responses 30min apart) (Session 16:07)
