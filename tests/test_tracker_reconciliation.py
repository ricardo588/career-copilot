import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "tracker_reconciliation.py"
SPEC = importlib.util.spec_from_file_location("career_tracker_reconciliation", SCRIPT)
TRACKER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = TRACKER
SPEC.loader.exec_module(TRACKER)


HEADERS = [
    "No", "Company", "Role", "Location", "Canonical URL", "External Job ID", "Status", "Priority", "Notes",
]
FIELDS = {
    "business_id": "No",
    "company": "Company",
    "role": "Role",
    "location": "Location",
    "canonical_url": "Canonical URL",
    "external_job_id": "External Job ID",
    "status": "Status",
    "priority": "Priority",
    "notes": "Notes",
}


def row(physical_row, **values):
    return {"physical_row": physical_row, "values": values}


def snapshot(*rows):
    return {"headers": HEADERS, "rows": list(rows)}


def intended(**overrides):
    record = {
        "business_id": "8",
        "company": "Acme Cloud",
        "role": "Director, Program Delivery",
        "location": "Mexico City, Mexico",
        "canonical_url": "https://jobs.example.test/acme/PROGRAM-8",
        "external_job_id": "PROGRAM-8",
        "status": "identified",
        "priority": "medium",
        "notes": "Synthetic record only.",
    }
    record.update(overrides)
    return record


