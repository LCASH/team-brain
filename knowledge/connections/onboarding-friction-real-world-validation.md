---
title: "Connection: Onboarding Friction and Setup Automation Validation"
connects:
  - "concepts/setup-kb-skill"
  - "concepts/claude-code-skills-directory"
  - "concepts/team-knowledge-base-architecture"
sources:
  - "daily/carts00/2026-04-10.md"
created: 2026-04-12
updated: 2026-04-12
---

# Connection: Onboarding Friction and Setup Automation Validation

## The Connection

When carts00 became the first team member to onboard to the shared knowledge base, the process encountered three distinct friction points — each of which validates the need for the `/setup-kb` automation skill while simultaneously revealing gaps in its current implementation.

## Key Insight

The non-obvious insight is that **the friction points were all environmental, not conceptual**. carts00 understood what the system does and wanted to use it. The barriers were: (1) Claude Code's skills directory resolution silently ignoring `~/.claude/skills/` in favor of project-level `.claude/skills/`, (2) the raw GitHub URL for the skill file returning a 404, and (3) SSL certificate issues on Windows preventing curl-based downloads from GitHub. None of these are problems with the knowledge base design itself — they are platform and tooling issues that an automated setup process should handle transparently.

This pattern is common in developer tooling: the conceptual model is sound, but onboarding fails at the edges where the tool meets the developer's actual environment. The `/setup-kb` skill was designed to prevent exactly this class of failure, but the skill itself couldn't be deployed because of the skills directory resolution issue — a bootstrapping problem where the automation tool can't automate its own installation.

## Evidence

carts00's onboarding session on 2026-04-10 documented three specific failures:
1. Placed the `setup-kb.md` skill file in `~/.claude/skills/` — the skill didn't appear. Had to discover that project-level `.claude/skills/` is required.
2. The raw GitHub URL for the skill file from LCASH/team-brain returned 404 — possibly a private repo or incorrect URL path.
3. On Windows, curl to raw GitHub URLs hit SSL certificate verification errors, requiring `--insecure` flag or alternative download methods.

Despite these obstacles, carts00 successfully completed onboarding by cloning the repo directly instead of curling individual files. The team KB is now configured for carts00 with daily logs flowing to `daily/carts00/` and a Stop hook installed in the project's `.claude/settings.json`. This outcome validates that the system design is correct even if the setup automation has gaps.

## Related Concepts

- [[concepts/setup-kb-skill]] - The automation intended to prevent these friction points
- [[concepts/claude-code-skills-directory]] - The root cause of the skills deployment failure
- [[concepts/team-knowledge-base-architecture]] - The system successfully onboarded despite the friction
- [[concepts/stop-hook-periodic-capture]] - The capture mechanism successfully configured as the final onboarding step
