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
    "interviewer", "notes", "vacancy_last_verified", "human_path_last_verified", "evidence_ref",
]
PRE_EVIDENCE_TRACKER_FIELDS = TRACKER_FIELDS[:-1]
LEGACY_TRACKER_FIELDS = PRE_EVIDENCE_TRACKER_FIELDS[:-2] + ["last_verified"]
STOPWORDS = {"and", "or", "the", "a", "an", "of", "for", "to", "in", "with", "de", "la", "el", "y", "para", "con"}
TERMINAL_TRACKER_STATUSES = {"withdrawn", "rejected", "discarded"}
PROTECTED_REQUIREMENT_PATTERNS = [
    re.compile(
        r"\b(?:(?:candidate|applicant|candidato|candidata)(?:'s|\s+de)?\s+age|"
        r"age\s+(?:requirement|must\s+be|between|under|over|\d{1,3})|aged\s+\d{1,3}|"
        r"(?:under|over)\s+\d{1,3}\s+years?\s+old|years?\s+old|"
        r"born\s+(?:after|before|on|in)|birth\s*date|"
        r"graduat(?:ed|ion)\s+(?:after|before|since|in)\s+\d{4}|"
        r"(?:class\s+of|graduation\s+year|year\s+of\s+graduation)\s+\d{4}|"
        r"date\s+of\s+birth|edad\s+(?:requerida|mínima|máxima)|años?\s+de\s+edad|"
        r"nacid[oa]\s+(?:después|antes|el|en)|fecha\s+de\s+nacimiento|"
        r"graduad[oa]\s+(?:después|antes|desde|en)\s+(?:de\s+)?\d{4}|"
        r"graduación\s+(?:después|antes|desde|en)\s+(?:de\s+)?\d{4}|"
        r"(?:año\s+de\s+graduación|generación)\s+\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:(?:male|female|man|woman|nonbinary|transgender|masculino|femenino|hombre|mujer)\s+"
        r"(?:candidate|applicant|person|individual|employee|professional|candidato|candidata|persona)|"
        r"(?:candidate|applicant|candidato|candidata)\s+(?:must\s+be\s+|debe\s+ser\s+)?"
        r"(?:male|female|man|woman|nonbinary|transgender|masculino|femenino|hombre|mujer)|"
        r"(?:candidate|applicant|candidato|candidata)(?:'s|\s+de)?\s+(?:gender|sex|género|sexo)|"
        r"(?:women|men|mujeres|hombres)\s+only|only\s+(?:women|men)|solo\s+(?:mujeres|hombres))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:candidate|applicant|candidato|candidata)(?:'s|\s+de)?\s+"
        r"(?:race|racial|ethnicity|ethnic\s+origin|raza|origen\s+étnico)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:(?:black|white|asian|hispanic|latin[oa]s?|indigenous|african\s+american|native\s+american|"
        r"negr[oa]s?|blanc[oa]s?|asiátic[oa]s?|afrodescendientes?|indígenas?)\s+"
        r"(?:candidates?|applicants?|candidatos?|candidatas?|aspirantes)|"
        r"(?:candidate|applicant|candidates?|applicants?|candidatos?|candidatas?|aspirantes)\s+"
        r"(?:must\s+be\s+|debe(?:n)?\s+ser\s+)?"
        r"(?:black|white|asian|hispanic|latin[oa]s?|indigenous|african\s+american|native\s+american|"
        r"negr[oa]s?|blanc[oa]s?|asiátic[oa]s?|afrodescendientes?|indígenas?))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:candidate|applicant|candidato|candidata)(?:'s|\s+de)?\s+"
        r"(?:religion|religious\s+affiliation|religión|afiliación\s+religiosa)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:(?:candidate|applicant|candidato|candidata)\s+"
        r"(?:must\s+be\s+|debe\s+ser\s+)?(?:catholic|christian|muslim|jewish|hind[uú]|"
        r"católic[oa]|cristian[oa]|musulm[aá]n|judí[oa])|"
        r"(?:catholic|christian|muslim|jewish|hind[uú]|católic[oa]|cristian[oa]|musulm[aá]n|judí[oa])\s+"
        r"(?:candidate|applicant|candidato|candidata))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:(?:disabled|discapacitado|discapacitada)\s+(?:candidate|applicant|candidato|candidata)|"
        r"(?:candidate|applicant|candidato|candidata)(?:'s|\s+de)?\s+"
        r"(?:disability|medical\s+condition|genetic\s+information|discapacidad|condición\s+médica))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:marital\s+status|family\s+status|must\s+be\s+(?:married|unmarried|single)|"
        r"(?:married|unmarried|single)\s+(?:applicants?|candidates?)\s+only|"
        r"estado\s+civil|situación\s+familiar|debe\s+ser\s+(?:casad[oa]|solter[oa])|"
        r"(?:casad[oa]s?|solter[oa]s?)\s+(?:aspirantes|candidatos|candidatas)\s+solamente|"
        r"pregnan\w*|embarazad[oa])\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:submit|provide|include|attach|enviar|proporcionar|incluir|adjuntar)\b.{0,24}"
        r"\b(?:photo|photograph|headshot|foto|fotografía)\b|"
        r"\b(?:recent|current|reciente|actual)\s+(?:photo|photograph|headshot|foto|fotografía)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:(?:western|american|english|local|native|foreign)[ -]sounding\s+"
        r"(?:name|surname|last\s+name)|"
        r"(?:name|surname|last\s+name).{0,30}(?:must|should|needs?\s+to)\s+sound\s+"
        r"(?:western|american|english|local|native|foreign)|"
        r"(?:western|american|english|local|native|foreign)\s+"
        r"(?:name|surname|last\s+name)\s+(?:required|only)|"
        r"(?:nombre|apellido).{0,30}(?:debe|que)\s+sonar\s+"
        r"(?:occidental|estadounidense|americano|local|nativo|extranjero)|"
        r"(?:nombre|apellido)\s+(?:occidental|estadounidense|americano|local|nativo|extranjero)\s+"
        r"(?:requerido|solamente))\b",
        re.IGNORECASE,
    ),
]
PROTECTED_REQUIREMENT_CATEGORIES = {
    "protected_attribute", "protected_proxy", "non_job_relevant",
}
RELATIONSHIP_ROLES = {
    "contact",
    "advocate",
    "connector",
    "recruiter/poster",
    "probable decision maker",
    "confirmed decision maker",
    "reference",
}
DEBRIEF_OUTCOMES = {"positive", "ambiguous", "rejected", "no_response", "failed_interview"}


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


