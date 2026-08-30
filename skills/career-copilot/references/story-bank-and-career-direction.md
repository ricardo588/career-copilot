# Private story bank and career direction

## Data boundary

`stories.jsonl` belongs beside `profile.yaml` in the candidate workspace. It must remain outside the installed profile, skill directory and every Git repository. Bootstrap creates it with mode `0600`; the workspace remains `0700`.

The repository contains only the schema, deterministic tooling and synthetic fixtures. Never copy a real story bank into the distribution.

## Story record

Each JSONL record has a stable `id` and separates:

- context and challenge;
- candidate actions;
- confirmed result facts and explicit unknowns;
- confirmed metrics, each with unit, source and user confirmation;
- evidence sources and provenance;
- competency, role or industry tags;
- recency;
- confidentiality (`shareable`, `candidate_private` or `restricted`);
- `user_confirmed` state.

Metrics and outcomes are never inferred. Client/employer-confidential detail is omitted by default. A STAR/CAR/DAR rendering is a view of one record, never a new source or fact.

## Legacy evidence

Onboarding schema 4 preserves `profile.verified_evidence`. If the story bank is empty at finalization, each existing evidence string is also represented by a stable migrated story whose provenance names `verified_evidence`, whose metrics are empty and whose missing detail remains explicit. The original profile list is not removed or rewritten.

## Selection and views

Use one confirmed story by stable ID across evaluation, interview and optional CV work. Do not duplicate rendered wording back into the bank as a new fact.

```bash
python3 "$SKILL_DIR/scripts/story_bank.py" \
  --profile "$WORKSPACE/profile.yaml" \
  --stories "$WORKSPACE/stories.jsonl" \
  --vacancy "$WORKSPACE/applications/example-vacancy.json" \
  --mode interview
```

- `evaluation`: concise context, actions, results, explicit unknowns and provenance.
- `interview`: STAR-style view from the same source record.
- `cv`: only candidate-confirmed `shareable` stories.
- `restricted` stories are excluded from all generated views.

`--migrate-verified-evidence` is the only write mode. Without it, the command is read-only.

## Optional career direction

Schema 4 adds optional `profile.career_direction` sections:

- `success_criteria`
- `values`
- `non_negotiables`
- `tolerable_tradeoffs`
- `development_gaps`
- `departure_narrative`

Every section keeps `facts`, `interpretations` and `preferences` separate. Empty or unknown preferences are not filters. Candidate preferences are subjective tradeoff inputs, not objective employer facts; compare them only with sourced `vacancy.career_signals`.

A departure narrative is reusable only when `candidate_approved` is true. Draft wording uses the approved factual list; interpretations are never silently promoted into the statement and nothing is published automatically.
