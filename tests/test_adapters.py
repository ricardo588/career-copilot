import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "career-copilot" / "scripts" / "adapters.py"
SPEC = importlib.util.spec_from_file_location("career_adapters", SCRIPT)
ADAPTERS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(ADAPTERS)


class FakeRunner:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, command):
        self.calls.append(command)
        return self.responses.pop(0)


class AdapterTests(unittest.TestCase):
    draft_only = {"permissions": {"external_action_mode": "draft_only", "external_action_mode_locked": True}}
    confirm_each = {"permissions": {"external_action_mode": "confirm_each_external", "external_action_mode_locked": False}}
    tracker_headers = ["No", "Company", "Role", "Location", "Canonical URL", "External Job ID", "Status", "Priority", "Notes"]
    tracker_fields = {
        "business_id": "No", "company": "Company", "role": "Role", "location": "Location",
        "canonical_url": "Canonical URL", "external_job_id": "External Job ID", "status": "Status",
        "priority": "Priority", "notes": "Notes",
    }
    tracker_record = {
        "business_id": "1", "company": "Synthetic Co", "role": "Program Director", "location": "Remote",
        "canonical_url": "https://jobs.example.test/synthetic/1", "external_job_id": "SYN-1",
        "status": "identified", "priority": "medium", "notes": "Updated synthetic note.",
    }

    def test_sheets_update_is_dry_run_by_default(self):
        fake = FakeRunner([])
        result = ADAPTERS.sheets_update(fake, "sheet-example-1234", "Applications!A2:B2", [["Acme", "Role"]])
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(fake.calls, [])
        self.assertNotIn("sheet-example-1234", str(result))

    def test_sheets_reconcile_is_read_only_and_preserves_physical_rows(self):
        fake = FakeRunner([{"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1?utm_source=mail", "SYN-1", "identified", "medium", "Old synthetic note."],
        ]}])
        result = ADAPTERS.sheets_reconcile(
            fake, "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["target"]["sheet"], "…1234")
        self.assertNotIn("sheet-example-1234", str(result))
        self.assertEqual(result["plan"]["decision"], "update_plan")
        self.assertEqual(result["plan"]["physical_row"], 5)
        self.assertEqual(result["plan"]["changes"], [{
            "logical_field": "notes", "header": "Notes", "old_value": "Old synthetic note.", "new_value": "Updated synthetic note.",
        }])
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("get", fake.calls[0])
        self.assertNotIn("update", fake.calls[0])

    def test_sheets_reconcile_skips_fully_blank_rows_but_blocks_blank_business_ids(self):
        fake = FakeRunner([{"values": [
            self.tracker_headers,
            [],
            ["", "Synthetic Co", "Program Director", "Remote", "", "SYN-1", "identified", "medium", ""],
        ]}])
        result = ADAPTERS.sheets_reconcile(
            fake, "sheet-example-1234", "Applications!A10:I100", 10,
            self.tracker_fields, self.tracker_record,
        )
        self.assertEqual(result["plan"]["decision"], "integrity_failure")
        self.assertEqual(result["plan"]["audit"]["invalid_ids"], [{"physical_row": 12, "value": "", "reason": "blank"}])
        self.assertEqual(len(fake.calls), 1)

    def test_sheets_reconcile_rejects_unsafe_range_and_never_writes(self):
        fake = FakeRunner([{"values": [self.tracker_headers]}])
        with self.assertRaisesRegex(ValueError, "must start at --header-row"):
            ADAPTERS.sheets_reconcile(
                fake, "sheet-example-1234", "Applications!A2:I100", 3,
                self.tracker_fields, self.tracker_record,
            )
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("get", fake.calls[0])
        self.assertNotIn("update", fake.calls[0])

    def test_sheets_apply_requires_matching_readback(self):
        fake = FakeRunner([{"updatedRows": 1}, {"values": [["Acme", "Role"]]}])
        with tempfile.TemporaryDirectory() as tmp:
            result = ADAPTERS.sheets_update(
                fake, "sheet-example-1234", "Applications!A2:B2", [["Acme", "Role"]],
                apply=True, profile=self.confirm_each, workspace=Path(tmp) / "private",
            )
            audit = (Path(tmp) / "private" / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertTrue(result["verified"])
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("update", fake.calls[0])
        self.assertIn("get", fake.calls[1])
        self.assertIn('"result":"attempted"', audit)
        self.assertIn('"result":"applied"', audit)
        self.assertIn('"result":"verified"', audit)

    def test_reconcile_apply_requires_approved_current_plan_and_writes_only_changed_cells(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old synthetic note."],
        ]}
        preview = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        self.assertEqual(preview["status"], "dry_run")
        self.assertEqual(preview["plan"]["writes"], [{
            "range": "Applications!I5", "values": [["Updated synthetic note."]],
        }])

        fake = FakeRunner([snapshot, {"updatedCells": 1}, {"values": [["Updated synthetic note."]]}])
        with tempfile.TemporaryDirectory() as tmp:
            result = ADAPTERS.sheets_reconcile_apply(
                fake, "sheet-example-1234", "Applications!A4:I100", 4,
                self.tracker_fields, self.tracker_record,
                apply=True, approved_plan_sha256=preview["approval_sha256"],
                profile=self.confirm_each, workspace=Path(tmp) / "private",
            )
            audit = (Path(tmp) / "private" / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertTrue(result["verified"])
        self.assertEqual(len(fake.calls), 3)
        self.assertIn("get", fake.calls[0])
        self.assertIn("update", fake.calls[1])
        self.assertIn("get", fake.calls[2])
        self.assertIn('"operation":"reconcile_apply"', audit)
        self.assertIn('"result":"attempted"', audit)
        self.assertIn('"result":"verified"', audit)

    def test_reconcile_apply_blocks_stale_approval_before_any_write(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "A concurrent note."],
        ]}
        fake = FakeRunner([snapshot])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaisesRegex(ValueError, "does not match"):
                ADAPTERS.sheets_reconcile_apply(
                    fake, "sheet-example-1234", "Applications!A4:I100", 4,
                    self.tracker_fields, self.tracker_record,
                    apply=True, approved_plan_sha256="0" * 64,
                    profile=self.confirm_each, workspace=workspace,
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("get", fake.calls[0])
        self.assertNotIn("update", fake.calls[0])
        self.assertIn('"result":"blocked"', audit)

    def test_reconcile_approval_hash_is_bound_to_exact_sheet_id_without_exposing_it(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old synthetic note."],
        ]}
        first = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "abcx1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        second = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "zzzq1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        self.assertEqual(first["plan"]["target"]["sheet"], second["plan"]["target"]["sheet"])
        self.assertNotEqual(first["approval_sha256"], second["approval_sha256"])
        fake = FakeRunner([snapshot])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "does not match"):
                ADAPTERS.sheets_reconcile_apply(
                    fake, "zzzq1234", "Applications!A4:I100", 4,
                    self.tracker_fields, self.tracker_record, apply=True,
                    approved_plan_sha256=first["approval_sha256"],
                    profile=self.confirm_each, workspace=Path(tmp) / "private",
                )
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn("update", fake.calls[0])

    def test_reconcile_apply_blocks_draft_only_before_any_write(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old synthetic note."],
        ]}
        preview = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        fake = FakeRunner([snapshot])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaisesRegex(ValueError, "draft_only"):
                ADAPTERS.sheets_reconcile_apply(
                    fake, "sheet-example-1234", "Applications!A4:I100", 4,
                    self.tracker_fields, self.tracker_record, apply=True,
                    approved_plan_sha256=preview["approval_sha256"], profile=self.draft_only, workspace=workspace,
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("get", fake.calls[0])
        self.assertNotIn("update", fake.calls[0])
        self.assertIn('"result":"blocked"', audit)

    def test_reconcile_apply_returns_verified_no_change_without_an_external_mutation(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Updated synthetic note."],
        ]}
        preview = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        self.assertEqual(preview["plan"]["decision"], "no_change")
        fake = FakeRunner([snapshot])
        result = ADAPTERS.sheets_reconcile_apply(
            fake, "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record, apply=True,
            approved_plan_sha256=preview["approval_sha256"],
        )
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(result["status"], "no_change")
        self.assertTrue(result["verified"])

    def test_reconcile_apply_never_treats_integrity_failure_as_no_change(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old note."],
            ["1", "Duplicate Co", "Other Role", "Remote", "https://jobs.example.test/duplicate/1", "SYN-DUP", "identified", "medium", ""],
        ]}
        preview = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        self.assertEqual(preview["plan"]["decision"], "integrity_failure")
        fake = FakeRunner([snapshot])
        with self.assertRaisesRegex(ValueError, "not applicable: integrity_failure"):
            ADAPTERS.sheets_reconcile_apply(
                fake, "sheet-example-1234", "Applications!A4:I100", 4,
                self.tracker_fields, self.tracker_record, apply=True,
                approved_plan_sha256=preview["approval_sha256"],
            )
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("get", fake.calls[0])
        self.assertNotIn("update", fake.calls[0])

    def test_reconcile_apply_fails_when_cell_readback_differs(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old synthetic note."],
        ]}
        preview = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, self.tracker_record,
        )
        fake = FakeRunner([snapshot, {"updatedCells": 1}, {"values": [["Concurrent replacement."]]}])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaisesRegex(RuntimeError, "readback did not match"):
                ADAPTERS.sheets_reconcile_apply(
                    fake, "sheet-example-1234", "Applications!A4:I100", 4,
                    self.tracker_fields, self.tracker_record, apply=True,
                    approved_plan_sha256=preview["approval_sha256"], profile=self.confirm_each, workspace=workspace,
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertEqual(len(fake.calls), 3)
        self.assertIn('"result":"attempted"', audit)
        self.assertIn('"result":"applied"', audit)
        self.assertIn('"result":"failed"', audit)

    def test_reconcile_apply_audits_narrow_write_completed_before_later_failure(self):
        snapshot = {"values": [
            self.tracker_headers,
            ["1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old synthetic note."],
        ]}
        record = dict(self.tracker_record, priority="high")
        preview = ADAPTERS.sheets_reconcile_apply(
            FakeRunner([snapshot]), "sheet-example-1234", "Applications!A4:I100", 4,
            self.tracker_fields, record,
        )
        calls = []
        updates = 0

        def partial_failure_runner(command):
            nonlocal updates
            calls.append(command)
            if "get" in command:
                return snapshot
            updates += 1
            if updates == 2:
                raise RuntimeError("synthetic second-cell failure")
            return {"updatedCells": 1}

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaisesRegex(RuntimeError, "second-cell failure"):
                ADAPTERS.sheets_reconcile_apply(
                    partial_failure_runner, "sheet-example-1234", "Applications!A4:I100", 4,
                    self.tracker_fields, record, apply=True,
                    approved_plan_sha256=preview["approval_sha256"], profile=self.confirm_each, workspace=workspace,
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertEqual(len(calls), 3)
        self.assertEqual(audit.count('"result":"applied"'), 1)
        self.assertIn('"result":"failed"', audit)
        self.assertIn("1 cell write(s) completed", audit)

    def test_reconcile_apply_rejects_create_outside_explicit_snapshot_range(self):
        record = dict(self.tracker_record, business_id="2", external_job_id="SYN-2", canonical_url="https://jobs.example.test/synthetic/2")
        fake = FakeRunner([{"values": [self.tracker_headers, ["1", "Other Co", "Other Role", "Remote", "https://jobs.example.test/other/1", "OTHER-1", "identified", "medium", ""]]}])
        with self.assertRaisesRegex(ValueError, "inside the explicit snapshot range"):
            ADAPTERS.sheets_reconcile_apply(
                fake, "sheet-example-1234", "Applications!A4:I5", 4,
                self.tracker_fields, record, operation="create", create_physical_row=6,
            )
        self.assertEqual(len(fake.calls), 1)

    def test_gmail_mark_read_is_dry_run_then_verified(self):
        dry_fake = FakeRunner([])
        dry = ADAPTERS.gmail_mark_read(dry_fake, "synthetic-message")
        self.assertEqual(dry["status"], "dry_run")
        self.assertEqual(dry_fake.calls, [])

        apply_fake = FakeRunner([{"id": "synthetic-message"}, {"id": "synthetic-message", "labelIds": ["INBOX"]}])
        with tempfile.TemporaryDirectory() as tmp:
            applied = ADAPTERS.gmail_mark_read(
                apply_fake, "synthetic-message", apply=True, profile=self.confirm_each,
                workspace=Path(tmp) / "private",
            )
            audit = (Path(tmp) / "private" / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertTrue(applied["verified"])
        self.assertEqual(len(apply_fake.calls), 2)
        self.assertIn('"payload_plan_sha256"', audit)

    def test_draft_only_blocks_external_mutations_even_with_apply(self):
        fake = FakeRunner([])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaises(ValueError):
                ADAPTERS.sheets_update(
                    fake, "sheet-example-1234", "Applications!A2:B2", [["Acme", "Role"]],
                    apply=True, profile=self.draft_only, workspace=workspace,
                )
            with self.assertRaises(ValueError):
                ADAPTERS.gmail_mark_read(
                    fake, "synthetic-message", apply=True, profile=self.draft_only, workspace=workspace,
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertEqual(fake.calls, [])
        self.assertEqual(audit.count('"result":"blocked"'), 2)

    def test_gmail_evidence_is_private_minimal_and_requires_direct_support(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            ref = ADAPTERS.record_gmail_evidence(
                workspace, account_ref="me", message_id="message-123", thread_id="thread-456",
                supported_fact="Recruiter explicitly scheduled a screen", excerpt="I would like to schedule a screen.",
            )
            evidence_path = workspace / "evidence" / "gmail-evidence.jsonl"
            stored = evidence_path.read_text(encoding="utf-8")
            self.assertTrue(ref.startswith("evidence/gmail-evidence.jsonl#"))
            self.assertIn('"message_id":"message-123"', stored)
            self.assertEqual((workspace.stat().st_mode & 0o777), 0o700)
            self.assertEqual((evidence_path.stat().st_mode & 0o777), 0o600)
            with self.assertRaisesRegex(ValueError, "ambiguous or contradictory"):
                ADAPTERS.record_gmail_evidence(
                    workspace, account_ref="me", message_id="message-124", supported_fact="ambiguous", excerpt="maybe", support_status="ambiguous",
                )
            with self.assertRaisesRegex(ValueError, "ambiguous or contradictory"):
                ADAPTERS.record_gmail_evidence(
                    workspace, account_ref="me", message_id="message-125", supported_fact="contradictory", excerpt="maybe", support_status="contradictory",
                )
            with self.assertRaises(ValueError):
                ADAPTERS.record_gmail_evidence(
                    workspace, account_ref="me", message_id="message-126", supported_fact="invalid", excerpt="maybe", content_sha256="abc",
                )

    def test_mutation_failure_is_audited_after_the_preflight_event(self):
        def failing_runner(command):
            raise RuntimeError("synthetic provider failure")

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaisesRegex(RuntimeError, "provider failure"):
                ADAPTERS.gmail_mark_read(
                    failing_runner, "synthetic-message", apply=True, profile=self.confirm_each, workspace=workspace,
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertIn('"result":"attempted"', audit)
        self.assertIn('"result":"failed"', audit)

    def test_obsidian_write_is_scoped_dry_run_first_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            dry = ADAPTERS.obsidian_write(vault, "CareerCopilot/Brief.md", "# Brief\n")
            self.assertEqual(dry["status"], "dry_run")
            self.assertFalse((vault / "CareerCopilot" / "Brief.md").exists())

            applied = ADAPTERS.obsidian_write(vault, "CareerCopilot/Brief.md", "# Brief\n", apply=True)
            self.assertTrue(applied["verified"])
            self.assertEqual((vault / "CareerCopilot" / "Brief.md").read_text(encoding="utf-8"), "# Brief\n")

            with self.assertRaises(ValueError):
                ADAPTERS.obsidian_write(vault, "../outside.md", "blocked", apply=True)


if __name__ == "__main__":
    unittest.main()