class TrackerReconciliationTests(unittest.TestCase):
    def test_external_job_id_returns_exact_update_plan_and_preserves_physical_row(self):
        result = TRACKER.reconcile(
            snapshot(row(41, **{
                "No": "8", "Company": "Acme Cloud", "Role": "Director, Program Delivery",
                "Location": "Mexico City, Mexico", "Canonical URL": "https://jobs.example.test/acme/PROGRAM-8",
                "External Job ID": "PROGRAM-8", "Status": "identified", "Priority": "medium", "Notes": "Old note",
            })),
            FIELDS,
            intended(notes="Updated synthetic note."),
            require_contiguous_business_ids=False,
        )
        self.assertEqual(result["decision"], "update_plan")
        self.assertEqual(result["physical_row"], 41)
        self.assertEqual(result["changes"], [{
            "logical_field": "notes", "header": "Notes", "old_value": "Old note", "new_value": "Updated synthetic note.",
        }])
        self.assertEqual(result["audit"]["max_id"], 8)

    def test_canonical_url_ignores_tracking_parameters(self):
        result = TRACKER.reconcile(
            snapshot(row(18, **{
                "No": "8", "Company": "Acme Cloud", "Role": "Director, Program Delivery",
                "Location": "Mexico City, Mexico",
                "Canonical URL": "https://jobs.example.test/acme/PROGRAM-8/?utm_source=test&ref=feed",
                "External Job ID": "", "Status": "identified", "Priority": "medium", "Notes": "",
            })),
            FIELDS,
            intended(external_job_id="", canonical_url="https://jobs.example.test/acme/PROGRAM-8?ref=feed&trk=linkedin", notes=""),
        )
        self.assertEqual(result["decision"], "no_change")
        self.assertEqual(result["physical_row"], 18)
        self.assertEqual(result["match_type"], "stable")

    def test_near_identical_company_and_role_requires_human_review(self):
        result = TRACKER.reconcile(
            snapshot(row(9, **{
                "No": "8", "Company": "Acme Cloud", "Role": "Director Program Delivery",
                "Location": "Mexico City, Mexico", "Canonical URL": "", "External Job ID": "",
                "Status": "identified", "Priority": "medium", "Notes": "",
            })),
            FIELDS,
            intended(external_job_id="", canonical_url=""),
        )
        self.assertEqual(result["decision"], "ambiguous_identity")
        self.assertEqual(result["reason"], "company_and_near_identical_role_requires_review")
        self.assertEqual(result["matches"], {"near_role": [9]})

    def test_missing_business_id_blocks_when_contiguity_is_required(self):
        result = TRACKER.reconcile(
            snapshot(
                row(2, **{"No": "1", "Company": "One", "Role": "One", "Location": "", "Canonical URL": "", "External Job ID": "", "Status": "", "Priority": "", "Notes": ""}),
                row(4, **{"No": "3", "Company": "Three", "Role": "Three", "Location": "", "Canonical URL": "", "External Job ID": "", "Status": "", "Priority": "", "Notes": ""}),
            ),
            FIELDS,
            intended(),
            require_contiguous_business_ids=True,
        )
        self.assertEqual(result["decision"], "integrity_failure")
        self.assertEqual(result["audit"]["missing_ids"], [2])
        self.assertEqual(result["reason"], "business_id_audit_failed")

    def test_blank_business_id_in_a_supplied_record_row_fails_closed(self):
        result = TRACKER.reconcile(
            snapshot(row(9, **{"No": "", "Company": "Blank ID", "Role": "Program Director"})),
            FIELDS,
            intended(),
            require_contiguous_business_ids=True,
        )
        self.assertEqual(result["decision"], "integrity_failure")
        self.assertEqual(result["audit"]["invalid_ids"], [{"physical_row": 9, "value": "", "reason": "blank"}])

    def test_duplicate_business_ids_block_before_identity_resolution(self):
        result = TRACKER.reconcile(
            snapshot(
                row(2, **{"No": "8", "Company": "A", "Role": "A", "Location": "", "Canonical URL": "", "External Job ID": "", "Status": "", "Priority": "", "Notes": ""}),
                row(3, **{"No": "8", "Company": "B", "Role": "B", "Location": "", "Canonical URL": "", "External Job ID": "", "Status": "", "Priority": "", "Notes": ""}),
            ),
            FIELDS,
            intended(),
        )
        self.assertEqual(result["decision"], "integrity_failure")
        self.assertEqual(result["audit"]["duplicate_ids"], {"8": [2, 3]})

    def test_create_requires_explicit_target_physical_row_and_business_id(self):
        empty = snapshot()
        no_target = TRACKER.reconcile(empty, FIELDS, intended())
        self.assertEqual(no_target["decision"], "integrity_failure")
        self.assertEqual(no_target["reason"], "explicit_create_physical_row_required")

        no_business_id = TRACKER.reconcile(empty, FIELDS, intended(business_id=""), create_physical_row=2)
        self.assertEqual(no_business_id["decision"], "integrity_failure")
        self.assertEqual(no_business_id["reason"], "explicit_business_id_required")

        planned = TRACKER.reconcile(empty, FIELDS, intended(), create_physical_row=2)
        self.assertEqual(planned["decision"], "create_plan")
        self.assertEqual(planned["physical_row"], 2)
        self.assertEqual(len(planned["changes"]), len(FIELDS))

    def test_requested_business_id_cannot_collide_on_create_or_update(self):
        existing = snapshot(
            row(11, **{"No": "4", "Company": "Acme", "Role": "Program Director", "External Job ID": "JOB-4"}),
            row(12, **{"No": "5", "Company": "Other", "Role": "Delivery Director", "External Job ID": "JOB-5"}),
        )
        create = TRACKER.reconcile(
            existing,
            FIELDS,
            intended(company="New", role="Transformation Director", external_job_id="JOB-NEW", business_id="5"),
            create_physical_row=13,
            require_contiguous_business_ids=False,
        )
        self.assertEqual(create["decision"], "integrity_failure")
        self.assertEqual(create["reason"], "requested_business_id_already_occupied")
        update = TRACKER.reconcile(
            existing,
            FIELDS,
            intended(external_job_id="JOB-4", business_id="5"),
            require_contiguous_business_ids=False,
        )
        self.assertEqual(update["decision"], "integrity_failure")
        self.assertEqual(update["matches"], {"business_id": [12]})
        with self.assertRaisesRegex(TRACKER.ReconciliationError, "positive integer"):
            TRACKER.reconcile(snapshot(), FIELDS, intended(business_id="0"), create_physical_row=2)

    def test_multiple_stable_matches_and_unknown_intended_field_fail_closed(self):
        duplicate_identity = snapshot(
            row(4, **{"No": "1", "External Job ID": "SAME"}),
            row(5, **{"No": "2", "External Job ID": "SAME"}),
        )
        result = TRACKER.reconcile(duplicate_identity, FIELDS, intended(external_job_id="SAME"))
        self.assertEqual(result["decision"], "ambiguous_identity")
        self.assertEqual(result["reason"], "multiple_stable_matches")
        json.dumps(result)
        with self.assertRaisesRegex(TRACKER.ReconciliationError, "unmapped field"):
            TRACKER.reconcile(snapshot(), FIELDS, {**intended(), "unmapped": "value"})

    def test_create_operation_reports_existing_stable_identity_as_duplicate(self):
        result = TRACKER.reconcile(
            snapshot(row(11, **{
                "No": "8", "Company": "Acme Cloud", "Role": "Director, Program Delivery",
                "Location": "Mexico City, Mexico", "Canonical URL": "", "External Job ID": "PROGRAM-8",
                "Status": "identified", "Priority": "medium", "Notes": "",
            })),
            FIELDS,
            intended(canonical_url=""),
            operation="create",
            create_physical_row=12,
        )
        self.assertEqual(result["decision"], "duplicate_match")
        self.assertEqual(result["physical_row"], 11)

    def test_conflicting_stable_identity_fails_closed_and_is_json_serializable(self):
        result = TRACKER.reconcile(
            snapshot(
                row(7, **{"No": "7", "Company": "Acme Cloud", "Role": "Director, Program Delivery", "Location": "Mexico City, Mexico", "Canonical URL": "https://jobs.example.test/acme/another", "External Job ID": "PROGRAM-8", "Status": "", "Priority": "", "Notes": ""}),
                row(8, **{"No": "8", "Company": "Acme Cloud", "Role": "Director, Program Delivery", "Location": "Mexico City, Mexico", "Canonical URL": "https://jobs.example.test/acme/PROGRAM-8", "External Job ID": "OTHER-8", "Status": "", "Priority": "", "Notes": ""}),
            ),
            FIELDS,
            intended(),
        )
        self.assertEqual(result["decision"], "ambiguous_identity")
        self.assertEqual(result["reason"], "conflicting_stable_identity")
        self.assertEqual(result["matches"], {"external_job_id": [7], "canonical_url": [8], "near_role": [7, 8]})
        json.dumps(result)

    def test_unmapped_extra_columns_are_supported_but_duplicate_headers_are_rejected(self):
        expanded = {
            "headers": HEADERS + ["Contact"],
            "rows": [row(2, **{
                "No": "8", "Company": "Acme Cloud", "Role": "Director, Program Delivery",
                "Location": "Mexico City, Mexico", "Canonical URL": "", "External Job ID": "PROGRAM-8",
                "Status": "identified", "Priority": "medium", "Notes": "", "Contact": "Synthetic",
            })],
        }
        result = TRACKER.reconcile(expanded, FIELDS, intended(canonical_url="", notes=""))
        self.assertEqual(result["decision"], "no_change")
        with self.assertRaisesRegex(TRACKER.ReconciliationError, "duplicate snapshot headers"):
            TRACKER.reconcile({"headers": HEADERS + ["Company"], "rows": []}, FIELDS, intended())
        with self.assertRaisesRegex(TRACKER.ReconciliationError, "trimmed strings"):
            TRACKER.reconcile({"headers": ["No", "Company "], "rows": []}, FIELDS, intended())


if __name__ == "__main__":
    unittest.main()
