# Guided private story capture

`story_capture.py` turns an explicit private JSON capture into a reviewable STAR proposal. It never writes a story bank, tracker, CV or external system.

```bash
python3 skills/career-copilot/scripts/story_capture.py --input /private/workspace/story-capture.json
```

The capture must provide a `title`; optional inputs are `context`, `challenge`, `actions`, `results.facts`, `results.unknowns`, `confirmed_metrics`, `tags` and `confidentiality`.

Every proposal has `confirmation_required: true` and `story.user_confirmed: false`. It asks for missing context, challenge, actions, result facts, confirmed metrics and evidence sources. Unknowns are preserved rather than converted into achievements. A metric is accepted only when the candidate supplies its label, value, unit and source and sets `confirmed_by_user: true`.

Review the proposal with the candidate. After explicit confirmation, run the same command against the reviewed proposal with `--confirm`; it returns one candidate-confirmed story record, still without writing a story bank. A separate private workspace update must persist that record. Do not infer an outcome, quantify an unsourced result or treat a draft as reusable interview/CV evidence.
