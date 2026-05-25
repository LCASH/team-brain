---
title: "Discord-Brain MCP Agent Architecture"
aliases: [discord-brain, mcp-agent-search, claude-code-headless-hosting, iterative-search-agent]
tags: [architecture, claude-code, mcp, ai-agent, discord, headless-hosting]
sources:
  - "daily/lcash/2026-05-22.md"
  - "daily/lcash/2026-05-23.md"
created: 2026-05-22
updated: 2026-05-23
---

# Discord-Brain MCP Agent Architecture

On 2026-05-22, lcash upgraded the discord-brain `/ask` feature from fixed-retrieval RAG (stuffing top-30 search hits into a prompt) to a **tool-calling agent** using Claude Code's headless hosting pattern + a pure stdio MCP server. Instead of pre-fetching results and hoping they're relevant, the spawned Claude agent iteratively calls `search_messages`, `get_thread`, and other read-only tools to explore the message database — broadening queries, pulling thread context, and synthesizing answers with citations. This is the core architectural shift: RAG pre-fetches once, agents iterate until they find the answer.

## Key Points

- **Agent over RAG**: Claude iteratively calls MCP search tools instead of receiving pre-fetched top-30 hits — can refine queries, pull thread context, explore related channels
- **Pure stdio JSON-RPC MCP server** (6 read-only tools): `search_messages`, `search_with_context`, `get_thread`, `list_servers`, `list_channels`, `get_stats` — zero external deps
- **Strict tool allowlist**: spawned Claude can ONLY call 6 MCP tools; Bash/Write/Edit/WebFetch/WebSearch all denied — scoped via `--allowedTools` + `settings.json` permissions
- **`stream-json` over `json` output format**: enables SSE streaming of NDJSON events to browser — user sees tool calls happening in real-time before the answer lands
- **120s hard timeout** with SIGTERM→SIGKILL escalation on the claude subprocess; `session_id` persisted for `--resume` on transient failure
- **`acceptEdits` permission mode** + settings.json allowlist is the correct combo for scoped headless agents (NOT `bypassPermissions`)

## Details

### Why Agent Over RAG

The prior `/ask` implementation fetched the top 30 search results from the SQLite database and stuffed them into a Claude prompt. This approach has three limitations: (1) if the answer requires information from result #31 or beyond, it's invisible; (2) if the initial query terms are slightly wrong, all 30 results may be irrelevant; (3) thread context around a matching message is not fetched, losing critical surrounding discussion.

The MCP agent approach solves all three by giving Claude the search tools directly. The agent can:
- Start with a broad search, examine results, then narrow with refined queries
- Follow thread references to pull complete conversation context
- Check multiple channels or servers when the first search returns insufficient data
- Make 5-15 tool calls per question depending on complexity

### Claude Code Headless Hosting Playbook

The implementation follows a portable playbook for deploying Claude Code CLI on any project:

**Auth**: `ANTHROPIC_API_KEY` env var is simplest; OAuth creds from `~/.claude/.credentials.json` also work; Bedrock/Vertex supported for enterprise

**Flags**: `claude -p "prompt" --output-format stream-json --allowedTools "mcp__discord_brain__search_messages,mcp__discord_brain__get_thread,..."` — the `stream-json` format is better than `json` for long runs because progress events can be teed to logs while still parsing the final result envelope

**Permissions**: Combine `--allowedTools` (whitelist tool names) with `settings.json` (whitelist tool arguments) for defense in depth. `--permission-mode acceptEdits` gives the agent permission to use allowed tools without prompting but doesn't grant blanket system access

**MCP Servers**: Configured in `.claude/settings.json` under `"mcpServers"` — auto-discovered by the agent on any host. The discord-brain MCP server uses stdio transport (stdin/stdout JSON-RPC) with no external dependencies

**Process Management**: 120s hard timeout, `session_id` persisted for `--resume`, `SIGTERM→SIGKILL` escalation. The `_find_claude_cli()` fallback chain searches: PATH → `claude_agent_sdk/_bundled/claude` → `~/.claude/local/claude`

### MCP Server Implementation

The MCP server (`src/mcp-server.js`) is a pure stdio JSON-RPC implementation — `readline` + `JSON.parse` + dispatch on `method`. No Express, no HTTP, no external dependencies. Six read-only tools map to SQLite queries:

