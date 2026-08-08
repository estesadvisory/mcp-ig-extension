# Agent instructions (mcp-ig-extension)

This repository is the **local source of truth** for the Instagram metrics Lambda extension in the Grok CLI.
Web UI Grok Projects do **not** sync here. Continuity is: **disk + this file** (+ Memory MCP when used).

- **Local path:** `~/repos/mcp-ig-extension`
- **GitHub:** https://github.com/estesadvisory/mcp-ig-extension (public)

## What this repo is

Scheduled **container Lambda** that pulls Instagram metrics (Meta Graph API) and writes JSON into the **Artifactum** MCP vault over authenticated HTTPS. Independent of the Artifactum source tree (HTTP client only).

> Historical name references (`grok-memory-mcp`) may appear in older docs/strings; product vault is **Artifactum**. Align new work with Artifactum naming (portfolio-ops #6).

## Portfolio process (shared)

Cross-repo standards: **[estesadvisory/portfolio-ops](https://github.com/estesadvisory/portfolio-ops)**.

1. **Issue bodies** are source of truth; update bodies when closing.
2. **Priority in titles:** `[P0]`…`[P3]`; park as `[P3 / parked]` with unpark criteria.
3. **Small PRs**; `Refs #N` in commits when an issue exists.
4. **Review before merge** for product/infra code; pure docs use judgment.
5. **Human owns** assignee and merge; disclose AI assistance when useful.
6. **Never** embed PATs/tokens in `git remote` URLs — clean HTTPS + `gh auth` keyring (or SSH).
7. **Product-impacting** MCP target/URL/auth changes: file issues first; no silent break of prod writes.

## Repo-specific non-negotiables

1. **Secrets:** IG tokens + MCP bearer from **Secrets Manager** / env — never commit tokens.
2. **Loose coupling:** do not import Artifactum package code; HTTPS to Function URL only.
3. **Deploy:** `make push-to-ecr` + Terraform; verify scheduled run / logs after change.
4. **v1 scope:** metrics JSON only unless an issue expands scope (no media archive by default).
5. Prefer issue-driven backlog (this repo was historically quiet — portfolio-ops #6 park/revive).

## Useful links

- [README.md](./README.md)
- Artifactum product: https://github.com/estesadvisory/artifactum
- Portfolio hub: https://github.com/estesadvisory/portfolio-ops
