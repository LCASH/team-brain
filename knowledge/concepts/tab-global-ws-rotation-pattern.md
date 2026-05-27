---
title: "TAB Global WebSocket Rotation Pattern"
aliases: [tab-ws-rotation, tab-dual-ws-dead-end, tab-global-sweep, tab-reconnect-optimization]
tags: [superwin, tab, websocket, architecture, reverse-engineering, reliability]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# TAB Global WebSocket Rotation Pattern

TAB's push infrastructure (`push.beta.tab.com.au`) runs a **global server-side periodic sweep** that kills ALL live WebSocket connections simultaneously — not per-IP, not per-session-age, not per-jurisdiction. On 2026-05-26, three experiments to achieve zero-downtime via dual Worker A/B architecture all failed because the global sweep drops both connections in the same second. The warm-cache approach (300s cache-reuse window) reduces reconnect gap to 3-4 seconds, and this is accepted as good enough — the remaining time is dominated by TLS handshake + Socket.IO namespace negotiation + 1053 subscribe frames.

## Key Points

- **TAB drops ALL WS connections simultaneously** — global wall-clock-based rotation, not per-session or per-IP
- **Three dual-WS experiments all failed**: (1) staggered connection ages, (2) different source IPs (WebShare proxy), (3) different jurisdictions (NSW vs VIC) — all dropped in the same second
- **3-4s reconnect gap** after removing the 5s mandatory sleep — floor is TLS handshake + Engine.IO + namespace ack + 1053 subscribe frames
- **Warm-cache window 300s** means reconnects serve cached data instead of stale; any future drop is a ~3s blink not a 60-90s cold REST freeze
- **TAB jurisdictions (NSW/VIC) are cosmetic** — same 1100 propositions, same update counts, same backend; different parameter, identical data
- **WebShare proxies ARE compatible** with TAB WS endpoint (valid handshake, full data flow) — useful knowledge for other purposes but not for zero-downtime
- **VPS restart-looping discovered**: `superwin.service` being stopped externally every 2-6 minutes — unknown watchdog or second user session, separate issue

## Details

### The Three Experiments

**Experiment 1 — Staggered Connection Ages:** Worker A connected first, Worker B connected 30 seconds later. Theory: TAB's rotation timer is per-session, so A and B would drop at different times. Result: both dropped in the same second. Disproved the per-session-age hypothesis.

**Experiment 2 — Different Source IPs:** Worker B routed through a WebShare proxy (Brazilian IP), giving A and B different source IPs. Theory: TAB tracks rate/rotation per-IP. Result: both dropped in the same second despite different IPs and different countries. Disproved the per-IP hypothesis.

**Experiment 3 — Different Jurisdictions:** Worker A connected as NSW, Worker B as VIC. Theory: different AU jurisdictions route to different backend clusters with independent rotation schedules. Result: both dropped in the same second. Additionally confirmed that NSW and VIC return identical data — same 1100 propositions, same update counts. Jurisdictions are cosmetic routing parameters, not independent backends.

### The Global Sweep Mechanism

All evidence points to a **global wall-clock-based connection rotation**: TAB's push server runs a periodic sweep that terminates all active WebSocket connections simultaneously. The rotation cadence appears variable — one PID showed 11 minutes of uptime between drops, while prior observations showed 3-5 minute cadence. The variability suggests the sweep may be triggered by server load or maintenance schedules rather than a fixed timer, but the key property is that ALL connections die together regardless of client-side configuration.

### Optimized Reconnect Architecture

Since dual-WS zero-downtime is structurally impossible, the focus shifted to **minimizing reconnect time**:

| Metric | Before Optimization | After |
|--------|-------------------|-------|
| Mandatory sleep between drops | 5 seconds | 0 seconds |
| Reconnect gap (disconnect → resubscribe) | 6-15 seconds | 3-4 seconds |
| Cached data served during gap | 60 seconds (cold REST) | 300 seconds (warm cache) |
| User-visible impact | 60-90s frozen odds | 3-4s stale snapshot |

The 3-4 second floor is dominated by TLS handshake + Engine.IO protocol negotiation + Socket.IO namespace acknowledgment + sending 1053 individual subscribe frames. Further optimization would require parallelizing handshake stages or bulk-subscribing — meaningful refactors for marginal gain.

The 300s warm-cache window means that during the 3-4s reconnect gap, the scanner serves cached odds from the last successful WS session rather than falling back to a 60-90s cold REST discovery cycle. This transforms the reconnect from "all odds frozen for a minute" to "odds are 3 seconds stale for 3 seconds."

### TAB Stream Stability After No-Sleep Fix

Post-optimization monitoring showed TAB workers reaching stable state between drops, with 7+ minutes continuous uptime observed. The catalogue remained populated (118 TAB open races) with no new error patterns. After 68 minutes of monitoring, the system was stable across all 9 bookies.

### Alert Threshold Noise

The monitoring alert count climbed to 100 during testing, but all alerts were "Regression" warnings from betr/boostbet/tab tier rotation causing per-cycle counts to dip below the 70% baseline threshold. This is threshold noise from natural tier cycling, not real regressions.

## Related Concepts

- [[concepts/tabtouch-domain-migration-mqtt]] - TabTouch racing uses AWS IoT MQTT (different protocol, different infra) — TAB uses Engine.IO/Socket.IO; both face server-side connection management
- [[concepts/opticodds-sse-reconnect-state-loss]] - OpticOdds SSE has a similar reconnect-state-loss pattern (delta-only on reconnect); TAB's warm cache solves the same class of problem
- [[concepts/betr-no-websocket-xhr-only-architecture]] - Betr has zero WS (pure XHR); TAB has WS that periodically dies — different transport architectures with different reliability profiles
- [[concepts/neds-pointsbet-ws-racing-adapters]] - Neds Socket.IO and Pointsbet SignalR may face similar rotation patterns — worth monitoring after deployment

## Sources

- [[daily/lcash/2026-05-26.md]] - Three dual-WS experiments: staggered ages, proxy IP, NSW/VIC jurisdiction — all dropped same second; TAB runs global server-side sweep; jurisdictions are cosmetic (same 1100 propositions); 3-4s reconnect after removing 5s sleep; warm-cache 300s reduces user impact; WebShare proxies compatible with TAB WS; VPS restart-looping from unknown external stop calls; alert threshold noise from tier rotation (Sessions 16:27, 17:45). TAB stream stability: heartbeat/cache-reuse fix held 4+ min zero disconnects; odds confirmed mutating; dual WS hot/standby proposed then disproved (Session 14:54)
