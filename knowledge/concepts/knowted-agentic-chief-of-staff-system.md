---
title: "Knowted Agentic Chief-of-Staff System"
aliases: [knowted-os, business-os, dept-heartbeat, asks-ledger, skill-smith, agentic-cos]
tags: [knowted, architecture, ai-agent, automation, business-os, claude-code]
sources:
  - "daily/lcash/2026-06-12.md"
created: 2026-06-12
updated: 2026-06-12
---

# Knowted Agentic Chief-of-Staff System

On 2026-06-12, lcash built an autonomous "business OS" for Knowted using Claude Code remote agents. The system is structured around three core engines: a dept-heartbeat reusable skill that sweeps across all business functions, an asks-ledger that progressively grows the agent's access to external systems, and a skill-smith that evolves the agent's own capabilities over time. The cloud routine runs weekly on Monday 06:30 Brisbane (Sun 20:30 UTC) as a free backup, while local manual runs retain superior capability through access to AdsPower, Perplexity, and Google Drive.

## Key Points

- **Dept-heartbeat skill**: Reusable engine accepting sales/marketing/investor-relations/finance/legal/people/strategy/customer-success/1-8/all as parameters; produces one-line-per-department briefings written to weekly-briefing.md
- **Two evolution engines**: Asks-ledger grows ACCESS (one ask per run, resolved asks become permanent "gained" capabilities, never re-asked); skill-smith grows SKILLS (closing step of dept-heartbeat, only touches .claude/skills/**, additive/reversible via git, one change per run, never weakens safety/voice, never grants act-power)
- **Cloud routine**: Scheduled via Claude Code remote agents (routine ID trig_011bAmUD9vATJhhZKufMycMb, env env_01KpozgE7RnQtZHpa3sJzm43); agents are ephemeral/sandboxed with less capability than local runs
- **Private repo**: LCASH/knowted-os (74 markdown files, 492K) created for cloud agent access
- **Finance heartbeat revealed runway is 0**: burn ~$460 AUD/mo vs ~$400 AUD MRR

## Details

### Architecture and Execution Model

The system is built as a reusable skill engine rather than a monolithic script. The dept-heartbeat skill accepts a department parameter and runs a structured sweep: gather context, assess status, identify blockers, propose next actions, and write output. When called with "all", it iterates across every department in sequence. The weekly briefing follows strict formatting anti-patterns: one line per department, de-duplicate cross-department items, never red-flag without a recovery step, and escalate based on days-since-movement rather than zero outcomes.

The user initially explored a VPS always-on architecture but pivoted to local manual mode, parking the VPS design at expert/agent-computer-vps.md. The cloud routine was left running as a free weekly backup rather than the primary execution path. This decision was driven by the recognition that local runs have materially more capability -- AdsPower for browser automation, Perplexity for research, and Google Drive for document access are all unavailable in the ephemeral cloud sandbox.

### Evolution Engines

The asks-ledger and skill-smith represent two distinct growth vectors. The asks-ledger manages a queue of access requests (API keys, service credentials, file permissions) with a strict one-ask-per-run discipline. Once an ask is resolved, it becomes a permanent capability displayed as a green "gained" card and is never re-asked. This prevents the agent from repeatedly requesting the same access and creates a visible record of capability accumulation.

The skill-smith operates under tighter constraints. It only modifies files under .claude/skills/**, makes exactly one change per run, and all changes must be additive and reversible via git. Critical safety boundaries are enforced: changes must never weaken safety or voice guidelines, and must never grant act-power (send, spend, or delete operations remain human-gated). Every change is logged to evolution-log.md for auditability.

### Initial Heartbeat Outputs

The IR heartbeat drafted four artifacts during the first run: jeffrey-chase-banker-intros, banker-intro-followup, investor-1pager, and monthly-update-june-2026. The finance heartbeat surfaced a critical finding: runway is effectively zero, with monthly burn of approximately $460 AUD against approximately $400 AUD MRR. This immediate surfacing of a material financial constraint validated the dept-heartbeat approach as a discovery mechanism, not just a reporting tool.

## Related Concepts

- [[concepts/self-evolving-operational-skill]] - The broader pattern of skills that modify their own capabilities over time, which the skill-smith instantiates
- [[connections/output-before-infrastructure-sequencing]] - The sequencing principle that drove building the OS after establishing content output
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The accountability framework that the dept-heartbeat now automates monitoring of
- [[concepts/knowted-content-first-gtm-strategy]] - The GTM strategy that the marketing heartbeat tracks progress against

## Sources

- [[daily/lcash/2026-06-12.md]] - Full build session: dept-heartbeat skill engine, asks-ledger + skill-smith dual evolution, cloud routine scheduling (trig_011bAmUD9vATJhhZKufMycMb), LCASH/knowted-os repo creation (74 files, 492K), VPS pivot to local manual, IR heartbeat 4 artifacts, finance heartbeat runway=0 ($460 burn vs $400 MRR), anti-patterns codified (Session times)
