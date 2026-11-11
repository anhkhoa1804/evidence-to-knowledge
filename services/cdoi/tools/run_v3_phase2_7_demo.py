"""Generate the versioned Phase 2.7 demo snapshot from the raw-demo fixture."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from cdoi.operational_context import TopologyScope, assemble_context, load_incident_windows, snapshot_for, write_snapshot
from cdoi.raw_preprocessing import process_dataset


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_7"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = process_dataset(FIXTURE / "manifest.yaml")
    incident = load_incident_windows(FIXTURE / "incidents" / "incidents.csv", "incidents/incidents.csv")[0]
    snapshot = snapshot_for(assemble_context(result, incident, TopologyScope.ONE_HOP))
    snapshots = ARCHIVE / "incident_snapshots"
    written = write_snapshot(snapshot, snapshots)
    context = snapshot.context
    report = {
        "schema_version": "v3_phase2_7_demo_result_v1",
        "snapshot": written,
        "incident_id": incident.incident_id,
        "window": {"start_time": incident.start_time, "end_time": incident.end_time},
        "topology_scope": context.topology_scope.value,
        "direct_entity_ids": list(context.direct_entity_ids),
        "expanded_entity_ids": list(context.expanded_entity_ids),
        "counts": {
            "entities": len(context.entities),
            "relations": len(context.relations),
            "events": len(context.events),
            "changes": len(context.changes),
            "semantic_terms": len(context.semantic_terms),
            "unresolved": len(context.unresolved),
        },
        "selection_rule_counts": dict(sorted(Counter(item.selection_rule for item in context.selections).items())),
        "provenance_trace_examples": {
            "entity": next(item for item in snapshot.artifact()["entities"] if item["external_id"] == "payment-service")["provenance"],
            "relation": next(item for item in snapshot.artifact()["relations"] if item["relation"] == "calls")["provenance"],
        },
    }
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    baseline = ROOT / "experiments" / "archive" / "v3_phase2_7_baseline" / "BASELINE.json"
    (ARCHIVE / "BASELINE.json").write_text(baseline.read_text(encoding="utf-8"), encoding="utf-8")
    (ARCHIVE / "DEMO_RESULT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gate = {
        "schema_version": "v3_phase2_7_research_gate_v1",
        "statuses": {
            "raw_preprocessing_integrity": "SUPPORTED",
            "normalized_evidence_integration": "SUPPORTED",
            "incident_window_representation": "SUPPORTED",
            "exact_identity_correlation": "SUPPORTED",
            "temporal_filtering": "SUPPORTED",
            "topology_context_assembly": "SUPPORTED",
            "snapshot_determinism": "SUPPORTED",
            "end_to_end_provenance": "SUPPORTED",
            "causal_separation_safety": "SUPPORTED",
            "metrics_intake_readiness": "METRICS_INTAKE_ARCHITECTURALLY_READY",
            "trace_intake_readiness": "PARTIALLY_SUPPORTED",
            "rca_reasoning_readiness": "NOT_IMPLEMENTED",
        },
        "limits": [
            "No metrics or trace adapter is implemented.",
            "No candidate-cause representation, scoring, ranking, causal inference, or root-cause output exists.",
            "Semantic terms are not selected without an exact linkage contract.",
            "Snapshots remain outside ontology proposal, review, approval, and canonical-KG paths.",
        ],
    }
    (ARCHIVE / "RESEARCH_GATE.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "v3_phase2_7_archive_manifest_v1",
        "artifacts": {
            "BASELINE.json": _digest(ARCHIVE / "BASELINE.json"),
            "DEMO_RESULT.json": _digest(ARCHIVE / "DEMO_RESULT.json"),
            "RESEARCH_GATE.json": _digest(ARCHIVE / "RESEARCH_GATE.json"),
            "incident_snapshots/inc-001.json": _digest(snapshots / "inc-001.json"),
            "baseline_reference": _digest(ROOT / "experiments" / "archive" / "v3_phase2_7_baseline" / "BASELINE.json"),
        },
    }
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
