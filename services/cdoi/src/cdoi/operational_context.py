"""Deterministic, non-causal operational evidence-context assembly.

This module consumes immutable normalized evidence.  It does not alter
preprocessing serialization, induce schema, write a KG, or make a causal claim.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .raw_preprocessing import (
    NormalizedChangeEventEvidence,
    NormalizedEntityEvidence,
    NormalizedEventEvidence,
    NormalizedMetricEvidence,
    NormalizedRelationEvidence,
    NormalizedSemanticTerm,
    NormalizedTraceSpanEvidence,
    PreprocessingIssue,
    PreprocessingResult,
)
from .trace_evidence import TraceExecutionGraph, execution_graphs


CONTEXT_SCHEMA_VERSION = "operational_evidence_context_v1"
INCIDENT_SOURCE_VERSION = "incident_window_csv_v1"
RULE_DIRECT_ENTITY = "DIRECT_INCIDENT_ENTITY_V1"
RULE_ONE_HOP_NEIGHBOR = "ONE_HOP_TOPOLOGY_NEIGHBOR_V1"
RULE_RELATION = "RELATION_CONNECTS_SELECTED_ENTITY_V1"
RULE_EVENT = "EVENT_IN_TIME_WINDOW_V1"
RULE_CHANGE = "CHANGE_IN_TIME_WINDOW_V1"
RULE_METRIC_DIRECT = "METRIC_DIRECT_ENTITY_IN_WINDOW_V1"
RULE_METRIC_ONE_HOP = "METRIC_ONE_HOP_ENTITY_IN_WINDOW_V1"
RULE_TRACE_DIRECT = "TRACE_DIRECT_ENTITY_OVERLAPS_WINDOW_V1"
RULE_TRACE_ONE_HOP = "TRACE_ONE_HOP_ENTITY_OVERLAPS_WINDOW_V1"
RULE_UNRESOLVED_INCIDENT = "UNRESOLVED_INCIDENT_ENTITY_V1"
RULE_PREPROCESSING_UNRESOLVED = "PREPROCESSING_UNRESOLVED_EVIDENCE_V1"


class OperationalContextError(ValueError):
    """A fail-closed error in a declared incident or context request."""


class TopologyScope(str, Enum):
    DIRECT_ONLY = "DIRECT_ONLY"
    ONE_HOP = "ONE_HOP"


def _clean(value: object) -> str:
    return " ".join(str(value).replace("\ufeff", "").split())


def _parse_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationalContextError(f"INVALID_INCIDENT_TIMESTAMP: {value}") from exc
    if parsed.tzinfo is None:
        raise OperationalContextError(f"INVALID_INCIDENT_TIMESTAMP: timezone is required: {value}")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _time_key(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(_as_json(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _as_json(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _as_json(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _as_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_as_json(item) for item in value]
    return value


@dataclass(frozen=True)
class IncidentWindow:
    """A user-declared time/entity collection boundary, not a validated outage."""

    incident_id: str
    start_time: str
    end_time: str
    affected_entity_ids: tuple[str, ...]
    environment: str | None = None
    summary: str | None = None
    source: str = "USER_DECLARED_INCIDENT_CSV"
    external_incident_id: str | None = None
    provenance: Mapping[str, Any] = MappingProxyType({})
    original_start_time: str | None = None
    original_end_time: str | None = None

    def __post_init__(self) -> None:
        incident_id = _clean(self.incident_id)
        if not incident_id:
            raise OperationalContextError("INVALID_INCIDENT: incident_id is required")
        start, end = _parse_time(self.start_time), _parse_time(self.end_time)
        if start > end:
            raise OperationalContextError("INVALID_INCIDENT_INTERVAL: start_time must be <= end_time")
        affected = tuple(sorted({_clean(item) for item in self.affected_entity_ids if _clean(item)}))
        if not affected:
            raise OperationalContextError("INVALID_INCIDENT: at least one affected_entity_id is required")
        object.__setattr__(self, "incident_id", incident_id)
        object.__setattr__(self, "start_time", start)
        object.__setattr__(self, "end_time", end)
        object.__setattr__(self, "affected_entity_ids", affected)
        object.__setattr__(self, "environment", _clean(self.environment or "") or None)
        object.__setattr__(self, "summary", _clean(self.summary or "") or None)
        object.__setattr__(self, "source", _clean(self.source) or "USER_DECLARED_INCIDENT_CSV")
        object.__setattr__(self, "external_incident_id", _clean(self.external_incident_id or "") or None)
        object.__setattr__(self, "original_start_time", self.original_start_time or self.start_time)
        object.__setattr__(self, "original_end_time", self.original_end_time or self.end_time)
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))


@dataclass(frozen=True)
class EvidenceSelection:
    """Why a normalized record is in this context; this is not causal evidence."""

    evidence_id: str | None
    selection_rule: str
    raw_evidence_id: str | None
    source_file: str
    source_record_id: str


@dataclass(frozen=True)
class OperationalEvidenceContext:
    """Readonly evidence membership for a declared incident/window."""

    incident: IncidentWindow
    topology_scope: TopologyScope
    direct_entity_ids: tuple[str, ...]
    expanded_entity_ids: tuple[str, ...]
    entities: tuple[NormalizedEntityEvidence, ...]
    relations: tuple[NormalizedRelationEvidence, ...]
    events: tuple[NormalizedEventEvidence, ...]
    changes: tuple[NormalizedChangeEventEvidence, ...]
    semantic_terms: tuple[NormalizedSemanticTerm, ...]
    unresolved: tuple[PreprocessingIssue, ...]
    selections: tuple[EvidenceSelection, ...]
    dataset_id: str
    manifest_hash: str
    metrics: tuple[NormalizedMetricEvidence, ...] = ()
    traces: tuple[NormalizedTraceSpanEvidence, ...] = ()
    trace_execution_graphs: tuple[TraceExecutionGraph, ...] = ()
    context_schema_version: str = CONTEXT_SCHEMA_VERSION


@dataclass(frozen=True)
class EvidenceSnapshot:
    """Deterministic serializable context artifact for later, separate RCA work."""

    context: OperationalEvidenceContext
    snapshot_id: str
    content_sha256: str

    def artifact(self) -> dict[str, Any]:
        return {
            "schema_version": CONTEXT_SCHEMA_VERSION,
            "snapshot_id": self.snapshot_id,
            "content_sha256": self.content_sha256,
            "incident": _as_json(self.context.incident),
            "topology_scope": self.context.topology_scope.value,
            "direct_entity_ids": list(self.context.direct_entity_ids),
            "expanded_entity_ids": list(self.context.expanded_entity_ids),
            "entities": _as_json(self.context.entities),
            "relations": _as_json(self.context.relations),
            "events": _as_json(self.context.events),
            "changes": _as_json(self.context.changes),
            "metrics": _as_json(self.context.metrics),
            "traces": _as_json(self.context.traces),
            "trace_execution_graphs": _as_json(self.context.trace_execution_graphs),
            "semantic_terms": _as_json(self.context.semantic_terms),
            "unresolved": _as_json(self.context.unresolved),
            "selection_provenance": _as_json(self.context.selections),
            "dataset_id": self.context.dataset_id,
            "manifest_hash": self.context.manifest_hash,
            "semantic_term_linkage": "NOT_LINKED_BY_EXACT_ID",
        }


def load_incident_windows(path: Path, source_file: str | None = None) -> tuple[IncidentWindow, ...]:
    """Load constrained incident declarations; they are control input, not raw semantic evidence."""
    try:
        reader = csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines())
    except OSError as exc:
        raise OperationalContextError(f"INCIDENT_SOURCE_NOT_FOUND: {path}") from exc
    required = {"incident_id", "start_time", "end_time", "affected_service_ids"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise OperationalContextError("INVALID_INCIDENT_SOURCE: incident_id, start_time, end_time, affected_service_ids are required")
    source_name = source_file or path.name
    windows: list[IncidentWindow] = []
    seen: set[str] = set()
    for index, row in enumerate(reader, 2):
        incident_id = _clean(row.get("incident_id", ""))
        if incident_id in seen:
            raise OperationalContextError(f"DUPLICATE_INCIDENT_ID: {incident_id}")
        affected = tuple(part for part in (_clean(item) for item in _clean(row.get("affected_service_ids", "")).split("|")) if part)
        window = IncidentWindow(
            incident_id=incident_id,
            start_time=_clean(row.get("start_time", "")),
            end_time=_clean(row.get("end_time", "")),
            affected_entity_ids=affected,
            environment=_clean(row.get("environment", "")) or None,
            summary=_clean(row.get("summary", "")) or None,
            source=_clean(row.get("source", "")) or "USER_DECLARED_INCIDENT_CSV",
            external_incident_id=_clean(row.get("external_incident_id", "")) or None,
            provenance={"incident_input_version": INCIDENT_SOURCE_VERSION, "source_file": source_name, "source_record_id": str(index)},
            original_start_time=_clean(row.get("start_time", "")),
            original_end_time=_clean(row.get("end_time", "")),
        )
        seen.add(window.incident_id)
        windows.append(window)
    return tuple(sorted(windows, key=lambda item: item.incident_id))


def _selection(item: Any, rule: str) -> EvidenceSelection:
    provenance = item.provenance
    return EvidenceSelection(
        evidence_id=getattr(item, "evidence_id", None),
        selection_rule=rule,
        raw_evidence_id=str(provenance.get("raw_evidence_id")) if provenance.get("raw_evidence_id") else None,
        source_file=str(provenance.get("source_file", "")),
        source_record_id=str(provenance.get("source_record_id", "")),
    )


def _incident_issue(window: IncidentWindow, entity_id: str) -> PreprocessingIssue:
    provenance = window.provenance
    return PreprocessingIssue(
        status="UNRESOLVED_INCIDENT_ENTITY",
        source_id=window.source,
        source_file=str(provenance.get("source_file", "")),
        source_record_id=str(provenance.get("source_record_id", window.incident_id)),
        detail=entity_id,
    )


def assemble_context(
    result: PreprocessingResult,
    incident: IncidentWindow,
    topology_scope: TopologyScope = TopologyScope.ONE_HOP,
) -> OperationalEvidenceContext:
    """Assemble exact-ID, inclusive-time evidence without deriving causal meaning."""
    if not isinstance(topology_scope, TopologyScope):
        topology_scope = TopologyScope(topology_scope)
    inventory = {item.external_id: item for item in result.entities}
    direct_ids = tuple(sorted(entity_id for entity_id in incident.affected_entity_ids if entity_id in inventory))
    incident_issues = tuple(_incident_issue(incident, entity_id) for entity_id in incident.affected_entity_ids if entity_id not in inventory)
    direct_set = set(direct_ids)
    selected_relations = tuple(sorted(
        (row for row in result.relations if row.source_external_id in direct_set or row.target_external_id in direct_set),
        key=lambda item: item.evidence_id,
    ))
    neighbor_ids: set[str] = set()
    if topology_scope is TopologyScope.ONE_HOP:
        for row in selected_relations:
            if row.source_external_id in direct_set:
                neighbor_ids.add(row.target_external_id)
            if row.target_external_id in direct_set:
                neighbor_ids.add(row.source_external_id)
    expanded_ids = tuple(sorted(direct_set | {item for item in neighbor_ids if item in inventory}))
    selected_entities = tuple(inventory[item] for item in expanded_ids)
    selected_set = set(expanded_ids)
    events = tuple(sorted(
        (row for row in result.events if row.service_external_id in selected_set and incident.start_time <= row.observed_at <= incident.end_time),
        key=lambda item: (item.observed_at, item.evidence_id),
    ))
    changes = tuple(sorted(
        (row for row in result.changes if row.target_external_id in selected_set and incident.start_time <= row.observed_at <= incident.end_time),
        key=lambda item: (item.observed_at, item.evidence_id),
    ))
    metrics = tuple(sorted(
        (row for row in result.metrics if row.service_external_id in selected_set and incident.start_time <= row.observed_at <= incident.end_time),
        key=lambda item: (item.service_external_id, item.series_key, item.observed_at, item.evidence_id),
    ))
    traces = tuple(sorted(
        (row for row in result.traces if row.service_external_id in selected_set and _time_key(row.observed_at) <= _time_key(incident.end_time) and _time_key(row.end_time) >= _time_key(incident.start_time)),
        key=lambda item: (item.trace_id, _time_key(item.observed_at), item.span_id, item.evidence_id),
    ))
    all_graph_statuses = {graph.trace_id: graph.status for graph in execution_graphs(result.traces)}
    graphs = tuple(replace(graph, status=all_graph_statuses.get(graph.trace_id, graph.status)) for graph in execution_graphs(traces))
    selections: list[EvidenceSelection] = []
    for entity in selected_entities:
        selections.append(_selection(entity, RULE_DIRECT_ENTITY if entity.external_id in direct_set else RULE_ONE_HOP_NEIGHBOR))
    selections.extend(_selection(row, RULE_RELATION) for row in selected_relations)
    selections.extend(_selection(row, RULE_EVENT) for row in events)
    selections.extend(_selection(row, RULE_CHANGE) for row in changes)
    selections.extend(_selection(row, RULE_METRIC_DIRECT if row.service_external_id in direct_set else RULE_METRIC_ONE_HOP) for row in metrics)
    selections.extend(_selection(row, RULE_TRACE_DIRECT if row.service_external_id in direct_set else RULE_TRACE_ONE_HOP) for row in traces)
    selections.extend(EvidenceSelection(None, RULE_UNRESOLVED_INCIDENT, None, item.source_file, item.source_record_id) for item in incident_issues)
    selections.extend(EvidenceSelection(item.raw_evidence_id, RULE_PREPROCESSING_UNRESOLVED, item.raw_evidence_id, item.source_file, item.source_record_id) for item in result.unresolved)
    return OperationalEvidenceContext(
        incident=incident,
        topology_scope=topology_scope,
        direct_entity_ids=direct_ids,
        expanded_entity_ids=expanded_ids,
        entities=selected_entities,
        relations=selected_relations,
        events=events,
        changes=changes,
        metrics=metrics,
        traces=traces,
        trace_execution_graphs=graphs,
        semantic_terms=(),
        unresolved=tuple(sorted((*result.unresolved, *incident_issues), key=lambda item: (item.source_file, item.source_record_id, item.status, item.detail))),
        selections=tuple(sorted(selections, key=lambda item: (item.selection_rule, item.evidence_id or "", item.source_file, item.source_record_id))),
        dataset_id=result.manifest.dataset_id,
        manifest_hash=result.manifest_hash,
    )


def snapshot_for(context: OperationalEvidenceContext) -> EvidenceSnapshot:
    """Create the stable snapshot identifier from content, not runtime metadata."""
    content = {
        "context_schema_version": context.context_schema_version,
        "incident": _as_json(context.incident),
        "topology_scope": context.topology_scope,
        "direct_entity_ids": context.direct_entity_ids,
        "expanded_entity_ids": context.expanded_entity_ids,
        "entities": context.entities,
        "relations": context.relations,
        "events": context.events,
        "changes": context.changes,
        "metrics": context.metrics,
        "traces": context.traces,
        "trace_execution_graphs": context.trace_execution_graphs,
        "semantic_terms": context.semantic_terms,
        "unresolved": context.unresolved,
        "selections": context.selections,
        "dataset_id": context.dataset_id,
        "manifest_hash": context.manifest_hash,
    }
    content_hash = _stable_hash(content)
    return EvidenceSnapshot(context=context, snapshot_id="snapshot-" + content_hash[:24], content_sha256=content_hash)


def write_snapshot(snapshot: EvidenceSnapshot, output: Path) -> Mapping[str, Any]:
    """Write one deterministic snapshot; no ontology, KG, or approval state is touched."""
    output.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot.artifact(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path = output / f"{snapshot.context.incident.incident_id}.json"
    path.write_text(text, encoding="utf-8")
    return {"path": path.name, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "snapshot_id": snapshot.snapshot_id}
