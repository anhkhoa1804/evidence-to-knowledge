"""Deterministic, unranked Phase 2.11 evidence-aware hypotheses.

Rules in this module make services eligible for investigation.  They do not
assert causality, select a root cause, or assign confidence.
"""
from __future__ import annotations

import hashlib
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping

from .incident_evidence_graph import CauseCandidate
from .scalable_evidence import IncidentEvidenceGraphView, IncidentEvidenceStore, generate_frozen_candidates_from_store

HYPOTHESIS_GENERATION_VERSION = "evidence_aware_hypothesis_generation_v1"
METRIC_LEVEL_SHIFT_RULE = "METRIC_LEVEL_SHIFT_HYPOTHESIS_V1"
TRACE_VOLUME_SHIFT_RULE = "TRACE_PARTICIPATION_SHIFT_HYPOTHESIS_V1"
TOPOLOGY_ADJACENCY_RULE = "BOUNDED_TOPOLOGY_ADJACENCY_HYPOTHESIS_V1"
TEMPORAL_CHANGE_RULE = "TEMPORAL_CHANGE_CONTEXT_HYPOTHESIS_V1"


@dataclass(frozen=True)
class HypothesisConfiguration:
    """Versioned fixed constants chosen without RCAEval ground-truth labels."""

    baseline_seconds: int = 300
    metric_minimum_observations: int = 60
    metric_median_relative_shift: float = 0.50
    metric_persistent_fraction: float = 0.60
    trace_minimum_spans_per_partition: int = 100
    trace_volume_shift_factor: float = 2.0
    schema_version: str = HYPOTHESIS_GENERATION_VERSION


