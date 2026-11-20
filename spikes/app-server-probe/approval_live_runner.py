#!/usr/bin/env python3
"""Explicit human-gated M0 command-approval experiment.

This is a throwaway probe, not production approval code. It starts a pinned
public App Server only after an explicit command-line opt-in. No model is run
by importing this module or running its offline unit tests.
"""

from __future__ import annotations

import argparse
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
from typing import Any, Callable

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError


PINNED_VERSION = "codex-cli 0.170.0"
APPROVAL_METHOD = "item/commandExecution/requestApproval"
RESOLVED_METHOD = "serverRequest/resolved"
SAFE_COMMAND = "echo ORBITA_APPROVAL_ACCEPTED"
SAFE_SENTINEL = "ORBITA_APPROVAL_ACCEPTED"
SAFE_PROMPT = (
    "In the disposable project, request an ordinary command approval for exactly "
    "`echo ORBITA_APPROVAL_ACCEPTED`. Execute that exact command only if the user approves. "
    "Do not run any other command. Do not read or write files. Do not use network, MCP, plugins, "
    "or subagents. Do not use a session, policy, automatic, guardian, or humanCommand approval."
)
CHILD_ENV_ALLOWLIST = {
    "APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA", "PATH", "PATHEXT",
    "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "SYSTEMDRIVE",
    "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE", "WINDIR",
}


class LiveApprovalFailure(RuntimeError):
    """A bounded machine-readable failure for the live experiment."""


def build_child_environment(parent: dict[str, str], codex_home: Path) -> dict[str, str]:
    environment = {key: value for key, value in parent.items() if key.upper() in CHILD_ENV_ALLOWLIST}
    environment["CODEX_HOME"] = str(codex_home)
    return environment


class LiveApprovalSchemaValidator:
    def __init__(self, schema_dir: Path) -> None:
        def load(name: str) -> Draft7Validator:
            return Draft7Validator(json.loads((schema_dir / name).read_text(encoding="utf-8")))

        self.client_request = load("ClientRequest.json")
        self.client_notification = load("ClientNotification.json")
        self.server_request = load("ServerRequest.json")
        self.server_notification = load("ServerNotification.json")
        self.response = load("JSONRPCResponse.json")
        self.command_response = load("CommandExecutionRequestApprovalResponse.json")
        self.response_results = {
            "initialize": load("v1/InitializeResponse.json"),
            "thread/start": load("v2/ThreadStartResponse.json"),
            "turn/start": load("v2/TurnStartResponse.json"),
        }

    @staticmethod
    def _check(validator: Draft7Validator, value: object, category: str = "invalidContractMessage") -> None:
        try:
            validator.validate(value)
        except ValidationError as error:
            raise LiveApprovalFailure(category) from error

    def validate_client(self, message: dict[str, object]) -> None:
        self._check(self.client_request if "id" in message else self.client_notification, message)

    def validate_approval_response(self, message: dict[str, object]) -> None:
        self._check(self.response, message)
        result = message.get("result")
        if not isinstance(result, dict):
            raise LiveApprovalFailure("invalidApprovalResponse")
        self._check(self.command_response, result, "invalidApprovalResponse")

    def validate_server(self, message: dict[str, object], requests: dict[object, str]) -> str | None:
        method = message.get("method")
        if isinstance(method, str):
            self._check(self.server_request if "id" in message else self.server_notification, message)
            return method
        request_method = requests.get(message.get("id"))
        if request_method is None:
            raise LiveApprovalFailure("uncorrelatedServerResponse")
        self._check(self.response, message)
        if "error" in message:
            raise LiveApprovalFailure("requestFailed")
        result = message.get("result")
        if not isinstance(result, dict):
            raise LiveApprovalFailure("invalidContractMessage")
        result_validator = self.response_results.get(request_method)
        if result_validator is None:
            raise LiveApprovalFailure("unsupportedClientRequest")
        self._check(result_validator, result)
        return None


def build_one_shot_response(request_id: object, decision: str) -> dict[str, object]:
    if decision not in {"accept", "decline"}:
        raise LiveApprovalFailure("unsupportedOperatorDecision")
    return {"id": request_id, "result": {"decision": decision}}


