# Private onboarding

## Goal

Create a candidate-owned workspace without collecting secrets in chat or storing personal information in the distributable skill.

## Procedure

1. Resolve the configured workspace path.
2. If the workspace does not exist, ask permission to create it and run the bundled bootstrap script.
3. Ask the candidate to complete or provide only the fields needed for the current task:
   - target roles and seniority;
   - locations, work modes and employment types;
   - verified strengths, achievements and evidence;
   - gaps or roles to avoid;
   - source priorities and freshness rules;
   - compensation constraints, if the candidate wants them considered;
   - document paths;
   - external-action permissions.
4. Store personal details only in the private workspace.
5. Read the files back and summarize missing fields without repeating sensitive values unnecessarily.

## Minimum viable onboarding

The skill can evaluate a vacancy once target roles, seniority, locations, core evidence and external-action policy are known. Compensation and integrations are optional.

## Guardrails

- Do not ask for passwords, API keys, government IDs or payment information.
- Do not infer achievements or compensation.
- Blank fields are unknown, not permission to guess.
- Use synthetic data in demonstrations and tests.
