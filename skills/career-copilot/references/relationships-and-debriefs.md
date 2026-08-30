# Relationship intelligence and interview debriefs

## Private relationship artifact

Store candidate-owned relationship records in the private workspace, never in the skill, installed profile or a Git repository. A record separates:

- `relationship_role`: contact, advocate, connector, recruiter/poster, probable decision maker or confirmed decision maker;
- `influence` and `strength`;
- `current_company` and `current_role`;
- `evidence`, direct `source_url`, `confidence` and `freshness`;
- `authorization.contact`, `reference`, `referral`, `follow_up` and `introduce`.

Identity, influence and authorization are independent. Discovering or confirming a person never authorizes contact, reference use, referral language, an introduction or follow-up. Legacy confirmed `trusted_contact` records are conservatively mapped as authorized contacts only for backward compatibility; new records must state authorization explicitly.

Probable and confirmed decision makers remain distinct. A probable identity without direct confirmation stays in `unverified_paths`.

## Informational meeting preparation

Generate a private read-only brief:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/pipeline.py \
  --relationship-prep <PRIVATE_RELATIONSHIP_JSON> \
  [--meeting <PRIVATE_MEETING_JSON>] \
  --relationship-prep-md <PRIVATE_OUTPUT_MD>
```

The meeting object can instead be embedded as `meeting` in the relationship artifact. It may include company, topic, objective, timebox, context, questions, a draft follow-up and a structured outcome. The output:

- labels each relationship and its authorization state;
- records objectives, questions and supplied outcomes;
- never claims a commitment or referral unless explicitly present;
- leaves follow-up as a draft;
- never sends, contacts or updates the application tracker.

Private Markdown writes are atomic, `0600`, read back for verification and rejected inside the distribution, installed profile or any Git repository.

## Post-interview debrief

Allowed outcomes are:

- `positive`
- `ambiguous`
- `rejected`
- `no_response`
- `failed_interview`

Run:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/pipeline.py \
  --interview-debrief <PRIVATE_DEBRIEF_JSON> \
  --interview-debrief-md <PRIVATE_OUTPUT_MD>
```

Keep `observed_facts` separate from `candidate_interpretation`. Sentiment is reflective context only and never changes tracker state. Record preparation, logistics, story quality, questions, signals, close, improvements, learning and unanswered questions without rewriting prior history.

`learning` can inform future private briefs. It is not evidence about an employer and must not retroactively alter prior interview records or tracker rows.

Rejected and failed-interview outcomes may produce respectful closure drafts. Other outcomes may also contain an appropriate draft. All remain drafts until an exact external action is separately approved, executed and verified; this CLI performs no external action.

## Synthetic verification

- `examples/synthetic/relationship-meeting.json`
- `examples/synthetic/interview-debrief.json`

These fixtures use synthetic identities and no live candidate data.
