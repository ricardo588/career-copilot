import csv
import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "pipeline.py"
DEMO = ROOT / "skills" / "career-copilot" / "scripts" / "run_synthetic_demo.py"
FIXTURES = ROOT / "skills" / "career-copilot" / "examples" / "synthetic"
SPEC = importlib.util.spec_from_file_location("career_pipeline", SCRIPT)
PIPELINE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PIPELINE)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.profile = PIPELINE.load_document(FIXTURES / "profile.json")
        self.rules = PIPELINE.load_document(FIXTURES / "rules.json")
        self.vacancy = PIPELINE.load_document(FIXTURES / "vacancy.json")
        self.as_of = date(2026, 8, 26)

    def test_high_fit_uses_only_meaningful_requirement_overlap(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        self.assertEqual(result["recommendation"], "High")
        self.assertEqual(len(result["matched_requirements"]), 3)
        self.assertNotIn("Vendor commercial management", result["matched_requirements"])

    def test_gmail_evidence_reference_is_opaque_and_preserved_on_refresh(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        reference = "evidence/gmail-evidence.jsonl#123e4567-e89b-12d3-a456-426614174000"
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, result, self.as_of, evidence_ref=reference)
            self.assertEqual(PIPELINE.read_tracker(tracker)[0]["evidence_ref"], reference)
            PIPELINE.track(tracker, self.vacancy, result, self.as_of)
            self.assertEqual(PIPELINE.read_tracker(tracker)[0]["evidence_ref"], reference)
            with self.assertRaisesRegex(ValueError, "opaque Gmail"):
                PIPELINE.track(tracker, self.vacancy, result, self.as_of, evidence_ref="message-id: private-content")

    def test_tracker_deduplicates_and_verifies(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Synthetic Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Transformation Leader",
                "source_url": "https://example.test/people/synthetic-contact",
                "confidence": "confirmed",
            }],
            "recruiter": None,
            "hiring_manager": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            interviewer_research = {
                "interviewers": [
                    {"name": "Verified Interviewer", "source_url": "https://example.test/interviewer"},
                    {"name": "Unsourced Interviewer"},
                ]
            }
            first = PIPELINE.track(
                tracker, self.vacancy, result, self.as_of, human_path, interviewer_research,
            )
            second = PIPELINE.track(
                tracker, self.vacancy, result, self.as_of, human_path, interviewer_research,
            )
            self.assertEqual(first["action"], "added")
            self.assertEqual(second["action"], "updated_existing")
            with tracker.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["canonical_url"], "https://jobs.example.test/acme/TPD-001")
            self.assertEqual(rows[0]["human_path_status"], "confirmed")
            self.assertEqual(rows[0]["contact"], "Synthetic Contact")
            self.assertEqual(rows[0]["interviewer"], "Verified Interviewer")
            self.assertEqual(rows[0]["fit_recommendation"], "High")
            self.assertEqual(rows[0]["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(rows[0]["human_path_last_verified"], "2026-08-25")

    def test_duplicate_refreshes_fit_fields_without_regressing_process_status(self):
        initial = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, initial, self.as_of)
            rows = PIPELINE.read_tracker(tracker)
            rows[0]["status"] = "interview"
            rows[0]["next_action"] = "obsolete action"
            PIPELINE.atomic_write_tracker(tracker, rows)

            stale = dict(self.vacancy)
            stale["date_posted"] = "2026-07-01"
            reevaluation = PIPELINE.evaluate(self.profile, self.rules, stale, self.as_of)
            update = PIPELINE.track(tracker, stale, reevaluation, self.as_of)
            refreshed = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(update["action"], "updated_existing")
            self.assertEqual(refreshed["fit_recommendation"], "Discard")
            self.assertEqual(refreshed["priority"], "discard")
            self.assertEqual(refreshed["next_action"], reevaluation["next_action"])
            self.assertEqual(refreshed["date_posted"], "2026-07-01")
            self.assertEqual(refreshed["status"], "interview")
            self.assertEqual(refreshed["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(refreshed["human_path_last_verified"], "")
            self.assertEqual(refreshed["human_path_status"], "")

    def test_vacancy_only_refresh_preserves_human_path_and_interviewer(self):
        initial = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Current Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Director",
                "source_url": "https://example.test/current-contact",
                "confidence": "confirmed",
            }],
            "recruiter": {
                "name": "Current Recruiter",
                "source_url": "https://example.test/current-recruiter",
                "confidence": "confirmed",
            },
            "hiring_manager": {
                "name": "Current Manager",
                "current_company": "Acme Cloud Services",
                "source_url": "https://example.test/current-manager",
                "confidence": "confirmed",
            },
        }
        interviewer = {
            "interviewers": [{
                "name": "Current Interviewer",
                "source_url": "https://example.test/current-interviewer",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, initial, self.as_of, human_path, interviewer)

            later = date(2026, 8, 28)
            refreshed_vacancy = dict(self.vacancy)
            refreshed_vacancy["location"] = "Mexico City, Mexico"
            reevaluation = PIPELINE.evaluate(self.profile, self.rules, refreshed_vacancy, later)
            PIPELINE.track(tracker, refreshed_vacancy, reevaluation, later)
            row = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(row["contact"], "Current Contact")
            self.assertEqual(row["recruiter"], "Current Recruiter")
            self.assertEqual(row["hiring_manager"], "Current Manager")
            self.assertEqual(row["interviewer"], "Current Interviewer")
            self.assertEqual(row["human_path_status"], "confirmed")
            self.assertEqual(row["human_path_last_verified"], "2026-08-25")
            self.assertEqual(row["vacancy_last_verified"], "2026-08-28")

    def test_explicit_none_found_human_path_refresh_uses_artifact_date(self):
        initial = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        initial_human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Former Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Director",
                "source_url": "https://example.test/former-contact",
                "confidence": "confirmed",
            }],
        }
        interviewer = {
            "interviewers": [{
                "name": "Preserved Interviewer",
                "source_url": "https://example.test/preserved-interviewer",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, initial, self.as_of, initial_human_path, interviewer)

            none_found = {"retrieved_at": "2026-08-27", "contacts": []}
            PIPELINE.track(tracker, self.vacancy, initial, date(2026, 8, 28), none_found)
            row = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(row["contact"], "")
            self.assertEqual(row["recruiter"], "")
            self.assertEqual(row["hiring_manager"], "")
            self.assertEqual(row["human_path_status"], "none_found")
            self.assertEqual(row["human_path_last_verified"], "2026-08-27")
            self.assertEqual(row["interviewer"], "Preserved Interviewer")

    def test_explicit_human_path_requires_valid_retrieved_at(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with self.assertRaisesRegex(ValueError, "retrieved_at"):
                PIPELINE.track(tracker, self.vacancy, result, self.as_of, {"contacts": []})
            with self.assertRaisesRegex(ValueError, "future"):
                PIPELINE.track(
                    tracker, self.vacancy, result, self.as_of,
                    {"retrieved_at": "2026-08-27", "contacts": []},
                )

    def test_invalid_human_path_shape_cannot_erase_existing_evidence(self):
        result = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        initial_human_path = {
            "retrieved_at": "2026-08-25",
            "contacts": [{
                "name": "Preserved Contact",
                "path_type": "trusted_contact",
                "current_company": "Acme Cloud Services",
                "current_role": "Director",
                "source_url": "https://example.test/preserved-contact",
                "confidence": "confirmed",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.track(tracker, self.vacancy, result, self.as_of, initial_human_path)
            before = tracker.read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "contacts"):
                PIPELINE.track(
                    tracker,
                    self.vacancy,
                    result,
                    date(2026, 8, 28),
                    {"retrieved_at": "2026-08-27", "contacts": "malformed"},
                )

            self.assertEqual(tracker.read_text(encoding="utf-8"), before)
            self.assertEqual(PIPELINE.read_tracker(tracker)[0]["contact"], "Preserved Contact")

    def test_human_path_summary_rejects_malformed_shape(self):
        with self.assertRaisesRegex(ValueError, "contacts"):
            PIPELINE.summarize_human_path(self.vacancy, {"contacts": "malformed"})

    def test_legacy_tracker_migration_splits_clock_conservatively(self):
        legacy_fields = [
            "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
            "date_posted", "date_discovered", "status", "fit_recommendation", "priority", "next_action",
            "next_action_date", "contact", "human_path_status", "recruiter", "hiring_manager",
            "interviewer", "notes", "last_verified",
        ]
        legacy_rows = [{
            "id": "legacy-1",
            "company": "Legacy Co",
            "role": "Legacy Role",
            "status": "interview",
            "next_action": "prepare panel",
            "contact": "Known Person",
            "human_path_status": "confirmed",
            "last_verified": "2026-08-20",
        }, {
            "id": "legacy-2",
            "company": "Second Co",
            "role": "Second Role",
            "status": "applied",
            "next_action": "wait for response",
            "last_verified": "2026-08-21",
        }]
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=legacy_fields)
                writer.writeheader()
                writer.writerows(legacy_rows)

            self.assertTrue(PIPELINE.migrate_tracker_schema(tracker))
            rows = PIPELINE.read_tracker(tracker)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["id"], "legacy-1")
            self.assertEqual(rows[0]["status"], "interview")
            self.assertEqual(rows[0]["next_action"], "prepare panel")
            self.assertEqual(rows[0]["vacancy_last_verified"], "2026-08-20")
            self.assertEqual(rows[0]["human_path_last_verified"], "")
            self.assertEqual(rows[0]["contact"], "Known Person")
            self.assertEqual(rows[1]["id"], "legacy-2")
            self.assertNotIn("last_verified", rows[0])
            with tracker.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                persisted = list(reader)
                self.assertEqual(persisted[0]["id"], "legacy-1")
                self.assertNotIn("last_verified", reader.fieldnames or [])

    def test_company_and_near_identical_role_dedupe_preserves_stable_id(self):
        first_vacancy = dict(self.vacancy)
        first_vacancy["external_job_id"] = ""
        first_vacancy["canonical_url"] = ""
        evaluation = PIPELINE.evaluate(self.profile, self.rules, first_vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            first = PIPELINE.track(tracker, first_vacancy, evaluation, self.as_of)

            refreshed = dict(self.vacancy)
            refreshed["external_job_id"] = "NEW-SOURCE-ID"
            refreshed["canonical_url"] = "https://jobs.example.test/acme/new-source"
            refreshed["title"] = "Director, Technical Program"
            second_evaluation = PIPELINE.evaluate(self.profile, self.rules, refreshed, self.as_of)
            second = PIPELINE.track(tracker, refreshed, second_evaluation, self.as_of)

            rows = PIPELINE.read_tracker(tracker)
            self.assertEqual(second["action"], "updated_existing")
            self.assertEqual(second["id"], first["id"])
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], first["id"])
            self.assertEqual(rows[0]["canonical_url"], refreshed["canonical_url"])

    def test_fuzzy_dedupe_does_not_merge_distinct_location_or_conflicting_identity(self):
        evaluation = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            first = PIPELINE.track(tracker, self.vacancy, evaluation, self.as_of)

            distinct = dict(self.vacancy)
            distinct["external_job_id"] = "DEMO-TPD-002"
            distinct["canonical_url"] = "https://jobs.example.test/acme/TPD-002"
            distinct["location"] = "Toronto, Canada"
            second_evaluation = PIPELINE.evaluate(self.profile, self.rules, distinct, self.as_of)
            second = PIPELINE.track(tracker, distinct, second_evaluation, self.as_of)

            self.assertEqual(first["action"], "added")
            self.assertEqual(second["action"], "added")
            self.assertEqual(len(PIPELINE.read_tracker(tracker)), 2)

    def test_fuzzy_dedupe_does_not_fill_missing_location_by_merging_another_opportunity(self):
        first_vacancy = dict(self.vacancy)
        first_vacancy["external_job_id"] = ""
        first_vacancy["canonical_url"] = ""
        first_vacancy["location"] = ""
        first_evaluation = PIPELINE.evaluate(self.profile, self.rules, first_vacancy, self.as_of)

        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            first = PIPELINE.track(tracker, first_vacancy, first_evaluation, self.as_of)

            distinct = dict(self.vacancy)
            distinct["external_job_id"] = "DEMO-TPD-TORONTO"
            distinct["canonical_url"] = "https://jobs.example.test/acme/TPD-TORONTO"
            distinct["location"] = "Toronto, Canada"
            second_evaluation = PIPELINE.evaluate(self.profile, self.rules, distinct, self.as_of)
            second = PIPELINE.track(tracker, distinct, second_evaluation, self.as_of)

            rows = PIPELINE.read_tracker(tracker)
            self.assertEqual(first["action"], "added")
            self.assertEqual(second["action"], "added")
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["location"], "")
            self.assertEqual(rows[1]["location"], "Toronto, Canada")

    def test_track_automatically_migrates_legacy_tracker_without_erasing_human_evidence(self):
        legacy_fields = [
            "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
            "date_posted", "date_discovered", "status", "fit_recommendation", "priority", "next_action",
            "next_action_date", "contact", "human_path_status", "recruiter", "hiring_manager",
            "interviewer", "notes", "last_verified",
        ]
        legacy_row = {
            "id": "legacy-stable-id",
            "company": self.vacancy["company"],
            "role": self.vacancy["title"],
            "canonical_url": PIPELINE.canonicalize_url(self.vacancy["canonical_url"]),
            "status": "interview",
            "next_action": "prepare panel",
            "contact": "Known Contact",
            "human_path_status": "confirmed",
            "recruiter": "Known Recruiter",
            "hiring_manager": "Known Manager",
            "interviewer": "Known Interviewer",
            "last_verified": "2026-08-20",
        }
        evaluation = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=legacy_fields)
                writer.writeheader()
                writer.writerow(legacy_row)

            result = PIPELINE.track(tracker, self.vacancy, evaluation, self.as_of)
            row = PIPELINE.read_tracker(tracker)[0]

            self.assertEqual(result["action"], "updated_existing")
            self.assertEqual(result["id"], "legacy-stable-id")
            self.assertEqual(len(PIPELINE.read_tracker(tracker)), 1)
            self.assertEqual(row["status"], "interview")
            self.assertEqual(row["contact"], "Known Contact")
            self.assertEqual(row["human_path_status"], "confirmed")
            self.assertEqual(row["recruiter"], "Known Recruiter")
            self.assertEqual(row["hiring_manager"], "Known Manager")
            self.assertEqual(row["interviewer"], "Known Interviewer")
            self.assertEqual(row["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(row["human_path_last_verified"], "")

    def test_reordered_current_schema_is_normalized_without_losing_rows(self):
        reordered = list(reversed(PIPELINE.TRACKER_FIELDS))
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=reordered)
                writer.writeheader()
                writer.writerow({"id": "current-1", "company": "Current Co", "status": "applied"})

            self.assertTrue(PIPELINE.migrate_tracker_schema(tracker))
            with tracker.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(reader.fieldnames, PIPELINE.TRACKER_FIELDS)
            self.assertEqual(rows[0]["id"], "current-1")
            self.assertEqual(rows[0]["status"], "applied")

    def test_schema_with_extra_columns_is_rejected_without_data_loss(self):
        fields = PIPELINE.TRACKER_FIELDS + ["custom_private_note"]
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            with tracker.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow({"id": "custom-1", "custom_private_note": "preserve me"})
            before = tracker.read_text(encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unsupported extra fields"):
                PIPELINE.migrate_tracker_schema(tracker)
            self.assertEqual(tracker.read_text(encoding="utf-8"), before)

    def test_human_path_requires_sources_and_separates_unknowns(self):
        research = {
            "contacts": [
                {
                    "name": "Confirmed Person",
                    "path_type": "trusted_contact",
                    "current_company": "Acme Cloud Services",
                    "current_role": "Director",
                    "source_url": "https://example.test/confirmed",
                    "confidence": "confirmed",
                },
                {
                    "name": "Unsourced Person",
                    "path_type": "possible_contact",
                    "current_company": "Acme Cloud Services",
                    "current_role": "Manager",
                    "confidence": "possible",
                },
            ],
            "recruiter": None,
            "hiring_manager": None,
        }
        result = PIPELINE.summarize_human_path(self.vacancy, research)
        self.assertEqual(result["status"], "confirmed")
        self.assertEqual(len(result["confirmed_paths"]), 1)
        self.assertEqual(len(result["unverified_paths"]), 1)
        self.assertIn("recruiter/poster", result["unknowns"])

    def test_interviewer_research_is_rendered_as_facts_and_hypotheses(self):
        evaluation = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        interviewer = {
            "interviewers": [{
                "name": "Alex Example",
                "current_role": "VP Transformation",
                "source_url": "https://example.test/alex",
                "confirmed_facts": ["Leads enterprise transformation"],
                "hypotheses": ["May focus on value realization"],
            }]
        }
        brief = PIPELINE.interview_brief(self.profile, self.vacancy, evaluation, interviewer_research=interviewer)
        self.assertIn("## Interviewer intelligence", brief)
        self.assertIn("Confirmed fact: Leads enterprise transformation", brief)
        self.assertIn("Interview hypothesis: May focus on value realization", brief)
        self.assertIn("https://example.test/alex", brief)

    def test_requirement_matrix_is_rendered_as_cited_brief_context(self):
        evaluation = PIPELINE.evaluate(self.profile, self.rules, self.vacancy, self.as_of)
        matrix = {
            "requirements": [{
                "requirement": "Cloud delivery", "assessment": "direct",
                "direct_evidence": [{"ref": "profile.verified_evidence[0]"}],
            }, {
                "requirement": "Payment rails", "assessment": "transferable", "direct_evidence": [],
            }]
        }
        brief = PIPELINE.interview_brief(self.profile, self.vacancy, evaluation, requirement_matrix=matrix)
        self.assertIn("## Requirement evidence matrix", brief)
        self.assertIn("Cloud delivery: direct; evidence refs: profile.verified_evidence[0]", brief)
        self.assertIn("Transferability is analysis, not direct experience", brief)

    def test_offer_negotiation_brief_renders_provenance_comparison_and_drafts(self):
        offer = {
            "company": "Acme Cloud Services",
            "role": "Transformation Program Director",
            "record": {
                "source": {"value": "https://example.test/offers/acme", "status": "confirmed"},
                "date_received": {"value": "2026-08-26", "status": "confirmed"},
                "currency": {"value": "USD", "status": "confirmed"},
                "geography": {"value": "Remote in Canada", "status": "confirmed"},
                "employment_type": {"value": "full-time", "status": "confirmed"},
            },
            "package": {
                "base": {"offer": "180000", "candidate_priority": "195000 floor", "status": "needs review"},
                "variable": {"offer": "15% bonus", "candidate_priority": "20% bonus", "status": "confirmed"},
                "equity": {"offer": "600 RSUs", "candidate_priority": "1-year refresh grant", "status": "unknown"},
                "benefits": {"offer": "standard health and pension", "candidate_priority": "expanded parental leave", "status": "confirmed"},
                "location": {"offer": "Remote in Canada", "candidate_priority": "Hybrid optional", "status": "confirmed"},
                "flexibility": {"offer": "occasional travel", "candidate_priority": "no more than 10% travel", "status": "confirmed"},
                "scope": {"offer": "enterprise transformation portfolio", "candidate_priority": "clear decision rights", "status": "confirmed"},
                "risk": {"offer": "annual incentive is discretionary", "candidate_priority": "base protection if targets slip", "status": "confirmed"},
                "candidate_tradeoffs": {"offer": "larger scope", "candidate_priority": "accept smaller bonus for stronger scope", "status": "confirmed"},
            },
            "market_research": [
                {
                    "summary": "Synthetic salary guide suggests director-level packages are influenced by travel demands.",
                    "source_url": "https://example.test/research/salary-guide",
                    "source_date": "2026-08-20",
                    "retrieved_at": "2026-08-26",
                }
            ],
            "candidate_priorities": ["Protect base pay", "Preserve flexibility"],
            "questions": ["Can you confirm the bonus plan and vesting schedule?"],
            "drafts": [
                {"kind": "acknowledgement", "text": "Thank you for the offer and the clear outline of the role."},
                {"kind": "clarification", "text": "Can you confirm whether the bonus target is prorated in year one?"},
                {"kind": "counterproposal", "text": "Could we move the base salary to 195000 and add a signing bonus?"},
                {"kind": "accept", "text": "Draft only: I am ready to accept once the final terms are confirmed."},
                {"kind": "decline", "text": "Draft only: I will decline if the final package cannot meet the stated floor."},
            ],
        }
        brief = PIPELINE.offer_negotiation_brief(offer)
        self.assertIn("# Offer negotiation — Acme Cloud Services / Transformation Program Director", brief)
        self.assertIn("## Offer record", brief)
        self.assertIn("source: confirmed — https://example.test/offers/acme", brief)
        self.assertIn("date_received: confirmed — 2026-08-26", brief)
        self.assertIn("## Total package comparison", brief)
        self.assertIn("Base", brief)
        self.assertIn("Candidate tradeoffs", brief)
        self.assertIn("## Market research", brief)
        self.assertIn("source date: 2026-08-20", brief)
        self.assertIn("## Candidate priorities and questions", brief)
        self.assertIn("Protect base pay", brief)
        self.assertIn("## Negotiation drafts", brief)
        self.assertIn("Acknowledgement", brief)
        self.assertIn("Counterproposal", brief)
        self.assertIn("Accept", brief)
        self.assertIn("## Guardrails", brief)
        self.assertIn("not legal, tax or financial advice", brief)

    def test_offer_negotiation_rejects_unverified_external_actions(self):
        offer = {
            "company": "Acme Cloud Services",
            "role": "Transformation Program Director",
            "requested_action": "send",
            "authorization": {"exact": False, "readback_verified": False},
        }
        with self.assertRaisesRegex(ValueError, "exact authorization and verified readback"):
            PIPELINE.offer_negotiation_brief(offer)

    def test_stale_or_ineligible_vacancy_is_discarded(self):
        stale = dict(self.vacancy)
        stale["date_posted"] = "2026-07-01"
        self.assertEqual(PIPELINE.evaluate(self.profile, self.rules, stale, self.as_of)["recommendation"], "Discard")
        elsewhere = dict(self.vacancy)
        elsewhere["location"] = "Example City"
        self.assertEqual(PIPELINE.evaluate(self.profile, self.rules, elsewhere, self.as_of)["recommendation"], "Discard")

    def test_protected_attributes_and_proxies_are_excluded_from_fit_scoring(self):
        profile = json.loads(json.dumps(self.profile))
        profile["profile"]["age"] = 55
        profile["profile"]["gender"] = "female"
        profile["profile"]["date_of_birth"] = "1971-01-01"
        profile["profile"]["verified_evidence"] = [
            "Led cloud transformation programs",
            "Female executive born in 1971",
        ]
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = [
            "Cloud transformation",
            "Female candidate",
            "Must be under 60 years old",
            "Born after 1970",
            "Recent headshot photograph",
        ]

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["matched_requirements"], ["Cloud transformation"])
        self.assertEqual(result["ignored_non_job_relevant_requirements"], 4)
        self.assertFalse(any("age" in item.casefold() or "gender" in item.casefold() for item in result["unknowns"]))

    def test_candidate_declared_location_eligibility_remains_job_relevant(self):
        profile = json.loads(json.dumps(self.profile))
        profile["profile"]["age"] = 55
        profile["constraints"]["locations"] = ["Mexico"]
        vacancy = dict(self.vacancy)
        vacancy["location"] = "Example City"

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["recommendation"], "Discard")
        self.assertIn("location is outside configured eligibility", result["risks"])

    def test_structured_work_authorization_is_a_hard_constraint_without_substring_match(self):
        profile = json.loads(json.dumps(self.profile))
        profile["constraints"]["countries"] = []
        profile["constraints"]["locations"] = []
        profile["constraints"]["job_eligibility"] = {"work_authorization": ["Mexico"]}
        vacancy = dict(self.vacancy)
        vacancy["location"] = "New Mexico (Remote)"

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["recommendation"], "Discard")
        self.assertIn("location is outside configured eligibility", result["risks"])

    def test_plain_text_women_only_requirement_is_excluded(self):
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = ["Women only", "Only women", "Program governance"]

        result = PIPELINE.evaluate(self.profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["ignored_non_job_relevant_requirements"], 2)
        self.assertEqual(result["matched_requirements"], ["Program governance"])

    def test_plain_text_date_religion_and_family_proxies_are_excluded(self):
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = [
            "Graduated after 2015",
            "Class of 2015",
            "Graduation year 2015",
            "Candidate must be Catholic",
            "Single applicants only",
            "Graduado después de 2018",
            "Año de graduación 2018",
            "Candidato católico",
            "Black candidates only",
            "Candidatos latinos solamente",
            "Western-sounding name required",
            "El nombre debe sonar estadounidense",
            "Program governance",
        ]

        result = PIPELINE.evaluate(self.profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["ignored_non_job_relevant_requirements"], 12)
        self.assertEqual(result["matched_requirements"], ["Program governance"])

    def test_candidate_target_role_is_not_filtered_as_an_employer_requirement(self):
        profile = json.loads(json.dumps(self.profile))
        profile["profile"]["target_roles"] = ["Women Only Shelter Director"]
        vacancy = dict(self.vacancy)
        vacancy["title"] = "Women Only Shelter Director"

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertIn("title aligns with a target role", result["reasons"])

    def test_job_relevant_language_is_not_removed_by_protected_attribute_guardrail(self):
        profile = json.loads(json.dumps(self.profile))
        profile["profile"]["verified_evidence"] = [
            "Owned a single point of accountability",
            "Led disability accessibility programs",
            "Managed good faith negotiations",
            "Delivered medical platform transformation",
            "Directed aged care modernization",
        ]
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = [
            "Single point of accountability",
            "Disability accessibility programs",
            "Good faith negotiations",
            "Medical platform transformation",
            "Aged care modernization",
        ]

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["ignored_non_job_relevant_requirements"], 0)
        self.assertEqual(result["matched_requirements"], vacancy["requirements"])

    def test_structured_protected_requirements_are_ignored_without_keyword_deletion(self):
        profile = json.loads(json.dumps(self.profile))
        profile["profile"]["verified_evidence"] = ["Led women in technology programs"]
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = [
            {"category": "protected_attribute", "text": "Women only"},
            {"category": "job_requirement", "text": "Women in technology programs"},
        ]

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["ignored_non_job_relevant_requirements"], 1)
        self.assertEqual(result["matched_requirements"], ["Women in technology programs"])

    def test_english_and_spanish_guardrail_fixtures_classify_semantic_categories(self):
        fixtures = PIPELINE.load_document(FIXTURES / "guardrail-fixtures.json")
        for language in ("english", "spanish"):
            with self.subTest(language=language, kind="excluded"):
                self.assertTrue(all(
                    PIPELINE.is_protected_or_non_job_relevant_requirement(item)
                    for item in fixtures[language]["excluded"]
                ))
            with self.subTest(language=language, kind="job_relevant"):
                self.assertFalse(any(
                    PIPELINE.is_protected_or_non_job_relevant_requirement(item)
                    for item in fixtures[language]["job_relevant"]
                ))

    def test_declared_eligibility_and_accommodation_are_structured_outside_fit_score(self):
        profile = json.loads(json.dumps(self.profile))
        profile["constraints"]["job_eligibility"] = {
            "work_authorization": ["Mexico"],
            "travel": "up to 25 percent",
        }
        profile["constraints"]["accommodations"] = ["step-free interview access"]

        result = PIPELINE.evaluate(profile, self.rules, self.vacancy, self.as_of)

        declared = result["candidate_declared_job_constraints"]
        self.assertEqual(declared["eligibility"], profile["constraints"]["job_eligibility"])
        self.assertEqual(declared["accommodations"], profile["constraints"]["accommodations"])
        self.assertFalse(declared["used_as_fit_score"])
        self.assertNotIn("step-free", json.dumps(result["matched_requirements"]).casefold())

    def test_spanish_protected_candidate_requirements_are_not_scored(self):
        profile = json.loads(json.dumps(self.profile))
        profile["profile"]["verified_evidence"] = ["Mujer candidata nacida en 1971"]
        vacancy = dict(self.vacancy)
        vacancy["requirements"] = [
            "Candidata debe ser mujer",
            "Menor de 60 años de edad",
            "Adjuntar fotografía reciente",
        ]

        result = PIPELINE.evaluate(profile, self.rules, vacancy, self.as_of)

        self.assertEqual(result["ignored_non_job_relevant_requirements"], 3)
        self.assertEqual(result["matched_requirements"], [])
        self.assertFalse(any("evidence for" in item for item in result["unknowns"]))

    def test_protected_attribute_contract_is_present_in_skill_and_evaluation_docs(self):
        skill = (ROOT / "skills" / "career-copilot" / "SKILL.md").read_text(encoding="utf-8").casefold()
        evaluation = (ROOT / "skills" / "career-copilot" / "references" / "evaluation.md").read_text(encoding="utf-8").casefold()
        for text in (skill, evaluation):
            self.assertIn("protected", text)
            self.assertIn("age", text)
            self.assertIn("gender", text)
            self.assertIn("photo", text)
            self.assertIn("accommodation", text)

    def test_tracker_review_flags_only_actionable_overdue_rows_without_mutation(self):
        statuses = ["applied", "contact", "recruiter_screen", "interview"]
        rows = []
        for index, status in enumerate(statuses, start=1):
            row = {field: "" for field in PIPELINE.TRACKER_FIELDS}
            row.update({
                "id": f"active-{index}",
                "company": "Synthetic Co",
                "role": "Synthetic Role",
                "status": status,
                "next_action": "send neutral follow-up",
                "next_action_date": "2026-08-25",
            })
            rows.append(row)
        for index, status in enumerate(("withdrawn", "rejected", "discarded"), start=1):
            row = {field: "" for field in PIPELINE.TRACKER_FIELDS}
            row.update({
                "id": f"terminal-{index}",
                "status": status,
                "next_action": "old action",
                "next_action_date": "2026-08-20",
            })
            rows.append(row)
        for identity, next_action, next_action_date in (
            ("future", "follow up later", "2026-08-27"),
            ("due-today", "follow up today", "2026-08-26"),
            ("missing-date", "follow up", ""),
            ("invalid-date", "follow up", "not-a-date"),
            ("missing-action", "", "2026-08-20"),
        ):
            row = {field: "" for field in PIPELINE.TRACKER_FIELDS}
            row.update({
                "id": identity,
                "status": "applied",
                "next_action": next_action,
                "next_action_date": next_action_date,
            })
            rows.append(row)

        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.atomic_write_tracker(tracker, rows)
            before = tracker.read_bytes()
            before_stat = tracker.stat()

            review = PIPELINE.review_tracker(tracker, self.as_of)

            self.assertEqual(review["summary"]["rows"], 12)
            self.assertEqual(review["summary"]["follow_up_overdue"], 4)
            self.assertEqual(review["summary"]["unknown_dates"], 1)
            self.assertEqual(review["summary"]["invalid_dates"], 1)
            overdue = [item for item in review["items"] if item["follow_up_overdue"]]
            self.assertEqual({item["status"] for item in overdue}, set(statuses))
            self.assertTrue(all("ghosted" not in json.dumps(item).casefold() for item in review["items"]))
            self.assertEqual(next(item for item in review["items"] if item["id"] == "missing-date")["next_action_date_state"], "unknown")
            self.assertEqual(next(item for item in review["items"] if item["id"] == "invalid-date")["next_action_date_state"], "invalid")
            self.assertFalse(next(item for item in review["items"] if item["id"] == "due-today")["follow_up_overdue"])
            self.assertEqual(tracker.read_bytes(), before)
            after_stat = tracker.stat()
            self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)
            self.assertEqual(stat.S_IMODE(after_stat.st_mode), stat.S_IMODE(before_stat.st_mode))
            self.assertEqual([row["status"] for row in PIPELINE.read_tracker(tracker)], [row["status"] for row in rows])

    def test_tracker_review_handles_blank_and_unknown_status_without_rewriting(self):
        rows = []
        for index, status in enumerate(("", "custom_pipeline_stage"), start=1):
            row = {field: "" for field in PIPELINE.TRACKER_FIELDS}
            row.update({
                "id": f"unknown-status-{index}",
                "status": status,
                "next_action": "verify follow-up",
                "next_action_date": "2026-08-20",
            })
            rows.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.atomic_write_tracker(tracker, rows)
            before = tracker.read_bytes()

            review = PIPELINE.review_tracker(tracker, self.as_of)

            self.assertEqual(review["summary"]["follow_up_overdue"], 2)
            self.assertEqual([item["status"] for item in review["items"]], ["", "custom_pipeline_stage"])
            self.assertEqual(tracker.read_bytes(), before)

    def test_tracker_review_rejects_missing_or_unsupported_trackers(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.csv"
            with self.assertRaisesRegex(FileNotFoundError, "does not exist"):
                PIPELINE.review_tracker(missing, self.as_of)

            unsupported = Path(tmp) / "unsupported.csv"
            unsupported.write_text("id,status,unexpected\n1,applied,value\n", encoding="utf-8")
            before = unsupported.read_bytes()
            with self.assertRaisesRegex(ValueError, "unsupported tracker schema"):
                PIPELINE.review_tracker(unsupported, self.as_of)
            self.assertEqual(unsupported.read_bytes(), before)

    def test_tracker_review_accepts_legacy_and_reordered_schema_without_migration(self):
        legacy_fields = [
            "id", "company", "role", "location", "source", "canonical_url", "external_job_id",
            "date_posted", "date_discovered", "status", "fit_recommendation", "priority", "next_action",
            "next_action_date", "contact", "human_path_status", "recruiter", "hiring_manager",
            "interviewer", "notes", "last_verified",
        ]
        cases = (
            ("legacy.csv", legacy_fields),
            ("reordered.csv", list(reversed(PIPELINE.TRACKER_FIELDS))),
        )
        with tempfile.TemporaryDirectory() as tmp:
            for filename, fieldnames in cases:
                tracker = Path(tmp) / filename
                row = {field: "" for field in fieldnames}
                row.update({
                    "id": filename,
                    "status": "applied",
                    "next_action": "follow up",
                    "next_action_date": "2026-08-20",
                })
                with tracker.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerow(row)
                before = tracker.read_bytes()
                before_stat = tracker.stat()

                review = PIPELINE.review_tracker(tracker, self.as_of)

                self.assertEqual(review["summary"]["follow_up_overdue"], 1)
                self.assertEqual(tracker.read_bytes(), before)
                self.assertEqual(tracker.stat().st_mtime_ns, before_stat.st_mtime_ns)

    def test_tracker_review_cli_accepts_explicit_as_of_without_evaluation_inputs(self):
        row = {field: "" for field in PIPELINE.TRACKER_FIELDS}
        row.update({
            "id": "cli-overdue",
            "status": "applied",
            "next_action": "follow up",
            "next_action_date": "2026-08-25",
        })
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            PIPELINE.atomic_write_tracker(tracker, [row])
            before = tracker.read_bytes()
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--review-tracker", str(tracker),
                    "--as-of", "2026-08-26",
                ],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["as_of"], "2026-08-26")
            self.assertTrue(result["read_only"])
            self.assertEqual(result["summary"]["follow_up_overdue"], 1)
            self.assertEqual(tracker.read_bytes(), before)

    def test_cli_without_human_path_reports_not_supplied(self):
        fixtures = FIXTURES
        with tempfile.TemporaryDirectory() as tmp:
            tracker = Path(tmp) / "tracker.csv"
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--profile", str(fixtures / "profile.json"),
                    "--rules", str(fixtures / "rules.json"),
                    "--vacancy", str(fixtures / "vacancy.json"),
                    "--tracker", str(tracker),
                    "--as-of", "2026-08-26",
                ],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(completed.stdout)
            row = PIPELINE.read_tracker(tracker)[0]
            self.assertEqual(result["human_path"]["status"], "not_supplied")
            self.assertEqual(row["human_path_status"], "")
            self.assertEqual(row["human_path_last_verified"], "")
            self.assertEqual(row["vacancy_last_verified"], "2026-08-26")

    def test_cli_rejects_unvalidated_human_path_without_tracker(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "human-path.json"
            artifact.write_text(json.dumps({"contacts": []}), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable, str(SCRIPT),
                    "--profile", str(FIXTURES / "profile.json"),
                    "--rules", str(FIXTURES / "rules.json"),
                    "--vacancy", str(FIXTURES / "vacancy.json"),
                    "--human-path", str(artifact),
                    "--as-of", "2026-08-26",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("retrieved_at", completed.stderr)

    def test_full_synthetic_demo_generates_all_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo"
            completed = subprocess.run(
                [sys.executable, str(DEMO), "--output-dir", str(output)],
                check=True, capture_output=True, text=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["evaluation"]["recommendation"], "High")
            self.assertEqual(result["external_actions"], 0)
            self.assertEqual(result["human_path"]["status"], "confirmed")
            self.assertEqual(result["tracker_rows"], 1)
            self.assertTrue(result["tracker_review"]["read_only"])
            self.assertEqual(result["tracker_review"]["summary"]["follow_up_overdue"], 1)
            tracker_row = PIPELINE.read_tracker(output / "tracker.csv")[0]
            self.assertEqual(tracker_row["status"], "applied")
            self.assertEqual(tracker_row["vacancy_last_verified"], "2026-08-26")
            self.assertEqual(tracker_row["human_path_last_verified"], "2026-08-26")
            self.assertTrue((output / "tracker.csv").is_file())
            self.assertTrue((output / "interview-brief.md").is_file())
            self.assertTrue((output / "offer-negotiation.md").is_file())
            self.assertTrue((output / "demo-result.json").is_file())
            self.assertTrue((output / "tracker-review.json").is_file())
            brief = (output / "interview-brief.md").read_text(encoding="utf-8")
            offer_brief = (output / "offer-negotiation.md").read_text(encoding="utf-8")
            self.assertIn("## Human Path", brief)
            self.assertIn("## Interviewer intelligence", brief)
            self.assertIn("## Offer record", offer_brief)
            self.assertIn("## Negotiation drafts", offer_brief)


if __name__ == "__main__":
    unittest.main()
