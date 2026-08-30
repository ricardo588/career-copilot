# Vacancy evaluation

Evaluate against the candidate's private profile and rules, never against hard-coded author preferences.

## Decision order

1. Is the role still open and is the source current enough?
2. Is the candidate eligible for the location and work arrangement?
3. Does seniority align?
4. Do responsibilities match a target track?
5. Is there verified evidence for the critical requirements?
6. Are any local hard exclusions triggered?
7. Is the expected value worth the candidate's time?

## Output

- Company and role
- Recommendation: High / Medium / Low / Discard
- Confirmed match: concise evidence
- Gaps or risks: clearly labeled
- Unknowns requiring verification
- Recommended next action

## Rules

- Missing information is unknown, not a match.
- Do not invent experience, metrics or domain exposure.
- Never infer or use age, gender, sex, race or ethnicity, religion, disability, medical or genetic information, marital or family status, pregnancy, or another protected/non-job-relevant attribute to score fit.
- Never derive those attributes from names, photos, dates, graduation years or similar proxies.
- Candidate-declared, job-relevant eligibility and accommodation facts live under `constraints.job_eligibility` and `constraints.accommodations`. They are exposed as `candidate_declared_job_constraints`, not added to the evidence-based fit score; supported eligibility fields may still act as explicit hard constraints.
- Missing demographic information is neither a gap nor an unknown to research.
- Vacancy requirements may use structured categories (`job_requirement`, `protected_attribute`, `protected_proxy`, `non_job_relevant`). Protected/non-job-relevant categories are excluded from deterministic requirement matching and counted in `ignored_non_job_relevant_requirements`.
- Legacy string requirements are rejected only when an explicit discriminatory criterion or protected proxy is present. The scorer never deletes isolated keywords as a substitute for semantic classification; phrases such as “aged care”, “single point”, disability accessibility, “good faith” and medical-platform work remain job-relevant.
- A keyword match without responsibility/seniority alignment is weak evidence.
- If the role is inaccessible, closed or fails a hard constraint, stop early and explain the reason.
- For batches, evaluate all supplied URLs and deduplicate before proposing tracker changes.
