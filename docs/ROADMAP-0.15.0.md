# Career Copilot 0.15.0 — Community Skill Distribution

Spanish version: [docs/es/ROADMAP-0.15.0.md](es/ROADMAP-0.15.0.md).

## Goal

Make Career Copilot's public community-skill route explicit, portable and reviewable alongside its complete Hermes profile distribution. This is a distribution and documentation release: it does not change candidate-data handling, execution capability or external-action policy.

## Delivered scope

- The portable `career-copilot` skill frontmatter declares the same Apache-2.0 license as the repository and `skills.sh.json`.
- English and Spanish documentation distinguish the community-skill installation path from the complete Hermes profile path.
- Both routes state the private-workspace boundary, `draft_only` default and optional-adapter authorization requirements.
- Documentation supplies the exact community-skill identifier and a future indexing checklist.

## Non-negotiable boundaries

- No candidate workspace, CV, contact, tracker, credential, session or other private data is included in the repository or distribution.
- No plugin, official Marketplace listing, automatic directory listing, telemetry feature, network capability or external action is added by this release.
- The public directory provider controls indexing and search timing. `skills.sh.json` supplies category metadata only when a provider indexes the repository; it is not a claim of listing or endorsement.
- The profile distribution remains an optional Hermes adapter; it is not silently installed by the community-skill route.

## Release gates

- `python3 -m json.tool skills.sh.json`
- `python3 scripts/validate_bundle.py`
- `python3 -m unittest discover -s tests -v`
- `python3 skills/career-copilot/scripts/privacy_scan.py .`
- Disposable profile-install verification and synthetic smoke test.
- Public release-resolution check against tag `v0.15.0` using the `skills` CLI without touching a real candidate workspace.