---
title: "Claude Code Skills Directory Resolution"
aliases: [skills-directory, skills-path, project-skills]
tags: [claude-code, skills, configuration, gotcha]
sources:
  - "daily/carts00/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-12
---

# Claude Code Skills Directory Resolution

Claude Code skills (`.md` files that define slash commands like `/setup-kb`) must be placed in the project-level `.claude/skills/` directory, not the user's home directory at `~/.claude/skills/`. The home-level directory is not scanned for skill definitions.

## Key Points

- Skills must live at `<project-root>/.claude/skills/`, not `~/.claude/skills/`
- The home-level `~/.claude/` directory is used for global configuration (e.g., `CLAUDE.md`, credentials) but does not resolve skills
- This distinction is not obvious from documentation and was discovered empirically by carts00 during team knowledge base onboarding
- Skills placed in the wrong directory silently fail to appear — there is no error message indicating the skill was not found
- Each project that needs skills must have its own `.claude/skills/` directory

## Details

Claude Code uses a layered configuration system where some settings are global (in `~/.claude/`) and others are project-local (in `<project>/.claude/`). Global `CLAUDE.md` instructions are loaded from `~/.claude/CLAUDE.md` and merged with project-level instructions. This creates a reasonable expectation that skills would follow the same pattern — global skills in `~/.claude/skills/` and project skills in `<project>/.claude/skills/`.

However, skills resolution only checks the project-level directory. A developer who places a skill file at `~/.claude/skills/setup-kb.md` will find that the `/setup-kb` command simply doesn't appear in their skill list, with no warning or error. This silent failure mode makes the issue harder to diagnose, as the developer must already know to check the file's location rather than its contents.

This behavior was discovered by carts00 during onboarding to the team knowledge base. The `/setup-kb` skill was expected to be available after placing the file in the home-level skills directory, but it was not recognized until moved to the project's `.claude/skills/` directory. For team-wide skills that should be available across multiple projects, the skill file must be copied or symlinked into each project's `.claude/skills/` directory.

## Related Concepts

- [[concepts/setup-kb-skill]] - The skill whose deployment revealed this directory resolution behavior
- [[concepts/team-knowledge-base-architecture]] - The system context in which this was discovered during onboarding

## Sources

- [[daily/carts00/2026-04-10.md]] - carts00 discovered that `~/.claude/skills/` doesn't get picked up; skills need to be in project-level `.claude/skills/`
