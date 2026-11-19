import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROBE_ROOT = Path(__file__).resolve().parents[1]
PROBE = PROBE_ROOT / "probe.py"
SUCCESSFUL_TURN = PROBE_ROOT / "tests" / "fixtures" / "successful-turn-transcript.json"

PROBE_SPEC = importlib.util.spec_from_file_location("orbita_m0_probe", PROBE)
assert PROBE_SPEC is not None and PROBE_SPEC.loader is not None
PROBE_MODULE = importlib.util.module_from_spec(PROBE_SPEC)
PROBE_SPEC.loader.exec_module(PROBE_MODULE)


def run_normalize(capture: dict[str, object], temp_dir: str) -> tuple[subprocess.CompletedProcess[str], dict[str, object], str]:
    input_path = Path(temp_dir) / "capture.json"
    output_path = Path(temp_dir) / "normalized.json"
    input_path.write_text(json.dumps(capture), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(PROBE), "normalize-turn", "--input", str(input_path), "--output", str(output_path)],
        cwd=PROBE_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    serialized = output_path.read_text(encoding="utf-8")
    return completed, json.loads(serialized), serialized


class ProbeCliTests(unittest.TestCase):
    def test_child_environment_omits_inherited_credentials(self) -> None:
        parent = dict(os.environ)
        parent["ORBITA_SEEDED_SECRET"] = "seeded-secret-must-not-cross-boundary"
        parent["OPENAI_API_KEY"] = "sk-seeded-api-key"

        child = PROBE_MODULE.build_child_environment(parent)

        self.assertNotIn("ORBITA_SEEDED_SECRET", child)
        self.assertNotIn("OPENAI_API_KEY", child)
        self.assertNotIn("seeded-secret-must-not-cross-boundary", child.values())
        self.assertIn("PATH", {key.upper() for key in child})

    def test_artifact_writer_fails_closed_on_recursive_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "unsafe.json"
            with self.assertRaises(ValueError):
                PROBE_MODULE.write_json(
                    output,
                    {"safe": [{"authorization": "Bearer sk-seeded-secret-value"}]},
                )
            self.assertFalse(output.exists())

    def test_runtime_metadata_pins_native_binary_and_effective_features(self) -> None:
        launcher = Path(PROBE_MODULE.codex_executable())
        runtime = PROBE_MODULE.runtime_record("codex-cli 0.170.0", launcher)

        self.assertEqual(
            runtime["nativeExecutableSha256"],
            "8d06dc231dba649c7d48d3eecab239c452a1ac498c41dd6492a6f301b90a22ce",
        )
        self.assertGreater(len(runtime["featureSnapshot"]), 200)
        self.assertTrue(runtime["effectiveConfigSha256"])
        self.assertNotIn("C:\\Users\\", json.dumps(runtime))

    def test_capture_records_the_pinned_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "contract.json"

            completed = subprocess.run(
                [sys.executable, str(PROBE), "capture-contract", "--output", str(output)],
                cwd=PROBE_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["contractSchemaVersion"], 1)
            self.assertEqual(result["runtime"]["cliVersion"], "codex-cli 0.170.0")
            self.assertEqual(result["runtime"]["nativeExecutableSha256"], "8d06dc231dba649c7d48d3eecab239c452a1ac498c41dd6492a6f301b90a22ce")
            self.assertGreater(len(result["runtime"]["featureSnapshot"]), 200)
            self.assertEqual(result["generatedContract"]["stable"]["manifestSha256"], "86d780e116e5d176752ec0065b55e81267c517b1b71423e22fa4af4a67357118")
            self.assertEqual(result["generatedContract"]["experimental"]["manifestSha256"], "1ba3f58b199dee49d6ad7b0c6a2083e8a66c92dc8917dd1ef198aee2b6c30f8c")

    def test_initialize_is_a_deterministic_sanitized_public_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "initialize-1.json"
            second = Path(temp_dir) / "initialize-2.json"

            for output in (first, second):
                completed = subprocess.run(
                    [sys.executable, str(PROBE), "initialize", "--output", str(output)],
                    cwd=PROBE_ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            first_result = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(first_result, json.loads(second.read_text(encoding="utf-8")))
            self.assertEqual(first_result["fixtureSchemaVersion"], 1)
            self.assertEqual(first_result["runtime"]["cliVersion"], "codex-cli 0.170.0")
            self.assertEqual(first_result["runtime"]["nativeExecutableSha256"], "8d06dc231dba649c7d48d3eecab239c452a1ac498c41dd6492a6f301b90a22ce")
            self.assertGreater(len(first_result["runtime"]["featureSnapshot"]), 200)
            self.assertEqual(
                first_result["transcript"][0],
                {
                    "direction": "clientToServer",
                    "message": {
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
                    },
                },
            )
            response = first_result["transcript"][1]
            self.assertEqual(response["direction"], "serverToClient")
            self.assertEqual(response["message"]["id"], "initialize-1")
            self.assertEqual(response["message"]["result"]["codexHome"], "<redacted-absolute-path>")
            self.assertEqual(response["message"]["result"]["platformFamily"], "windows")
            self.assertEqual(response["message"]["result"]["platformOs"], "windows")
            self.assertEqual(
                response["message"]["result"]["userAgent"], "<SERVER_USER_AGENT>"
            )
            self.assertEqual(
                first_result["transcript"][2],
                {
                    "direction": "clientToServer",
                    "message": {"method": "initialized"},
                },
            )
            self.assertEqual(
                first_result["transcript"][3],
                {
                    "direction": "clientToServer",
                    "message": {
                        "id": "thread-start-1",
                        "method": "thread/start",
                        "params": {"cwd": "<DISPOSABLE_PROJECT>"},
                    },
                },
            )
            self.assertEqual(
                first_result["transcript"][4],
                {
                    "direction": "serverToClient",
                    "message": {
                        "id": "thread-start-1",
                        "result": {"thread": {"id": "<THREAD_1>"}},
                    },
                },
            )
            self.assertEqual(
                first_result["outcome"],
                {
                    "classification": "directly observed",
                    "initializeResponseId": "initialize-1",
                    "rootThreadObserved": True,
                    "threadResponseId": "thread-start-1",
                },
            )

    def test_normalize_turn_correlates_streaming_and_authoritative_terminal_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "normalized.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROBE),
                    "normalize-turn",
                    "--input",
                    str(SUCCESSFUL_TURN),
                    "--output",
                    str(output),
                ],
                cwd=PROBE_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                result["outcome"],
                {
                    "finalAgentText": "ORBITA_M0_OK",
                    "rootThreadObserved": True,
                    "streamingEvidenceObserved": True,
                    "success": True,
                    "terminalSignal": "turn/completed",
                    "terminalStatus": "completed",
                    "turnObserved": True,
                },
            )
            self.assertEqual(
                result["repeatabilityDigest"],
                "9963774130a20a21c838727ff985e035a89bc27b074d6496cbffea044c1030cc",
            )
            serialized = output.read_text(encoding="utf-8")
            self.assertNotIn("019a-thread-source", serialized)
            self.assertNotIn("019a-turn-source", serialized)
            self.assertNotIn("C:\\synthetic-private", serialized)
            self.assertIn("<THREAD_1>", serialized)
            self.assertIn("<TURN_1>", serialized)
            self.assertNotIn("noise", serialized)
            self.assertEqual(
                sum(
                    entry.get("method") == "item/completed"
                    for entry in result["transcript"]
                ),
                1,
            )
            terminal_refs = result["evidenceRefs"]["terminalSignal"]
            self.assertTrue(terminal_refs)
            self.assertTrue(
                all(
                    result["transcript"][index].get("method") == "turn/completed"
                    for index in terminal_refs
                )
            )
            self.assertTrue(result["evidenceRefs"]["streamingEvidenceObserved"])

    def test_normalize_turn_fails_closed_without_matching_terminal_signal(self) -> None:
        source = json.loads(SUCCESSFUL_TURN.read_text(encoding="utf-8"))
        source["messages"] = [
            entry
            for entry in source["messages"]
            if entry["message"].get("method") != "turn/completed"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "incomplete.json"
            output = Path(temp_dir) / "failure.json"
            input_path.write_text(json.dumps(source), encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROBE),
                    "normalize-turn",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output),
                ],
                cwd=PROBE_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["outcome"],
                {"failure": "missingMatchingTurnCompleted", "success": False},
            )

    def test_live_turn_requires_explicit_model_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "must-not-exist.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROBE),
                    "live-turn",
                    "--output",
                    str(output),
                ],
                cwd=PROBE_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("--confirm-live-model", completed.stderr)
            self.assertFalse(output.exists())

    def test_normalize_turn_rejects_structurally_invalid_contract_message(self) -> None:
        capture = json.loads(SUCCESSFUL_TURN.read_text(encoding="utf-8"))
        terminal = capture["messages"][-1]["message"]["params"]["turn"]
        del terminal["status"]
        with tempfile.TemporaryDirectory() as temp_dir:
            completed, result, _ = run_normalize(capture, temp_dir)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(result["outcome"], {"failure": "invalidContractMessage", "success": False})

    def test_normalize_turn_rejects_mismatched_source_safety_params(self) -> None:
        capture = json.loads(SUCCESSFUL_TURN.read_text(encoding="utf-8"))
        thread_start = next(
            entry["message"] for entry in capture["messages"] if entry["message"].get("method") == "thread/start"
        )
        thread_start["params"]["ephemeral"] = False
        with tempfile.TemporaryDirectory() as temp_dir:
            completed, result, _ = run_normalize(capture, temp_dir)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(result["outcome"], {"failure": "unsafeThreadStartParams", "success": False})

    def test_normalize_turn_rejects_tool_activity(self) -> None:
        capture = json.loads(SUCCESSFUL_TURN.read_text(encoding="utf-8"))
        capture["messages"].insert(
            -1,
            {
                "direction": "serverToClient",
                "message": {
                    "method": "item/started",
                    "params": {
                        "item": {"command": "echo forbidden", "commandActions": [], "cwd": "C:\\synthetic-private\\project", "id": "tool-item", "status": "inProgress", "type": "commandExecution"},
                        "startedAtMs": 123457,
                        "threadId": "019a-thread-source",
                        "turnId": "019a-turn-source",
                    },
                },
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            completed, result, serialized = run_normalize(capture, temp_dir)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(result["outcome"], {"failure": "toolActivityObserved", "success": False})
        self.assertNotIn("echo forbidden", serialized)

    def test_unknown_secret_variant_is_bounded_sanitized_and_fails_closed(self) -> None:
        capture = json.loads(SUCCESSFUL_TURN.read_text(encoding="utf-8"))
        capture["messages"].insert(
            -1,
            {
                "direction": "serverToClient",
                "message": {
                    "method": "future/credentialEvent",
                    "params": {"authorization": "Bearer sk-seeded-secret-value"},
                },
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            completed, result, serialized = run_normalize(capture, temp_dir)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(result["outcome"], {"failure": "unknownSurfaceClassification", "success": False})
        self.assertNotIn("sk-seeded-secret-value", serialized)
        self.assertNotIn("authorization", serialized.lower())
        self.assertLessEqual(len(result["diagnostics"]), 16)
        self.assertEqual(result["diagnostics"][0]["method"], "future/credentialEvent")


if __name__ == "__main__":
    unittest.main()
