# Hunter process review

`hunter_process_review.py` creates local, deterministic review artifacts from an **explicit local snapshot**. It is designed for private workspaces only.

## Boundary

The command never opens URLs, queries Google Sheets, reads credentials or environment variables, invokes a browser, sends messages, applies, writes a tracker, or mutates its inputs. It uses no network or subprocess path.

Inputs and outputs are private candidate data. Keep them outside the Career Copilot distribution repository and any Git repository. Repository fixtures are synthetic and use `example.test` only.

## Inputs

- `--snapshot`: JSON export with `metadata`, `headers`, and physical `rows`.
- `--mapping`: mapping YAML following `templates/hunter-process-mapping.template.yaml`.
- `--workspace`: canonical private workspace that bounds output paths.
- `--as-of`: ISO date (`YYYY-MM-DD`) used only for deterministic review.
- `--output-json`, `--output-md`: distinct absolute paths below `--workspace`.

The mapping must contain exactly the ten logical fields. Headers are exact and fail closed when missing, duplicate, or padded. Unknown snapshot columns are tolerated but never copied into the normalized analysis.

## Commands

```bash
python3 skills/career-copilot/scripts/hunter_process_review.py report \
  --snapshot /private/Hunter/snapshot.json \
  --mapping /private/Hunter/hunter-process-mapping.yaml \
  --workspace /private/Hunter \
  --as-of 2026-11-23 \
  --output-json /private/Hunter/reports/review.json \
  --output-md /private/Hunter/reports/review.md
```

```bash
python3 skills/career-copilot/scripts/hunter_process_review.py packet \
  --snapshot /private/Hunter/snapshot.json \
  --mapping /private/Hunter/hunter-process-mapping.yaml \
  --context /private/Hunter/decision-context.json \
  --workspace /private/Hunter \
  --opportunity-id 7 \
  --as-of 2026-11-23 \
  --output-json /private/Hunter/reports/packet-7.json \
  --output-md /private/Hunter/reports/packet-7.md
```

Outputs are refused if they exist unless `--overwrite` is explicit. The command rejects symlink workspaces, symlinked output paths, paths outside the workspace, and paths in a Git/distribution repository. It creates private directories as `0700` and files as `0600` where supported.

`packet` accepts only one existing, valid, unambiguous `No`. Context is optional and schema-versioned; unknown top-level fields are rejected. A contact signal never grants contact, referral, reference, introduction, or follow-up authorization.

## Interpretation

A report distinguishes snapshot facts, data-quality signals, and external unknowns. URL tracking parameters are removed only for duplicate comparison; the original URL is retained in a decision packet. A contact in the snapshot is always an unverified signal unless the supplied Human Path artifact provides exact identity, current company, a direct source, and a valid retrieval date.

The generated recommendation is local review guidance only. Every packet includes: `Borrador/revisión solamente. Ricardo debe aprobar y ejecutar cualquier acción externa exacta.`

## Synthetic demo

Use only synthetic fixtures during repository verification:

```bash
workspace=$(mktemp -d)
python3 skills/career-copilot/scripts/hunter_process_review.py report \
  --snapshot skills/career-copilot/examples/synthetic/hunter-process-snapshot.json \
  --mapping skills/career-copilot/examples/synthetic/hunter-process-mapping.yaml \
  --workspace "$workspace" --as-of 2026-11-23 \
  --output-json "$workspace/review.json" --output-md "$workspace/review.md"
```
