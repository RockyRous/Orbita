import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROBE_ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = PROBE_ROOT / "continuity_projection.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

SPEC = importlib.util.spec_from_file_location("orbita_continuity_projection", NORMALIZER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def normalize(source: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object], str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "projection.json"
        completed = subprocess.run(
            [sys.executable, str(NORMALIZER), "--input", str(source), "--output", str(output)],
            cwd=PROBE_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        serialized = output.read_text(encoding="utf-8")
    return completed, json.loads(serialized), serialized


class ContinuityProjectionTests(unittest.TestCase):
    def test_identical_replay_is_byte_stable_and_duplicate_events_do_not_duplicate_root_or_outcome(self) -> None:
        source = FIXTURES / "continuity-replay.json"
        first_completed, first, first_serialized = normalize(source)
        second_completed, second, second_serialized = normalize(source)

        self.assertEqual(first_completed.returncode, 0, first_completed.stderr)
        self.assertEqual(second_completed.returncode, 0, second_completed.stderr)
        self.assertEqual(first_serialized, second_serialized)
        self.assertEqual(first, second)
        self.assertEqual(first["roots"], [{
            "id": "<ROOT_1>",
            "outcome": {"provenance": ["event-outcome-1"], "status": "completed"},
        }])

    def test_unknown_variant_isolated_to_diagnostics_and_does_not_break_known_root(self) -> None:
        completed, projection, serialized = normalize(FIXTURES / "continuity-replay.json")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(projection["roots"][0]["outcome"]["status"], "completed")
        self.assertEqual(projection["unknownEvents"], [{"eventId": "event-future-1", "kind": "future/continuity"}])
        self.assertNotIn("synthetic-private", serialized)
        self.assertNotIn("seeded-secret", serialized)

    def test_unrecoverable_interval_is_a_gap_and_never_an_idle_or_successful_outcome(self) -> None:
        completed, projection, _ = normalize(FIXTURES / "continuity-gap.json")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(projection["gaps"], [{
            "endSequence": 8,
            "eventId": "event-gap-1",
            "reason": "unrecoverableInterval",
            "rootId": "<ROOT_1>",
            "startSequence": 4,
        }])
        self.assertEqual(projection["roots"], [{
            "id": "<ROOT_1>",
            "outcome": {"provenance": ["event-gap-1"], "status": "unknown"},
        }])

    def test_rejects_unpinned_or_unsanitized_fixture(self) -> None:
        source = json.loads((FIXTURES / "continuity-replay.json").read_text(encoding="utf-8"))
        del source["runtime"]["contractManifestSha256"]
        with self.assertRaises(MODULE.ProjectionError) as error:
            MODULE.normalize_fixture(source)
        self.assertEqual(error.exception.category, "invalidRuntimePin")

        source = json.loads((FIXTURES / "continuity-replay.json").read_text(encoding="utf-8"))
        source["events"][0]["payload"] = {"authorization": "Bearer seeded-secret-value"}
        with self.assertRaises(MODULE.ProjectionError) as error:
            MODULE.normalize_fixture(source)
        self.assertEqual(error.exception.category, "unsafeFixture")

    def test_conflicting_duplicate_event_id_fails_closed_instead_of_selecting_an_outcome(self) -> None:
        source = json.loads((FIXTURES / "continuity-replay.json").read_text(encoding="utf-8"))
        source["events"][2]["status"] = "failed"

        with self.assertRaises(MODULE.ProjectionError) as error:
            MODULE.normalize_fixture(source)

        self.assertEqual(error.exception.category, "conflictingDuplicateEvent")


if __name__ == "__main__":
    unittest.main()
