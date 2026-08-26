# Privacy and external actions

## Data boundary

Public/distributable: workflows, schemas, templates, validators and synthetic examples.

Private/user-owned: candidate profile, CVs, compensation, contacts, messages, tracker contents, document paths, memories, sessions, credentials and integration identifiers.

## Authorization levels

- `read`: inspect user-provided or connected sources.
- `draft`: prepare text or artifacts without transmitting them.
- `track`: update the user's private tracker.
- `external`: send, submit, publish, contact or modify a public/third-party system.

Default to `read` and `draft`. `track` follows the local rules. Every `external` action requires explicit approval for the specific destination and content.

## Proof rules

- Drafted does not mean sent.
- Approved does not mean sent.
- Tracker status `applied` requires candidate confirmation or authoritative submission evidence.
- A tool success must be verified with a returned ID, URL, readback or visible state when possible.

## Repository guard

Never write candidate data beneath the distribution repository. Before committing or publishing, run the privacy scanner with any known private markers supplied only through the `PRIVATE_MARKERS` environment variable.
