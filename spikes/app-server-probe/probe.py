#!/usr/bin/env python3
"""Throwaway M0 probe for the public Codex App Server boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


PINNED_VERSION = "codex-cli 0.170.0"
SURFACES = ("initialize", "initialized", "thread/start", "turn/start")


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
    return {
        "cliVersion": version,
        "launcherSha256": sha256(executable),
        "features": {"experimentalApi": False},
        "transport": "stdio://",
    }


def write_json(output: Path, value: object) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
            env=process_environment,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture-contract")
    capture.add_argument("--output", required=True, type=Path)
    initialize_parser = subparsers.add_parser("initialize")
    initialize_parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "capture-contract":
        capture_contract(arguments.output)
    elif arguments.command == "initialize":
        initialize(arguments.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
