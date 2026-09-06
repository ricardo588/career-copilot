# Career Copilot 0.8 — Transactional Gmail Triage

Spanish version: [docs/es/ROADMAP-0.8.md](es/ROADMAP-0.8.md).

## Status

**Delivered:** v0.8.0 adds a deliberately narrow Gmail evidence-triage flow and a private Obsidian projection boundary. It is a safety release: no application submission, email sending, reply, forwarding, draft creation, archive, labeling, deletion, automatic reconciliation, or recurring job is introduced.

## Goal

Make one explicitly selected Gmail message usable as **reviewable private evidence** without treating email text as an automatic tracker decision. A person remains responsible for reviewing evidence, resolving identity, choosing a tracker record, and approving any mutation.

## Accepted product decisions

1. **Evidence first:** Gmail triage reads one exact message and creates a local review proposal. It never infers a tracker fact from message text.
2. **Private retention:** a reviewed fact requires a caller-supplied `supported_fact` plus exactly one minimal excerpt or a content hash. The resulting reference is opaque and remains in the private workspace.
3. **Read-only reconciliation:** `gmail-reconcile` passes a reviewed opaque reference to the deterministic tracker reconciliation planner and returns only a dry-run proposal. It cannot write Gmail, CSV, Sheets, or a remote tracker.
4. **Narrow mark-read:** Gmail can remove only `UNREAD`, only after an exact reviewed plan hash, `confirm_each_external`, a current unread preflight, and readback confirming that `UNREAD` is absent.
5. **Ledger fail-closed:** the append-only local ledger is idempotent for the same message, blocks a fingerprint collision, and blocks corrupt ledger input for human review.
6. **Obsidian only:** V0.8 permits an optional local Markdown projection with dry-run, exact plan hash, private audit, atomic write, and readback. Vaults that are symlinks or reside in the distribution or a Git repository are rejected. Remote Kanban is deferred to V0.9.

## Flow

```text
explicit Gmail message
  → private review proposal
  → optional reviewed evidence event
  → pure tracker reconciliation proposal (dry-run only)
  → optional individual mark-read, separately approved and read back
```

The evidence and audit paths are private workspace artifacts:

- `evidence/gmail-evidence.jsonl#<uuid>`
- `triage/gmail-triage.jsonl#<uuid>`
- `audit/external-actions.jsonl#<uuid>`

They must never be copied to a tracker, repository, profile distribution, or public ticket.

## Security and privacy criteria

- A ledger event stores minimal references and hashes, not Gmail bodies.
- Evidence storage rejects ambiguous or contradictory support and accepts one excerpt (maximum 500 characters) **or** a lowercase 64-character SHA-256 content hash, never both.
- Any invalid message readback, stale `UNREAD` state, incorrect approval hash, readback mismatch, path escape, ledger corruption, or identity ambiguity stops the flow.
- `draft_only` blocks every mutation before Gmail or Obsidian mutation activity.
- Successful mutation reports verified readback; a provider success response alone is insufficient.
- No production Gmail, Obsidian, Sheets, tracker, candidate profile, credential, contact, compensation, or message data is used in tests or demos.

## Upgrade

No private data migration is required for 0.8. Existing workspaces and local CSV trackers remain compatible. New Gmail evidence, ledger, and adapter audit directories are created only under a user-selected private workspace when the relevant optional command is run.

Before replacing an installed profile, install this release into a disposable profile, run the synthetic demo, and confirm that the workspace stays outside the distribution and every Git repository.

## Release verification

The release gate runs:

1. full unit tests;
2. bundle validation;
3. synthetic end-to-end demo with zero external actions;
4. disposable Hermes-profile installation;
5. privacy scan and Git diff checks.

## Deferred to V0.9 or later

- Remote Kanban projection or reconciliation.
- Automatic identity resolution from Gmail evidence.
- Inbox-wide/background triage, schedules, and recurring jobs.
- Sending, replying, forwarding, drafting, archiving, labeling, or deleting email.
- Multi-system transactions and automatic tracker changes.
