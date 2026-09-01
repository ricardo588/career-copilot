# Assessment prep

## Scope

Prepare private presentation, case or assessment materials without sending anything externally or scoring protected attributes.

## Run

```bash
python3 ${HERMES_SKILL_DIR}/scripts/pipeline.py \
  --assessment-prep <PRIVATE_ASSESSMENT_PREP_JSON> \
  --assessment-prep-md <PRIVATE_OUTPUT_MD>
```

## Output contract

The private markdown brief must keep these sections separate:

- known instructions;
- assumptions;
- open questions;
- suggested structure;
- rehearsal plan;
- technical and logistics checks;
- psychometric guidance, when relevant;
- declared accommodations and constraints, when relevant;
- risks;
- next steps.

The suggested structure should cover, as appropriate:

- problem;
- evidence;
- options;
- recommendation;
- risks;
- next steps.

## Guardrails

- Rehearsal is timeboxed and includes technical and logistics checks before the assessment.
- Psychometric guidance explains format, timing, allowed aids and accommodation steps.
- Never coach falsification, hidden identity or condition masking.
- Do not invent validity, pass-rate or hiring statistics without a source.
- Candidate-declared accommodations stay separate from scoring and are never used as inference targets.
- Protected attributes are not scored, inferred or converted into prep hypotheses.

## Synthetic verification

- `examples/synthetic/assessment-prep.json`

Use only synthetic fixtures or candidate-approved private notes.
