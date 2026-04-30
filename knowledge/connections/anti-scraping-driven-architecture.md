---
title: "Connection: Anti-Scraping Defenses Drive Adapter Architecture"
connects:
  - "concepts/spa-navigation-state-api-access"
  - "concepts/browser-mediated-websocket-streaming"
  - "concepts/bet365-racing-adapter-architecture"
  - "concepts/cdp-browser-data-interception"
sources:
  - "daily/lcash/2026-04-11.md"
  - "daily/lcash/2026-04-13.md"
  - "daily/lcash/2026-04-14.md"
  - "daily/lcash/2026-04-15.md"
  - "daily/lcash/2026-04-21.md"
  - "daily/lcash/2026-04-29.md"
  - "daily/lcash/2026-04-30.md"
created: 2026-04-12
updated: 2026-04-30
---

# Connection: Anti-Scraping Defenses Drive Adapter Architecture

## The Connection

Every major architectural pivot in the bet365 racing adapter was forced by a specific anti-scraping defense, not by a design preference. The adapter's final two-layer architecture (HTTP discovery + WS streaming via browser piggybacking) is the shape that bet365's defenses carved out — the only viable path through a layered defense system.

## Key Insight

The non-obvious insight is that bet365's anti-scraping operates at **six independent layers**, and each layer independently invalidates a different standard scraping approach:

1. **Cloudflare (network layer):** Blocks datacenter IPs and headless browser fingerprints → forces use of AdsPower with residential proxy. Confirmed on 2026-04-14 from VPS testing: DigitalOcean Sydney ASN (`170.64.213.223`) gets `__cf_bm` cookie + 403 challenge on every request including raw curl with Chrome 146 UA; `curl_cffi` with chrome146/131/124/120 impersonation all 403'd; block is IP-reputation at ASN level, not TLS fingerprint. The WS endpoint (`wss://premws-pt1.365lpodds.com/zap/`) is behind the same Cloudflare edge (CNAME → `cdn.cloudflare.net`) and also 403s from datacenter IPs — WS is NOT a shortcut around the IP block
2. **Headless detection + CDP artifact detection (application layer):** bet365 detects `--headless=new` Chrome and serves degraded/inert SPA content — page loads, JS runs, WS wrapper injects, but zero WS traffic arrives. Discovered on 2026-04-15 during Dell server port: four Chrome configs tested, only headed (visible) mode receives data. This is distinct from Cloudflare — it operates within the SPA itself, not at the network level. See [[concepts/bet365-headless-detection]]. On 2026-04-21, a further refinement was discovered: bet365 also detects CDP (Chrome DevTools Protocol) artifacts even in headed mode with `--disable-blink-features=AutomationControlled`. The SPA sidebar loads normally, but game content areas render blank — network API responses still flow, but DOM rendering is blocked. This means headed mode is necessary but not sufficient for full SPA interaction; native Playwright clicks (not hash navigation or synthetic JS clicks) are required to trigger API calls. See [[concepts/spa-navigation-state-api-access]]
3. **SPA navigation state (application layer):** API returns empty unless browser has followed expected navigation flow → forces real browser navigation, not HTTP clients
4. **SPA internal caching (client layer):** After ~15 navigations, stops making HTTP requests → forces navigate-away trick and periodic reloads
5. **WebSocket authentication (transport layer):** Rejects non-browser WS connections with 403 → forces piggybacking on browser's authenticated connection
6. **WebSocket instance isolation (runtime layer):** SPA creates WS inside closures and never exposes globally; cross-origin WS creation from the page fails because cookies aren't sent to `365lpodds.com` from `bet365.com.au`; prototype monkey-patching fails because `send` is bound at instance creation → forces pre-page-load constructor injection via `Page.addScriptToEvaluateOnNewDocument` (see [[concepts/websocket-constructor-injection]])

No single defense is insurmountable, but each one eliminates a class of simpler solutions. Direct HTTP? Blocked by layers 1 and 3. Headless Playwright? Blocked by layers 1 and 2. Headed browser with fetch()? Blocked by layer 3. Headed browser with navigation? Works for HTTP but hits layer 4 at scale and can't stream via layer 5. Open a new WS from page JS? Blocked by layer 6 (cross-origin). Find the SPA's existing WS at runtime? Blocked by layer 6 (closure-hidden). The only architecture that survives all six layers is: anti-detection browser (layer 1) + headed mode (layer 2) + real SPA navigation (layer 3) + navigate-away cache busting (layer 4) + constructor-injected WS capture before page load (layers 5+6).

Two additional defensive behaviors were discovered on 2026-04-29:

- **Request context validation (layer 3 refinement):** `fetch()` via CDP `Runtime.evaluate` returns HTTP 200 with an empty body — bet365 validates not just the navigation state but the request origin. Programmatic `fetch()` calls from within the page context are distinguished from the SPA's own HTTP requests. The hash-nav approach works because it triggers the SPA's own internal request pipeline, not a programmatic fetch. Similarly, same-URL `page.goto()` re-navigation doesn't re-fire the API — the SPA detects the duplicate URL and serves cached content. Refresh loops must cycle through different URLs (bounce strategy) to trigger fresh HTTP requests. See [[concepts/bet365-mlb-hash-nav-mg-fetching]].

