"""Generate the deterministic V3 Phase 2.9 trace-evidence archive."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from cdoi.operational_context import TopologyScope, assemble_context, load_incident_windows, snapshot_for, write_snapshot
from cdoi.raw_preprocessing import process_dataset, write_artifacts


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_9"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = process_dataset(FIXTURE / "manifest.yaml")
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    preprocessing = write_artifacts(result, ARCHIVE / "preprocessing_output")
    incident = load_incident_windows(FIXTURE / "incidents" / "incidents.csv", "incidents/incidents.csv")[0]
    snapshot = snapshot_for(assemble_context(result, incident, TopologyScope.ONE_HOP))
    written = write_snapshot(snapshot, ARCHIVE / "incident_snapshots")
    context = snapshot.context
    trace_evidence = {
        "schema_version": "trace_evidence_v1",
        "preprocessing_contract": "cdoi_preprocessing_v1",
        "contract": {
            "required_fields": ["trace_id", "span_id", "service_id", "start_time"],
            "optional_fields": ["parent_span_id", "operation", "duration_ms", "end_time", "status", "kind", "sampled", "error_code", "attributes", "peer_service_id"],
            "identity": "trace_id + span_id within a source trace",
            "temporal_membership": "inclusive interval overlap",
            "attribute_policy": "normalized evidence records attributes_present only; raw provenance retains source location",
        },
        "diagnostics": preprocessing["trace_diagnostics"],
        "schema_candidate_effect": "ZERO_TRACE_DERIVED_CANDIDATES",
    }
    graph = {
        "schema_version": "trace_execution_graph_v1",
        "graphs": [
            {
                "trace_id": item.trace_id,
                "node_count": len(item.nodes),
                "edge_count": len(item.edges),
                "root_count": len(item.root_evidence_ids),
                "missing_parent_count": len(item.missing_parent_evidence_ids),
                "branch_count": item.branch_count,
                "status": item.status,
                "edges": [{"parent_evidence_id": edge.parent_evidence_id, "child_evidence_id": edge.child_evidence_id} for edge in item.edges],
            }
            for item in context.trace_execution_graphs
        ],
    }
    demo = {
        "schema_version": "v3_phase2_9_demo_result_v1",
        "snapshot": written,
        "incident_id": incident.incident_id,
        "window": {"start_time": incident.start_time, "end_time": incident.end_time},
        "topology_scope": context.topology_scope.value,
        "counts": {"entities": len(context.entities), "relations": len(context.relations), "events": len(context.events), "changes": len(context.changes), "metrics": len(context.metrics), "traces": len(context.traces), "trace_graphs": len(context.trace_execution_graphs), "semantic_terms": len(context.semantic_terms), "unresolved": len(context.unresolved)},
        "trace_membership": [{"trace_id": item.trace_id, "span_id": item.span_id, "service_id": item.service_external_id, "operation": item.operation, "status": item.status, "parent_span_id": item.parent_span_id} for item in context.traces],
        "selection_rule_counts": dict(sorted(Counter(item.selection_rule for item in context.selections).items())),
        "trace_provenance_trace": next(item for item in snapshot.artifact()["traces"] if item["span_id"] == "span-payment")["provenance"],
        "interpretation_boundary": "static topology != execution path; execution traversal != causal path; ERROR span != root cause; duration != anomaly",
    }
    gate = {
        "schema_version": "v3_phase2_9_research_gate_v1",
        "statuses": {
            "trace_preprocessing": "SUPPORTED", "trace_identity": "SUPPORTED", "span_identity": "SUPPORTED",
            "parent_child_reconstruction": "SUPPORTED", "service_identity": "SUPPORTED",
            "temporal_overlap_filtering": "SUPPORTED", "partial_trace_handling": "SUPPORTED",
            "missing_parent_handling": "SUPPORTED", "fan_out_preservation": "SUPPORTED",
            "execution_graph_determinism": "SUPPORTED", "trace_provenance": "SUPPORTED",
            "snapshot_integration": "SUPPORTED", "static_topology_separation": "SUPPORTED",
            "causal_separation_safety": "SUPPORTED", "schema_leakage_safety": "SUPPORTED",
            "incident_evidence_graph_readiness": "INCIDENT_EVIDENCE_GRAPH_ARCHITECTURALLY_READY",
            "rca_readiness": "NOT_IMPLEMENTED",
        },
        "limits": [
            "Only constrained JSONL trace files are implemented; no collector, tracing API, or streaming intake exists.",
            "Trace execution edges preserve explicit parent links only and never alter static topology.",
            "No anomaly, causal, candidate-cause, ranking, root-cause, schema, proposal, or KG result is generated.",
        ],
    }
    baseline = ROOT / "experiments" / "archive" / "v3_phase2_9_baseline" / "BASELINE.json"
    (ARCHIVE / "BASELINE.json").write_text(baseline.read_text(encoding="utf-8"), encoding="utf-8")
    (ARCHIVE / "TRACE_EVIDENCE.json").write_text(json.dumps(trace_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ARCHIVE / "EXECUTION_GRAPH.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ARCHIVE / "DEMO_RESULT.json").write_text(json.dumps(demo, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ARCHIVE / "RESEARCH_GATE.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {"schema_version": "v3_phase2_9_archive_manifest_v1", "artifacts": {name: _digest(ARCHIVE / name) for name in ("BASELINE.json", "TRACE_EVIDENCE.json", "EXECUTION_GRAPH.json", "DEMO_RESULT.json", "RESEARCH_GATE.json")} | {"incident_snapshots/inc-001.json": _digest(ARCHIVE / "incident_snapshots" / "inc-001.json"), "preprocessing_output/traces.jsonl": _digest(ARCHIVE / "preprocessing_output" / "traces.jsonl")}}
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
