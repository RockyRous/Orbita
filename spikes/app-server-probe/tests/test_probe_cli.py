import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROBE_ROOT = Path(__file__).resolve().parents[1]
PROBE = PROBE_ROOT / "probe.py"


class ProbeCliTests(unittest.TestCase):
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
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8")),
                {
                    "contractSchemaVersion": 1,
                    "runtime": {
                        "cliVersion": "codex-cli 0.170.0",
                        "launcherSha256": "c54db6755e710c39703f7c37512f9e35ed41042d8080558d2b84b8d2694323c3",
                        "features": {"experimentalApi": False},
                        "transport": "stdio://",
                    },
                    "generatedContract": {
                        "experimental": {
                            "bundleSha256": "e3f3b0a75918871280e808a186b33f583ec4a9eb1a1038c2bd13d2ae1c5dc8db",
                            "command": [
                                "codex",
                                "app-server",
                                "generate-json-schema",
                                "--experimental",
                                "--out",
                                "<temporary-directory>",
                            ],
                            "manifestSha256": "1ba3f58b199dee49d6ad7b0c6a2083e8a66c92dc8917dd1ef198aee2b6c30f8c",
                            "schemaFileCount": 479,
                        },
                        "stable": {
                            "bundleSha256": "ca6123bc03238217a62a32c745b45e267fdb26825a80ce6849e893fcbe6628b8",
                            "command": [
                                "codex",
                                "app-server",
                                "generate-json-schema",
                                "--out",
                                "<temporary-directory>",
                            ],
                            "manifestSha256": "86d780e116e5d176752ec0065b55e81267c517b1b71423e22fa4af4a67357118",
                            "schemaFileCount": 329,
                        },
                    },
                    "digestStrategy": {
                        "algorithm": "sha256",
                        "contractManifestEncoding": "canonical-json-utf8-lf",
                        "contractManifestEntry": ["path", "sha256"],
                    },
                    "surfaceClassification": {
                        "initialize": "stable",
                        "initialized": "stable",
                        "thread/start": "stable",
                        "turn/start": "stable",
                    },
                },
            )

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
            self.assertEqual(
                first_result["runtime"],
                {
                    "cliVersion": "codex-cli 0.170.0",
                    "launcherSha256": "c54db6755e710c39703f7c37512f9e35ed41042d8080558d2b84b8d2694323c3",
                    "features": {"experimentalApi": False},
                    "transport": "stdio://",
                },
            )
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


if __name__ == "__main__":
    unittest.main()
