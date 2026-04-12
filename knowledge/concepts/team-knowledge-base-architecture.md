---
title: "Team Knowledge Base Architecture"
aliases: [team-brain, shared-kb, team-kb]
tags: [architecture, knowledge-management, collaboration]
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-12
---

# Team Knowledge Base Architecture

A shared knowledge base system designed for multi-developer teams using Claude Code. The architecture compiles individual AI conversation logs into structured wiki articles, enabling team-wide knowledge synthesis without manual curation. The canonical implementation is hosted at LCASH/team-brain on GitHub.

## Key Points

- Each developer gets their own directory under `daily/` (e.g., `daily/lcash/`, `daily/alice/`) to avoid merge conflicts when multiple people push conversation logs simultaneously
- Knowledge compilation happens locally on each developer's machine rather than in CI, with a nightly fallback for missed compilations
- Onboarding is handled by a single `/setup-kb` skill that clones the repo and configures all necessary hooks
- The system follows a compiler analogy: daily logs are "source code," the LLM is the "compiler," and the knowledge base is the "executable"
- Team members' insights are attributed individually but synthesized into shared concept articles
- Sessions are tagged with project context (`[project-name]`) via cwd extraction, disambiguating multi-project daily logs

## Details

The architecture addresses the fundamental challenge of team knowledge sharing: developers learn things in private AI conversations that would benefit the entire team, but rarely take the time to document them. By automating the extraction pipeline — capture via hooks, flush to daily logs, compile to wiki articles — the system removes the friction that prevents knowledge sharing.

The per-developer directory structure (`daily/{developer}/`) is a deliberate design choice driven by Git workflow constraints. When multiple developers push daily logs simultaneously, file-level merge conflicts are common if everyone writes to the same directory or file. Isolating each developer's logs into their own subdirectory eliminates this class of conflicts entirely, since each developer only ever appends to their own files.

The shared `knowledge/` directory is where synthesis happens. The compiler reads logs from all developers and produces unified concept articles, connection articles, and Q&A entries. This means a pattern discovered by one developer can be linked to a related discovery by another, building team-wide understanding that no individual would have alone.

## Related Concepts

- [[concepts/local-compilation-strategy]] - Why compilation runs locally instead of in CI
- [[concepts/setup-kb-skill]] - One-command onboarding for new team members
- [[concepts/stop-hook-periodic-capture]] - The primary capture mechanism feeding daily logs
- [[concepts/claude-code-hook-reliability]] - Hook behavior that shaped the capture architecture
- [[concepts/project-context-tagging]] - Project disambiguation in daily logs via cwd extraction

## Sources

- [[daily/lcash/2026-04-10.md]] - Initial setup of shared knowledge repo (LCASH/team-brain), decision on per-developer directories, and overall architecture choices
