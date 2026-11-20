"""Offline projection of schema-validated command-approval evidence.

This module deliberately accepts recorded protocol envelopes only. It does not
start Codex, send JSON-RPC responses, or decide on a user's behalf.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError


COMMAND_APPROVAL_METHOD = "item/commandExecution/requestApproval"
RESOLVED_METHOD = "serverRequest/resolved"


class ApprovalContractError(ValueError):
    """Raised when an offline fixture is not valid approval evidence."""


class CommandApprovalSchemaValidator:
    """Validate the small public App Server surface used by this offline slice."""

    def __init__(self, schema_dir: Path) -> None:
        def load(name: str) -> Draft7Validator:
            return Draft7Validator(json.loads((schema_dir / name).read_text(encoding="utf-8")))

        self.server_request = load("ServerRequest.json")
        self.server_notification = load("ServerNotification.json")
        self.jsonrpc_response = load("JSONRPCResponse.json")
        self.command_approval_response = load("CommandExecutionRequestApprovalResponse.json")

    @staticmethod
    def _check(validator: Draft7Validator, value: object) -> None:
        try:
            validator.validate(value)
        except ValidationError as error:
            raise ApprovalContractError("invalidContractMessage") from error

    def validate_server_request(self, message: dict[str, object]) -> None:
        self._check(self.server_request, message)
        if message.get("method") != COMMAND_APPROVAL_METHOD:
            raise ApprovalContractError("unsupportedApprovalMethod")

    def validate_resolution(self, message: dict[str, object]) -> None:
        self._check(self.server_notification, message)
        if message.get("method") != RESOLVED_METHOD:
            raise ApprovalContractError("unsupportedApprovalMethod")

    def validate_response(self, message: dict[str, object]) -> None:
        self._check(self.jsonrpc_response, message)
        result = message.get("result")
        if not isinstance(result, dict):
            raise ApprovalContractError("invalidContractMessage")
        self._check(self.command_approval_response, result)


def _failure(category: str) -> ApprovalContractError:
    return ApprovalContractError(category)


def normalize_command_approval_capture(
    capture: dict[str, object], validator: CommandApprovalSchemaValidator
) -> dict[str, object]:
    """Return a deterministic attention projection from an offline transcript.

    The caller supplies a validator created from the exact generated schema
    bundle. The function only records observed decisions; it never supplies a
    default acceptance or derives an execution outcome from request resolution.
    """

    messages = capture.get("messages")
    if not isinstance(messages, list):
        raise _failure("invalidCapture")

    approvals: dict[object, dict[str, object]] = {}
    late_or_mismatched: list[dict[str, object]] = []

    for entry in messages:
        if not isinstance(entry, dict) or not isinstance(entry.get("message"), dict):
            raise _failure("invalidContractMessage")
        direction = entry.get("direction")
        message = entry["message"]
        method = message.get("method")

        if direction == "serverToClient" and method == COMMAND_APPROVAL_METHOD:
            validator.validate_server_request(message)
            request_id = message.get("id")
            params = message.get("params")
            if request_id in approvals or not isinstance(params, dict):
                raise _failure("conflictingRequestIdentity")
            required = ("threadId", "turnId", "itemId", "startedAtMs")
            if not all(isinstance(params.get(key), str) for key in required[:-1]) or not isinstance(
                params.get("startedAtMs"), int
            ):
                raise _failure("invalidContractMessage")
            command = params.get("command")
            approvals[request_id] = {
                "command": command if isinstance(command, str) else None,
                "decision": None,
                "itemId": params["itemId"],
                "kind": params.get("kind", "command"),
                "requestId": request_id,
                "resolution": "pending",
                "sourceContext": {
                    "approvalId": params.get("approvalId"),
                    "cwd": params.get("cwd"),
                    "reason": params.get("reason"),
                },
                "threadId": params["threadId"],
                "turnId": params["turnId"],
            }
            continue

        if direction == "clientToServer" and "id" in message:
            request_id = message.get("id")
            if request_id not in approvals:
                raise _failure("responseWithoutPendingApproval")
            validator.validate_response(message)
            if approvals[request_id]["decision"] is not None:
                raise _failure("duplicateApprovalResponse")
            result = message["result"]
            assert isinstance(result, dict)
            approvals[request_id]["decision"] = result["decision"]
            continue

        if direction == "serverToClient" and method == RESOLVED_METHOD:
            validator.validate_resolution(message)
            params = message.get("params")
            assert isinstance(params, dict)
            request_id = params.get("requestId")
            approval = approvals.get(request_id)
            if approval is None or approval["threadId"] != params.get("threadId") or approval["resolution"] != "pending":
                late_or_mismatched.append(
                    {"requestId": request_id, "threadId": params.get("threadId")}
                )
                continue
            approval["resolution"] = "resolved"
            continue

        raise _failure("unsupportedApprovalMethod")

    projected = list(approvals.values())
    action_required = any(approval["resolution"] == "pending" for approval in projected)
    return {
        "approvals": projected,
        "attention": {
            "actionRequired": action_required,
            "state": "Action required" if action_required else "No attention",
        },
        "fixtureSchemaVersion": 1,
        "lateOrMismatchedResolutions": late_or_mismatched,
        "surfaceClassification": {
            COMMAND_APPROVAL_METHOD: "stable",
            RESOLVED_METHOD: "stable",
        },
    }
