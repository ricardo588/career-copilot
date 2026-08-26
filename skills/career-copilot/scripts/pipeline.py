#!/usr/bin/env python3
"""Deterministic local evaluation, tracking and interview-brief engine."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKER_FIELDS = [
    "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
    "date_posted", "date_discovered", "status", "priority", "next_action",
    "next_action_date", "contact", "notes", "last_verified",
]
STOPWORDS = {"and", "or", "the", "a", "an", "of", "for", "to", "in", "with", "de", "la", "el", "y", "para", "con"}


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError(f"{path} is not JSON-compatible YAML; finalize onboarding or install PyYAML") from exc
        loaded = yaml.safe_load(text)
        if not isinstance(loaded, dict):
            raise ValueError(f"expected mapping in {path}")
        return loaded


def tokens(value: Any) -> set[str]:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    found = re.findall(r"[A-Za-zÀ-ÿ0-9+#.-]+", str(value).casefold())
    return {item for item in found if len(item) > 1 and item not in STOPWORDS}


def canonicalize_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.casefold().startswith(("utm_", "trk", "tracking"))]
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/"), urlencode(query), ""))


def parse_iso_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def evaluate(profile: dict[str, Any], rules: dict[str, Any], vacancy: dict[str, Any], as_of: date) -> dict[str, Any]:
    reasons: list[str] = []
    risks: list[str] = []
    unknowns: list[str] = []

    if str(vacancy.get("status", "")).casefold() != "open":
        return {"recommendation": "Discard", "reasons": [], "risks": ["vacancy is not confirmed open"], "unknowns": [], "next_action": "none"}

    posted = vacancy.get("date_posted")
    freshness_days = int(rules.get("search", {}).get("freshness_days", 14))
    if posted:
        age = (as_of - parse_iso_day(str(posted))).days
        if age < 0:
            risks.append("posting date is in the future relative to evaluation date")
        elif age > freshness_days:
            return {"recommendation": "Discard", "reasons": [], "risks": [f"posting is {age} days old; limit is {freshness_days}"], "unknowns": [], "next_action": "none"}
    else:
        unknowns.append("posting date")

    candidate = profile.get("profile", {})
    constraints = profile.get("constraints", {})
    target_roles = candidate.get("target_roles", [])
    target_seniority = tokens(candidate.get("target_seniority", []))
    title_tokens = tokens(vacancy.get("title", ""))
    target_role_tokens = tokens(target_roles)
    role_overlap = title_tokens & target_role_tokens
    role_match = len(role_overlap) >= 2 or any(str(role).casefold() in str(vacancy.get("title", "")).casefold() for role in target_roles)
    if role_match:
        reasons.append("title aligns with a target role")
    else:
        risks.append("title has weak alignment with target roles")

    vacancy_seniority = tokens(vacancy.get("seniority", ""))
    seniority_match = bool(target_seniority & vacancy_seniority) if vacancy_seniority else False
    if seniority_match:
        reasons.append("seniority aligns")
    elif vacancy_seniority:
        risks.append("seniority does not match configured targets")
    else:
        unknowns.append("seniority")

    eligible_locations = tokens(constraints.get("countries", [])) | tokens(constraints.get("locations", []))
    vacancy_location = tokens(vacancy.get("location", ""))
    location_match = not eligible_locations or bool(eligible_locations & vacancy_location)
    if location_match:
        reasons.append("location appears eligible")
    else:
        return {"recommendation": "Discard", "reasons": reasons, "risks": ["location is outside configured eligibility"], "unknowns": unknowns, "next_action": "none"}

    exclusion_tokens = tokens(constraints.get("excluded_roles", [])) | tokens(rules.get("evaluation", {}).get("hard_exclusions", []))
    vacancy_all_tokens = tokens([vacancy.get("title", ""), vacancy.get("requirements", []), vacancy.get("responsibilities", [])])
    triggered = sorted(exclusion_tokens & vacancy_all_tokens)
    if triggered:
        return {"recommendation": "Discard", "reasons": reasons, "risks": ["hard exclusion triggered: " + ", ".join(triggered)], "unknowns": unknowns, "next_action": "none"}

    evidence_tokens = tokens(candidate.get("strengths", [])) | tokens(candidate.get("verified_evidence", []))
    requirements = [str(item) for item in vacancy.get("requirements", [])]
    matched_requirements = []
    for item in requirements:
        requirement_tokens = tokens(item)
        minimum_overlap = 1 if len(requirement_tokens) <= 1 else 2
        if len(requirement_tokens & evidence_tokens) >= minimum_overlap:
            matched_requirements.append(item)
    if matched_requirements:
        reasons.append(f"verified evidence supports {len(matched_requirements)} requirement(s)")
    if requirements and len(matched_requirements) < len(requirements):
        unknowns.append(f"evidence for {len(requirements) - len(matched_requirements)} requirement(s)")

    ratio = len(matched_requirements) / len(requirements) if requirements else 0.0
    if role_match and seniority_match and ratio >= 0.5:
        recommendation = "High"
        next_action = "prepare application materials"
    elif role_match and (seniority_match or ratio > 0):
        recommendation = "Medium"
        next_action = "verify gaps before applying"
    else:
        recommendation = "Low"
        next_action = "review only if strategically useful"

    return {
        "recommendation": recommendation,
        "reasons": reasons,
        "risks": risks,
        "unknowns": unknowns,
        "matched_requirements": matched_requirements,
        "next_action": next_action,
    }


def stable_id(vacancy: dict[str, Any]) -> str:
    external = str(vacancy.get("external_job_id", "")).strip()
    if external:
        return external
    identity = canonicalize_url(str(vacancy.get("canonical_url", ""))) or f"{vacancy.get('company', '')}|{vacancy.get('title', '')}"
    return "job-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


def read_tracker(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def atomic_write_tracker(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACKER_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in TRACKER_FIELDS} for row in rows)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def track(path: Path, vacancy: dict[str, Any], evaluation: dict[str, Any], as_of: date) -> dict[str, Any]:
    rows = read_tracker(path)
    identity = stable_id(vacancy)
    canonical = canonicalize_url(str(vacancy.get("canonical_url", "")))
    duplicate = next((row for row in rows if row.get("id") == identity or canonical and row.get("canonical_url") == canonical), None)
    if duplicate:
        duplicate["last_verified"] = as_of.isoformat()
        atomic_write_tracker(path, rows)
        return {"action": "updated_existing", "id": duplicate["id"], "row_count": len(rows)}

    recommendation = evaluation.get("recommendation", "Low")
    priority = {"High": "high", "Medium": "medium", "Low": "low", "Discard": "discard"}.get(str(recommendation), "low")
    status = "discarded" if recommendation == "Discard" else "identified"
    row = {
        "id": identity,
        "company": str(vacancy.get("company", "")),
        "role": str(vacancy.get("title", "")),
        "location": str(vacancy.get("location", "")),
        "source": str(vacancy.get("source", "")),
        "canonical_url": canonical,
        "external_job_id": str(vacancy.get("external_job_id", "")),
        "date_posted": str(vacancy.get("date_posted", "")),
        "date_discovered": as_of.isoformat(),
        "status": status,
        "priority": priority,
        "next_action": str(evaluation.get("next_action", "")),
        "next_action_date": "",
        "contact": "",
        "notes": "; ".join(evaluation.get("risks", [])),
        "last_verified": as_of.isoformat(),
    }
    rows.append(row)
    atomic_write_tracker(path, rows)
    readback = read_tracker(path)
    verified = any(item.get("id") == identity and item.get("company") == row["company"] for item in readback)
    if not verified:
        raise RuntimeError("tracker readback verification failed")
    return {"action": "added", "id": identity, "row_count": len(readback)}


def interview_brief(profile: dict[str, Any], vacancy: dict[str, Any], evaluation: dict[str, Any]) -> str:
    evidence = profile.get("profile", {}).get("verified_evidence", [])
    lines = [
        f"# Interview brief — {vacancy.get('company', '')} / {vacancy.get('title', '')}",
        "",
        "## Confirmed role context",
        f"- Location: {vacancy.get('location', 'unknown')}",
        f"- Seniority: {vacancy.get('seniority', 'unknown')}",
        f"- Fit recommendation: {evaluation.get('recommendation', 'unknown')}",
        "",
        "## Candidate evidence to use",
    ]
    lines.extend(f"- {item}" for item in evidence)
    lines.extend([
        "",
        "## Gaps or unknowns",
        *[f"- {item}" for item in evaluation.get("unknowns", [])],
        "",
        "## Questions to prepare",
        "- Which outcome would define success in the first six months?",
        "- Which stakeholders and teams are most critical to this role?",
        "- Which delivery risks are currently hardest to manage?",
        "",
        "## Guardrail",
        "Use only verified candidate evidence; do not invent metrics or experience.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--vacancy", required=True)
    parser.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    parser.add_argument("--tracker")
    parser.add_argument("--brief")
    args = parser.parse_args()
    try:
        profile = load_document(Path(args.profile))
        rules = load_document(Path(args.rules))
        vacancy = load_document(Path(args.vacancy))
        as_of = parse_iso_day(args.as_of)
        result = evaluate(profile, rules, vacancy, as_of)
        payload: dict[str, Any] = {"evaluation": result}
        if args.tracker:
            payload["tracker"] = track(Path(args.tracker), vacancy, result, as_of)
        if args.brief:
            brief_path = Path(args.brief)
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            brief_path.write_text(interview_brief(profile, vacancy, result), encoding="utf-8")
            os.chmod(brief_path, 0o600)
            payload["brief"] = str(brief_path)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
