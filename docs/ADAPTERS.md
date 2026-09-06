# Optional adapters

Versión en español: [docs/es/ADAPTERS.md](es/ADAPTERS.md).

All adapters are optional, disabled in the template, and dry-run-first. Credentials, IDs and vault paths remain local.

Set the installed adapter path once:

```bash
ADAPTER="$HOME/.hermes/profiles/<PROFILE>/skills/career-copilot/scripts/adapters.py"
```

## Safety contract

- Reads may execute when the user requests them.
- Mutations show a plan unless `--apply` is explicitly supplied.
- Google mutations require `--profile <private-profile.yaml>` and are blocked when that profile is `draft_only`.
- Every mutation performs readback verification.
- The Gmail adapter cannot send messages; triage reads exactly one explicit message and stores only private reviewable evidence.
- The Sheets adapter updates only an explicit range.
- The Obsidian adapter rejects paths outside the configured vault and vaults that are symlinks or reside in the distribution or a Git repository.

## Google Workspace prerequisite

Install and authenticate a compatible `gws` CLI using its official instructions. Keep its credential file outside the repository. Verify readiness with:

```bash
gws --help
```

The adapter inherits the current environment, including any credential-file environment variable required by the local `gws` installation.

## Google Sheets

Read:

```bash
python3 "$ADAPTER" sheets-read \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:P10'
```

Reconcile a tracker record (read-only; **no `--apply` option exists**):

```bash
python3 "$ADAPTER" sheets-reconcile \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:I500' \
  --header-row 1 \
  --fields-json '{"business_id":"No","company":"Company","role":"Role","location":"Location","canonical_url":"Canonical URL","external_job_id":"External Job ID","status":"Status","priority":"Priority","notes":"Notes"}' \
  --record-json '{"business_id":"1","company":"Example Company","role":"Program Director","location":"Mexico City","canonical_url":"https://jobs.example.test/1","external_job_id":"SYN-1","status":"identified","priority":"medium","notes":""}'
```

The range must begin exactly at the header row. The command reads once, derives
physical row positions from that explicit range, and returns a deterministic
`create_plan`, `update_plan`, `no_change`, or blocking decision. It never calls
a Sheets write endpoint. See the skill reference for the private mapping and
integrity contract.

### Reconcile, review, and apply one approved plan

`sheets-reconcile-apply` first behaves as a dry run. It returns the exact cell
ranges, old/new reconciliation values, integrity audit, and an
`approval_sha256`. Review those values before doing anything else.

```bash
python3 "$ADAPTER" sheets-reconcile-apply \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:I500' \
  --header-row 1 \
  --fields-json "$FIELDS_JSON" \
  --record-json "$RECORD_JSON"
```

To write, repeat exactly the reviewed arguments and add `--apply`, the returned
hash, a private workspace, and a profile whose mode is
`confirm_each_external`:

```bash
python3 "$ADAPTER" sheets-reconcile-apply \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A1:I500' \
  --header-row 1 \
  --fields-json "$FIELDS_JSON" \
  --record-json "$RECORD_JSON" \
  --approved-plan-sha256 '<HASH_FROM_REVIEWED_DRY_RUN>' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml" \
  --workspace "$HOME/Documents/CareerCopilot" \
  --apply
```

The apply call re-reads the live range and recomputes the plan. It blocks before
any write if that current plan hash differs from the reviewed hash. It accepts
only a closed A1 rectangle with a worksheet name, writes only changed cells,
reads back each changed cell, and appends minimal private audit events. It never
submits an application or sends outreach.

The approval hash is bound to the exact spreadsheet ID without disclosing that
ID in command output. A matching no-change plan returns `no_change` and performs
no external mutation or audit write.

Preview an update:

```bash
python3 "$ADAPTER" sheets-update \
  --sheet-id "$CAREER_COPILOT_SHEET_ID" \
  --range 'Applications!A2:B2' \
  --values-json '[["Example Company","Program Director"]]' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml"
```

Apply only after confirming the sheet, range and values:

```bash
# `confirm_each_external` only: add --apply after exact confirmation.
```

The adapter reads the same range back and fails if values differ.

## Gmail

Search and read:

```bash
python3 "$ADAPTER" gmail-search --query 'newer_than:7d (recruiter OR application)'
python3 "$ADAPTER" gmail-get --message-id '<MESSAGE_ID>'
```

Preview marking a handled message as read. The response includes an `approval_sha256` bound to that message and user identity:

