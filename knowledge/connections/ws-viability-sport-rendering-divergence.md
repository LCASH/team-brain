---
title: "Connection: WebSocket Viability Diverges by Sport Rendering Architecture"
connects:
  - "concepts/bet365-ws-topic-authorization"
  - "concepts/bet365-racing-adapter-architecture"
  - "concepts/bet365-mlb-lazy-subscribe-migration"
  - "concepts/odds-staleness-pipeline-diagnosis"
sources:
  - "daily/lcash/2026-04-15.md"
created: 2026-04-15
updated: 2026-04-15
---

# Connection: WebSocket Viability Diverges by Sport Rendering Architecture

## The Connection

bet365's WebSocket streaming viability is determined by how the SPA renders each sport's data — specifically, whether individual markets receive per-element render registrations or are bulk-fetched via HTTP. Racing odds stream successfully via WS because each runner tile is individually rendered and registered; NBA/MLB player props cannot stream via WS because they are bulk-fetched through the BB wizard HTTP endpoint with no per-prop registration. This means the racing adapter's proven architecture cannot be directly ported to NBA props.

## Key Insight

The racing WS adapter's success created an assumption that the same architecture could be ported to NBA player props. The WS probe on 2026-04-15 disproved this by uncovering the session-bound topic authorization mechanism: bet365's backend only permits subscriptions for topics that the SPA has registered via `P-ENDP` frames during normal rendering. The architecture that works for racing is structurally impossible for props — not because of a protocol difference, but because of a rendering architecture difference.

This has a non-obvious implication: **the success of a scraping technique on one sport does not predict its viability on another sport at the same bookmaker.** The same WS protocol, the same auth tokens, the same subscription format, and the same server infrastructure — but different SPA rendering patterns create fundamentally different data access paths. The assumption that "if racing WS works, NBA WS will work too" was a category error conflating protocol-level compatibility with application-level authorization.

This also connects to the MLB lazy-subscribe migration (see [[concepts/bet365-mlb-lazy-subscribe-migration]]): MLB props moved from BB wizard to a lazy-subscribe model that uses intersection observer-triggered WS subscriptions. If these lazy-subscribe subscriptions produce `P-ENDP` registrations, MLB props might be WS-streamable where NBA props are not — a testable hypothesis that could inform future architecture decisions.

## Evidence

The racing adapter (see [[concepts/bet365-racing-adapter-architecture]]) successfully streams live odds via WS by:
1. Injecting a WebSocket constructor wrapper before page load
2. Capturing the SPA's authenticated WS connection
3. Sending `PM{fid}-{pid}` subscription messages
4. Receiving `F|` snapshots and `U|` deltas

The NBA WS probe attempted the identical technique:
1. Same constructor wrapper injection ✓
2. Same WS connection capture ✓
3. Same `PM{fid}-{pid}` subscription format ✓
4. Received responses for main markets (spread/total/moneyline) ✓
5. Received zero responses for prop markets ✗

The divergence occurs at step 5: main markets are rendered individually in the SPA (each with a render registration), while props are fetched via BB wizard HTTP and rendered as a batch without individual registrations. The server honors subscriptions for registered topics and silently drops unregistered ones.

## Architectural Consequences

This divergence forces a dual-architecture approach for comprehensive bet365 odds coverage:

- **Main markets (spread/total/moneyline)**: WS streaming is viable and would provide sub-second updates
- **Player props**: HTTP polling remains the only path, with optimization potential (8s intervals, no hash-skip, per-game parallelization) — see [[concepts/odds-staleness-pipeline-diagnosis]]
- **Racing**: WS streaming works end-to-end (proven in production)

The recommended approach is to optimize HTTP polling for props (where WS doesn't work) and optionally add WS for main markets (where it does). This avoids the trap of pursuing a single unified architecture when the platform itself enforces different access patterns per sport/market type.

A three-phase plan was agreed: Phase 1 (standalone WS probe — completed, answered unknowns) → Phase 2 (HTTP-poll optimization + `source_captured_at` reinstatement) → Phase 3 (optional WS for main markets if sub-second updates prove valuable).

**Phase 2 progress (Session 22:36):** The HTTP-poll optimization work was organized into a three-commit feature branch on the same day. Beyond the planned parameter changes (15s→8s polling, hash-skip removal), a more substantive optimization was added: a coupon endpoint dual-capture strategy using alternating I99/I0 tab navigation (332 odds/game, 5-15s additional freshness improvement). See [[concepts/bet365-nba-coupon-endpoint]]. Additionally, the Pinnacle prediction market pipeline was committed separately (`9a0b19d`), adding Kalshi, Polymarket, and other prediction markets as soft books evaluated against Pinnacle's sharp line — see [[concepts/pinnacle-prediction-market-pipeline]].

## Related Concepts

- [[concepts/bet365-ws-topic-authorization]] - The session-bound authorization mechanism that creates the divergence
- [[concepts/bet365-racing-adapter-architecture]] - The racing adapter where WS streaming succeeds
- [[concepts/bet365-mlb-lazy-subscribe-migration]] - MLB's lazy-subscribe model may produce individual registrations (testable)
- [[concepts/odds-staleness-pipeline-diagnosis]] - The HTTP-poll optimization path necessitated by WS non-viability for props
- [[connections/anti-scraping-driven-architecture]] - The broader defense stack that WS topic authorization is part of
- [[concepts/bet365-nba-coupon-endpoint]] - The concrete HTTP-poll optimization built in Phase 2
- [[concepts/pinnacle-prediction-market-pipeline]] - New soft book universe (prediction markets) committed alongside Phase 2 work
