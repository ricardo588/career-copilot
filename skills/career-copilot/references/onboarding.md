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

Ask one phase at a time and allow the user to skip optional fields.

1. **Goals** — target roles and target seniority.
2. **Evidence** — strengths and concrete verified achievements/examples.
3. **Constraints** — at least one eligible country or location; optional work modes, employment types and exclusions.
4. **Preferences** — industries, source priority and vacancy freshness.
5. **Compensation** — optional and disabled unless the user wants it considered.
6. **Documents** — optional local paths; never upload or copy documents without a separate request.
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

- `profile.target_roles`
- `profile.target_seniority`
- `profile.strengths`
- `profile.verified_evidence`
- at least one of `constraints.countries` or `constraints.locations`
- `permissions.tracker_updates`


Blank means unknown, never permission to infer.

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
- **Workspace inside profile/repo:** stop and select an external private directory.