```bash
python3 "$ADAPTER" gmail-mark-read \
  --message-id '<MESSAGE_ID>' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml"
```

In `confirm_each_external`, apply only with the exact reviewed hash, a private workspace and a current re-read showing the target remains unread:

```bash
python3 "$ADAPTER" gmail-mark-read \
  --message-id '<MESSAGE_ID>' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml" \
  --workspace "$HOME/Documents/CareerCopilot" \
  --approved-plan-sha256 '<HASH_FROM_REVIEWED_DRY_RUN>' \
  --apply
```

In `draft_only`, the adapter blocks the mutation before any Gmail request. A successful apply confirms that the `UNREAD` label is absent.

Triage one explicit message without any Gmail mutation:

```bash
python3 "$ADAPTER" gmail-triage \
  --message-id '<MESSAGE_ID>' \
  --account-ref me \
  --workspace "$HOME/Documents/CareerCopilot"
```

Triage writes only a minimal private ledger and returns a review proposal; a repeated message is an idempotent `already_processed` no-op. A corrupt ledger or a fingerprint collision blocks the flow for human review. It never infers a tracker fact from message text. To record a fact, pass an explicitly reviewed `--supported-fact` plus exactly one minimal `--excerpt` or a lowercase 64-character SHA-256 `--content-sha256`.

Bind a reviewed opaque evidence reference to a deterministic tracker proposal. This command is read-only and cannot modify Gmail, a CSV tracker, Sheets or any remote tracker:

```bash
python3 "$ADAPTER" gmail-reconcile \
  --snapshot-json "$TRACKER_SNAPSHOT_JSON" \
  --fields-json "$FIELDS_JSON" \
  --record-json "$REVIEWED_RECORD_JSON" \
  --evidence-ref 'evidence/gmail-evidence.jsonl#<EVIDENCE_UUID>'
```

The caller must resolve the target identity and review the returned decision. Identity ambiguity, collisions and insufficient support remain blocking states, not automatic tracker updates.

Sending, replying, forwarding and creating drafts are intentionally unsupported in this adapter version. Career Copilot can prepare local draft text, but a separate approved workflow must handle transmission.

## Obsidian

Preview a note write:

```bash
python3 "$ADAPTER" obsidian-write \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --relative-path 'CareerCopilot/Interview Brief.md' \
  --content-file '/path/to/local/interview-brief.md'
```

The preview returns an `approval_sha256` bound to the content, relative note path and one canonical vault without revealing the vault path. Applying requires that exact reviewed hash, a private profile and a private workspace; the adapter writes atomically, reads the exact note back and preserves a minimal audit trail. Applied writes reject vaults that are symlinks or reside in the distribution or any Git repository. Remote Kanban is intentionally out of scope for 0.8: there is no Kanban adapter or synchronization.

```bash
python3 "$ADAPTER" obsidian-write \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --relative-path 'CareerCopilot/Interview Brief.md' \
  --content-file '/path/to/local/interview-brief.md' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml" \
  --workspace "$HOME/Documents/CareerCopilot" \
  --approved-plan-sha256 '<HASH_FROM_REVIEWED_DRY_RUN>' \
  --apply
```

### Optional Obsidian Kanban

`obsidian-kanban-project` projects one reviewed artifact into one local board using the public Obsidian Kanban Markdown grammar (`kanban-plugin: board`, `##` lanes, Markdown task cards, and a settings block). It never scans a vault, imports board content, syncs, or treats a board as tracker authority.

Preview first; this does not write:

```bash
python3 "$ADAPTER" obsidian-kanban-project \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --relative-path 'CareerCopilot/Board.md' \
  --lane 'To do' \
  --artifact-json '{"artifact_ref":"evidence/gmail-evidence.jsonl#<UUID>","card_text":"Reviewed synthetic summary"}'
```

The plan binds the canonical vault, relative path, current board fingerprint, lane, opaque artifact reference, generated opaque card marker and exact Markdown payload. To write, repeat the exact reviewed arguments with `--profile`, `--workspace`, `--approved-plan-sha256`, and `--apply`. The vault must be private, non-symlinked, outside Git/distribution paths, and the current board must still match the reviewed plan. The adapter writes atomically and verifies exact readback.

## Testing without accounts

`tests/test_adapters.py` uses fake command runners for Google and a temporary local vault for Obsidian. CI never needs account credentials.
