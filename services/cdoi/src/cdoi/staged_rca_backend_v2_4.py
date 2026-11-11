"""V2.4 reliability adapter: explicit IDs, contextual repair, bounded stop."""
from __future__ import annotations

import json
from typing import Any, Mapping

from .qwen_rca import QwenRCAError
from .staged_rca_backend_v2_3 import (
    TOOL_ARGUMENTS, StagedRCAAgentV23Model, validate_tool_action,
)

TOOL_BUDGET = 8
RCA_AGENT_V2_4_PROMPT_VERSION = "rca_agent_staged_reliability_v2_4"


def collect_ids(value: Any, keys: frozenset[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in keys and isinstance(child, str):
                found.add(child)
            elif key in keys and isinstance(child, (list, tuple)):
                found.update(item for item in child if isinstance(item, str))
                found.update(collect_ids(child, keys))
            else:
                found.update(collect_ids(child, keys))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.update(collect_ids(child, keys))
    return found


def canonical_allowed_ids(candidate_ids: set[str] | frozenset[str],
                          evidence_ids: set[str] | frozenset[str]) -> dict[str, list[str]]:
    return {"candidate_ids": sorted(set(candidate_ids)), "evidence_ids": sorted(set(evidence_ids))}


def tool_call_signature(name: str, arguments: Mapping[str, Any]) -> str:
    return json.dumps({"name": name, "arguments": dict(arguments)}, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)


def validate_tool_references(name: str, arguments: Mapping[str, Any],
                             candidate_ids: set[str], evidence_ids: set[str]) -> None:
    if "candidate_id" in arguments and arguments["candidate_id"] not in candidate_ids:
        raise QwenRCAError("V24_TOOL_UNKNOWN_CANDIDATE_ID")
    if "evidence_id" in arguments and arguments["evidence_id"] not in evidence_ids:
        raise QwenRCAError("V24_TOOL_UNKNOWN_EVIDENCE_ID")


def parse_action(content: str) -> Mapping[str, Any]:
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise QwenRCAError("V24_ACTION_JSON_INVALID") from exc
    if not isinstance(value, Mapping):
        raise QwenRCAError("V24_ACTION_OBJECT_REQUIRED")
    return value


class StagedRCAAgentV24Model(StagedRCAAgentV23Model):
    prompt_version = RCA_AGENT_V2_4_PROMPT_VERSION
    system_prompt = "\n".join((
        StagedRCAAgentV23Model.system_prompt,
        "Reliability contract V2.4: use only the exact candidate_ids and evidence_ids explicitly listed in the current request or tool results.",
        "Never cite an evidence ID unless it is listed for the candidate being cited. Never invent, repair, approximate, or copy IDs from another scope.",
        "The total read-only TOOL-call budget is exactly eight. After the eighth TOOL result, return one REPORT action; do not request a ninth tool.",
        "Do not repeat a completed TOOL action with identical name and arguments.",
    ))

    def __init__(self, config, requester=None, *, max_output_tokens: int = 2048) -> None:
        super().__init__(config, requester=requester, max_output_tokens=max_output_tokens)
        self.exposed_candidate_ids: set[str] = set()
        self.exposed_evidence_ids: set[str] = set()
        self.evidence_by_candidate: dict[str, set[str]] = {}
        self.report_repair_attempts = 0
        self.budget_stop_repairs = 0
        self.tool_call_signatures: set[str] = set()

    def public_metadata(self) -> Mapping[str, Any]:
        return {**super().public_metadata(), "reliability_protocol_version": "v3_rca_agent_v2_4",
                "tool_budget": TOOL_BUDGET, "max_transport_retries": 0}

    def _record_exposure(self, request: Mapping[str, Any]) -> None:
        self.exposed_candidate_ids.update(collect_ids(request, frozenset({"candidate_id"})))
        evidence_keys = frozenset({"evidence_id", "aggregate_evidence_id", "representative_evidence_ids",
                                   "supporting_evidence_ids", "contradictory_evidence_ids"})
        self.exposed_evidence_ids.update(collect_ids(request, evidence_keys))
        for profile in request.get("preloaded_candidate_profiles", ()):
            if not isinstance(profile, Mapping) or not isinstance(profile.get("candidate_id"), str):
                continue
            candidate_id = profile["candidate_id"]
            allowed = collect_ids(profile, evidence_keys)
            self.evidence_by_candidate.setdefault(candidate_id, set()).update(allowed)
        for result in request.get("prior_tool_results", ()):
            if not isinstance(result, Mapping):
                continue
            payload = result.get("result")
            if not isinstance(payload, Mapping):
                continue
            profile = payload.get("profile")
            if isinstance(profile, Mapping) and isinstance(profile.get("candidate_id"), str):
                candidate_id = profile["candidate_id"]
                allowed = collect_ids(profile, evidence_keys)
                self.evidence_by_candidate.setdefault(candidate_id, set()).update(allowed)
            elif result.get("tool") == "get_evidence_by_id":
                evidence_id = payload.get("evidence_id")
                evidence = payload.get("evidence")
                if isinstance(evidence_id, str) and isinstance(evidence, Mapping):
                    self.exposed_evidence_ids.add(evidence_id)

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if "prior_tool_results" not in request:
            self.exposed_candidate_ids.clear()
            self.exposed_evidence_ids.clear()
            self.evidence_by_candidate.clear()
            self.report_repair_attempts = 0
            self.budget_stop_repairs = 0
            self.tool_call_signatures.clear()
        self._record_exposure(request)
        result = dict(super().generate(request))
        tool_turns = sum(action.get("action") == "TOOL" for action in self.action_history)
        if result.get("tool_calls") and tool_turns > TOOL_BUDGET:
            return self._repair_over_budget_action(result)
        if result.get("tool_calls"):
            call = result["tool_calls"][0]
            validate_tool_references(call["name"], call["arguments"],
                                     self.exposed_candidate_ids, self.exposed_evidence_ids)
            signature = tool_call_signature(call["name"], call["arguments"])
            if signature in self.tool_call_signatures:
                return self._repair_repeated_action(result, signature)
            self.tool_call_signatures.add(signature)
        return result

    def _repair_over_budget_action(self, invalid_action: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._repair_tool_action(invalid_action, "TOOL_BUDGET_EXHAUSTED", "V24_TOOL_BUDGET_REPAIR_EXHAUSTED")

    def _repair_repeated_action(self, invalid_action: Mapping[str, Any], signature: str) -> Mapping[str, Any]:
        return self._repair_tool_action(invalid_action, "DUPLICATE_TOOL_ACTION", "V24_DUPLICATE_TOOL_REPAIR_EXHAUSTED", signature)

    def _repair_tool_action(self, invalid_action: Mapping[str, Any], reason: str,
                            exhaustion_code: str, signature: str | None = None) -> Mapping[str, Any]:
        if self.tool_action_repairs >= 1:
            raise QwenRCAError(exhaustion_code)
        self.budget_stop_repairs += 1
        self.tool_action_repairs += 1
        prompt = {
            "task": "Return one corrected JSON action. If the read-only call budget is exhausted, return REPORT. Never repeat a completed call.",
            "rejected_action": invalid_action,
            "validation_error": reason,
            "rejected_call_signature": signature,
            "tool_calls_executed": min(TOOL_BUDGET, sum(action.get("action") == "TOOL" for action in self.action_history)),
            "remaining_tool_calls": max(0, TOOL_BUDGET - sum(action.get("action") == "TOOL" for action in self.action_history)),
            "allowed_ids": canonical_allowed_ids(self.exposed_candidate_ids, self.exposed_evidence_ids),
            "evidence_by_candidate": {key: sorted(value) for key, value in sorted(self.evidence_by_candidate.items())},
            "action_schema": {"TOOL": "one valid non-repeated read-only call if budget remains", "REPORT": "RCAReport satisfying unchanged V2.1 contract"},
        }
        turn = self.complete([*self._staged_messages,
                              {"role": "user", "content": json.dumps(prompt, sort_keys=True)}],
                             response_format={"type": "json_object"})
        content = turn["message"].get("content")
        if turn["message"].get("tool_calls") or not isinstance(content, str):
            raise QwenRCAError("V24_TOOL_BUDGET_REPAIR_INVALID")
        action = parse_action(content)
        if action.get("action") == "REPORT" and set(action) == {"action", "report"} and isinstance(action.get("report"), Mapping):
            self.action_history.append({"action": "TOOL_ACTION_REPAIR", "reason": reason,
                                        "latency_ms": turn["latency_ms"], "retry_count": turn["retry_count"],
                                        "input_tokens": turn["usage"].get("input_tokens"),
                                        "output_tokens": turn["usage"].get("output_tokens")})
            return {"report": dict(action["report"])}
        if action.get("action") == "TOOL" and set(action) == {"action", "tool_name", "arguments"} and isinstance(action.get("arguments"), Mapping):
            name, arguments = action["tool_name"], action["arguments"]
            validate_tool_action(name, arguments)
            validate_tool_references(name, arguments, self.exposed_candidate_ids, self.exposed_evidence_ids)
            corrected_signature = tool_call_signature(name, arguments)
            if corrected_signature in self.tool_call_signatures:
                raise QwenRCAError("V24_TOOL_ACTION_REPAIR_DUPLICATE")
            tool_turns = sum(item.get("action") == "TOOL" for item in self.action_history)
            if tool_turns > TOOL_BUDGET:
                raise QwenRCAError("V24_TOOL_BUDGET_REPAIR_INVALID")
            if tool_turns == 1 and name != "get_incident_summary":
                raise QwenRCAError("V24_FIRST_TOOL_MUST_BE_INCIDENT_SUMMARY")
            self.tool_call_signatures.add(corrected_signature)
            self._staged_messages.append({"role": "assistant", "content": content})
            self.action_history.append({"action": "TOOL_ACTION_REPAIR", "reason": reason,
                                        "latency_ms": turn["latency_ms"], "retry_count": turn["retry_count"],
                                        "input_tokens": turn["usage"].get("input_tokens"),
                                        "output_tokens": turn["usage"].get("output_tokens")})
            return {"tool_calls": [{"name": name, "arguments": dict(arguments)}]}
        else:
            raise QwenRCAError("V24_TOOL_BUDGET_REPAIR_INVALID")

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str,
                      request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.report_repair_attempts += 1
        if self.report_repair_attempts > 1:
            raise QwenRCAError("V24_REPORT_REPAIR_EXHAUSTED")
        candidate_ids = self.exposed_candidate_ids | collect_ids(request, frozenset({"candidate_id"}))
        evidence_ids = self.exposed_evidence_ids | collect_ids(request, frozenset({
            "evidence_id", "aggregate_evidence_id", "representative_evidence_ids",
            "supporting_evidence_ids", "contradictory_evidence_ids"}))
        by_candidate = {key: sorted(value) for key, value in sorted(self.evidence_by_candidate.items())}
        original_status = raw_output.get("status")
        prompt = {
            "task": "Repair this report exactly once and return one plain RCAReport JSON object.",
            "validation_error": str(error_code),
            "invalid_report": dict(raw_output),
            "preserve_original_status": original_status if original_status in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"} else None,
            "allowed_ids": canonical_allowed_ids(candidate_ids, evidence_ids),
            "evidence_ids_allowed_for_each_candidate": by_candidate,
            "required_status_contract": {
                "RCA_HYPOTHESIS": "primary_hypothesis must use an allowed candidate_id; nonempty limitations required",
                "INSUFFICIENT_EVIDENCE": "primary_hypothesis=null; investigated_candidate_ids must equal the exact H1 set; comparison_completed=true; nonempty abstention_reason and missing_or_conflicting_evidence",
            },
            "citation_rule": "Cite only exact evidence_ids allowed for the cited candidate. Do not map, approximate, omit unknown IDs automatically, or invent IDs.",
            "schema": "RCAReport; include all common fields and arrays; keep hypothesis status unchanged when present in the invalid report",
        }
        # Keep the full staged interaction history. The old V2.3 implementation
        # sent repair a new isolated prompt without the tool results.
        messages = [*self._staged_messages,
                    {"role": "user", "content": json.dumps(prompt, sort_keys=True)}]
        result = self.complete(messages, response_format={"type": "json_object"})
        content = result["message"].get("content")
        if result["message"].get("tool_calls") or not isinstance(content, str):
            raise QwenRCAError("V24_REPORT_REPAIR_CONTENT_INVALID")
        repaired = parse_action(content)
        if repaired.get("action") == "REPORT" and isinstance(repaired.get("report"), Mapping):
            repaired = repaired["report"]
        if original_status in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"} and repaired.get("status") != original_status:
            raise QwenRCAError("V24_REPAIR_STATUS_CHANGED")
        return {"report": dict(repaired)}
