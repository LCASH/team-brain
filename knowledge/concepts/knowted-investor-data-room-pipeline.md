---
title: "Knowted Investor Data Room and Fundraise Velocity"
aliases: [data-room, investor-data-room, sends-not-builds, fundraise-velocity, knowted-data-room]
tags: [knowted, investor-relations, fundraise, strategy, operations]
sources:
  - "daily/lcash/2026-06-16.md"
created: 2026-06-16
updated: 2026-06-16
---

# Knowted Investor Data Room and Fundraise Velocity

On 2026-06-16, lcash built a complete investor data room (v1) for Knowted and simultaneously unblocked the stalled fundraise by sending three overdue communications. The dominant insight: the raise was stalling on **sends, not builds** — three of four P0 raise-critical items were blocked by unsent drafts, not unfinished deliverables. Three 5-minute sends (Jeffrey re-chase for banker intros, June investor update, Danny retention touch) moved the raise more than hours of additional building could have. The data room itself covers financial model, cap table, traction metrics, and diligence index — all grounded in documented numbers with soft spots honestly flagged, nothing fabricated.

## Key Points

- **"Sends not builds" insight**: The raise was stalled because three comms were drafted but unsent — not because deliverables were incomplete. Three sends in 15 minutes created more raise momentum than the previous week of building.
- **Data room v1 complete**: `financial-model.csv`, `financial-model-notes.md`, `cap-table.md`, `traction-metrics.md`, `README.md` — grounded in pitch deck numbers, soft spots flagged, zero fabrication
- **Cap table documented**: Jeffrey 55% / Luke 45% + Braedon arrangement; first formal documentation of equity split
- **Three persistent financial model blanks**: exact cash-on-hand, Jeffrey's monthly infrastructure cost, whether Braedon's coverage is a formal arrangement — these recur as blockers across Finance and IR workstreams
- **Single point of failure in investor pipeline**: warmest investor path (banker's 2 intros) runs through a person the system can't name, held only by Jeffrey; fallback direct-ask draft prepared for Thu 18 Jun if silent
- **Jeffrey call completed same day**: All product claims confirmed TRUE, language support is 12 (not unlimited) — this was the key unblock for website copy and ad library (resolves D2 from launch decision register)

## Details

### The Sends-Not-Builds Diagnosis

The fundraise had been stalling for over a week despite continuous work on marketing assets, website copy, competitive analysis, and ad creative. The diagnosis on 2026-06-16 identified that three of four P0 raise-critical items were not waiting for work to be completed — they were waiting for existing work to be **sent**:

| P0 Item | Status Before Jun 16 | Blocker | Resolution |
|---------|---------------------|---------|------------|
| Jeffrey banker intros | Draft ready | Not sent | Sent 16 Jun |
| June investor update | Draft ready | Not sent | Sent 16 Jun |
| Danny retention touch | Draft ready | Not sent | Sent 16 Jun |
| Data room | Not built | Needed building | Built 16 Jun |

Only the data room required actual building work. The other three were "sends" — 5-minute actions that had been deferred while the team focused on building. This pattern — building feels productive while sending feels risky — is a classic founder avoidance behavior where the psychologically harder action (putting work in front of people who can judge it) is deferred in favor of the psychologically safer action (continuing to build in private).

The meta-lesson extends the "output before infrastructure" principle documented in [[connections/output-before-infrastructure-sequencing]]: not only should output precede infrastructure, but **distribution should precede production**. The most valuable use of time is sending completed work, not polishing it further.

### Data Room Architecture

The data room lives at `data-room/` in the Knowted OS repo and contains five documents designed for a VC who opens a folder and needs to form an opinion in under 10 minutes:

**`financial-model.csv`**: Monthly projections grounded in pitch deck numbers — revenue per tier, customer counts, churn assumptions, burn rate. Three cells are explicitly flagged as soft (cash-on-hand, Jeffrey's infra line, Braedon formality) rather than filled with estimates. The model surfaced that runway is effectively zero ($460 AUD/mo burn vs ~$400 AUD MRR), confirming the finance heartbeat finding from [[concepts/knowted-agentic-chief-of-staff-system]].

**`cap-table.md`**: Jeffrey 55% / Luke 45% with a note on Braedon's arrangement. First formal documentation — previously only discussed verbally.

**`traction-metrics.md`**: Whatever exists — waitlist signups, user testing feedback, engagement data. Honest about the pre-revenue state.

**`README.md`**: Diligence index explaining what each file contains and what's explicitly NOT included (legal formation docs, tech architecture diagrams — flagged as follow-ups, not pretended to exist).

### The Banker Single Point of Failure

The warmest investor path runs through a person lcash refers to as "the banker" — Jeffrey's contact described as ex-IPO advisory Hong Kong, now angel investing, met 2 Jun 2026. The system has been carrying this placeholder label with no actual name recorded anywhere. The banker offered two investor intros during the 2 Jun meeting; Jeffrey was supposed to forward these by 9 Jun but hasn't as of 16 Jun (7 days overdue).

This creates a single-point-of-failure in the investor pipeline: the two warmest potential investor conversations are gated on one person forwarding two emails, and only Jeffrey holds the relationship. A fallback direct-ask draft was prepared with a 48-hour deadline — if Jeffrey hasn't forwarded by Thu 18 Jun, Luke sends directly (though this requires the banker's name, which remains unknown).

### Jeffrey Product Truth Confirmation

A 30-minute Jeffrey call on 2026-06-16 confirmed all product claims as TRUE:
- Unlimited recording: confirmed
- Transcription accuracy: confirmed
- Multi-speaker support: confirmed
- No-bot architecture: confirmed
- In-meeting Q&A: confirmed
- **Language support: 12** (corrected from earlier "100+" claim)

This resolves D2 (product-truth matrix) from the [[concepts/knowted-launch-decision-register]], unblocking website copy and the ad library. The language correction from "100+" to "12" is a factual accuracy improvement that prevents a potentially embarrassing claim on public materials.

## Related Concepts

- [[connections/output-before-infrastructure-sequencing]] - The "sends not builds" insight extends this principle: distribution should precede further production, not just output before infrastructure
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The accountability framework that tracks the fundraise cadence; the three sends advance commitments from this plan
- [[concepts/knowted-launch-decision-register]] - D2 (product truth) resolved by Jeffrey call on 16 Jun; D1 (recording consent) remains the longest dependency
- [[concepts/knowted-agentic-chief-of-staff-system]] - Finance heartbeat revealed runway=0; the data room's financial model confirms this with documented numbers
- [[concepts/knowted-expert-knowledge-base-architecture]] - The expert/ directory where the data room findings feed into Finance (area 3) and IR (area 2) — previously the thinnest areas

## Sources

- [[daily/lcash/2026-06-16.md]] - Three sends completed (Jeffrey re-chase, June update, Danny retention); data room v1 built (financial model, cap table, traction metrics); "sends not builds" diagnosis; banker still unnamed (single point of failure); Jeffrey call confirmed all product claims TRUE, 12 languages; three persistent financial model blanks (cash-on-hand, infra cost, Braedon formality); fallback direct-ask draft ready for Thu 18 Jun (Sessions 12:40, 13:17, 15:23)
