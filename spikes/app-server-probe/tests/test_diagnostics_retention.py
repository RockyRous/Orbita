import importlib.util
import json
import unittest
from pathlib import Path


PROBE_ROOT = Path(__file__).resolve().parents[1]
TOOL = PROBE_ROOT / "diagnostics_retention.py"
FIXTURE = PROBE_ROOT / "tests" / "fixtures" / "diagnostics-retention-events.json"


class DiagnosticsRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("orbita_diagnostics_retention", TOOL)
        assert spec is not None and spec.loader is not None
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def test_measures_classifies_and_marks_a_bounded_buffer_gap(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

        artifact = self.tool.measure_and_sanitize(fixture, max_events=2)

        self.assertEqual(artifact["measurement"]["eventCount"], 5)
        self.assertEqual(
            artifact["measurement"]["classCounts"],
            {"diagnostic-only": 2, "recovery-critical": 3},
        )
        self.assertGreater(artifact["measurement"]["inputBytes"], 0)
        self.assertEqual(
            artifact["buffer"]["gap"],
            {"droppedEventCount": 3, "firstDroppedOrdinal": 0, "kind": "truncated"},
        )
        self.assertEqual(
            [event["method"] for event in artifact["buffer"]["events"]],
            ["serverRequest/resolved", "turn/completed"],
        )
        self.assertEqual(artifact["buffer"]["events"][0]["retentionClass"], "recovery-critical")

    def test_export_is_deterministic_and_omits_message_payload_content(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        artifact = self.tool.measure_and_sanitize(fixture, max_events=5)

        first = self.tool.export_sanitized_diagnostics(artifact)
        second = self.tool.export_sanitized_diagnostics(artifact)

        self.assertEqual(first, second)
        self.assertNotIn("params", first)
        self.assertNotIn("<THREAD_1>", first)
        self.assertIn('"eventCount":5', first)

    def test_secret_or_private_path_fails_before_any_artifact_can_be_produced(self) -> None:
        for unsafe in ("Bearer sk-private-token", "C:\\Users\\private\\project"):
            with self.subTest(unsafe=unsafe):
                fixture = {"fixtureSchemaVersion": 1, "events": [{"message": {"method": "turn/started", "params": {"value": unsafe}}}]}
                with self.assertRaisesRegex(self.tool.DiagnosticsSanitationError, "unsafeInput"):
                    self.tool.measure_and_sanitize(fixture, max_events=1)


if __name__ == "__main__":
    unittest.main()
