---
title: "bet365 Racing Data Protocol"
aliases: [bet365-protocol, bet365-wire-format, bet365-ws-protocol]
tags: [bet365, websocket, protocol, racing, reverse-engineering]
sources:
  - "daily/lcash/2026-04-11.md"
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-04-14.md"
created: 2026-04-11
updated: 2026-04-15
---

# bet365 Racing Data Protocol

bet365 uses a custom binary-ish protocol over WebSocket for streaming racing data — not JSON. The format is pipe-delimited with two-letter field codes as keys, hierarchical nesting via semicolons, and a prefix system distinguishing full snapshots from incremental updates.

## Key Points

- `F|` prefix indicates a full snapshot (initial data load); `U|` prefix indicates a delta/incremental update
- Fields use two-letter codes as keys (e.g., `NA=` for name, `OD=` for odds, `FI=` for selection ID)
- Pipe `|` separates top-level blocks; semicolon `;` separates sub-records within a block; equals `=` separates key from value
- WebSocket subscriptions use the format `PM{fixture_id}-{participant_id}` per runner, with comma-separated lists for bulk subscription
- Multiple WebSocket clusters serve different roles: `premws-pt1.365lpodds.com` carries full odds data, `pshudws.z1.365lpodds.com` carries push notifications/limited data; hijacking the wrong cluster produces near-zero coverage (see [[concepts/bet365-websocket-cluster-topology]]); main connections rotate every ~80 seconds

## Details

The protocol serves two layers of the bet365 racing data system. The HTTP layer delivers full race card data via the `racecoupon` endpoint, while the WebSocket layer streams real-time odds updates. Both use the same two-letter field code encoding, but the HTTP responses are larger snapshots while WS messages are compact deltas.

### Field Code Reference

| Code | Meaning | Example |
|------|---------|---------|
| `NA` | Runner name | `NA=Rapid Tycoon` |
| `OD` | Odds (fractional) | `OD=4/1` |
| `BC` | Back price (decimal) | `BC=5.50` |
| `FI` | Selection/fixture ID | `FI=100893412` |
| `FF` | Full name | `FF=R7 1609m Pace M` |
| `JN` | Jockey name | `JN=J McDonald` |
| `TN` | Trainer name | `TN=C Waller` |
| `HW` | Weight | `HW=56.5` |
| `HY` | Age | `HY=4` |
| `FO` | Form | `FO=2131` |
| `PN` | Barrier/post number | `PN=3` |
| `SI` | Silks image | `SI=...` |
| `FW` | Win odds | `FW=3.50` |
| `FP` | Place odds | `FP=1.80` |
| `OH` | Odds history | `OH=...` |
| `CL` | Classification | `CL=2030` (horse), `CL=2031` (greyhounds), `CL=2032` (harness) |
| `SM` | Status marker | `SM=1` |
| `DO` | Decimal odds (WS update) | `DO=30/1` |
| `EX` | Scratched indicator | `EX=Scratched` |
| `SA` | Scratched status | `SA=0,1` |

Approximately 30+ field codes exist; this table covers those mapped so far. The WS stream delivers odds updates in the format `PM{fixture}-{participant}U|DO=30/1;` — compact messages containing only the changed fields, with the fixture and participant IDs encoded in the subscription topic rather than the payload.

### Binary Framing (Control Characters)

The WebSocket payload uses control characters for message framing, correcting earlier documentation that assumed a simpler `L{fixture}-{participant}_30_0` format:

| Byte | Meaning |
|------|---------|
| `\x14` | Full snapshot prefix — followed by `PM{fixture}-{participant}\x01F\|PA;...DO=1.35;OD=7/20;...` |
| `\x15` | Update prefix — followed by `...U\|...` containing only changed fields |
| `\x16` | Subscription prefix — sent as `\x16` + subscription payload to request odds for specific runners |
| `\x08` | Chunk separator — multiple messages within a single WebSocket frame are separated by this byte |
| `\x01` | Field separator within a message, delimiting the topic from the payload |

A single WebSocket frame may contain multiple messages (chunks separated by `\x08`). The `DO=` field carries decimal odds while `OD=` carries fractional — both may appear in the same message. Initial subscription responses arrive as `\x14` snapshots (the `F|` path), while subsequent price changes arrive as `\x15` updates (the `U|` path).

### Data Hierarchy

The racecoupon HTTP response follows a hierarchical structure: event header → market sections (`MA;SY=rc`) → participant records (`PA;`). Each racecoupon response contains data for exactly one race, despite having multiple `MA;SY=rc` sections — the additional sections represent Same Race Multi markets and should be deduplicated. Promotional entries can be identified by `#P12#` in their PD field and should be filtered.

### Authentication

Every WebSocket connection requires two tokens: a session token (`S_`) derived from the `pstk` cookie, and an auth token (`A_`) from the `x-net-sync-term` value. The sync-term rotates approximately every 55 seconds and is accessible via `window.__syncTerm` in the page's JavaScript context. The `cf_clearance` cookie from Cloudflare is also required for initial connection establishment.

The WS subscription protocol embeds auth in-band: `\x16{PM topics},A_{x-net-sync-term}` — no separate HTTP auth header is needed once the WebSocket is open. The auth token is IP-independent once issued and lives for hours, opening a potential deployment pattern where the token is captured on a residential-IP machine and shipped to a VPS for use with a raw Python WebSocket client.

### WebSocket Cluster Topology

bet365 operates multiple WS clusters that carry different data streams. The `premws` cluster carries full fixture odds (snapshots and deltas), while the `pshudws` cluster carries push notifications with limited/different data. Both endpoints are behind Cloudflare CDN with identical IP-reputation blocking. Subscribing to odds topics on `pshudws` produces partial results (1% coverage) — only the `premws` cluster responds with complete odds data. See [[concepts/bet365-websocket-cluster-topology]] for cluster selection logic and failure modes.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - The adapter architecture built to consume this protocol
- [[concepts/cdp-browser-data-interception]] - The interception technique used to capture protocol data
- [[concepts/spa-navigation-state-api-access]] - Navigation requirements for the HTTP layer of this protocol
- [[concepts/browser-mediated-websocket-streaming]] - How WS subscriptions are injected using this protocol's format
- [[concepts/websocket-constructor-injection]] - The technique for capturing the WS instance to send/receive protocol messages
- [[concepts/bet365-websocket-cluster-topology]] - The cluster topology determining which WS endpoint carries which data

## Sources

- [[daily/lcash/2026-04-11.md]] - Full protocol reverse-engineering across 7 sessions: field codes mapped from captured WS frames and HTTP responses; subscription format, auth tokens, and data hierarchy documented
- [[daily/lcash/2026-04-13.md]] - Binary framing correction: `\x14`/`\x15`/`\x16`/`\x08`/`\x01` control characters documented, replacing earlier `L{fixture}` format assumption; `DO=` decimal odds vs `OD=` fractional confirmed in live captures (Session 15:00 onward)
- [[daily/lcash/2026-04-14.md]] - WS cluster topology confirmed: premws vs pshudws carry different data; in-band auth format `\x16{topics},A_{token}`; both WS endpoints behind same Cloudflare edge with ASN-level IP blocking (Sessions 10:00, 11:24)
