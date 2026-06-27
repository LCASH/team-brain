---
title: "Knowted Investor Data Room Build"
aliases: [data-room, investor-data-room, sends-not-builds, fundraise-velocity, knowted-financial-model]
tags: [knowted, investor-relations, fundraise, strategy, data-room, operations]
sources:
  - "daily/lcash/2026-06-16.md"
  - "daily/lcash/2026-06-27.md"
created: 2026-06-16
updated: 2026-06-27
---

# Knowted Investor Data Room Build

On 2026-06-16, lcash built Knowted's investor data room (P0 #2 from the accountability framework) as a complete package: `financial-model.csv`, `financial-model-notes.md`, `cap-table.md`, `traction-metrics.md`, and `README.md` — all grounded in existing pitch deck numbers with soft spots honestly flagged. The most important insight from the day was that the raise had been stalling on **sending, not building** — three of four P0 raise tasks were blocked by unsent drafts (Jeffrey re-chase, investor update, Danny retention), not unfinished deliverables. Three 5-minute sends moved the raise more than hours of building.

## Key Points

- **"Sends not builds" diagnosis**: Three of four P0 raise tasks were blocked by unsent drafts, not missing work — three 5-minute sends (Jeffrey re-chase, June investor update, Danny retention) moved the raise more than hours of building
- **Data room v1 complete**: financial-model.csv, cap-table.md (Jeffrey 55 / Luke 45 + Braedon arrangement), traction-metrics.md, diligence index — nothing fabricated, soft spots flagged
- **Three persistent financial model blanks**: exact cash-on-hand, Jeffrey's infrastructure cost line, whether Braedon's monthly coverage is formally structured — these recur as blockers across Finance and IR workstreams
- **Banker identity gap**: The warmest investor intro path runs through a contact the system can't name — only Jeffrey holds the relationship; single point of failure for the raise pipeline
- **Sent 16 Jun**: Jeffrey re-chase on banker intros, June investor update to banker + Braedon, Danny retention touch — first real raise movement in over a week
- **Fallback draft ready**: If Jeffrey is silent on forwarding banker intros by Thu 18 Jun, a direct-ask draft is staged

## Details

### The "Sends Not Builds" Insight

The fundraise had been stalling for over a week despite significant deliverable production (data room, ICP research, ad creative pipeline, website iterations). Investigation of the P0 task list revealed that three of the four highest-priority raise tasks were **already written** — they were draft emails and messages sitting unset in the admin repo. The blocking factor was the act of pressing send, not the act of creating content.

This is a specific instance of the broader pattern documented in [[connections/output-before-infrastructure-sequencing]]: building infrastructure (data room, pitch deck, financial models) without shipping the output (sending the emails, forwarding the intros, scheduling the calls) is the founder trap applied to fundraising. The data room IS necessary — VCs need something to open — but sending the relationship-maintenance emails takes 5 minutes each and directly generates pipeline movement, while the data room passively waits for someone to request it.

Three sends were completed on June 16:
1. **Jeffrey re-chase**: Reminder on the 2 banker intros now 7 days overdue (originally due Jun 9)
2. **June investor update**: Monthly progress update to the banker and Braedon, maintaining relationship warmth
3. **Danny retention touch**: Outreach to a potential reference account

### The Data Room

The data room was built at `data-room/` in the Knowted OS repo with five files:

| File | Contents | Notes |
|------|----------|-------|
| `financial-model.csv` | Monthly projections, burn rate, runway | ~$460 AUD/mo burn vs ~$400 AUD MRR; 3 placeholder cells flagged |
| `financial-model-notes.md` | Assumptions, methodology, limitations | Grounded in deck numbers, nothing fabricated |
| `cap-table.md` | Jeffrey 55% / Luke 45% + Braedon arrangement | Equity split documented for first time |
| `traction-metrics.md` | User counts, MRR, pipeline, milestones | Honest current state with growth trajectory |
| `README.md` | Diligence index for investors | Links to all assets, explains what's available |

The data room fills the gap identified in [[concepts/knowted-cofounder-accountability-banker-feedback]]: a VC or angel investor presented with the pitch deck previously had nothing to drill into. Now there is a structured set of documents that can be shared as a follow-up to any investor conversation.

### Persistent Financial Model Blanks

Three values remain as persistent placeholders across multiple workstreams:

1. **Exact cash-on-hand**: The finance heartbeat (Jun 12) flagged ~$460/mo burn vs ~$400 MRR but exact available cash was never confirmed
2. **Jeffrey's infrastructure cost**: A line item in the financial model that Luke can't fill — only Jeffrey knows the real hosting/infra spend
3. **Braedon arrangement formality**: Monthly coverage that bridges the burn-MRR gap, but whether it's a formal loan, equity arrangement, or informal support is unrecorded

These blanks recur as blockers in the Finance expert area, the IR expert area, and the data room — a 30-minute Jeffrey call would resolve all three simultaneously.

### Banker Single Point of Failure

The warmest investor pipeline path runs through a contact described only as "the banker" — an ex-IPO advisory professional from Hong Kong, now angel investing, who met with Jeffrey on 2 Jun 2026. The system has been carrying this placeholder label since the accountability framework was built (Jun 4). The banker offered 2 investor introductions that Jeffrey was supposed to forward by Jun 9 — now 7 days overdue. Luke confirmed he knows who the person is but the name remains unrecorded in any system artifact.

This creates a single point of failure: the warmest intro path is mediated by Jeffrey, referenced by a label nobody else can act on, and overdue by a week. The fallback direct-ask draft (staged if silence continues past Thu Jun 18) provides a workaround but doesn't address the structural risk of the relationship being held by one person with the identity unrecorded.

## Related Concepts

- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The accountability framework that identified P0 #2 (data room) and the banker intro pipeline; this article documents the completion of P0 #2 and the operational discovery that sends were the bottleneck
- [[connections/output-before-infrastructure-sequencing]] - The "sends not builds" insight is a fundraise-specific instance of "infrastructure without output is the classic founder trap"
- [[concepts/knowted-agentic-chief-of-staff-system]] - The finance heartbeat that surfaced runway=0 ($460 burn vs $400 MRR) feeding into the financial model
- [[concepts/knowted-expert-knowledge-base-architecture]] - Finance and IR identified as thinnest expert areas despite being most raise-critical; the data room fills the IR gap

## Sources

- [[daily/lcash/2026-06-16.md]] - Data room built (financial model, cap table, traction metrics, README); "sends not builds" diagnosis — 3 sends completed (Jeffrey re-chase, investor update, Danny retention); cap table: Jeffrey 55 / Luke 45 + Braedon; 3 persistent financial model blanks (cash, infra cost, Braedon formality); banker identity gap — warmest intro path runs through unnamed contact, 2 intros 7 days overdue; fallback direct-ask draft staged for Thu 18 Jun (Sessions 12:40, 13:17, 15:23)
- [[daily/lcash/2026-06-27.md]] - P0 items 1-4 confirmed done by user (Jeffrey re-chase sent, June investor update sent, Danny touch sent, D2 cleared); Jeff plan drafted covering website go-live, waitlist endpoint, product claims, and data room completion; user didn't know what "data room" meant — investor jargon landed badly, keep terminology plain when talking to founders; infra cost still outstanding from Jeff; consider copying `data-room/` to shareable Google Drive folder (Session 14:13)