| Tool | Purpose |
|------|---------|
| `search_messages` | Full-text search across message content |
| `search_with_context` | Search + return surrounding messages (±5 messages by default) |
| `get_thread` | Fetch complete reply thread for a message ID |
| `list_servers` | Enumerate available Discord servers |
| `list_channels` | List channels within a server |
| `get_stats` | Database statistics (message counts, date ranges, active users) |

The agent's `settings.json` explicitly denies `Bash`, `Write`, `Edit`, `WebFetch`, and `WebSearch` — the agent can only read the message database through MCP tools. This makes the spawned process safe to run on any host with the SQLite database.

### SSE Streaming UX

The `stream-json` output format emits NDJSON events during agent execution. The `/ask` Express endpoint pipes these events to the browser as Server-Sent Events. Users see tool calls appearing in real-time (e.g., "Searching for 'deployment error'... Found 12 results... Getting thread context...") before the final synthesized answer arrives. This creates a much better UX than the 30-60 second silent wait of the RAG approach.

### Model Upgrade and Research Quality (2026-05-23)

On 2026-05-23, the default model was switched from Sonnet to **Opus 4.7** for deeper multi-step research queries (~$0.50-$1.50 vs ~$0.30 per deep dive). A smoke test showed 31 tool calls, 0 auto-scoped searches, and proper breadth exploration with rephrasing on empty results. Two research quality improvements were baked into the system prompt: (1) Claude was auto-scoping `search_messages` to a single server even when no filter was set — the prompt now explicitly says "DO NOT pass a server argument unless the user specifies one"; (2) a "build running findings doc → summarize at end" pattern forces proper breadth (minimum 8 searches for deep dive, target 10-15) instead of premature synthesis from a few hits.

A chat history sidebar was also added (`/conversations` and `/conversations/:sessionId` endpoints) so past research runs are browsable from the UI. Per-conversation logging at `data/ask-logs/<session_id>.jsonl` captures the full tool-call chain for post-query analysis of search strategy and synthesis quality. Output rendering was upgraded from raw markdown text to proper HTML with headings, lists, tables, code blocks, and inline 220×160 image thumbnails for attachment URLs.

### Applicability Beyond Discord

The playbook is project-agnostic: any application that needs an AI agent with controlled tool access can follow the same pattern. The key elements — stdio MCP server, tool allowlist, stream-json output, timeout management, session persistence — are reusable across Discord bots, Slack integrations, CLI tools, or web applications.

## Related Concepts

- [[concepts/news-agent-injury-pipeline]] - The news agent pipeline uses Claude Agent SDK's `query()` function for tool-calling agents; discord-brain uses the CLI subprocess pattern instead — both are valid approaches with different tradeoffs (SDK for Python-native, CLI for process isolation)
- [[concepts/podcast-pick-extraction-pipeline]] - The podcast pipeline established the `@tool` + `create_sdk_mcp_server()` pattern; discord-brain's stdio MCP is the Node.js equivalent
- [[concepts/news-agent-stage2-production-scaling]] - Stage 2's `claude -p` subprocess timeout and Windows CMD truncation issues apply to any Claude CLI deployment; the discord-brain playbook addresses these with `stream-json` format and single-line prompts
- [[concepts/discord-brain-army-research-pipeline]] - The Army multi-worker pipeline that builds on this MCP architecture for parallel deep-dive research across multiple bookies
- [[concepts/discord-message-corpus-management]] - The corpus management infrastructure (808K messages, server whitelisting, FTS5 operations) that the MCP agent searches against

## Sources

- [[daily/lcash/2026-05-22.md]] - User shared Claude Code headless hosting playbook; applied to discord-brain: rewrote /ask spawn, built MCP server, scoped permissions; agent over RAG as core architectural shift; 6 read-only MCP tools via pure stdio JSON-RPC; stream-json + SSE for real-time UX; 120s timeout + session_id for resume; acceptEdits + allowedTools for defense in depth; bypassPermissions only for ephemeral workspaces (Sessions 13:59, 14:02)
- [[daily/lcash/2026-05-23.md]] - Model upgraded from Sonnet to Opus 4.7 for deeper research; auto-scoping search bug fixed ("DO NOT pass server argument"); "build running findings → summarize at end" prompt pattern enforces breadth (min 8, target 10-15 searches); chat history sidebar + per-conversation JSONL logging added; output rendering upgraded to proper HTML with image thumbnails; conversation context uses ±10-min time windows not reply chains (Session 11:36)