def is_protected_or_non_job_relevant_requirement(value: Any) -> bool:
    """Classify explicit protected criteria; never delete isolated words as a proxy for semantics."""
    if isinstance(value, dict):
        category = str(value.get("category", "job_requirement")).strip().casefold()
        if category in PROTECTED_REQUIREMENT_CATEGORIES:
            return True
        text = str(value.get("text", value.get("requirement", "")))
    else:
        text = str(value)
    return any(pattern.search(text) for pattern in PROTECTED_REQUIREMENT_PATTERNS)


def requirement_text(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("text", value.get("requirement", ""))).strip()
    return str(value).strip()


def candidate_declared_job_constraints(profile: dict[str, Any]) -> dict[str, Any]:
    """Expose declared eligibility/accommodation separately from evidence-based fit scoring."""
    constraints = profile.get("constraints", {})
    if not isinstance(constraints, dict):
        return {"eligibility": {}, "accommodations": [], "used_as_fit_score": False}
    eligibility = constraints.get("job_eligibility")
    if not isinstance(eligibility, dict):
        eligibility = {
            "countries": constraints.get("countries", []),
            "locations": constraints.get("locations", []),
            "work_modes": constraints.get("work_modes", []),
            "employment_types": constraints.get("employment_types", []),
        }
    accommodations = constraints.get("accommodations", [])
    if not isinstance(accommodations, list):
        accommodations = [accommodations] if accommodations else []
    return {
        "eligibility": eligibility,
        "accommodations": accommodations,
        "used_as_fit_score": False,
    }


def normalized_location_parts(value: Any) -> set[str]:
    """Return explicit location components without equating Mexico with New Mexico."""
    parts = re.split(r"[,;/|()]|\s[-–—]\s", str(value).casefold())
    normalized = {
        " ".join(item for item in re.findall(r"[\w+#.-]+", part) if item not in STOPWORDS)
        for part in parts
    }
    return {part for part in normalized if part}


def location_is_eligible(vacancy_location: Any, eligible_values: list[Any]) -> bool:
    vacancy_parts = normalized_location_parts(vacancy_location)
    eligible_parts = {
        part
        for value in eligible_values
        for part in normalized_location_parts(value)
    }
    return not eligible_parts or bool(vacancy_parts & eligible_parts)


def same_company_near_role(row: dict[str, str], vacancy: dict[str, Any]) -> bool:
    row_company = tokens(row.get("company", ""))
    new_company = tokens(vacancy.get("company", ""))
    row_role = tokens(row.get("role", ""))
    new_role = tokens(vacancy.get("title", ""))
    if not row_company or row_company != new_company or not row_role or not new_role:
        return False
    row_external = str(row.get("external_job_id", "")).strip()
    new_external = str(vacancy.get("external_job_id", "")).strip()
    row_canonical = canonicalize_url(str(row.get("canonical_url", "")))
    new_canonical = canonicalize_url(str(vacancy.get("canonical_url", "")))
    if (row_external or row_canonical) and (new_external or new_canonical):
        return False
    row_locations = normalized_location_parts(row.get("location", ""))
    new_locations = normalized_location_parts(vacancy.get("location", ""))
    if bool(row_locations) != bool(new_locations):
        return False
    if row_locations != new_locations:
        return False
    row_posted = str(row.get("date_posted", "")).strip()
    new_posted = str(vacancy.get("date_posted", "")).strip()
    if row_posted and new_posted and row_posted != new_posted:
        return False
    return len(row_role & new_role) / len(row_role | new_role) >= 0.8


