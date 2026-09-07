# Career Copilot 0.9 — Optional Obsidian Kanban Projection

Spanish version: [docs/es/ROADMAP-0.9.md](es/ROADMAP-0.9.md).

## Status

**Delivered in v0.9.0.** v0.9 extends the v0.8 private, atomic Obsidian Markdown projection boundary with an optional local Obsidian Kanban card projection. It does not create remote providers, vault scans, synchronization, or automatic actions. The detailed safety contract below remains the release boundary; later hardening beyond the implemented one-board command remains deferred rather than implied.

## Goal

Allow a user to optionally render an explicitly selected, reviewed Career Copilot artifact into one **private Obsidian Kanban board** in their existing Obsidian workflow.

The board is a local, reviewable view—not a tracker authority, synchronization system, or source for automatic decisions. The exact board format must be configured privately and be compatible with the user's existing Obsidian Kanban process; the public distribution must not contain a candidate's board, vault path, board name, or card content.

## Product decisions

1. **Obsidian only.** v0.9 adds no remote Kanban provider, credentials, API integration, or network activity. It operates only through the existing local Obsidian vault boundary.
2. **Optional, one board at a time.** A user explicitly selects one configured private vault and one board-relative Markdown path. No board is created, scanned, migrated, or updated during installation.
3. **One-way rendering.** Career Copilot renders a reviewed local artifact into a Kanban card or board section. It never imports, parses, reconciles, or treats Kanban content as canonical tracker data.
4. **Pinned plugin grammar.** The renderer targets the public Markdown grammar of [Obsidian Kanban](https://github.com/community-archive/obsidian-kanban), verified against its `main` revision `5134c05`. A private configuration selects only the permitted board-relative path, lane keys, and controlled card markers; it cannot redefine or guess the grammar. A missing, invalid, ambiguous, or incompatible configuration blocks rather than overwriting a board.
5. **Dry-run first.** The default output contains the deterministic Markdown change, destination-relative path, current-content fingerprint, and `approval_sha256`; it does not write. `--apply` requires a private `confirm_each_external` profile, private workspace, exact reviewed hash, current preflight, atomic write, and exact readback.
6. **Reuse the v0.8 vault guard.** Vaults that are symlinks or reside in the distribution or a Git repository remain rejected. The write remains local but requires the same private path, audit, and readback boundary as v0.8.
7. **Minimum necessary content.** A rendered card contains only the caller-selected reviewed summary, explicitly allowed fields, and opaque local provenance references. Gmail bodies, credentials, candidate data beyond the reviewed payload, absolute paths, and raw source artifacts never enter repository files, public logs, or synthetic fixtures.

## Non-goals

- No remote Kanban service, provider selection, OAuth/API key handling, webhooks, polling, or synchronization.
- No automatic task creation, background workers, recurring jobs, schedules, inbox-wide triage, bulk board generation, or board discovery.
- No import, reverse reconciliation, automatic identity resolution, or tracker update based on board content.
- No multi-surface transaction with Gmail, Sheets, CSV, or another Obsidian note.
- No application submission, outreach, email send/reply/forward/draft/archive/label/delete, or public action.
- The previously listed source-plan policy, opt-in schedules/blueprints, expanded interview dossier, and mobile-first PDF remain deferred; they are not bundled into v0.9.

## Architecture and safety contract

### 1. Pure board renderer

Add a dependency-free renderer that accepts only normalized input:

- a reviewed local artifact and opaque provenance references;
- a private board-format descriptor or template version;
- an explicit board-relative Markdown path;
- an explicit column or lane key; and
- the current board content, when an approved update targets an existing board.

It returns exactly one deterministic result:

- `create_board_plan`;
- `append_card_plan`;
- `update_card_plan`;
- `no_change`;
- `duplicate_projection`;
- `ambiguous_target`;
- `integrity_failure`; or
- `policy_blocked`.

The renderer has no filesystem mutation or network dependency. Missing provenance, a malformed or unsupported board format, ambiguous lane/card identity, unsafe relative path, corrupt projection ledger, or incompatible current board content is blocking—not a best-effort fallback.

### 2. Pinned board grammar and controlled region

The renderer supports the plugin's Markdown-backed board grammar only. Its synthetic fixture and output must use:

```markdown
---
kanban-plugin: board
---

## <configured lane heading>

- [ ] <reviewed card text> ^<opaque-card-marker>

%% kanban:settings
```

The plugin source defines `kanban-plugin` frontmatter, renders each `##` heading as a lane, and represents cards as Markdown list items; its canonical writer also emits a trailing `%% kanban:settings` block. An archive is a `***` thematic break followed by an `## Archive` heading. v0.9 does not create, move, complete, archive, or parse that archive region.

Private configuration may define only allowed lane keys and headings, a stable opaque card marker, permitted card fields/order, and the exact render boundary. The implementation modifies only that boundary. If plugin frontmatter/settings are absent or inconsistent, a lane heading is missing or duplicated, the controlled marker is absent/repeated/manually altered, or content outside the configured boundary would change, the operation blocks. It must never rewrite an entire vault, infer a lane from text, silently convert another board grammar, or treat a non-board note as a board.

### 3. Approval and write lifecycle

The dry-run `approval_sha256` binds a versioned canonical plan including:

- the canonical vault identity hash and board-relative path;
- board format/version, lane key, render boundary, and current-board fingerprint;
- operation, opaque card identity, reviewed artifact/provenance references, and exact Markdown payload; and
- expected preflight state.

For `--apply`, the adapter must:

1. reject `draft_only` before filesystem mutation;
2. require the exact reviewed hash, private profile, private workspace, and `confirm_each_external`;
3. revalidate the vault, relative path, format configuration, and current board fingerprint;
4. recompute the plan and block on a stale or mismatched hash;
5. write only the reviewed Markdown change atomically; and
6. read back the exact board file and append a minimal private audit event only after verifying the expected content.

An atomic-write return alone is not success. A failed or mismatched readback is an integrity failure, never a no-op.

### 4. Idempotency and recovery

Maintain a private append-only projection ledger keyed by a versioned fingerprint of the reviewed artifact, canonical vault identity, board-relative path, board format, lane, and exact card payload. It stores only opaque references, hashes, and outcomes.

- A verified matching prior projection produces `duplicate_projection` or `no_change` without writing.
- A matching fingerprint bound to another board/card identity is a collision and blocks.
- Corrupt ledger input, unsafe permissions, symlink traversal, path escape, stale board content, or failed readback blocks the operation.
- A partial local failure is audited as a failure; recovery requires a newly reviewed plan from current content.

### 5. CLI contract (proposed)

The command name may change during implementation, but the boundary may not:

```text
obsidian-kanban-project \
  --vault <private-vault> \
  --relative-path <board-relative-markdown-path> \
  --board-format-config <private-format-config> \
  --lane <configured-lane-key> \
  --artifact-json <reviewed-local-artifact>
```

Without `--apply`, it emits a redacted deterministic plan and `approval_sha256`. Applying repeats the exact reviewed inputs and adds:

```text
--profile <private-profile.yaml> \
--workspace <private-workspace> \
--approved-plan-sha256 <reviewed-hash> \
--apply
```

It must not offer flags for vault scans, broad board queries, bulk projection, format conversion, synchronization, automatic execution, or content-derived lane selection.

## Delivery plan

### Milestone A — format contract and pure renderer

- Define a generic, private board-format configuration schema and strict render-boundary marker.
- Add the canonical renderer, plan hash, projection ledger contract, and generic templates with placeholders only.
- Add unit tests for every renderer decision, format compatibility, path safety, duplicate/collision behavior, render-boundary preservation, and hash binding.

**Exit criteria:** all renderer tests run without candidate content, a real vault, filesystem mutation, or network activity; ambiguous format/content always fails closed.

### Milestone B — gated Obsidian Kanban adapter

- Add the narrow `obsidian-kanban-project` command beside the existing Obsidian adapter boundary.
- Reuse v0.8 private-vault validation, atomic write, exact readback, minimal audit events, and `draft_only` protection.
- Add fake/temp-vault tests for dry-run, stale approval, wrong vault, unsafe paths, incorrect render marker, and failed readback.

**Exit criteria:** no write is reachable without the entire reviewed approval contract, and the adapter changes only its configured render boundary.

### Milestone C — synthetic flow and release hardening

- Add a synthetic private board-format fixture and a synthetic board with opaque references only.
- Demonstrate create/append/update/no-change outcomes locally; retain `external_actions == 0` for the ordinary synthetic demo because this is not an external provider action.
- Update paired English/Spanish adapter documentation, then run the full release gate, privacy scan, bundle validation, isolated-profile install, and independent review.

**Exit criteria:** repository and demo output contain no real board, vault, candidate, Gmail, tracker, credential, or workspace data.

## Test matrix

The implementation must cover:

- create, append, update, no-change, duplicate, ambiguous target, policy block, and integrity-failure renderer results;
- approval binding changes to vault, relative path, board format, render boundary, lane, artifact, provenance, payload, and current-board fingerprint;
- missing or invalid profile/workspace/hash, `draft_only`, stale plan, unsafe paths, symlinks, Git/distribution vaults, corrupt ledgers, and collisions;
- missing/duplicated/modified render markers, unsupported format, lane mismatch, unexpected manual content in the controlled region, atomic-write failure, and readback mismatch;
- preservation of all content outside the configured render boundary; and
- bilingual docs, CLI help, synthetic demo, privacy scan, bundle validation, isolated install, and the complete unit suite.

## Upgrade and release impact

v0.9 performs no installation-time migration, vault scan, board discovery, or write. Existing CSV, Sheets, Gmail-triage, and v0.8 free-form Obsidian Markdown projection remain compatible and independent. The Kanban capability is disabled until a user explicitly provides private vault and board-format configuration and runs the command.

This document does not authorize access to, copying from, or changes to any separate Job Hunter workflow or candidate workspace. If a later local smoke test is authorized, it must use a disposable private test vault and synthetic board content.

## Deferred beyond v0.9

- Remote Kanban providers, synchronization, imports, polling, webhooks, recurring schedules, and bulk projection.
- Automatic tracker changes, cross-system atomicity, and Kanban-driven fact inference.
- Board-format conversion or automatic migration of existing boards.
- Source-plan policy, opt-in schedules/blueprints, expanded interview dossier, and mobile-first PDF output.