- **Concurrent navigation rate-limiting:** When 15 game pages fire `Page.navigate` simultaneously via `asyncio.gather`, bet365's server returns empty responses for approximately half the requests (odds count dropped from 12,401 to 6,145). This is not network congestion — it is server-side detection of concurrent bulk navigation from a single browser session. A bounded semaphore (sem=3, maximum 3 concurrent navigations) restores full data quality. This defense is distinct from all six layers above: it doesn't block access entirely, but **degrades response quality** when navigation patterns exceed what a human user would produce. Validated on 2026-04-30 via the v3 capability ladder: 11,018 odds at 0% drift over 704 seconds with sem=3, confirming the pattern holds at production scale. See [[concepts/mlb-parallel-scraper-workers]] and [[concepts/bet365-v3-scraper-capability-ladder]].

**Countermeasures (2026-04-30):** Two countermeasures were validated against the defense stack:

- **Diversion tab**: A background tab that periodically navigates to non-sport pages simulating natural browsing patterns. Combined with cross-sport activity from parallel sport servers, this provides behavioral camouflage. The v3 stability test showed -3.3% drift (with diversion) vs -50% cliff-drop (without). However, the diversion tab caused Playwright EPIPE crashes on Windows/Node v24 (see [[concepts/playwright-node-pipe-crash-vector]]) and was disabled in multi-server production where other sport servers provide sufficient cross-sport activity naturally.

- **Partial-result shield**: Rejects API responses that return significantly fewer results than the prior capture (e.g., 67% of previous odds count, below a 70% floor). Prevents bet365's occasional degraded responses from overwriting good cached data. This is distinct from all six defense layers — it doesn't counter a specific defense but mitigates the data quality degradation that occurs when detection is partial rather than complete.

Additionally, even after surviving all six layers, a **seventh constraint** limits what can be streamed: session-bound topic authorization (see [[concepts/bet365-ws-topic-authorization]]) means the backend only permits WS subscriptions for topics the SPA has registered via `P-ENDP` frames. Racing runner tiles get per-participant registrations (WS works); NBA props are bulk-fetched via BB wizard HTTP (WS silently drops). This is not a defense per se, but a rendering architecture difference that determines WS viability per sport.

This mirrors the broader pattern in [[connections/hook-reliability-and-capture-architecture]] — **design for observed behavior, not intended behavior**. Here, the "observed behavior" is bet365's actual defense stack, and the architecture is the shape that remains after every shortcut has been eliminated.

## Evidence

The adapter went through four iterations in a single day (2026-04-11), each triggered by hitting a new defense layer:

- **Iteration 1 → 2:** Direct `fetch()` returned empty → discovered SPA navigation state requirement → switched to hash navigation with CDP interception
- **Iteration 2 → 3:** Navigation worked but SPA cached after ~15 requests → discovered navigate-away trick → added soccer-hash cache busting between meetings
- **Iteration 3 → 4:** HTTP polling worked (67 races, 661 runners, ~4 min) but user wanted real-time streaming → Python WS returned 403 → pivoted to browser-mediated WS piggybacking
- **Within Iteration 4 (2026-04-13):** Prototype monkey-patching of `WebSocket.prototype.send` failed (SPA binds at creation) → opening a new WS from page JS to `365lpodds.com` failed (cross-origin, no cookies) → discovered `Page.addScriptToEvaluateOnNewDocument` to wrap the constructor before the SPA runs

Each discovery was empirical: the defense was only understood after the simpler approach failed. The progression from "direct HTTP" to "constructor-injected WS capture" represents a full traversal of all five defense layers.

**VPS validation (2026-04-14):** A teammate's deployment doc (OCEAN_DEPLOY) assessed "Cloudflare Bot Management ❌ Not present" — true from a residential AU IP, false from a datacenter IP. This highlighted that anti-bot assessments are environment-dependent and must be validated from the actual deployment environment. Testing from DigitalOcean Sydney confirmed every endpoint (HTTP and WS) is behind Cloudflare with ASN-level IP reputation blocking. Raw Python WebSocket (`websockets` library) to the `premws` endpoint remains the ideal primary path once the IP block is solved — no Playwright needed, no 500MB RAM overhead — but requires either residential proxy, a Mac-based relay, or a token-shipping scheme where the auth token is captured locally and sent to the VPS daily.

## Related Concepts

- [[concepts/spa-navigation-state-api-access]] - Defense layer 2: SPA state validation
- [[concepts/browser-mediated-websocket-streaming]] - Defense layer 4: WS authentication
- [[concepts/bet365-racing-adapter-architecture]] - The architecture shaped by all four layers
- [[concepts/cdp-browser-data-interception]] - The interception technique that works within the constrained architecture
- [[concepts/bet365-racing-data-protocol]] - The protocol whose access is gated by these defenses
- [[concepts/websocket-constructor-injection]] - Defense layer 5: the pre-page-load capture technique
- [[connections/hook-reliability-and-capture-architecture]] - Parallel pattern: observed behavior driving architecture
- [[concepts/bet365-headless-detection]] - Defense layer 2: headless Chrome detection serving empty data
- [[concepts/bet365-ws-topic-authorization]] - Session-bound topic authorization limiting WS streaming to registered render topics
- [[connections/ws-viability-sport-rendering-divergence]] - How the defense stack's WS layer interacts differently with racing vs NBA props
- [[concepts/mlb-parallel-scraper-workers]] - Concurrent navigation rate-limiting discovered during MLB scraper rewrite; bounded semaphore (sem=3) avoids detection
- [[concepts/bet365-mlb-hash-nav-mg-fetching]] - Request context validation: `fetch()` via `Runtime.evaluate` returns 200-but-empty; hash-nav triggers SPA's own requests