def is_matching_resolution(params: dict[str, object], approval: dict[str, object]) -> bool:
    return params.get("requestId") == approval.get("requestId") and params.get("threadId") == approval.get("threadId")


def safe_display_context(params: dict[str, object]) -> dict[str, object]:
    """Return only the contract context needed for this fixed synthetic action."""
    return {
        "approvalId": "<APPROVAL_1>" if params.get("approvalId") is not None else None,
        "command": params.get("command"),
        "cwd": "<DISPOSABLE_PROJECT>",
        "itemId": "<ITEM_1>",
        "kind": params.get("kind", "command"),
        "reason": None,
        "threadId": "<THREAD_1>",
        "turnId": "<TURN_1>",
    }


def operator_decision_after_display(
    context: dict[str, object], *, display: Callable[[str], None] = print, read_input: Callable[[str], str] = input
) -> str:
    display("Approval context (sanitized): " + json.dumps(context, sort_keys=True))
    decision = read_input("Type exactly accept or decline to send that one-shot decision; press Enter to abort: ").strip()
    if decision not in {"accept", "decline"}:
        raise LiveApprovalFailure("operatorDecisionRequired")
    return decision


def _generate_stable_schema(schema_dir: Path, executable: str) -> None:
    subprocess.run(
        [executable, "app-server", "generate-json-schema", "--out", str(schema_dir)],
        text=True,
        capture_output=True,
        check=True,
    )


def _read_protocol_lines(stream: Any, events: queue.Queue[object]) -> None:
    try:
        for line in stream:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise LiveApprovalFailure("nonObjectProtocolMessage")
            events.put(value)
        events.put(LiveApprovalFailure("protocolEof"))
    except Exception:
        events.put(LiveApprovalFailure("invalidProtocolMessage"))


def _receive(events: queue.Queue[object], deadline: float) -> dict[str, object]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LiveApprovalFailure("deadlineExceeded")
    try:
        value = events.get(timeout=remaining)
    except queue.Empty as error:
        raise LiveApprovalFailure("deadlineExceeded") from error
    if isinstance(value, LiveApprovalFailure):
        raise value
    if not isinstance(value, dict):
        raise LiveApprovalFailure("invalidProtocolMessage")
    return value


def _send(process: subprocess.Popen[str], message: dict[str, object]) -> None:
    if process.stdin is None:
        raise LiveApprovalFailure("processStdinUnavailable")
    try:
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as error:
        raise LiveApprovalFailure("processWriteFailed") from error


def _event_thread_turn(message: dict[str, object]) -> tuple[str | None, str | None]:
    params = message.get("params")
    if not isinstance(params, dict):
        return None, None
    thread_id = params.get("threadId")
    turn_id = params.get("turnId")
    turn = params.get("turn")
    if isinstance(turn, dict):
        turn_id = turn.get("id")
    return thread_id if isinstance(thread_id, str) else None, turn_id if isinstance(turn_id, str) else None


def _contains_exact_sentinel(value: object) -> bool:
    if isinstance(value, str):
        return value == SAFE_SENTINEL
    if isinstance(value, list):
        return any(_contains_exact_sentinel(child) for child in value)
    if isinstance(value, dict):
        return any(_contains_exact_sentinel(child) for child in value.values())
    return False


def _assert_exact_approval(params: dict[str, object], project: Path, thread_id: str, turn_id: str) -> dict[str, object]:
    if (
        params.get("kind", "command") != "command"
        or params.get("command") != SAFE_COMMAND
        or params.get("threadId") != thread_id
        or params.get("turnId") != turn_id
        or not isinstance(params.get("itemId"), str)
        or params.get("cwd") != str(project)
        or params.get("reason") is not None
        or params.get("networkApprovalContext") is not None
        or params.get("proposedExecpolicyAmendment") is not None
        or params.get("proposedNetworkPolicyAmendments") is not None
    ):
        raise LiveApprovalFailure("unexpectedApprovalContext")
    return safe_display_context(params)


