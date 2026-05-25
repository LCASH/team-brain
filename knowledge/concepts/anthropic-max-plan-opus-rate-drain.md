---
title: "Anthropic Max Plan Opus Rate Drain"
aliases: [opus-rate-drain, anthropic-rate-limit, max-plan-budget, oauth-5-hour-window, opus-budget-multiplier]
tags: [ai-agent, anthropic, rate-limiting, operations, cost]
sources:
  - "daily/lcash/2026-05-23.md"
created: 2026-05-23
updated: 2026-05-23
---

# Anthropic Max Plan Opus Rate Drain

Anthropic's Max plan has a 5-hour rolling rate limit window where Opus calls consume 5-10x more budget than Sonnet calls. On 2026-05-23, the Discord Brain Army pipeline's parallel battery (~70 simultaneous Opus calls across 7 bookies) drained the OAuth bucket, causing synth2 (the consolidation pass — typically the largest single prompt at ~50KB) to silently return $0 output. The `status: allowed` field in the API response is misleading when the bucket is depleted — small chatty requests still work while large requests fail silently. The rate limit is per-account (tied to the OAuth email), not per-token, so re-authenticating provides no relief.

## Key Points

- **Opus consumes 5-10x more budget** than Sonnet in the 5-hour rolling window — ~30+ Opus calls (including parallel battery of ~80) can drain the entire budget
- **Large requests fail first**: Synth2 (~50KB prompt) silently rate-limited while small chatty requests still work — the `status: allowed` is misleading
- **Per-account, not per-token**: Rate limit bucket is tied to the OAuth email (b8steel@gmail.com Max plan), not the auth token — re-authenticating doesn't help
- **`rate_limit_event` in stream** should be detected and surfaced as "rate limited, partial result" in SSE UI — currently produces silent $0 output with no user-visible error
- **Mitigation paths**: (1) switch Army runs to Sonnet (`CLAUDE_MODEL=claude-sonnet-4-6`) for lower budget consumption, (2) use `ANTHROPIC_API_KEY` env var for heavy iteration days to bypass OAuth window, (3) synth2 prompt compression (60K→18K chars) to fit within throttled capacity
- **Bun segfault appeared during rate-limited synth2** — transient bug in bundled Bun runtime inside `claude` CLI binary, not application code

## Details

### The Budget Drain Mechanism

The Anthropic Max plan allocates a rolling 5-hour usage budget. Each API call deducts from this budget based on model and token count. Opus calls deduct at a significantly higher rate than Sonnet — empirically 5-10x based on the observation that ~30+ Opus calls (which would be routine for 300+ Sonnet calls) depleted the window.

The Army pipeline's 7-bookie parallel battery was the trigger: each bookie spawned 2-7 primary workers + 2-5 followup workers + 1 synth2 pass, all using Opus. At peak parallelism, ~70 Opus subprocesses were running simultaneously. While each individual call was within normal bounds, the aggregate consumption across all 7 concurrent armies exceeded the 5-hour budget within ~2 hours.

### Silent Failure Mode

The rate limit manifests as a silent output failure rather than an explicit error. When synth2 was rate-limited, the Claude CLI subprocess ran normally (no crash, no error output), but the response contained zero content — `$0 output` in cost terms. The orchestrator saw a completed subprocess with empty results, which could be misinterpreted as "no findings to consolidate" rather than "rate limited."

The `rate_limit_event` field appears in the streaming response but the discord-brain SSE pipeline didn't detect or surface it. This is a detection gap: the UI should display "rate limited, partial result" instead of presenting an empty synthesis as if it were a genuine finding.

### The Per-Account Constraint

A critical operational finding: the rate limit is tied to the OAuth account email, not the authentication token. Re-authenticating (obtaining a new token for the same email) does not reset or bypass the rate limit. The budget is tracked server-side per account, and all tokens issued to that account share the same rolling window.

This means the only ways to get more budget are: (1) wait for the 5-hour window to roll past the high-usage period, (2) use a different account, or (3) switch to an API key (`ANTHROPIC_API_KEY` env var) which has separate rate limits from the OAuth path.

### Mitigation Strategy

Three complementary mitigations were identified:

1. **Model downgrade for bulk work**: Switch Army runs to Sonnet via `CLAUDE_MODEL=claude-sonnet-4-6`. Sonnet consumes dramatically less budget per call and produces adequate quality for structured search+synthesis tasks. Reserve Opus for the `/ask` single-query deep dives where reasoning quality matters most.

2. **API key fallback**: Set `ANTHROPIC_API_KEY` in `.env` for heavy iteration days. API key rate limits are separate from OAuth limits and may have different thresholds. This provides a manual escape valve when the OAuth budget is drained.

3. **Prompt compression**: The synth2 prompt compression (60K→18K chars — see [[concepts/discord-brain-army-research-pipeline]]) reduces the per-call budget consumption by ~3.3x, making the same work fit within a tighter budget window.

## Related Concepts

- [[concepts/discord-brain-army-research-pipeline]] - The Army pipeline whose parallel battery triggered the rate drain; synth2 prompt compression was deployed as a direct mitigation
- [[concepts/discord-brain-mcp-agent-architecture]] - The MCP agent architecture that uses the same Opus model; single /ask queries are less affected due to lower total token consumption
- [[concepts/news-agent-stage2-production-scaling]] - Stage 2's Sonnet cost optimization ($0.60/event) demonstrates that structured research tasks can use cheaper models without quality loss

## Sources

- [[daily/lcash/2026-05-23.md]] - TABtouch v7 synth2 silently rate-limited ($0 output) from 5-hour OAuth window drain; ~70 concurrent Opus calls across 7-bookie battery was the trigger; `status: allowed` misleading; re-auth doesn't help (per-account not per-token); Bun segfault during rate-limited call; Opus drains 5-10x faster than Sonnet; ANTHROPIC_API_KEY bypass suggested (Sessions 14:18, 14:49). Synth2 prompt compression 60K→18K as mitigation (Session 14:49)