def evaluate(profile: dict[str, Any], rules: dict[str, Any], vacancy: dict[str, Any], as_of: date) -> dict[str, Any]:
    reasons: list[str] = []
    risks: list[str] = []
    unknowns: list[str] = []
    raw_requirements_value = vacancy.get("requirements", [])
    raw_requirements = raw_requirements_value if isinstance(raw_requirements_value, list) else [raw_requirements_value]
    nonempty_requirements = [item for item in raw_requirements if requirement_text(item)]
    requirements = [
        requirement_text(item) for item in nonempty_requirements
        if not is_protected_or_non_job_relevant_requirement(item)
    ]
    ignored_requirements = len(nonempty_requirements) - len(requirements)
    declared_job_constraints = candidate_declared_job_constraints(profile)

    if str(vacancy.get("status", "")).casefold() != "open":
        return {
            "recommendation": "Discard", "reasons": [], "risks": ["vacancy is not confirmed open"],
            "unknowns": [], "next_action": "none",
            "ignored_non_job_relevant_requirements": ignored_requirements,
            "candidate_declared_job_constraints": declared_job_constraints,
        }

    posted = vacancy.get("date_posted")
    freshness_days = int(rules.get("search", {}).get("freshness_days", 14))
    if posted:
        age = (as_of - parse_iso_day(str(posted))).days
        if age < 0:
            risks.append("posting date is in the future relative to evaluation date")
        elif age > freshness_days:
            return {
                "recommendation": "Discard", "reasons": [],
                "risks": [f"posting is {age} days old; limit is {freshness_days}"],
                "unknowns": [], "next_action": "none",
                "ignored_non_job_relevant_requirements": ignored_requirements,
                "candidate_declared_job_constraints": declared_job_constraints,
            }
    else:
        unknowns.append("posting date")

    candidate = profile.get("profile", {})
    constraints = profile.get("constraints", {})
    raw_target_roles = candidate.get("target_roles", [])
    target_roles = raw_target_roles if isinstance(raw_target_roles, list) else [raw_target_roles]
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

    job_eligibility = constraints.get("job_eligibility", {})
    work_authorization = job_eligibility.get("work_authorization", []) if isinstance(job_eligibility, dict) else []
    eligible_locations = (
        list(constraints.get("countries", []))
        + list(constraints.get("locations", []))
        + (list(work_authorization) if isinstance(work_authorization, list) else [])
    )
    location_match = location_is_eligible(vacancy.get("location", ""), eligible_locations)
    if location_match:
        reasons.append("location appears eligible")
    else:
        return {
            "recommendation": "Discard", "reasons": reasons,
            "risks": ["location is outside configured eligibility"], "unknowns": unknowns,
            "next_action": "none", "ignored_non_job_relevant_requirements": ignored_requirements,
            "candidate_declared_job_constraints": declared_job_constraints,
        }

    raw_exclusions = list(constraints.get("excluded_roles", [])) + list(rules.get("evaluation", {}).get("hard_exclusions", []))
    job_relevant_exclusions = [
        item for item in raw_exclusions
        if not is_protected_or_non_job_relevant_requirement(item)
    ]
    exclusion_tokens = tokens(job_relevant_exclusions)
    vacancy_all_tokens = tokens([vacancy.get("title", ""), requirements, vacancy.get("responsibilities", [])])
    triggered = sorted(exclusion_tokens & vacancy_all_tokens)
    if triggered:
        return {
            "recommendation": "Discard", "reasons": reasons,
            "risks": ["hard exclusion triggered: " + ", ".join(triggered)],
            "unknowns": unknowns, "next_action": "none",
            "ignored_non_job_relevant_requirements": ignored_requirements,
            "candidate_declared_job_constraints": declared_job_constraints,
        }

    evidence_tokens = tokens(candidate.get("strengths", [])) | tokens(candidate.get("verified_evidence", []))
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
        "ignored_non_job_relevant_requirements": ignored_requirements,
        "candidate_declared_job_constraints": declared_job_constraints,
    }


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _relationship_role(item: dict[str, Any], fallback: str = "contact") -> str:
    role = str(item.get("relationship_role", item.get("path_type", item.get("role", fallback)))).strip().casefold()
    if role in {"recruiter", "recruiter/poster", "poster"}:
        return "recruiter/poster"
    if role in {"decision maker", "decisionmaker", "hiring manager", "hiring_manager"}:
        status = str(item.get("decision_maker_status", item.get("confidence", "probable"))).strip().casefold()
        return "confirmed decision maker" if status == "confirmed" else "probable decision maker"
    if role in RELATIONSHIP_ROLES:
        return role
    return fallback


def _relationship_authorization(item: dict[str, Any]) -> dict[str, bool]:
    raw = item.get("authorization")
    authorization = raw if isinstance(raw, dict) else {}
    contact = authorization.get("contact")
    if contact is None:
        contact = authorization.get("can_contact")
    if contact is None and str(item.get("path_type", "")).casefold() == "trusted_contact" and str(item.get("confidence", "")).casefold() == "confirmed":
        contact = True
    return {
        "contact": bool(contact),
        "reference": bool(authorization.get("reference", authorization.get("can_reference", False))),
        "referral": bool(authorization.get("referral", False)),
        "follow_up": bool(authorization.get("follow_up", False)),
        "introduce": bool(authorization.get("introduce", False)),
    }


def _normalize_relationship_entry(item: dict[str, Any], fallback_role: str, company: str) -> dict[str, Any]:
    source_url = str(item.get("source_url", "")).strip()
    current_company = str(item.get("current_company", "")).strip()
    current_role = str(item.get("current_role", "")).strip()
    role = _relationship_role(item, fallback_role)
    confidence = str(item.get("confidence", "")).strip().casefold()
    company_required = role in {"contact", "advocate", "connector", "probable decision maker", "confirmed decision maker"}
    company_matches = not company_required or not current_company or not company or current_company.casefold() == company
    freshness = str(item.get("freshness", item.get("retrieved_at", ""))).strip()
    authorization = _relationship_authorization(item)
    return {
        "name": str(item.get("name", "unknown")).strip() or "unknown",
        "relationship_role": role,
        "influence": str(item.get("influence", item.get("path_type", ""))).strip(),
        "strength": str(item.get("strength", item.get("relationship_strength", ""))).strip(),
        "current_company": current_company,
        "current_role": current_role,
        "evidence": _as_text_list(item.get("evidence", item.get("source_evidence", []))),
        "freshness": freshness,
        "authorization": authorization,
        "source_url": source_url,
        "decision_maker_status": "confirmed" if role == "confirmed decision maker" and confidence == "confirmed" else "probable" if role in {"probable decision maker", "confirmed decision maker"} else "",
        "company_matches": company_matches,
        "confidence": confidence,
    }


