# Versioned portal coverage catalog

## Purpose and boundary

This catalog is the evidence record for Career Copilot's local portal-coverage suggestions. It is **not** a market-performance ranking, a claim of current vacancy availability, a compatibility guarantee, or an instruction to query or use a portal.

The product returns only entries whose declared profile conditions match its local heuristic. The candidate can select, modify, or skip every suggestion. Career Copilot does not open, query, scrape, authenticate to, apply through, or otherwise act on these services.

The canonical source for an individual vacancy remains the relevant company career site or ATS. The `official_company_sites` recommendation is a product safety policy, documented in the [v0.10.0 roadmap](../../../docs/ROADMAP-0.10.0.md#safety-boundaries), rather than a market-coverage claim.

## Catalog version `2026-09-07`

`onboarding.py` exposes this exact version as `catalog_version` and `evidence_checked_on` for every suggested portal. `evidence_url` is the cited source below. The evidence only supports the stated coverage category.

| ID | Declared coverage condition | Evidence-supported scope |
| --- | --- | --- |
| `linkedin` | Baseline professional-network coverage | LinkedIn documents job search and location-aware search.[1] |
| `official_company_sites` | Baseline canonical-source coverage | Product safety policy; see boundary above. |
| `occ_mundial` | Mexico declared | OCC publishes a Mexico job-listing page.[2] |
| `computrabajo` | Mexico declared | Computrabajo's Mexico portal exposes location-based job coverage.[3] |
| `hireline` | Technology role and Mexico declared | Hireline describes a Mexico technology-employment portal.[4] |
| `get_on_board` | Technology role and Latin America or remote declared | Get on Board presents Mexico and remote technology employment coverage.[5] |
| `behance` | Creative role or industry declared | Behance documents Joblist filtering by creative field, location and employment type.[6] |
| `we_work_remotely` | Remote work mode declared | We Work Remotely publishes a remote-jobs listing page.[7] |
| `upwork` | Contract or freelance employment type declared | Upwork publishes a freelance-jobs page.[8] |
| `the_ladders` | United States and executive seniority declared | Ladders publishes senior-level job-search listings.[9] |
| `indeed` | Geography not yet declared | Indeed exposes job search with a location input.[10] |

## Evidence inventory

- LinkedIn’s official help documents job search and location-aware results.[1]
- OCC’s official page is a Mexico job-listing page.[2]
- Computrabajo’s Mexico portal lists location-based employment coverage.[3]
- Hireline’s official Mexico page describes technology employment coverage.[4]
- Get on Board’s official Mexico page presents technology and remote employment coverage.[5]
- Behance’s official help describes filtering its Joblist by creative field, location and employment type.[6]
- We Work Remotely publishes an official remote-jobs listing page.[7]
- Upwork publishes an official freelance-jobs page.[8]
- Ladders publishes senior-level job-search listings.[9]
- Indeed exposes job search with a location input.[10]

## Maintenance rule

Before changing an entry, re-check its official source, update the date-version in `onboarding.py`, update this table and its Spanish counterpart, and add or revise a focused onboarding test. If a source no longer supports the documented scope, narrow or remove the suggestion. Do not infer rankings, volume, conversion, suitability, eligibility, or real-time availability from this catalog.

## Sources

[1] https://linkedin.com/help/linkedin/answer/a511260
[2] https://www.occ.com.mx/empleos/en-ciudad-de-mexico
[3] https://mx.computrabajo.com
[4] https://hireline.io/mx
[5] https://www.getonbrd.com.mx
[6] https://help.behance.net/hc/en-us/articles/360034476413-Guide-Applying-For-Jobs-On-Behance
[7] https://weworkremotely.com/remote-jobs
[8] https://www.upwork.com/freelance-jobs
[9] https://theladders.com/signup/all-jobs
[10] https://www.indeed.com
