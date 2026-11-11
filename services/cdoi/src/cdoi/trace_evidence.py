"""Read-only reconstruction of declared distributed-trace execution structure.

Parent-to-child span edges are observed hierarchy evidence, never causal edges.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .raw_preprocessing import NormalizedTraceSpanEvidence, trace_by_id


@dataclass(frozen=True)
class TraceExecutionEdge:
    parent_evidence_id: str
    child_evidence_id: str


@dataclass(frozen=True)
class TraceExecutionGraph:
    trace_id: str
    nodes: tuple[NormalizedTraceSpanEvidence, ...]
    edges: tuple[TraceExecutionEdge, ...]
    root_evidence_ids: tuple[str, ...]
    missing_parent_evidence_ids: tuple[str, ...]
    status: str
    branch_count: int


def execution_graph_for_trace(traces: Sequence[NormalizedTraceSpanEvidence], trace_id: str) -> TraceExecutionGraph:
    """Build an execution-only graph from explicit parent references, fail-closed on cycles."""
    nodes = trace_by_id(traces, trace_id)
    by_span_id = {item.span_id: item for item in nodes}
    edges: list[TraceExecutionEdge] = []
    missing: list[str] = []
    children: dict[str, list[str]] = defaultdict(list)
    statuses: set[str] = set()
    for child in nodes:
        if child.parent_resolution_status == "ROOT":
            continue
        if child.parent_resolution_status == "PARENT_CYCLE":
            statuses.add("PARTIAL_PARENT_CYCLE")
            missing.append(child.evidence_id)
            continue
        parent = by_span_id.get(child.parent_span_id or "")
        if child.parent_resolution_status != "RESOLVED_PARENT" or not parent:
            statuses.add("PARTIAL_MISSING_PARENT" if child.parent_resolution_status == "UNRESOLVED_PARENT" else "PARTIAL_SCOPE_EXCLUDED_PARENT")
            missing.append(child.evidence_id)
            continue
        edges.append(TraceExecutionEdge(parent.evidence_id, child.evidence_id))
        children[parent.evidence_id].append(child.evidence_id)
    if any(item.correlation_status != "RESOLVED_EXACT_ID" for item in nodes):
        statuses.add("PARTIAL_UNRESOLVED_SERVICE")
    status = sorted(statuses)[0] if statuses else "COMPLETE_UNDER_OBSERVED_PARENT_LINKS"
    return TraceExecutionGraph(
        trace_id=trace_id,
        nodes=nodes,
        edges=tuple(sorted(edges, key=lambda item: (item.parent_evidence_id, item.child_evidence_id))),
        root_evidence_ids=tuple(sorted(item.evidence_id for item in nodes if item.parent_resolution_status == "ROOT")),
        missing_parent_evidence_ids=tuple(sorted(set(missing))),
        status=status,
        branch_count=sum(len(items) > 1 for items in children.values()),
    )


def execution_graphs(traces: Sequence[NormalizedTraceSpanEvidence]) -> tuple[TraceExecutionGraph, ...]:
    """Return all trace graphs in deterministic trace-ID order."""
    return tuple(execution_graph_for_trace(traces, trace_id) for trace_id in sorted({item.trace_id for item in traces}))
