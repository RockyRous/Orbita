import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "recovery_live_runner.py"
SPEC = importlib.util.spec_from_file_location("orbita_recovery_live_runner", RUNNER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RecoveryLiveRunnerTests(unittest.TestCase):
    def test_cli_requires_explicit_live_recovery_opt_in(self) -> None:
        with patch.object(MODULE, "run_live_recovery", side_effect=AssertionError("must not start")):
            self.assertEqual(MODULE.main(["--output", "ignored.json"]), 2)

    def test_missing_recovered_identity_becomes_explicit_gap(self) -> None:
        projection = MODULE.project_recovery(
            {"rootId": "<ROOT_1>", "turnId": "<TURN_1>"},
            {"thread": None, "turns": [], "items": []},
        )

        self.assertEqual(projection["gaps"], [{
            "kind": "rootIdentityUnavailable",
            "rootId": "<ROOT_1>",
        }])
        self.assertEqual(projection["outcome"], {"status": "unknown", "source": "gap"})

    def test_recovery_dedupes_correlated_history_without_creating_a_second_root(self) -> None:
        projection = MODULE.project_recovery(
            {"rootId": "<ROOT_1>", "turnId": "<TURN_1>"},
            {
                "thread": {"id": "<ROOT_1>"},
                "turns": [
                    {"id": "<TURN_1>", "status": "completed", "threadId": "<ROOT_1>"},
                    {"id": "<TURN_1>", "status": "completed", "threadId": "<ROOT_1>"},
                ],
                "items": [
                    {"id": "<ITEM_1>", "threadId": "<ROOT_1>"},
                    {"id": "<ITEM_1>", "threadId": "<ROOT_1>"},
                ],
            },
        )

        self.assertEqual(projection["roots"], [{"id": "<ROOT_1>"}])
        self.assertEqual(projection["history"], {"itemCount": 1, "turnCount": 1})
        self.assertEqual(projection["outcome"], {"status": "completed", "source": "thread/turns/list"})

    def test_recovery_requests_are_only_read_surfaces_and_never_thread_resume(self) -> None:
        requests = MODULE.build_recovery_requests("thread-source")

        self.assertEqual([request["method"] for request in requests], [
            "thread/read", "thread/turns/list", "thread/items/list",
        ])
        self.assertTrue(all(request["method"] != "thread/resume" for request in requests))
        self.assertTrue(all(request["params"]["threadId"] == "thread-source" for request in requests))


if __name__ == "__main__":
    unittest.main()
