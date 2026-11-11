"""SQLite-backed logical evidence access for research-scale incident evaluation.

The module does not alter incident_evidence_graph_v1 or cause_candidate_v1.
It keeps every selected trace span addressable on disk while materializing only
candidate-relevant query results.  Small contexts can request an exhaustive
graph identifier to prove exact candidate equivalence with the frozen path.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from .incident_evidence_graph import CauseCandidate, build_incident_evidence_graph
from .operational_context import EvidenceSnapshot, OperationalEvidenceContext
from .raw_preprocessing import (
    NormalizedChangeEventEvidence, NormalizedEventEvidence, NormalizedMetricEvidence,
    NormalizedTraceSpanEvidence,
)

STORE_VERSION = "incident_evidence_store_v1"
VIEW_VERSION = "incident_evidence_graph_view_v1"


def _hash(parts: Sequence[str]) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _candidate_id(incident_id: str, kind: str, owner: str, support: Sequence[str], graph_id: str) -> str:
    return "candidate-" + _hash([incident_id, kind, owner, *sorted(set(support)), graph_id])[:24]


@dataclass(frozen=True)
class ResourceConfiguration:
    trace_chunk_size: int = 1000
    query_page_size: int = 1000


@dataclass(frozen=True)
class IncidentEvidenceGraphView:
    """A complete logical graph whose trace rows remain disk-addressable."""

    incident_id: str
    graph_id: str
    snapshot_id: str | None
    trace_count: int
    resource_configuration: ResourceConfiguration
    schema_version: str = VIEW_VERSION


class IncidentEvidenceStore:
    """Deterministic local SQLite index with no ground-truth fields."""

    def __init__(self, database: Path, context: OperationalEvidenceContext, *, resource_configuration: ResourceConfiguration = ResourceConfiguration(), legacy_graph_id: str | None = None) -> None:
        self.database = database
        self.context = context
        self.resource_configuration = resource_configuration
        self._legacy_graph_id = legacy_graph_id
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database)
        self.connection.execute("PRAGMA journal_mode=OFF")
        self.connection.execute("PRAGMA synchronous=OFF")
        self.connection.execute("CREATE TABLE IF NOT EXISTS trace_span (evidence_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, span_id TEXT NOT NULL, parent_span_id TEXT, service_id TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, status TEXT, provenance TEXT NOT NULL)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS trace_span_service_status ON trace_span(service_id, status, evidence_id)")
        self.connection.execute("CREATE INDEX IF NOT EXISTS trace_span_trace_parent ON trace_span(trace_id, parent_span_id, span_id)")

    @classmethod
    def from_context(cls, database: Path, context: OperationalEvidenceContext, *, resource_configuration: ResourceConfiguration = ResourceConfiguration(), exact_legacy_graph_id: bool = False, snapshot: EvidenceSnapshot | None = None) -> "IncidentEvidenceStore":
        graph_id = build_incident_evidence_graph(snapshot).graph_id if exact_legacy_graph_id and snapshot is not None else None
        store = cls(database, context, resource_configuration=resource_configuration, legacy_graph_id=graph_id)
        store.add_trace_spans(context.traces)
        return store

    def close(self) -> None:
        self.connection.close()

    def add_trace_spans(self, spans: Iterable[NormalizedTraceSpanEvidence]) -> int:
        """Insert every supplied trace span in deterministic-sized batches."""
        total = 0
        batch: list[tuple[str, ...]] = []
        for span in spans:
            batch.append((span.evidence_id, span.trace_id, span.span_id, span.parent_span_id, span.service_external_id, span.observed_at, span.end_time, span.status, json.dumps(dict(span.provenance), sort_keys=True, separators=(",", ":"))))
            if len(batch) == self.resource_configuration.trace_chunk_size:
                self.connection.executemany("INSERT OR IGNORE INTO trace_span VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
                total += len(batch); batch = []
        if batch:
            self.connection.executemany("INSERT OR IGNORE INTO trace_span VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
            total += len(batch)
        self.connection.commit()
        return total

    def trace_count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM trace_span").fetchone()[0])

    def trace_spans_for_entities(self, entity_ids: Iterable[str]) -> Iterator[Mapping[str, str | None]]:
        values = tuple(sorted(set(entity_ids)))
        if not values:
            return iter(())
        placeholders = ",".join("?" for _ in values)
        rows = self.connection.execute(f"SELECT evidence_id, trace_id, span_id, parent_span_id, service_id, start_time, end_time, status, provenance FROM trace_span WHERE service_id IN ({placeholders}) ORDER BY trace_id, start_time, span_id, evidence_id", values)
        return ({"evidence_id": row[0], "trace_id": row[1], "span_id": row[2], "parent_span_id": row[3], "service_id": row[4], "start_time": row[5], "end_time": row[6], "status": row[7], "provenance": row[8]} for row in rows)

    def trace_error_evidence_for_entities(self, entity_ids: Iterable[str]) -> Mapping[str, tuple[str, ...]]:
        values = tuple(sorted(set(entity_ids)))
        if not values:
            return {}
        placeholders = ",".join("?" for _ in values)
        rows = self.connection.execute(f"SELECT service_id, evidence_id FROM trace_span WHERE status = 'ERROR' AND service_id IN ({placeholders}) ORDER BY service_id, evidence_id", values)
        answer: dict[str, list[str]] = {}
        for service, evidence_id in rows:
            answer.setdefault(service, []).append(evidence_id)
        return {key: tuple(value) for key, value in answer.items()}

    def trace_counts_for_entities(self, entity_ids: Iterable[str]) -> Mapping[str, Mapping[str, int]]:
        """Return complete and error-only span counts without materializing spans."""
        values = tuple(sorted(set(entity_ids)))
        if not values:
            return {}
        placeholders = ",".join("?" for _ in values)
        rows = self.connection.execute(
            f"SELECT service_id, COUNT(*), SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) "
            f"FROM trace_span WHERE service_id IN ({placeholders}) GROUP BY service_id ORDER BY service_id",
            values,
        )
        return {row[0]: {"trace_span_count": int(row[1]), "error_trace_span_count": int(row[2])} for row in rows}

    def unresolved_parent_count_for_entity(self, entity_id: str) -> int:
        """Diagnose partial traces by checking indexed parent-span availability."""
        row = self.connection.execute(
            "SELECT COUNT(*) FROM trace_span child "
            "WHERE child.service_id = ? AND child.parent_span_id IS NOT NULL AND NOT EXISTS "
            "(SELECT 1 FROM trace_span parent WHERE parent.trace_id = child.trace_id "
            "AND parent.span_id = child.parent_span_id)",
            (entity_id,),
        ).fetchone()
        return int(row[0])

    def trace_volume_shift_aggregates(self, cutoff_time: str, *, minimum_count: int, factor: float) -> Mapping[str, Mapping[str, object]]:
        """Summarize pre/post trace participation without materializing span rows.

        This is an eligibility feature, not a causal or trace-reachability
        assertion.  The returned digest makes each aggregate reproducible.
        """
        if minimum_count < 1 or factor <= 1:
            raise ValueError("INVALID_TRACE_SHIFT_CONFIGURATION")
        rows = self.connection.execute(
            "SELECT service_id, SUM(CASE WHEN start_time < ? THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN start_time >= ? THEN 1 ELSE 0 END) "
            "FROM trace_span GROUP BY service_id ORDER BY service_id",
            (cutoff_time, cutoff_time),
        )
        answer: dict[str, Mapping[str, object]] = {}
        for service, before, after in rows:
            before_count, after_count = int(before), int(after)
            if before_count < minimum_count or after_count < minimum_count:
                continue
            ratio = after_count / before_count
            if 1 / factor < ratio < factor:
                continue
            digest = hashlib.sha256()
            source_rows = self.connection.execute(
                "SELECT evidence_id FROM trace_span WHERE service_id = ? ORDER BY evidence_id",
                (service,),
            )
            for (evidence_id,) in source_rows:
                digest.update(evidence_id.encode("utf-8"))
                digest.update(b"\x1f")
            answer[service] = {
                "pre_count": before_count,
                "post_count": after_count,
                "post_to_pre_ratio": ratio,
                "input_evidence_sha256": digest.hexdigest(),
            }
        return answer

    def trace_provenance(self, evidence_id: str) -> Mapping[str, object] | None:
        row = self.connection.execute("SELECT provenance FROM trace_span WHERE evidence_id = ?", (evidence_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def logical_view(self, snapshot_id: str | None = None) -> IncidentEvidenceGraphView:
        if self._legacy_graph_id:
            graph_id = self._legacy_graph_id
        else:
            digest = hashlib.sha256()
            digest.update(self.context.incident.incident_id.encode())
            for row in self.connection.execute("SELECT evidence_id, trace_id, span_id, parent_span_id, service_id, start_time, end_time, status, provenance FROM trace_span ORDER BY evidence_id"):
                digest.update(json.dumps(row, separators=(",", ":"), ensure_ascii=False).encode())
            graph_id = "iegview-" + digest.hexdigest()[:24]
        return IncidentEvidenceGraphView(self.context.incident.incident_id, graph_id, snapshot_id, self.trace_count(), self.resource_configuration)


def generate_frozen_candidates_from_store(
    store: IncidentEvidenceStore,
    view: IncidentEvidenceGraphView,
    *,
    include_metrics: bool = True,
    include_events: bool = True,
    include_traces: bool = True,
) -> tuple[CauseCandidate, ...]:
    """Apply frozen eligibility rules; flags only expose the documented R2 ablations."""
    entities = {item.external_id for item in store.context.entities}
    metrics_by_entity: dict[str, list[str]] = {}
    if include_metrics:
        for item in store.context.metrics:
            if item.service_external_id in entities:
                metrics_by_entity.setdefault(item.service_external_id, []).append(item.evidence_id)
    groups: dict[tuple[str, str, str], list[str]] = {}
    for item in store.context.changes:
        if item.target_external_id in entities:
            groups.setdefault(("CHANGE_EVENT_CANDIDATE", item.target_external_id, "CHANGE_AFFECTS_INCIDENT_ENTITY_V1"), []).append(item.evidence_id)
    if include_events:
        for item in store.context.events:
            if item.service_external_id in entities and item.severity == "ERROR":
                groups.setdefault(("OBSERVED_ERROR_CANDIDATE", item.service_external_id, "ERROR_EVENT_ON_INCIDENT_ENTITY_V1"), []).append(item.evidence_id)
    if include_traces:
        for service, evidence_ids in store.trace_error_evidence_for_entities(entities).items():
            groups.setdefault(("OBSERVED_ERROR_CANDIDATE", service, "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1"), []).extend(evidence_ids)
    candidates = []
    for (kind, service, rule), support in groups.items():
        support_ids = tuple(sorted(set(support)))
        candidates.append(CauseCandidate(
            _candidate_id(store.context.incident.incident_id, kind, f"entity:{service}", support_ids, view.graph_id),
            store.context.incident.incident_id, view.graph_id, f"entity:{service}", kind, (rule,), support_ids,
            tuple(sorted(metrics_by_entity.get(service, []))), (),
        ))
    return tuple(sorted(candidates, key=lambda item: (item.candidate_kind, item.subject_node_id, item.candidate_id)))
