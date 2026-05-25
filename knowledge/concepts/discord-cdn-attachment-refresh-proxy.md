---
title: "Discord CDN Attachment URL Refresh Proxy"
aliases: [discord-cdn-proxy, attachment-refresh, cdn-url-expiry, discord-signed-urls]
tags: [discord, architecture, proxy, cdn, attachments]
sources:
  - "daily/lcash/2026-05-23.md"
created: 2026-05-23
updated: 2026-05-23
---

# Discord CDN Attachment URL Refresh Proxy

Discord CDN attachment URLs (`cdn.discordapp.com/attachments/...`) include signed parameters that expire approximately 24 hours after the message was sent (Discord began requiring signed URLs in late 2023). Research reports that reference Discord attachments — promotional screenshots, betting slips, market comparisons — produce dead links within a day of generation. On 2026-05-23, a `/attachment/refresh?url=...` proxy endpoint was built that calls Discord's official `/attachments/refresh-urls` API, receives a freshly-signed URL, and 302-redirects the browser. All synth output attachment URLs are auto-rewritten client-side to use this proxy.

## Key Points

- Discord CDN URLs expire ~24h after message creation due to signed parameter expiry (introduced late 2023)
- **`/attachment/refresh?url=...`** proxy calls Discord's `/attachments/refresh-urls` API and 302-redirects to the freshly-signed URL — transparent to the user
- Client-side auto-rewrite: all `cdn.discordapp.com/attachments/` URLs in synth output are rewritten to route through the proxy endpoint
- Fastify `reply.redirect()` takes `(url, code)` not `(code, url)` — args were backwards causing 502 on initial deployment
- The proxy is stateless and requires no caching — each click generates a fresh signed URL on demand
- Synth2 output includes a `## Relevant attachments` section with categorized URLs; betr test produced 62 categorized attachment URLs

## Details

### The URL Expiry Problem

When Discord introduced signed attachment URLs in late 2023, all CDN URLs began including query parameters (`ex=`, `is=`, `hm=`) that encode an expiry timestamp and HMAC signature. After expiry, the CDN returns HTTP 404 regardless of whether the underlying file still exists. This broke any workflow that stores or references Discord CDN URLs long-term — knowledge bases, research reports, documentation.

For the Discord Brain Army pipeline (see [[concepts/discord-brain-army-research-pipeline]]), this means the synth2 research reports contain attachment URLs (promo screenshots, betting slips, market screenshots) that become dead links within a day. The reports are intended for long-term reference, making expired URLs a fundamental usability problem.

### The Refresh Proxy Pattern

Discord provides an official API endpoint (`/attachments/refresh-urls`) that accepts expired CDN URLs and returns freshly-signed equivalents. The proxy wraps this API call behind a simple HTTP endpoint:

1. Browser requests `/attachment/refresh?url=https://cdn.discordapp.com/attachments/...`
2. Proxy extracts the original URL from the query parameter
3. Proxy calls Discord's refresh API with the bot token
4. Discord returns a new signed URL valid for another ~24h
5. Proxy 302-redirects the browser to the fresh URL

This is transparent to the user — clicking an attachment link in a research report triggers the proxy, which silently refreshes and redirects. The proxy is stateless (no URL caching needed) because each refresh call is cheap and Discord's API handles the signing server-side.

### Client-Side URL Rewriting

All URLs matching `cdn.discordapp.com/attachments/` in synth2 output are auto-rewritten to use the proxy endpoint before rendering in the browser. This happens at display time, not at storage time — the original Discord CDN URLs are preserved in the database and synth output for provenance. The rewrite is a simple string replacement in the markdown rendering pipeline.

### Attachment Capture in Research

The Army pipeline's MCP `search_messages` and `get_thread` tools now surface up to 3 attachment URLs per message (agent-judged relevance — the worker prompt instructs to include only plausibly-relevant attachments like promo screenshots, betting slips, and market shots, skipping tenor gifs and generic links). The synth2 consolidation pass deduplicates and categorizes attachments across all workers.

## Related Concepts

- [[concepts/discord-brain-army-research-pipeline]] - The Army pipeline that produces research reports containing attachment URLs; the proxy ensures these reports remain usable long-term
- [[concepts/discord-brain-mcp-agent-architecture]] - The MCP agent architecture whose search tools now surface attachment URLs alongside message content
- [[concepts/discord-message-corpus-management]] - The corpus management system where attachment metadata is stored alongside message content

## Sources

- [[daily/lcash/2026-05-23.md]] - Discord CDN URLs expire ~24h from signed params; `/attachment/refresh?url=...` proxy built calling Discord's refresh-urls API with 302 redirect; Fastify redirect arg order bug (url, code not code, url → 502); client-side auto-rewrite of cdn.discordapp.com URLs; betr Army test produced 62 categorized attachment URLs in synth2 output; Phase 1 of 3-phase attachment strategy (URL passthrough → fetch_url MCP tool → bulk pre-index) (Sessions 14:18, 14:49)
