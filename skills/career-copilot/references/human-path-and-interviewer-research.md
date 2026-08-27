# Human Path and interviewer intelligence

## Purpose

For every viable vacancy, research whether the candidate has a credible human route to the company and preserve that evidence for later stages. Once an interview is scheduled, research the confirmed interviewer(s) and use verified facts as preparation input.

Research is read-only. Finding a person never authorizes following, connecting, messaging, emailing, reacting or requesting a referral.

## Human Path workflow

Run this after canonical vacancy verification and before final prioritization.

1. **Candidate-owned contacts**
   - Search configured private contact sources first.
   - Require an exact identity and current evidence that the person works at the vacancy company.
   - Record relationship strength separately from current company/role.
   - Do not use fuzzy name matches, similarly named companies or historical employment as confirmation.

2. **Recruiter or vacancy poster**
   - Inspect the canonical posting and the direct recruiter message, when present.
   - Confirm that the person is tied to this exact vacancy or requisition.
   - Distinguish internal recruiter, external headhunter and generic talent contact.
   - A recruiter tied to a confidential client is not evidence of the client's identity.

3. **Hiring manager**
   - Look for an explicitly named manager in the posting, invitation or recruiter message.
   - Otherwise research the most likely owning organization using current company pages, direct public profiles and credible professional sources.
   - Label a likely manager as a hypothesis until a direct source or recruiter confirms ownership.

4. **Classify the result**
   - `confirmed`: exact identity, current role/company relationship and direct source URL.
   - `unverified`: plausible identity but missing direct current evidence.
   - `none_found`: no credible path after the scoped search.

5. **Persist and verify**
   - Store only the minimum necessary fields in the private tracker.
   - Keep source URL and retrieval date in the private research artifact.
   - Read the tracker back after any update.

## Human Path evidence shape

```json
{
  "contacts": [
    {
      "name": "Example Person",
      "path_type": "trusted_contact",
      "current_company": "Example Company",
      "current_role": "Example Role",
      "relationship": "former colleague",
      "source_url": "https://example.test/profile",
      "confidence": "confirmed"
    }
  ],
  "recruiter": null,
  "hiring_manager": null,
  "retrieved_at": "YYYY-MM-DD"
}
```

Use `scripts/pipeline.py --human-path <private-json>` to validate and incorporate this evidence into the tracker and brief.

## Interviewer research trigger

Start interviewer research only when an interview or named conversation is confirmed. Do not prepare speculatively from an assumed manager.

1. Reconcile the invitation, recruiter message or user-provided evidence.
2. Confirm every visible attendee, organizer, interview stage and duration.
3. Verify each interviewer's current identity and role using direct public sources when accessible.
4. Extract only job-relevant confirmed facts:
   - current mandate and scope;
   - career path relevant to the role;
   - public operating language, frameworks or transformation themes;
   - recent company-relevant talks, articles or official bios.
5. Keep likely priorities and likely questions under `hypotheses`; never present them as facts.
6. Do not infer personality, management style, influence or preferences from a title, credential, photo or demographic characteristic.
7. Map candidate evidence to the confirmed mandate and prepare:
   - a 60–90 second opening;
   - three or four proof stories;
   - likely questions and one mini-case;
   - risks to neutralize;
   - questions about mandate, success measures, team, decision rights and first-six-month outcomes.
8. Cite each source in the research artifact and retain the source URL in the brief.

## Interviewer research shape

```json
{
  "interviewers": [
    {
      "name": "Example Interviewer",
      "current_role": "VP Transformation",
      "source_url": "https://example.test/interviewer",
      "confirmed_facts": ["Leads enterprise transformation"],
      "hypotheses": ["May focus on value realization"]
    }
  ],
  "invitation": {
    "stage": "hiring-manager interview",
    "duration_minutes": 60,
    "organizer": "Example Recruiter"
  },
  "retrieved_at": "YYYY-MM-DD"
}
```

Use `scripts/pipeline.py --interviewer-research <private-json> --brief <private-md>` to include sourced facts and explicitly labeled hypotheses in the interview brief.

## Output contract

Always separate:

- confirmed identities and facts;
- hypotheses;
- unknowns;
- candidate evidence to use;
- recommended next step;
- authorization status (`draft_only` or `confirm_each_external`).
