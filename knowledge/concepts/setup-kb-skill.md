---
title: "Setup KB Skill"
aliases: [setup-kb, onboarding-skill, /setup-kb]
tags: [onboarding, skills, developer-experience, tooling]
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-10
---

# Setup KB Skill

A Claude Code skill (`/setup-kb`) that provides one-command onboarding for developers joining the team knowledge base. It handles cloning the shared repository, installing dependencies, and configuring the necessary hooks for automatic conversation capture.

## Key Points

- Invoked as `/setup-kb` within any Claude Code session
- Automates the full onboarding flow: clone repo, install dependencies, configure hooks
- Reduces onboarding friction from a multi-step manual process to a single command
- Designed for the team knowledge base multi-developer workflow
- Ensures consistent hook configuration across all team members' environments

## Details

Developer onboarding is a common friction point for team knowledge systems. Without automation, each new team member would need to manually clone the shared repository, ensure the correct Python dependencies are installed (via uv), configure Claude Code hooks in their `.claude/settings.json`, and verify that the capture pipeline is working. Any misconfiguration means their conversations silently fail to capture, and the knowledge gap isn't noticed until someone asks why a developer's insights aren't appearing in compilations.

The `/setup-kb` skill eliminates this class of problems by encoding the entire setup process as a single executable command. When a developer runs `/setup-kb`, the skill handles all configuration steps and validates the result. This follows the principle that onboarding should be a single command — if it requires a checklist, people will skip steps.

The skill is particularly important in the team knowledge base context because the system's value scales with participation. A knowledge base that only captures one developer's conversations is useful but limited; one that captures the entire team's conversations enables cross-pollination of insights and pattern discovery that no individual could achieve alone. Minimizing onboarding friction directly increases the likelihood of full team adoption.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The system that this skill onboards developers into
- [[concepts/stop-hook-periodic-capture]] - The capture mechanism configured during onboarding
- [[concepts/claude-code-hook-reliability]] - Hook behavior that the skill must configure correctly

## Sources

- [[daily/lcash/2026-04-10.md]] - Creation of `/setup-kb` skill for one-command onboarding to the team knowledge base
