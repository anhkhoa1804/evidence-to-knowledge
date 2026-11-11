"""Deterministic, GT-free characterization of unranked RCA candidates.

Profiles describe observable incident evidence.  They are deliberately not
scores, causal assertions, or calibrated confidence estimates.
"""
from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from .hypothesis_generation import AggregateEvidence
from .incident_evidence_graph import CauseCandidate
from .operational_context import OperationalEvidenceContext
from .scalable_evidence import IncidentEvidenceStore

CANDIDATE_EVIDENCE_PROFILE_VERSION = "candidate_evidence_profile_v1"


def _json(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return value


def _profile_id(incident_id: str, subject_id: str, candidate_id: str) -> str:
    # A candidate ID disambiguates distinct frozen rule bundles for one subject;
    # the stable identity is still derived from incident, subject, and version.
    payload = "\x1f".join((CANDIDATE_EVIDENCE_PROFILE_VERSION, incident_id, subject_id, candidate_id))
    return "candidate-profile-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _time_relation(observed_at: str | None, incident_start: str) -> str:
    if not observed_at:
        return "UNKNOWN"
    observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    start = datetime.fromisoformat(incident_start.replace("Z", "+00:00"))
    if observed < start:
        return "PRECEDES"
    if observed > start:
        return "FOLLOWS"
    return "OVERLAPS"


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    evidence_type: str
    observed_at: str | None
    source_file: str | None


@dataclass(frozen=True)
class CandidateEvidenceProfile:
    """A stable evidence description, never a claim that a candidate is a cause."""

    profile_id: str
    candidate_id: str
    incident_id: str
    subject_id: str
    eligibility_sources: tuple[str, ...]
    metric_evidence: tuple[Mapping[str, Any], ...]
    trace_evidence: Mapping[str, Any]
    event_evidence: Mapping[str, Any]
    change_evidence: tuple[Mapping[str, Any], ...]
    topology_evidence: Mapping[str, Any]
    temporal_context: tuple[Mapping[str, Any], ...]
    supporting_evidence: tuple[EvidenceReference, ...]
    contradictory_evidence: tuple[EvidenceReference, ...]
    context_evidence: tuple[EvidenceReference, ...]
    missing_evidence: tuple[str, ...]
    provenance: Mapping[str, Any]
    schema_version: str = CANDIDATE_EVIDENCE_PROFILE_VERSION

    def artifact(self) -> dict[str, Any]:
        return _json(self)


class CandidateEvidenceProfileBuilder:
    """Read-only profile builder. Candidate membership is never changed here."""

    def __init__(self, context: OperationalEvidenceContext, store: IncidentEvidenceStore, aggregates: Iterable[AggregateEvidence] = ()) -> None:
        self.context, self.store = context, store
        self.aggregates = tuple(sorted(aggregates, key=lambda item: item.evidence_id))
        self._by_id = {
            item.evidence_id: item
            for collection in (context.events, context.changes, context.metrics, context.traces, context.relations, context.entities)
            for item in collection
        }

    def _reference(self, evidence_id: str) -> EvidenceReference:
        row = self._by_id.get(evidence_id)
        if row is None:
            aggregate = next((item for item in self.aggregates if item.evidence_id == evidence_id), None)
            if aggregate:
                return EvidenceReference(evidence_id, aggregate.evidence_type, aggregate.time_start, None)
            return EvidenceReference(evidence_id, "AGGREGATE_OR_UNAVAILABLE", None, None)
        return EvidenceReference(
            evidence_id,
            type(row).__name__,
            getattr(row, "observed_at", None),
            str(getattr(row, "provenance", {}).get("source_file", "")) or None,
        )

    def build(self, candidate: CauseCandidate) -> CandidateEvidenceProfile:
        if candidate.incident_id != self.context.incident.incident_id:
            raise ValueError("CANDIDATE_INCIDENT_MISMATCH")
        service = candidate.subject_node_id.removeprefix("entity:")
        metrics = [item for item in self.context.metrics if item.service_external_id == service]
        events = [item for item in self.context.events if item.service_external_id == service]
        changes = [item for item in self.context.changes if item.target_external_id == service]
        aggregates = [item for item in self.aggregates if item.service_external_id == service]
        metric_rows: list[Mapping[str, Any]] = []
        for row in aggregates:
            if row.evidence_type == "METRIC_LEVEL_SHIFT_AGGREGATE":
                metric_rows.append({"aggregate_evidence_id": row.evidence_id, "series_key": row.attributes.get("series_key"), "metric_kind": row.attributes.get("metric_kind"), "unit": row.attributes.get("unit"), "pre_count": row.attributes.get("pre_observation_count"), "post_count": row.attributes.get("post_observation_count"), "pre_median": row.attributes.get("pre_median"), "post_median": row.attributes.get("post_median"), "relative_level_shift": row.attributes.get("relative_median_shift"), "persistent_excursion_fraction": row.attributes.get("persistent_post_fraction"), "source_evidence_ids_sha256": row.input_evidence_sha256, "eligibility_triggered": row.rule_id in candidate.generation_rules})
        if not metric_rows and metrics:
            grouped: dict[str, list[Any]] = {}
            for item in metrics:
                grouped.setdefault(item.series_key, []).append(item)
            for series, rows in sorted(grouped.items()):
                metric_rows.append({"series_key": series, "metric_kind": rows[0].metric_kind, "unit": rows[0].unit, "observation_count": len(rows), "median": statistics.median(item.value for item in rows), "representative_evidence_ids": tuple(item.evidence_id for item in rows[:5]), "eligibility_triggered": False})
        trace_counts = self.store.trace_counts_for_entities((service,)).get(service, {"trace_span_count": 0, "error_trace_span_count": 0})
        trace_rows = list(self.store.trace_spans_for_entities((service,)))
        operations = tuple(sorted({item.operation for item in self.context.traces if item.service_external_id == service and item.operation}))
        upstream, downstream = set(), set()
        relation_ids: list[str] = []
        for relation in self.context.relations:
            if relation.target_external_id == service:
                upstream.add(relation.source_external_id); relation_ids.append(relation.evidence_id)
            if relation.source_external_id == service:
                downstream.add(relation.target_external_id); relation_ids.append(relation.evidence_id)
        errors = self.store.trace_error_evidence_for_entities((service,)).get(service, ())
        trace_profile = {"trace_span_count": trace_counts["trace_span_count"], "error_trace_span_count": trace_counts["error_trace_span_count"], "unresolved_parent_count": self.store.unresolved_parent_count_for_entity(service), "representative_evidence_ids": tuple(row["evidence_id"] for row in trace_rows[:5]), "error_evidence_ids": tuple(errors[:10]), "operation_distribution": operations, "upstream_observed_services": tuple(sorted(upstream)), "downstream_observed_services": tuple(sorted(downstream)), "interpretation_boundary": "TRACE_PATH_NOT_CAUSAL_PATH; ERROR_SPAN_NOT_ROOT_CAUSE"}
        severity: dict[str, int] = {}
        for event in events:
            severity[event.severity or "UNSPECIFIED"] = severity.get(event.severity or "UNSPECIFIED", 0) + 1
        event_profile = {"event_count": len(events), "severity_distribution": dict(sorted(severity.items())), "representative_evidence_ids": tuple(item.evidence_id for item in events[:5]), "first_event_time": events[0].observed_at if events else None, "last_event_time": events[-1].observed_at if events else None, "identity_status": tuple(sorted({item.correlation_status for item in events})) or ("NO_EVENT_EVIDENCE",)}
        change_rows = tuple({"evidence_id": item.evidence_id, "change_id": item.change_id, "change_type": item.change_type, "timestamp": item.observed_at, "time_relation_to_incident": _time_relation(item.observed_at, self.context.incident.start_time), "target_external_id": item.target_external_id, "source_file": item.provenance.get("source_file"), "interpretation_boundary": "TEMPORAL_PRECEDENCE_NOT_CAUSALITY"} for item in changes)
        temporal = []
        for family, rows in (("EVENT", events), ("CHANGE", changes), ("METRIC", metrics)):
            if rows:
                first = min(item.observed_at for item in rows)
                temporal.append({"evidence_family": family, "first_observed_at": first, "incident_start": self.context.incident.start_time, "relation_to_incident_start": _time_relation(first, self.context.incident.start_time)})
        support_ids = tuple(sorted(set(candidate.supporting_evidence_ids)))
        context_ids = tuple(sorted(set(candidate.context_evidence_ids)))
        missing = []
        if not metrics: missing.append("MISSING_METRIC_EVIDENCE")
        if not trace_rows: missing.append("MISSING_TRACE_EVIDENCE")
        if not events: missing.append("MISSING_EVENT_EVIDENCE")
        if not changes: missing.append("MISSING_CHANGE_EVIDENCE")
        return CandidateEvidenceProfile(
            _profile_id(candidate.incident_id, service, candidate.candidate_id), candidate.candidate_id, candidate.incident_id, service,
            tuple(sorted(candidate.generation_rules)), tuple(metric_rows), trace_profile, event_profile, change_rows,
            {"scope": self.context.topology_scope.value, "direct_upstream": tuple(sorted(upstream)), "direct_downstream": tuple(sorted(downstream)), "relation_evidence_ids": tuple(sorted(set(relation_ids))), "interpretation_boundary": "TOPOLOGY_ADJACENCY_NOT_CAUSALITY"},
            tuple(sorted(temporal, key=lambda item: item["evidence_family"])), tuple(self._reference(item) for item in support_ids), tuple(), tuple(self._reference(item) for item in context_ids), tuple(missing),
            {"dataset_id": self.context.dataset_id, "manifest_hash": self.context.manifest_hash, "snapshot_boundary": "INCIDENT_SCOPED_READ_ONLY"},
        )

    def build_all(self, candidates: Sequence[CauseCandidate]) -> tuple[CandidateEvidenceProfile, ...]:
        return tuple(sorted((self.build(item) for item in candidates), key=lambda item: (item.subject_id, item.candidate_id)))
