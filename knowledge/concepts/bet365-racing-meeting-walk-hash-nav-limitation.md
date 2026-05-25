---
title: "bet365 Racing Meeting-Walk Hash-Nav Limitation"
aliases: [meeting-walk, meeting-tab-walk, hash-nav-no-ws-subscription, display-ids-vs-pm-ids, meeting-walk-revert]
tags: [superwin, bet365, racing, scraping, architecture, websocket, reverse-engineering]
sources:
  - "daily/lcash/2026-05-22.md"
created: 2026-05-22
updated: 2026-05-22
---

# bet365 Racing Meeting-Walk Hash-Nav Limitation

On 2026-05-22, lcash attempted to expand bet365 racing fixture coverage from ~24 races (NTJ click-scan) to ~110 races by walking through meeting pages via hash navigation. The meeting-walk approach successfully triggered `racecouponcontentapi` HTTP responses (getting static race card data), but **did NOT cause the SPA to subscribe to PM market topics** — meaning zero live odds streaming for any race discovered this way. The root cause: hash navigation to fixture F-URLs triggers HTTP fetches but NOT the SPA's internal WebSocket subscription machinery. The meeting-walk was shipped then reverted (commit `fc8f7a2`), and production restored to NTJ click-scan.

## Key Points

- **Hash-nav to fixture URLs triggers HTTP (racecoupon body) but NOT WS subscriptions** — gets static snapshot but zero live odds streaming
- **Display-layer IDs ≠ PM stream IDs**: `aee_ids` and `EP` ids from racecoupon bodies are display identifiers; bet365 assigns different `participant_ids` for PM streaming that only surface on real click activation
- **Diagnostic signal**: 2,255 unmatched WS chunks + 0 live updates = dead giveaway that subscriptions are invalid; compare to 0 unmatched chunks when working correctly
- **Reverted to NTJ click-scan** (commit `fc8f7a2`) — the only proven method for WS market activation remains `locator.click()` on visible NTJ race elements
- **Full-snapshot reclassification** eliminates win↔place swap problem from scan-time classification — self-correcting on every subsequent Full snapshot
- **Healthy startup baseline established**: ~43 races, ~210 runners with both win+place odds, 0 unmatched chunks, ~50-100 place movements per 60s

## Details

### The Architecture Gap: Discovery vs Activation

The bet365 racing scraper has two distinct phases that were conflated in the meeting-walk attempt:

**Discovery** = finding all fixture IDs across all meetings. Hash navigation (`window.location.hash = "#/...F{fixture_id}/"`) works for this — the SPA fires `racecouponcontentapi` HTTP requests that return runner names, barriers, jockeys, and static FW/FP odds.

**Activation** = subscribing to live PM market topics so WS delivers real-time price changes. Only real Playwright `locator.click()` events trigger this — the SPA's internal subscription machinery validates click origin at a level deeper than DOM event dispatch (consistent with the `isTrusted` detection documented in [[concepts/bet365-istrusted-synthetic-click-detection]]).

The meeting-walk approach successfully completed the Discovery phase (finding ~100 fixtures across ~13 meetings) but produced zero Activation — all PM subscriptions were against display-layer IDs that the WS backend didn't recognize.

### Display IDs vs PM Stream IDs

A critical finding: the participant IDs embedded in `racecouponcontentapi` HTTP responses (`ID`, `EP` fields) are **display-layer identifiers** used for rendering the race card HTML. They are NOT the same IDs that bet365 uses for PM WebSocket streaming. The actual PM stream `participant_ids` are only assigned by the SPA's internal subscription system when a real user click activates a race's live market — they are never exposed in HTTP responses.

This means that any approach based on extracting IDs from HTTP responses and constructing PM subscription topics will always fail. The 2,255 unmatched WS chunks diagnostic confirmed this: the WS stream was receiving frames for races activated via NTJ clicks, but zero frames matched the IDs extracted from meeting-walk HTTP responses.

### Concurrent Stream Contention

An additional operational finding: running a validation browser alongside the production stream caused capture contention. Meeting-walk probes must run INSIDE the production stream process, not as a parallel browser session, to avoid stealing WS captures from the production odds pipeline.

### The Correct Hybrid Approach

The revert preserves the proven NTJ click-scan architecture while documenting the required hybrid approach for future coverage expansion:

1. **Meeting-walk for Discovery** — use hash navigation to enumerate all fixture IDs across all meetings (~100+ fixtures vs ~24 from NTJ)
2. **Real click for Activation** — click each discovered race's sidebar row via `locator.click()` to trigger SPA PM subscriptions
3. **Merge** — combine the discovery data (runner names, barriers from racecoupon) with the activation data (live PM stream IDs)

This hybrid approach requires a robust DOM locator for sidebar race rows on the meeting page — a dedicated implementation session. The meeting-walk code was left as dead code for future reference rather than deleted.

### Place Odds Monitoring

The session also established a production monitoring baseline for bet365 racing: ~43 races, ~210 runners with both win+place odds, 0 unmatched WS chunks, and ~50-100 place price movements per 60 seconds. A transient "0 bet365 races" alarm during a rescan walk cycle was confirmed as VPS catalogue rebuilding during the walk — not a real failure. This baseline was documented in a memory file to prevent re-diagnosis of known-benign states.

## Related Concepts

- [[concepts/bet365-racing-click-loop-scanner]] - The NTJ click-scan architecture that meeting-walk attempted to expand; click activation remains the only proven path for WS market subscription
- [[concepts/bet365-istrusted-synthetic-click-detection]] - The isTrusted check on click events that prevents synthetic/programmatic clicks from activating markets — same mechanism blocks hash-nav from triggering WS subscriptions
- [[concepts/spa-navigation-state-api-access]] - Hash navigation triggers HTTP but not WS activation — another instance of bet365's SPA distinguishing between programmatic and genuine user navigation
- [[connections/anti-scraping-driven-architecture]] - The meeting-walk failure reinforces the click-gated WS state machine as a defensive layer — even HTTP discovery doesn't grant WS access
- [[concepts/bet365-coupon-pm-id-mismatch]] - A related ID mismatch: coupon PA IDs ≠ PM subscription IDs in the racing adapter; the meeting-walk finding shows this extends to display-layer IDs from HTTP responses

## Sources

- [[daily/lcash/2026-05-22.md]] - Meeting-walk shipped then reverted (fc8f7a2): hash-nav triggers racecoupon HTTP but NOT WS PM subscriptions; display-layer IDs (aee_ids, EP) ≠ PM stream participant_ids; 2,255 unmatched WS chunks diagnostic; hybrid approach needed (discovery via hash-nav + activation via real click); concurrent-stream contention; healthy baseline: ~43 races, ~210 runners, 0 unmatched, ~50-100 place movements/60s; Full-snapshot reclassification self-corrects win↔place swap; transient "0 races" during rescan is benign VPS catalogue rebuild (Sessions 11:00, 12:42)
