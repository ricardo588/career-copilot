# Checkpointed private onboarding

## Goal

Create a candidate-owned workspace without storing personal information in the distributable skill. Onboarding is resumable, phase-based and complete only after required evidence, eligibility and permission fields are present.

## Initialize

Resolve the configured workspace. It must be outside the installed profile/distribution and outside any Git clone containing Career Copilot.

```bash
python3 ${HERMES_SKILL_DIR}/scripts/bootstrap_workspace.py --workspace <WORKSPACE>
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <WORKSPACE> start
```

`start` resumes an existing checkpoint. Use `--reset` only when the user explicitly wants to discard the onboarding checkpoint; it does not delete profile, rules or tracker files.

## Conversation phases

Ask one phase at a time and allow the user to skip optional fields. The first question is always whether the candidate already has a CV.

1. **CV availability** — ask `documents.has_cv`.
2. **CV extraction and confirmation** — when true, request a local CV, follow `cv-first-onboarding.md`, and ask the user to confirm or correct the proposal. Never apply extracted fields silently.
3. **Goals and evidence** — ask only for required items the CV did not establish or the user rejected.
4. **Constraints** — at least one user-confirmed eligible country or location; optional work modes, employment types, structured `job_eligibility`, accommodations and exclusions. These are candidate declarations, not demographic inferences or fit evidence.
5. **Preferences** — industries, source priority and vacancy freshness.
6. **Compensation** — optional and disabled unless the user wants it considered.
7. **Permissions** — tracker update policy and external-action mode. `draft_only` is the default; `confirm_each_external` requires explicit opt-in.
8. **Integrations** — optional and disabled by default.

List the machine-readable catalog with:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <WORKSPACE> questions
```

## Checkpoint each answer

Use JSON values to preserve arrays, booleans and numbers:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <WORKSPACE> answer \
  --field profile.target_roles \
  --json-value '["Program Director","Transformation Director"]'
```

For a string, either use `--value '<text>'` or valid JSON with `--json-value`. Do not put secrets on the command line.

After each phase:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <WORKSPACE> status
```

Report progress and the next phase without echoing private answers unless requested.

## Required completion fields

- `documents.has_cv`
- when `documents.has_cv` is true: `documents.primary_cv` and either confirmed CV proposals or an explicit manual fallback
- `profile.target_roles`
- `profile.target_seniority`
- `profile.strengths`
- `profile.verified_evidence`
- at least one of `constraints.countries` or `constraints.locations`
- `permissions.tracker_updates`


Blank means unknown, never permission to infer.

## CV-first commands

When a CV exists, use `read_file` locally, stage supported fields with `cv-propose`, present the proposal to the user, and call `cv-confirm` only after the user confirms or corrects it. If extraction cannot be completed locally, use `cv-skip` and continue manually.

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <WORKSPACE> \
  cv-propose --json-file <PRIVATE_PROPOSAL_JSON>

python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <WORKSPACE> \
  cv-confirm --overrides-json '{}' --reject-fields-json '[]'
```

See `cv-first-onboarding.md` for the proposal schema, inference rules, privacy requirements and scanned-document fallback.

## Locked draft-only profiles

Initialize a user/profile that must never perform external actions with:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py \
  --workspace <WORKSPACE> start --lock-draft-only
```

The lock persists through `start --reset`. The onboarding `answer` command cannot modify the lock or select `confirm_each_external` while locked. Removing the lock requires an intentional manual policy migration outside conversational onboarding.

## Finalize

When `missing` is empty:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/onboarding.py --workspace <WORKSPACE> finalize
```

Finalization:

- validates required fields;
- writes JSON-compatible YAML to `profile.yaml` and `rules.yaml`;
- creates one-time `.pre-onboarding.bak` copies of existing files;
- updates the private checkpoint to `complete`;
- never modifies `tracker.csv`.

## Edge cases

- **Interrupted conversation:** call `start` or `status`; do not restart questions already answered.
- **Candidate changes direction:** update only the changed fields, then finalize again.
- **Sensitive value accidentally offered:** do not persist secrets; ask the user to rotate them if exposed.
- **Conflicting answers:** label the conflict and ask before replacing the stored value.
- **Multiple candidates:** use separate workspaces and separate Hermes profiles when practical.
- **Incomplete evidence:** preserve the gap; do not create achievements or metrics.
- **Current location in CV:** treat it only as a proposed eligible location and require confirmation.
- **Scanned or unreadable CV:** use local OCR if available; otherwise switch to explicit manual fallback. Never upload it to an external parser by default.
- **Workspace inside profile/repo:** stop and select an external private directory.
