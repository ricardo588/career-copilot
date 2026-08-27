# Privacy and external actions

## Data boundary

Public/distributable: workflows, schemas, templates, validators and synthetic examples.

Private/user-owned: candidate profile, CVs, compensation, contacts, messages, tracker contents, document paths, memories, sessions, credentials and integration identifiers.

## External-action modes

- `draft_only` — default. Read authorized sources, research, analyze, prepare drafts/previews and update approved private local state. Block sending, applying, publishing, contacting people and third-party mutations even if text was approved or `--apply` was supplied.
- `confirm_each_external` — explicit opt-in for other users. Every exact action, destination and content still requires fresh confirmation and execution proof.
- `external_action_mode_locked: true` — profile policy. The mode must remain `draft_only`; onboarding and checkpoint reset cannot change it.

Human Path and interviewer research are read-only in both modes. Finding a person never authorizes following, connecting, reacting, emailing or messaging.

## Proof rules

- Drafted does not mean sent.
- Approved does not mean sent.
- A Human Path does not mean contacted or referral-ready.
- Tracker status `applied` requires candidate confirmation or authoritative submission evidence.
- A tool success must be verified with a returned ID, URL, readback or visible state when possible.

## Repository guard

Never write candidate data beneath the distribution repository. Before committing or publishing, run the privacy scanner with any known private markers supplied only through the `PRIVATE_MARKERS` environment variable.
