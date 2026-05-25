---
title: "bet365 Racing Click-Loop Scanner"
aliases: [click-loop-scanner, bet365-racing-ntj, ws-click-gated-state-machine, racing-click-scan, bet365-racing-v2]
tags: [superwin, bet365, racing, scraping, architecture, websocket]
sources:
  - "daily/lcash/2026-05-21.md"
  - "daily/lcash/2026-05-22.md"
created: 2026-05-21
updated: 2026-05-22
---

# bet365 Racing Click-Loop Scanner

bet365's racing WebSocket is a **click-gated state machine** — the server acknowledges PM subscription topics but returns `EMPTY` for markets not activated by the SPA via a real Playwright `locator.click()`. All programmatic navigation variants (`window.location.hash`, `history.pushState`, `page.goto`, fake anchor clicks, `hashchange` dispatch) silently fail or 403. On 2026-05-21, lcash replaced the broken HTML-scrape approach with a click-loop scanner that clicks each visible Next-To-Jump (NTJ) race via Playwright, captures racecoupon HTTP responses, then piggybacks WS for live odds streaming. Coverage is limited to NTJ (~24 races, ~2h rolling window), which aligns with the scanner's 0.5–180 min pre-jump gate.

## Key Points

- bet365 WS is a **fanout model gated by SPA activation** — you can subscribe to `PM{fid}-{pid}` but get `EMPTY` until the SPA has clicked into that market via a real browser click
- All programmatic navigation variants (hash, pushState, goto, fake clicks, hashchange dispatch) are **silently ignored** — only `locator.click()` triggers the racecoupon API and WS market fan-out
- **No "all meetings" view exists** in bet365 — the NTJ (Next-To-Jump) widget is the only racing list without navigating into a specific meeting first
- NTJ coverage: ~24 races in a ~2h rolling window — sufficient because edge picks fire in the 0.5–180 min pre-jump band
- End-to-end flow: click-scan → racecoupon body capture → WS odds streaming → VPS push → catalogue merge; 14 bet365 races matched with 5-bookie odds on first deployment
- First click in the loop often misses (cold-start timing) — needs warm-up click or retry
- **Place odds** stream via separate participant IDs per horse — Win pid has `FW`, Place pid has `FP`; racecoupon body is the snapshot source (WS `FP` field is actually win fractional, not place)
- `sync_term` (1192 chars) rotates every ~45s — needs fresh capture for any subscription attempt

## Details

### Why Click-Loop Was Necessary

The prior HTML-scrape approach (`_scan_venue`) used programmatic navigation to reach race pages and parse the DOM. On 2026-05-21, systematic testing of every navigation variant proved that bet365's SPA only activates racing markets via real Playwright clicks:

| Navigation Method | Result |
|-------------------|--------|
| `window.location.hash = "#/AS/B2/..."` | Silently ignored — URL changes but no API call fires |
| `history.pushState(...)` | Silently ignored |
| `page.goto(race_url)` | HTTP 403 from Cloudflare |
| Fake `<a>` click via JS | DOM event fires but SPA doesn't route |
| `hashchange` event dispatch | SPA doesn't respond |
| **`locator.click()` on NTJ race** | **Racecoupon API fires, WS markets activate** |

This confirms that bet365's racing SPA validates click origin at a level deeper than DOM event dispatch — consistent with the `isTrusted` detection documented for sports betting in [[concepts/bet365-istrusted-synthetic-click-detection]].

### The Click-Loop Architecture

The scanner clicks through visible NTJ races using Playwright locators:

1. Navigate to bet365 racing page (already open in AdsPower Chrome)
2. Locate NTJ race elements (race name + venue links in the Next-To-Jump widget)
3. Click each race via `locator.click()` — triggers racecoupon HTTP response
4. Capture racecoupon via CDP response interception — extract runner names, barriers, jockeys, FW/FP odds
5. WS subscription activates automatically from the click — `PM{fid}-{pid}` topics begin streaming
6. Repeat for next race (`max_clicks=20` default)
7. Push merged race data to VPS via `POST /api/v1/ingest/bet365` with `{"races": [...]}` wrapper

The `already_activated` parameter enables dedup on periodic re-scans (every 5 minutes): races already in the active set are skipped, only new races entering the NTJ window are clicked.

### Place Odds: Separate Participant IDs

A significant discovery during place odds integration: bet365 uses **separate participant IDs** for Win vs Place markets per horse. Each horse in a racecoupon has TWO PA entries — one carrying `FW` (Fractional Win) odds and one carrying `FP` (Fractional Place) odds. The WS stream delivers odds updates on separate PM topics for each:

