# Optional adapters

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
