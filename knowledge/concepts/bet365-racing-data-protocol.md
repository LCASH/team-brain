---
title: "bet365 Racing Data Protocol"
aliases: [bet365-protocol, bet365-wire-format, bet365-ws-protocol]
tags: [bet365, websocket, protocol, racing, reverse-engineering]
sources:
  - "daily/lcash/2026-04-11.md"
created: 2026-04-11
updated: 2026-04-12
---

# bet365 Racing Data Protocol

bet365 uses a custom binary-ish protocol over WebSocket for streaming racing data — not JSON. The format is pipe-delimited with two-letter field codes as keys, hierarchical nesting via semicolons, and a prefix system distinguishing full snapshots from incremental updates.

## Key Points

- `F|` prefix indicates a full snapshot (initial data load); `U|` prefix indicates a delta/incremental update
- Fields use two-letter codes as keys (e.g., `NA=` for name, `OD=` for odds, `FI=` for selection ID)
- Pipe `|` separates top-level blocks; semicolon `;` separates sub-records within a block; equals `=` separates key from value
- WebSocket subscriptions use the format `PM{fixture_id}-{participant_id}` per runner, with comma-separated lists for bulk subscription
- Three WebSocket connection types rotate: main data (`premws-pt1.365lpodds.com`), push notifications (`pshudws.z1.365lpodds.com`), with main connections rotating every ~80 seconds

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

### Data Hierarchy

The racecoupon HTTP response follows a hierarchical structure: event header → market sections (`MA;SY=rc`) → participant records (`PA;`). Each racecoupon response contains data for exactly one race, despite having multiple `MA;SY=rc` sections — the additional sections represent Same Race Multi markets and should be deduplicated. Promotional entries can be identified by `#P12#` in their PD field and should be filtered.

### Authentication

Every WebSocket connection requires two tokens: a session token (`S_`) derived from the `pstk` cookie, and an auth token (`A_`) from the `x-net-sync-term` value. The sync-term rotates approximately every 55 seconds and is accessible via `window.__syncTerm` in the page's JavaScript context. The `cf_clearance` cookie from Cloudflare is also required for initial connection establishment.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - The adapter architecture built to consume this protocol
- [[concepts/cdp-browser-data-interception]] - The interception technique used to capture protocol data
- [[concepts/spa-navigation-state-api-access]] - Navigation requirements for the HTTP layer of this protocol
- [[concepts/browser-mediated-websocket-streaming]] - How WS subscriptions are injected using this protocol's format

## Sources

- [[daily/lcash/2026-04-11.md]] - Full protocol reverse-engineering across 7 sessions: field codes mapped from captured WS frames and HTTP responses; subscription format, auth tokens, and data hierarchy documented
