---
title: "bet365 WS Subscription Injection Viability"
aliases: [ws-injection, ws-subscribe-probe, bs-topic-prefix, interceptor-on-spa-ws, ws-auth-replay, disjoint-pa-id-spaces, ws-injection-dead, 4-sport-injection-test, empty-ack-semantics, mg-id-namespace-mismatch]
tags: [value-betting, bet365, websocket, reverse-engineering, architecture, scraping]
sources:
  - "daily/lcash/2026-05-07.md"
created: 2026-05-07
updated: 2026-05-07
---

# bet365 WS Subscription Injection Viability

On 2026-05-07 (Sessions 19:51, 20:23, and 20:56), lcash performed deep WS protocol reversal confirming that **interceptor-on-existing-SPA-WS works** for sending subscribes — `add_init_script` storing WS instances in `window.__wsObjs` does NOT trigger bot detection (correcting earlier claims). A 3-topic injection probe demonstrated that the server processes injected subscriptions (known-stable PA → EMPTY ack, active topic like `OVInPlay_30_0` → full F-frame snapshot, bogus topic → EMPTY ack). However, a definitive **4-sport injection test** (NBA, MLB, NRL, Tennis) in Session 20:56 proved that server acknowledgment does NOT mean data delivery — 100% of injected subscribes were acked but 0% produced U-frame deltas, including on an actively-trading live Tennis match. This conclusively kills WS injection as a viable architecture for pre-game prop streaming. The investigation also revealed three separate PA_ID namespaces (HTTP catalog, WS live-trading, betslip) and confirmed that standalone WS auth replay definitively fails.

## Key Points

- **Interceptor-on-existing-SPA-WS confirmed working** — `add_init_script` + `window.__wsObjs` does NOT trigger bet365 bot detection (page renders 131KB body, both WS connections open, no blanking); corrects the earlier claim in [[concepts/bet365-istrusted-synthetic-click-detection]]
- **3-topic injection probe results**: known-stable PA → EMPTY ack (no data to push), active topic (`OVInPlay_30_0`) → full F-frame snapshot, bogus topic → EMPTY ack — all 3 processed by server without rejection
- **BS prefix** is a new betslip-specific WS topic type: `\x16\x00BS{pa_id}-{selection_id},A_<1700b_auth>` — distinct from `PM` (price message) and `L` (live) prefixes
- **Standalone WS auth replay definitively fails** — auth token is bound to session ID; capturing `A_<base64-1697-bytes>` and replaying on a fresh `websockets.connect()` returns HTTP 400
- **Disjoint PA_ID spaces**: HTTP wizard returns static catalog IDs (`1224xxx` range), WS carries live trading IDs (`1238-1240xxx` range) — fundamentally different populations, explaining all "0 overlap" results
- **Betslip validates via HTTP re-fetch** at "Place Bet" click, NOT via real-time WS — debunks assumption that continuous WS streaming is required for bet placement
- **Auth token reusable within session** (same token sent in 3 frames over 60s) but NOT cross-session; SPA only sends subscribe frames at the moment of UI action

## Details

### The Interceptor Correction

The earlier claim (documented in Session 14:32) that "bet365 checks `WebSocket.toString()` to detect constructor tampering — any prototype wrapping triggers anti-bot detection and produces a blank page" was overstated. Session 20:23 proved that the `add_init_script` interceptor pattern (which stores WS instances in `window.__wsObjs` without modifying the WebSocket prototype or overriding `send`) works correctly:

- Page renders 131KB body (normal, not blank)
- Both WS connections open and streaming (`premws` and `pshudws`)
- No anti-bot blanking or detection triggered
- Subscription injection via `window.__wsObjs[0].send()` succeeds

The distinction is between **prototype wrapping** (overriding `WebSocket.prototype.send`, which DOES change `WebSocket.toString()` output and IS detected) and **instance storage** (capturing WS objects in a global array without modifying the prototype, which does NOT change toString and is NOT detected). The racing adapter's constructor injection pattern (see [[concepts/websocket-constructor-injection]]) wraps the constructor itself, which may trigger the `toString()` check; the simpler `add_init_script` approach that only stores references avoids this.

### 3-Topic Injection Probe

Three subscription topics were injected via the captured SPA WebSocket to test server behavior:

