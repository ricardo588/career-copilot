# Offer records and negotiation drafts

## Intent

Keep private offer records source-dated and read-only by default. Compare the total package instead of reducing the decision to base salary alone. Draft negotiation language locally and never send, accept, decline, sign or reject without exact authorization and a verified readback.

## Private record shape

Store candidate-owned offer records in the private workspace only. Preserve the source record and label each key field as confirmed or unknown:

- `source`
- `date_received`
- `currency`
- `geography`
- `employment_type`

The record may also include a package comparison for:

- `base`
- `variable`
- `equity`
- `benefits`
- `location`
- `flexibility`
- `scope`
- `risk`
- `candidate_tradeoffs`

Each category should keep the offer value separate from the candidate priority or tradeoff note.

## Market research

Any market note must carry its own source URL and date.

- Do not state a market fact without a source.
- Do not reuse a stale market note without its retrieval date.
- Keep market research in the private workspace; do not embed uncited claims in drafts.

## Draft kinds

Offer negotiation drafts are local only and may be one of:

- `acknowledgement`
- `clarification`
- `counterproposal`
- `accept`
- `decline`

These are draft labels, not permission to execute an external action.

## Authorization boundary

Never treat the following as complete unless exact authorization and verified readback exist for the specific destination and action:

- accept
- decline
- reject
- sign
- send

If the requested action is not exact and read back, keep the output as a draft and stop there.

## Advice boundary

Offer negotiation support is not legal, tax or financial advice.

## Synthetic example

- `skills/career-copilot/examples/synthetic/offer-negotiation.json`
