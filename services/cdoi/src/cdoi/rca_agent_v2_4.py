"""Separately versioned V2.4 exact-exposure and repair integration."""
from __future__ import annotations

from typing import Any, Mapping

from .rca_agent_v2_3 import RCAAgentV23
from .rca_investigation import RCAReport, ReadOnlyRCATools
from .staged_rca_backend_v2_4 import StagedRCAAgentV24Model

RCA_AGENT_V2_4_PROMPT_VERSION = "rca_agent_staged_reliability_v2_4"
RCA_AGENT_V2_4_TRACE_VERSION = "rca_agent_trace_v2_4"


def validate_exposed_report(report: RCAReport, candidate_ids: set[str], evidence_ids: set[str],
                            evidence_by_candidate: Mapping[str, set[str]]) -> None:
    """Reject IDs outside the model-visible set and cross-candidate citations."""
    report.validate(candidate_ids, evidence_ids)
    referenced = set(report.supporting_evidence_ids) | set(report.contradictory_evidence_ids)
    for hypothesis in (report.primary_hypothesis, *report.alternative_hypotheses):
        if hypothesis is None:
            continue
        referenced.update(hypothesis.supporting_evidence_ids)
        allowed = evidence_by_candidate.get(hypothesis.candidate_id, set())
        if not set(hypothesis.supporting_evidence_ids) <= allowed:
            raise ValueError("RCA_REPORT_CANDIDATE_EVIDENCE_SCOPE_VIOLATION")
    if not referenced <= evidence_ids:
        raise ValueError("RCA_REPORT_UNEXPOSED_EVIDENCE")


class RCAAgentV24(RCAAgentV23):
    trace_schema_version = RCA_AGENT_V2_4_TRACE_VERSION

    def __init__(self, model: StagedRCAAgentV24Model, *, budget=None) -> None:
        super().__init__(model, budget=budget)
        self.trace_schema_version = RCA_AGENT_V2_4_TRACE_VERSION

    def _validated_report(self, incident: str, raw: Mapping[str, Any], calls: int,
                          metadata: Mapping[str, Any], tools: ReadOnlyRCATools,
                          h1_ids: set[str]) -> RCAReport:
        report = super()._validated_report(incident, raw, calls, metadata, tools, h1_ids)
        candidate_ids = set(getattr(self.model, "exposed_candidate_ids", set()))
        evidence_ids = set(getattr(self.model, "exposed_evidence_ids", set()))
        evidence_by_candidate = {key: set(value) for key, value in
                                 getattr(self.model, "evidence_by_candidate", {}).items()}
        # Include exact serialized IDs from H1 profiles; they were in the initial prompt.
        for profile in tools.profiles:
            candidate_id = profile.candidate_id
            candidate_ids.add(candidate_id)
            evidence_by_candidate.setdefault(candidate_id, set()).update(
                item.evidence_id for item in (*profile.supporting_evidence, *profile.context_evidence))
            evidence_ids.update(item.evidence_id for item in (*profile.supporting_evidence, *profile.context_evidence))
        validate_exposed_report(report, candidate_ids or set(tools._candidate),
                                evidence_ids, evidence_by_candidate)
        return report

    def _repair(self, raw: Mapping[str, Any], error: ValueError,
                request: Mapping[str, Any]) -> Mapping[str, Any]:
        repair = getattr(self.model, "repair_output", None)
        if not callable(repair):
            raise error
        repaired = repair(raw, str(error), request)
        if not isinstance(repaired, Mapping):
            raise ValueError("V24_REPAIR_OUTPUT_INVALID")
        report = repaired.get("report", repaired)
        if not isinstance(report, Mapping):
            raise ValueError("V24_REPAIR_REPORT_INVALID")
        original_status = raw.get("status")
        if original_status in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"} and report.get("status") != original_status:
            raise ValueError("V24_REPAIR_STATUS_CHANGED")
        return dict(report)
