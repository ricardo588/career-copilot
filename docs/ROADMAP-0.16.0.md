# Career Copilot 0.16.0 — Portable Marketplace Plugin Release Candidate

Spanish version: [docs/es/ROADMAP-0.16.0.md](es/ROADMAP-0.16.0.md).

## Goal

Prepare the public repository as a portable Agent Plugins v1 package for later Hermes Marketplace review, without changing Career Copilot's privacy or action contract.

## Delivered local scope

- Root `plugin.json` declares the Agent Plugins v1 schema, `career-copilot` identity, Apache-2.0 license and version `0.16.0`.
- The package directly reuses `skills/career-copilot/`; no duplicate skill tree was added.
- The package is skill-only: no plugin code, tools, hooks, middleware, MCP server, service, cron, install/network hook, telemetry, secret/configuration requirement, or dependency manifest.
- English and Spanish Marketplace documentation describes lifecycle commands, namespaces, route coexistence, privacy, optional integrations, workspace-safe removal, and the difference between local validation and catalog admission.
- A local-only catalog preparation process intentionally omits a SHA until an authorized published release exists.
- Bundle validation and unit tests check portable-manifest identity and the absence of declared capabilities/runtime entrypoints.

## Non-negotiable boundaries

- Candidate workspaces remain private, user-selected and outside the repository, plugin installation and profile distribution.
- `draft_only` remains the default. Installation and enablement do not apply, message, contact, publish, mutate a real pipeline, authenticate, or make a network call.
- Google Sheets, Gmail and Obsidian remain optional, user-configured integrations with explicit authorization boundaries.
- This release candidate is not a catalog entry, approved listing, searchable Marketplace package, published release or tag.

## Local release gates

```bash
hermes plugins doctor . --ci
python3 scripts/validate_bundle.py
python3 -m unittest discover -s tests -v
python3 skills/career-copilot/scripts/privacy_scan.py .
python3 skills/career-copilot/scripts/run_synthetic_demo.py --output-dir <temporary-directory>
git diff --check
```

## Next approval

Publishing a release/tag, opening a catalog PR, or making any external write requires Ricardo's explicit authorization. A later catalog entry must use the exact full immutable 40-character SHA of that authorized release and pass catalog validation at that pin.