| Market | Racecoupon Field | WS Topic | Stream Field |
|--------|-----------------|----------|--------------|
| Win | `FW=3.50` | `PM{fid}-{win_pid}` | `DO=3.50` |
| Place | `FP=1.80` | `PM{fid}-{place_pid}` | `DO=1.80` |

A critical disambiguation: the WS update frame's `FP` field is actually **Fractional Price** (a duplicate of the win price in fractional format), NOT Fractional Place. The racecoupon body is the only source where `FP` genuinely means Place odds. This semantic overloading caused an initial bug where live streaming appeared to deliver place odds but was actually duplicating win odds.

The fix snapshots place odds from the racecoupon body (refreshed every 90 seconds via click re-scan) and streams win odds live via WS — place odds don't move fast enough to need sub-second streaming.

### Data Quality Fixes

Three data quality issues were discovered and fixed during deployment:

1. **Duplicate runners**: bet365 emits two PA entries per horse (Win + Place) — click-scan must dedup by normalized name, keeping the entry with more data
2. **Vacant box entries**: `*** VACANT BOX ***` placeholder entries in greyhound races leak through to the catalogue — filtered at both scan and ingest
3. **Result prefix bleed**: Finished races leak position prefixes into runner names (e.g., `"1. Lacy Sarah"`) — stripped via regex at scan and ingest

A shared `_sanitize_runner_name()` helper was created to handle all three across every ingest path (scaffold, merge, canonical-add).

### Betfair Auth Outage Discovery

During the same day, all venues appeared "orange" (missing Betfair data) on the TAKEOVER dashboard. This was NOT a venue-linking issue — all 13 bet365 venues matched canonical names correctly. The root cause was Betfair's `identitysso.betfair.com` returning 503 from Cloudflare blocking the DigitalOcean IP range. The permanent fix is cert-based auth (`identitysso-cert.betfair.com/api/certlogin`) which bypasses Cloudflare entirely.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - The broader racing adapter architecture that the click-loop scanner replaces the HTML scrape approach within
- [[concepts/bet365-istrusted-synthetic-click-detection]] - The same click authentication pattern: bet365 validates click origin for racing (NTJ clicks) and sports (sidebar clicks)
- [[concepts/spa-navigation-state-api-access]] - The SPA navigation constraints that make programmatic navigation impossible for racing — same family as the sports props click-through requirement
- [[connections/anti-scraping-driven-architecture]] - The click-gated WS state machine is another defensive layer: data streams are available but require SPA-authenticated activation via real clicks
- [[concepts/scanner-warmup-false-ev-guard]] - The warmup guard applies to bet365 racing ramp-up alongside TAB/TabTouch/Betfair
- [[concepts/bet365-racing-meeting-walk-hash-nav-limitation]] - Meeting-walk attempt to expand coverage from ~24 to ~110 races: hash-nav triggers HTTP but NOT WS subscriptions; display-layer IDs ≠ PM stream IDs; reverted to NTJ click-scan

## Sources

- [[daily/lcash/2026-05-22.md]] - Meeting-walk attempt shipped then reverted (fc8f7a2): hash-nav to fixture F-URLs triggers racecoupon HTTP but NOT WS PM subscriptions; display-layer IDs (aee_ids, EP) ≠ PM stream participant_ids; 2,255 unmatched WS chunks diagnostic; hybrid approach needed (discovery via hash-nav + activation via real click); healthy baseline: ~43 races, ~210 runners, 0 unmatched, ~50-100 place movements/60s; Full-snapshot reclassification self-corrects win↔place swap; transient "0 races" during rescan is benign VPS catalogue rebuild (Sessions 11:00, 12:42)
- [[daily/lcash/2026-05-21.md]] - Every programmatic navigation variant tested and failed; only locator.click() activates WS markets; no "all meetings" view exists; NTJ coverage ~24 races/~2h window; click-loop scanner deployed to Eve; 14 races matched with 5-bookie odds; first click cold-start miss; VPS ingest expects `{"races": [...]}` wrapper not raw list; 6/20 races unmatched (NZ); separate Win/Place participant IDs; racecoupon FP ≠ WS FP semantics; 3 data quality fixes (dupes, vacants, saddle prefix); Betfair auth outage from Cloudflare blocking DigitalOcean (Sessions 10:49, 11:33, 11:40, 12:57, 13:30, 14:00, 15:21, 15:52)