def _gather_relationship_candidates(research: dict[str, Any], company: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    raw_relationships = research.get("relationships", [])
    if isinstance(raw_relationships, list) and raw_relationships:
        for item in raw_relationships:
            if isinstance(item, dict):
                candidates.append(_normalize_relationship_entry(item, _relationship_role(item), company))
        return candidates
    for item in research.get("contacts", []) or []:
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("path_type", "trusted_contact")
            candidates.append(_normalize_relationship_entry(normalized, "contact", company))
    for key, fallback in (("recruiter", "recruiter/poster"), ("hiring_manager", "probable decision maker")):
        item = research.get(key)
        if isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("path_type", fallback)
            candidates.append(_normalize_relationship_entry(normalized, fallback, company))
    return candidates


def _relationship_contact_authorized(item: dict[str, Any]) -> bool:
    return bool(item.get("authorization", {}).get("contact"))


def summarize_human_path(vacancy: dict[str, Any], research: dict[str, Any]) -> dict[str, Any]:
    """Separate sourced human paths from possible or unsupported identities."""
    _validate_human_path_shape(research)
    company = str(vacancy.get("company", "")).strip().casefold()
    candidates = _gather_relationship_candidates(research, company)

    confirmed: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    for item in candidates:
        source_url = str(item.get("source_url", "")).strip()
        if source_url.startswith(("https://", "http://")) and item["confidence"] == "confirmed" and item["company_matches"]:
            confirmed.append(item)
        else:
            unverified.append(item)

    confirmed_types = {item["relationship_role"] for item in confirmed}
    unknowns = []
    if not any(item["relationship_role"] in {"contact", "advocate", "connector"} and item.get("authorization", {}).get("contact") for item in confirmed):
        unknowns.append("trusted company contact")
    if "recruiter/poster" not in confirmed_types:
        unknowns.append("recruiter/poster")
    if not any(item["relationship_role"] in {"probable decision maker", "confirmed decision maker"} for item in confirmed):
        unknowns.append("decision maker")

    order = {"contact": 0, "advocate": 0, "connector": 0, "recruiter/poster": 1, "probable decision maker": 2, "confirmed decision maker": 2, "reference": 3}
    confirmed.sort(key=lambda item: (order.get(item["relationship_role"], 9), item["name"].casefold()))
    status = "confirmed" if confirmed else "unverified" if unverified else "none_found"
    return {
        "status": status,
        "relationships": candidates,
        "confirmed_paths": confirmed,
        "unverified_paths": unverified,
        "unknowns": unknowns,
        "recommended_path": confirmed[0] if confirmed else None,
        "authorization_summary": {
            "contact_authorized": [item["name"] for item in confirmed if _relationship_contact_authorized(item)],
            "contact_denied": [item["name"] for item in confirmed if not _relationship_contact_authorized(item)],
        },
        "guardrail": "Research is read-only; a path is not permission to contact anyone.",
    }


def _not_supplied_human_summary() -> dict[str, Any]:
    return {
        "status": "not_supplied",
        "relationships": [],
        "confirmed_paths": [],
        "unverified_paths": [],
        "unknowns": ["Human Path artifact"],
        "recommended_path": None,
        "authorization_summary": {"contact_authorized": [], "contact_denied": []},
        "guardrail": "No Human Path artifact was supplied; existing tracker evidence was not refreshed.",
    }


def _validate_human_path_shape(research: dict[str, Any]) -> None:
    if not isinstance(research, dict):
        raise ValueError("Human Path artifact must be a mapping")
    relationships = research.get("relationships")
    if relationships is not None:
        if not isinstance(relationships, list) or any(not isinstance(item, dict) for item in relationships):
            raise ValueError("Human Path artifact relationships must be a list of mappings")
    contacts = research.get("contacts", [])
    if not isinstance(contacts, list) or any(not isinstance(item, dict) for item in contacts):
        raise ValueError("Human Path artifact contacts must be a list of mappings")
    for field in ("recruiter", "hiring_manager"):
        value = research.get(field)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"Human Path artifact {field} must be a mapping or null")


def _validated_human_path_retrieved_at(research: dict[str, Any], as_of: date) -> str:
    _validate_human_path_shape(research)
    raw = str(research.get("retrieved_at", "")).strip()
    if not raw:
        raise ValueError("Human Path artifact requires retrieved_at in YYYY-MM-DD format")
    try:
        retrieved_at = parse_iso_day(raw)
    except ValueError as exc:
        raise ValueError("Human Path artifact retrieved_at must use YYYY-MM-DD format") from exc
    if retrieved_at > as_of:
        raise ValueError("Human Path artifact retrieved_at cannot be in the future")
    return retrieved_at.isoformat()


def stable_id(vacancy: dict[str, Any]) -> str:
    external = str(vacancy.get("external_job_id", "")).strip()
    if external:
        return external
    identity = canonicalize_url(str(vacancy.get("canonical_url", ""))) or f"{vacancy.get('company', '')}|{vacancy.get('title', '')}"
    return "job-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


