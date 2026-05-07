---
title: "bet365 xcft Token HMAC Forgery"
aliases: [xcft-token, nst-forgery, x-net-sync-term-hmac, bet365-token-formula, swt-pstk-hmac]
tags: [bet365, reverse-engineering, websocket, authentication, security-research]
sources:
  - "daily/lcash/2026-05-06.md"
created: 2026-05-06
updated: 2026-05-07
---

# bet365 xcft Token HMAC Forgery

On 2026-05-06, lcash reverse-engineered the bet365 `X-Net-Sync-Term` (xcft) token generation algorithm: it is `base64url(HMAC-SHA256(key=raw_bytes(swt_cookie), message=raw_bytes(pstk_session_id)))`. This is fully reproducible in Python using only the `hmac` standard library module and two cookies — no JavaScript execution, no browser, no obfuscated bundle parsing required. The discovery eliminates the browser dependency for WebSocket authentication, potentially enabling standalone Python WS clients for real-time odds streaming.

## Key Points

- **Token formula**: `xcft = base64url(HMAC-SHA256(swt_cookie_bytes, pstk_session_id_bytes))` — two cookies, one HMAC, fully deterministic
- **`swt` cookie** is the signing key (48 bytes decoded) — rotates on every page navigation, generating a new signing key each load
- **`pstk` cookie** is the message (38-char hex string) — the session identifier, also available in `window.flashvars`
- The token was traced through bet365's ~1029KB obfuscated JS bundle (`wsr` key in routing manifest) containing `WebsocketTransportMethod`, `StandardProtocolConstants`, and HMAC signing via `crypto.subtle`
- Previous understanding was that NST required executing bet365's obfuscated JS via `xcftr`/`xfctReady` custom DOM events — now proven unnecessary
- WS handshake requires: session cookies + `Sec-WebSocket-Protocol: zap-protocol-v2` + permessage-deflate; after 101, server sends `101<id>`, client echoes `100<id>`
- bet365 allows only ONE WS connection per auth token (token is connection-bound); multiple tokens per Chrome session are possible (one per tab)
- `window.SyncManager` is the **browser's native Background Sync API**, NOT bet365's code — a red herring that consumed debugging time

## Details

### The Discovery Path

The investigation began with attempts to understand why `othersportsmatchmarketscontentapi` returned 200/0b from external curl despite correct cookies and NST. The breakthrough came from realizing that NST tokens generated via DOM event dispatch (`xcftr`) were NOT pre-activated server-side — only NSTs that had already been used in a real browser XHR were valid. This led to tracing the token generation through the JS bundle rather than trying to capture pre-made tokens.

The JS bundle analysis revealed the HMAC construction: `crypto.subtle.importKey` imports the `swt` cookie as an HMAC-SHA256 key, `crypto.subtle.sign` signs the `pstk` session ID, and the result is base64url-encoded. The implementation in Python is trivial:

```python
import hmac, hashlib, base64
token = base64.urlsafe_b64encode(
    hmac.new(swt_bytes, pstk_bytes, hashlib.sha256).digest()
).rstrip(b'=').decode()
```

### WS Connection Protocol

The full standalone WS connection sequence is:

1. Extract `pstk` from cookies (or `window.flashvars`)
2. Extract `swt` from cookies
3. Compute `hmac_sha256(swt_raw, pstk_raw)` and base64url encode
4. Open WebSocket with `Sec-WebSocket-Protocol: zap-protocol-v2`, session cookies, and permessage-deflate enabled
5. After server sends `101<connection_id>`, echo back `100<connection_id>`
6. Send auth: `A_<xcft_token>` (bare auth frame)
7. Subscribe to topics: `\x16\x00DKNCK4,A_<xcft_token>` (with subscription prefix)

### Connection Binding Constraint

Each xcft token can only authenticate ONE WebSocket connection. Once a WS is established with a token, the token is "consumed" — attempting to open a second WS with the same token fails. However, multiple tokens can coexist within a single Chrome session (one per tab), since each page navigation generates a fresh `swt` cookie and thus a fresh token.

This constraint means a standalone Python client needs fresh cookies for each WS connection. The practical workflow: extract `pstk` + `swt` from an active browser session, forge the token, connect once. For continuous operation, cookies must be periodically refreshed from the browser.

### Implications for Scraper Architecture

The token forgery eliminates the browser as a mandatory intermediary for WS authentication. Previously, WS streaming required piggybacking on the browser's authenticated connection (see [[concepts/browser-mediated-websocket-streaming]]) because independent Python WS connections received 403. With the forged token, a Python `websockets` client can authenticate directly — no Playwright, no Node.js subprocess pipe, no CDP overhead.

However, two constraints remain: (1) the `swt` cookie rotates on every navigation, so the Python client needs a mechanism to periodically obtain fresh cookies from a browser session, and (2) Cloudflare IP reputation blocking (see [[connections/anti-scraping-driven-architecture]]) still applies to the WS endpoint from datacenter IPs. The forged token solves the application-layer auth but not the network-layer blocking.

### Prior Art: NST Red Herrings

Two significant red herrings consumed debugging time:

1. **`window.SyncManager`** — this is the browser's native Web Background Sync API, not bet365's code. It appeared in the investigation because `SyncManager` shares naming conventions with bet365's sync term, but is completely unrelated.

2. **DOM event dispatch** (`xfctReady`/`xcftr`) — dispatching these custom events inside the page DOES generate NST tokens, but the tokens are not pre-activated server-side. They require at least one real XHR roundtrip to become valid. Generating tokens this way and passing them to external curl still produced 0-byte responses.

## Related Concepts

- [[concepts/browser-mediated-websocket-streaming]] - The piggybacking architecture that xcft forgery could eventually replace for WS auth
- [[concepts/bet365-racing-data-protocol]] - The WS protocol format (subscriptions, binary framing) used after authentication
- [[concepts/websocket-constructor-injection]] - The constructor wrapping technique that captures the browser's WS — no longer the only path to WS access with forged tokens
- [[concepts/bet365-ws-topic-authorization]] - Session-bound P-ENDP topic authorization remains a constraint even with forged tokens — the server still validates topic registrations
- [[connections/anti-scraping-driven-architecture]] - Cloudflare IP blocking at the network layer remains even when application-layer auth is forged
- [[concepts/bet365-in-browser-cdp-fetch-transport]] - The in-browser fetch approach that works without token forgery by leveraging the browser's active WS session

## Sources

- [[daily/lcash/2026-05-06.md]] - xcft token traced to HMAC-SHA256(swt, pstk) via JS bundle analysis; `window.SyncManager` confirmed as browser API not bet365; WS handshake protocol documented (zap-protocol-v2, 101/100 exchange, A_ auth frame); one-connection-per-token constraint; DOM event tokens not pre-activated server-side; `swt` rotates per navigation, `pstk` is 38-char hex session ID (Sessions 10:46, 10:56)
