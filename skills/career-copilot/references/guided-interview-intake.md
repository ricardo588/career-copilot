# Guided interview intake

`interview_intake.py` normalizes candidate-provided interview logistics locally before any interviewer research or brief generation.

```bash
python3 skills/career-copilot/scripts/interview_intake.py --input /private/workspace/interview-intake.json
```

It requires only confirmed `company`, `stage` and `source`. A listed participant requires both name and role. It preserves optional candidate hypotheses separately, labels missing logistics as `unknowns`, returns `research_status: not_started`, and has `external_actions: 0`.

After confirming visible attendees, invoke the existing separate interviewer-research and interview-brief workflow. Do not infer an attendee, mandate, employment relationship or authorization from title or an intake draft.
