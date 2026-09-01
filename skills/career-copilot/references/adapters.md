# Optional adapter contract

Use `scripts/adapters.py`. All Google mutations and all Obsidian writes are dry-run-first. External Google mutations also require `--profile <private-profile.yaml>` and `--workspace <private-workspace>`. A `draft_only` profile blocks them even when `--apply` is present; `confirm_each_external` permits the reviewed operation only after exact confirmation.

Every attempted Google mutation is logged in the private workspace at `audit/external-actions.jsonl`; the directory is normalized to `0700` and each artifact file to `0600`. The log is append-only during normal operation, but it is an operational record rather than cryptographic tamper-proofing. It stores only a minimal target reference and a plan hash—never credentials or full messages/documents.

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
- `gmail-mark-read --apply --profile <profile.yaml> --workspace <workspace>` removes `UNREAD`, records attempt/applied/verified audit events, and confirms the label is absent when permitted.
- For any tracker fact or process update derived from a Gmail message, first write a private evidence event with `record_gmail_evidence`. It stores account reference, message ID, optional thread ID, retrieval time, the directly supported fact, and one minimal excerpt **or** content hash. Pass its opaque `evidence_ref` to `pipeline.py --tracker`; never copy message bodies or message IDs to `tracker.csv`.
- Ambiguous or contradictory wording remains unknown. It cannot advance process state; in particular, `applied` still requires candidate confirmation or authoritative submission evidence.
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
