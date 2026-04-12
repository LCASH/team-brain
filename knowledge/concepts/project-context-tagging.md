---
title: "Project Context Tagging"
aliases: [project-tagging, cwd-extraction, session-project-tag]
tags: [daily-logs, hooks, multi-project, developer-experience]
sources:
  - "daily/lcash/2026-04-10.md"
created: 2026-04-10
updated: 2026-04-12
---

# Project Context Tagging

A convention for tagging daily log session entries with the project they originated from, using the format `### Session (HH:MM) [project-name]`. Enabled by extracting the current working directory (cwd) from Claude Code hooks, this feature disambiguates sessions when a developer works across multiple projects in a single day.

## Key Points

- Session headers use the format `### Session (HH:MM) [project-name]` where the project name is derived from the cwd
- Cwd extraction was added to all hooks (SessionStart, Stop, PreCompact, SessionEnd) to make project context universally available
- Without project tagging, daily logs from developers working on multiple projects would intermingle sessions with no way to filter or attribute them
- The tag is appended to the session header rather than stored in metadata, keeping the daily log format human-readable and greppable
- The project name is typically the directory name of the project root (e.g., `value-betting-scanner`, `Knowted admin`)

## Details

Developers frequently switch between multiple projects throughout a day. A single daily log file (`daily/{developer}/YYYY-MM-DD.md`) may contain sessions from three or four different codebases. Without project context, a compiler reading the log must infer which project each session relates to from the content alone — an unreliable heuristic that breaks when sessions discuss cross-cutting concerns or generic tooling.

Project context tagging solves this by extracting the current working directory from the hook's environment at capture time. Claude Code hooks receive context about the active session, including the working directory. By parsing the cwd and appending a `[project-name]` tag to the session header, each session entry is unambiguously associated with its originating project. This enables downstream tooling to filter compilations by project, generate project-specific knowledge indexes, or attribute insights to the correct codebase.

The implementation required updating all hooks to extract cwd — not just the Stop hook used for periodic capture, but also SessionStart, PreCompact, and SessionEnd. This ensures project context is available regardless of which hook triggers the capture. The change is backward-compatible: session headers without a project tag (from before this feature was added) remain valid and are treated as untagged.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The multi-developer system that benefits from per-project session disambiguation
- [[concepts/stop-hook-periodic-capture]] - The primary capture mechanism whose hooks were updated to extract cwd
- [[concepts/claude-code-hook-reliability]] - All hooks updated with cwd extraction, reinforcing the multi-hook capture strategy

## Sources

- [[daily/lcash/2026-04-10.md]] - lcash added cwd extraction to all hooks and established the `### Session (HH:MM) [project-name]` tag format during a Knowted admin testing session
