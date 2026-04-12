---
title: "Connection: Anti-Scraping Defenses Drive Adapter Architecture"
connects:
  - "concepts/spa-navigation-state-api-access"
  - "concepts/browser-mediated-websocket-streaming"
  - "concepts/bet365-racing-adapter-architecture"
  - "concepts/cdp-browser-data-interception"
sources:
  - "daily/lcash/2026-04-11.md"
created: 2026-04-12
updated: 2026-04-12
---

# Connection: Anti-Scraping Defenses Drive Adapter Architecture

## The Connection

Every major architectural pivot in the bet365 racing adapter was forced by a specific anti-scraping defense, not by a design preference. The adapter's final two-layer architecture (HTTP discovery + WS streaming via browser piggybacking) is the shape that bet365's defenses carved out — the only viable path through a layered defense system.

## Key Insight

The non-obvious insight is that bet365's anti-scraping operates at **four independent layers**, and each layer independently invalidates a different standard scraping approach:

1. **Cloudflare (network layer):** Blocks datacenter IPs and headless browser fingerprints → forces use of AdsPower with residential proxy
2. **SPA navigation state (application layer):** API returns empty unless browser has followed expected navigation flow → forces real browser navigation, not HTTP clients
3. **SPA internal caching (client layer):** After ~15 navigations, stops making HTTP requests → forces navigate-away trick and periodic reloads
4. **WebSocket authentication (transport layer):** Rejects non-browser WS connections with 403 → forces piggybacking on browser's authenticated connection

No single defense is insurmountable, but each one eliminates a class of simpler solutions. Direct HTTP? Blocked by layers 1 and 2. Headless Playwright? Blocked by layer 1. Browser with fetch()? Blocked by layer 2. Browser with navigation? Works for HTTP but hits layer 3 at scale and can't stream via layer 4. The only architecture that survives all four layers is: anti-detection browser (layer 1) + real SPA navigation (layer 2) + navigate-away cache busting (layer 3) + browser-mediated WS piggybacking (layer 4).

This mirrors the broader pattern in [[connections/hook-reliability-and-capture-architecture]] — **design for observed behavior, not intended behavior**. Here, the "observed behavior" is bet365's actual defense stack, and the architecture is the shape that remains after every shortcut has been eliminated.

## Evidence

The adapter went through four iterations in a single day (2026-04-11), each triggered by hitting a new defense layer:

- **Iteration 1 → 2:** Direct `fetch()` returned empty → discovered SPA navigation state requirement → switched to hash navigation with CDP interception
- **Iteration 2 → 3:** Navigation worked but SPA cached after ~15 requests → discovered navigate-away trick → added soccer-hash cache busting between meetings
- **Iteration 3 → 4:** HTTP polling worked (67 races, 661 runners, ~4 min) but user wanted real-time streaming → Python WS returned 403 → pivoted to browser-mediated WS piggybacking

Each discovery was empirical: the defense was only understood after the simpler approach failed. The progression from "direct HTTP" to "browser-mediated WS" represents a full traversal of the defense stack.

## Related Concepts

- [[concepts/spa-navigation-state-api-access]] - Defense layer 2: SPA state validation
- [[concepts/browser-mediated-websocket-streaming]] - Defense layer 4: WS authentication
- [[concepts/bet365-racing-adapter-architecture]] - The architecture shaped by all four layers
- [[concepts/cdp-browser-data-interception]] - The interception technique that works within the constrained architecture
- [[concepts/bet365-racing-data-protocol]] - The protocol whose access is gated by these defenses
- [[connections/hook-reliability-and-capture-architecture]] - Parallel pattern: observed behavior driving architecture

