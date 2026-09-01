# Requirement matrix and opt-in CV review

## Requirement-to-evidence matrix

Build one private matrix per opportunity before relying on automated fit explanations, interview preparation or a CV review:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/requirement_matrix.py \
  --profile <PRIVATE_WORKSPACE>/profile.yaml \
  --vacancy <PRIVATE_VACANCY_JSON> \
  --stories <PRIVATE_WORKSPACE>/stories.jsonl \
  --output <PRIVATE_WORKSPACE>/applications/<opportunity>-requirement-matrix.json
```

The vacancy must contain its current `canonical_url`. Each job-relevant requirement is recorded with that cited source, an assessment (`direct`, `transferable`, `gap` or `unknown`), private evidence references and a follow-up action. `transferable` is explicitly analysis, **not** direct experience. A gap is an explicitly candidate-declared gap; an unknown has no verified evidence yet. Structured protected/non-job-relevant requirements are excluded and shown separately.

On refresh, retain the old matrix privately and pass it with `--prior`; changed canonical source content is exposed as `source_changed` while private evidence references remain traceable.

Use a compatible matrix when producing an evaluation/brief:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/pipeline.py \
  --profile <PRIVATE_WORKSPACE>/profile.yaml --rules <PRIVATE_WORKSPACE>/rules.yaml \
  --vacancy <PRIVATE_VACANCY_JSON> --as-of <YYYY-MM-DD> \
  --requirement-matrix <PRIVATE_MATRIX_JSON> --brief <PRIVATE_BRIEF.md>
```

The pipeline rejects a matrix whose canonical vacancy URL differs from the evaluated vacancy. The matrix is a source of references; it never authorizes copying facts into a tracker, CV or message.

## Local CV and ATS-safe review

The review is explicitly opt-in and never modifies the source CV. It locally extracts `.txt`, `.md` and `.docx`; PDFs require a local `pdftotext` binary. It reports extraction quality, layout signals, date/title items for candidate review and contact-data signals. These are checks, not a universal ATS guarantee.

```bash
python3 ${HERMES_SKILL_DIR}/scripts/cv_review.py \
  --cv <CANDIDATE_APPROVED_LOCAL_CV> \
  --matrix <PRIVATE_MATRIX_JSON> \
  --output <PRIVATE_WORKSPACE>/applications/<opportunity>-cv-review.json
```

The private report uses `0700/0600` permissions, keeps the original file untouched and presents candidate-review-only changes anchored in requirement-matrix evidence references. It does not estimate rejection rates, add template galleries, auto-rewrite content, or recommend keyword stuffing. Any real CV edit needs fresh, explicit candidate approval and must preserve truthful evidence.