| Topic | Type | Server Response | Interpretation |
|-------|------|----------------|---------------|
| Known-stable PA (pre-game) | `PM{fid}-{pid}` | EMPTY ack | No data to push (pre-game lines haven't moved) |
| `OVInPlay_30_0` | Active firehose | Full F-frame snapshot | Server accepts subscription, delivers data |
| Bogus topic string | Invalid | EMPTY ack | Server processes without error or disconnect |

All three topics were processed by the server. No rejection, no disconnect, no anti-bot triggering. This confirms that the server honors injected subscriptions on the SPA's authenticated WS connection — the April 15 finding about "silent NACK on unauthorized subscribes" was specific to standalone WS connections without the P-ENDP handshake, NOT to injection on an existing SPA connection.

The EMPTY ack on the known-stable PA is consistent with the pre-game stationarity finding (see [[concepts/bet365-ws-pre-game-prop-streaming-limitation]]): there is literally nothing to push for a pre-game line that hasn't moved. This is not a subscription failure — it's an absence of data events.

### Disjoint PA_ID Spaces

The persistent "0 PA_ID overlap" between WS frames and HTTP wizard data was traced to a fundamental data architecture difference:

| Source | ID Range | Population |
|--------|----------|------------|
| HTTP wizard (I99) | `1224xxx` | Static catalog — all props pre-computed at market creation |
| WS deltas | `1238-1240xxx` | Live trading — only props being actively traded/adjusted |
| Per-G-ID hash-nav | `1238xxx` (same as WS) | Live trading space — `page.goto(/G{gid}/S^1/)` captures in this range |

This explains why the MLB scraper's 26 G-ID walk produces PA_IDs that overlap with WS (both in the live trading space), while the NBA I99 wizard produces IDs that never overlap (static catalog space). The per-G-ID `page.goto(/G{gid}/S^1/)` approach is functionally equivalent to clicking a dropdown — it fires an HTTP `partial?G{gid}` response AND activates SPA WS subscription for that market group simultaneously.

### BS Topic Prefix

A new WS topic type was discovered when monitoring betslip activity: `BS{pa_id}-{selection_id}` (Betslip Subscribe). The captured frame format:

```
\x16\x00BS194210784-1238371616,A_<1700b_auth_token>
```

This is distinct from the previously documented `PM` (Price Message) and `L` (Live) prefixes. The `BS` topic delivers real-time price updates for selections added to the betslip — a narrow, high-priority data channel that bet365 uses for bet placement validation.

### Standalone WS Auth Failure

The `A_<base64-1697-bytes>` auth blob captured from the SPA's subscribe frame was tested on a standalone `websockets.connect()`:

```python
async with websockets.connect("wss://premws-pt3.bet365.com.au/zap/", 
    subprotocols=["zap-protocol-v2"]) as ws:
    await ws.send(auth_frame)  # replayed captured frame
    # → HTTP 400 — server rejects session-unbound auth
```

The server binds the auth token to the session established during the initial WS handshake. The `A_` token embeds a session identifier (the `uid` from the `S_` prefix in the handshake) that must match the connection's session context. Replaying the token on a different connection fails because the uid doesn't match.

This definitively answers the question left open from April 15 and partially addressed by the xcft HMAC forgery on May 6: **forging the xcft token enables WS connection establishment, but the subscribe-frame auth is separately session-bound.** A viable standalone client would need to: (1) forge xcft to open the WS, (2) complete the 101/100 handshake, (3) capture the session uid, (4) construct a fresh subscribe frame with that session's uid — not replay a captured frame.

### Betslip HTTP Validation Pattern

A significant operational finding: bet365's "Place Bet" flow uses an HTTP re-fetch of current odds at the moment the bet is submitted, NOT real-time WS streaming. The betslip displays odds from WS updates (via the `BS` topic), but the actual bet validation and placement happens via a separate HTTP POST that fetches the canonical current price. This means the "live odds" feel in the betslip UI is presentation — the transactional price comes from HTTP.

This has implications for the scraper: there is no need to achieve sub-second WS streaming for accurate pre-game prop odds. The HTTP polling interval (10-15s) captures the same prices that bet365 uses for bet placement validation.

### Definitive 4-Sport Injection Death Verdict (Session 20:56)

On 2026-05-07 (Session 20:56), a comprehensive injection test across **4 sports** (NBA, MLB, NRL, Tennis) definitively proved that WS subscription injection cannot deliver real-time line movement data:

- **100% subscribe ack rate** — server acknowledged every injected topic across all 4 sports
- **0% delta delivery rate** — zero `U`-frame updates received for any injected topic, including an actively-trading live Tennis match (Giron vs Cilic, E194090499)
- **84/84 EMPTY acks** on the Tennis match over 60 seconds — the server registered all subscribes but pushed nothing

This conclusively resolves the question: **EMPTY ack does NOT mean "subscribe accepted, data will follow."** It means "subscribe registered in the session's topic list" with no guarantee of future delivery. The server independently decides which topics receive push updates based on its own featured-content algorithm (the `OV_POPULAR` firehose), not based on client subscription requests. The render-state topic authorization documented in [[concepts/bet365-ws-topic-authorization]] (April 15) was correct all along — the May 7 Session 20:23 correction only applied to the specific mechanism (interceptor-on-SPA-WS works for sending subscribes), not to the server-side delivery decision.

### Three PA_ID Namespaces

The 4-sport injection test also confirmed that bet365 operates **three separate PA_ID namespaces**, not two:

| Namespace | ID Range | Access Method | Population |
|-----------|----------|---------------|------------|
| HTTP catalog (static) | `1219xxx`–`1224xxx` | I99 wizard, coupon endpoints | All props pre-computed at market creation |
| WS live-trading | `1238xxx`–`1240xxx` | Per-G-ID `page.goto`, WS deltas | Actively traded/adjusted props |
| Betslip | `194210784` range | `BS` topic prefix in subscribe frames | Betslip-specific price feeds |

The same player prop (e.g., "Anthony Edwards 20+ Points") has a **different PA_ID in each namespace**. Injecting a subscribe for a static-catalog PA_ID on the WS will never produce deltas because the server's delta engine operates in the live-trading namespace. This is the root cause of ALL "0 PA_ID overlap" findings across every probe test since April 15.

### MG_ID Namespace Mismatch (Session 21:27)

A final investigation on 2026-05-07 (Session 21:27) revealed that the WS topic format `L{MG_ID}-{PA_ID}_30_0` has a **dual namespace problem**, not just a single one. The PA_ID namespace disjoint was already documented above, but the MG_ID component is ALSO in a different namespace between HTTP responses and WS topics:

| MG ID Type | Range | Source | Population |
|------------|-------|--------|------------|
| Local MG IDs | 3-digit (`340`–`351`) | HTTP wizard body | Per-fixture page-local identifiers |
| Global prop-template IDs | 5-6 digit (`181378`, `181551`) | HTTP wizard `MG;ID=` field | Shared templates (e.g., "Player Points O/U") |
| Per-instance MG_IDs | 9-digit (`194110689`, `194110690`) | WS `L{X}-{PA_ID}` topics | Per-fixture, per-market-group instance IDs |

The HTTP wizard body was examined for any 9-digit numbers that could serve as the `{MG_ID}` in WS topic format. Only 5 distinct 9-digit numbers were found — all event/fixture-adjacent IDs (e.g., `194110689`, `194110690`, `194110691`, `194110712`, `182990`), not per-market-group identifiers. None of these matched the MG_ID pattern used in live WS `L{X}-{PA_ID}_30_0` frames.

The May 6 finding that `matchbettingcontentapi/coupon` responses contain `MG;ID=194xxxxxx` records was tested against four NBA HTTP endpoints (wizard I99, partials I0/I1/I43/I45) — none returned 9-digit per-instance MG_IDs. The original finding was either wrong or context-specific (possibly limited to live/in-play content served from a different response format).

This MG_ID mismatch compounds the PA_ID mismatch to make WS topic construction from HTTP data **doubly impossible**: even if PA_IDs could be mapped (they can't — different namespaces), the MG_ID component of the topic also cannot be derived from any available HTTP response. Both halves of the `L{MG_ID}-{PA_ID}_30_0` topic are in namespaces inaccessible from HTTP endpoints.

Three forward paths were identified: (1) a live-fixture probe to capture actual WS frames during active trading and build a reverse map of `{PA_ID: MG_ID}` from observed topics, (2) capturing `OV_POPULAR_30_0` frames during prime time to check if wizard PA_IDs appear in streamed deltas, and (3) testing the 5 event-adjacent 9-digit IDs as the `{MG_ID}` in topic format. The recommended fallback remains HTTP polling at 10-15s intervals.

### Architecture Pivot: HTTP Primary, WS Supplemental

Based on the definitive 4-sport injection failure, the production architecture was confirmed as:

| Layer | Role | Coverage |
|-------|------|----------|
| **HTTP refresh loop (10-15s)** | Primary data source | All pre-game props, all games, all sports |
| **WS listener** | Passive supplement | Only bet365-featured content (near-tipoff, in-play) |

The `_refresh_loop` to be added to both `WSNBAOrchestrator` and `WSMLBOrchestrator` performs periodic wizard fetches at 10-15 second intervals. WS frames from `OV_POPULAR` are opportunistically matched against the PA map — any overlap provides a free sub-second update between refresh cycles, but the system does not depend on WS for correctness or completeness.

## Related Concepts

- [[concepts/bet365-istrusted-synthetic-click-detection]] - The article whose WebSocket.toString() claim is corrected here: interceptor-on-SPA-WS works without triggering bot detection when using instance storage (not prototype wrapping)
- [[concepts/bet365-ws-pre-game-prop-streaming-limitation]] - Pre-game EMPTY acks confirmed via injection probe: no data to push for static lines; the disjoint ID space explains the 0 overlap; 4-sport injection death verdict reinforces HTTP polling as permanent architecture
- [[concepts/bet365-ws-topic-authorization]] - April 15 "injection fails" was about standalone WS; injection on SPA's existing WS works for sending subscribes but server independently decides delivery — render-state authorization confirmed correct
- [[concepts/bet365-xcft-token-hmac-forgery]] - xcft forgery enables WS connection but subscribe-frame auth is separately session-bound; full standalone path requires session uid construction
- [[concepts/websocket-constructor-injection]] - The constructor wrapping technique that MAY trigger WebSocket.toString() detection; the simpler add_init_script storage pattern does not
- [[concepts/bet365-racing-data-protocol]] - The `\x16` subscription prefix and `F|`/`U|` frame format confirmed in the injection probe responses
- [[concepts/bet365-ws-native-scraper-architecture]] - The WS-native scrapers whose HTTP refresh loop decision was informed by these findings; per-G-ID navigation confirmed as capturing live trading PA_IDs

## Sources

- [[daily/lcash/2026-05-07.md]] - Disjoint PA_ID spaces: HTTP wizard 1224xxx (static) vs WS 1238-1240xxx (live trading); page.goto(/G{gid}/S^1/) fires HTTP partial AND activates WS subscription — captures in live trading range; betslip validates via HTTP re-fetch at "Place Bet" not WS; BS prefix for betslip topics; 2 WS connections confirmed (premws 56 frames, pshudws 1 frame) (Session 19:51). Interceptor-on-SPA-WS confirmed working (131KB page body, both WS open, no blanking); 3-topic injection probe: stable PA → EMPTY, OVInPlay → F-frame, bogus → EMPTY; standalone auth replay returns 400 (session-bound); auth token reusable within session (same token 3 frames/60s) not cross-session; SPA subscribes only at UI action moment; consolidated to `project_bet365_ws_protocol_reversed.md`; April 15 "injection fails" was standalone-specific, not interceptor (Session 20:23). **4-sport injection death verdict**: comprehensive test across NBA, MLB, NRL, Tennis — 100% ack rate, 0% delta delivery across all sports; Tennis live match (Giron vs Cilic) 84/84 EMPTY acks in 60s; EMPTY ack = "registered" not "data will follow"; 3 PA_ID namespaces confirmed (HTTP catalog 1219-1224xxx, WS live-trading 1238-1240xxx, betslip 194xxx); architecture pivot to HTTP polling (10-15s) as primary with WS as passive supplement; April 15 render-state authorization confirmed correct — server decides delivery independently of client subscription (Session 20:56). **MG_ID namespace mismatch**: HTTP wizard body contains only 3-digit local MG IDs (340-351) and 5-6 digit global prop-template IDs (181378, 181551), NOT the 9-digit per-instance MG_IDs required for WS `L{MG_ID}-{PA_ID}_30_0` topics; only 5 event-adjacent 9-digit numbers in wizard body; May 6 `matchbettingcontentapi/coupon` MG_ID finding not validated across 4 NBA HTTP endpoints; dual namespace problem (MG_ID + PA_ID both disjoint) makes WS topic construction from HTTP data doubly impossible; 3 forward paths identified: live-fixture probe, OV_POPULAR capture, event-adjacent ID testing (Session 21:27)
