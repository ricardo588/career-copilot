import importlib.util
import json
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

    def test_gmail_triage_reads_one_message_and_proposes_without_mutation(self):
        message = {
            "id": "synthetic-message",
            "threadId": "synthetic-thread",
            "labelIds": ["INBOX", "UNREAD"],
            "internalDate": "1760000000000",
            "snippet": "Your recruiter screen is scheduled.",
        }
        fake = FakeRunner([message])
        with tempfile.TemporaryDirectory() as tmp:
            result = ADAPTERS.gmail_triage(
                fake, "synthetic-message", workspace=Path(tmp) / "private", account_ref="me",
            )
        self.assertEqual(result["status"], "proposed")
        self.assertEqual(result["message_ref"], "gmail:synthetic-message")
        self.assertEqual(result["proposal"]["kind"], "gmail_evidence_review")
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("get", fake.calls[0])
        self.assertNotIn("modify", fake.calls[0])

    def test_gmail_triage_records_only_explicit_direct_evidence(self):
        message = {"id": "synthetic-message", "threadId": "synthetic-thread"}
        fake = FakeRunner([message])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            result = ADAPTERS.gmail_triage(
                fake, "synthetic-message", workspace=workspace, account_ref="me",
                supported_fact="Recruiter explicitly scheduled a screen", excerpt="I would like to schedule a screen.",
            )
            evidence = (workspace / "evidence" / "gmail-evidence.jsonl").read_text(encoding="utf-8")
        self.assertTrue(result["proposal"]["evidence_ref"].startswith("evidence/gmail-evidence.jsonl#"))
        self.assertIn('"supported_fact":"Recruiter explicitly scheduled a screen"', evidence)

    def test_gmail_evidence_can_feed_a_read_only_tracker_reconciliation_proposal(self):
        snapshot = {"headers": self.tracker_headers, "rows": [{
            "physical_row": 5,
            "values": dict(zip(self.tracker_headers, [
                "1", "Synthetic Co", "Program Director", "Remote", "https://jobs.example.test/synthetic/1", "SYN-1", "identified", "medium", "Old note.",
            ])),
        }]}
        result = ADAPTERS.gmail_reconciliation_proposal(
            snapshot, self.tracker_fields, self.tracker_record,
            "evidence/gmail-evidence.jsonl#00000000-0000-0000-0000-000000000000",
        )
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["plan"]["decision"], "update_plan")
        self.assertEqual(result["evidence_ref"], "evidence/gmail-evidence.jsonl#00000000-0000-0000-0000-000000000000")

    def test_gmail_triage_reprocessing_is_a_private_idempotent_no_op(self):
        message = {"id": "synthetic-message", "threadId": "synthetic-thread"}
        fake = FakeRunner([message, message])
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            first = ADAPTERS.gmail_triage(fake, "synthetic-message", workspace=workspace, account_ref="me")
            second = ADAPTERS.gmail_triage(fake, "synthetic-message", workspace=workspace, account_ref="me")
            ledger = (workspace / "triage" / "gmail-triage.jsonl").read_text(encoding="utf-8")
        self.assertEqual(first["status"], "proposed")
        self.assertEqual(second["status"], "already_processed")
        self.assertEqual(ledger.count('"outcome":"proposed"'), 1)
        self.assertEqual(len(fake.calls), 2)

    def test_gmail_triage_blocks_a_fingerprint_collision(self):
        message = {"id": "synthetic-message", "threadId": "synthetic-thread"}
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            ADAPTERS.gmail_triage(FakeRunner([message]), "synthetic-message", workspace=workspace, account_ref="me")
            ledger_path = workspace / "triage" / "gmail-triage.jsonl"
            event = json.loads(ledger_path.read_text(encoding="utf-8"))
            event["message_id"] = "different-message"
            ledger_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint collision"):
                ADAPTERS.gmail_triage(FakeRunner([message]), "synthetic-message", workspace=workspace, account_ref="me")

    def test_gmail_triage_fails_closed_when_ledger_is_corrupt(self):
        message = {"id": "synthetic-message", "threadId": "synthetic-thread"}
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            ledger_path = workspace / "triage" / "gmail-triage.jsonl"
            ledger_path.parent.mkdir(parents=True)
            ledger_path.write_text("not-json\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ledger is invalid"):
                ADAPTERS.gmail_triage(
                    FakeRunner([message]), "synthetic-message", workspace=workspace, account_ref="me",
                )

    def test_gmail_mark_read_rejects_apply_without_the_reviewed_plan_hash(self):
        fake = FakeRunner([])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "approved plan hash"):
                ADAPTERS.gmail_mark_read(
                    fake, "synthetic-message", apply=True, profile=self.confirm_each,
                    workspace=Path(tmp) / "private",
                )
        self.assertEqual(fake.calls, [])

    def test_gmail_mark_read_is_dry_run_then_verified(self):
        dry_fake = FakeRunner([])
        dry = ADAPTERS.gmail_mark_read(dry_fake, "synthetic-message")
        self.assertEqual(dry["status"], "dry_run")
        self.assertEqual(dry_fake.calls, [])

        apply_fake = FakeRunner([
            {"id": "synthetic-message", "labelIds": ["INBOX", "UNREAD"]},
            {"id": "synthetic-message"},
            {"id": "synthetic-message", "labelIds": ["INBOX"]},
        ])
        with tempfile.TemporaryDirectory() as tmp:
            applied = ADAPTERS.gmail_mark_read(
                apply_fake, "synthetic-message", apply=True, profile=self.confirm_each,
                workspace=Path(tmp) / "private", approved_plan_sha256=dry["approval_sha256"],
            )
            audit = (Path(tmp) / "private" / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertTrue(applied["verified"])
        self.assertEqual(len(apply_fake.calls), 3)
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
            gmail_dry = ADAPTERS.gmail_mark_read(fake, "synthetic-message")
            with self.assertRaises(ValueError):
                ADAPTERS.gmail_mark_read(
                    fake, "synthetic-message", apply=True, profile=self.draft_only, workspace=workspace,
                    approved_plan_sha256=gmail_dry["approval_sha256"],
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

    def test_gmail_evidence_rejects_an_invalid_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                ADAPTERS.record_gmail_evidence(
                    Path(tmp) / "private", account_ref="me", message_id="message-126",
                    supported_fact="reviewed", content_sha256="this must not be stored as a hash",
                )

    def test_mutation_failure_is_audited_after_the_preflight_event(self):
        calls = 0

        def failing_runner(command):
            nonlocal calls
            calls += 1
            if calls == 1:
                return {"id": "synthetic-message", "labelIds": ["UNREAD"]}
            raise RuntimeError("synthetic provider failure")

        dry = ADAPTERS.gmail_mark_read(FakeRunner([]), "synthetic-message")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "private"
            with self.assertRaisesRegex(RuntimeError, "provider failure"):
                ADAPTERS.gmail_mark_read(
                    failing_runner, "synthetic-message", apply=True, profile=self.confirm_each, workspace=workspace,
                    approved_plan_sha256=dry["approval_sha256"],
                )
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
        self.assertIn('"result":"attempted"', audit)
        self.assertIn('"result":"failed"', audit)

    def test_obsidian_write_rejects_apply_without_the_reviewed_plan_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "approved plan hash"):
                ADAPTERS.obsidian_write(
                    Path(tmp) / "vault", "CareerCopilot/Brief.md", "# Brief\n", apply=True,
                    profile=self.confirm_each, workspace=Path(tmp) / "private",
                )

    def test_obsidian_write_rejects_vault_inside_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            (vault / ".git").mkdir(parents=True)
            dry = ADAPTERS.obsidian_write(vault, "CareerCopilot/Brief.md", "# Brief\n")
            with self.assertRaisesRegex(ValueError, "Git repository"):
                ADAPTERS.obsidian_write(
                    vault, "CareerCopilot/Brief.md", "# Brief\n", apply=True,
                    profile=self.confirm_each, workspace=Path(tmp) / "private", approved_plan_sha256=dry["approval_sha256"],
                )

    def test_obsidian_write_rejects_vault_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_vault = Path(tmp) / "real-vault"
            real_vault.mkdir()
            vault_link = Path(tmp) / "vault-link"
            vault_link.symlink_to(real_vault, target_is_directory=True)
            dry = ADAPTERS.obsidian_write(vault_link, "CareerCopilot/Brief.md", "# Brief\n")
            with self.assertRaisesRegex(ValueError, "symlink"):
                ADAPTERS.obsidian_write(
                    vault_link, "CareerCopilot/Brief.md", "# Brief\n", apply=True,
                    profile=self.confirm_each, workspace=Path(tmp) / "private", approved_plan_sha256=dry["approval_sha256"],
                )

    def test_obsidian_write_approval_is_bound_to_one_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault_a = Path(tmp) / "vault-a"
            vault_b = Path(tmp) / "vault-b"
            dry = ADAPTERS.obsidian_write(vault_a, "CareerCopilot/Brief.md", "# Brief\n")
            with self.assertRaisesRegex(ValueError, "approved plan hash"):
                ADAPTERS.obsidian_write(
                    vault_b, "CareerCopilot/Brief.md", "# Brief\n", apply=True,
                    profile=self.confirm_each, workspace=Path(tmp) / "private", approved_plan_sha256=dry["approval_sha256"],
                )
            self.assertFalse((vault_b / "CareerCopilot" / "Brief.md").exists())

    def test_obsidian_write_is_scoped_dry_run_first_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            dry = ADAPTERS.obsidian_write(vault, "CareerCopilot/Brief.md", "# Brief\n")
            self.assertEqual(dry["status"], "dry_run")
            self.assertFalse((vault / "CareerCopilot" / "Brief.md").exists())

            workspace = Path(tmp) / "private"
            applied = ADAPTERS.obsidian_write(
                vault, "CareerCopilot/Brief.md", "# Brief\n", apply=True,
                profile=self.confirm_each, workspace=workspace, approved_plan_sha256=dry["approval_sha256"],
            )
            self.assertTrue(applied["verified"])
            self.assertEqual((vault / "CareerCopilot" / "Brief.md").read_text(encoding="utf-8"), "# Brief\n")
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
            self.assertIn('"result":"verified"', audit)

            with self.assertRaises(ValueError):
                ADAPTERS.obsidian_write(vault, "../outside.md", "blocked", apply=True)

    def test_obsidian_kanban_dry_run_creates_a_markdown_backed_board_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            result = ADAPTERS.obsidian_kanban_project(
                vault, "CareerCopilot/Board.md", "To do",
                {"artifact_ref": "evidence/gmail-evidence.jsonl#00000000-0000-0000-0000-000000000001", "card_text": "Synthetic review card"},
            )
            self.assertEqual(result["status"], "dry_run")
            self.assertEqual(result["plan"]["decision"], "create_board_plan")
            self.assertIn("kanban-plugin: board", result["markdown"])
            self.assertIn("## To do", result["markdown"])
            self.assertIn("- [ ] Synthetic review card ^cc-", result["markdown"])
            self.assertFalse((vault / "CareerCopilot" / "Board.md").exists())

    def test_obsidian_kanban_dry_run_appends_only_to_the_explicit_existing_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            board = vault / "CareerCopilot" / "Board.md"
            board.parent.mkdir(parents=True)
            original = (
                "---\nkanban-plugin: board\n---\n\n## To do\n\n- [ ] Existing synthetic card\n\n"
                "## Done\n\n- [x] Preserved synthetic completion\n\n%% kanban:settings\n```\n{\"kanban-plugin\":\"board\"}\n```\n%%\n"
            )
            board.write_text(original, encoding="utf-8")
            result = ADAPTERS.obsidian_kanban_project(
                vault, "CareerCopilot/Board.md", "To do",
                {"artifact_ref": "evidence/gmail-evidence.jsonl#00000000-0000-0000-0000-000000000002", "card_text": "New synthetic review card"},
            )
            self.assertEqual(result["plan"]["decision"], "append_card_plan")
            self.assertIn("- [ ] New synthetic review card ^cc-", result["markdown"])
            self.assertIn("## Done\n\n- [x] Preserved synthetic completion", result["markdown"])
            self.assertEqual(board.read_text(encoding="utf-8"), original)

    def test_obsidian_kanban_apply_requires_current_hash_and_verifies_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            artifact = {"artifact_ref": "evidence/gmail-evidence.jsonl#00000000-0000-0000-0000-000000000003", "card_text": "Approved synthetic card"}
            dry = ADAPTERS.obsidian_kanban_project(vault, "CareerCopilot/Board.md", "To do", artifact)
            workspace = Path(tmp) / "private"
            applied = ADAPTERS.obsidian_kanban_project(
                vault, "CareerCopilot/Board.md", "To do", artifact, apply=True,
                profile=self.confirm_each, workspace=workspace, approved_plan_sha256=dry["approval_sha256"],
            )
            self.assertTrue(applied["verified"])
            self.assertIn("Approved synthetic card", (vault / "CareerCopilot" / "Board.md").read_text(encoding="utf-8"))
            audit = (workspace / "audit" / "external-actions.jsonl").read_text(encoding="utf-8")
            self.assertIn('"operation":"project_card"', audit)
            self.assertIn('"result":"verified"', audit)

    def test_obsidian_kanban_preview_updates_its_own_marked_card_without_touching_other_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            artifact = {"artifact_ref": "evidence/gmail-evidence.jsonl#00000000-0000-0000-0000-000000000004", "card_text": "Original synthetic card"}
            created = ADAPTERS.obsidian_kanban_project(vault, "CareerCopilot/Board.md", "To do", artifact)
            board = vault / "CareerCopilot" / "Board.md"
            board.parent.mkdir(parents=True)
            board.write_text(created["markdown"], encoding="utf-8")
            updated = ADAPTERS.obsidian_kanban_project(
                vault, "CareerCopilot/Board.md", "To do", {**artifact, "card_text": "Updated synthetic card"},
            )
            self.assertEqual(updated["plan"]["decision"], "update_card_plan")
            self.assertIn("Updated synthetic card", updated["markdown"])
            self.assertNotIn("Original synthetic card", updated["markdown"])


if __name__ == "__main__":
    unittest.main()
