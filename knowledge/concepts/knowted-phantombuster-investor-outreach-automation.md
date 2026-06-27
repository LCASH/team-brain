---
title: "Knowted PhantomBuster Investor Outreach Automation"
aliases: [phantombuster-investor-dms, linkedin-investor-sequence, automated-investor-outreach, phantombuster-3-touch-sequence]
tags: [knowted, outreach, investor-relations, linkedin, phantombuster, automation]
sources:
  - "daily/lcash/2026-06-27.md"
created: 2026-06-27
updated: 2026-06-27
---

# Knowted PhantomBuster Investor Outreach Automation

On 2026-06-27, lcash configured a PhantomBuster-based automated LinkedIn DM campaign targeting 35 connected investors. The system uses a 3-touch automated sequence (opener → bump at +3 days → bump at +5 days) with a reply-triggered hand-sent path for engaged investors. Rate-limited to 10 messages/day on weekdays at 10:15 Brisbane time, the campaign reaches all 35 investors in approximately 4 working days. An existing "LinkedIn Message Sender" phantom was repurposed as "Investor Message Sender" because the PhantomBuster plan caps at 5 phantoms (already at 7 — no new phantom card created).

## Key Points

- **3-touch automated sequence**: Touch 1 (opener DM) → Bump 1 (+3 days) → Bump 2 (+5 days after that, then stop) — all automated via PhantomBuster
- **Reply-triggered hand-sent path**: advice → share 1-pager, second engage → soft open for future raise, 30-day keep-warm with milestone update — never automated, always personal
- **Rate: 10/day, weekdays, 10:15 Brisbane** → ~4 working days to reach all 35 connected investors; Bumps 1 and 2 require manual phantom swap (~July 1 and ~July 4)
- **Copy refinement**: Trimmed the "two things" opener to one (removed Gong/$19 line for a cleaner hook); fixed capitalization (`i'm`→`I'm`)
- **PhantomBuster operational gotchas**: API changes don't push to UI (need Cmd+Shift+R hard refresh); LinkedIn DM cap is ~8,000 chars (vs 300 for connection-request notes); investor phantom is linked to paused ICP campaign — must detach before resuming user outreach
- **ICP/user outreach stays paused** — investor connects at 20/day; user outreach resumes only after investor campaign completes and phantom is detached

## Details

### Campaign Architecture

The campaign is structured as two distinct paths: an automated 3-touch sequence for initial contact, and a hand-sent follow-up path triggered by investor replies. This separation is deliberate — automated messages handle the repeatable volume work (reaching all 35 investors with consistent messaging), while personal follow-ups handle the relationship-building that automation degrades.

**Automated Path (PhantomBuster):**
Touch 1 is a concise opener mentioning Knowted's positioning and requesting advice/feedback (not asking for money — a standard angel-network soft-ask pattern). Bump 1 fires 3 days after Touch 1 if no reply. Bump 2 fires 5 days after Bump 1 if still no reply. After Bump 2, the sequence stops — no further automated follow-up. The bumps can't be queued simultaneously in PhantomBuster; they require manual phantom configuration swaps on approximately July 1 (Bump 1) and July 4 (Bump 2).

**Hand-Sent Path (triggered by reply):**
When an investor replies, the conversation moves entirely to manual LinkedIn messaging. The progression: share advice/perspective → share the 1-pager (built from pitch deck) → soft-open for future raise participation → 30-day keep-warm with milestone updates. This path is designed to feel like a natural conversation, not a sales funnel.

### Phantom Reuse and Platform Constraints

PhantomBuster's plan limits the number of active phantoms. The team was already at 7 phantoms (over the 5-phantom cap on their plan), so creating a new "Investor Message Sender" phantom was avoided. Instead, the existing "LinkedIn Message Sender" phantom (previously used for ICP/user outreach) was repurposed. This creates a coupling risk: the investor phantom is internally linked to the paused ICP campaign. Resuming user outreach without first detaching the investor configuration would fire investor copy at sales leads — a potentially damaging misconfiguration.

### Copy Decisions

The opener was refined during the session. The original "two things" framing (mentioning both the product and the Gong/$19 price comparison) was trimmed to a single hook. The Gong/$19 line was removed because it shifts the conversation to competitive positioning before establishing the product's value — better suited for a second touch or the reply path where the investor has already shown interest. The capitalization fix (`i'm`→`I'm`) is minor but reflects the attention to detail that investor communications require.

### LinkedIn Platform Constraints

Two LinkedIn-specific constraints affect the campaign:
- **DM character limit ~8,000**: Far more generous than the 300-character connection-request note limit. The opener uses well under this, but the reply-path 1-pager share may need to be a link rather than inline text.
- **No simultaneous bump queueing**: PhantomBuster can only run one message variant at a time per phantom. Switching from Touch 1 to Bump 1 requires a live session to reconfigure the phantom — it can't be scheduled in advance.

## Related Concepts

- [[concepts/linkedin-adspower-inbox-bot]] - The AdsPower-based LinkedIn inbox automation for ICP/user outreach; the PhantomBuster investor campaign is a separate tool targeting a different audience (investors vs users)
- [[concepts/knowted-investor-data-room-build]] - The data room and 1-pager that the reply path references; the 1-pager needs to be built from the pitch deck for the engaged-investor flow
- [[concepts/knowted-cofounder-accountability-banker-feedback]] - The accountability framework tracking investor outreach velocity; the PhantomBuster campaign is the execution mechanism for the "3 investor conversations/week" target
- [[concepts/knowted-content-first-gtm-strategy]] - The GTM sequencing principle; investor outreach is running in parallel with (not before) content creation — both are "sends" that create momentum

## Sources

- [[daily/lcash/2026-06-27.md]] - PhantomBuster investor outreach configured: 3-touch automated sequence (opener → bump +3d → bump +5d); 10/day weekdays 10:15 Brisbane; 35 connected investors in ~4 working days; phantom repurposed from ICP campaign (plan capped at 5, already at 7); copy trimmed from "two things" to one hook (Gong/$19 removed); LinkedIn DM cap ~8,000 chars; bumps require manual swap ~July 1 and ~July 4; reply path: advice → 1-pager → soft open → 30-day keep-warm; PhantomBuster API changes need hard refresh (Session 19:37)
