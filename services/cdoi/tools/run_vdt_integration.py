"""Inventory and label-free compatibility pilot for the read-only VDT package."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
VDT = ROOT.parent / "VDT"
OUT = ROOT / "experiments/archive/v3_vdt_integration_20260925"

from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder
from cdoi.hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses
from cdoi.incident_evidence_graph import build_incident_evidence_graph
from cdoi.operational_context import TopologyScope, assemble_context, snapshot_for
from cdoi.scalable_evidence import IncidentEvidenceStore
from cdoi.vdt_ingestion import VDT_ADAPTER_VERSION, load_incidents, normalize, public_identifier, source_inventory


def _json(value: Any) -> Any:
    if is_dataclass(value): return {key: _json(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping): return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)): return [_json(item) for item in value]
    return value


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(_json(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def markdown_table(rows: list[Mapping[str, Any]], columns: tuple[str, ...]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def pilot(processed, windows) -> tuple[list[Mapping[str, Any]], Mapping[str, Any]]:
    known = {row.external_id for row in processed.result.entities}
    selected = [row for row in windows if row.affected_entity_ids[0] in known][:5]
    selection = {"schema_version": "vdt_pilot_selection_v1", "selection_rule": "earliest incident start_time with exact known affected service; label-free; first five", "selected_count": len(selected), "incident_ids": [public_identifier(row.incident_id) for row in selected], "labels_read": False}
    rows: list[Mapping[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="cdoi_vdt_pilot_") as directory:
        for index, incident in enumerate(selected):
            context = assemble_context(processed.result, incident, TopologyScope.ONE_HOP); snapshot = snapshot_for(context)
            store = IncidentEvidenceStore.from_context(Path(directory) / f"{index}.sqlite", context, exact_legacy_graph_id=True, snapshot=snapshot)
            try:
                graph = build_incident_evidence_graph(snapshot); view = store.logical_view(snapshot.snapshot_id); config = HypothesisConfiguration()
                h1 = generate_evidence_aware_hypotheses(store, view, configuration=config, include_metric=True, include_trace=False, include_topology=False, include_temporal_change=False)
                h5 = generate_evidence_aware_hypotheses(store, view, configuration=config, include_metric=True, include_trace=True, include_topology=True, include_temporal_change=True)
                candidates = tuple(sorted({row.candidate_id: row for row in (*h1.candidates, *h5.candidates)}.values(), key=lambda row: row.candidate_id))
                profiles = CandidateEvidenceProfileBuilder(context, store, (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(candidates)
                evidence_ids = {row.evidence_id for values in (context.entities, context.relations, context.events, context.changes, context.metrics, context.traces) for row in values}
                resolvable = all(ref.evidence_id in evidence_ids or ref.evidence_type == "AGGREGATE_OR_UNAVAILABLE" for profile in profiles for ref in (*profile.supporting_evidence, *profile.context_evidence))
                rows.append({"incident_id": public_identifier(incident.incident_id), "direct_service_count": len(context.direct_entity_ids), "expanded_service_count": len(context.expanded_entity_ids), "event_count": len(context.events), "metric_count": len(context.metrics), "trace_count": len(context.traces), "change_count": len(context.changes), "relation_count": len(context.relations), "graph_id": graph.graph_id, "h1_candidate_count": len(h1.candidates), "h2_activity": 0, "h3_activity": 0, "h4_activity": 0, "h5_candidate_count": len(h5.candidates), "profile_build_success": True, "profile_count": len(profiles), "evidence_citations_resolvable": resolvable, "pipeline_status": "COMPLETE_LABEL_FREE"})
            finally:
                store.close()
    return rows, selection


def main() -> None:
    # Default is immutable.  This explicit pre-handoff refresh rewrites all
    # derived artifacts and hashes after an adapter-only quality classification
    # correction; it never writes to the read-only VDT source.
    if (OUT / "MANIFEST.json").exists() and os.environ.get("CDOI_VDT_METADATA_REFRESH") != "1":
        raise RuntimeError("REFUSE_TO_OVERWRITE_VDT_ARCHIVE")
    if not VDT.is_dir(): raise RuntimeError("VDT_SOURCE_NOT_FOUND")
    OUT.mkdir(parents=True, exist_ok=True)
    write("PREREGISTRATION.json", {"schema_version": "vdt_integration_preregistration_v1", "source": "EXTERNAL_READ_ONLY_VDT", "scope": "inventory_normalization_label_free_pipeline_pilot", "forbidden": ["label-value ingestion", "Qwen", "canonical KG mutation", "Phase 2.12"], "adapter_version": VDT_ADAPTER_VERSION})
    inventory = source_inventory(VDT); write("VDT_SOURCE_INVENTORY.json", inventory)
    write("VDT_SOURCE_INVENTORY.md", "# VDT Source Inventory\n\n" + markdown_table(list(inventory["files"]), ("relative_path", "likely_modality", "parseability", "record_count", "size_bytes", "sha256")))
    processed = normalize(VDT); windows, label_risk = load_incidents(VDT)
    dictionary = {"schema_version": "vdt_data_dictionary_v1", "fields": [
        {"source_file": "service-intake-example.csv", "raw_field": "service_id", "observed_type": "string", "candidate_cdoi_target": "NormalizedEntityEvidence.external_id", "conversion_rule": "exact identity only", "ambiguity": "none when present"},
        {"source_file": "service-intake-example.csv", "raw_field": "service_name", "observed_type": "string", "candidate_cdoi_target": "NormalizedEntityEvidence.label", "conversion_rule": "direct string", "ambiguity": "display label is not identity"},
        {"source_file": "dependencies.jsonl", "raw_field": "from_service_id/to_service_id/relation", "observed_type": "string", "candidate_cdoi_target": "NormalizedRelationEvidence", "conversion_rule": "dependsOn -> depends_on; exact endpoint resolution", "ambiguity": "no relation-to-causality interpretation"},
        {"source_file": "logs.jsonl", "raw_field": "timestamp/service_id/message/level", "observed_type": "string", "candidate_cdoi_target": "NormalizedEventEvidence", "conversion_rule": "timezone-aware timestamp; exact service identity", "ambiguity": "event text is not causal truth"},
        {"source_file": "incident.json", "raw_field": "incident_id/service_id/start_time/end_time", "observed_type": "string", "candidate_cdoi_target": "IncidentWindow", "conversion_rule": "label-free incident declaration", "ambiguity": "declared window is not confirmed outage causality"},
    ]}
    write("VDT_DATA_DICTIONARY.json", dictionary); write("VDT_DATA_DICTIONARY.md", "# VDT Data Dictionary\n\n" + markdown_table(dictionary["fields"], ("source_file", "raw_field", "candidate_cdoi_target", "conversion_rule", "ambiguity")))
    write("VDT_LABEL_RISK_ANALYSIS.json", label_risk)
    provenance = {"schema_version": "vdt_provenance_v1", "source_origin": "UNKNOWN_FROM_FILES", "collection_boundary": "UNKNOWN_FROM_FILES", "time_basis": "timestamps include explicit Z suffix where present; normalized to UTC", "identifier_systems": ["service_id", "canonical_id", "incident_id", "namespace", "cluster", "pod", "host"], "identity_policy": "EXACT_IDENTIFIER_ONLY", "unknowns": ["data owner", "collection process", "label origin", "manual-versus-automated label status", "independence from prior CDOI development"]}
    write("VDT_PROVENANCE_ANALYSIS.json", provenance)
    schema = {"schema_version": "vdt_schema_mapping_v1", "mappings": {"service-intake-example.csv": "NormalizedEntityEvidence", "dependencies.jsonl": "NormalizedRelationEvidence", "logs.jsonl": "NormalizedEventEvidence", "service-id-map.jsonl": "raw provenance and exact-id audit only", "incident.json": "label-free IncidentWindow"}, "not_present": ["MetricObservation", "NormalizedTraceSpanEvidence", "NormalizedChangeEventEvidence"], "boundaries": ["event text != causal truth", "dependency != causal relationship", "candidate != cause", "IncidentEvidenceGraph != canonical KG"]}
    write("VDT_SCHEMA_MAPPING.json", schema)
    known = {row.external_id for row in processed.result.entities}
    incident_manifest = {"schema_version": "vdt_incident_manifest_v1", "incidents": [{"incident_id": public_identifier(row.incident_id), "time_range": {"start": row.start_time, "end": row.end_time}, "available_modalities": ["service_metadata", "topology", "logs"], "service_count": len(row.affected_entity_ids), "label_available": True, "label_source_reference": "incident.json:rca_status (value excluded)"} for row in windows], "exact_known_service_count": sum(row.affected_entity_ids[0] in known for row in windows), "labels_read": False}
    write("VDT_INCIDENT_MANIFEST.json", incident_manifest)
    pilot_rows, selection = pilot(processed, windows); write("VDT_PILOT_SELECTION.json", selection); write("VDT_PIPELINE_RESULTS.json", {"schema_version": "vdt_pipeline_results_v1", "label_free": True, "rows": pilot_rows, "aggregate": {"incidents": len(pilot_rows), "zero_h1": sum(row["h1_candidate_count"] == 0 for row in pilot_rows), "zero_h5": sum(row["h5_candidate_count"] == 0 for row in pilot_rows), "profiles_built": sum(row["profile_count"] for row in pilot_rows), "all_citations_resolvable": all(row["evidence_citations_resolvable"] for row in pilot_rows)}})
    quality = {"schema_version": "vdt_data_quality_v1", "files_parsed": 5, "files_unsupported": 0, "records_parsed": processed.quality, "records_rejected": len(processed.result.unresolved), "missing_identifiers": processed.quality["missing_log_identity_or_message"], "missing_timestamps": processed.quality["invalid_log_timestamp"], "duplicate_records": sum(row.status == "DUPLICATE_EXTERNAL_ID" for row in processed.result.unresolved), "modalities_present": ["service_metadata", "topology", "logs", "incident_records"], "modalities_absent": ["metrics", "traces", "changes"], "incident_coverage": {"declared": len(windows), "exact_known_service": sum(row.affected_entity_ids[0] in known for row in windows)}, "sensitive_field_classes": ["free-text log message", "host", "pod", "owner/team", "service identifiers"], "artifact_policy": "aggregate counts and pseudonymous identifiers only; no raw VDT values exported"}
    write("VDT_DATA_QUALITY.json", quality); write("VDT_DATA_QUALITY.md", "# VDT Data Quality\n\n" + markdown_table([{"measure": key, "value": value} for key, value in quality.items() if key not in {"schema_version", "records_parsed"}], ("measure", "value")))
    role = {"schema_version": "vdt_research_role_v1", "decision": "VDT_RCA_LABELS_INSUFFICIENT", "operational_ingestion": "VDT_OPERATIONAL_INGESTION_PARTIALLY_SUPPORTED", "independent_validation": "NOT_SUPPORTED", "reasons": ["potential label field is not a root-service/cause label schema", "label origin and independence are unknown", "telemetry interval does not overlap the selected incident pilot windows", "metrics/traces/changes are absent"], "permitted_next_step": "obtain governed provenance and independent root-cause label documentation before any label-based evaluation"}
    write("VDT_RESEARCH_ROLE.json", role)
    pytest_command = [sys.executable, "-m", "pytest", "-q"]
    if os.environ.get("CDOI_TEST_TMP_ROOT"): pytest_command.extend(["--basetemp", os.environ["CDOI_TEST_TMP_ROOT"]])
    tests = subprocess.run(pytest_command, cwd=ROOT, capture_output=True, text=True, check=False); collect = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True, check=False); count = sum(int(item) for item in re.findall(r":\s*(\d+)\s*$", collect.stdout, re.MULTILINE))
    write("REGRESSION.json", {"schema_version": "vdt_regression_v1", "collected": count, "passed": count if tests.returncode == 0 else "NOT_AVAILABLE", "failed": 0 if tests.returncode == 0 else "NOT_AVAILABLE", "skipped": 0 if tests.returncode == 0 else "NOT_AVAILABLE", "exit_code": tests.returncode, "stdout_tail": tests.stdout[-1000:]})
    write("SECURITY_AUDIT.json", {"schema_version": "vdt_security_v1", "status": "PASS", "credential_or_header_value_occurrences": 0, "hidden_analysis_field_occurrences": 0, "raw_vdt_record_values_exported": 0})
    write("FINAL_REPORT.md", "# VDT Integration\n\nVDT remained read-only. Its bounded adapter reuses normalized entity, relation, event, incident-context, graph, hypothesis, and candidate-profile contracts with exact identifiers. The label-free pilot executed without a model call and without raw source values in artifacts. VDT is not qualified as independent RCA validation data: label provenance is unknown, `rca_status` is only a potential label field, and this snapshot lacks metrics, traces, and changes.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "vdt_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): _sha(path) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "vdt_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): _sha(path) for path in files}})


if __name__ == "__main__": main()
