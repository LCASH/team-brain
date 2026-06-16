---
title: "Eve Team Development Environment with Gitea"
aliases: [eve-dev-env, gitea-eve, eve-shared-repos, eve-onboarding, team-development-environment]
tags: [infrastructure, deployment, collaboration, gitea, eve, operations]
sources:
  - "daily/lcash/2026-06-03.md"
created: 2026-06-03
updated: 2026-06-03
---

# Eve Team Development Environment with Gitea

On 2026-06-03, lcash set up Eve (the shared VPS at 100.69.199.85) as the team's central development environment. Four repos (TAKEOVER, TAKEOVER-dev, superwin, value-betting-scanner) were imported from GitHub into Gitea on Eve with push mirrors back to GitHub for Vercel deploys. An `eve` shell function provides one-command SSH access with multiple modes, and passwordless SSH was configured from Luke's Mac.

## Key Points

- 4 repos imported from GitHub to Eve Gitea with `god repo import` — branches, PRs, issues, releases, and wiki all transferred intact
- Gitea-to-GitHub push mirrors configured with `sync_on_commit: true` and an 8-hour fallback interval — Vercel deploys continue working without any CI configuration changes
- TAKEOVER vs TAKEOVER-dev deliberately kept as separate repos: 540 shared SHAs, 75 unique dev commits vs 11 unique prod/Vercel commits — the dev/prod split is by design, not an accident
- The `eve` shell function supports four modes: `eve` (bare shell), `eve "label"` (labeled Claude Code session), `eve repo_name` (cd into repo), `eve --pair` (pair mode) — teammates onboard with a single command
- Gitea listens on Tailscale IP only (100.69.199.85:3000, SSH on :2222) with no public exposure; uses SQLite backend for simplicity
- Security hardening included noVNC password, webhook HMAC verification, a secret-scanner with 11 regex patterns in the indexer, and Gitea API token migration away from basic-auth

## Details

The repo refresh strategy requires a deliberate sync dance because the flow is one-directional by design. Gitea push mirrors handle Eve-to-GitHub automatically, but GitHub-to-Eve sync (pulling in changes made directly on GitHub) requires an explicit `fetch from GitHub, push to Gitea` operation. This asymmetry is acceptable because the intended workflow is for all development to happen on Eve, with GitHub serving primarily as the deployment target for Vercel. Passwords for Gitea accounts are deliberately excluded from onboarding documentation — the "ask Luke" pattern provides centralized revocation control, ensuring that access can be cut for any team member without updating shared docs or rotating credentials.

The Gitea webhook receiver runs as a separate systemd service (`god-webhook.service` on port 9000) and feeds PR discussion threads into the team brain via the Claude God extraction pipeline. This captures architectural decisions and review feedback that happen in PR comments — a knowledge source that would otherwise be invisible to the brain since it occurs outside of Claude Code sessions. The Eve infrastructure follows a clean directory convention: `/shared/repos/` for all Git repositories, `/shared/brain/` for the team brain output, and `/shared/claude-god/` for the God extraction system. This separation keeps concerns isolated while making the full system discoverable for new team members exploring the VPS.

## Related Concepts

- [[concepts/team-knowledge-base-architecture]] - The shared brain system that Eve hosts and God populates
- [[concepts/claude-god-autonomous-knowledge-extraction]] - The God extraction system running on Eve as a systemd service
- [[concepts/deployment-verification-automation]] - Deployment automation that integrates with the Gitea-to-GitHub mirror flow

## Sources

- [[daily/lcash/2026-06-03.md]] - Sessions 13:25 (security hardening, noVNC, webhook HMAC, secret-scanner, onboarding documentation), 13:56 (repo import from GitHub, eve shell function, push mirror configuration)
