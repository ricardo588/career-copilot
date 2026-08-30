#!/usr/bin/env python3
"""Load, migrate, rank and render private candidate story banks."""

from __future__ import annotations

import hashlib
import json
import re
import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "for", "to", "in", "with", "de", "la", "el", "y", "para", "con",
}
VISIBLE_CONFIDENTIALITY = {"shareable", "candidate_private"}
CV_VISIBLE_CONFIDENTIALITY = {"shareable"}


def _tokens(value: Any) -> set[str]:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    found = re.findall(r"[A-Za-zÀ-ÿ0-9+#.-]+", str(value).casefold())
    return {item for item in found if len(item) > 1 and item not in STOPWORDS}


def _coerce_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"story field {field} must be a JSON array")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"story field {field} must contain non-empty strings")
        result.append(item.strip())
    return result


def _coerce_metric(metric: Any) -> dict[str, Any]:
    if not isinstance(metric, dict):
        raise ValueError("story confirmed_metrics entries must be mappings")
    label = str(metric.get("label", "")).strip()
    value = metric.get("value")
    unit = str(metric.get("unit", "")).strip()
    source = str(metric.get("source", "")).strip()
    if not label or value in {None, ""} or not unit or not source:
        raise ValueError("story confirmed_metrics entries need label, value, unit and source")
    confirmed = metric.get("confirmed_by_user", True)
    if not isinstance(confirmed, bool):
        raise ValueError("story confirmed_metrics confirmed_by_user must be boolean")
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "source": source,
        "confirmed_by_user": confirmed,
    }


