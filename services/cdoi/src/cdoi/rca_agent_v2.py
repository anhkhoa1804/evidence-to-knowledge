"""Versioned V2 RCA investigation control flow.

V2 is deliberately a research-only, read-only wrapper around the existing
candidate and evidence contracts.  It neither changes H1/H5 generation nor
turns an eligibility candidate into a causal finding.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol

from .candidate_evidence_profile import CandidateEvidenceProfile
from .rca_investigation import (
    CandidateSourceMode,
    RCAAgentV0,
    RCAReport,
    RCA_TOOL_SCHEMA_VERSION,
    ReadOnlyRCATools,
)

RCA_AGENT_V2_PROMPT_VERSION = "rca_agent_qwen_v2"
RCA_AGENT_V2_TRACE_VERSION = "rca_agent_trace_v2"
RCA_AGENT_V2_TOOL_SCHEMA_VERSION = "read_only_rca_tools_v2"

FALLBACK_REASONS = frozenset({
    "H1_AMBIGUOUS",
    "MISSING_DISTINGUISHING_SIGNAL",
    "CONFLICTING_H1_EVIDENCE",
    "RELEVANT_MODALITY_MISSING",
})


class InvestigationState(str, Enum):
    INITIALIZED = "INITIALIZED"
    H1_PROFILES_LOADED = "H1_PROFILES_LOADED"
    H1_COMPARED = "H1_COMPARED"
    TARGETED_INVESTIGATION = "TARGETED_INVESTIGATION"
    H5_EXPANDED = "H5_EXPANDED"
    READY_TO_REPORT = "READY_TO_REPORT"
    ABSTAIN_READY = "ABSTAIN_READY"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


class RCAAgentV2Model(Protocol):
    prompt_version: str
    system_prompt: str

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str,
                      request: Mapping[str, Any]) -> Mapping[str, Any]: ...


def _profile_view(profile: CandidateEvidenceProfile) -> Mapping[str, Any]:
    """Bounded deterministic profile projection safe for first-turn context."""
    return {
        "profile_id": profile.profile_id,
        "candidate_id": profile.candidate_id,
        "service_id": profile.subject_id,
        "eligibility_sources": list(profile.eligibility_sources),
        "metric_evidence": [dict(item) for item in profile.metric_evidence],
        "trace_evidence": dict(profile.trace_evidence),
        "event_evidence": dict(profile.event_evidence),
        "change_evidence": [dict(item) for item in profile.change_evidence],
        "topology_evidence": dict(profile.topology_evidence),
        "temporal_context": [dict(item) for item in profile.temporal_context],
        "missing_evidence": list(profile.missing_evidence),
        "supporting_evidence": [
            {"evidence_id": item.evidence_id, "evidence_type": item.evidence_type,
             "observed_at": item.observed_at, "source_file": item.source_file}
            for item in profile.supporting_evidence
        ],
        "contradictory_evidence": [
            {"evidence_id": item.evidence_id, "evidence_type": item.evidence_type,
             "observed_at": item.observed_at, "source_file": item.source_file}
            for item in profile.contradictory_evidence
        ],
        "context_evidence": [
            {"evidence_id": item.evidence_id, "evidence_type": item.evidence_type,
             "observed_at": item.observed_at, "source_file": item.source_file}
            for item in profile.context_evidence
        ],
        "boundary": "PROFILE_IS_OBSERVABLE_EVIDENCE_NOT_CAUSAL_PROOF",
    }


@dataclass(frozen=True)
class V2AgentBudget:
    max_tool_calls: int = 8
    max_h1_profiles: int = 20
    max_evidence_per_tool_call: int = 20
    max_output_repairs: int = 1

    def validate(self) -> None:
        if (self.max_tool_calls < 0 or self.max_h1_profiles < 1 or
                not 1 <= self.max_evidence_per_tool_call <= 100 or
                not 0 <= self.max_output_repairs <= 1):
            raise ValueError("INVALID_V2_AGENT_BUDGET")


class RCAAgentV2(RCAAgentV0):
    """Investigation-before-abstention V2 agent.

    All H1 profiles are put into the initial request.  An abstention therefore
    remains valid only when its response proves that these exact H1 candidates
    were compared and provides an observable unresolved-evidence reason.
    """
    def __init__(self, model: RCAAgentV2Model, *, budget: V2AgentBudget = V2AgentBudget()) -> None:
        budget.validate()
        super().__init__(model, max_tool_calls=budget.max_tool_calls,
                         max_candidate_profiles=budget.max_h1_profiles,
                         max_evidence_per_tool_call=budget.max_evidence_per_tool_call)
        self.budget = budget
        self.trace_schema_version = RCA_AGENT_V2_TRACE_VERSION
        self.last_states: list[str] = []

    @staticmethod
    def instructions() -> str:
        return " ".join((
            "You are a read-only RCA investigation assistant, not a causal prover.",
            "All H1 CandidateEvidenceProfiles are preloaded and must be compared before reporting INSUFFICIENT_EVIDENCE.",
            "Candidate, metric shift, ERROR span, trace path, temporal precedence, and topology adjacency are not causal proof.",
            "Use only supplied evidence IDs. Do not invent telemetry, topology, deployment, or benchmark answers.",
            "For an abstention include investigated_candidate_ids exactly matching H1, comparison_completed=true,",
            "an abstention_reason, and non-empty missing_or_conflicting_evidence.",
            "Use get_expanded_candidates only after H1 comparison and only with one permitted fallback_reason.",
            "Return exactly one JSON report object; RCA_HYPOTHESIS requires a primary_hypothesis.",
        ))

    def prompt_version(self) -> str:
        return str(getattr(self.model, "prompt_version", RCA_AGENT_V2_PROMPT_VERSION))

    @staticmethod
    def _transition(states: list[str], state: InvestigationState) -> None:
        states.append(state.value)

    def _abstention_contract(self, raw: Mapping[str, Any], h1_ids: set[str]) -> None:
        if str(raw.get("status", "")) != "INSUFFICIENT_EVIDENCE":
            return
        seen = raw.get("investigated_candidate_ids")
        if not isinstance(seen, list) or {str(item) for item in seen} != h1_ids:
            raise ValueError("V2_ABSTENTION_H1_COMPARISON_REQUIRED")
        if raw.get("comparison_completed") is not True:
            raise ValueError("V2_ABSTENTION_H1_COMPARISON_REQUIRED")
        if not isinstance(raw.get("abstention_reason"), str) or not raw["abstention_reason"].strip():
            raise ValueError("V2_ABSTENTION_REASON_REQUIRED")
        unresolved = raw.get("missing_or_conflicting_evidence")
        if not isinstance(unresolved, list) or not any(isinstance(item, str) and item.strip() for item in unresolved):
            raise ValueError("V2_ABSTENTION_DETAIL_REQUIRED")

    def _repair(self, raw: Mapping[str, Any], error: ValueError, request: Mapping[str, Any]) -> Mapping[str, Any]:
        repair = getattr(self.model, "repair_output", None)
        if not callable(repair):
            raise error
        repaired = repair(raw, str(error), request)
        if not isinstance(repaired, Mapping):
            raise ValueError("V2_REPAIR_OUTPUT_INVALID")
        return dict(repaired.get("report", repaired))

    def investigate(self, tools: ReadOnlyRCATools,
                    candidate_source: CandidateSourceMode = CandidateSourceMode.H1_THEN_H5_FALLBACK,
                    model_metadata: Mapping[str, Any] | None = None) -> tuple[RCAReport, Mapping[str, Any]]:
        if candidate_source is not CandidateSourceMode.H1_THEN_H5_FALLBACK:
            raise ValueError("V2_REQUIRES_H1_THEN_H5_FALLBACK")
        incident = tools.context.incident.incident_id
        states: list[str] = []; self.last_states = states
        self._transition(states, InvestigationState.INITIALIZED)
        h1 = tuple(tools.candidates)
        if len(h1) > self.budget.max_h1_profiles:
            raise ValueError("V2_H1_PROFILE_PRELOAD_BUDGET_EXCEEDED")
        profiles = tuple(profile for profile in tools.profiles if profile.candidate_id in {item.candidate_id for item in h1})
        h1_ids = {item.candidate_id for item in h1}
        if {item.candidate_id for item in profiles} != h1_ids:
            raise ValueError("V2_H1_PROFILE_PRELOAD_INCOMPLETE")
        preload = [_profile_view(item) for item in profiles]
        self._transition(states, InvestigationState.H1_PROFILES_LOADED)
        # The deterministic comparison record means V2 cannot treat an unseen
        # profile as a basis for an early abstention.
        comparison = {"compared_candidate_ids": sorted(h1_ids), "comparison_basis": "PRELOADED_H1_CANDIDATE_EVIDENCE_PROFILES"}
        self._transition(states, InvestigationState.H1_COMPARED)
        request: Mapping[str, Any] = {
            "prompt_version": self.prompt_version(), "instructions": self.instructions(),
            "incident": tools.get_incident_summary(incident),
            "candidates": tools.get_candidates(incident, limit=self.budget.max_h1_profiles),
            "preloaded_candidate_profiles": preload, "h1_comparison": comparison,
            "candidate_source": candidate_source.value,
            "tool_schema_version": RCA_AGENT_V2_TOOL_SCHEMA_VERSION,
            "report_schema": "RCAReport plus V2 abstention fields",
        }
        response = dict(self.model.generate(request))
        calls: list[Mapping[str, Any]] = []
        fallback: Mapping[str, Any] = {"fallback_used": False, "fallback_reason": None,
                                       "additional_candidates_exposed": 0}
        while True:
            requested = response.get("tool_calls", [])
            if not isinstance(requested, list):
                raise ValueError("INVALID_AGENT_TOOL_CALL")
            if not requested:
                break
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
                    if reason not in FALLBACK_REASONS:
                        raise ValueError("V2_INVALID_FALLBACK_REASON")
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
            response = dict(self.model.generate({"prompt_version": self.prompt_version(), "instructions": self.instructions(),
                                                  "prior_tool_results": results,
                                                  "candidate_source": candidate_source.value,
                                                  "h1_comparison": comparison}))
        raw = response.get("report", response)
        if not isinstance(raw, Mapping):
            raise ValueError("INVALID_AGENT_REPORT")
        repairs: list[Mapping[str, Any]] = []
        try:
            self._abstention_contract(raw, h1_ids)
            report = self._report(incident, raw, len(calls), model_metadata or {})
            evidence_ids = set(tools._evidence)
            for profile in tools.profiles:
                evidence_ids.update(item.evidence_id for item in profile.supporting_evidence)
                evidence_ids.update(item.evidence_id for item in profile.context_evidence)
            report.validate(set(tools._candidate), evidence_ids)
        except ValueError as error:
            if self.budget.max_output_repairs == 0:
                self._transition(states, InvestigationState.TECHNICAL_FAILURE)
                raise
            repairs.append({"attempt": 1, "error_code": str(error), "status": "REQUESTED"})
            raw = self._repair(raw, error, request)
            self._abstention_contract(raw, h1_ids)
            report = self._report(incident, raw, len(calls), model_metadata or {})
            evidence_ids = set(tools._evidence)
            for profile in tools.profiles:
                evidence_ids.update(item.evidence_id for item in profile.supporting_evidence)
                evidence_ids.update(item.evidence_id for item in profile.context_evidence)
            report.validate(set(tools._candidate), evidence_ids)
            repairs[-1] = {**repairs[-1], "status": "SUCCEEDED"}
        if report.status == "INSUFFICIENT_EVIDENCE":
            self._transition(states, InvestigationState.ABSTAIN_READY)
        else:
            self._transition(states, InvestigationState.READY_TO_REPORT)
        return report, {
            "schema_version": RCA_AGENT_V2_TRACE_VERSION,
            "prompt_version": self.prompt_version(), "tool_schema_version": RCA_AGENT_V2_TOOL_SCHEMA_VERSION,
            "candidate_source": candidate_source.value, "states": states,
            "h1_profile_preload": {"profile_count": len(preload), "profile_candidate_ids": sorted(h1_ids),
                                   "comparison": comparison},
            "fallback": fallback, "tool_calls": calls, "repairs": repairs,
            "budget": {"max_tool_calls": self.budget.max_tool_calls,
                       "max_h1_profiles": self.budget.max_h1_profiles,
                       "max_evidence_per_tool_call": self.budget.max_evidence_per_tool_call,
                       "max_output_repairs": self.budget.max_output_repairs},
        }
