---
title: "Knowted Expert Knowledge Base Directory Architecture"
aliases: [expert-directory, knowted-expert-kb, per-area-knowledge-folders, durable-vs-sprint-knowledge]
tags: [knowted, architecture, knowledge-management, organization, founder-operations]
sources:
  - "daily/lcash/2026-06-13.md"
created: 2026-06-13
updated: 2026-06-13
---

# Knowted Expert Knowledge Base Directory Architecture

On 2026-06-13, lcash created an `expert/` knowledge base directory for Knowted with one folder per business area (8 areas for Luke, 6 for Jeffrey), each anchored by an `expert.md` file following a consistent 8-section template. The mental model separates three persistence tiers: `expert/` holds compounding durable knowledge that grows over time, `workstreams/` holds sprint-scoped artifacts that are archived when done, and `STATUS.md` serves as the navigational map across both. This architecture emerged from the cofounder operating guide work that formalized the two-domain responsibility split.

## Key Points

- **8 expert areas for Luke**: sales/marketing/outreach, investor relations, finance/operations, legal/compliance, partnerships, content, customer success, competitive intelligence — each gets `expert/{N}-{area}/expert.md`
- **Consistent 8-section template**: Mandate → Current state → Workstream links → Playbook → Decision log → Open questions → Resources → Learning log (append-only)
- **Three persistence tiers**: `expert/` = compounding durable knowledge; `workstreams/` = archived-when-done sprints; `STATUS.md` = the map connecting both
- **Learning log is append-only** — captures insights that compound across workstreams; a workstream ends but its lessons persist in the expert area's learning log
- **Surfaced a strategic gap**: the operating guide names investor pipeline and financial model as P0 #1-2, but these expert areas (`2-investor-relations/`, `3-finance-operations/`) were identified as the thinnest — most raise-critical areas have no active workstream with July raise looming

## Details

### The Three-Tier Knowledge Architecture

The Knowted admin repository evolved from a flat `workstreams/` structure (where each workstream like `pricing/`, `outreach-gtm/`, `pitch-deck/` held all related artifacts) to a two-layer model that distinguishes knowledge lifecycle:

**`expert/` (durable, compounding):** Each of Luke's 8 responsibility areas gets a folder containing an `expert.md` anchor file. This file accumulates domain expertise that transcends any single workstream: playbooks for recurring tasks, decision logs for precedent, open questions that persist across sprints, and an append-only learning log. When a pricing workstream concludes, the pricing decisions and lessons learned are captured in `expert/1-sales/expert.md` — the workstream archive can be deleted, but the knowledge persists.

**`workstreams/` (sprint-scoped, archivable):** Active projects with defined start/end dates and deliverables. The pricing pivot (`workstreams/pricing/`), pitch deck rewrite (`workstreams/pitch-deck/`), and co-founder search (`workstreams/cofounder-search/`) each have their own folder with working artifacts. When a workstream completes, its folder is archived and its durable insights are migrated to the relevant `expert/` area.

**`STATUS.md` (navigational map):** A single-screen overview linking to both active workstreams and expert areas, with progress indicators and blockers. Designed for the weekly cofounder sync where both Luke and Jeffrey need the full picture without drilling into individual files.

### The 8-Section Expert Template

Each `expert.md` follows a standardized structure that balances reference material with living documentation:

| Section | Purpose | Update Cadence |
|---------|---------|----------------|
| Mandate | What this area is responsible for | Rarely — only on role changes |
| Current state | Latest assessment of health | Weekly or on significant events |
| Workstream links | Pointers to active sprints | As workstreams start/end |
| Playbook | Repeatable procedures and runbooks | When new procedures are established |
| Decision log | Key decisions with rationale and date | On each decision |
| Open questions | Unresolved issues requiring attention | As questions surface |
| Resources | External links, tools, contacts | As discovered |
| Learning log | Append-only insights from experience | After each significant learning |

The append-only learning log is architecturally important: it prevents knowledge loss when operators rotate areas or when historical context becomes relevant months later. Unlike decision logs (which track what was decided), the learning log tracks what was learned — including lessons from failures, surprising findings, and validated/invalidated hypotheses.

### Strategic Gap Discovery

The expert/ build-out itself served as a diagnostic tool. By mapping all 8 areas and assessing their "current state," the thinnest areas became immediately visible. Investor Relations (area 2) and Finance/Operations (area 3) — the two most raise-critical areas with the July raise approaching — had no active workstreams, no playbooks, and no decision logs. Recent work had been heavily weighted toward Marketing/Content/Competitive Analysis (areas 1, 7, 8), which are important but not raise-blocking.

This gap was flagged for the next cofounder review: P0 #1 (investor pipeline) and P0 #2 (financial model + data room) need active workstreams before the July raise timeline becomes critical.

### Relationship to Team Knowledge Base

The `expert/` pattern is conceptually parallel to the team knowledge base's `knowledge/concepts/` directory (see [[concepts/team-knowledge-base-architecture]]): both maintain durable, cross-referenced knowledge articles that compound over time. The key difference is that the team KB is LLM-compiled from daily logs (automated extraction), while Knowted's `expert/` is human-maintained (manual curation augmented by AI assistance). Both follow the principle that knowledge should outlive the activity that produced it.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The shared team KB that inspired the durable-knowledge-vs-sprint-artifacts separation; same compiler analogy (source → compiled knowledge)
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The cofounder operating guide that defined the 8-area responsibility split; the expert/ directory operationalizes this split as a knowledge architecture
- [[concepts/knowted-agentic-chief-of-staff-system]] - The dept-heartbeat skill iterates these same 8 areas; expert/ provides the durable context that the heartbeat reads and updates
- [[concepts/knowted-content-first-gtm-strategy]] - Content/marketing workstreams feed into `expert/1-sales/` and `expert/7-content/`; the expert areas persist after individual GTM sprints conclude

## Sources

- [[daily/lcash/2026-06-13.md]] - Created `expert/` directory with one folder per business area (8 for Luke), each with `expert.md` following 8-section template (Mandate → Current state → Workstream links → Playbook → Decision log → Open questions → Resources → Learning log); three-tier model: expert/ = durable, workstreams/ = sprint, STATUS.md = map; strategic gap surfaced: Finance and IR are thinnest areas despite being P0 #1-2 for July raise (Session 11:09, second session)
