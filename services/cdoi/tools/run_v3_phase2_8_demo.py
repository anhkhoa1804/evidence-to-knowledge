"""Generate the deterministic V3 Phase 2.8 metric-evidence archive."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from cdoi.operational_context import TopologyScope, assemble_context, load_incident_windows, snapshot_for, write_snapshot
from cdoi.raw_preprocessing import process_dataset, write_artifacts


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_8"


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
    metric_evidence = {
        "schema_version": "metric_evidence_v1",
        "preprocessing_contract": "cdoi_preprocessing_v1",
        "contract": {
            "required_fields": ["metric_id", "timestamp", "service_id", "metric_name", "value", "unit", "metric_kind"],
            "optional_fields": ["aggregation", "sampling_interval", "window_start", "window_end", "source_metric_name", "attributes", "environment"],
            "numeric_representation": "finite JSON number",
            "unit_policy": "preserve supported declared units without conversion",
            "series_key": "entity_id + metric_name + unit + metric_kind + aggregation",
        },
        "diagnostics": preprocessing["metric_diagnostics"],
        "schema_candidate_effect": "ZERO_METRIC_DERIVED_CANDIDATES",
    }
    demo = {
        "schema_version": "v3_phase2_8_demo_result_v1",
        "snapshot": written,
        "incident_id": incident.incident_id,
        "window": {"start_time": incident.start_time, "end_time": incident.end_time},
        "topology_scope": context.topology_scope.value,
        "counts": {
            "entities": len(context.entities),
            "relations": len(context.relations),
            "events": len(context.events),
            "changes": len(context.changes),
            "metrics": len(context.metrics),
            "semantic_terms": len(context.semantic_terms),
            "unresolved": len(context.unresolved),
        },
        "metric_membership": [{"metric_id": item.metric_id, "service_id": item.service_external_id, "metric_name": item.metric_name, "value": item.value, "unit": item.unit, "metric_kind": item.metric_kind, "aggregation": item.aggregation} for item in context.metrics],
        "selection_rule_counts": dict(sorted(Counter(item.selection_rule for item in context.selections).items())),
        "metric_provenance_trace": next(item for item in snapshot.artifact()["metrics"] if item["metric_id"] == "m-003")["provenance"],
        "interpretation_boundary": "temporal ordering != causality; metric value != anomaly",
    }
    gate = {
        "schema_version": "v3_phase2_8_research_gate_v1",
        "statuses": {
            "metric_preprocessing": "SUPPORTED",
            "metric_identity": "SUPPORTED",
            "unit_semantics": "PARTIALLY_SUPPORTED",
            "metric_kind_semantics": "SUPPORTED",
            "sampling_metadata": "SUPPORTED",
            "aggregation_semantics": "SUPPORTED",
            "temporal_filtering": "SUPPORTED",
            "exact_entity_correlation": "SUPPORTED",
            "snapshot_integration": "SUPPORTED",
            "snapshot_determinism": "SUPPORTED",
            "metric_provenance": "SUPPORTED",
            "counter_safety": "SUPPORTED",
            "anomaly_separation_safety": "SUPPORTED",
            "causal_separation_safety": "SUPPORTED",
            "trace_readiness": "PARTIALLY_SUPPORTED",
            "rca_readiness": "NOT_IMPLEMENTED",
        },
        "limits": [
            "Only a constrained CSV source is implemented; no scraping, API, database, or streaming intake exists.",
            "Supported units are preserved without cross-unit conversion; unsupported units are explicit preprocessing issues.",
            "No baseline, threshold, anomaly, trend, delta, causal, or root-cause interpretation is generated.",
            "Metrics create no SchemaCandidates, DataPropertyCandidates, proposals, reviews, approvals, or KG assertions.",
        ],
    }
    baseline = ROOT / "experiments" / "archive" / "v3_phase2_8_baseline" / "BASELINE.json"
    (ARCHIVE / "BASELINE.json").write_text(baseline.read_text(encoding="utf-8"), encoding="utf-8")
    (ARCHIVE / "METRIC_EVIDENCE.json").write_text(json.dumps(metric_evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ARCHIVE / "DEMO_RESULT.json").write_text(json.dumps(demo, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ARCHIVE / "RESEARCH_GATE.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v3_phase2_8_archive_manifest_v1",
        "artifacts": {
            "BASELINE.json": _digest(ARCHIVE / "BASELINE.json"),
            "METRIC_EVIDENCE.json": _digest(ARCHIVE / "METRIC_EVIDENCE.json"),
            "DEMO_RESULT.json": _digest(ARCHIVE / "DEMO_RESULT.json"),
            "RESEARCH_GATE.json": _digest(ARCHIVE / "RESEARCH_GATE.json"),
            "incident_snapshots/inc-001.json": _digest(ARCHIVE / "incident_snapshots" / "inc-001.json"),
            "preprocessing_output/metrics.jsonl": _digest(ARCHIVE / "preprocessing_output" / "metrics.jsonl"),
        },
    }
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
