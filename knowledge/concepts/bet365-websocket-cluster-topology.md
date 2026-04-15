---
title: "bet365 WebSocket Cluster Topology"
aliases: [ws-clusters, premws-vs-pshudws, ws-endpoint-selection, websocket-cluster]
tags: [bet365, websocket, infrastructure, streaming, racing]
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# bet365 WebSocket Cluster Topology

bet365 operates multiple WebSocket clusters (`premws`, `pshudws`) that carry different data streams. The racing adapter must specifically hijack the `premws-pt1.365lpodds.com` cluster for full fixture odds — hijacking the `pshudws.z1.365lpodds.com` cluster instead produces partial or empty odds, a failure mode that presents as valid subscriptions with near-zero coverage.

## Key Points

- bet365 runs at least two WS clusters: `premws` (primary odds data) and `pshudws` (push notifications/limited data)
- Hijacking `pshudws` instead of `premws` results in 1% coverage (4/556 participants) despite valid subscriptions — a wrong-endpoint failure, not a parsing or subscription issue
- The `premws` connections can transition to CLOSED state (readyState=3) mid-session, leaving only `pshudws` active — the adapter must detect and recover from this
- WS hijack logic must prefer `premws` cluster and validate the endpoint before sending subscriptions
- A 1% coverage rate with valid subscription messages is a diagnostic signal for wrong-cluster hijack

## Details

### Cluster Roles

bet365's WebSocket infrastructure distributes real-time data across multiple endpoint clusters:

- **`premws-pt1.365lpodds.com`** — the primary odds cluster. This carries full fixture snapshots (`F|` messages), incremental odds updates (`U|` messages), and responds to `PM{fixture}-{participant}` subscription requests with complete price data. This is the cluster the adapter needs.

- **`pshudws.z1.365lpodds.com`** — a push/notification cluster. This carries a subset of data — likely event-level notifications, score updates, or status changes rather than full participant-level odds. Subscriptions sent to this endpoint may partially succeed (some fixtures respond) but with drastically reduced coverage and detail.

The browser's SPA maintains connections to both clusters simultaneously. When the adapter's WebSocket hijack logic (see [[concepts/websocket-constructor-injection]]) selects which captured WebSocket to use, it must filter by endpoint hostname and prefer `premws` connections.

### The 1% Coverage Failure

On 2026-04-14, the adapter achieved a successful discovery (8 AU/NZ meetings, 556 participants, 33 fixtures) and sent 12 subscription chunks — but only 4 fixtures returned prices, each showing `1/1` runner mapped despite ~17 runners per fixture on average. Total coverage was 4/556 (0.7%).

Root cause analysis revealed the adapter had hijacked a `pshudws` connection instead of a `premws` connection. The 3 `premws` connections had all transitioned to CLOSED state (readyState=3), leaving only the `pshudws` endpoint alive. The adapter's WS selection logic did not distinguish between clusters — it picked any open WebSocket, which happened to be the wrong one.

### Connection State Transitions

WebSocket connections have four readyState values: 0 (CONNECTING), 1 (OPEN), 2 (CLOSING), 3 (CLOSED). The `premws` connections rotating every ~80 seconds (documented in [[concepts/bet365-racing-data-protocol]]) means that at any given moment, some `premws` connections may be in CLOSED state. If the adapter checks for open WebSockets at the wrong moment, all `premws` connections might be closed while a `pshudws` connection remains open — leading to wrong-cluster hijack.

The fix requires two changes: (1) the hijack selection logic must prefer connections to `premws` hosts, and (2) the rehijack/recovery logic must also apply the same preference, so that when a new `premws` connection opens after rotation, the adapter switches to it.

### Diagnostic Pattern

A coverage rate near 1% with valid subscriptions and successful discovery is a strong diagnostic signal for wrong-cluster hijack. Other failure modes (bad subscriptions, parsing errors, authentication failures) produce different signatures — typically 0% coverage with error messages, or high coverage with missing fields. The pattern of "some fixtures respond, but with minimal data" is characteristic of receiving data from a secondary cluster that carries partial information.

## Related Concepts

- [[concepts/bet365-racing-data-protocol]] - The protocol used on both clusters; `premws` carries full `F|`/`U|` payloads
- [[concepts/websocket-constructor-injection]] - The capture technique that provides access to all WS instances, requiring cluster-aware selection
- [[concepts/browser-mediated-websocket-streaming]] - The piggybacking architecture where cluster selection occurs
- [[concepts/bet365-racing-adapter-architecture]] - The adapter whose coverage depends on correct cluster selection

## Sources

- [[daily/lcash/2026-04-14.md]] - 8 meetings discovered, 556 participants, but only 4/556 coverage (1%); root cause: hijacked pshudws instead of premws; 3 premws connections were CLOSED (state=3); updated hijack and rehijack logic to prefer premws cluster (Session 10:00)