def validate_evidence_ref(value: Optional[str]) -> str:
    """Allow opaque, private evidence references only; no message content belongs in tracker.csv."""
    if value is None:
        return ""
    reference = str(value).strip()
    if not reference:
        return ""
    if not re.fullmatch(r"evidence/gmail-evidence\.jsonl#[0-9a-f-]{36}", reference):
        raise ValueError("evidence_ref must be an opaque Gmail evidence reference")
    return reference


def _tracker_schema_kind(fieldnames: list[str]) -> str:
    current = len(fieldnames) == len(TRACKER_FIELDS) and set(fieldnames) == set(TRACKER_FIELDS)
    if current:
        return "current"
    pre_evidence = len(fieldnames) == len(PRE_EVIDENCE_TRACKER_FIELDS) and set(fieldnames) == set(PRE_EVIDENCE_TRACKER_FIELDS)
    if pre_evidence:
        return "pre_evidence"
    legacy = len(fieldnames) == len(LEGACY_TRACKER_FIELDS) and set(fieldnames) == set(LEGACY_TRACKER_FIELDS)
    if legacy:
        return "legacy"
    missing = [field for field in TRACKER_FIELDS if field not in fieldnames]
    supported = set(TRACKER_FIELDS) | {"last_verified"}
    extra = [field for field in fieldnames if field not in supported]
    detail = []
    if missing:
        detail.append(f"missing fields: {', '.join(missing)}")
    if extra:
        detail.append(f"unsupported extra fields: {', '.join(extra)}")
    raise ValueError(f"unsupported tracker schema; {'; '.join(detail) or 'unrecognized columns'}")


