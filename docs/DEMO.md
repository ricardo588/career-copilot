# Synthetic end-to-end demo

The bundled scenario proves the local workflow without using a real candidate, employer, account or vacancy.

## Flow

1. Load a synthetic candidate profile and rules.
2. Load a synthetic open vacancy from a reserved `.test` URL.
3. Evaluate title, seniority, eligibility, freshness and evidence overlap.
4. Load a sourced synthetic Human Path with contact, recruiter and hiring manager.
5. Create one canonical tracker row with Human Path fields.
6. Re-run safely without creating a duplicate.
7. Load sourced interviewer facts plus explicitly labeled hypotheses.
8. Generate an interview brief using only declared evidence.
9. Record that zero external actions occurred.

## Run

From an installed profile:

```bash
SKILL_DIR="$HOME/.hermes/profiles/<PROFILE>/skills/career-copilot"
OUTPUT_DIR="$(mktemp -d)/career-copilot-demo"
python3 "$SKILL_DIR/scripts/run_synthetic_demo.py" --output-dir "$OUTPUT_DIR"
```

From the source repository:

```bash
OUTPUT_DIR="$(mktemp -d)/career-copilot-demo"
python3 skills/career-copilot/scripts/run_synthetic_demo.py --output-dir "$OUTPUT_DIR"
```

Generated artifacts:

- `demo-result.json`
- `tracker.csv`
- `interview-brief.md`

## Pass criteria

- `evaluation.recommendation` is `High`.
- Exactly three requirements are supported by meaningful evidence overlap.
- The unrelated commercial-management requirement is not marked as supported.
- `tracker_rows` is `1`.
- `human_path.status` is `confirmed`.
- `external_actions` is `0`.
- The interview brief contains Human Path, interviewer intelligence and the evidence guardrail.

The fixed default evaluation date is `2026-08-26`, making the test reproducible.
