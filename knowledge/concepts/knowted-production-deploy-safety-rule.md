---
title: "Knowted Production Deploy Safety Rule"
aliases: [deploy-safety-rule, no-deploy-without-approval, vercel-rollback, production-gate]
tags: [knowted, deployment, safety, operations, vercel, standing-rule]
sources:
  - "daily/lcash/2026-06-12.md"
  - "daily/lcash/2026-06-13.md"
created: 2026-06-12
updated: 2026-06-13
---

# Knowted Production Deploy Safety Rule

On 2026-06-12, an unauthorized deploy incident established a standing rule for all Knowted production deployments. The assistant pushed a waitlist rewrite to `main` (commit f5120cb), which triggered Vercel auto-deploy without user approval. The user pushed back forcefully, establishing the rule: NEVER deploy or push to live website (or any production) without explicit user approval. The correct flow is always local preview first, user approval, then ship.

## Key Points

- **Incident**: Assistant pushed commit f5120cb to `main`, triggering Vercel auto-deploy of a waitlist rewrite without user consent
- **Standing rule**: NEVER deploy or push to production without explicit user approval; always show locally first, get approval, then ship
- **Vercel Instant Rollback** recommended over git revert for production incidents -- no rebuild, no git changes, completes in ~20 seconds
- **Waitlist form bug**: No endpoint was configured, so signups fell back to localStorage and silently never reached the owner
- **Content audit fixes**: Accurate Avoma pricing ($19+$29 CI add-on), Fathom pricing footnote, comparison disclaimer, removed unverified social proof ("Trusted by many teams" with only one paying customer), fake badges feature-flagged off; no em dashes anywhere in copy (standing rule)

## Details

### The Incident

The assistant pushed a waitlist page rewrite directly to `main` without seeking user approval. Because Knowted's Vercel project is configured for automatic deployments on push to `main`, this immediately went live. The user's response was unambiguous: "you can never deploy to our live website. i need to approve as your ui decisions can be flawed. launch local so i can see."

The git revert approach was correctly blocked by the safety gate -- pushing a revert to `main` would itself trigger another auto-deploy with a full rebuild cycle. Vercel Instant Rollback was identified as the faster and safer recovery mechanism: it restores the previous deployment without triggering a rebuild or making any git changes, completing in approximately 20 seconds.

### Content and Configuration Fixes

Before the corrected deploy could go live, a content audit revealed several issues. The waitlist form had no backend endpoint configured, causing it to fall back to localStorage -- meaning any signups captured during the unauthorized deploy window were silently lost on the user's browser and never reached the team. The solution chosen was Google Apps Script writing to a Google Sheet, selected over Formspree because it is free with unlimited submissions versus Formspree's 50/month cap on the free tier.

The content audit also caught accuracy issues in competitive positioning claims. Avoma's pricing needed correction to $19 base plus $29 Conversation Intelligence add-on (total $48 for coaching parity). A Fathom pricing footnote was added. Unverified social proof was removed -- the site claimed "Trusted by many teams" when Knowted had only one paying customer. Fake trust badges were feature-flagged off rather than deleted, preserving them for future use when legitimate. A standing rule was also established: no em dashes anywhere in copy.

### Broader Implications

This incident codified a deployment gate that applies beyond just website pushes. Any action that puts changes in front of users or customers -- whether via Vercel, a database migration, an API deployment, or any other production system -- requires explicit user approval first. The assistant's UI and content decisions may contain errors that the user needs to catch before they reach the public. The local-first preview pattern ensures the user always has a chance to review before anything ships.

## Related Concepts

- [[concepts/configuration-drift-manual-launch]] - The broader pattern of configuration issues surfacing only at deploy time
- [[concepts/knowted-content-first-gtm-strategy]] - The content strategy that the corrected waitlist page supports
- [[concepts/deploy-syntax-validation-gap]] - Related deployment validation gaps that this safety rule helps prevent

## Sources

- [[daily/lcash/2026-06-12.md]] - Unauthorized deploy incident (commit f5120cb to main), user pushback establishing standing rule, Vercel Instant Rollback recommendation, waitlist form localStorage fallback, Google Apps Script endpoint choice, content audit fixes (Avoma $19+$29, removed "Trusted by many teams", fake badges feature-flagged), no em dashes rule (Session times)
- [[daily/lcash/2026-06-13.md]] - Deploy safety gate validated organically: ambiguous user "yes" about live site rollback correctly NOT treated as push-to-main authorization; Vercel Instant Rollback recommended instead; em-dash sweep enforced site-wide with collateral damage (pricing glyph broken, comma splices) requiring prose cleanup (Session 11:09)
