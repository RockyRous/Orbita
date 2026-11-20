#!/usr/bin/env python3
"""Pure offline measurement and sanitation foundation for M0 diagnostics.

The tool accepts only already-sanitized synthetic fixtures. It measures their
shape in memory, emits a bounded content-free buffer, and never starts Codex or
reads runtime state.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RECOVERY_CRITICAL_METHODS = {
    "turn/completed",
    "serverRequest/resolved",
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
    "item/permissions/requestApproval",
    "item/tool/requestUserInput",
}
PAYLOAD_CLASSES = {
    "turn/completed": "turn-lifecycle",
    "turn/started": "turn-lifecycle",
    "serverRequest/resolved": "request-resolution",
    "item/commandExecution/requestApproval": "approval",
    "item/fileChange/requestApproval": "approval",
    "item/permissions/requestApproval": "approval",
    "item/tool/requestUserInput": "user-question",
    "item/agentMessage/delta": "streaming",
    "item/started": "item-lifecycle",
    "item/completed": "item-lifecycle",
}
FORBIDDEN_KEY = re.compile(r"authorization|password|cookie|credential|secret|(?:^|_)token(?:$|_)", re.IGNORECASE)
FORBIDDEN_VALUE = re.compile(
    r"bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|[A-Za-z]:\\(?:Users|python)\\|/(?:home|Users)/|seeded-secret",
    re.IGNORECASE,
)


class DiagnosticsSanitationError(ValueError):
    """Input is unsuitable for persistence or diagnostics export."""


def _canonical_bytes(value: object) -> int:
    return len((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))


def _reject_sensitive(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if FORBIDDEN_KEY.search(str(key)):
                raise DiagnosticsSanitationError("unsafeInput")
            _reject_sensitive(child)
    elif isinstance(value, list):
        for child in value:
            _reject_sensitive(child)
    elif isinstance(value, str) and FORBIDDEN_VALUE.search(value):
        raise DiagnosticsSanitationError("unsafeInput")


def _event_descriptor(ordinal: int, event: dict[str, object]) -> dict[str, object]:
    message = event.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("method"), str):
        raise DiagnosticsSanitationError("invalidFixture")
    method = message["method"]
    return {
        "method": method,
        "ordinal": ordinal,
        "payloadBytes": _canonical_bytes(event),
        "payloadClass": PAYLOAD_CLASSES.get(method, "unknown"),
        "retentionClass": "recovery-critical" if method in RECOVERY_CRITICAL_METHODS else "diagnostic-only",
    }


def measure_and_sanitize(fixture: dict[str, object], *, max_events: int) -> dict[str, object]:
    """Measure a fixture and return an explicitly bounded, content-free artifact."""
    if max_events < 1:
        raise DiagnosticsSanitationError("invalidBufferLimit")
    _reject_sensitive(fixture)
    events = fixture.get("events")
    if fixture.get("fixtureSchemaVersion") != 1 or not isinstance(events, list):
        raise DiagnosticsSanitationError("invalidFixture")

    descriptors = [_event_descriptor(ordinal, event) for ordinal, event in enumerate(events) if isinstance(event, dict)]
    if len(descriptors) != len(events):
        raise DiagnosticsSanitationError("invalidFixture")
    class_counts = {"diagnostic-only": 0, "recovery-critical": 0}
    payload_class_counts: dict[str, int] = {}
    for descriptor in descriptors:
        retention_class = descriptor["retentionClass"]
        payload_class = descriptor["payloadClass"]
        assert isinstance(retention_class, str) and isinstance(payload_class, str)
        class_counts[retention_class] += 1
        payload_class_counts[payload_class] = payload_class_counts.get(payload_class, 0) + 1

    dropped = max(0, len(descriptors) - max_events)
    retained = descriptors[dropped:]
    gap = None if dropped == 0 else {
        "droppedEventCount": dropped,
        "firstDroppedOrdinal": 0,
        "kind": "truncated",
    }
    return {
        "buffer": {"events": retained, "gap": gap, "maxEvents": max_events},
        "fixtureSchemaVersion": 1,
        "measurement": {
            "classCounts": class_counts,
            "eventCount": len(descriptors),
            "inputBytes": _canonical_bytes({"events": events, "fixtureSchemaVersion": 1}),
            "payloadClassCounts": dict(sorted(payload_class_counts.items())),
        },
        "sanitation": {
            "omitted": ["message.id", "message.params", "message.result", "message.error", "direction"],
            "policyVersion": 1,
        },
    }


def export_sanitized_diagnostics(artifact: dict[str, object]) -> str:
    """Perform the stricter second pass used by deterministic diagnostic export."""
    _reject_sensitive(artifact)
    buffer = artifact.get("buffer")
    measurement = artifact.get("measurement")
    if not isinstance(buffer, dict) or not isinstance(measurement, dict):
        raise DiagnosticsSanitationError("invalidArtifact")
    events = buffer.get("events")
    if not isinstance(events, list):
        raise DiagnosticsSanitationError("invalidArtifact")
    export_events: list[dict[str, object]] = []
    for event in events:
        if not isinstance(event, dict):
            raise DiagnosticsSanitationError("invalidArtifact")
        export_events.append({
            "method": event.get("method"),
            "ordinal": event.get("ordinal"),
            "payloadClass": event.get("payloadClass"),
            "retentionClass": event.get("retentionClass"),
        })
    exported = {
        "buffer": {"events": export_events, "gap": buffer.get("gap"), "maxEvents": buffer.get("maxEvents")},
        "diagnosticsExportVersion": 1,
        "measurement": measurement,
        "sanitation": {"contentOmitted": True, "policyVersion": 1},
    }
    return json.dumps(exported, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-events", required=True, type=int)
    arguments = parser.parse_args(argv)
    fixture = json.loads(arguments.input.read_text(encoding="utf-8"))
    if not isinstance(fixture, dict):
        raise DiagnosticsSanitationError("invalidFixture")
    artifact = measure_and_sanitize(fixture, max_events=arguments.max_events)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(export_sanitized_diagnostics(artifact), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
