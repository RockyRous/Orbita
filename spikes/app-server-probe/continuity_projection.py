"""Pure, offline continuity projection for M0 fixtures.

This module deliberately does not connect to App Server or start a model turn.
It turns already-sanitized, pinned source-event fixtures into a small, stable
projection for Gate E/F replay experiments.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXTURE_SCHEMA_VERSION = 1
PROJECTION_VERSION = 1
KNOWN_KINDS = {"root/observed", "outcome/observed", "continuity/gap"}
FORBIDDEN_KEY = re.compile(r"(authorization|password|cookie|credential|secret|(?:^|_)token(?:$|_))", re.IGNORECASE)
FORBIDDEN_VALUE = re.compile(
    r"(Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|[A-Za-z]:\\(?:Users|python)\\|/home/|seeded-secret)",
    re.IGNORECASE,
)


class ProjectionError(Exception):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def assert_sanitized(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if FORBIDDEN_KEY.search(str(key)):
                raise ProjectionError("unsafeFixture")
            assert_sanitized(child)
    elif isinstance(value, list):
        for child in value:
            assert_sanitized(child)
    elif isinstance(value, str) and FORBIDDEN_VALUE.search(value) and not value.startswith("<"):
        raise ProjectionError("unsafeFixture")


def validate_runtime_pin(fixture: dict[str, object]) -> dict[str, str]:
    runtime = fixture.get("runtime")
    if not isinstance(runtime, dict):
        raise ProjectionError("invalidRuntimePin")
    required = ("cliVersion", "contractManifestSha256", "transport")
    if any(not isinstance(runtime.get(key), str) or not runtime[key] for key in required):
        raise ProjectionError("invalidRuntimePin")
    if not re.fullmatch(r"[0-9a-f]{64}", runtime["contractManifestSha256"]):
        raise ProjectionError("invalidRuntimePin")
    return {key: runtime[key] for key in required}


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def normalize_fixture(fixture: dict[str, object]) -> dict[str, object]:
    assert_sanitized(fixture)
    if fixture.get("fixtureSchemaVersion") != FIXTURE_SCHEMA_VERSION:
        raise ProjectionError("unsupportedFixtureVersion")
    if fixture.get("projectionVersion") != PROJECTION_VERSION:
        raise ProjectionError("unsupportedProjectionVersion")
    runtime = validate_runtime_pin(fixture)
    events = fixture.get("events")
    if not isinstance(events, list):
        raise ProjectionError("invalidEvents")

    roots: dict[str, dict[str, object]] = {}
    gaps: list[dict[str, object]] = []
    unknown_events: list[dict[str, str]] = []
    seen_events: dict[str, str] = {}

    for event in events:
        if not isinstance(event, dict):
            raise ProjectionError("invalidEvent")
        event_id = event.get("eventId")
        kind = event.get("kind")
        root_id = event.get("rootId")
        if not all(isinstance(value, str) and value for value in (event_id, kind, root_id)):
            raise ProjectionError("invalidEvent")
        fingerprint = canonical_json(event)
        previous_fingerprint = seen_events.get(event_id)
        if previous_fingerprint is not None:
            if previous_fingerprint != fingerprint:
                raise ProjectionError("conflictingDuplicateEvent")
            continue
        seen_events[event_id] = fingerprint
        if kind not in KNOWN_KINDS:
            unknown_events.append({"eventId": event_id, "kind": kind})
            continue
        root = roots.setdefault(root_id, {"id": root_id, "outcome": {"provenance": [], "status": "unknown"}})
        outcome = root["outcome"]
        assert isinstance(outcome, dict)
        if kind == "root/observed":
            continue
        if kind == "outcome/observed":
            status = event.get("status")
            if status not in {"completed", "failed", "interrupted"}:
                raise ProjectionError("invalidOutcome")
            if outcome["status"] != "unknown" and outcome["status"] != status:
                raise ProjectionError("conflictingOutcome")
            outcome["status"] = status
            outcome["provenance"] = [event_id]
            continue
        start_sequence = event.get("startSequence")
        end_sequence = event.get("endSequence")
        if (
            event.get("reason") != "unrecoverableInterval"
            or not isinstance(start_sequence, int)
            or not isinstance(end_sequence, int)
            or start_sequence > end_sequence
        ):
            raise ProjectionError("invalidGap")
        gap = {
            "endSequence": end_sequence,
            "eventId": event_id,
            "reason": "unrecoverableInterval",
            "rootId": root_id,
            "startSequence": start_sequence,
        }
        gaps.append(gap)
        outcome["status"] = "unknown"
        outcome["provenance"] = [event_id]

    projection = {
        "fixtureSchemaVersion": FIXTURE_SCHEMA_VERSION,
        "gaps": sorted(gaps, key=lambda gap: (gap["rootId"], gap["startSequence"], gap["eventId"])),
        "projectionVersion": PROJECTION_VERSION,
        "roots": [roots[root_id] for root_id in sorted(roots)],
        "runtime": runtime,
        "unknownEvents": sorted(unknown_events, key=lambda event: (event["eventId"], event["kind"])),
    }
    projection["projectionSha256"] = hashlib.sha256(canonical_json(projection).encode("utf-8")).hexdigest()
    return projection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        fixture = json.loads(arguments.input.read_text(encoding="utf-8"))
        if not isinstance(fixture, dict):
            raise ProjectionError("invalidFixture")
        projection = normalize_fixture(fixture)
    except (OSError, json.JSONDecodeError, ProjectionError) as error:
        category = error.category if isinstance(error, ProjectionError) else "invalidFixture"
        projection = {
            "fixtureSchemaVersion": FIXTURE_SCHEMA_VERSION,
            "outcome": {"failure": category, "success": False},
            "projectionVersion": PROJECTION_VERSION,
        }
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(canonical_json(projection), encoding="utf-8")
        return 1
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(canonical_json(projection), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
