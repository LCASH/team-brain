---
title: "Neds and Pointsbet WebSocket Racing Adapters"
aliases: [neds-adapter, pointsbet-adapter, neds-socket-io, pointsbet-signalr, ws-first-recon-rule]
tags: [superwin, racing, scraping, websocket, socket-io, signalr, bookie-onboarding]
sources:
  - "daily/lcash/2026-05-26.md"
created: 2026-05-26
updated: 2026-05-26
---

# Neds and Pointsbet WebSocket Racing Adapters

On 2026-05-26, lcash built and deployed racing adapters for both Neds (Socket.IO v4) and Pointsbet (Azure SignalR) in a single day. Both adapters shipped REST-first with WS streaming deferred to a follow-up phase. The session established a critical operational rule from the user: **"we always optimise for websocket"** — meaning bookie onboarding recon must always start with a WS presence test before falling back to REST/HTML scraping. A key debugging lesson: the wrong WS subscribe channel (`racing/livemarketupdated` = in-play only) led to a false conclusion that WS was in-play-only, corrected only after the user challenged the conclusion based on domain observation.

## Key Points

- **User rule: "we always optimise for websocket"** — recon priority for all future bookie onboarding starts with WS detection
- **Neds**: Socket.IO v4 at `wss://push.neds.com.au/socket.io/`; **per-market subscriptions** (not global firehose); `pricing/prices` channel delivers pre-race odds at 137 frames/90s (~1.5/sec); 243 AU+NZ races via paginated POST `/v2/racing/search`
- **Pointsbet**: Azure SignalR at `wss://push.au.pointsbet.com/client/?hub=signalrhub`; JWT-gated (3600s TTL); full day-card at `/api/racing/v4/meetings` (151KB)
- **REST-first shipped, WS deferred** — too risky to ship both new protocol integration and new bookie simultaneously
- **Wrong subscribe channel = wrong conclusion**: `racing/livemarketupdated` is in-play only; `pricing/prices` carries pre-race odds — always capture browser's actual subscribe payloads before concluding WS doesn't carry data
- **Both hit 100% venue match** on first production cycle — no `/link-venues` manual cleanup required
- **Price type mapping**: Neds Win=`940b8704-...`, Place=`7cf3eea6-...` — verified empirically via DOM probe (win 5.00 → place 2.00, confirming 1+(W-1)/4 formula)

## Details

### Neds Protocol Architecture

Neds runs on the Entain platform (same as Ladbrokes AU, book_id 902), using Socket.IO v4 over WebSocket with session-ID authentication. The initial WS investigation wrongly concluded WS was in-play only — the mistake was subscribing to `racing/livemarketupdated` (which only carries in-play data) instead of `pricing/prices` (which carries pre-race fixed odds). The user challenged the conclusion ("I see Neds odds moving crazy"), and re-investigation proved the user correct: `pricing/prices` pushed 137 frames in 90 seconds (~1.5/sec) with real pre-race odds updates.

Neds Socket.IO uses **per-market subscriptions**, not a global firehose:
- `{handler:"pricing", method:"prices", market_ids:[...]}` — odds updates
- `{handler:"racing", method:"marketupdated", ids:[...]}` — market status
- `{handler:"racing", method:"entrantupdated", ids:[...]}` — runner changes
- `{handler:"racing", method:"racecard-status", id:...}` — race lifecycle

Race discovery uses paginated POST `/v2/racing/search` with `page_size` cap of 20 (same pagination pattern as BoostBet). Full AU+NZ catalogue = 243 races in ~28s of pagination.

The entity-normalized REST model stores races, markets, entrants, and prices all keyed by UUID — a different structural pattern from other bookies that requires mapping between entity types during parsing.

### Pointsbet Protocol Architecture

Pointsbet uses Azure SignalR (`wss://push.au.pointsbet.com/client/?hub=signalrhub`) with JWT authentication (3600s TTL). The full day-card is available at `/api/racing/v4/meetings` (151KB response). Like Neds, the REST adapter was shipped first with WS streaming deferred.

During initial warmup, Pointsbet produces `PERF YELLOW` warnings that are transient — they normalize once the hot tier populates after the first warm sweep. `Runner not in scaffold` log lines are benign (runners the bookie has that Betfair doesn't — NZ suffix horses, late scratchings).

### The WS-First Recon Rule

The user established **"we always optimise for websocket"** as a hard rule for bookie onboarding. This reorders the recon priority sequence:

1. **First**: Check for WS presence via live browser CDP monitoring (not static JS analysis — lazy-loaded WS connections are invisible to static recon)
2. **Second**: If WS confirmed, characterize the subscribe protocol (per-market vs global, auth requirements)
3. **Third**: If no WS, fall back to REST polling or HTML scraping

Static recon (scanning JS bundles for `wss://` references) is insufficient for WS determination because WebSocket connections may be lazily initialized only after user interaction or specific page navigation. Live DevTools observation via CDP is the authoritative test.

### The Wrong Channel Lesson

The most valuable debugging lesson from the Neds investigation: subscribing to the wrong WS channel produces a technically accurate but operationally misleading conclusion. `racing/livemarketupdated` genuinely only carries in-play data — the conclusion "Neds WS is in-play only" was correct for that channel but wrong for the bookie. The correction came from **trusting domain expert observation over technical conclusion**: the user watches Neds odds move daily on the website and knew WS must be carrying pre-race data.

This mirrors the value-betting scanner's broader lesson documented across multiple bugs: when real-world observation contradicts a technical conclusion, re-investigate before doubling down.

### Production Deployment

Both adapters were deployed to production with immediate results:
- **Neds**: 152 AU+NZ races in local smoke test; 100% venue match on first production cycle; committed as `dbd7332`
- **Pointsbet**: 19 hot-tier races initially, scaling to 76+; 100% venue match; committed as `9a48535`

Edge configurations follow the standard pattern: `*-normal` (value mode) and `racing-run-2nd-3rd-*` (refund-as-bonus mode with `bonus_conversion: 0.80`, `min_field_size: 8`).

## Related Concepts

- [[concepts/neds-entain-api-recon]] - Initial Neds reconnaissance (May 18) that identified Entain platform + Socket.IO; this article covers the full adapter build
- [[concepts/boostbet-racing-adapter]] - Built in the same day; BoostBet is pure REST (no WS), contrasting with Neds/Pointsbet's WS-first potential
- [[concepts/betr-no-websocket-xhr-only-architecture]] - Betr confirmed zero WebSocket; Neds/Pointsbet confirm WS presence — different bookies, different transport architectures
- [[concepts/tabtouch-kambi-white-label-sports]] - Kambi Socket.IO is live-only (no pre-game); Neds Socket.IO confirmed to carry pre-race odds — same protocol, different data scope
- [[concepts/superwin-racing-profitability-dimensions]] - New bookies add to the multi-bookie edge-scanning surface; harness coverage particularly valuable

## Sources

- [[daily/lcash/2026-05-26.md]] - Neds: Socket.IO v4, per-market subscriptions, pricing/prices channel (137 frames/90s), paginated search (243 races), entity-normalized model, Win/Place price_type_id mapping, committed dbd7332 (Sessions 12:35, 12:52, 13:46). Pointsbet: Azure SignalR, JWT-gated, full day-card 151KB, PERF YELLOW warmup transient, committed 9a48535 (Sessions 12:35, 13:46). User rule: "we always optimise for websocket"; wrong subscribe channel = wrong conclusion; trust domain experts over technical conclusions (Session 12:35). Both hit 100% venue match first cycle; REST-first shipped, WS deferred (Session 13:46)