def _coerce_source(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise ValueError("story evidence_sources entries must be mappings")
    kind = str(source.get("kind", "")).strip()
    label = str(source.get("label", "")).strip()
    reference = str(source.get("reference", "")).strip()
    if not kind or not label:
        raise ValueError("story evidence_sources entries need kind and label")
    confirmed = source.get("confirmed_by_user", True)
    if not isinstance(confirmed, bool):
        raise ValueError("story evidence_sources confirmed_by_user must be boolean")
    result = {
        "kind": kind,
        "label": label,
        "reference": reference,
        "confirmed_by_user": confirmed,
    }
    if "url" in source:
        result["url"] = str(source.get("url", "")).strip()
    return result


def _coerce_recency(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("story recency must be a mapping")
    recency = {key: value.get(key) for key in value}
    if "last_confirmed" in recency and recency["last_confirmed"] not in {None, ""}:
        try:
            datetime.strptime(str(recency["last_confirmed"]), "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("story recency.last_confirmed must use YYYY-MM-DD") from exc
    return recency


def _validate_story(story: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(story, dict):
        raise ValueError("story bank entries must be mappings")
    story_id = str(story.get("id", "")).strip()
    title = str(story.get("title", "")).strip()
    context = str(story.get("context", "")).strip()
    challenge = str(story.get("challenge", "")).strip()
    actions = _coerce_list(story.get("actions", []), "actions")
    results = story.get("results", {})
    if not isinstance(results, dict):
        raise ValueError("story results must be a mapping")
    facts = _coerce_list(results.get("facts", []), "results.facts")
    unknowns = _coerce_list(results.get("unknowns", []), "results.unknowns")
    confirmed_metrics = [_coerce_metric(item) for item in story.get("confirmed_metrics", []) or []]
    evidence_sources = [_coerce_source(item) for item in story.get("evidence_sources", []) or []]
    tags = _coerce_list(story.get("tags", []), "tags")
    recency = _coerce_recency(story.get("recency", {}))
    confidentiality = str(story.get("confidentiality", "candidate_private")).strip().casefold()
    if confidentiality not in {"shareable", "candidate_private", "restricted", "confidential"}:
        raise ValueError("story confidentiality must be shareable, candidate_private, restricted or confidential")
    provenance = story.get("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError("story provenance must be a mapping")
    user_confirmed = story.get("user_confirmed", True)
    if not isinstance(user_confirmed, bool):
        raise ValueError("story user_confirmed must be boolean")
    if not story_id:
        story_id = stable_story_id(title or "|".join(facts) or "story")
    return {
        "id": story_id,
        "title": title or story_id,
        "context": context,
        "challenge": challenge,
        "actions": actions,
        "results": {"facts": facts, "unknowns": unknowns},
        "confirmed_metrics": confirmed_metrics,
        "evidence_sources": evidence_sources,
        "tags": tags,
        "recency": recency,
        "confidentiality": confidentiality,
        "provenance": provenance,
        "user_confirmed": user_confirmed,
    }


def stable_story_id(seed: str) -> str:
    return "story-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def legacy_story_record(text: str, index: int, source_field: str = "profile.verified_evidence") -> dict[str, Any]:
    text = text.strip()
    seed = f"{source_field}:{index}:{text}"
    return {
        "id": stable_story_id(seed),
        "title": f"Legacy verified evidence {index + 1}",
        "context": "",
        "challenge": "",
        "actions": [],
        "results": {
            "facts": [text],
            "unknowns": [
                "Legacy verified_evidence keeps the original fact but lacks story context, actions and quantified outcomes."
            ],
        },
        "confirmed_metrics": [],
        "evidence_sources": [
            {
                "kind": "legacy_verified_evidence",
                "label": source_field,
                "reference": text,
                "confirmed_by_user": True,
            }
        ],
        "tags": [],
        "recency": {"source": "legacy_profile", "last_confirmed": "", "bucket": "legacy"},
        "confidentiality": "candidate_private",
        "provenance": {
            "source_kind": "legacy_profile",
            "source_field": source_field,
            "migrated_from": "verified_evidence",
        },
        "user_confirmed": True,
    }


def load_story_bank(path: Path | None, legacy_evidence: Iterable[str] | None = None) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    if path is not None and path.is_file():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            story = json.loads(line)
            stories.append(_validate_story(story))
    legacy_items = [item for item in (legacy_evidence or []) if isinstance(item, str) and item.strip()]
    if not stories and legacy_items:
        stories = [legacy_story_record(text, index) for index, text in enumerate(legacy_items)]
    return stories


def save_story_bank(path: Path, stories: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [_validate_story(story) for story in stories]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for story in normalized:
            handle.write(json.dumps(story, ensure_ascii=False) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def story_bank_path(profile_path: Path) -> Path:
    return profile_path.expanduser().resolve().with_name("stories.jsonl")


def _story_visible(story: dict[str, Any], mode: str) -> bool:
    confidentiality = str(story.get("confidentiality", "candidate_private")).casefold()
    if mode == "cv":
        return story.get("user_confirmed", False) and confidentiality in CV_VISIBLE_CONFIDENTIALITY
    return story.get("user_confirmed", False) and confidentiality in VISIBLE_CONFIDENTIALITY


def _recency_bonus(story: dict[str, Any]) -> int:
    recency = story.get("recency", {})
    if not isinstance(recency, dict):
        return 0
    raw = str(recency.get("last_confirmed", "")).strip()
    if not raw:
        return 0
    try:
        confirmed = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return 0
    days = max(0, (date.today() - confirmed).days)
    if days <= 30:
        return 3
    if days <= 180:
        return 2
    if days <= 365:
        return 1
    return 0


def story_score(story: dict[str, Any], terms: set[str]) -> int:
    if not _story_visible(story, "evaluation"):
        return -1
    story_terms = _tokens(story.get("title", ""))
    story_terms |= _tokens(story.get("context", ""))
    story_terms |= _tokens(story.get("challenge", ""))
    story_terms |= _tokens(story.get("actions", []))
    story_terms |= _tokens(story.get("results", {}).get("facts", []))
    story_terms |= _tokens(story.get("results", {}).get("unknowns", []))
    story_terms |= _tokens(story.get("tags", []))
    story_terms |= _tokens([item.get("label", "") for item in story.get("confirmed_metrics", []) if isinstance(item, dict)])
    story_terms |= _tokens([item.get("label", "") for item in story.get("evidence_sources", []) if isinstance(item, dict)])
    return (
        len(terms & story_terms)
        + len(terms & _tokens(story.get("tags", []))) * 2
        + len(story.get("confirmed_metrics", []))
        + _recency_bonus(story)
    )


def select_stories(
    stories: Iterable[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
    vacancy: dict[str, Any] | None = None,
    mode: str = "evaluation",
    limit: int = 3,
) -> list[dict[str, Any]]:
    terms: set[str] = set()
    if isinstance(profile, dict):
        candidate = profile.get("profile", {})
        terms |= _tokens(candidate.get("target_roles", []))
        terms |= _tokens(candidate.get("target_industries", []))
        terms |= _tokens(candidate.get("strengths", []))
        terms |= _tokens(candidate.get("verified_evidence", []))
        direction = candidate.get("career_direction", {})
        if isinstance(direction, dict):
            for field in ("success_criteria", "values", "non_negotiables", "tolerable_tradeoffs", "development_gaps"):
                section = direction.get(field, {})
                if isinstance(section, dict):
                    terms |= _tokens(section.get("facts", []))
                    terms |= _tokens(section.get("interpretations", []))
                    terms |= _tokens(section.get("preferences", []))
    if isinstance(vacancy, dict):
        terms |= _tokens(vacancy.get("company", ""))
        terms |= _tokens(vacancy.get("title", ""))
        terms |= _tokens(vacancy.get("requirements", []))
        terms |= _tokens(vacancy.get("responsibilities", []))
        terms |= _tokens(vacancy.get("location", ""))
    ranked: list[tuple[int, dict[str, Any]]] = []
    for story in stories:
        if not _story_visible(story, mode):
            continue
        score = story_score(story, terms)
        ranked.append((score, story))
    ranked.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    return [item[1] for item in ranked[:limit]]


def _format_confirmed_metrics(story: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for metric in story.get("confirmed_metrics", []):
        if not isinstance(metric, dict):
            continue
        label = str(metric.get("label", "")).strip()
        value = metric.get("value")
        unit = str(metric.get("unit", "")).strip()
        source = str(metric.get("source", "")).strip()
        if not label or value in {None, ""}:
            continue
        metric_text = f"{label}: {value} {unit}".strip()
        if source:
            metric_text += f" ({source})"
        lines.append(metric_text)
    return lines


def render_story_view(story: dict[str, Any], mode: str = "evaluation") -> str:
    if mode not in {"evaluation", "interview", "cv"}:
        raise ValueError("story view mode must be evaluation, interview or cv")
    story = _validate_story(story)
    lines = [f"- Story {story['id']}: {story['title']}"]
    if mode == "evaluation":
        lines.append(f"  - Context: {story['context'] or 'unknown'}")
        lines.append(f"  - Challenge: {story['challenge'] or 'unknown'}")
    elif mode == "interview":
        lines.append(f"  - Situation: {story['context'] or 'unknown'}")
        lines.append(f"  - Task: {story['challenge'] or 'unknown'}")
    else:
        lines.append(f"  - Summary: {story['context'] or story['challenge'] or 'unknown'}")
    action_text = "; ".join(story.get("actions", [])) or "unknown"
    lines.append(f"  - Actions: {action_text}")
    result_facts = story.get("results", {}).get("facts", [])
    if result_facts:
        lines.append(f"  - Results: {'; '.join(result_facts)}")
    else:
        lines.append("  - Results: unknown")
    unknowns = story.get("results", {}).get("unknowns", [])
    if unknowns:
        lines.append(f"  - Explicit unknowns: {'; '.join(unknowns)}")
    metrics = _format_confirmed_metrics(story)
    if metrics:
        lines.append(f"  - Confirmed metrics: {'; '.join(metrics)}")
    evidence = []
    for item in story.get("evidence_sources", []):
        if isinstance(item, dict):
            evidence.append(str(item.get("label", "")).strip() or str(item.get("kind", "")).strip())
    if evidence:
        lines.append(f"  - Evidence sources: {'; '.join(evidence)}")
    lines.append(f"  - Confidentiality: {story.get('confidentiality', 'candidate_private')}")
    return "\n".join(lines)


def serialize_story_views(
    stories: Iterable[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
    vacancy: dict[str, Any] | None = None,
    mode: str = "evaluation",
    limit: int = 3,
) -> dict[str, Any]:
    selected = select_stories(stories, profile=profile, vacancy=vacancy, mode=mode, limit=limit)
    return {
        "mode": mode,
        "story_count": len(selected),
        "story_ids": [story["id"] for story in selected],
        "stories": [
            {
                "id": story["id"],
                "title": story["title"],
                "confidentiality": story.get("confidentiality", "candidate_private"),
                "view": render_story_view(story, mode=mode),
            }
            for story in selected
        ],
    }


def career_direction_view(profile: dict[str, Any], vacancy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Expose candidate-declared tradeoffs without turning them into employer facts or hard filters."""
    candidate = profile.get("profile", {}) if isinstance(profile, dict) else {}
    direction = candidate.get("career_direction", {}) if isinstance(candidate, dict) else {}
    if not isinstance(direction, dict):
        direction = {}
    declared: dict[str, dict[str, list[str]]] = {}
    for field in ("success_criteria", "values", "non_negotiables", "tolerable_tradeoffs", "development_gaps"):
        section = direction.get(field, {})
        if not isinstance(section, dict):
            continue
        normalized = {
            category: _coerce_list(section.get(category, []), f"career_direction.{field}.{category}")
            for category in ("facts", "interpretations", "preferences")
        }
        if any(normalized.values()):
            declared[field] = normalized

    vacancy_signals = vacancy.get("career_signals", {}) if isinstance(vacancy, dict) else {}
    sourced_signals = vacancy_signals if isinstance(vacancy_signals, dict) else {}
    return {
        "candidate_declared": declared,
        "vacancy_sourced_signals": sourced_signals,
        "hard_filters_applied": [],
        "unknown_preferences_ignored": True,
        "interpretation": (
            "Candidate preferences are subjective tradeoff inputs. Employer alignment remains unknown unless "
            "the vacancy supplies sourced career_signals; no preference is an objective company fact."
        ),
    }


def approved_departure_statement(profile: dict[str, Any]) -> str | None:
    candidate = profile.get("profile", {}) if isinstance(profile, dict) else {}
    direction = candidate.get("career_direction", {}) if isinstance(candidate, dict) else {}
    narrative = direction.get("departure_narrative", {}) if isinstance(direction, dict) else {}
    if not isinstance(narrative, dict) or narrative.get("candidate_approved") is not True:
        return None
    facts = _coerce_list(narrative.get("facts", []), "career_direction.departure_narrative.facts")
    return " ".join(facts) if facts else None


def _load_document(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError(f"{path} is not JSON-compatible YAML; finalize onboarding or install PyYAML") from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"expected mapping in {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Private profile JSON/YAML-compatible file")
    parser.add_argument("--stories", help="Private stories.jsonl; defaults beside profile")
    parser.add_argument("--vacancy", help="Optional vacancy JSON")
    parser.add_argument("--mode", choices=("evaluation", "interview", "cv"), default="evaluation")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--migrate-verified-evidence",
        action="store_true",
        help="Create stories.jsonl from legacy verified_evidence only when the bank is empty",
    )
    args = parser.parse_args()
    try:
        profile_path = Path(args.profile).expanduser().resolve()
        profile = _load_document(profile_path)
        vacancy = _load_document(Path(args.vacancy).expanduser().resolve()) if args.vacancy else {}
        bank_path = Path(args.stories).expanduser().resolve() if args.stories else story_bank_path(profile_path)
        legacy = profile.get("profile", {}).get("verified_evidence", [])
        bank_was_empty = not bank_path.exists() or bank_path.stat().st_size == 0
        stories = load_story_bank(bank_path, legacy_evidence=legacy if args.migrate_verified_evidence else None)
        if args.migrate_verified_evidence and bank_was_empty:
            save_story_bank(bank_path, stories)
        result = serialize_story_views(
            stories,
            profile=profile,
            vacancy=vacancy,
            mode=args.mode,
            limit=max(0, args.limit),
        )
        result["career_direction"] = career_direction_view(profile, vacancy)
        result["approved_departure_statement"] = approved_departure_statement(profile)
        result["read_only"] = not args.migrate_verified_evidence
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