def _sanitized_result(
    *, decision: str | None, approval_seen: bool, resolution_seen: bool, sentinel_seen: bool,
    terminal_status: str | None, failure: str | None
) -> dict[str, object]:
    outcome: dict[str, object] = {
        "approvalObserved": approval_seen,
        "decision": decision,
        "resolutionObserved": resolution_seen,
        "sentinelObserved": sentinel_seen,
        "terminalStatus": terminal_status,
        "success": failure is None,
    }
    if failure is not None:
        outcome["failure"] = failure
    return {
        "fixtureSchemaVersion": 1,
        "outcome": outcome,
        "runtime": PINNED_VERSION,
        "scenario": "human-gated-ordinary-command-approval",
        "sanitation": {
            "omitted": ["rawProtocol", "paths", "requestIds", "threadIds", "turnIds", "itemIds", "reason"],
            "policyVersion": 1,
        },
        "surfaceClassification": {APPROVAL_METHOD: "stable", RESOLVED_METHOD: "stable"},
    }


def _write_sanitized_output(path: Path, artifact: dict[str, object]) -> None:
    serialized = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    forbidden = re.compile(r"bearer\s+|sk-[A-Za-z0-9_-]{8,}|[A-Za-z]:\\(?:Users|python)\\|/home/", re.IGNORECASE)
    if forbidden.search(serialized):
        raise LiveApprovalFailure("sanitationFailed")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")


