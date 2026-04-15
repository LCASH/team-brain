---
title: "bet365 WebSocket Session-Bound Topic Authorization"
aliases: [p-endp, ws-topic-auth, session-topic-authorization, client-push-subscription]
tags: [bet365, websocket, authorization, reverse-engineering, value-betting]
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# bet365 WebSocket Session-Bound Topic Authorization

bet365's WebSocket infrastructure enforces session-bound topic authorization: the backend only permits subscriptions for topics that the SPA has registered via its `P-ENDP` connection frame during normal rendering. Injecting arbitrary subscription topics — even with valid auth tokens — is silently dropped. This makes WS streaming viable for racing (per-participant render registrations) but not for NBA/MLB player props (bulk-fetched via BB wizard HTTP, never individually registered).

## Key Points

- bet365 WS is client-push, not server-inferred — the SPA explicitly sends comma-separated `PM<fid>-<pid>` topic lists with `,A_<auth_token>` suffix
- Session-bound topic authorization ties permitted subscriptions to the SPA's declared rendering state via `P-ENDP` registration frames
- NBA props live inside BB wizard (HTTP-fetched component) and never get individual per-prop render registrations, so the server silently drops prop subscription requests
- Racing has individual runner tiles that each get per-participant render registrations, which is why racing WS streaming works
- Hierarchical fixture→participant mapping matters: prop PA IDs belong to specific fixture IDs; crossing wrong fid+pid produces nonexistent topics silently dropped (no error, no response)

## Details

### The WS Probe

On 2026-04-15, lcash ran a series of increasingly refined injection probes against bet365's WebSocket infrastructure to determine whether NBA player prop odds could be streamed in real-time:

1. **Baseline capture** — confirmed the SPA's actual subscription format: comma-separated `PM<fid>-<pid>` topics with `,A_<auth_token>` suffix, matching the racing adapter pattern
2. **Naive injection** — injected subscription topics without auth token → silently dropped
3. **Auth-token injection** — added valid auth token → still silently dropped
4. **Correct fid+pid injection** — mapped correct fixture and participant IDs from BB wizard HTTP response → still silently dropped
5. **Same-session injection** — used topics observed in the SPA's own subscription traffic → received responses for main market topics only, not props

Each iteration fixed a real bug (wrong fixture ID, missing auth token, wrong PA type), but the final result was still negative for prop data. Full findings were documented in `brain/findings/2026-04-15-bet365-ws-probe.md`.

### Client-Push Architecture

An earlier hypothesis assumed that bet365's backend auto-pushes odds based on the currently-viewed page context. The probe disproved this: the SPA explicitly sends subscription topic lists to the WS server. The `add_init_script` WebSocket interceptor pattern (wrapping `WebSocket.prototype.send`) successfully captured all SPA `send()` calls, enabling complete protocol reverse-engineering.

The subscription format confirmed is: `\x16PM{fid1}-{pid1},PM{fid1}-{pid2},...,A_{auth_token}` — identical to the racing adapter's format documented in [[concepts/bet365-racing-data-protocol]].

### Session-Bound Authorization

The critical discovery is that bet365's backend maintains a per-session whitelist of permitted topics. When the SPA renders a page, it sends a `P-ENDP` (endpoint registration) frame that declares which data streams it needs. The backend only honors subscription requests for topics that match this registration.

For racing, each runner tile in the SPA constitutes an individual render event that registers its `PM{fid}-{pid}` topic. For NBA props, the BB wizard endpoint fetches all player prop data via a single HTTP request — no individual per-prop rendering occurs, so no per-prop topic registration happens. When the adapter injects `PM{fid}-{pid}` subscriptions for NBA prop participants, the server checks its session whitelist, finds no matching registration, and silently drops the request.

This silent dropping — no error response, no disconnect, just nothing — makes the failure mode particularly hard to diagnose. The adapter receives valid responses for main market topics (spread/total/moneyline, which ARE rendered individually) but zero responses for prop topics, creating the appearance of a data mapping issue when it's actually an authorization issue.

### Implications for Architecture

This finding means the racing WS adapter's architecture (documented in [[concepts/bet365-racing-adapter-architecture]]) cannot be directly ported to NBA player props. The recommended path forward for NBA is HTTP-poll optimization: reduce `_REFRESH_INTERVAL` from 15s to 8s, eliminate the 30s hash-skip blackout in `server/main.py`, and parallelize per-game fetching. The `source_captured_at` diagnostic plumbing (see [[concepts/odds-staleness-pipeline-diagnosis]]) should be reinstated to surface per-pick staleness on the dashboard.

WS streaming IS viable for main markets only (spread/total/moneyline) — the protocol is fully decoded and working. This could become a secondary path if sub-second main market updates prove valuable.

### Unexplored Avenues

Two low-cost experiments remain untried: (1) sweeping tab codes I3-I20 to check for an unexplored NBA prop tab that might trigger per-prop WS registrations, and (2) manually expanding a player prop in visible Chrome to see if DOM interaction triggers prop-specific WS subscriptions. These are unlikely to change the conclusion but haven't been formally ruled out.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The WS protocol format used for subscriptions (identical for racing and NBA main markets)
- [[concepts/bet365-racing-adapter-architecture]] - The racing adapter that successfully uses WS streaming due to per-participant render registration
- [[concepts/bet365-mlb-lazy-subscribe-migration]] - BB wizard vs lazy-subscribe models; props live inside BB wizard, never individually registered
- [[concepts/websocket-constructor-injection]] - The constructor injection technique used in the probe
- [[concepts/browser-mediated-websocket-streaming]] - The piggybacking architecture that WS topic authorization constrains
- [[concepts/odds-staleness-pipeline-diagnosis]] - The HTTP-poll optimization path necessitated by WS non-viability for props
- [[connections/ws-viability-sport-rendering-divergence]] - How bet365's different rendering architectures per sport determine WS viability

## Sources

- [[daily/lcash/2026-04-15.md]] - Full WS probe: 5 injection iterations, `add_init_script` interceptor captured SPA send() calls, P-ENDP session-bound authorization discovered, racing per-participant vs NBA bulk BB wizard rendering difference identified, NBA prop WS declared non-viable, HTTP-poll optimization recommended, WS viable for main markets only (Session 16:20)
