# Compensation policy

Compensation is private candidate configuration. It is optional and disabled by
default. It informs evaluation; it does not submit, withdraw, reject, or change
a tracker record by itself.

## Private profile shape

```yaml
compensation:
  enabled: true
  policies:
    - employment_type: payroll
      currency: MXN
      periodicity: monthly
      target_base: 150000
      floor_base: 120000
    - employment_type: contractor
      currency: USD
      periodicity: hourly
      target_base: 70
      floor_base: 60
  below_floor_terminal_status: withdrawn
  below_floor_reason: budget_below_floor
```

A policy applies only when `employment_type`, `currency`, and `periodicity`
all match the disclosed offer exactly (case-insensitively for text). Currency
conversion and inferred periodicity are deliberately unsupported.

## Vacancy input

The deterministic evaluator reads an optional private `compensation` mapping
from the supplied vacancy JSON:

```json
{
  "employment_type": "payroll",
  "currency": "MXN",
  "periodicity": "monthly",
  "base": 130000,
  "total": 180000,
  "candidate_approved_exception": false
}
```

`base` is the only comparison value. `total` is returned for context but never
substitutes for undisclosed base compensation.

## Result states

- `not_configured`: compensation is disabled or there is no policy.
- `unknown`: no disclosed base, incomplete basis, or no unique matching policy.
- `compatible`: disclosed base meets the configured floor.
- `below_floor`: disclosed base is below floor; evaluation emits a proposed
  terminal action only. It does not mutate any tracker.
- `exception_required`: disclosed base is below floor and the input explicitly
  records `candidate_approved_exception: true`; review remains manual.

A `below_floor` proposal keeps candidate withdrawal distinct from an employer
rejection. Any future tracker write must separately satisfy tracker permission,
an explicit reviewed plan, and readback verification.

## Upgrading a legacy profile

Profiles created before v0.7 may contain only `currency`, `target`, and `floor`.
Onboarding preserves those amounts in one `unspecified` policy, but deliberately
does **not** guess employment type or periodicity. Evaluating such a policy
returns `unknown` with `migration_required: true` until it is replaced with one
or more explicit policies. This avoids comparing a monthly payroll floor to an
hourly or daily offer merely because the currency matches.

## Privacy and retention

Keep policy values, offer figures, and exception decisions in the private
workspace. Do not commit them to this distribution, include them in public
briefs, or use them as evidence about an employer.
