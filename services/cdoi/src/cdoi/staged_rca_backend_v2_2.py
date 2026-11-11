"""Bounded JSON-action tool protocol for OpenAI-compatible providers.

This backend is independent of the frozen V2.1 native-tool transport. Each
provider turn produces exactly one JSON action. A TOOL action is executed only
by the existing read-only RCA tool dispatcher; a REPORT action is validated by
the unchanged V2.1 report contract. Ambiguous/unknown actions fail closed.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from .qwen_rca import QwenRCAError
from .qwen_rca_v2_1 import QwenRCAAgentV21Model
from .rca_agent_v2_2 import RCA_AGENT_V2_2_PROMPT_VERSION

STAGED_PROTOCOL_VERSION = "rca_staged_json_action_v2_2"
ALLOWED_TOOLS = frozenset({
    "get_incident_summary", "get_candidates", "get_expanded_candidates",
    "get_candidate_profile", "get_metric_evidence", "get_trace_evidence",
    "get_event_evidence", "get_change_evidence", "get_topology_context",
    "get_evidence_by_id",
})


class StagedRCAAgentV22Model(QwenRCAAgentV21Model):
    prompt_version = RCA_AGENT_V2_2_PROMPT_VERSION
    system_prompt = "\n".join((
        QwenRCAAgentV21Model.system_prompt,
        "Use exactly one JSON action per turn: TOOL with tool_name and arguments, or REPORT with report object.",
        "Your first action MUST be TOOL get_incident_summary for the supplied incident_id; do not report on the first turn.",
        "A TOOL action may call only the supplied read-only tool names. Do not emit native tool calls or prose.",
        "After a TOOL result, inspect the returned evidence and choose another bounded TOOL or final REPORT.",
        "Never infer ground truth. A report is an unapproved, non-causal hypothesis or valid abstention.",
    ))

    def __init__(self, config, requester=None, *, max_output_tokens: int = 2048) -> None:
        super().__init__(config, requester=requester, max_output_tokens=max_output_tokens)
        self._staged_messages: list[Mapping[str, Any]] = []
        self.action_history: list[Mapping[str, Any]] = []
        self._first_action_pending = True

    def public_metadata(self) -> Mapping[str, Any]:
        return {**super().public_metadata(), "staged_protocol_version": STAGED_PROTOCOL_VERSION,
                "native_tool_transport": False, "tool_execution": "EXISTING_READ_ONLY_DISPATCHER"}

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if "prior_tool_results" not in request:
            self._first_action_pending = True
            h1_ids = sorted(str(item.get("candidate_id")) for item in request.get("preloaded_candidate_profiles", [])
                            if isinstance(item, Mapping) and item.get("candidate_id"))
            payload = {"incident": request.get("incident"), "candidates": request.get("candidates"),
                       "preloaded_candidate_profiles": request.get("preloaded_candidate_profiles"),
                       "h1_comparison": request.get("h1_comparison"),
                       "candidate_source": request.get("candidate_source"),
                       "report_schema": request.get("report_schema"),
                       "allowed_read_only_tools": sorted(ALLOWED_TOOLS),
                       "report_contract": {
                           "statuses": ["RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"],
                           "common_required": ["status", "primary_hypothesis", "alternative_hypotheses",
                                               "supporting_evidence_ids", "contradictory_evidence_ids",
                                               "reasoning_summary", "limitations"],
                           "abstention_required": {"primary_hypothesis": None,
                                                   "investigated_candidate_ids": h1_ids,
                                                   "comparison_completed": True,
                                                   "abstention_reason": "nonempty string",
                                                   "missing_or_conflicting_evidence": ["at least one concrete gap or conflict"]},
                           "hypothesis_required": {"primary_hypothesis": {"candidate_id": "one supplied candidate ID",
                                                                              "statement": "non-causal hypothesis",
                                                                              "supporting_evidence_ids": [],
                                                                              "limitations": ["nonempty limitation"],
                                                                              "model_self_assessment": "LOW"},
                                                   "limitations": ["nonempty limitation"]},
                           "evidence_ids": "cite only supplied IDs, or an empty list",
                       },
                       "action_schema": {"TOOL": {"action": "TOOL", "tool_name": "string", "arguments": {}},
                                         "REPORT": {"action": "REPORT", "report": {}}}}
            self._staged_messages = [{"role": "system", "content": self.system_prompt},
                                     {"role": "user", "content": json.dumps(payload, sort_keys=True)}]
        else:
            results = request["prior_tool_results"]
            if not isinstance(results, list):
                raise QwenRCAError("V22_INVALID_TOOL_RESULT")
            self._staged_messages.append({"role": "user", "content": json.dumps({
                "tool_results": results,
                "instruction": "Return exactly one JSON TOOL or REPORT action. Use only supplied evidence IDs.",
            }, sort_keys=True)})
        turn = self.complete(self._staged_messages, response_format={"type": "json_object"})
        message = turn["message"]
        if message.get("tool_calls"):
            raise QwenRCAError("V22_UNEXPECTED_NATIVE_TOOL_CALL")
        content = message.get("content")
        if not isinstance(content, str):
            raise QwenRCAError("V22_ACTION_CONTENT_REQUIRED")
        try:
            action = json.loads(content)
        except json.JSONDecodeError as exc:
            raise QwenRCAError("V22_ACTION_JSON_INVALID") from exc
        if not isinstance(action, Mapping):
            raise QwenRCAError("V22_ACTION_OBJECT_REQUIRED")
        kind = action.get("action")
        self.action_history.append({"action": kind if isinstance(kind, str) else "INVALID",
                                    "latency_ms": turn["latency_ms"], "retry_count": turn["retry_count"],
                                    "input_tokens": turn["usage"].get("input_tokens"),
                                    "output_tokens": turn["usage"].get("output_tokens")})
        if kind == "TOOL":
            if set(action) != {"action", "tool_name", "arguments"}:
                raise QwenRCAError("V22_TOOL_ACTION_SCHEMA_INVALID")
            name, arguments = action["tool_name"], action["arguments"]
            if name not in ALLOWED_TOOLS or not isinstance(arguments, Mapping):
                raise QwenRCAError("V22_TOOL_ACTION_INVALID")
            if self._first_action_pending and name != "get_incident_summary":
                raise QwenRCAError("V22_FIRST_TOOL_MUST_BE_INCIDENT_SUMMARY")
            self._first_action_pending = False
            self._staged_messages.append({"role": "assistant", "content": content})
            return {"tool_calls": [{"name": name, "arguments": dict(arguments)}]}
        if kind == "REPORT":
            if self._first_action_pending:
                raise QwenRCAError("V22_FIRST_TURN_SUMMARY_REQUIRED")
            if set(action) != {"action", "report"} or not isinstance(action["report"], Mapping):
                raise QwenRCAError("V22_REPORT_ACTION_SCHEMA_INVALID")
            return {"report": dict(action["report"])}
        raise QwenRCAError("V22_ACTION_INVALID")

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str,
                      request: Mapping[str, Any]) -> Mapping[str, Any]:
        # Repair is a *report* turn, not an action turn. Separating the two
        # envelopes avoids conflicting provider instructions while retaining
        # V2.1's one-repair, exact-status, fail-closed validation.
        prompt = {"task": "Return exactly one corrected RCAReport JSON object, not a TOOL/REPORT action wrapper.",
                  "validation_error": error_code, "invalid_report": dict(raw_output),
                  "h1_candidate_ids": [item.get("candidate_id") for item in request.get("preloaded_candidate_profiles", [])
                                       if isinstance(item, Mapping)],
                  "required_status": ["RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"],
                  "required_schema": request.get("report_schema")}
        result = self.complete([{"role": "system", "content": "Repair one JSON RCAReport only. Do not invent evidence, candidates, or causal proof. Return JSON object without action wrapper or prose."},
                                {"role": "user", "content": json.dumps(prompt, sort_keys=True)}],
                               response_format={"type": "json_object"})
        content = result["message"].get("content")
        if not isinstance(content, str):
            raise QwenRCAError("V22_REPAIR_CONTENT_INVALID")
        try:
            repaired = json.loads(content)
        except json.JSONDecodeError as exc:
            raise QwenRCAError("V22_REPAIR_JSON_INVALID") from exc
        if not isinstance(repaired, Mapping):
            raise QwenRCAError("V22_REPAIR_OBJECT_REQUIRED")
        return {"report": dict(repaired)}
