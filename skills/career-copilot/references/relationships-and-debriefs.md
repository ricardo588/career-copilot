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

## Selective weak-tie reconnection

This route is for building or renewing a professional relationship, **not** for outreach about a specific vacancy. Read the candidate's private `rules.yaml` `relationship_networking` settings before proposing work. If enabled, propose at most `max_candidates_per_cycle` candidates (default: 3; fewer or zero is valid).

Each candidate must have a real, candidate-owned relationship context such as a former colleague, client, industry contact or indirect connection with an explicit shared context. For every proposed reconnection, keep private:

- the verified relationship context and its freshness;
- the distinct perspective, industry or non-redundant network bridge it could provide; and
- an optional short, personal draft.

The first-contact draft must not ask for a job, a specific vacancy, a referral or an introduction. It may renew the connection, share a truthful relevant update, or invite a low-pressure exchange. The configured prohibitions in `initial_contact` are hard limits. A draft remains a draft; exact contact authorization and the configured external-action mode still govern any sending.

For a specific vacancy, do **not** relabel this route as relationship building to bypass the Human Path workflow. Follow the normal vacancy workflow, preserve the distinction between discovery and authorization, and use vacancy-specific outreach only with the required current evidence and exact approval.

## Evidence-led positioning

For a pitch, introduction or letter, select two or three private, verified proof points. Each proof point should make clear:

1. the problem or scope (scale, complexity, region, portfolio or relevant stakeholder);
2. the candidate's leadership action; and
3. a concrete outcome, only when supported by the candidate profile, approved CV or a confirmed story record.

Prefer evidence relevant to the opportunity. Do not invent numbers, certifications, technical depth, outcomes or relationship claims. The process may prepare candidate-review-only wording, but it never modifies a source CV without explicit, fresh candidate approval.

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