def read_tracker(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [_normalize_tracker_row(row) for row in csv.DictReader(handle)]


def review_tracker(path: Path, as_of: date) -> dict[str, Any]:
    """Derive neutral follow-up signals without changing tracker data or status."""
    if not path.is_file():
        raise FileNotFoundError(f"tracker does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        _tracker_schema_kind(list(reader.fieldnames or []))
        rows = [_normalize_tracker_row(row) for row in reader]
    items: list[dict[str, Any]] = []
    unknown_dates = 0
    invalid_dates = 0
    overdue_count = 0
    for row in rows:
        status = str(row.get("status", "")).strip()
        normalized_status = status.casefold()
        next_action = str(row.get("next_action", "")).strip()
        raw_date = str(row.get("next_action_date", "")).strip()
        due_date: Optional[date] = None
        if not raw_date:
            date_state = "unknown"
            reason = "next_action_date is missing"
            unknown_dates += 1
        else:
            try:
                due_date = parse_iso_day(raw_date)
                date_state = "valid"
                reason = "not overdue"
            except ValueError:
                date_state = "invalid"
                reason = "next_action_date is invalid"
                invalid_dates += 1

        overdue = bool(
            next_action
            and due_date is not None
            and due_date < as_of
            and normalized_status not in TERMINAL_TRACKER_STATUSES
        )
        if overdue:
            reason = "follow_up_overdue"
            overdue_count += 1
        elif due_date is not None and normalized_status in TERMINAL_TRACKER_STATUSES:
            reason = "terminal status"
        elif due_date is not None and not next_action:
            reason = "next_action is missing"

        items.append({
            "id": str(row.get("id", "")),
            "company": str(row.get("company", "")),
            "role": str(row.get("role", "")),
            "status": status,
            "next_action": next_action,
            "next_action_date": raw_date,
            "next_action_date_state": date_state,
            "follow_up_overdue": overdue,
            "reason": reason,
        })

    return {
        "as_of": as_of.isoformat(),
        "read_only": True,
        "summary": {
            "rows": len(items),
            "follow_up_overdue": overdue_count,
            "unknown_dates": unknown_dates,
            "invalid_dates": invalid_dates,
        },
        "items": items,
    }


def _normalize_tracker_row(row: dict[str, Any]) -> dict[str, str]:
    normalized = {field: str(row.get(field, "") or "") for field in TRACKER_FIELDS}
    if not normalized["vacancy_last_verified"]:
        normalized["vacancy_last_verified"] = str(row.get("last_verified", "") or "")
    return normalized


def migrate_tracker_schema(path: Path) -> bool:
    """Persist the legacy single verification clock as vacancy freshness only."""
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    schema_kind = _tracker_schema_kind(list(fieldnames))
    if schema_kind == "current" and fieldnames == TRACKER_FIELDS:
        return False
    atomic_write_tracker(path, rows)
    return True


def atomic_write_tracker(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACKER_FIELDS)
        writer.writeheader()
        writer.writerows(_normalize_tracker_row(row) for row in rows)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def track(
    path: Path,
    vacancy: dict[str, Any],
    evaluation: dict[str, Any],
    as_of: date,
    human_path: Optional[dict[str, Any]] = None,
    interviewer_research: Optional[dict[str, Any]] = None,
    evidence_ref: Optional[str] = None,
) -> dict[str, Any]:
    identity = stable_id(vacancy)
    referenced_evidence = validate_evidence_ref(evidence_ref)
    canonical = canonicalize_url(str(vacancy.get("canonical_url", "")))
    human_summary = _not_supplied_human_summary()
    human_fields: dict[str, str] = {}
    if human_path is not None:
        retrieved_at = _validated_human_path_retrieved_at(human_path, as_of)
        human_summary = summarize_human_path(vacancy, human_path)
        confirmed_paths = human_summary["confirmed_paths"]
        contacts = [
            item["name"] for item in confirmed_paths
            if item["relationship_role"] in {"contact", "advocate", "connector"} and item.get("authorization", {}).get("contact")
        ]
        recruiters = [item["name"] for item in confirmed_paths if item["relationship_role"] == "recruiter/poster"]
        hiring_managers = [
            item["name"] for item in confirmed_paths
            if item["relationship_role"] in {"probable decision maker", "confirmed decision maker"}
        ]
        human_fields = {
            "contact": "; ".join(contacts),
            "human_path_status": human_summary["status"],
            "recruiter": "; ".join(recruiters),
            "hiring_manager": "; ".join(hiring_managers),
            "human_path_last_verified": retrieved_at,
        }
    interviewer_fields: dict[str, str] = {}
    if interviewer_research is not None:
        if not isinstance(interviewer_research, dict):
            raise ValueError("interviewer research artifact must be a mapping")
        interviewers = [
            str(item.get("name", "")).strip()
            for item in interviewer_research.get("interviewers", [])
            if (
                isinstance(item, dict)
                and str(item.get("name", "")).strip()
                and str(item.get("source_url", "")).strip().startswith(("https://", "http://"))
            )
        ]
        interviewer_fields = {"interviewer": "; ".join(interviewers)}
    migrate_tracker_schema(path)
    rows = read_tracker(path)
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
        "vacancy_last_verified": as_of.isoformat(),
    }
    if referenced_evidence:
        evaluation_fields["evidence_ref"] = referenced_evidence
    duplicate = next((
        row for row in rows
        if row.get("id") == identity
        or canonical and row.get("canonical_url") == canonical
        or same_company_near_role(row, vacancy)
    ), None)
    if duplicate:
        previous_status = duplicate.get("status", "identified")
        if previous_status in {"identified", "evaluating", "discarded"}:
            if recommendation == "Discard":
                duplicate["status"] = "discarded"
            elif previous_status == "discarded":
                duplicate["status"] = "identified"
        duplicate.update(evaluation_fields)
        if human_fields:
            duplicate.update(human_fields)
        if interviewer_fields:
            duplicate.update(interviewer_fields)
        atomic_write_tracker(path, rows)
        readback = read_tracker(path)
        verified = next((item for item in readback if item.get("id") == duplicate["id"]), None)
        expected_fields = {**evaluation_fields, **human_fields, **interviewer_fields}
        if not verified or any(verified.get(field, "") != value for field, value in expected_fields.items()):
            raise RuntimeError("tracker update readback verification failed")
        return {"action": "updated_existing", "id": duplicate["id"], "row_count": len(readback), "human_path": human_summary}

    status = "discarded" if recommendation == "Discard" else "identified"
    row = {field: "" for field in TRACKER_FIELDS}
    row.update({
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
        **interviewer_fields,
    })
    rows.append(row)
    atomic_write_tracker(path, rows)
    readback = read_tracker(path)
    verified = next((item for item in readback if item.get("id") == identity), None)
    if (
        len(readback) != len(rows)
        or not verified
        or any(verified.get(field, "") != value for field, value in row.items())
    ):
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
    human_summary = summarize_human_path(vacancy, human_path) if human_path is not None else _not_supplied_human_summary()
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
            contact_state = "contact authorized" if item.get("authorization", {}).get("contact") else "identity confirmed; contact not authorized"
            role = item.get("relationship_role", item.get("path_type", "relationship"))
            company_name = item.get("current_company", "")
            role_name = item.get("current_role", "")
            influence = item.get("influence", "")
            strength = item.get("strength", "")
            freshness = item.get("freshness", "")
            detail_bits = [bit for bit in (
                f"influence {influence}" if influence else "",
                f"strength {strength}" if strength else "",
                f"freshness {freshness}" if freshness else "",
            ) if bit]
            detail = f"; {'; '.join(detail_bits)}" if detail_bits else ""
            company_segment = f" at {company_name}" if company_name else ""
            role_segment = f" — {role_name}" if role_name else ""
            lines.append(
                f"- Confirmed {role}: {item['name']}{role_segment}{company_segment}"
                f" ({item['source_url']}){detail}; {contact_state}"
            )
    elif human_summary["status"] == "not_supplied":
        lines.append("- No Human Path artifact was supplied; current human evidence is unknown.")
    else:
        lines.append("- No sourced contact, recruiter/poster or decision maker was confirmed.")
    lines.extend([
        "- Read-only research is not permission to contact anyone.",
        "- Authorization, relationship role, influence and strength are separate fields.",
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


def relationship_meeting_prep(relationship_artifact: dict[str, Any], meeting: dict[str, Any]) -> str:
    if not isinstance(relationship_artifact, dict):
        raise ValueError("relationship artifact must be a mapping")
    if not isinstance(meeting, dict):
        raise ValueError("meeting prep artifact must be a mapping")
    candidates = _gather_relationship_candidates(relationship_artifact, str(meeting.get("company", "")).strip().casefold())
    lines = [
        f"# Informational meeting prep — {meeting.get('topic', 'relationship conversation')}",
        "",
        "## Objective",
        f"- {str(meeting.get('objective', '')).strip() or 'unknown'}",
        "",
        "## Timebox",
        f"- {str(meeting.get('timebox_minutes', '')).strip() or 'unknown'} minutes",
        "",
        "## Context",
        f"- {str(meeting.get('context', '')).strip() or 'unknown'}",
        "",
        "## Questions",
    ]
    questions = _as_text_list(meeting.get("questions", []))
    if questions:
        lines.extend(f"- {question}" for question in questions)
    else:
        lines.append("- No questions were supplied.")
    lines.extend([
        "",
        "## Relationship model",
    ])
    if candidates:
        for item in candidates:
            auth = item.get("authorization", {})
            auth_bits = [name for name, allowed in (("contact", auth.get("contact")), ("reference", auth.get("reference")), ("referral", auth.get("referral")), ("follow_up", auth.get("follow_up")), ("introduce", auth.get("introduce"))) if allowed]
            lines.append(
                f"- {item['name']} — {item['relationship_role']}; influence {item['influence'] or 'unknown'}; strength {item['strength'] or 'unknown'}; "
                f"{item['current_role'] or 'current role unknown'} at {item['current_company'] or 'current company unknown'}; "
                f"freshness {item['freshness'] or 'unknown'}; authorization {', '.join(auth_bits) if auth_bits else 'none'}"
            )
    else:
        lines.append("- No relationship entries were supplied.")
    lines.extend([
        "",
        "## Draft follow-up",
    ])
    draft_follow_up = str(meeting.get("draft_follow_up", "")).strip()
    if draft_follow_up:
        lines.append(draft_follow_up)
    else:
        lines.append("- No draft follow-up was supplied.")
    lines.extend([
        "",
        "## Recorded outcome",
    ])
    outcome = meeting.get("outcome", {})
    if isinstance(outcome, dict) and outcome:
        for key in sorted(outcome):
            lines.append(f"- {key}: {outcome[key]}")
    elif outcome:
        lines.append(f"- {outcome}")
    else:
        lines.append("- No outcome was supplied; do not infer a commitment, referral or next step.")
    lines.extend([
        "",
        "## Guardrails",
        "- Discovery does not imply permission to contact, refer or connect.",
        "- Outcome commitments and referrals are only confirmed when explicitly approved.",
        "- Keep the follow-up as a draft unless and until explicit approval and external readback exist.",
    ])
    return "\n".join(lines) + "\n"


def interview_debrief(debrief: dict[str, Any]) -> str:
    if not isinstance(debrief, dict):
        raise ValueError("interview debrief artifact must be a mapping")
    outcome = str(debrief.get("outcome", "")).strip().casefold()
    if outcome not in DEBRIEF_OUTCOMES:
        raise ValueError("interview debrief outcome must be one of positive, ambiguous, rejected, no_response or failed_interview")
    sections = debrief.get("sections", {})
    if sections is not None and not isinstance(sections, dict):
        raise ValueError("interview debrief sections must be a mapping")
    lines = [
        f"# Interview debrief — {str(debrief.get('company', 'unknown')).strip() or 'unknown'} / {str(debrief.get('role', 'unknown')).strip() or 'unknown'}",
        "",
        "## Outcome",
        f"- {outcome}",
        f"- Sentiment is recorded for reflection only: {str(debrief.get('sentiment', 'unknown')).strip() or 'unknown'}",
        "- Sentiment never changes tracker state.",
        "",
        "## Observed facts",
    ]
    observed_facts = _as_text_list(debrief.get("observed_facts", []))
    for item in observed_facts:
        lines.append(f"- {item}")
    if not observed_facts:
        lines.append("- No observed facts were supplied.")
    lines.extend([
        "",
        "## Candidate interpretation",
    ])
    for item in _as_text_list(debrief.get("candidate_interpretation", [])):
        lines.append(f"- {item}")
    if lines[-1] == "## Candidate interpretation":
        lines.append("- No interpretation was supplied.")
    lines.extend([
        "",
        "## Learning for future briefs",
    ])
    learning = _as_text_list(debrief.get("learning", []))
    if learning:
        lines.extend(f"- {item}" for item in learning)
    else:
        lines.append("- No learning was supplied.")
    lines.extend([
        "",
        "## Unanswered questions",
    ])
    unanswered = _as_text_list(debrief.get("unanswered_questions", []))
    if unanswered:
        lines.extend(f"- {item}" for item in unanswered)
    else:
        lines.append("- No unanswered questions were supplied.")
    lines.extend([
        "",
        "## Debrief themes",
    ])
    theme_fields = [
        ("Preparation", debrief.get("preparation")),
        ("Logistics", debrief.get("logistics")),
        ("Story quality", debrief.get("story_quality")),
        ("Questions", debrief.get("questions")),
        ("Signals", debrief.get("signals")),
        ("Close", debrief.get("close")),
        ("Improvements", debrief.get("improvements")),
    ]
    for label, value in theme_fields:
        lines.append(f"### {label}")
        items = _as_text_list(value)
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("- Not supplied.")
    lines.extend([
        "",
        "## Authorized follow-up",
    ])
    authorized_follow_up = debrief.get("authorized_follow_up", {})
    if isinstance(authorized_follow_up, dict):
        if authorized_follow_up:
            for key in sorted(authorized_follow_up):
                value = authorized_follow_up[key]
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- None supplied.")
    else:
        lines.append(f"- {authorized_follow_up}")
    lines.extend([
        "",
        "## Follow-up draft",
    ])
    draft = str(debrief.get("follow_up_draft", "")).strip()
    if draft:
        lines.append(draft)
    elif outcome in {"rejected", "failed_interview"}:
        lines.append("- Draft follow-up required but not supplied.")
    else:
        lines.append("- No follow-up draft; keep this debrief read-only.")
    lines.extend([
        "",
        "## Guardrails",
        "- Learning may inform future briefs, but it does not rewrite prior tracker rows or interview history.",
        "- Keep any follow-up as a draft unless explicit approval and external readback exist.",
        "- Rejections and failed interviews may receive a closure draft; every outcome remains read-only until a separately approved external action is executed and verified.",
    ])
    return "\n".join(lines) + "\n"


def write_private_markdown(raw_path: str, markdown: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.exists() and path.is_symlink():
        raise ValueError("private markdown output cannot be a symlink")
    path = path.resolve()
    distribution_root = Path(__file__).resolve().parents[3]
    if path == distribution_root or distribution_root in path.parents:
        raise ValueError("private markdown output must be outside the distribution or installed profile")
    for ancestor in (path.parent, *path.parent.parents):
        if (ancestor / ".git").exists():
            raise ValueError("private markdown output must be outside Git repositories")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(markdown, encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    if path.read_text(encoding="utf-8") != markdown:
        raise RuntimeError("private markdown readback verification failed")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--rules")
    parser.add_argument("--vacancy")
    parser.add_argument("--as-of", help="YYYY-MM-DD; required for evaluation and tracker review")
    parser.add_argument("--tracker")
    parser.add_argument("--review-tracker", help="read-only tracker follow-up review")
    parser.add_argument("--brief")
    parser.add_argument("--human-path", help="JSON/YAML file with sourced contacts, recruiter/poster and hiring-manager evidence")
    parser.add_argument("--interviewer-research", help="JSON/YAML file with sourced interviewer facts and labeled hypotheses")
    parser.add_argument("--evidence-ref", help="Opaque private Gmail evidence reference for this tracker update")
    parser.add_argument("--relationship-prep", help="JSON/YAML file with an informational meeting prep artifact")
    parser.add_argument("--meeting", help="optional separate JSON/YAML meeting objectives, questions and outcome")
    parser.add_argument("--relationship-prep-md", help="write the informational meeting prep markdown to this path")
    parser.add_argument("--interview-debrief", help="JSON/YAML file with a post-interview debrief artifact")
    parser.add_argument("--interview-debrief-md", help="write the interview debrief markdown to this path")
    args = parser.parse_args()
    try:
        special_modes = [name for name, enabled in (("relationship-prep", args.relationship_prep), ("interview-debrief", args.interview_debrief)) if enabled]
        if args.relationship_prep_md and not args.relationship_prep:
            raise ValueError("--relationship-prep-md requires --relationship-prep")
        if args.meeting and not args.relationship_prep:
            raise ValueError("--meeting requires --relationship-prep")
        if args.interview_debrief_md and not args.interview_debrief:
            raise ValueError("--interview-debrief-md requires --interview-debrief")
        if special_modes:
            if len(special_modes) > 1:
                raise ValueError("relationship prep and interview debrief modes are separate")
            evaluation_options = (
                args.profile, args.rules, args.vacancy, args.tracker, args.review_tracker, args.brief,
                args.human_path, args.interviewer_research,
            )
            if any(evaluation_options):
                raise ValueError("relationship or debrief modes cannot be combined with evaluation or tracker options")
            if args.relationship_prep:
                relationship_artifact = load_document(Path(args.relationship_prep))
                meeting = load_document(Path(args.meeting)) if args.meeting else relationship_artifact.get("meeting", {})
                markdown = relationship_meeting_prep(relationship_artifact, meeting)
                payload: dict[str, Any] = {"relationship_prep": relationship_artifact, "markdown": markdown}
                if args.relationship_prep_md:
                    prep_path = write_private_markdown(args.relationship_prep_md, markdown)
                    payload["relationship_prep_markdown"] = str(prep_path)
                print(json.dumps(payload, indent=2, ensure_ascii=False))
                return 0
            debrief_artifact = load_document(Path(args.interview_debrief))
            markdown = interview_debrief(debrief_artifact)
            payload = {"interview_debrief": debrief_artifact, "markdown": markdown}
            if args.interview_debrief_md:
                debrief_path = write_private_markdown(args.interview_debrief_md, markdown)
                payload["interview_debrief_markdown"] = str(debrief_path)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        if not args.as_of:
            raise ValueError("--as-of is required for evaluation and tracker review")
        as_of = parse_iso_day(args.as_of)
        if args.review_tracker:
            evaluation_options = (
                args.profile, args.rules, args.vacancy, args.tracker, args.brief,
                args.human_path, args.interviewer_research,
            )
            if any(evaluation_options):
                raise ValueError("--review-tracker cannot be combined with evaluation or write options")
            print(json.dumps(review_tracker(Path(args.review_tracker), as_of), indent=2, ensure_ascii=False))
            return 0
        missing = [
            option for option, value in (
                ("--profile", args.profile), ("--rules", args.rules), ("--vacancy", args.vacancy),
            ) if not value
        ]
        if missing:
            raise ValueError("evaluation mode requires " + ", ".join(missing))
        profile = load_document(Path(args.profile))
        rules = load_document(Path(args.rules))
        vacancy = load_document(Path(args.vacancy))
        human_path = load_document(Path(args.human_path)) if args.human_path else None
        interviewer_research = load_document(Path(args.interviewer_research)) if args.interviewer_research else None
        result = evaluate(profile, rules, vacancy, as_of)
        if human_path is not None:
            _validated_human_path_retrieved_at(human_path, as_of)
        human_summary = summarize_human_path(vacancy, human_path) if human_path is not None else _not_supplied_human_summary()
        payload: dict[str, Any] = {"evaluation": result, "human_path": human_summary}
        if args.tracker:
            payload["tracker"] = track(
                Path(args.tracker), vacancy, result, as_of, human_path, interviewer_research, args.evidence_ref,
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
