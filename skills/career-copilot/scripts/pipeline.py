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
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKER_FIELDS = [
    "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
    "date_posted", "date_discovered", "status", "fit_recommendation", "priority", "next_action",
    "next_action_date", "contact", "human_path_status", "recruiter", "hiring_manager",
    "interviewer", "notes", "last_verified",
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


def summarize_human_path(vacancy: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    """Separate sourced human paths from possible or unsupported identities."""
    company = str(vacancy.get("company", "")).strip().casefold()
    candidates: list[dict[str, Any]] = []
    for item in research.get("contacts", []) or []:
        if isinstance(item, dict):
            candidates.append(dict(item))
    for key, path_type in (("recruiter", "recruiter_or_poster"), ("hiring_manager", "hiring_manager")):
        item = research.get(key)
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("path_type", path_type)
            candidates.append(normalized)

    confirmed: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    for item in candidates:
        name = str(item.get("name", "")).strip()
        source_url = str(item.get("source_url", "")).strip()
        confidence = str(item.get("confidence", "")).casefold()
        path_type = str(item.get("path_type", "possible_contact"))
        current_company = str(item.get("current_company", "")).strip().casefold()
        company_required = path_type in {"trusted_contact", "possible_contact", "hiring_manager"}
        company_matches = not company_required or bool(company and current_company == company)
        normalized = {
            "name": name or "unknown",
            "path_type": path_type,
            "current_role": str(item.get("current_role", "")).strip(),
            "current_company": str(item.get("current_company", "")).strip(),
            "relationship": str(item.get("relationship", "")).strip(),
            "source_url": source_url,
        }
        if name and source_url.startswith(("https://", "http://")) and confidence == "confirmed" and company_matches:
            confirmed.append(normalized)
        else:
            unverified.append(normalized)

    confirmed_types = {item["path_type"] for item in confirmed}
    unknowns = []
    if "trusted_contact" not in confirmed_types:
        unknowns.append("trusted company contact")
    if "recruiter_or_poster" not in confirmed_types:
        unknowns.append("recruiter/poster")
    if "hiring_manager" not in confirmed_types:
        unknowns.append("hiring manager")

    order = {"trusted_contact": 0, "recruiter_or_poster": 1, "hiring_manager": 2}
    confirmed.sort(key=lambda item: order.get(item["path_type"], 9))
    status = "confirmed" if confirmed else "unverified" if unverified else "none_found"
    return {
        "status": status,
        "confirmed_paths": confirmed,
        "unverified_paths": unverified,
        "unknowns": unknowns,
        "recommended_path": confirmed[0] if confirmed else None,
        "guardrail": "Research is read-only; a path is not permission to contact anyone.",
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


def track(
    path: Path,
    vacancy: dict[str, Any],
    evaluation: dict[str, Any],
    as_of: date,
    human_path: Optional[dict[str, Any]] = None,
    interviewer_research: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    rows = read_tracker(path)
    identity = stable_id(vacancy)
    canonical = canonicalize_url(str(vacancy.get("canonical_url", "")))
    human_summary = summarize_human_path(vacancy, human_path or {})
    confirmed_paths = human_summary["confirmed_paths"]
    contacts = [item["name"] for item in confirmed_paths if item["path_type"] == "trusted_contact"]
    recruiters = [item["name"] for item in confirmed_paths if item["path_type"] == "recruiter_or_poster"]
    hiring_managers = [item["name"] for item in confirmed_paths if item["path_type"] == "hiring_manager"]
    interviewers = [
        str(item.get("name", "")).strip()
        for item in (interviewer_research or {}).get("interviewers", [])
        if (
            isinstance(item, dict)
            and str(item.get("name", "")).strip()
            and str(item.get("source_url", "")).strip().startswith(("https://", "http://"))
        )
    ]
    human_fields = {
        "contact": "; ".join(contacts),
        "human_path_status": human_summary["status"],
        "recruiter": "; ".join(recruiters),
        "hiring_manager": "; ".join(hiring_managers),
        "interviewer": "; ".join(interviewers),
    }
    recommendation = str(evaluation.get("recommendation", "Low"))
    priority = {"High": "high", "Medium": "medium", "Low": "low", "Discard": "discard"}.get(recommendation, "low")
    evaluation_fields = {
        "company": str(vacancy.get("company", "")),
        "role": str(vacancy.get("title", "")),
        "location": str(vacancy.get("location", "")),
        "source": str(vacancy.get("source", "")),
        "canonical_url": canonical,
        "external_job_id": str(vacancy.get("external_job_id", "")),
        "date_posted": str(vacancy.get("date_posted", "")),
        "fit_recommendation": recommendation,
        "priority": priority,
        "next_action": str(evaluation.get("next_action", "")),
        "notes": "; ".join(evaluation.get("risks", [])),
        "last_verified": as_of.isoformat(),
    }
    duplicate = next((row for row in rows if row.get("id") == identity or canonical and row.get("canonical_url") == canonical), None)
    if duplicate:
        previous_status = duplicate.get("status", "identified")
        if previous_status in {"identified", "evaluating", "discarded"}:
            if recommendation == "Discard":
                duplicate["status"] = "discarded"
            elif previous_status == "discarded":
                duplicate["status"] = "identified"
        duplicate.update(evaluation_fields)
        duplicate.update(human_fields)
        atomic_write_tracker(path, rows)
        readback = read_tracker(path)
        verified = next((item for item in readback if item.get("id") == duplicate["id"]), None)
        if not verified or any(verified.get(field, "") != value for field, value in evaluation_fields.items()):
            raise RuntimeError("tracker update readback verification failed")
        return {"action": "updated_existing", "id": duplicate["id"], "row_count": len(readback), "human_path": human_summary}

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
        **evaluation_fields,
        "next_action_date": "",
        **human_fields,
    }
    rows.append(row)
    atomic_write_tracker(path, rows)
    readback = read_tracker(path)
    verified = any(item.get("id") == identity and item.get("company") == row["company"] for item in readback)
    if not verified:
        raise RuntimeError("tracker readback verification failed")
    return {"action": "added", "id": identity, "row_count": len(readback), "human_path": human_summary}


def interview_brief(
    profile: dict[str, Any],
    vacancy: dict[str, Any],
    evaluation: dict[str, Any],
    human_path: Optional[dict[str, Any]] = None,
    interviewer_research: Optional[dict[str, Any]] = None,
) -> str:
    evidence = profile.get("profile", {}).get("verified_evidence", [])
    human_summary = summarize_human_path(vacancy, human_path or {})
    lines = [
        f"# Interview brief — {vacancy.get('company', '')} / {vacancy.get('title', '')}",
        "",
        "## Confirmed role context",
        f"- Location: {vacancy.get('location', 'unknown')}",
        f"- Seniority: {vacancy.get('seniority', 'unknown')}",
        f"- Fit recommendation: {evaluation.get('recommendation', 'unknown')}",
        "",
        "## Human Path",
        f"- Status: {human_summary['status']}",
    ]
    if human_summary["confirmed_paths"]:
        for item in human_summary["confirmed_paths"]:
            lines.append(
                f"- Confirmed {item['path_type']}: {item['name']} — {item['current_role']} "
                f"({item['source_url']})"
            )
    else:
        lines.append("- No sourced contact, recruiter/poster or hiring manager was confirmed.")
    lines.extend([
        "- Read-only research is not permission to contact anyone.",
        "",
        "## Interviewer intelligence",
    ])
    interviewers = (interviewer_research or {}).get("interviewers", [])
    if not interviewers:
        lines.append("- Interviewer identity has not been confirmed.")
    for interviewer in interviewers:
        if not isinstance(interviewer, dict):
            continue
        name = str(interviewer.get("name", "unknown")).strip() or "unknown"
        role = str(interviewer.get("current_role", "unknown")).strip() or "unknown"
        source_url = str(interviewer.get("source_url", "")).strip()
        if not source_url.startswith(("https://", "http://")):
            lines.append(f"- Unverified interviewer: {name} — {role}; no direct source supplied.")
            continue
        lines.append(f"- {name} — {role} ({source_url})")
        for fact in interviewer.get("confirmed_facts", []) or []:
            lines.append(f"  - Confirmed fact: {fact}")
        for hypothesis in interviewer.get("hypotheses", []) or []:
            lines.append(f"  - Interview hypothesis: {hypothesis}")
    lines.extend([
        "- Do not infer personality, preferences or decision power from a title or credential.",
        "",
        "## Candidate evidence to use",
    ])
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
    parser.add_argument("--human-path", help="JSON/YAML file with sourced contacts, recruiter/poster and hiring-manager evidence")
    parser.add_argument("--interviewer-research", help="JSON/YAML file with sourced interviewer facts and labeled hypotheses")
    args = parser.parse_args()
    try:
        profile = load_document(Path(args.profile))
        rules = load_document(Path(args.rules))
        vacancy = load_document(Path(args.vacancy))
        human_path = load_document(Path(args.human_path)) if args.human_path else {}
        interviewer_research = load_document(Path(args.interviewer_research)) if args.interviewer_research else {}
        as_of = parse_iso_day(args.as_of)
        result = evaluate(profile, rules, vacancy, as_of)
        human_summary = summarize_human_path(vacancy, human_path)
        payload: dict[str, Any] = {"evaluation": result, "human_path": human_summary}
        if args.tracker:
            payload["tracker"] = track(
                Path(args.tracker), vacancy, result, as_of, human_path, interviewer_research,
            )
        if args.brief:
            brief_path = Path(args.brief)
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            brief_path.write_text(
                interview_brief(profile, vacancy, result, human_path, interviewer_research),
                encoding="utf-8",
            )
            os.chmod(brief_path, 0o600)
            payload["brief"] = str(brief_path)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
