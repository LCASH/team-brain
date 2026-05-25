---
title: "Supabase Edge Runtime URL Signature Verification Bug"
aliases: [edge-runtime-url-bug, twilio-signature-failure, supabase-req-url-internal, webhook-url-mismatch]
tags: [takeover, supabase, twilio, security, bug, deployment]
sources:
  - "daily/lcash/2026-05-25.md"
created: 2026-05-25
updated: 2026-05-25
---

# Supabase Edge Runtime URL Signature Verification Bug

Inside Supabase Edge Functions, `req.url` returns the **internal** runtime URL (e.g., `http://edge-runtime.supabase-demo.com:8001/receive-sms`), not the public webhook URL (e.g., `https://xxx.supabase.co/functions/v1/receive-sms`). Any signature verification that hashes `req.url` — including Twilio, Stripe, and other webhook providers — will silently reject ALL legitimate requests because the URL used for hashing doesn't match the URL Twilio signed against. Discovered on 2026-05-25 when inbound SMS stopped arriving on May 18 after commit `43c8802` added Twilio signature verification to the `receive-sms` edge function.

## Key Points

- **`req.url` inside Edge Functions returns the internal runtime URL**, not the public-facing URL that webhook providers sign against — signature verification silently fails for all legitimate webhooks
- **Commit `43c8802` (May 18) introduced the break**: security hardening that added Twilio signature verification wasn't tested with real inbound traffic — all SMS silently rejected for 7 days
- **Fix: multi-URL-candidate approach** — try canonical `SUPABASE_URL` first, then `req.url`, then `x-forwarded-*` headers; use whichever URL produces a valid Twilio signature
- **47 missed messages recovered** via Twilio REST API backfill with `metadata.backfilled=true` and original `MessageSid` as `external_id` for dedup
- The pattern applies to **any webhook signature verification in Supabase Edge Functions** — Stripe, GitHub, Slack, etc. all sign against the public URL
- **Zero error signal for 7 days**: the signature check returned `false`, the function responded with 403, Twilio marked the message as failed and moved on — no logs, no alerts, no SMS delivered

## Details

### The URL Mismatch Mechanism

Webhook signature verification works by both the sender and receiver computing HMAC-SHA256 (or equivalent) over the same inputs: the request body and the **request URL**. Twilio signs against the public URL it sends the webhook to: `https://xxx.supabase.co/functions/v1/receive-sms`. When the Edge Function receives the request, it needs to compute the same HMAC using the same URL.

Inside Supabase Edge Functions, `req.url` returns the internal Deno runtime URL — something like `http://edge-runtime.supabase-demo.com:8001/receive-sms`. This is the URL as seen by the Deno process, not the public URL that Twilio sent the request to. The HMAC computed with this internal URL doesn't match Twilio's signature, so verification fails — silently, on every single request.

The fix reconstructs the public URL from the `SUPABASE_URL` environment variable plus the function path. A multi-candidate approach tries several URL reconstructions:

1. `${SUPABASE_URL}/functions/v1/receive-sms` (canonical)
2. `req.url` (internal — unlikely to work but included as fallback)
3. Reconstruction from `x-forwarded-host` and `x-forwarded-proto` headers

Whichever candidate produces a matching Twilio signature is used.

### The 7-Day Silent Outage

The security hardening in commit `43c8802` (dated May 18) was never tested with real inbound Twilio traffic before deployment. It was tested locally or against a different Supabase environment where the URL mismatch may not exist (localhost is a secure context with different URL handling). In production, every inbound SMS from May 18 to May 25 was silently rejected.

The failure was invisible because:
- Edge Functions don't have persistent logging unless explicitly configured
- Twilio marks failed deliveries in its dashboard, but nobody checked
- The TAKEOVER app continued to function for all other features — only inbound SMS was broken
- No automated alert existed for "zero inbound SMS in N hours"

### Twilio Message Backfill

47 messages from the 7-day gap were recovered via the Twilio REST API (`messages.list(dateSent=after_date)`) and inserted into Supabase with `metadata.backfilled=true` and the original Twilio `MessageSid` as `external_id`. The `external_id` field enables dedup — if the edge function had partially processed any messages, the backfill won't create duplicates.

### General Applicability

This bug applies to **any webhook signature verification** running inside Supabase Edge Functions — not just Twilio. Any provider that includes the URL in its signature computation (Twilio, Stripe, GitHub, Slack) will fail the same way. The fix pattern (reconstruct public URL from env vars rather than trusting `req.url`) should be applied proactively to all webhook handlers in Edge Functions.

## Related Concepts

- [[concepts/takeover-shared-role-security-lockdown-collateral]] - The same security hardening session (May 18-19) that broke TAKEOVER staff DB access also broke Twilio SMS — security changes with insufficient live testing
- [[connections/silent-type-coercion-data-corruption]] - The URL mismatch produces a "plausible wrong output" — the signature check returns `false` (a valid boolean), the function returns 403 (a valid HTTP status) — no crash, no error, just silently wrong
- [[concepts/deploy-syntax-validation-gap]] - Another deployment that wasn't tested against real traffic; the Twilio fix emphasizes the need for integration tests on webhook flows

## Sources

- [[daily/lcash/2026-05-25.md]] - Supabase Edge Runtime `req.url` returns internal URL not public; commit `43c8802` (May 18) added Twilio signature verification that silently broke all inbound SMS for 7 days; fix: multi-URL-candidate approach (SUPABASE_URL, req.url, x-forwarded headers); 47 messages backfilled via Twilio REST API with MessageSid dedup; pattern applies to any webhook signature verification in Edge Functions (Session 10:52)
