#!/usr/bin/env python3
"""Explicit, bounded M0 reconnect probe; importing it never starts App Server."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError


PINNED_VERSION = "codex-cli 0.170.0"
ROOT_PROMPT = "Reply with exactly: ORBITA_RECOVERY_ROOT_OK. Do not use tools."
ROOT_SENTINEL = "ORBITA_RECOVERY_ROOT_OK"
READ_METHODS = ("thread/read", "thread/turns/list", "thread/items/list")
ENV_ALLOWLIST = {"APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "PATH", "PATHEXT", "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "WINDIR"}


class LiveRecoveryFailure(RuntimeError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def build_recovery_requests(thread_id: str) -> list[dict[str, object]]:
    """The reconnect leg is intentionally read-only: no resume or turn start."""
    return [
        {"id": "recovery-thread-read", "method": "thread/read", "params": {"threadId": thread_id}},
        {"id": "recovery-turns-list", "method": "thread/turns/list", "params": {"threadId": thread_id}},
        {"id": "recovery-items-list", "method": "thread/items/list", "params": {"threadId": thread_id}},
    ]


def _unique_correlated(records: object, root_id: str) -> list[dict[str, object]]:
    if not isinstance(records, list):
        return []
    unique: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("threadId") not in {None, root_id}:
            continue
        record_id = record.get("id")
        if isinstance(record_id, str) and record_id and record_id not in unique:
            unique[record_id] = record
    return [unique[record_id] for record_id in sorted(unique)]


def project_recovery(baseline: dict[str, str], recovered: dict[str, object]) -> dict[str, object]:
    root_id = baseline.get("rootId")
    turn_id = baseline.get("turnId")
    thread = recovered.get("thread")
    if not isinstance(root_id, str) or not isinstance(turn_id, str):
        raise LiveRecoveryFailure("invalidBaseline")
    if not isinstance(thread, dict) or thread.get("id") != root_id:
        return {"gaps": [{"kind": "rootIdentityUnavailable", "rootId": root_id}], "history": {"itemCount": 0, "turnCount": 0}, "outcome": {"status": "unknown", "source": "gap"}, "roots": [{"id": root_id}]}
    turns = _unique_correlated(recovered.get("turns"), root_id)
    items = _unique_correlated(recovered.get("items"), root_id)
    observed_turn = next((turn for turn in turns if turn.get("id") == turn_id), None)
    if isinstance(observed_turn, dict) and observed_turn.get("status") in {"completed", "failed", "interrupted"}:
        outcome = {"status": observed_turn["status"], "source": "thread/turns/list"}
    else:
        outcome = {"status": "unknown", "source": "unavailable"}
    return {"gaps": [], "history": {"itemCount": len(items), "turnCount": len(turns)}, "outcome": outcome, "roots": [{"id": root_id}]}


class SchemaValidator:
    def __init__(self, schema_dir: Path) -> None:
        def load(name: str) -> Draft7Validator:
            return Draft7Validator(json.loads((schema_dir / name).read_text(encoding="utf-8")))
        self.client_request = load("ClientRequest.json")
        self.client_notification = load("ClientNotification.json")
        self.server_notification = load("ServerNotification.json")
        self.server_request = load("ServerRequest.json")
        self.response = load("JSONRPCResponse.json")
        self.results = {method: load(name) for method, name in {
            "initialize": "v1/InitializeResponse.json", "thread/start": "v2/ThreadStartResponse.json",
            "turn/start": "v2/TurnStartResponse.json", "thread/read": "v2/ThreadReadResponse.json",
            "thread/turns/list": "v2/ThreadTurnsListResponse.json", "thread/items/list": "v2/ThreadItemsListResponse.json",
        }.items()}

    @staticmethod
    def check(validator: Draft7Validator, value: object) -> None:
        try:
            validator.validate(value)
        except ValidationError as error:
            raise LiveRecoveryFailure("invalidContractMessage") from error

    def client(self, message: dict[str, object]) -> None:
        self.check(self.client_request if "id" in message else self.client_notification, message)

    def server(self, message: dict[str, object], requests: dict[object, str]) -> str | None:
        method = message.get("method")
        if isinstance(method, str):
            self.check(self.server_request if "id" in message else self.server_notification, message)
            return method
        requested = requests.get(message.get("id"))
        if requested is None or requested not in self.results:
            raise LiveRecoveryFailure("uncorrelatedServerResponse")
        self.check(self.response, message)
        if "error" in message:
            raise LiveRecoveryFailure("requestFailed")
        result = message.get("result")
        if not isinstance(result, dict):
            raise LiveRecoveryFailure("invalidContractMessage")
        self.check(self.results[requested], result)
        return None


def _environment(parent: dict[str, str], home: Path) -> dict[str, str]:
    result = {key: value for key, value in parent.items() if key.upper() in ENV_ALLOWLIST}
    result["CODEX_HOME"] = str(home)
    return result


def _pump(stream: Any, events: queue.Queue[object]) -> None:
    try:
        for line in stream:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise LiveRecoveryFailure("invalidProtocolMessage")
            events.put(value)
        events.put(LiveRecoveryFailure("protocolEof"))
    except Exception:
        events.put(LiveRecoveryFailure("invalidProtocolMessage"))


def _receive(events: queue.Queue[object], deadline: float) -> dict[str, object]:
    try:
        value = events.get(timeout=max(0, deadline - time.monotonic()))
    except queue.Empty as error:
        raise LiveRecoveryFailure("deadlineExceeded") from error
    if isinstance(value, LiveRecoveryFailure):
        raise value
    if not isinstance(value, dict):
        raise LiveRecoveryFailure("invalidProtocolMessage")
    return value


def _send(process: subprocess.Popen[str], validator: SchemaValidator, requests: dict[object, str], message: dict[str, object]) -> None:
    validator.client(message)
    if "id" in message:
        requests[message["id"]] = message["method"]  # type: ignore[index]
    if process.stdin is None:
        raise LiveRecoveryFailure("processStdinUnavailable")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _stop(process: subprocess.Popen[str]) -> None:
    if process.stdin is not None:
        process.stdin.close()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _sanitize_write(output: Path, artifact: dict[str, object]) -> None:
    text = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    if re.search(r"Bearer\s+|sk-[A-Za-z0-9_-]{8,}|[A-Za-z]:\\(?:Users|python)\\|/home/", text, re.IGNORECASE):
        raise LiveRecoveryFailure("sanitationFailed")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _sanitize_projection(projection: dict[str, object] | None, root_id: str | None) -> dict[str, object] | None:
    if projection is None:
        return None
    sanitized = json.loads(json.dumps(projection))
    if root_id is not None:
        for root in sanitized.get("roots", []):
            if isinstance(root, dict) and root.get("id") == root_id:
                root["id"] = "<THREAD_1>"
        for gap in sanitized.get("gaps", []):
            if isinstance(gap, dict) and gap.get("rootId") == root_id:
                gap["rootId"] = "<THREAD_1>"
    return sanitized


def run_live_recovery(output: Path, timeout_seconds: float) -> bool:
    """One root turn then a fresh stdio connection; no resume/new-turn in recovery leg."""
    # This runner deliberately records a gap/unavailable result on any missing
    # recovery evidence. It is not invoked by tests and requires CLI opt-in.
    failure: str | None = None
    root: Path | None = None
    first: subprocess.Popen[str] | None = None
    second: subprocess.Popen[str] | None = None
    projection: dict[str, object] | None = None
    observed_root_id: str | None = None
    contract_bundle_sha256: str | None = None
    try:
        executable = shutil.which("codex")
        if executable is None:
            raise LiveRecoveryFailure("codexNotFound")
        version = subprocess.run([executable, "--version"], text=True, capture_output=True, check=True).stdout.strip()
        if version != PINNED_VERSION:
            raise LiveRecoveryFailure("runtimeVersionMismatch")
        root = Path(tempfile.mkdtemp(prefix="orbita-recovery-live-"))
        home, project, schema = root / "home", root / "project", root / "schema"
        home.mkdir(); project.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=project, text=True, capture_output=True, check=True)
        subprocess.run([executable, "app-server", "generate-json-schema", "--out", str(schema)], text=True, capture_output=True, check=True)
        contract_bundle_sha256 = hashlib.sha256((schema / "codex_app_server_protocol.schemas.json").read_bytes()).hexdigest()
        validator = SchemaValidator(schema)
        deadline = time.monotonic() + timeout_seconds

        def connect() -> tuple[subprocess.Popen[str], queue.Queue[object], dict[object, str]]:
            process = subprocess.Popen([executable, "app-server", "--listen", "stdio://"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=_environment(dict(os.environ), home))
            assert process.stdout is not None
            events: queue.Queue[object] = queue.Queue()
            threading.Thread(target=_pump, args=(process.stdout, events), daemon=True).start()
            requests: dict[object, str] = {}
            _send(process, validator, requests, {"id": "initialize", "method": "initialize", "params": {"capabilities": {"experimentalApi": False}, "clientInfo": {"name": "orbita-m0-recovery", "version": "0.0.0-throwaway"}}})
            while True:
                message = _receive(events, deadline)
                if validator.server(message, requests) is None and message.get("id") == "initialize":
                    _send(process, validator, requests, {"method": "initialized"})
                    return process, events, requests

        first, events, requests = connect()
        _send(first, validator, requests, {"id": "thread-start", "method": "thread/start", "params": {"approvalPolicy": "never", "cwd": str(project), "ephemeral": True, "sandbox": "read-only"}})
        thread_id: str | None = None; turn_id: str | None = None; completed = False; text_seen = False
        while not completed:
            message = _receive(events, deadline); method = validator.server(message, requests)
            if method is None and message.get("id") == "thread-start":
                thread = message["result"].get("thread")  # type: ignore[index]
                thread_id = thread.get("id") if isinstance(thread, dict) else None
                if not isinstance(thread_id, str): raise LiveRecoveryFailure("missingThreadIdentity")
                _send(first, validator, requests, {"id": "turn-start", "method": "turn/start", "params": {"threadId": thread_id, "input": [{"type": "text", "text": ROOT_PROMPT, "text_elements": []}]}})
            elif method is None and message.get("id") == "turn-start":
                turn = message["result"].get("turn")  # type: ignore[index]
                turn_id = turn.get("id") if isinstance(turn, dict) else None
                if not isinstance(turn_id, str): raise LiveRecoveryFailure("missingTurnIdentity")
            elif method == "item/completed" and ROOT_SENTINEL in json.dumps(message): text_seen = True
            elif method == "turn/completed" and isinstance(message.get("params"), dict):
                turn = message["params"].get("turn")  # type: ignore[index]
                completed = isinstance(turn, dict) and turn.get("id") == turn_id and turn.get("status") == "completed"
        if not text_seen or thread_id is None or turn_id is None: raise LiveRecoveryFailure("rootOutcomeNotObserved")
        observed_root_id = thread_id
        _stop(first); first = None
        second, events, requests = connect()
        responses: dict[str, dict[str, object]] = {}
        for request in build_recovery_requests(thread_id): _send(second, validator, requests, request)
        while len(responses) < len(READ_METHODS):
            message = _receive(events, deadline); method = validator.server(message, requests)
            if method is None and isinstance(message.get("id"), str) and message["id"] in requests:
                responses[requests[message["id"]]] = message["result"]  # type: ignore[index]
            elif method is not None and "id" in message: raise LiveRecoveryFailure("unexpectedServerRequest")
        recovered = {"thread": responses["thread/read"].get("thread"), "turns": responses["thread/turns/list"].get("turns", []), "items": responses["thread/items/list"].get("items", [])}
        projection = project_recovery({"rootId": thread_id, "turnId": turn_id}, recovered)
    except (LiveRecoveryFailure, subprocess.CalledProcessError) as error:
        failure = error.category if isinstance(error, LiveRecoveryFailure) else "subprocessFailed"
    finally:
        if first is not None: _stop(first)
        if second is not None: _stop(second)
        if root is not None: shutil.rmtree(root, ignore_errors=True)
    if projection is None and failure is not None:
        projection = {"gaps": [{"kind": "recoveryUnavailable", "rootId": "<unknown>"}], "history": {"itemCount": 0, "turnCount": 0}, "outcome": {"status": "unknown", "source": "gap"}, "roots": []}
    artifact = {"contract": {"stableBundleSha256": contract_bundle_sha256}, "fixtureSchemaVersion": 1, "outcome": {"failure": failure, "success": failure is None}, "projection": _sanitize_projection(projection, observed_root_id), "runtime": {"cliVersion": PINNED_VERSION}, "scenario": "fresh-connection-read-only-recovery"}
    _sanitize_write(output, artifact)
    return failure is None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-live-recovery", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    arguments = parser.parse_args(argv)
    if not arguments.confirm_live_recovery or arguments.timeout_seconds <= 0:
        return 2
    return 0 if run_live_recovery(arguments.output, arguments.timeout_seconds) else 1


if __name__ == "__main__":
    raise SystemExit(main())
