# Career Copilot 0.14.0 — Private LinkedIn Connection Evidence

Spanish version: [docs/es/ROADMAP-0.14.0.md](es/ROADMAP-0.14.0.md).

## Goal

Add a deterministic, local-only importer for an explicitly supplied LinkedIn **connections** export that produces conservative Human Path discovery clues. It must never claim current employment, exact identity, relationship strength, referral capacity or authorization to contact.

## Security architecture

The importer is **read-only**:

- It accepts a private workspace plus export and vacancy inputs under that workspace.
- It opens input paths descriptor-relatively with `O_NOFOLLOW`, rejects symlinks, Git workspaces and non-regular files, and continues from the originally opened directory descriptors if a pathname ancestor changes later.
- It performs no network, browser, API, login, cookie, credential, process launch or external action.
- It emits the review artifact to stdout only. It has no `--output` argument and performs no filesystem write. A host that chooses to persist stdout owns that separate write boundary.

This deliberately removes the prior output-publication race from the importer’s security model.

## Evidence contract

Each candidate result keeps independent states:

- `discovery_state: export_match_found`
- `identity_state: needs_identity_review`
- `current_employment: unverified`
- the authorization field always has the value `not_granted`

A text match is never identity confirmation. Company-only and duplicate textual matches are manual-review ambiguities. No tracker, story bank, Sheets, Obsidian, email, calendar or Human Path record is mutated.

## Acceptance gates

- Only documented UTF-8 CSV headers are accepted; duplicate and unsupported headers fail closed.
- All fixtures are synthetic; no real exports, contacts, identifiers or profile URLs enter the repository.
- Tests patch socket and process-launch entry points and assert no attempted call.
- Regressions cover outside-workspace paths, Git workspaces, symlinks, malformed CSV, ambiguity and input immutability.
- Bundle validation, full test suite, privacy scan and independent security audit pass before release.
