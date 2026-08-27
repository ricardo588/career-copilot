# Optional adapter contract

Use `scripts/adapters.py`. All Google mutations and all Obsidian writes are dry-run-first. External Google mutations also require `--profile <private-profile.yaml>`. A `draft_only` profile blocks them even when `--apply` is present; `confirm_each_external` permits the reviewed operation only after exact confirmation.

## Google Sheets

Prerequisites: a compatible authenticated `gws` CLI and a locally supplied spreadsheet ID.

- `sheets-read` reads an explicit range.
- `sheets-update` previews by default.
- `sheets-update --apply --profile <profile.yaml>` writes only that range and reads it back when the profile is `confirm_each_external`.
- A readback mismatch is failure, even if the command exited successfully.

Never place spreadsheet IDs or credential paths in the skill/repository.

## Gmail

- `gmail-search` lists message IDs from a narrow query.
- `gmail-get` reads one full message before classification.
- `gmail-mark-read` previews by default.
- `gmail-mark-read --apply --profile <profile.yaml>` removes `UNREAD` and confirms the label is absent when permitted.
- Sending, replying, forwarding and draft creation are not implemented.

A local text draft is not authorization to send.

## Obsidian

- Resolve the concrete vault path locally.
- `obsidian-write` previews target path and character count.
- `obsidian-write --apply` writes atomically and reads back exact content.
- Only relative `.md` paths beneath the vault are allowed.

## Failure ladder

1. Stop after any wrong-account, wrong-target or verification signal.
2. Read the exact source object again.
3. Correct configuration locally; never commit IDs or credentials.
4. Retry only the smallest scoped operation.
5. Report success only with readback evidence.

See the repository `docs/ADAPTERS.md` for command examples.
