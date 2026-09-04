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
- The Gmail adapter cannot send messages.
- The Sheets adapter updates only an explicit range.
- The Obsidian adapter rejects paths outside the configured vault.

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

Preview marking a handled message as read:

```bash
python3 "$ADAPTER" gmail-mark-read \
  --message-id '<MESSAGE_ID>' \
  --profile "$HOME/Documents/CareerCopilot/profile.yaml"
```

In `confirm_each_external`, apply by adding `--apply` after exact confirmation. In `draft_only`, the adapter blocks the mutation. When applied, it confirms that the `UNREAD` label is absent.

Sending, replying, forwarding and creating drafts are intentionally unsupported in this adapter version. Career Copilot can prepare local draft text, but a separate approved workflow must handle transmission.

## Obsidian

Preview a note write:

```bash
python3 "$ADAPTER" obsidian-write \
  --vault "$OBSIDIAN_VAULT_PATH" \
  --relative-path 'CareerCopilot/Interview Brief.md' \
  --content-file '/path/to/local/interview-brief.md'
```

Apply by adding `--apply`. The adapter writes atomically and reads the exact note back.

## Testing without accounts

`tests/test_adapters.py` uses fake command runners for Google and a temporary local vault for Obsidian. CI never needs account credentials.