def run_live_approval(output: Path, timeout_seconds: int) -> bool:
    """Run one human-gated public-protocol experiment; never called without CLI opt-in."""
    approval_seen = False
    resolution_seen = False
    sentinel_seen = False
    decision: str | None = None
    terminal_status: str | None = None
    failure: str | None = None
    process: subprocess.Popen[str] | None = None
    try:
        executable = shutil.which("codex")
        if executable is None:
            raise LiveApprovalFailure("codexNotFound")
        version = subprocess.run([executable, "--version"], text=True, capture_output=True, check=True).stdout.strip()
        if version != PINNED_VERSION:
            raise LiveApprovalFailure("runtimeVersionMismatch")
        with tempfile.TemporaryDirectory(prefix="orbita-approval-live-") as temp_dir:
            root = Path(temp_dir)
            schema_dir = root / "stable-schema"
            home = root / "isolated-codex-home"
            project = root / "read-only-project"
            home.mkdir()
            project.mkdir()
            subprocess.run(["git", "init", "--quiet"], cwd=project, text=True, capture_output=True, check=True)
            _generate_stable_schema(schema_dir, executable)
            validator = LiveApprovalSchemaValidator(schema_dir)
            process = subprocess.Popen(
                [executable, "app-server", "--listen", "stdio://"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", env=build_child_environment(dict(os.environ), home),
            )
            assert process.stdout is not None
            events: queue.Queue[object] = queue.Queue()
            threading.Thread(target=_read_protocol_lines, args=(process.stdout, events), daemon=True).start()
            deadline = time.monotonic() + timeout_seconds
            requests: dict[object, str] = {}

            initialize = {"id": "initialize-approval", "method": "initialize", "params": {"capabilities": {"experimentalApi": False}, "clientInfo": {"name": "orbita-m0-approval-probe", "version": "0.0.0-throwaway"}}}
            validator.validate_client(initialize)
            requests[initialize["id"]] = initialize["method"]
            _send(process, initialize)
            initialized = {"method": "initialized"}
            thread_id: str | None = None
            turn_id: str | None = None
            approval: dict[str, object] | None = None
            _send_after_init = False

            while terminal_status is None or not resolution_seen:
                message = _receive(events, deadline)
                method = validator.validate_server(message, requests)
                if method is None:
                    response_to = requests[message["id"]]
                    if response_to == "initialize" and not _send_after_init:
                        validator.validate_client(initialized)
                        _send(process, initialized)
                        thread_start = {"id": "thread-start-approval", "method": "thread/start", "params": {"approvalPolicy": "on-request", "approvalsReviewer": "user", "cwd": str(project), "ephemeral": True, "sandbox": "read-only"}}
                        validator.validate_client(thread_start)
                        requests[thread_start["id"]] = thread_start["method"]
                        _send(process, thread_start)
                        _send_after_init = True
                    elif response_to == "thread/start":
                        result = message["result"]
                        assert isinstance(result, dict)
                        thread = result.get("thread")
                        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
                            raise LiveApprovalFailure("missingThreadIdentity")
                        thread_id = thread["id"]
                        turn_start = {"id": "turn-start-approval", "method": "turn/start", "params": {"threadId": thread_id, "approvalPolicy": "on-request", "approvalsReviewer": "user", "sandboxPolicy": {"type": "readOnly", "networkAccess": False}, "input": [{"type": "text", "text": SAFE_PROMPT, "text_elements": []}]}}
                        validator.validate_client(turn_start)
                        requests[turn_start["id"]] = turn_start["method"]
                        _send(process, turn_start)
                    elif response_to == "turn/start":
                        result = message["result"]
                        assert isinstance(result, dict)
                        turn = result.get("turn")
                        if not isinstance(turn, dict) or not isinstance(turn.get("id"), str) or not turn["id"]:
                            raise LiveApprovalFailure("missingTurnIdentity")
                        turn_id = turn["id"]
                    continue

                if method == APPROVAL_METHOD:
                    params = message.get("params")
                    if not isinstance(params, dict) or thread_id is None or turn_id is None or approval is not None:
                        raise LiveApprovalFailure("unexpectedApprovalContext")
                    context = _assert_exact_approval(params, project, thread_id, turn_id)
                    approval = {"requestId": message.get("id"), "threadId": thread_id, "turnId": turn_id, "itemId": params["itemId"]}
                    approval_seen = True
                    decision = operator_decision_after_display(context)
                    response = build_one_shot_response(approval["requestId"], decision)
                    validator.validate_approval_response(response)
                    _send(process, response)
                    continue

                if method == RESOLVED_METHOD:
                    params = message.get("params")
                    if not isinstance(params, dict) or approval is None or not is_matching_resolution(params, approval):
                        raise LiveApprovalFailure("mismatchedResolution")
                    resolution_seen = True
                    continue

                if "id" in message:
                    # Only the one ordinary command-approval request is in scope.
                    # MCP, file, permission, question, and future request surfaces
                    # are not silently ignored or routed through this human gate.
                    raise LiveApprovalFailure("unexpectedServerRequest")

                event_thread, event_turn = _event_thread_turn(message)
                if event_thread == thread_id and event_turn == turn_id:
                    if _contains_exact_sentinel(message):
                        sentinel_seen = True
                    if method == "turn/completed":
                        params = message.get("params")
                        turn = params.get("turn") if isinstance(params, dict) else None
                        if not isinstance(turn, dict) or not isinstance(turn.get("status"), str):
                            raise LiveApprovalFailure("invalidTerminalOutcome")
                        terminal_status = turn["status"]

            if not approval_seen:
                raise LiveApprovalFailure("approvalNotObserved")
            if decision == "accept" and (not sentinel_seen or terminal_status != "completed"):
                raise LiveApprovalFailure("acceptOutcomeNotObserved")
            if decision == "decline" and sentinel_seen:
                raise LiveApprovalFailure("declinedCommandExecuted")
    except (LiveApprovalFailure, subprocess.CalledProcessError) as error:
        failure = error.args[0] if isinstance(error, LiveApprovalFailure) else "subprocessFailed"
    finally:
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
        _write_sanitized_output(output, _sanitized_result(
            decision=decision, approval_seen=approval_seen, resolution_seen=resolution_seen,
            sentinel_seen=sentinel_seen, terminal_status=terminal_status, failure=failure,
        ))
    return failure is None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-live-approval", action="store_true", help="required before any App Server process can start")
    parser.add_argument("--output", required=True, type=Path, help="explicit path for one sanitized result")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if not arguments.confirm_live_approval:
        return 2
    if arguments.timeout_seconds <= 0:
        return 2
    return 0 if run_live_approval(arguments.output, arguments.timeout_seconds) else 1


if __name__ == "__main__":
    raise SystemExit(main())