@dataclass(frozen=True)
class AggregateEvidence:
    """Compact provenance for a bounded aggregate over raw evidence IDs."""

    evidence_id: str
    evidence_type: str
    service_external_id: str
    rule_id: str
    time_start: str
    time_end: str
    input_count: int
    input_evidence_sha256: str
    attributes: Mapping[str, Any]
    manifest_hash: str

    def artifact(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HypothesisGenerationResult:
    candidates: tuple[CauseCandidate, ...]
    aggregate_evidence: tuple[AggregateEvidence, ...]
    enabled_families: tuple[str, ...]
    schema_version: str = HYPOTHESIS_GENERATION_VERSION

    def artifact(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "enabled_families": list(self.enabled_families),
            "aggregate_evidence": [item.artifact() for item in self.aggregate_evidence],
            "candidates": [item.artifact() for item in self.candidates],
            "serialization_order": "subject ID then deterministic candidate ID; this is not RCA ranking",
        }


def _digest(values: Iterable[str]) -> str:
    hasher = hashlib.sha256()
    for value in sorted(values):
        hasher.update(value.encode("utf-8")); hasher.update(b"\x1f")
    return hasher.hexdigest()


def _id(kind: str, *parts: str) -> str:
    return f"phase211-{kind}-" + _digest(parts)[:24]


def _cutoff(store: IncidentEvidenceStore, configuration: HypothesisConfiguration) -> str:
    start = datetime.fromisoformat(store.context.incident.start_time.replace("Z", "+00:00"))
    return (start + timedelta(seconds=configuration.baseline_seconds)).isoformat().replace("+00:00", "Z")


def _metric_aggregates(store: IncidentEvidenceStore, cutoff: str, configuration: HypothesisConfiguration) -> tuple[AggregateEvidence, ...]:
    grouped: dict[tuple[str, str], list[Any]] = {}
    for metric in store.context.metrics:
        grouped.setdefault((metric.service_external_id, metric.series_key), []).append(metric)
    rows: list[AggregateEvidence] = []
    for (service, series), observations in sorted(grouped.items()):
        # A level rule never converts a declared counter to a rate or gauge.
        if {item.metric_kind for item in observations} == {"COUNTER"}:
            continue
        if len({item.unit for item in observations}) != 1 or not all(math.isfinite(item.value) for item in observations):
            continue
        before = [item for item in observations if item.observed_at < cutoff]
        after = [item for item in observations if item.observed_at >= cutoff]
        if len(before) < configuration.metric_minimum_observations or len(after) < configuration.metric_minimum_observations:
            continue
        baseline, recent = statistics.median(item.value for item in before), statistics.median(item.value for item in after)
        scale = max(abs(baseline), 1e-9)
        relative_shift = abs(recent - baseline) / scale
        persistent_fraction = sum(abs(item.value - baseline) / scale >= configuration.metric_median_relative_shift for item in after) / len(after)
        if relative_shift < configuration.metric_median_relative_shift or persistent_fraction < configuration.metric_persistent_fraction:
            continue
        inputs = tuple(item.evidence_id for item in observations)
        rows.append(AggregateEvidence(
            _id("metric", store.context.incident.incident_id, service, series, _digest(inputs)),
            "METRIC_LEVEL_SHIFT_AGGREGATE", service, METRIC_LEVEL_SHIFT_RULE,
            before[0].observed_at, after[-1].observed_at, len(inputs), _digest(inputs),
            {"series_key": series, "unit": before[0].unit, "metric_kind": before[0].metric_kind,
             "pre_median": baseline, "post_median": recent, "relative_median_shift": relative_shift,
             "persistent_post_fraction": persistent_fraction, "pre_observation_count": len(before), "post_observation_count": len(after)},
            store.context.manifest_hash,
        ))
    return tuple(rows)


def _trace_aggregates(store: IncidentEvidenceStore, cutoff: str, configuration: HypothesisConfiguration) -> tuple[AggregateEvidence, ...]:
    rows = []
    for service, values in sorted(store.trace_volume_shift_aggregates(cutoff, minimum_count=configuration.trace_minimum_spans_per_partition, factor=configuration.trace_volume_shift_factor).items()):
        rows.append(AggregateEvidence(
            _id("trace", store.context.incident.incident_id, service, str(values["input_evidence_sha256"])),
            "TRACE_VOLUME_SHIFT_AGGREGATE", service, TRACE_VOLUME_SHIFT_RULE,
            store.context.incident.start_time, store.context.incident.end_time,
            int(values["pre_count"]) + int(values["post_count"]), str(values["input_evidence_sha256"]), dict(values), store.context.manifest_hash,
        ))
    return tuple(rows)


def _merge(view: IncidentEvidenceGraphView, store: IncidentEvidenceStore, contributions: Iterable[tuple[str, str, Iterable[str], Iterable[str]]]) -> tuple[CauseCandidate, ...]:
    grouped: dict[str, dict[str, set[str]]] = {}
    for service, rule, support, context in contributions:
        if service not in {item.external_id for item in store.context.entities}:
            continue
        row = grouped.setdefault(service, {"rules": set(), "support": set(), "context": set()})
        row["rules"].add(rule); row["support"].update(support); row["context"].update(context)
    candidates = []
    for service, row in sorted(grouped.items()):
        support, rules, context = tuple(sorted(row["support"])), tuple(sorted(row["rules"])), tuple(sorted(row["context"]))
        candidate_id = _id("candidate", store.context.incident.incident_id, view.graph_id, service, *rules, *support)
        candidates.append(CauseCandidate(candidate_id, store.context.incident.incident_id, view.graph_id, f"entity:{service}", "EVIDENCE_AWARE_HYPOTHESIS", rules, support, context, ()))
    return tuple(sorted(candidates, key=lambda item: (item.subject_node_id, item.candidate_id)))


def generate_evidence_aware_hypotheses(
    store: IncidentEvidenceStore,
    view: IncidentEvidenceGraphView,
    *,
    configuration: HypothesisConfiguration = HypothesisConfiguration(),
    include_metric: bool = True,
    include_trace: bool = True,
    include_topology: bool = True,
    include_temporal_change: bool = True,
) -> HypothesisGenerationResult:
    """Generate deterministic unranked hypotheses without accepting evaluation labels."""
    cutoff = _cutoff(store, configuration)
    frozen = generate_frozen_candidates_from_store(store, view)
    contributions: list[tuple[str, str, Iterable[str], Iterable[str]]] = [
        (item.subject_node_id.removeprefix("entity:"), rule, item.supporting_evidence_ids, item.context_evidence_ids)
        for item in frozen for rule in item.generation_rules
    ]
    aggregates: list[AggregateEvidence] = []
    metric = _metric_aggregates(store, cutoff, configuration) if include_metric else ()
    trace = _trace_aggregates(store, cutoff, configuration) if include_trace else ()
    aggregates.extend(metric); aggregates.extend(trace)
    for row in metric:
        contributions.append((row.service_external_id, row.rule_id, (row.evidence_id,), ()))
    for row in trace:
        contributions.append((row.service_external_id, row.rule_id, (row.evidence_id,), ()))
    seeds = {row.service_external_id for row in (*metric, *trace)} | {item.subject_node_id.removeprefix("entity:") for item in frozen}
    if include_topology:
        for relation in store.context.relations:
            if relation.source_external_id in seeds or relation.target_external_id in seeds:
                neighbor = relation.target_external_id if relation.source_external_id in seeds else relation.source_external_id
                contributions.append((neighbor, TOPOLOGY_ADJACENCY_RULE, (relation.evidence_id,), ()))
    if include_temporal_change:
        for change in store.context.changes:
            if change.observed_at <= cutoff and change.target_external_id in seeds:
                contributions.append((change.target_external_id, TEMPORAL_CHANGE_RULE, (change.evidence_id,), ()))
    enabled = ["H0_FROZEN"]
    if include_metric: enabled.append("H1_METRIC")
    if include_trace: enabled.append("H2_TRACE")
    if include_topology: enabled.append("H3_TOPOLOGY")
    if include_temporal_change: enabled.append("H4_TEMPORAL_CHANGE")
    return HypothesisGenerationResult(_merge(view, store, contributions), tuple(sorted(aggregates, key=lambda item: item.evidence_id)), tuple(enabled))
