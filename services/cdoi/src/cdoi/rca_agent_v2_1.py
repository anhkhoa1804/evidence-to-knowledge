"""V2.1 fail-closed RCA report-status contract.

This module intentionally leaves V2 intact.  It preserves V2's investigation
policy and changes only report contract ordering: status and status-specific
fields must validate before an RCAReport can be constructed.
"""
from __future__ import annotations

from typing import Any, Mapping

from .rca_agent_v2 import (
    FALLBACK_REASONS, InvestigationState, RCAAgentV2, RCAAgentV2Model,
    V2AgentBudget, _profile_view,
)
from .rca_investigation import CandidateSourceMode, RCAReport, ReadOnlyRCATools

RCA_AGENT_V2_1_PROMPT_VERSION = "rca_agent_qwen_v2_1"
RCA_AGENT_V2_1_TRACE_VERSION = "rca_agent_trace_v2_1"
RCA_AGENT_V2_1_STATUS_CONTRACT_VERSION = "rca_report_status_contract_v2_1"
MODEL_SEMANTIC_STATUSES = frozenset({"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"})


class RCAAgentV21(RCAAgentV2):
    """V2 policy with a separately versioned, fail-closed report contract."""

    trace_schema_version = RCA_AGENT_V2_1_TRACE_VERSION

    def __init__(self, model: RCAAgentV2Model, *, budget: V2AgentBudget = V2AgentBudget()) -> None:
        super().__init__(model, budget=budget)
        self.trace_schema_version = RCA_AGENT_V2_1_TRACE_VERSION

    def prompt_version(self) -> str:
        return str(getattr(self.model, "prompt_version", RCA_AGENT_V2_1_PROMPT_VERSION))

    @staticmethod
    def _status(raw: Mapping[str, Any]) -> str:
        if "status" not in raw or raw.get("status") is None:
            raise ValueError("RCA_STATUS_REQUIRED")
        status = raw["status"]
        if not isinstance(status, str) or not status.strip():
            raise ValueError("RCA_STATUS_REQUIRED")
        if status not in MODEL_SEMANTIC_STATUSES:
            raise ValueError("RCA_STATUS_INVALID")
        return status

    @classmethod
    def validate_raw_report(cls, raw: Mapping[str, Any], h1_ids: set[str]) -> str:
        """Validate raw schema before report construction or semantic checks."""
        status = cls._status(raw)
        if status == "INSUFFICIENT_EVIDENCE":
            seen = raw.get("investigated_candidate_ids")
            if not isinstance(seen, list) or {str(item) for item in seen} != h1_ids:
                raise ValueError("RCA_ABSTENTION_CANDIDATES_REQUIRED")
            if raw.get("comparison_completed") is not True:
                raise ValueError("RCA_ABSTENTION_CANDIDATES_REQUIRED")
            reason = raw.get("abstention_reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("RCA_ABSTENTION_REASON_REQUIRED")
            unresolved = raw.get("missing_or_conflicting_evidence")
            if not isinstance(unresolved, list) or not any(isinstance(item, str) and item.strip() for item in unresolved):
                raise ValueError("RCA_ABSTENTION_EVIDENCE_REQUIRED")
        else:
            primary = raw.get("primary_hypothesis")
            if not isinstance(primary, Mapping):
                raise ValueError("RCA_HYPOTHESIS_REQUIRES_PRIMARY")
            limits = raw.get("limitations")
            if not isinstance(limits, list) or not any(isinstance(item, str) and item.strip() for item in limits):
                raise ValueError("RCA_HYPOTHESIS_LIMITATIONS_REQUIRED")
        return status

    def _validated_report(self, incident: str, raw: Mapping[str, Any], calls: int,
                          metadata: Mapping[str, Any], tools: ReadOnlyRCATools,
                          h1_ids: set[str]) -> RCAReport:
        self.validate_raw_report(raw, h1_ids)
        report = self._report(incident, raw, calls, metadata)
        evidence_ids = set(tools._evidence)
        for profile in tools.profiles:
            evidence_ids.update(item.evidence_id for item in profile.supporting_evidence)
            evidence_ids.update(item.evidence_id for item in profile.context_evidence)
        report.validate(set(tools._candidate), evidence_ids)
        return report

    def investigate(self, tools: ReadOnlyRCATools,
                    candidate_source: CandidateSourceMode = CandidateSourceMode.H1_THEN_H5_FALLBACK,
                    model_metadata: Mapping[str, Any] | None = None) -> tuple[RCAReport, Mapping[str, Any]]:
        if candidate_source is not CandidateSourceMode.H1_THEN_H5_FALLBACK:
            raise ValueError("V2_1_REQUIRES_H1_THEN_H5_FALLBACK")
        incident = tools.context.incident.incident_id
        states: list[str] = []; self.last_states = states
        self._transition(states, InvestigationState.INITIALIZED)
        h1 = tuple(tools.candidates)
        if len(h1) > self.budget.max_h1_profiles:
            raise ValueError("V2_H1_PROFILE_PRELOAD_BUDGET_EXCEEDED")
        h1_ids = {item.candidate_id for item in h1}
        profiles = tuple(profile for profile in tools.profiles if profile.candidate_id in h1_ids)
        if {item.candidate_id for item in profiles} != h1_ids:
            raise ValueError("V2_H1_PROFILE_PRELOAD_INCOMPLETE")
        preload = [_profile_view(item) for item in profiles]
        self._transition(states, InvestigationState.H1_PROFILES_LOADED)
        comparison = {"compared_candidate_ids": sorted(h1_ids),
                      "comparison_basis": "PRELOADED_H1_CANDIDATE_EVIDENCE_PROFILES"}
        self._transition(states, InvestigationState.H1_COMPARED)
        request: Mapping[str, Any] = {
            "prompt_version": self.prompt_version(), "instructions": self.instructions(),
            "incident": tools.get_incident_summary(incident),
            "candidates": tools.get_candidates(incident, limit=self.budget.max_h1_profiles),
            "preloaded_candidate_profiles": preload, "h1_comparison": comparison,
            "candidate_source": candidate_source.value, "tool_schema_version": "read_only_rca_tools_v2",
            "report_schema": "RCAReport plus V2.1 explicit status contract",
        }
        response = dict(self.model.generate(request)); calls: list[Mapping[str, Any]] = []
        fallback: Mapping[str, Any] = {"fallback_used": False, "fallback_reason": None,
                                       "additional_candidates_exposed": 0}
        while True:
            requested = response.get("tool_calls", [])
            if not isinstance(requested, list): raise ValueError("INVALID_AGENT_TOOL_CALL")
            if not requested: break
            if len(calls) + len(requested) > self.budget.max_tool_calls:
                raise ValueError("INVALID_OR_EXCESSIVE_AGENT_TOOL_CALLS")
            self._transition(states, InvestigationState.TARGETED_INVESTIGATION)
            results = []
            for call in requested:
                if not isinstance(call, Mapping) or not isinstance(call.get("name"), str) or not isinstance(call.get("arguments", {}), Mapping):
                    raise ValueError("INVALID_AGENT_TOOL_CALL")
                name, args = call["name"], dict(call["arguments"])
                if name == "get_expanded_candidates":
                    reason = args.pop("fallback_reason", None)
                    if reason not in FALLBACK_REASONS: raise ValueError("V2_INVALID_FALLBACK_REASON")
                    result = tools.call(name, args)
                    fallback = {"fallback_used": True, "fallback_reason": reason,
                                "additional_candidates_exposed": int(result.get("total", 0))}
                    self._transition(states, InvestigationState.H5_EXPANDED)
                else:
                    if name not in {"get_incident_summary", "get_candidate_profile", "get_topology_context", "get_evidence_by_id"}:
                        args.setdefault("limit", self.budget.max_evidence_per_tool_call)
                    result = tools.call(name, args)
                ids = tuple(sorted({str(item.get("evidence_id")) for item in result.get("items", [])
                                    if isinstance(item, Mapping) and item.get("evidence_id")}))
                calls.append({"order": len(calls) + 1, "tool_name": name, "arguments": args,
                              "status": "OK", "returned_evidence_ids": ids,
                              "truncated": result.get("truncated", False)})
                results.append({"tool": name, "result": result})
            response = dict(self.model.generate({"prompt_version": self.prompt_version(),
                "instructions": self.instructions(), "prior_tool_results": results,
                "candidate_source": candidate_source.value, "h1_comparison": comparison}))
        raw = response.get("report", response)
        if not isinstance(raw, Mapping): raise ValueError("RCA_REPORT_CONTRACT_FAILURE")
        repairs: list[Mapping[str, Any]] = []
        try:
            report = self._validated_report(incident, raw, len(calls), model_metadata or {}, tools, h1_ids)
        except ValueError as error:
            if self.budget.max_output_repairs == 0:
                self._transition(states, InvestigationState.TECHNICAL_FAILURE)
                raise ValueError(f"RCA_REPORT_CONTRACT_FAILURE:{error}") from error
            repairs.append({"attempt": 1, "error_code": str(error), "status": "REQUESTED"})
            try:
                raw = self._repair(raw, error, request)
                report = self._validated_report(incident, raw, len(calls), model_metadata or {}, tools, h1_ids)
            except ValueError as repair_error:
                repairs[-1] = {**repairs[-1], "status": "FAILED", "repair_error_code": str(repair_error)}
                self._transition(states, InvestigationState.TECHNICAL_FAILURE)
                raise ValueError(f"RCA_REPORT_CONTRACT_FAILURE:{repair_error}") from repair_error
            repairs[-1] = {**repairs[-1], "status": "SUCCEEDED"}
        self._transition(states, InvestigationState.ABSTAIN_READY if report.status == "INSUFFICIENT_EVIDENCE" else InvestigationState.READY_TO_REPORT)
        return report, {"schema_version": RCA_AGENT_V2_1_TRACE_VERSION,
            "status_contract_version": RCA_AGENT_V2_1_STATUS_CONTRACT_VERSION,
            "prompt_version": self.prompt_version(), "tool_schema_version": "read_only_rca_tools_v2",
            "candidate_source": candidate_source.value, "states": states,
            "h1_profile_preload": {"profile_count": len(preload), "profile_candidate_ids": sorted(h1_ids), "comparison": comparison},
            "fallback": fallback, "tool_calls": calls, "repairs": repairs,
            "budget": {"max_tool_calls": self.budget.max_tool_calls, "max_h1_profiles": self.budget.max_h1_profiles,
                       "max_evidence_per_tool_call": self.budget.max_evidence_per_tool_call,
                       "max_output_repairs": self.budget.max_output_repairs}}
