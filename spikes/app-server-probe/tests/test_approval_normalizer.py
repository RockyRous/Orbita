import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


PROBE_ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = PROBE_ROOT / "approval_normalizer.py"
PENDING_FIXTURE = PROBE_ROOT / "tests" / "fixtures" / "approval-command-pending.json"
DECISION_FIXTURES = {
    "accept": PROBE_ROOT / "tests" / "fixtures" / "approval-command-accept.json",
    "decline": PROBE_ROOT / "tests" / "fixtures" / "approval-command-decline.json",
    "cancel": PROBE_ROOT / "tests" / "fixtures" / "approval-command-cancel.json",
}
LATE_RESOLUTION_FIXTURE = PROBE_ROOT / "tests" / "fixtures" / "approval-command-late-resolution.json"
MULTIPLE_PENDING_FIXTURE = PROBE_ROOT / "tests" / "fixtures" / "approval-command-multiple-pending.json"


class CommandApprovalNormalizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        codex = shutil.which("codex")
        assert codex is not None
        with tempfile.TemporaryDirectory(prefix="orbita-approval-schema-") as temp_dir:
            cls.schema_dir = Path(temp_dir) / "stable"
            subprocess.run(
                [codex, "app-server", "generate-json-schema", "--out", str(cls.schema_dir)],
                check=True,
                text=True,
                capture_output=True,
            )
            cls._schema_copy = tempfile.TemporaryDirectory(prefix="orbita-approval-schema-copy-")
            shutil.copytree(cls.schema_dir, Path(cls._schema_copy.name) / "stable")
        cls.schema_dir = Path(cls._schema_copy.name) / "stable"

        spec = importlib.util.spec_from_file_location("orbita_approval_normalizer", NORMALIZER)
        assert spec is not None and spec.loader is not None
        cls.normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.normalizer)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._schema_copy.cleanup()

    def test_projects_schema_valid_pending_command_approval_as_attributable_attention(self) -> None:
        capture = json.loads(PENDING_FIXTURE.read_text(encoding="utf-8"))
        validator = self.normalizer.CommandApprovalSchemaValidator(self.schema_dir)

        artifact = self.normalizer.normalize_command_approval_capture(capture, validator)

        self.assertEqual(
            artifact,
            {
                "approvals": [
                    {
                        "command": "echo ORBITA_APPROVAL_SENTINEL",
                        "decision": None,
                        "itemId": "<ITEM_1>",
                        "kind": "command",
                        "requestId": "<REQUEST_1>",
                        "resolution": "pending",
                        "sourceContext": {
                            "approvalId": None,
                            "cwd": "<DISPOSABLE_PROJECT>",
                            "reason": "synthetic approval test"
                        },
                        "threadId": "<THREAD_1>",
                        "turnId": "<TURN_1>"
                    }
                ],
                "attention": {"actionRequired": True, "state": "Action required"},
                "fixtureSchemaVersion": 1,
                "lateOrMismatchedResolutions": [],
                "surfaceClassification": {
                    "item/commandExecution/requestApproval": "stable",
                    "serverRequest/resolved": "stable"
                }
            }
        )

    def test_records_only_observed_accept_decline_and_cancel_without_inferring_execution_outcome(self) -> None:
        for decision, fixture_path in DECISION_FIXTURES.items():
            with self.subTest(decision=decision):
                capture = json.loads(fixture_path.read_text(encoding="utf-8"))
                validator = self.normalizer.CommandApprovalSchemaValidator(self.schema_dir)

                artifact = self.normalizer.normalize_command_approval_capture(capture, validator)

                self.assertEqual(artifact["attention"], {"actionRequired": False, "state": "No attention"})
                self.assertEqual(artifact["lateOrMismatchedResolutions"], [])
                self.assertEqual(artifact["approvals"][0]["decision"], decision)
                self.assertEqual(artifact["approvals"][0]["resolution"], "resolved")
                self.assertNotIn("executionStatus", artifact)
                self.assertNotIn("turnOutcome", artifact)

    def test_late_or_mismatched_resolution_cannot_clear_current_actionable_attention(self) -> None:
        capture = json.loads(LATE_RESOLUTION_FIXTURE.read_text(encoding="utf-8"))
        validator = self.normalizer.CommandApprovalSchemaValidator(self.schema_dir)

        artifact = self.normalizer.normalize_command_approval_capture(capture, validator)

        self.assertEqual(artifact["attention"], {"actionRequired": True, "state": "Action required"})
        self.assertEqual(artifact["approvals"][0]["requestId"], "<REQUEST_CURRENT>")
        self.assertEqual(artifact["approvals"][0]["resolution"], "pending")
        self.assertEqual(
            artifact["lateOrMismatchedResolutions"],
            [
                {"requestId": "<REQUEST_OLD>", "threadId": "<THREAD_OLD>"},
                {"requestId": "<REQUEST_CURRENT>", "threadId": "<THREAD_WRONG>"},
            ],
        )

    def test_resolving_one_of_multiple_pending_requests_leaves_the_other_actionable(self) -> None:
        capture = json.loads(MULTIPLE_PENDING_FIXTURE.read_text(encoding="utf-8"))
        validator = self.normalizer.CommandApprovalSchemaValidator(self.schema_dir)

        artifact = self.normalizer.normalize_command_approval_capture(capture, validator)

        self.assertEqual(artifact["attention"], {"actionRequired": True, "state": "Action required"})
        self.assertEqual(
            [(approval["requestId"], approval["decision"], approval["resolution"]) for approval in artifact["approvals"]],
            [
                ("<REQUEST_1>", "accept", "resolved"),
                ("<REQUEST_2>", None, "pending"),
            ],
        )

    def test_rejects_schema_invalid_request_before_it_can_become_attention(self) -> None:
        capture = json.loads(PENDING_FIXTURE.read_text(encoding="utf-8"))
        del capture["messages"][0]["message"]["params"]["itemId"]
        validator = self.normalizer.CommandApprovalSchemaValidator(self.schema_dir)

        with self.assertRaisesRegex(self.normalizer.ApprovalContractError, "invalidContractMessage"):
            self.normalizer.normalize_command_approval_capture(capture, validator)


if __name__ == "__main__":
    unittest.main()
