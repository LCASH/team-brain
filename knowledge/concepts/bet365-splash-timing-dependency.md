---
title: "bet365 Splash Endpoint Timing Dependency"
aliases: [splash-timing, splash-population-delay, http-vs-ws-discovery, ov-topics]
tags: [bet365, racing, discovery, timing, architecture]
sources:
  - "daily/lcash/2026-04-14.md"
created: 2026-04-14
updated: 2026-04-14
---

# bet365 Splash Endpoint Timing Dependency

The bet365 racing adapter's discovery phase depends solely on the HTTP splash endpoint (`nexttojumpcontentapi/splash`), which has a population delay — returning 0 meetings before approximately 09:00 AEST. Meanwhile, WebSocket OV topics already carry live race data by 07:50 AEST. This creates a time-of-day blind spot where the adapter cannot discover races that are already streaming.

## Key Points

- The splash HTTP endpoint returns 0 meetings at 07:52 AEST on a Tuesday morning — bet365 hasn't populated the "Today" splash that early
- WebSocket OV topics (e.g., Manawatu, Townsville) are already visible in WS frames at the same time — a completely independent data path
- Previous Sunday 16:30 testing masked this gap because the splash was already fully populated by afternoon
- The SPA's "Next to Jump" view uses WS OV topics, not the splash API — confirming WS is the primary real-time path
- Two distinct discovery paths exist: HTTP splash (batch, delayed population) vs WS OV topics (real-time, always-on)

## Details

### The Discovery Timing Gap

The bet365 racing adapter's discovery phase (documented in [[concepts/bet365-racing-adapter-architecture]]) relies on the HTTP splash endpoint to enumerate all current racing meetings. This endpoint returns a comprehensive list of venues, race times, and PD identifiers. However, the endpoint has a server-side population schedule — bet365 does not populate the "Today" splash data until approximately 09:00 AEST. Before that time, the endpoint returns a valid but empty response.

This was discovered on 2026-04-14 during a Tuesday morning stress test. At 07:52 AEST, the splash endpoint returned 0 meetings, causing the adapter pipeline to abort at the discovery phase. However, inspection of WebSocket frames on the same browser session revealed that race data for venues like Manawatu and Townsville was already flowing via WS OV topics. The data existed — the adapter just couldn't see it because it only looked through the HTTP path.

### Two Data Paths

bet365 maintains two independent data paths for racing discovery:

1. **HTTP splash (batch, delayed):** The `nexttojumpcontentapi/splash` endpoint returns a full snapshot of all racing meetings. It is populated on a schedule and serves the traditional race card view. The adapter currently uses this as its sole discovery mechanism.

2. **WS OV topics (real-time, always-on):** WebSocket connections carry OV (overview) topics with race information hours before the splash endpoint is populated. The SPA's "Next to Jump" widget consumes these topics directly, which is why users see races in the UI before the splash API returns them.

Relying on only the HTTP path creates a time-of-day blind spot: early-morning races (particularly New Zealand meetings which start earlier in AEST) are invisible to the adapter until the splash populates, despite being actively streamed via WebSocket.

### Why Sunday Testing Masked This

The adapter was previously tested on Sunday evening (16:30 AEST), when the splash endpoint returned 16 meetings and 45 active runners. At that time of day, the splash was already fully populated, so the timing dependency was invisible. The Tuesday 07:52 test was the first early-morning run, exposing the gap.

This is a general testing lesson: data-source dependencies that have time-of-day behavior will only be discovered when tested at the problematic times. Evening and afternoon tests systematically miss morning-population delays.

### Recommended Fix

WS-based discovery — parsing race information directly from WS OV topics — would eliminate the splash-timing dependency entirely. This would make the adapter capable of discovering races as soon as bet365's WebSocket infrastructure begins streaming them, rather than waiting for the HTTP batch population. Implementation is deferred pending a decision on whether to build WS discovery now or wait for the splash to populate and stress-test scaling issues with a full card first.

## Related Concepts

- [[concepts/bet365-racing-adapter-architecture]] - The adapter whose discovery phase is affected by this timing dependency
- [[concepts/bet365-racing-data-protocol]] - The WS protocol that carries OV topics as an alternative discovery source
- [[concepts/bet365-websocket-cluster-topology]] - The WS cluster architecture through which OV topics flow
- [[concepts/websocket-constructor-injection]] - The WS capture technique that could enable WS-based discovery

## Sources

- [[daily/lcash/2026-04-14.md]] - Splash returned 0 meetings at 07:52 AEST while WS OV topics showed Manawatu/Townsville data; Sunday 16:30 test had 16 meetings; identified as timing dependency not code regression; WS-based discovery recommended as long-term fix (Session 07:56)
