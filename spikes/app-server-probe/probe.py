#!/usr/bin/env python3
"""Throwaway M0 probe for the public Codex App Server boundary."""

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
SURFACES = ("initialize", "initialized", "thread/start", "turn/start")
LIVE_PROMPT = "Reply with exactly: ORBITA_M0_OK. Do not use tools."
LIVE_SENTINEL = "ORBITA_M0_OK"
CHILD_ENV_ALLOWLIST = {
    "APPDATA", "CODEX_HOME", "COMSPEC", "HOMEDRIVE", "HOMEPATH",
    "LOCALAPPDATA", "PATH", "PATHEXT", "PROGRAMDATA", "PROGRAMFILES",
    "PROGRAMFILES(X86)", "PROGRAMW6432", "SYSTEMDRIVE", "SYSTEMROOT",
    "TEMP", "TMP", "USERPROFILE", "WINDIR",
}
REQUIRED_LIVE_SURFACES = {
    "initialize", "initialized", "thread/start", "turn/start", "turn/started",
    "item/agentMessage/delta", "item/completed", "turn/completed",
}


def build_child_environment(parent: dict[str, str]) -> dict[str, str]:
    """Return the minimal non-credential environment needed by the local runtime."""
    return {key: value for key, value in parent.items() if key.upper() in CHILD_ENV_ALLOWLIST}


def codex_executable() -> str:
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("codex executable was not found on PATH")
    return executable


