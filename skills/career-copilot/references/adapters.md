# Optional adapter contract

Use `scripts/adapters.py`. All Google mutations and all Obsidian writes are dry-run-first. Add `--apply` only after the user approves the exact target and change.

## Google Sheets

Prerequisites: a compatible authenticated `gws` CLI and a locally supplied spreadsheet ID.

- `sheets-read` reads an explicit range.
- `sheets-update` previews by default.
- `sheets-update --apply` writes only that range and reads it back.
- A readback mismatch is failure, even if the command exited successfully.

Never place spreadsheet IDs or credential paths in the skill/repository.

## Gmail

- `gmail-search` lists message IDs from a narrow query.
- `gmail-get` reads one full message before classification.
- `gmail-mark-read` previews by default.
- `gmail-mark-read --apply` removes `UNREAD` and confirms the label is absent.
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
