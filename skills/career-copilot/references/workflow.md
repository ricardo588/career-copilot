# Operating workflows

## Evaluate a vacancy

1. Read the minimum profile and rules.
2. Fetch or inspect the current canonical posting.
3. Apply eligibility and hard exclusions first.
4. Assess fit using verified candidate evidence; require meaningful multi-term overlap for multi-term requirements.
5. Deduplicate against the tracker using canonical URL or external job ID.
6. Research the Human Path: current trusted contacts, exact recruiter/poster and confirmed or likely hiring manager. Separate sourced identities from hypotheses.
7. Recommend a next action; update the tracker only under local permissions.
8. Optionally use `scripts/pipeline.py` for deterministic evaluation, Human Path normalization, CSV update and brief generation, but never treat it as live-source verification.

## Search

1. Read source priorities, target roles, geography and freshness.
2. Prefer official employer/ATS sources, then configured secondary sources.
3. Treat search output as a shortlist, not approved tracker entries.
4. Verify each promising role on a canonical source.
5. Deduplicate before writing.
6. Run a scoped Human Path search for every viable role before final prioritization.
7. Report reviewed sources, verified additions, Human Paths, discards and incomplete sources.

## Reconcile evidence

1. Identify authoritative evidence: submission confirmation, recruiter message, interview invitation, rejection, withdrawal or offer.
2. Match it to a stable tracker record.
3. Apply the newest authoritative state without inventing intermediate events.
4. Update next action only when concrete.
5. Verify state by readback.

## Draft outreach

1. Identify relationship, channel and objective.
2. Use only verified candidate/contact context.
3. Draft concise copy appropriate to the channel.
4. Do not send without explicit approval.

## Interview preparation

1. Verify the company, role and current stage.
2. Reconcile the invitation and confirm every visible interviewer, organizer, stage and duration.
3. Research current company/role facts and each confirmed interviewer from credible direct sources.
4. Separate interviewer facts from hypotheses; do not infer personality or preferences.
5. Select real candidate evidence from the private profile and map it to the interviewer's confirmed mandate.
6. Prepare pitch, stories, likely questions, one mini-case, risks and candidate questions.
7. Separate confirmed company/interviewer facts from positioning recommendations.

## Assessment preparation

1. Read the exact prompt or instructions before planning content.
2. Separate known instructions from assumptions and open questions.
3. Build the answer around problem, evidence, options, recommendation, risks and next steps as appropriate.
4. Timebox rehearsal, including technical and logistics checks before the assessment.
5. For psychometric assessments, explain format, conditions, timing and allowed aids; never coach falsification or hidden identity.
6. Keep candidate-declared accommodations separate from scoring and never infer protected attributes.
7. Write a private read-only brief only; do not send or externalize the artifact.

## Status summary

Return active priorities, blockers with owners, and the next one to three concrete actions. Do not turn passive waiting into an artificial task.

## Review follow-ups

1. Run `scripts/pipeline.py --review-tracker <csv> --as-of <YYYY-MM-DD>` with an explicit review date.
2. Treat `follow_up_overdue` as a derived reminder, not a process event or assertion about another person's response.
3. Report missing dates as `unknown` and malformed dates as `invalid`.
4. Preserve every tracker row, status and next action; the review path is read-only.