def run_checked(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        text=True,
        capture_output=True,
        check=True,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runtime_record(version: str, executable: Path) -> dict[str, object]:
    native_candidates = sorted(
        (executable.parent / "node_modules" / "@openai" / "codex" / "node_modules" / "@openai").glob(
            "codex-win32-*/vendor/*/bin/codex.exe"
        )
    )
    if len(native_candidates) != 1:
        raise RuntimeError("could not resolve exactly one native Codex executable")
    features_output = subprocess.run(
        [str(executable), "features", "list"],
        text=True,
        capture_output=True,
        check=True,
        env=build_child_environment(dict(os.environ)),
    ).stdout
    feature_snapshot: list[dict[str, object]] = []
    for line in features_output.splitlines():
        match = re.fullmatch(r"(\S+)\s{2,}(.+?)\s{2,}(true|false)", line.strip())
        if match is None:
            raise RuntimeError("unexpected codex features list format")
        feature_snapshot.append(
            {"enabled": match.group(3) == "true", "name": match.group(1), "stage": match.group(2)}
        )
    config_record = {
        "configOverrides": [],
        "featureSnapshot": feature_snapshot,
        "protocolCapabilities": {"experimentalApi": False},
    }
    return {
        "cliVersion": version,
        "configOverrides": [],
        "effectiveConfigSha256": canonical_digest(config_record),
        "featureSnapshot": feature_snapshot,
        "launcherSha256": sha256(executable),
        "nativeExecutableSha256": sha256(native_candidates[0]),
        "protocolCapabilities": {"experimentalApi": False},
        "transport": "stdio://",
    }


def write_json(output: Path, value: object) -> None:
    forbidden_key = re.compile(r"(authorization|password|cookie|credential|secret|(?:^|_)token(?:$|_))", re.IGNORECASE)
    forbidden_value = re.compile(
        r"(Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|[A-Za-z]:\\(?:Users|python)\\|/home/|seeded-secret)",
        re.IGNORECASE,
    )

    def scan(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if forbidden_key.search(str(key)):
                    raise ValueError("artifact contains a forbidden key")
                scan(child)
        elif isinstance(node, list):
            for child in node:
                scan(child)
        elif isinstance(node, str) and forbidden_value.search(node) and not node.startswith("<"):
            raise ValueError("artifact contains a forbidden value")

    scan(value)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_digest(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def remove_disposable_directory(path: Path) -> None:
    for attempt in range(20):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def method_names(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        method = value.get("properties", {}).get("method", {})
        if isinstance(method, dict):
            found.update(item for item in method.get("enum", []) if isinstance(item, str))
        for child in value.values():
            found.update(method_names(child))
    elif isinstance(value, list):
        for child in value:
            found.update(method_names(child))
    return found


class ContractMessageError(Exception):
    def __init__(self, category: str, method: str | None = None) -> None:
        super().__init__(category)
        self.category = category
        self.method = method


class GeneratedContractValidator:
    def __init__(self, schema_dir: Path) -> None:
        def load(relative: str) -> Draft7Validator:
            return Draft7Validator(json.loads((schema_dir / relative).read_text(encoding="utf-8")))

        self.client_request = load("ClientRequest.json")
        self.client_notification = load("ClientNotification.json")
        self.server_notification = load("ServerNotification.json")
        self.server_request = load("ServerRequest.json")
        self.response = load("JSONRPCResponse.json")
        self.error = load("JSONRPCError.json")
        self.response_results = {
            "initialize": load("v1/InitializeResponse.json"),
            "thread/start": load("v2/ThreadStartResponse.json"),
            "turn/start": load("v2/TurnStartResponse.json"),
        }
        method_schemas = [
            json.loads((schema_dir / name).read_text(encoding="utf-8"))
            for name in ("ClientRequest.json", "ClientNotification.json", "ServerNotification.json", "ServerRequest.json")
        ]
        self.stable_methods = set().union(*(method_names(schema) for schema in method_schemas))

    @staticmethod
    def check(validator: Draft7Validator, value: object, method: str | None = None) -> None:
        try:
            validator.validate(value)
        except ValidationError as error:
            raise ContractMessageError("invalidContractMessage", method) from error

    def validate_client(self, message: dict[str, object]) -> str:
        method = message.get("method")
        if not isinstance(method, str):
            raise ContractMessageError("invalidContractMessage")
        if method not in self.stable_methods:
            raise ContractMessageError("unknownSurfaceClassification", method)
        self.check(self.client_request if "id" in message else self.client_notification, message, method)
        return method

    def validate_server(self, message: dict[str, object], requests: dict[object, str]) -> str | None:
        method = message.get("method")
        if isinstance(method, str):
            if method not in self.stable_methods:
                raise ContractMessageError("unknownSurfaceClassification", method)
            self.check(self.server_request if "id" in message else self.server_notification, message, method)
            return method
        request_method = requests.get(message.get("id"))
        if request_method is None:
            raise ContractMessageError("invalidContractMessage")
        if "result" in message:
            self.check(self.response, message, request_method)
            result_validator = self.response_results.get(request_method)
            if result_validator is None:
                raise ContractMessageError("unknownSurfaceClassification", request_method)
            self.check(result_validator, message["result"], request_method)
        elif "error" in message:
            self.check(self.error, message, request_method)
        else:
            raise ContractMessageError("invalidContractMessage", request_method)
        return None


def validate_capture_contract(capture: dict[str, object], validator: GeneratedContractValidator) -> dict[str, str]:
    messages = capture.get("messages")
    if not isinstance(messages, list):
        raise ContractMessageError("invalidCapture")
    requests: dict[object, str] = {}
    observed: set[str] = set()
    for entry in messages:
        if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
            raise ContractMessageError("invalidContractMessage")
        message = entry["message"]
        if entry.get("direction") == "clientToServer":
            method = validator.validate_client(message)
            observed.add(method)
            if "id" in message:
                if message["id"] in requests and requests[message["id"]] != method:
                    raise ContractMessageError("conflictingRequestIdentity", method)
                requests[message["id"]] = method
        elif entry.get("direction") == "serverToClient":
            method = validator.validate_server(message, requests)
            if method is not None:
                observed.add(method)
        else:
            raise ContractMessageError("invalidContractMessage")
    missing = sorted(method for method in observed if method not in validator.stable_methods)
    if missing:
        raise ContractMessageError("unknownSurfaceClassification", missing[0])
    return {method: "stable" for method in sorted(observed)}


def contract_manifest_digest(output_dir: Path) -> tuple[str, int]:
    entries = [
        {
            "path": path.relative_to(output_dir).as_posix(),
            "sha256": sha256(path),
        }
        for path in sorted(output_dir.rglob("*.json"))
    ]
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest(), len(entries)


def generate_contract(output_dir: Path, *, experimental: bool) -> dict[str, object]:
    arguments = [codex_executable(), "app-server", "generate-json-schema"]
    if experimental:
        arguments.append("--experimental")
    arguments.extend(["--out", str(output_dir)])
    run_checked(arguments)

    bundle = output_dir / "codex_app_server_protocol.schemas.json"
    manifest_digest, schema_file_count = contract_manifest_digest(output_dir)
    return {
        "bundleSha256": sha256(bundle),
        "command": [
            "codex",
            "app-server",
            "generate-json-schema",
            *(["--experimental"] if experimental else []),
            "--out",
            "<temporary-directory>",
        ],
        "manifestSha256": manifest_digest,
        "schemaFileCount": schema_file_count,
    }


def capture_contract(output: Path) -> None:
    executable = Path(codex_executable())
    version = run_checked([str(executable), "--version"]).stdout.strip()
    if version != PINNED_VERSION:
        raise RuntimeError(f"expected {PINNED_VERSION!r}, got {version!r}")

    with tempfile.TemporaryDirectory(prefix="orbita-app-server-contract-") as temp_dir:
        root = Path(temp_dir)
        stable_dir = root / "stable"
        experimental_dir = root / "experimental"
        stable = generate_contract(stable_dir, experimental=False)
        experimental = generate_contract(experimental_dir, experimental=True)

        stable_methods = method_names(
            json.loads((stable_dir / "ClientRequest.json").read_text(encoding="utf-8"))
        ) | method_names(
            json.loads((stable_dir / "ClientNotification.json").read_text(encoding="utf-8"))
        )
        missing = set(SURFACES) - stable_methods
        if missing:
            raise RuntimeError(f"pinned stable contract is missing: {sorted(missing)}")

    result = {
        "contractSchemaVersion": 1,
        "runtime": runtime_record(version, executable),
        "generatedContract": {
            "experimental": experimental,
            "stable": stable,
        },
        "surfaceClassification": {surface: "stable" for surface in SURFACES},
        "digestStrategy": {
            "algorithm": "sha256",
            "contractManifestEncoding": "canonical-json-utf8-lf",
            "contractManifestEntry": ["path", "sha256"],
        },
    }
    write_json(output, result)


def read_json_line(stream: object, messages: queue.Queue[object]) -> None:
    try:
        line = stream.readline()  # type: ignore[attr-defined]
        messages.put(json.loads(line) if line else RuntimeError("app-server closed stdout"))
    except Exception as error:
        messages.put(error)


def receive_response(stream: object, request_id: str) -> dict[str, object]:
    deadline_messages: queue.Queue[object] = queue.Queue()
    while True:
        reader = threading.Thread(
            target=read_json_line,
            args=(stream, deadline_messages),
            daemon=True,
        )
        reader.start()
        message = deadline_messages.get(timeout=10)
        if isinstance(message, Exception):
            raise message
        if not isinstance(message, dict):
            raise RuntimeError("app-server stdout message was not a JSON object")
        if message.get("id") != request_id:
            continue
        if "error" in message or not isinstance(message.get("result"), dict):
            raise RuntimeError(f"request {request_id!r} failed")
        return message


def initialize(output: Path) -> None:
    executable = Path(codex_executable())
    version = run_checked([str(executable), "--version"]).stdout.strip()
    if version != PINNED_VERSION:
        raise RuntimeError(f"expected {PINNED_VERSION!r}, got {version!r}")

    request = {
        "id": "initialize-1",
        "method": "initialize",
        "params": {
            "capabilities": {"experimentalApi": False},
            "clientInfo": {
                "name": "orbita-m0-probe",
                "title": "Orbita M0 probe",
                "version": "0.0.0-throwaway",
            },
        },
    }
    initialized = {"method": "initialized"}
    with tempfile.TemporaryDirectory(
        prefix="orbita-m0-live-", ignore_cleanup_errors=True
    ) as temp_dir:
        temp_root = Path(temp_dir)
        probe_home = temp_root / "codex-home"
        project = temp_root / "project"
        probe_home.mkdir()
        project.mkdir()
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=project,
            text=True,
            capture_output=True,
            check=True,
        )
        process_environment = dict(os.environ)
        process_environment["CODEX_HOME"] = str(probe_home)
        process = subprocess.Popen(
            [str(executable), "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=build_child_environment(process_environment),
        )
        try:
            assert process.stdin is not None
            assert process.stdout is not None
            process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
            process.stdin.flush()
            response = receive_response(process.stdout, request["id"])

            process.stdin.write(json.dumps(initialized, separators=(",", ":")) + "\n")
            process.stdin.flush()

            thread_request = {
                "id": "thread-start-1",
                "method": "thread/start",
                "params": {"cwd": str(project.resolve())},
            }
            process.stdin.write(json.dumps(thread_request, separators=(",", ":")) + "\n")
            process.stdin.flush()
            thread_response = receive_response(process.stdout, thread_request["id"])
            thread = thread_response["result"].get("thread")
            if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
                raise RuntimeError("thread/start response did not contain a non-empty thread id")
        finally:
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

    remove_disposable_directory(temp_root)

    normalized_response = json.loads(json.dumps(response))
    normalized_response["result"]["codexHome"] = "<redacted-absolute-path>"
    normalized_response["result"]["userAgent"] = "<SERVER_USER_AGENT>"
    normalized_thread_request = json.loads(json.dumps(thread_request))
    normalized_thread_request["params"]["cwd"] = "<DISPOSABLE_PROJECT>"
    normalized_thread_response = {
        "id": thread_response["id"],
        "result": {"thread": {"id": "<THREAD_1>"}},
    }
    fixture = {
        "fixtureSchemaVersion": 1,
        "runtime": runtime_record(version, executable),
        "transcript": [
            {"direction": "clientToServer", "message": request},
            {"direction": "serverToClient", "message": normalized_response},
            {"direction": "clientToServer", "message": initialized},
            {"direction": "clientToServer", "message": normalized_thread_request},
            {"direction": "serverToClient", "message": normalized_thread_response},
        ],
        "outcome": {
            "classification": "directly observed",
            "initializeResponseId": request["id"],
            "rootThreadObserved": True,
            "threadResponseId": thread_request["id"],
        },
    }
    write_json(output, fixture)


def normalize_turn_capture(capture: dict[str, object]) -> tuple[dict[str, object], bool]:
    metadata = capture.get("runMetadata")
    messages = capture.get("messages")
    if not isinstance(metadata, dict) or not isinstance(messages, list):
        return {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidCapture", "success": False}}, False

    requests: dict[object, str] = {}
    thread_id: str | None = None
    turn_id: str | None = None
    thread_request_matches = False
    turn_started = False
    delta_item_ids: set[str] = set()
    matching_delta = False
    final_agent_text: str | None = None
    final_agent_item_id: str | None = None
    terminal_status: str | None = None

    for entry in messages:
        if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
            return {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidContractMessage", "success": False}}, False
        message = entry["message"]
        method = message.get("method")
        params = message.get("params")
        if method == "turn/completed":
            turn = params.get("turn") if isinstance(params, dict) else None
            if not isinstance(turn, dict) or not isinstance(turn.get("status"), str):
                return {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidContractMessage", "success": False}}, False
        if entry.get("direction") == "serverToClient" and method in ("item/started", "item/completed") and isinstance(params, dict):
            item = params.get("item")
            item_type = item.get("type") if isinstance(item, dict) else None
            if item_type in {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall", "webSearch", "imageGeneration"}:
                return {"fixtureSchemaVersion": 1, "outcome": {"failure": "toolActivityObserved", "success": False}}, False

    thread_starts = [
        entry["message"]
        for entry in messages
        if entry.get("direction") == "clientToServer"
        and entry["message"].get("method") == "thread/start"
    ]
    if len(thread_starts) != 1 or not isinstance(thread_starts[0].get("params"), dict):
        return {"fixtureSchemaVersion": 1, "outcome": {"failure": "unsafeThreadStartParams", "success": False}}, False
    source_thread_params = thread_starts[0]["params"]
    if not (
        source_thread_params.get("approvalPolicy") == "never"
        and source_thread_params.get("sandbox") == "read-only"
        and source_thread_params.get("ephemeral") is True
        and isinstance(source_thread_params.get("cwd"), str)
        and bool(source_thread_params["cwd"])
    ):
        return {"fixtureSchemaVersion": 1, "outcome": {"failure": "unsafeThreadStartParams", "success": False}}, False

    turn_starts = [
        entry["message"]
        for entry in messages
        if entry.get("direction") == "clientToServer"
        and entry["message"].get("method") == "turn/start"
    ]
    expected_input = [{"text": LIVE_PROMPT, "text_elements": [], "type": "text"}]
    if (
        len(turn_starts) != 1
        or not isinstance(turn_starts[0].get("params"), dict)
        or turn_starts[0]["params"].get("input") != expected_input
    ):
        return {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidTurnStartParams", "success": False}}, False

    for entry in messages:
        if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
            continue
        message = entry["message"]
        if entry.get("direction") == "clientToServer" and isinstance(message.get("method"), str):
            if "id" in message:
                requests[message["id"]] = message["method"]
            continue
        if entry.get("direction") != "serverToClient":
            continue
        response_to = requests.get(message.get("id"))
        result = message.get("result")
        if response_to == "thread/start" and isinstance(result, dict):
            thread = result.get("thread")
            candidate = thread.get("id") if isinstance(thread, dict) else None
            if isinstance(candidate, str) and candidate:
                thread_id = candidate
        elif response_to == "turn/start" and isinstance(result, dict):
            turn = result.get("turn")
            candidate = turn.get("id") if isinstance(turn, dict) else None
            if isinstance(candidate, str) and candidate:
                turn_id = candidate

    if thread_id is not None and turn_id is not None:
        for entry in messages:
            if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
                continue
            message = entry["message"]
            direction = entry.get("direction")
            method = message.get("method")
            params = message.get("params")
            if direction == "clientToServer" and method == "turn/start" and isinstance(params, dict):
                thread_request_matches = params.get("threadId") == thread_id
            if direction != "serverToClient" or not isinstance(params, dict):
                continue
            matching_ids = params.get("threadId") == thread_id and (
                params.get("turnId") == turn_id
                or (isinstance(params.get("turn"), dict) and params["turn"].get("id") == turn_id)
            )
            if not matching_ids:
                continue
            if method == "turn/started":
                turn_started = True
            elif method == "item/agentMessage/delta":
                delta_item_id = params.get("itemId")
                if isinstance(delta_item_id, str):
                    delta_item_ids.add(delta_item_id)
            elif method == "item/completed":
                item = params.get("item")
                if isinstance(item, dict) and item.get("type") == "agentMessage" and isinstance(item.get("text"), str):
                    final_agent_text = item["text"].strip()
                    candidate_item_id = item.get("id")
                    if isinstance(candidate_item_id, str):
                        final_agent_item_id = candidate_item_id
            elif method == "turn/completed":
                turn = params.get("turn")
                if isinstance(turn, dict) and isinstance(turn.get("status"), str):
                    terminal_status = turn["status"]

    matching_delta = final_agent_item_id is not None and final_agent_item_id in delta_item_ids
    failure: str | None = None
    if thread_id is None:
        failure = "missingThreadIdentity"
    elif turn_id is None or not thread_request_matches:
        failure = "missingTurnCorrelation"
    elif terminal_status is None:
        failure = "missingMatchingTurnCompleted"
    elif terminal_status != "completed":
        failure = "terminalStatusNotCompleted"
    elif not turn_started or not matching_delta:
        failure = "missingStreamingEvidence"
    elif final_agent_text != LIVE_SENTINEL:
        failure = "unexpectedFinalAgentText"

    if failure is not None:
        return {
            "fixtureSchemaVersion": 1,
            "outcome": {"failure": failure, "success": False},
        }, False

    runtime = metadata.get("runtime")
    contract = metadata.get("contract")
    if not isinstance(runtime, dict) or not isinstance(contract, dict):
        return {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidRunMetadata", "success": False}}, False

    source_classification = metadata.get("surfaceClassification")
    if not isinstance(source_classification, dict):
        return {"fixtureSchemaVersion": 1, "outcome": {"failure": "missingSurfaceClassification", "success": False}}, False
    surface_classification = dict(source_classification)
    projection = {
        "contract": contract,
        "correlation": {"rootThreadObserved": True, "turnObserved": True},
        "evidenceKinds": ["agentMessageDelta", "turnCompleted", "turnStarted"],
        "runtime": runtime,
        "surfaceClassification": surface_classification,
        "terminal": {
            "finalAgentText": LIVE_SENTINEL,
            "method": "turn/completed",
            "status": "completed",
        },
    }
    sanitized_transcript: list[dict[str, object]] = []
    for ordinal, entry in enumerate(messages):
        if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
            continue
        message = entry["message"]
        method = message.get("method")
        direction = entry.get("direction")
        record: dict[str, object] | None = None
        if direction == "clientToServer" and method in SURFACES:
            record = {"direction": direction, "method": method, "ordinal": ordinal}
            if method == "thread/start":
                record["params"] = {
                    "approvalPolicy": source_thread_params["approvalPolicy"],
                    "cwd": "<DISPOSABLE_PROJECT>",
                    "ephemeral": source_thread_params["ephemeral"],
                    "sandbox": source_thread_params["sandbox"],
                }
            elif method == "turn/start":
                record["params"] = {
                    "prompt": turn_starts[0]["params"]["input"][0]["text"],
                    "threadId": "<THREAD_1>",
                }
        elif direction == "clientToServer" and method == "initialized":
            record = {"direction": direction, "method": method, "ordinal": ordinal}
        elif direction == "serverToClient" and requests.get(message.get("id")) in ("initialize", "thread/start", "turn/start"):
            response_to = requests[message.get("id")]
            record = {"direction": direction, "ordinal": ordinal, "responseTo": response_to}
            if response_to == "thread/start":
                record["threadId"] = "<THREAD_1>"
            elif response_to == "turn/start":
                record["turnId"] = "<TURN_1>"
        elif direction == "serverToClient" and isinstance(message.get("params"), dict):
            params = message["params"]
            matching = params.get("threadId") == thread_id and (
                params.get("turnId") == turn_id
                or (isinstance(params.get("turn"), dict) and params["turn"].get("id") == turn_id)
            )
            if matching and method in ("turn/started", "item/agentMessage/delta", "item/completed", "turn/completed"):
                if method == "item/agentMessage/delta" and params.get("itemId") != final_agent_item_id:
                    continue
                if method == "item/completed":
                    item = params.get("item")
                    if not (
                        isinstance(item, dict)
                        and item.get("id") == final_agent_item_id
                        and item.get("type") == "agentMessage"
                        and isinstance(item.get("text"), str)
                        and item["text"].strip() == LIVE_SENTINEL
                    ):
                        continue
                record = {
                    "direction": direction,
                    "method": method,
                    "ordinal": ordinal,
                    "threadId": "<THREAD_1>",
                    "turnId": "<TURN_1>",
                }
                if method in ("item/agentMessage/delta", "item/completed"):
                    record["itemId"] = "<ITEM_1>"
                if method == "item/completed":
                    record["agentText"] = LIVE_SENTINEL
                if method == "turn/completed":
                    record["status"] = "completed"
        if record is not None:
            sanitized_transcript.append(record)

    outcome = {
        "finalAgentText": LIVE_SENTINEL,
        "rootThreadObserved": True,
        "streamingEvidenceObserved": True,
        "success": True,
        "terminalSignal": "turn/completed",
        "terminalStatus": "completed",
        "turnObserved": True,
    }
    def evidence_indices(predicate: object) -> list[int]:
        return [
            index
            for index, entry in enumerate(sanitized_transcript)
            if predicate(entry)  # type: ignore[operator]
        ]

    evidence_refs = {
        "finalAgentText": evidence_indices(lambda entry: entry.get("method") == "item/completed"),
        "rootThreadObserved": evidence_indices(lambda entry: entry.get("responseTo") == "thread/start"),
        "streamingEvidenceObserved": evidence_indices(lambda entry: entry.get("method") == "item/agentMessage/delta"),
        "terminalSignal": evidence_indices(lambda entry: entry.get("method") == "turn/completed"),
        "terminalStatus": evidence_indices(lambda entry: entry.get("method") == "turn/completed"),
        "turnObserved": evidence_indices(
            lambda entry: entry.get("responseTo") == "turn/start" or entry.get("method") == "turn/started"
        ),
    }
    artifact = {
        "contract": contract,
        "evidenceRefs": evidence_refs,
        "fixtureSchemaVersion": 1,
        "outcome": outcome,
        "probeInputRevision": "live-turn-v1",
        "repeatabilityDigest": canonical_digest(projection),
        "repeatabilityProjection": projection,
        "runtime": runtime,
        "sanitation": {
            "aliased": ["threadId", "turnId", "itemId"],
            "omitted": ["account", "model", "timestamps", "tokenUsage"],
            "policyVersion": 1,
            "replaced": ["codexHome", "cwd", "userAgent"],
        },
        "surfaceClassification": surface_classification,
        "transcript": sanitized_transcript,
    }
    return artifact, True


def normalize_turn_file(input_path: Path, output: Path) -> bool:
    capture = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(capture, dict):
        artifact, success = {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidCapture", "success": False}}, False
    else:
        try:
            with tempfile.TemporaryDirectory(prefix="orbita-m0-validate-") as temp_dir:
                schema_dir = Path(temp_dir) / "stable"
                generated = generate_contract(schema_dir, experimental=False)
                metadata = capture.get("runMetadata")
                contract = metadata.get("contract") if isinstance(metadata, dict) else None
                if not isinstance(contract, dict) or contract.get("stableManifestSha256") != generated["manifestSha256"]:
                    raise ContractMessageError("contractDigestMismatch")
                executable = Path(codex_executable())
                version = run_checked([str(executable), "--version"]).stdout.strip()
                if version != PINNED_VERSION:
                    raise ContractMessageError("runtimeVersionMismatch")
                metadata["runtime"] = runtime_record(version, executable)
                validator = GeneratedContractValidator(schema_dir)
                classification = validate_capture_contract(capture, validator)
                metadata["surfaceClassification"] = classification
            artifact, success = normalize_turn_capture(capture)
        except ContractMessageError as error:
            artifact = {
                "fixtureSchemaVersion": 1,
                "outcome": {"failure": error.category, "success": False},
            }
            if error.category == "unknownSurfaceClassification" and error.method is not None:
                artifact["diagnostics"] = [{"kind": "unknownProtocolMethod", "method": error.method}]
            success = False
    write_json(output, artifact)
    return success


class LiveProbeFailure(Exception):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def pump_protocol_lines(stream: object, events: queue.Queue[object]) -> None:
    try:
        for line in stream:  # type: ignore[union-attr]
            message = json.loads(line)
            if not isinstance(message, dict):
                raise LiveProbeFailure("nonObjectProtocolMessage")
            events.put(message)
        events.put(LiveProbeFailure("protocolEof"))
    except Exception:
        events.put(LiveProbeFailure("invalidProtocolMessage"))


def drain_stream(stream: object) -> None:
    try:
        for _line in stream:  # type: ignore[union-attr]
            pass
    except Exception:
        pass


def receive_live_message(events: queue.Queue[object], deadline: float) -> dict[str, object]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LiveProbeFailure("deadlineExceeded")
    try:
        message = events.get(timeout=remaining)
    except queue.Empty as error:
        raise LiveProbeFailure("deadlineExceeded") from error
    if isinstance(message, LiveProbeFailure):
        raise message
    if not isinstance(message, dict):
        raise LiveProbeFailure("invalidProtocolMessage")
    return message


def send_live_message(
    process: subprocess.Popen[str],
    transcript: list[dict[str, object]],
    message: dict[str, object],
    validator: GeneratedContractValidator,
    requests: dict[object, str],
) -> None:
    method = validator.validate_client(message)
    if "id" in message:
        requests[message["id"]] = method
    if process.stdin is None:
        raise LiveProbeFailure("processStdinUnavailable")
    transcript.append({"direction": "clientToServer", "message": message})
    try:
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as error:
        raise LiveProbeFailure("processWriteFailed") from error


def wait_live_response(
    events: queue.Queue[object],
    transcript: list[dict[str, object]],
    request_id: str,
    deadline: float,
    validator: GeneratedContractValidator,
    requests: dict[object, str],
) -> dict[str, object]:
    while True:
        message = receive_live_message(events, deadline)
        validator.validate_server(message, requests)
        if has_tool_activity(message):
            raise LiveProbeFailure("toolActivityObserved")
        transcript.append({"direction": "serverToClient", "message": message})
        if message.get("id") != request_id:
            continue
        if "error" in message or not isinstance(message.get("result"), dict):
            raise LiveProbeFailure("requestFailed")
        return message


def matching_terminal(message: dict[str, object], thread_id: str, turn_id: str) -> bool:
    if message.get("method") != "turn/completed" or not isinstance(message.get("params"), dict):
        return False
    params = message["params"]
    turn = params.get("turn")
    return (
        params.get("threadId") == thread_id
        and isinstance(turn, dict)
        and turn.get("id") == turn_id
    )


def has_tool_activity(message: dict[str, object]) -> bool:
    method = message.get("method")
    if isinstance(method, str) and any(token in method.lower() for token in ("command", "filechange", "toolcall", "websearch", "applypatch")):
        return True
    params = message.get("params")
    item = params.get("item") if isinstance(params, dict) else None
    item_type = item.get("type") if isinstance(item, dict) else None
    return item_type in {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall", "webSearch", "imageGeneration"}


def pinned_live_metadata(executable: Path, version: str) -> dict[str, object]:
    contract_fixture_path = Path(__file__).resolve().parent / "fixtures" / "contract.json"
    contract_fixture = json.loads(contract_fixture_path.read_text(encoding="utf-8"))
    observed_runtime = runtime_record(version, executable)
    if contract_fixture.get("runtime") != observed_runtime:
        raise LiveProbeFailure("runtimeDoesNotMatchPinnedContract")
    generated = contract_fixture.get("generatedContract")
    if not isinstance(generated, dict):
        raise LiveProbeFailure("invalidPinnedContractFixture")
    stable = generated.get("stable")
    experimental = generated.get("experimental")
    if not isinstance(stable, dict) or not isinstance(experimental, dict):
        raise LiveProbeFailure("invalidPinnedContractFixture")
    return {
        "contract": {
            "experimentalManifestSha256": experimental.get("manifestSha256"),
            "stableManifestSha256": stable.get("manifestSha256"),
        },
        "runtime": observed_runtime,
    }


def live_turn(output: Path, timeout_seconds: float) -> bool:
    if timeout_seconds <= 0:
        write_json(output, {"fixtureSchemaVersion": 1, "outcome": {"failure": "invalidDeadline", "success": False}})
        return False
    executable = Path(codex_executable())
    version = run_checked([str(executable), "--version"]).stdout.strip()
    if version != PINNED_VERSION:
        write_json(output, {"fixtureSchemaVersion": 1, "outcome": {"failure": "runtimeVersionMismatch", "success": False}})
        return False

    try:
        metadata = pinned_live_metadata(executable, version)
    except LiveProbeFailure as error:
        write_json(output, {"fixtureSchemaVersion": 1, "outcome": {"failure": error.category, "success": False}})
        return False

    transcript: list[dict[str, object]] = []
    failure: str | None = None
    temp_root = Path(tempfile.mkdtemp(prefix="orbita-m0-live-turn-"))
    project = temp_root / "project"
    project.mkdir()
    schema_dir = temp_root / "stable-schema"
    generated_contract = generate_contract(schema_dir, experimental=False)
    if generated_contract["manifestSha256"] != metadata["contract"]["stableManifestSha256"]:
        write_json(output, {"fixtureSchemaVersion": 1, "outcome": {"failure": "contractDigestMismatch", "success": False}})
        remove_disposable_directory(temp_root)
        return False
    validator = GeneratedContractValidator(schema_dir)
    request_methods: dict[object, str] = {}
    subprocess.run(["git", "init", "--quiet"], cwd=project, text=True, capture_output=True, check=True)
    process = subprocess.Popen(
        [str(executable), "app-server", "--listen", "stdio://"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=build_child_environment(dict(os.environ)),
    )
    events: queue.Queue[object] = queue.Queue()
    assert process.stdout is not None
    assert process.stderr is not None
    threading.Thread(target=pump_protocol_lines, args=(process.stdout, events), daemon=True).start()
    threading.Thread(target=drain_stream, args=(process.stderr,), daemon=True).start()
    deadline = time.monotonic() + timeout_seconds
    try:
        initialize_request = {
            "id": "initialize-1",
            "method": "initialize",
            "params": {
                "capabilities": {"experimentalApi": False},
                "clientInfo": {
                    "name": "orbita-m0-probe",
                    "title": "Orbita M0 probe",
                    "version": "0.0.0-throwaway",
                },
            },
        }
        send_live_message(process, transcript, initialize_request, validator, request_methods)
        wait_live_response(events, transcript, "initialize-1", deadline, validator, request_methods)
        send_live_message(process, transcript, {"method": "initialized"}, validator, request_methods)

        thread_request = {
            "id": "thread-start-1",
            "method": "thread/start",
            "params": {
                "approvalPolicy": "never",
                "cwd": str(project.resolve()),
                "ephemeral": True,
                "sandbox": "read-only",
            },
        }
        send_live_message(process, transcript, thread_request, validator, request_methods)
        thread_response = wait_live_response(events, transcript, "thread-start-1", deadline, validator, request_methods)
        thread = thread_response["result"].get("thread")
        thread_id = thread.get("id") if isinstance(thread, dict) else None
        if not isinstance(thread_id, str) or not thread_id:
            raise LiveProbeFailure("missingThreadIdentity")

        turn_request = {
            "id": "turn-start-1",
            "method": "turn/start",
            "params": {
                "input": [{"text": LIVE_PROMPT, "text_elements": [], "type": "text"}],
                "threadId": thread_id,
            },
        }
        send_live_message(process, transcript, turn_request, validator, request_methods)
        turn_response = wait_live_response(events, transcript, "turn-start-1", deadline, validator, request_methods)
        turn = turn_response["result"].get("turn")
        turn_id = turn.get("id") if isinstance(turn, dict) else None
        if not isinstance(turn_id, str) or not turn_id:
            raise LiveProbeFailure("missingTurnIdentity")

        already_terminal = any(
            isinstance(entry.get("message"), dict) and matching_terminal(entry["message"], thread_id, turn_id)
            for entry in transcript
            if entry.get("direction") == "serverToClient"
        )
        while not already_terminal:
            message = receive_live_message(events, deadline)
            validator.validate_server(message, request_methods)
            if has_tool_activity(message):
                raise LiveProbeFailure("toolActivityObserved")
            transcript.append({"direction": "serverToClient", "message": message})
            already_terminal = matching_terminal(message, thread_id, turn_id)
    except (LiveProbeFailure, ContractMessageError) as error:
        failure = error.category
    finally:
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
        remove_disposable_directory(temp_root)

    if failure is not None:
        write_json(
            output,
            {
                "fixtureSchemaVersion": 1,
                "outcome": {"failure": failure, "success": False},
                "probeInputRevision": "live-turn-v1",
                "runtime": metadata["runtime"],
            },
        )
        return False

    try:
        metadata["surfaceClassification"] = validate_capture_contract(
            {"runMetadata": metadata, "messages": transcript}, validator
        )
    except ContractMessageError as error:
        write_json(output, {"fixtureSchemaVersion": 1, "outcome": {"failure": error.category, "success": False}})
        return False
    artifact, success = normalize_turn_capture({"runMetadata": metadata, "messages": transcript})
    write_json(output, artifact)
    if success:
        print(f"repeatabilitySha256={artifact['repeatabilityDigest']}")
        print(f"fixture={output.resolve()}")
    return success


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture-contract")
    capture.add_argument("--output", required=True, type=Path)
    initialize_parser = subparsers.add_parser("initialize")
    initialize_parser.add_argument("--output", required=True, type=Path)
    normalize_parser = subparsers.add_parser("normalize-turn")
    normalize_parser.add_argument("--input", required=True, type=Path)
    normalize_parser.add_argument("--output", required=True, type=Path)
    live_parser = subparsers.add_parser("live-turn")
    live_parser.add_argument("--confirm-live-model", action="store_true", required=True)
    live_parser.add_argument("--output", required=True, type=Path)
    live_parser.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "capture-contract":
        capture_contract(arguments.output)
    elif arguments.command == "initialize":
        initialize(arguments.output)
    elif arguments.command == "normalize-turn":
        return 0 if normalize_turn_file(arguments.input, arguments.output) else 1
    elif arguments.command == "live-turn":
        return 0 if live_turn(arguments.output, arguments.timeout_seconds) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
