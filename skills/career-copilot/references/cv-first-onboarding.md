# CV-first onboarding

## Intent

Ask whether the candidate already has a CV before asking for goals and evidence. When a CV exists, extract supported onboarding information locally, present it as a proposal, and apply it only after the user confirms or corrects it.

The CV is evidence, not authorization to invent preferences. Compensation, exclusions, acceptable work modes, tracker permissions and external-action policy normally still require direct questions.

## Conversation flow

1. Start or resume onboarding and inspect `next_question`.
2. Ask `documents.has_cv` first.
3. If false, continue with manual questions.
4. If true, explain that Hermes extracts the file locally but the extracted content is processed by the model provider configured for that Hermes profile unless the user uses a local model. Ask the user to attach the CV or provide a local `.pdf`, `.docx`, `.txt` or `.md` path only if they accept that boundary, then store the path in `documents.primary_cv`.
5. Read the file with Hermes `read_file`; it extracts text from PDF and DOCX. Do not upload the CV to any additional document parser, OCR vendor or model service.
6. If the file is scanned and local text extraction is empty, use local OCR only when available and appropriate. Otherwise run `cv-skip` and continue manually.
7. Build proposals only for the allowlisted fields below. Label each proposal `direct` or `inferred` and name the CV section that supports it.
8. Stage the proposals with `cv-propose`. Show the resulting proposal summary to the user.
9. Ask the user to confirm, correct or reject the proposals. Do not call `cv-confirm` before that response.
10. Apply the confirmed set with `cv-confirm`, then ask only for required or optional information the CV could not establish.

## Supported fields

- `profile.display_name`
- `profile.target_roles`
- `profile.target_seniority`
- `profile.target_industries`
- `profile.strengths`
- `profile.verified_evidence`
- `constraints.countries`
- `constraints.locations`

Treat target roles, seniority, industries and eligible locations as **inferred** unless the CV explicitly states an objective, authorization, relocation or work-location preference. A current address is not automatically an eligible search location. Never convert missing information into a proposal.

`profile.verified_evidence` must preserve factual meaning. Do not improve titles, metrics, scope or outcomes.

## Stage proposals

Prefer a temporary JSON file with private permissions rather than embedding candidate data in shell history:

```json
{
  "source_file": "/private/local/path/CV.pdf",
  "proposals": {
    "profile.display_name": {
      "value": "Example Candidate",
      "basis": "direct",
      "source": "header"
    },
    "profile.target_roles": {
      "value": ["Program Director"],
      "basis": "inferred",
      "source": "headline and recent roles"
    },
    "profile.verified_evidence": {
      "value": ["Led the stated transformation program"],
      "basis": "direct",
      "source": "experience"
    }
  }
}
```

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <WORKSPACE> cv-propose --json-file <PRIVATE_PROPOSAL_JSON>
```

The source path must match `documents.primary_cv`. Unsupported fields—including compensation, permissions and external-action settings—are rejected.

## Confirm, correct or reject

After the user explicitly confirms the summary:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <WORKSPACE> cv-confirm \
  --overrides-json '{"profile.target_roles":["Transformation Director"]}' \
  --reject-fields-json '["profile.target_industries"]'
```

An override corrects one proposed value. A rejected field remains unanswered and may be collected manually. The checkpoint records which proposed fields were applied or rejected.

`cv-propose` records the CV's SHA-256 fingerprint. `cv-confirm` recalculates it and refuses to apply proposals if the file changed at the same path. Re-read and restage the CV instead of confirming stale proposals.

Pending proposals created before version 0.4.1 do not have a fingerprint and must also be restaged before confirmation.

Changing `documents.primary_cv` clears fields still attributed to the previous CV and requires a new proposal/confirmation. A field manually edited after confirmation is detached from CV provenance and is preserved.

If local extraction cannot be completed:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <WORKSPACE> cv-skip --reason "local text extraction unavailable"
```

## Privacy rules

- Do not copy the source CV into the skill, installed profile or Git clone.
- The CV may remain at its candidate-chosen local path, provided it is outside the installed profile, distribution and any Git repository; the private profile stores only that path and import status.
- Keep proposal files and checkpoints private (`0600`) and delete temporary proposal files after staging.
- Do not retain full extracted CV text in the checkpoint. Store only the proposed values, `direct`/`inferred` basis and source-section labels needed for confirmation.
- The configured Hermes model provider may process extracted CV text; do not claim the entire inference path is local unless that profile uses a verified local model.
- Never extract or request passwords, tokens, government IDs, financial identifiers or other secrets.
