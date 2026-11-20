import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


PROBE_ROOT = Path(__file__).resolve().parents[1]
RUNNER = PROBE_ROOT / "approval_live_runner.py"


class ApprovalLiveRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("orbita_approval_live_runner", RUNNER)
        assert spec is not None and spec.loader is not None
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def test_cli_requires_explicit_live_opt_in_before_runner_can_start(self) -> None:
        with patch.object(self.runner, "run_live_approval", side_effect=AssertionError("must not start")):
            exit_code = self.runner.main(["--output", "ignored.json"])

        self.assertEqual(exit_code, 2)

    def test_operator_decision_is_required_after_context_display_and_never_defaults_to_accept(self) -> None:
        displayed = []

        with self.assertRaisesRegex(self.runner.LiveApprovalFailure, "operatorDecisionRequired"):
            self.runner.operator_decision_after_display(
                {"command": self.runner.SAFE_COMMAND, "threadId": "<THREAD_1>"},
                display=displayed.append,
                read_input=lambda _prompt: "",
            )

        self.assertEqual(len(displayed), 1)

    def test_only_one_shot_accept_or_decline_response_is_constructed(self) -> None:
        self.assertEqual(
            self.runner.build_one_shot_response("request-1", "accept"),
            {"id": "request-1", "result": {"decision": "accept"}},
        )
        self.assertEqual(
            self.runner.build_one_shot_response("request-1", "decline"),
            {"id": "request-1", "result": {"decision": "decline"}},
        )
        with self.assertRaisesRegex(self.runner.LiveApprovalFailure, "unsupportedOperatorDecision"):
            self.runner.build_one_shot_response("request-1", "acceptForSession")

    def test_mismatched_resolution_cannot_close_the_observed_approval(self) -> None:
        approval = {"requestId": "request-1", "threadId": "thread-1"}

        self.assertFalse(
            self.runner.is_matching_resolution(
                {"requestId": "request-1", "threadId": "another-thread"}, approval
            )
        )
        self.assertFalse(
            self.runner.is_matching_resolution(
                {"requestId": "another-request", "threadId": "thread-1"}, approval
            )
        )
        self.assertTrue(
            self.runner.is_matching_resolution({"requestId": "request-1", "threadId": "thread-1"}, approval)
        )

    def test_non_synthetic_reason_or_policy_context_is_rejected_before_operator_prompt(self) -> None:
        with self.assertRaisesRegex(self.runner.LiveApprovalFailure, "unexpectedApprovalContext"):
            self.runner._assert_exact_approval(
                {
                    "command": self.runner.SAFE_COMMAND,
                    "cwd": "C:/disposable/project",
                    "itemId": "item-1",
                    "kind": "command",
                    "networkApprovalContext": None,
                    "proposedExecpolicyAmendment": None,
                    "proposedNetworkPolicyAmendments": None,
                    "reason": "unreviewed reason",
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                },
                Path("C:/disposable/project"),
                "thread-1",
                "turn-1",
            )

    def test_success_requires_a_complete_observed_accept_round_trip(self) -> None:
        self.assertIsNone(
            self.runner.classify_outcome(
                approval_seen=True,
                decision="accept",
                resolution_seen=True,
                sentinel_seen=True,
                terminal_status="completed",
            )
        )
        self.assertEqual(
            self.runner.classify_outcome(
                approval_seen=False,
                decision=None,
                resolution_seen=False,
                sentinel_seen=False,
                terminal_status="failed",
            ),
            "approvalNotObservedBeforeTerminal",
        )
        self.assertEqual(
            self.runner.classify_outcome(
                approval_seen=True,
                decision="accept",
                resolution_seen=True,
                sentinel_seen=True,
                terminal_status="failed",
            ),
            "terminalStatusNotCompleted",
        )

    def test_decline_is_successful_only_when_it_resolves_without_the_sentinel_and_completes(self) -> None:
        self.assertIsNone(
            self.runner.classify_outcome(
                approval_seen=True,
                decision="decline",
                resolution_seen=True,
                sentinel_seen=False,
                terminal_status="completed",
            )
        )
        self.assertEqual(
            self.runner.classify_outcome(
                approval_seen=True,
                decision="decline",
                resolution_seen=True,
                sentinel_seen=True,
                terminal_status="completed",
            ),
            "declinedCommandExecuted",
        )

    def test_controlled_cleanup_retries_windows_file_locks_once_process_has_stopped(self) -> None:
        with patch.object(self.runner.shutil, "rmtree", side_effect=[PermissionError(), PermissionError(), None]) as remove:
            with patch.object(self.runner.time, "sleep") as sleep:
                removed = self.runner._remove_disposable_directory(Path("C:/disposable/isolated-codex-home"))

        self.assertTrue(removed)
        self.assertEqual(remove.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
