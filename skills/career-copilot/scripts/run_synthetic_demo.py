#!/usr/bin/env python3
"""Run the bundled synthetic profile-to-interview Career Copilot demo."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from adapters import gmail_reconciliation_proposal, gmail_triage
from pipeline import (
    atomic_write_tracker,
    evaluate,
    interview_brief,
    load_document,
    offer_negotiation_brief,
    read_tracker,
    review_tracker,
    summarize_human_path,
    track,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="Directory for generated demo artifacts")
    parser.add_argument("--as-of", default="2026-08-26", help="Fixed YYYY-MM-DD evaluation date")
    args = parser.parse_args()

    fixtures = Path(__file__).resolve().parents[1] / "examples" / "synthetic"
    output = Path(args.output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    profile = load_document(fixtures / "profile.json")
    rules = load_document(fixtures / "rules.json")
    vacancy = load_document(fixtures / "vacancy.json")
    human_path = load_document(fixtures / "human-path.json")
    interviewer_research = load_document(fixtures / "interviewer-research.json")
    offer_negotiation = load_document(fixtures / "offer-negotiation.json")
    as_of = date.fromisoformat(args.as_of)

    evaluation = evaluate(profile, rules, vacancy, as_of)
    tracker_path = output / "tracker.csv"
    human_summary = summarize_human_path(vacancy, human_path)
    tracker_result = track(tracker_path, vacancy, evaluation, as_of, human_path, interviewer_research)
    tracker_rows = read_tracker(tracker_path)
    tracker_rows[0]["status"] = "applied"
    tracker_rows[0]["next_action"] = "send neutral follow-up"
    tracker_rows[0]["next_action_date"] = (as_of - timedelta(days=1)).isoformat()
    atomic_write_tracker(tracker_path, tracker_rows)
    tracker_before_review = tracker_path.read_bytes()
    tracker_review = review_tracker(tracker_path, as_of)
    if tracker_path.read_bytes() != tracker_before_review:
        raise RuntimeError("tracker review mutated the synthetic tracker")
    tracker_review_path = output / "tracker-review.json"
    tracker_review_path.write_text(
        json.dumps(tracker_review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    brief_path = output / "interview-brief.md"
    brief_path.write_text(
        interview_brief(profile, vacancy, evaluation, human_path, interviewer_research),
        encoding="utf-8",
    )
    offer_path = output / "offer-negotiation.md"
    offer_path.write_text(
        offer_negotiation_brief(offer_negotiation),
        encoding="utf-8",
    )

    gmail_message = {"id": "synthetic-gmail-message", "threadId": "synthetic-gmail-thread", "labelIds": ["INBOX", "UNREAD"]}
    gmail_triage_result = gmail_triage(
        lambda _command: dict(gmail_message), "synthetic-gmail-message", workspace=output / "gmail-private",
        account_ref="synthetic-account", supported_fact="Synthetic recruiter screen is scheduled",
        excerpt="Synthetic invitation confirms a recruiter screen.",
    )
    gmail_headers = ["No", "Company", "Role", "Location", "Canonical URL", "External Job ID", "Status", "Priority", "Notes"]
    gmail_fields = {
        "business_id": "No", "company": "Company", "role": "Role", "location": "Location",
        "canonical_url": "Canonical URL", "external_job_id": "External Job ID", "status": "Status",
        "priority": "Priority", "notes": "Notes",
    }
    gmail_record = {
        "business_id": "1", "company": "Synthetic Co", "role": "Program Director", "location": "Remote",
        "canonical_url": "https://jobs.example.test/synthetic/1", "external_job_id": "SYN-1",
        "status": "identified", "priority": "medium", "notes": "Synthetic Gmail evidence reviewed.",
    }
    gmail_snapshot = {"headers": gmail_headers, "rows": [{
        "physical_row": 5,
        "values": dict(zip(gmail_headers, [
            "1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "",
        ])),
    }]}
    gmail_reconciliation = gmail_reconciliation_proposal(
        gmail_snapshot, gmail_fields, gmail_record, gmail_triage_result["proposal"]["evidence_ref"],
    )
    gmail_triage_path = output / "gmail-triage.json"
    gmail_triage_path.write_text(json.dumps({
        "triage": gmail_triage_result,
        "reconciliation": gmail_reconciliation,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    result = {
        "scenario": "synthetic_profile_to_interview",
        "external_actions": 0,
        "evaluation": evaluation,
        "human_path": human_summary,
        "tracker": tracker_result,
        "tracker_rows": len(read_tracker(tracker_path)),
        "tracker_review": tracker_review,
        "tracker_review_artifact": str(tracker_review_path),
        "interview_brief": str(brief_path),
        "offer_negotiation": str(offer_path),
        "gmail_triage": gmail_triage_result,
        "gmail_reconciliation": gmail_reconciliation,
        "gmail_triage_artifact": str(gmail_triage_path),
    }
    result_path = output / "demo-result.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
