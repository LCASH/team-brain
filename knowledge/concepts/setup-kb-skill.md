---
title: "Setup KB Skill"
aliases: [setup-kb, onboarding-skill, /setup-kb]
tags: [onboarding, skills, developer-experience, tooling]
sources:
  - "daily/lcash/2026-04-10.md"
  - "daily/carts00/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-12
---

# Setup KB Skill

A Claude Code skill (`/setup-kb`) that provides one-command onboarding for developers joining the team knowledge base. It handles cloning the shared repository, installing dependencies, and configuring the necessary hooks for automatic conversation capture.

## Key Points

- Invoked as `/setup-kb` within any Claude Code session
- Automates the full onboarding flow: clone repo, install dependencies, configure hooks
- Reduces onboarding friction from a multi-step manual process to a single command
- Designed for the team knowledge base multi-developer workflow
- Ensures consistent hook configuration across all team members' environments
- First real-world onboarding (carts00) revealed platform-specific friction: skills directory resolution, GitHub URL 404s, and Windows SSL issues
- The skill file itself must be in project-level `.claude/skills/`, not `~/.claude/skills/` — a bootstrapping challenge for self-deploying skills

## Details

Developer onboarding is a common friction point for team knowledge systems. Without automation, each new team member would need to manually clone the shared repository, ensure the correct Python dependencies are installed (via uv), configure Claude Code hooks in their `.claude/settings.json`, and verify that the capture pipeline is working. Any misconfiguration means their conversations silently fail to capture, and the knowledge gap isn't noticed until someone asks why a developer's insights aren't appearing in compilations.

The `/setup-kb` skill eliminates this class of problems by encoding the entire setup process as a single executable command. When a developer runs `/setup-kb`, the skill handles all configuration steps and validates the result. This follows the principle that onboarding should be a single command — if it requires a checklist, people will skip steps.

The skill is particularly important in the team knowledge base context because the system's value scales with participation. A knowledge base that only captures one developer's conversations is useful but limited; one that captures the entire team's conversations enables cross-pollination of insights and pattern discovery that no individual could achieve alone. Minimizing onboarding friction directly increases the likelihood of full team adoption.

### First Real-World Onboarding: carts00

The first team member onboarding (carts00, 2026-04-10) validated the need for automation while revealing gaps in the current setup flow. Three friction points were encountered:

1. **Skills directory resolution:** carts00 placed the `setup-kb.md` file in `~/.claude/skills/`, expecting it to be picked up globally. Claude Code only resolves skills from project-level `.claude/skills/` directories, so the skill was silently unavailable. This is a bootstrapping problem — the automation skill can't automate its own installation if the user doesn't know where to put it.

2. **GitHub URL 404:** The raw GitHub URL for the skill file from LCASH/team-brain returned a 404 error. The workaround was to clone the entire repository instead of curling individual files.

3. **Windows SSL issues:** On Windows, curl requests to raw GitHub URLs encountered SSL certificate verification failures. The workaround required either the `--insecure` flag or an alternative download method (git clone).

Despite these obstacles, carts00 successfully completed onboarding by cloning the repo directly. The team KB is now configured with daily logs flowing to `daily/carts00/` and a Stop hook installed for periodic capture. These findings should inform future iterations of the skill to handle cross-platform edge cases.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The system that this skill onboards developers into
- [[concepts/stop-hook-periodic-capture]] - The capture mechanism configured during onboarding
- [[concepts/claude-code-hook-reliability]] - Hook behavior that the skill must configure correctly
- [[concepts/claude-code-skills-directory]] - The directory resolution behavior that caused the primary onboarding friction
- [[connections/onboarding-friction-real-world-validation]] - Analysis of carts00's onboarding friction points

## Sources

- [[daily/lcash/2026-04-10.md]] - Creation of `/setup-kb` skill for one-command onboarding to the team knowledge base
- [[daily/carts00/2026-04-10.md]] - First real-world onboarding: skills directory issue, GitHub URL 404, Windows SSL errors; successful completion via git clone
