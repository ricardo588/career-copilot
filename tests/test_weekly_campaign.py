from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills/career-copilot/scripts/weekly_campaign.py"
SPEC = importlib.util.spec_from_file_location("weekly_campaign_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
WEEKLY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WEEKLY)


class WeeklyCampaignTests(unittest.TestCase):
    def setUp(self):
        self.week_start = date(2026, 9, 7)
        self.context = {
            "focus": ["Prioritize sourced Director opportunities"],
            "drafts": [{"id": "draft-1", "kind": "follow_up", "opportunity_id": "job-1", "status": "draft"}],
            "authorized_actions": [{"id": "auth-1", "kind": "research", "scope": "target-company signals", "authorized_at": "2026-09-07"}],
            "attempts": [{"id": "try-1", "action_id": "auth-1", "attempted_at": "2026-09-08", "result": "blocked"}],
            "outcomes": [{"id": "out-1", "subject": "job-1", "state": "verified", "evidence_ref": "evidence/gmail-evidence.jsonl#abc"}],
            "learning": [{"observation": "Interviews clustered in cloud delivery", "interpretation": "candidate reflection", "next_experiment": "review case preparation"}],
        }

    def tracker(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "tracker.csv"
        fields = [
            "id", "company", "role", "location", "source", "canonical_url", "external_job_id", "date_posted",
            "date_discovered", "status", "fit_recommendation", "priority", "next_action", "next_action_date",
            "contact", "human_path_status", "recruiter", "hiring_manager", "interviewer", "notes",
            "vacancy_last_verified", "human_path_last_verified", "evidence_ref",
        ]
        rows = [
            {"id": "job-1", "company": "Synthetic Co", "role": "Program Director", "status": "applied", "next_action": "draft follow-up", "next_action_date": "2026-09-05"},
            {"id": "job-2", "company": "Waiting Co", "role": "Delivery Director", "status": "recruiter_screen", "next_action": "", "next_action_date": ""},
            {"id": "job-3", "company": "Closed Co", "role": "Director", "status": "rejected", "next_action": "follow up", "next_action_date": "2026-09-01"},
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])
        return path

    def targets(self, directory: Path) -> Path:
        path = directory / "targets.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "companies": [
                {"id": "company-1", "status": "active", "next_research_action": "verify strategy signal", "company_last_verified": "2026-08-01", "human_path_last_verified": "2026-09-06"},
                {"id": "company-2", "status": "archived", "next_research_action": "ignore", "company_last_verified": "2026-09-06", "human_path_last_verified": ""},
            ],
        }), encoding="utf-8")
        return path

    def test_plan_separates_activity_output_outcome_learning_and_does_not_impose_quotas(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = WEEKLY.build_weekly_plan(self.tracker(Path(tmp)), self.targets(Path(tmp)), self.context, self.week_start)
        self.assertEqual(plan["week_end"], "2026-09-13")
        self.assertEqual(plan["focus"], self.context["focus"])
        self.assertEqual(plan["activity"]["authorized_actions"][0]["id"], "auth-1")
        self.assertEqual(plan["outputs"]["drafts"][0]["status"], "draft")
        self.assertEqual(plan["outcomes"][0]["state"], "verified")
        self.assertEqual(plan["learning"][0]["interpretation"], "candidate reflection")
        self.assertNotIn("quota", plan["activity"])
        self.assertNotIn("quota", plan["actionable_items"])

    def test_plan_derives_overdue_follow_up_without_mutating_tracker_or_creating_waiting_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = self.tracker(Path(tmp))
            before = tracker.read_bytes()
            plan = WEEKLY.build_weekly_plan(tracker, self.targets(Path(tmp)), {}, self.week_start)
            self.assertEqual(before, tracker.read_bytes())
        self.assertEqual([item["id"] for item in plan["actionable_items"]["overdue_follow_ups"]], ["job-1"])
        self.assertEqual([item["id"] for item in plan["passive_waiting"]], ["job-2"])
        self.assertEqual(plan["passive_waiting"][0]["recommended_action"], "none")
        self.assertEqual(plan["mutation"], "none")

    def test_target_research_is_included_only_when_explicit_and_staleness_uses_separate_clocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = WEEKLY.build_weekly_plan(self.tracker(Path(tmp)), self.targets(Path(tmp)), {}, self.week_start)
        target_items = plan["actionable_items"]["target_research"]
        self.assertEqual(target_items, [{"id": "company-1", "next_research_action": "verify strategy signal"}])
        self.assertEqual(plan["research_gaps"]["company_evidence_stale"], ["company-1"])
        self.assertEqual(plan["research_gaps"]["human_path_evidence_stale"], [])

    def test_rejects_unverified_outcomes_and_actions_that_claim_send_or_status_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker, targets = self.tracker(Path(tmp)), self.targets(Path(tmp))
            with self.assertRaisesRegex(ValueError, "verified outcome"):
                WEEKLY.build_weekly_plan(tracker, targets, {"outcomes": [{"id": "x", "state": "verified"}]}, self.week_start)
            with self.assertRaisesRegex(ValueError, "must not send or mutate"):
                WEEKLY.build_weekly_plan(tracker, targets, {"authorized_actions": [{"id": "x", "kind": "send"}]}, self.week_start)

    def test_private_report_permissions_and_low_and_high_volume_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            low = WEEKLY.build_weekly_plan(self.tracker(root), self.targets(root), {}, self.week_start)
            self.assertEqual(low["volume_context"], "low_volume")
            high_tracker = self.tracker(root / "high")
            with high_tracker.open("a", encoding="utf-8") as handle:
                for number in range(12):
                    handle.write(f"job-x{number},Example,Director,,,,,,,identified,High,high,,, ,,,,,,,,\n")
            high = WEEKLY.build_weekly_plan(high_tracker, self.targets(root), {}, self.week_start)
            self.assertEqual(high["volume_context"], "higher_volume")
            output = root / "private" / "weekly.json"
            WEEKLY.write_private_report(output, low)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.parent.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
