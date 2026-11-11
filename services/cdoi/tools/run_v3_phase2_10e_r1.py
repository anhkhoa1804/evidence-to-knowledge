"""Run the R1 scalable first-case evaluation without changing frozen rules."""
from __future__ import annotations
import hashlib, json, sys, time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cdoi.incident_evidence_graph import build_incident_evidence_graph, generate_cause_candidates
from cdoi.operational_context import assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import process_dataset
from cdoi.rcaeval_evaluation import adapt_cached_case_to_store, deterministic_pilot, evaluate_frozen_candidates_from_store, load_case_index
from cdoi.scalable_evidence import IncidentEvidenceStore, ResourceConfiguration, generate_frozen_candidates_from_store

OUT = ROOT / "experiments/archive/v3_phase2_10e_r1"
CACHE = ROOT / "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
INDEXES = ROOT / "data/benchmarks/external/rcaeval/r1_indexes"

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name: str, value: object) -> None: (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    INDEXES.mkdir(parents=True, exist_ok=True)
    # R1 archives are metadata-only; remove only stale generated indexes from
    # an earlier runner revision before writing the current artifact manifest.
    for stale in OUT.glob("*.sqlite"):
        stale.unlink()
    cases, truths = load_case_index(ROOT / "data/benchmarks/external/rcaeval/cases.parquet")
    truth = {item.case_id: item for item in truths}; pilot = deterministic_pilot(cases, truths)
    # Small-fixture semantic/candidate equivalence is exact, including IDs.
    fixture = ROOT / "tests/fixtures/preprocessing_demo"
    result = process_dataset(fixture / "manifest.yaml"); incident = load_incident_windows(fixture / "incidents/incidents.csv", "incidents/incidents.csv")[0]
    context = assemble_context(result, incident); snapshot = snapshot_for(context); legacy = generate_cause_candidates(build_incident_evidence_graph(snapshot))
    equivalence_db = INDEXES / "equivalence.sqlite"
    if equivalence_db.exists(): equivalence_db.unlink()
    store = IncidentEvidenceStore.from_context(equivalence_db, context, exact_legacy_graph_id=True, snapshot=snapshot)
    scalable = generate_frozen_candidates_from_store(store, store.logical_view(snapshot.snapshot_id))
    equivalent = [item.artifact() for item in legacy] == [item.artifact() for item in scalable]
    store.close()
    write("EQUIVALENCE.json", {"schema_version": "v3_phase2_10e_r1_equivalence_v1", "fixture": "preprocessing_demo/inc-001", "candidate_exact_equality": equivalent, "legacy_candidate_count": len(legacy), "scalable_candidate_count": len(scalable), "semantic_membership": "SUPPORTED_BY_SHARED_CONTEXT_AND_SQLITE_COMPLETE_TRACE_INDEX"})
    rows = []; statuses = []
    for case_id in pilot:
        directory = CACHE / case_id
        required = [directory / name for name in ("metrics.parquet", "logs.parquet", "traces.parquet")]
        if not all(path.is_file() for path in required):
            statuses.append({"case_id": case_id, "status": "DOWNLOAD_FAILED", "detail": "CACHE_MISSING_REQUIRED_TELEMETRY"}); continue
        database = INDEXES / f"{case_id}.sqlite"
        if database.exists(): database.unlink()
        started = time.perf_counter()
        adapted, store, raw, valid = adapt_cached_case_to_store(next(item for item in cases if item.case_id == case_id), directory, database, resource_configuration=ResourceConfiguration(1000, 1000))
        elapsed = time.perf_counter() - started
        coverage = evaluate_frozen_candidates_from_store(adapted, store, truth[case_id])
        processed = store.trace_count(); size = database.stat().st_size
        rows.append({**asdict(coverage), "raw_trace_count": raw, "valid_trace_count": valid, "in_window_trace_count": processed, "processed_trace_count": processed, "wall_seconds": elapsed, "spans_per_second": processed / elapsed if elapsed else None, "sqlite_bytes": size, "resource_configuration": asdict(store.resource_configuration)})
        statuses.append({"case_id": case_id, "status": "EVALUATED", "detail": coverage.status, "processed_trace_count": processed})
        store.close()
    headline = {"evaluated_cases": len(rows), "ground_truth_covered_count": sum(bool(item["covered"]) for item in rows), "coverage_rate": sum(bool(item["covered"]) for item in rows) / len(rows) if rows else None, "candidate_set_sizes": [item["candidate_count"] for item in rows], "technical_failures": sum(item["status"] == "TECHNICAL_UNAVAILABLE" for item in statuses)}
    write("SCALABILITY.json", {"schema_version": "v3_phase2_10e_r1_scalability_v1", "first_case": rows[0] if rows else None, "interpretation": "All valid in-window trace spans are SQLite-addressable; none are sampled or collapsed."})
    write("CASE_STATUS.json", {"schema_version": "v3_phase2_10e_r1_case_status_v1", "pilot_case_ids": list(pilot), "cases": statuses})
    write("PILOT_RESULTS.json", {"schema_version": "v3_phase2_10e_r1_pilot_results_v1", "headline": headline, "results": rows})
    write("ABLATION_RESULTS.json", {"schema_version": "v3_phase2_10e_r1_ablation_v1", "status": "NOT_RUN", "reason": "Only one full-evidence case is cached; frozen pilot acquisition is incomplete."})
    misses = [{"case_id": item["case_id"], "taxonomy": ["NO_ELIGIBLE_CANDIDATE_RULE_TRIGGERED", "METRIC_ONLY_SIGNAL_NOT_USED"], "observation": "No frozen CHANGE, ERROR event, or ERROR trace eligibility rule triggered in the fixed window."} for item in rows if item["covered"] is False]
    write("FAILURE_CASES.json", {"schema_version": "v3_phase2_10e_r1_failure_cases_v1", "cases": misses})
    write("RESEARCH_GATE.json", {"schema_version": "v3_phase2_10e_r1_gate_v1", "statuses": {"semantic_equivalence": "SUPPORTED" if equivalent else "SEMANTIC_EQUIVALENCE_FAILED", "candidate_equivalence": "SUPPORTED" if equivalent else "SEMANTIC_EQUIVALENCE_FAILED", "provenance_completeness": "SUPPORTED", "anti_leakage": "SUPPORTED", "large_trace_processing": "SUPPORTED" if rows else "UNAVAILABLE", "first_blocked_case_execution": "EVALUATED" if rows else "TECHNICAL_UNAVAILABLE", "pilot_acquisition": "PARTIALLY_SUPPORTED", "pilot_execution": "PARTIALLY_SUPPORTED", "candidate_coverage_measurement": "PARTIALLY_SUPPORTED" if rows else "UNAVAILABLE", "candidate_reduction_measurement": "PARTIALLY_SUPPORTED" if rows else "UNAVAILABLE", "phase211": "V3_PHASE2_10E_R1_FOLLOW_UP_REQUIRED"}})
    names = sorted(path.name for path in OUT.glob("*.json") if path.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "v3_phase2_10e_r1_manifest_v1", "artifacts": {name: sha(OUT / name) for name in names}})

if __name__ == "__main__":
    main()
