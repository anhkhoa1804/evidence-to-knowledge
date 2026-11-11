"""Read-only RCA investigation tools, report contract, and thin orchestration.

Nothing in this module changes eligibility, asserts causality, commits a KG
fact, or performs remediation.  Agent output is an investigation hypothesis.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .candidate_evidence_profile import CandidateEvidenceProfile, CandidateEvidenceProfileBuilder
from .hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses
from .incident_evidence_graph import CauseCandidate
from .operational_context import OperationalEvidenceContext, TopologyScope, assemble_context, load_incident_windows, snapshot_for
from .raw_preprocessing import process_dataset
from .scalable_evidence import IncidentEvidenceStore

RCA_TOOL_SCHEMA_VERSION = "read_only_rca_tools_v1"
RCA_REPORT_VERSION = "rca_report_v1"
RCA_AGENT_PROMPT_VERSION = "rca_agent_v0_prompt_v1"
RCA_ORCHESTRATOR_VERSION = "rca_orchestrator_v0"


def _json(value: Any) -> Any:
    if isinstance(value, Enum): return value.value
    # ``asdict`` deep-copies nested immutable MappingProxyType values and
    # fails with "cannot pickle mappingproxy". Read-only tool output needs a
    # structural projection, not a deep copy or a mutation of evidence.
    if is_dataclass(value): return {field.name: _json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping): return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)): return [_json(item) for item in value]
    return value


def _write(path: Path, payload: Any) -> str:
    text = json.dumps(_json(payload), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _page(rows: Sequence[Any], limit: int = 20, offset: int = 0) -> Mapping[str, Any]:
    if limit < 1 or limit > 100 or offset < 0: raise ValueError("INVALID_READ_ONLY_QUERY_PAGE")
    return {"items": [_json(item) for item in rows[offset:offset + limit]], "limit": limit, "offset": offset, "total": len(rows), "truncated": offset + limit < len(rows), "schema_version": RCA_TOOL_SCHEMA_VERSION}


class InvestigationMode(str, Enum):
    PROFILE_ONLY = "PROFILE_ONLY"
    DETERMINISTIC_BASELINE = "DETERMINISTIC_BASELINE"
    AGENT = "AGENT"


class CandidateSourceMode(str, Enum):
    H1_SHORTLIST = "H1_SHORTLIST"
    H5_EXPANDED = "H5_EXPANDED"
    H1_THEN_H5_FALLBACK = "H1_THEN_H5_FALLBACK"


@dataclass(frozen=True)
class RCAHypothesis:
    candidate_id: str
    statement: str
    supporting_evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    model_self_assessment: str | None = None


@dataclass(frozen=True)
class RCAReport:
    """A non-causal, uncalibrated investigation report."""
    incident_id: str
    status: str
    primary_hypothesis: RCAHypothesis | None
    alternative_hypotheses: tuple[RCAHypothesis, ...]
    supporting_evidence_ids: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...]
    reasoning_summary: str
    limitations: tuple[str, ...]
    abstention_reason: str | None
    tool_calls: int
    model_metadata: Mapping[str, Any]
    report_version: str = RCA_REPORT_VERSION

    def validate(self, candidate_ids: set[str], evidence_ids: set[str]) -> None:
        if self.status not in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE", "TECHNICAL_FAILURE"}:
            raise ValueError("INVALID_RCA_REPORT_STATUS")
        hypotheses = tuple(item for item in (self.primary_hypothesis, *self.alternative_hypotheses) if item is not None)
        if self.status == "RCA_HYPOTHESIS" and self.primary_hypothesis is None: raise ValueError("RCA_HYPOTHESIS_REQUIRES_PRIMARY")
        if self.status != "RCA_HYPOTHESIS" and self.primary_hypothesis is not None: raise ValueError("NON_HYPOTHESIS_MUST_NOT_HAVE_PRIMARY")
        if any(item.candidate_id not in candidate_ids for item in hypotheses): raise ValueError("RCA_REPORT_UNKNOWN_CANDIDATE")
        cited = set(self.supporting_evidence_ids) | set(self.contradictory_evidence_ids)
        cited.update(evidence for item in hypotheses for evidence in item.supporting_evidence_ids)
        if not cited.issubset(evidence_ids): raise ValueError("RCA_REPORT_UNKNOWN_EVIDENCE")
        if any(item.model_self_assessment not in {None, "LOW", "MEDIUM", "HIGH"} for item in hypotheses): raise ValueError("INVALID_MODEL_SELF_ASSESSMENT")

    def artifact(self) -> Mapping[str, Any]: return _json(self)


class ReadOnlyRCATools:
    """A bounded read-only façade over incident evidence and evidence profiles."""
    def __init__(self, context: OperationalEvidenceContext, candidates: Sequence[CauseCandidate], profiles: Sequence[CandidateEvidenceProfile], store: IncidentEvidenceStore, expanded_candidates: Sequence[CauseCandidate] = ()) -> None:
        self.context, self.store = context, store
        self.candidates = tuple(sorted(candidates, key=lambda item: (item.subject_node_id, item.candidate_id)))
        self.expanded_candidates = tuple(sorted(expanded_candidates, key=lambda item: (item.subject_node_id, item.candidate_id)))
        self.profiles = tuple(sorted(profiles, key=lambda item: (item.subject_id, item.candidate_id)))
        self._candidate = {item.candidate_id: item for item in (*self.candidates, *self.expanded_candidates)}
        self._profile = {item.candidate_id: item for item in self.profiles}
        self._evidence = {item.evidence_id: item for values in (context.events, context.changes, context.metrics, context.traces, context.relations, context.entities) for item in values}

    def _check(self, incident_id: str) -> None:
        if incident_id != self.context.incident.incident_id: raise ValueError("UNKNOWN_INCIDENT")

    def get_incident_summary(self, incident_id: str) -> Mapping[str, Any]:
        self._check(incident_id)
        return {"schema_version": RCA_TOOL_SCHEMA_VERSION, "incident_id": incident_id, "start_time": self.context.incident.start_time, "end_time": self.context.incident.end_time, "affected_entity_ids": list(self.context.incident.affected_entity_ids), "topology_scope": self.context.topology_scope.value, "evidence_counts": {"events": len(self.context.events), "changes": len(self.context.changes), "metrics": len(self.context.metrics), "traces": self.store.trace_count(), "relations": len(self.context.relations)}, "boundary": "INCIDENT_DECLARATION_AND_EVIDENCE_ARE_NOT_CAUSAL_PROOF"}

    def get_candidates(self, incident_id: str, limit: int = 20, offset: int = 0) -> Mapping[str, Any]:
        self._check(incident_id); return _page(self.candidates, limit, offset)
    def get_expanded_candidates(self, incident_id: str, limit: int = 20, offset: int = 0) -> Mapping[str, Any]:
        """Explicit H5-minus-H1 context; never selected automatically."""
        self._check(incident_id); return _page(self.expanded_candidates, limit, offset)

    def get_candidate_profile(self, incident_id: str, candidate_id: str) -> Mapping[str, Any]:
        self._check(incident_id)
        if candidate_id not in self._profile: raise ValueError("UNKNOWN_CANDIDATE")
        return {"schema_version": RCA_TOOL_SCHEMA_VERSION, "profile": self._profile[candidate_id].artifact()}

    def _by_service(self, incident_id: str, service_id: str, collection: Sequence[Any], limit: int, offset: int, attr: str) -> Mapping[str, Any]:
        self._check(incident_id); return _page(tuple(item for item in collection if getattr(item, attr) == service_id), limit, offset)
    def get_metric_evidence(self, incident_id: str, service_id: str, limit: int = 20, offset: int = 0) -> Mapping[str, Any]: return self._by_service(incident_id, service_id, self.context.metrics, limit, offset, "service_external_id")
    def get_event_evidence(self, incident_id: str, service_id: str, limit: int = 20, offset: int = 0) -> Mapping[str, Any]: return self._by_service(incident_id, service_id, self.context.events, limit, offset, "service_external_id")
    def get_change_evidence(self, incident_id: str, service_id: str, limit: int = 20, offset: int = 0) -> Mapping[str, Any]: return self._by_service(incident_id, service_id, self.context.changes, limit, offset, "target_external_id")

    def get_trace_evidence(self, incident_id: str, service_id: str, limit: int = 20, offset: int = 0) -> Mapping[str, Any]:
        self._check(incident_id)
        rows = tuple(self.store.trace_spans_for_entities((service_id,)))
        return _page(rows, limit, offset)

    def get_topology_context(self, incident_id: str, service_id: str) -> Mapping[str, Any]:
        self._check(incident_id)
        rows = tuple(item for item in self.context.relations if item.source_external_id == service_id or item.target_external_id == service_id)
        return {"schema_version": RCA_TOOL_SCHEMA_VERSION, "scope": self.context.topology_scope.value, "relations": [_json(item) for item in rows], "boundary": "BOUNDED_TOPOLOGY_CONTEXT_NOT_CAUSALITY"}

    def get_evidence_by_id(self, evidence_id: str) -> Mapping[str, Any]:
        row = self._evidence.get(evidence_id)
        if row is None: return {"schema_version": RCA_TOOL_SCHEMA_VERSION, "status": "NOT_FOUND", "evidence_id": evidence_id}
        return {"schema_version": RCA_TOOL_SCHEMA_VERSION, "status": "FOUND", "evidence": _json(row)}

    def call(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        permitted = {"get_incident_summary", "get_candidates", "get_expanded_candidates", "get_candidate_profile", "get_metric_evidence", "get_trace_evidence", "get_event_evidence", "get_change_evidence", "get_topology_context", "get_evidence_by_id"}
        if name not in permitted: raise ValueError("READ_ONLY_TOOL_NOT_PERMITTED")
        return getattr(self, name)(**dict(arguments))


class RCAAgentModel(Protocol):
    """Provider-neutral model boundary; implementations receive no secrets in artifacts."""
    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]: ...


class RCAAgentV0:
    def __init__(self, model: RCAAgentModel, *, max_tool_calls: int = 8, max_candidate_profiles: int = 5, max_evidence_per_tool_call: int = 20) -> None:
        if max_tool_calls < 0 or max_candidate_profiles < 1 or not 1 <= max_evidence_per_tool_call <= 100: raise ValueError("INVALID_AGENT_BUDGET")
        self.model, self.max_tool_calls, self.max_candidate_profiles, self.max_evidence_per_tool_call = model, max_tool_calls, max_candidate_profiles, max_evidence_per_tool_call

    @staticmethod
    def instructions() -> str:
        return "Candidate != Cause. ERROR span != Cause. Metric shift != Cause. Trace path != causal path. Temporal precedence != causality. Absence of evidence != contradiction. Do not invent metrics, logs, dependency edges, changes, causal proof, or benchmark answers. Cite only supplied evidence IDs. Abstain with INSUFFICIENT_EVIDENCE when needed."

    def prompt_version(self) -> str:
        return str(getattr(self.model, "prompt_version", RCA_AGENT_PROMPT_VERSION))

    def investigate(self, tools: ReadOnlyRCATools, candidate_source: CandidateSourceMode = CandidateSourceMode.H1_THEN_H5_FALLBACK, model_metadata: Mapping[str, Any] | None = None) -> tuple[RCAReport, Mapping[str, Any]]:
        incident = tools.context.incident.incident_id; trace: list[Mapping[str, Any]] = []
        prompt_version = self.prompt_version()
        request = {"prompt_version": prompt_version, "instructions": self.instructions(), "incident": tools.get_incident_summary(incident), "candidates": tools.get_candidates(incident, limit=self.max_candidate_profiles), "candidate_source": candidate_source.value, "tool_schema_version": RCA_TOOL_SCHEMA_VERSION}
        response = dict(self.model.generate(request)); fallback: Mapping[str, Any] | None = None
        while True:
            calls = response.get("tool_calls", [])
            if not isinstance(calls, list): raise ValueError("INVALID_AGENT_TOOL_CALL")
            if not calls: break
            if len(trace) + len(calls) > self.max_tool_calls: raise ValueError("INVALID_OR_EXCESSIVE_AGENT_TOOL_CALLS")
            results = []
            for call in calls:
                if not isinstance(call, Mapping) or not isinstance(call.get("name"), str) or not isinstance(call.get("arguments", {}), Mapping): raise ValueError("INVALID_AGENT_TOOL_CALL")
                name, args = call["name"], dict(call["arguments"])
                if name == "get_expanded_candidates":
                    if candidate_source is not CandidateSourceMode.H1_THEN_H5_FALLBACK: raise ValueError("INVALID_FALLBACK_POLICY")
                    reason = args.pop("fallback_reason", None)
                    if reason not in {"INSUFFICIENT_EVIDENCE", "AMBIGUOUS_SHORTLIST", "MISSING_MODALITY", "NO_DISTINGUISHING_SUPPORT"}: raise ValueError("INVALID_FALLBACK_REASON")
                    fallback = {"fallback_used": True, "fallback_reason": reason}
                args.setdefault("limit", self.max_evidence_per_tool_call) if name not in {"get_incident_summary", "get_candidate_profile", "get_topology_context", "get_evidence_by_id"} else None
                result = tools.call(name, args)
                ids = tuple(sorted({str(item.get("evidence_id")) for item in result.get("items", []) if isinstance(item, Mapping) and item.get("evidence_id")}))
                trace.append({"order": len(trace) + 1, "tool_name": name, "arguments": args, "status": "OK", "returned_evidence_ids": ids, "truncated": result.get("truncated", False)})
                results.append({"tool": name, "result": result})
            response = dict(self.model.generate({"prompt_version": prompt_version, "instructions": self.instructions(), "prior_tool_results": results, "candidate_source": candidate_source.value}))
        report = self._report(incident, response.get("report", response), len(trace), model_metadata or {})
        candidate_ids = set(tools._candidate); evidence_ids = set(tools._evidence)
        for profile in tools.profiles:
            evidence_ids.update(item.evidence_id for item in profile.supporting_evidence); evidence_ids.update(item.evidence_id for item in profile.context_evidence)
        report.validate(candidate_ids, evidence_ids)
        return report, {"schema_version": "rca_agent_trace_v1", "prompt_version": prompt_version, "candidate_source": candidate_source.value, "fallback": fallback or {"fallback_used": False, "fallback_reason": None}, "tool_calls": trace, "budget": {"max_tool_calls": self.max_tool_calls, "max_candidate_profiles": self.max_candidate_profiles, "max_evidence_per_tool_call": self.max_evidence_per_tool_call}}

    def _report(self, incident_id: str, raw: Mapping[str, Any], tool_calls: int, metadata: Mapping[str, Any]) -> RCAReport:
        def hypothesis(value: Any) -> RCAHypothesis | None:
            if value is None: return None
            if not isinstance(value, Mapping): raise ValueError("INVALID_AGENT_HYPOTHESIS")
            return RCAHypothesis(str(value["candidate_id"]), str(value.get("statement", "")), tuple(sorted(str(item) for item in value.get("supporting_evidence_ids", []))), tuple(sorted(str(item) for item in value.get("limitations", []))), value.get("model_self_assessment"))
        return RCAReport(incident_id, str(raw.get("status", "INSUFFICIENT_EVIDENCE")), hypothesis(raw.get("primary_hypothesis")), tuple(item for item in (hypothesis(row) for row in raw.get("alternative_hypotheses", [])) if item), tuple(sorted(str(item) for item in raw.get("supporting_evidence_ids", []))), tuple(sorted(str(item) for item in raw.get("contradictory_evidence_ids", []))), str(raw.get("reasoning_summary", "")), tuple(sorted(str(item) for item in raw.get("limitations", []))), raw.get("abstention_reason"), tool_calls, dict(metadata))


@dataclass(frozen=True)
class PreparedRCAInvestigation:
    context: OperationalEvidenceContext
    store: IncidentEvidenceStore
    h1_candidates: tuple[CauseCandidate, ...]
    h5_candidates: tuple[CauseCandidate, ...]
    profiles: tuple[CandidateEvidenceProfile, ...]


class RCAOrchestrator:
    """Thin reusable integration path. It owns no semantic or causal policy."""
    def prepare(self, manifest: Path, incident_id: str, database: Path, scope: TopologyScope = TopologyScope.ONE_HOP, incident_file: Path | None = None) -> PreparedRCAInvestigation:
        processed = process_dataset(manifest)
        incident_file = incident_file or manifest.parent / "incidents" / "incidents.csv"
        incidents = {item.incident_id: item for item in load_incident_windows(incident_file, incident_file.name)}
        if incident_id not in incidents: raise ValueError("UNKNOWN_INCIDENT")
        context = assemble_context(processed, incidents[incident_id], scope); snapshot = snapshot_for(context)
        store = IncidentEvidenceStore.from_context(database, context, exact_legacy_graph_id=True, snapshot=snapshot)
        view = store.logical_view(snapshot.snapshot_id)
        configuration = HypothesisConfiguration()
        h1 = generate_evidence_aware_hypotheses(store, view, configuration=configuration, include_metric=True, include_trace=False, include_topology=False, include_temporal_change=False)
        h5 = generate_evidence_aware_hypotheses(store, view, configuration=configuration, include_metric=True, include_trace=True, include_topology=True, include_temporal_change=True)
        union = tuple(sorted({item.candidate_id: item for item in (*h1.candidates, *h5.candidates)}.values(), key=lambda item: item.candidate_id))
        profiles = CandidateEvidenceProfileBuilder(context, store, (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(union)
        return PreparedRCAInvestigation(context, store, h1.candidates, h5.candidates, profiles)

    def run(self, prepared: PreparedRCAInvestigation, output: Path, mode: InvestigationMode, candidate_source: CandidateSourceMode = CandidateSourceMode.H1_THEN_H5_FALLBACK, agent: RCAAgentV0 | None = None, model_metadata: Mapping[str, Any] | None = None) -> RCAReport:
        candidates = prepared.h1_candidates if candidate_source is not CandidateSourceMode.H5_EXPANDED else prepared.h5_candidates
        expanded = tuple(item for item in prepared.h5_candidates if item.candidate_id not in {row.candidate_id for row in prepared.h1_candidates}) if candidate_source is CandidateSourceMode.H1_THEN_H5_FALLBACK else ()
        profiles_by_candidate = {item.candidate_id: item for item in prepared.profiles}
        profiles = tuple(profiles_by_candidate[item.candidate_id] for item in (*candidates, *expanded) if item.candidate_id in profiles_by_candidate)
        tools = ReadOnlyRCATools(prepared.context, candidates, profiles, prepared.store, expanded)
        prompt = str(getattr(agent.model, "system_prompt", RCAAgentV0.instructions())) if agent else RCAAgentV0.instructions()
        prompt_version = agent.prompt_version() if agent else RCA_AGENT_PROMPT_VERSION
        manifest = {"schema_version": RCA_ORCHESTRATOR_VERSION, "run_timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "mode": mode.value, "candidate_source": candidate_source.value, "incident_id": prepared.context.incident.incident_id, "candidate_count": len(candidates), "expanded_candidate_count": len(expanded), "candidate_profile_version": "candidate_evidence_profile_v1", "tool_schema_version": RCA_TOOL_SCHEMA_VERSION, "prompt_version": prompt_version, "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), "semantic_boundary": "READ_ONLY_NON_CAUSAL_RESEARCH_PROTOTYPE", "model_metadata": dict(model_metadata or {})}
        _write(output / "RUN_MANIFEST.json", manifest); _write(output / "INCIDENT_SUMMARY.json", tools.get_incident_summary(prepared.context.incident.incident_id)); _write(output / "CANDIDATES.json", {"candidates": candidates, "serialization_order": "deterministic ID order; not causal ranking"}); _write(output / "CANDIDATE_PROFILES.json", {"profiles": profiles})
        if mode is InvestigationMode.AGENT:
            if agent is None:
                report = RCAReport(prepared.context.incident.incident_id, "TECHNICAL_FAILURE", None, (), (), (), "No configured live or mock RCA agent model.", ("LIVE_AGENT_RUNTIME_UNAVAILABLE",), "NO_AGENT_MODEL_CONFIGURED", 0, dict(model_metadata or {}))
            else:
                try:
                    report, trace = agent.investigate(tools, candidate_source, model_metadata)
                except (ValueError, KeyError, TypeError) as exc:
                    # Invalid or unsupported model output is never coerced into
                    # an RCA claim; every agent version fails closed within its
                    # bounded run.  A V2 trace preserves its observable state
                    # prefix and records the terminal technical state.
                    if getattr(agent, "trace_schema_version", None):
                        states = list(getattr(agent, "last_states", ()))
                        if not states or states[-1] != "TECHNICAL_FAILURE": states.append("TECHNICAL_FAILURE")
                        trace = {"schema_version": getattr(agent, "trace_schema_version"), "prompt_version": prompt_version,
                                 "status": "TECHNICAL_FAILURE", "states": states, "error_type": type(exc).__name__,
                                 "error_code": str(exc), "tool_calls": []}
                    else:
                        trace = {"schema_version": "rca_agent_trace_v1", "prompt_version": prompt_version, "status": "TECHNICAL_FAILURE", "error_type": type(exc).__name__, "error_code": str(exc), "tool_calls": []}
                    report = RCAReport(prepared.context.incident.incident_id, "TECHNICAL_FAILURE", None, (), (), (), "Agent output failed structured validation.", ("INVALID_AGENT_OUTPUT",), "INVALID_AGENT_OUTPUT", 0, dict(model_metadata or {}))
                trace = {**trace, "model": {key: value for key, value in dict(model_metadata or {}).items() if key not in {"api_key", "authorization", "token", "secret", "password"}}, "final_result_status": report.status}
                _write(output / "AGENT_TRACE.json", trace)
        else:
            status = "INSUFFICIENT_EVIDENCE"
            report = RCAReport(prepared.context.incident.incident_id, status, None, (), (), (), "Profile-only and deterministic baseline modes intentionally do not select or rank a cause candidate.", ("CANDIDATES_ARE_UNRANKED_ELIGIBILITY_HYPOTHESES",), "NO_CAUSAL_OR_CALIBRATED_RANKING_IN_BASELINE", 0, {"mode": mode.value})
        _write(output / "RCA_REPORT.json", report.artifact())
        _write(output / "RCA_REPORT.md", "# RCA Investigation Report\n\nStatus: " + report.status + "\n\nThis report is an evidence-backed, non-causal research hypothesis. It is not a root-cause confirmation, calibrated confidence, remediation instruction, or canonical-KG mutation.\n")
        return report
