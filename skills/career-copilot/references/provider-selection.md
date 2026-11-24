# Provider selection

`provider_selection.py` is a deterministic local selector. It consumes explicit private profile/rules JSON and writes one private JSON report. It does not open a provider, discover identifiers, use a browser, authenticate, modify a tracker or perform an external action.

## Coverage scope

The initial registry covers declared Mexico, Latin America, United States and remote-work conditions. It distinguishes:

- `integrated_read_only`: Greenhouse Job Board and Lever Postings have separately constrained public GET adapters. A candidate-confirmed board/site identifier and an explicit command are still required.
- `coverage_only`: a provider may be a manual-review suggestion but has no executable acquisition path.

A recommendation is coverage guidance, not a market ranking or evidence that a vacancy is current.

## Usage

```bash
python3 skills/career-copilot/scripts/provider_selection.py \
  --workspace /private/workspace \
  --profile /private/profile.json \
  --rules /private/rules.json \
  --output /private/provider-selection.json
```

Inputs and output must be inside the explicit existing private workspace, which must be outside the distribution and every Git repository. Inputs are read-only; existing outputs are refused. The writer is descriptor-anchored and rejects symlinked paths.

## Adding a provider

Do not add a network adapter only by inserting metadata. An executable provider needs a separately reviewed public contract, synthetic fixture, identifier and URL validation, no-redirect/network guard, focused tests and paired EN/ES documentation. Until then, use `coverage_only`.
