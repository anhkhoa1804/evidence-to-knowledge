"""Staged V2.3 backend with exact read-only tool signatures and one repair.

This changes only the model-facing tool argument contract. It neither changes
V2.1 report validation nor broadens the read-only tools, H1/H5 policy, or KG
authority. Malformed tool actions are never executed without correction.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from .qwen_rca import QwenRCAError
from .rca_agent_v2_3 import RCA_AGENT_V2_3_PROMPT_VERSION
from .staged_rca_backend_v2_2 import StagedRCAAgentV22Model

TOOL_ARGUMENT_CONTRACT_VERSION = "read_only_rca_tool_arguments_v2_3"
TOOL_ARGUMENTS: Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "get_incident_summary": (("incident_id",), ()),
    "get_candidates": (("incident_id",), ("limit", "offset")),
    "get_expanded_candidates": (("incident_id", "fallback_reason"), ("limit", "offset")),
    "get_candidate_profile": (("incident_id", "candidate_id"), ()),
    "get_metric_evidence": (("incident_id", "service_id"), ("limit", "offset")),
    "get_trace_evidence": (("incident_id", "service_id"), ("limit", "offset")),
    "get_event_evidence": (("incident_id", "service_id"), ("limit", "offset")),
    "get_change_evidence": (("incident_id", "service_id"), ("limit", "offset")),
    "get_topology_context": (("incident_id", "service_id"), ()),
    "get_evidence_by_id": (("evidence_id",), ()),
}


def validate_tool_action(name: str, arguments: Mapping[str, Any]) -> None:
    if name not in TOOL_ARGUMENTS:
        raise QwenRCAError("V23_TOOL_NOT_ALLOWED")
    required, optional = TOOL_ARGUMENTS[name]
    keys = set(arguments)
    if not set(required) <= keys or not keys <= set(required) | set(optional):
        raise QwenRCAError("V23_TOOL_ARGUMENTS_INVALID")
    for key in required:
        if not isinstance(arguments[key], str) or not arguments[key].strip():
            raise QwenRCAError("V23_TOOL_ARGUMENTS_INVALID")
    for key in ("limit", "offset"):
        if key in arguments and (not isinstance(arguments[key], int) or isinstance(arguments[key], bool)):
            raise QwenRCAError("V23_TOOL_ARGUMENTS_INVALID")
    if "fallback_reason" in arguments and not isinstance(arguments["fallback_reason"], str):
        raise QwenRCAError("V23_TOOL_ARGUMENTS_INVALID")


class StagedRCAAgentV23Model(StagedRCAAgentV22Model):
    prompt_version = RCA_AGENT_V2_3_PROMPT_VERSION
    system_prompt = "\n".join((
        StagedRCAAgentV22Model.system_prompt,
        "Exact read-only tool argument signatures follow. Include every required key and no other key.",
        "get_incident_summary(incident_id)",
        "get_candidates(incident_id, optional limit, offset)",
        "get_expanded_candidates(incident_id, optional limit, offset, fallback_reason)",
        "get_candidate_profile(incident_id, candidate_id)",
        "get_metric_evidence(incident_id, service_id, optional limit, offset)",
        "get_trace_evidence(incident_id, service_id, optional limit, offset)",
        "get_event_evidence(incident_id, service_id, optional limit, offset)",
        "get_change_evidence(incident_id, service_id, optional limit, offset)",
        "get_topology_context(incident_id, service_id)",
        "get_evidence_by_id(evidence_id)",
        "Use exact incident_id and service_id strings from the supplied evidence. An evidence_id is not a service_id.",
    ))

    def __init__(self, config, requester=None, *, max_output_tokens: int = 2048) -> None:
        super().__init__(config, requester=requester, max_output_tokens=max_output_tokens)
        self.tool_action_repairs = 0

    def public_metadata(self) -> Mapping[str, Any]:
        return {**super().public_metadata(), "tool_argument_contract_version": TOOL_ARGUMENT_CONTRACT_VERSION,
                "tool_action_repair_limit": 1}

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if "prior_tool_results" not in request:
            self.tool_action_repairs = 0
        was_first = "prior_tool_results" not in request
        result = super().generate(request)
        calls = result.get("tool_calls")
        if not calls:
            return result
        call = calls[0]
        try:
            validate_tool_action(call["name"], call["arguments"])
            return result
        except QwenRCAError:
            if self.tool_action_repairs >= 1:
                raise
            self.tool_action_repairs += 1
        # The invalid action is not executed. Ask the same provider for one
        # corrected JSON action with exact signatures; no loop or coercion.
        self._staged_messages.append({"role": "user", "content": json.dumps({
            "task": "Correct the immediately preceding TOOL action arguments. Return exactly one JSON TOOL action.",
            "required_and_optional_arguments": {name: {"required": list(required), "optional": list(optional)}
                                                for name, (required, optional) in TOOL_ARGUMENTS.items()},
            "error": "INVALID_READ_ONLY_TOOL_ARGUMENTS",
        }, sort_keys=True)})
        turn = self.complete(self._staged_messages, response_format={"type": "json_object"})
        content = turn["message"].get("content")
        if turn["message"].get("tool_calls") or not isinstance(content, str):
            raise QwenRCAError("V23_TOOL_ACTION_REPAIR_INVALID")
        try:
            corrected = json.loads(content)
        except json.JSONDecodeError as exc:
            raise QwenRCAError("V23_TOOL_ACTION_REPAIR_INVALID") from exc
        if not isinstance(corrected, Mapping) or set(corrected) != {"action", "tool_name", "arguments"} or corrected["action"] != "TOOL" or not isinstance(corrected["arguments"], Mapping):
            raise QwenRCAError("V23_TOOL_ACTION_REPAIR_INVALID")
        name, arguments = corrected["tool_name"], corrected["arguments"]
        validate_tool_action(name, arguments)
        if was_first and name != "get_incident_summary":
            raise QwenRCAError("V23_FIRST_TOOL_MUST_BE_INCIDENT_SUMMARY")
        self._first_action_pending = False
        self._staged_messages.append({"role": "assistant", "content": content})
        self.action_history.append({"action": "TOOL_ACTION_REPAIR", "latency_ms": turn["latency_ms"],
                                    "retry_count": turn["retry_count"],
                                    "input_tokens": turn["usage"].get("input_tokens"),
                                    "output_tokens": turn["usage"].get("output_tokens")})
        return {"tool_calls": [{"name": name, "arguments": dict(arguments)}]}
