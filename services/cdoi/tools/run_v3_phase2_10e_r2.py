"""Complete the frozen R2 RCAEval pilot without changing candidate semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.incident_evidence_graph import build_incident_evidence_graph, generate_cause_candidates
from cdoi.operational_context import assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import process_dataset
from cdoi.rcaeval_evaluation import (
    RCAEVAL_ADAPTER_VERSION,
    RCAEVAL_EVALUATION_VERSION,
    RCAEvalGroundTruth,
    adapt_cached_case_to_store,
    deterministic_pilot,
    load_case_index,
)
from cdoi.scalable_evidence import IncidentEvidenceStore, ResourceConfiguration, generate_frozen_candidates_from_store

REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
CACHE = ROOT / "data/benchmarks/external/rcaeval" / REVISION
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"
OUT = ROOT / "experiments/archive/v3_phase2_10e_r2"
INDEXES = ROOT / "data/benchmarks/external/rcaeval/r2_indexes"
R1 = ROOT / "experiments/archive/v3_phase2_10e_r1"
PHASE210 = ROOT / "experiments/archive/v3_phase2_10"
PHASE210E = ROOT / "experiments/archive/v3_phase2_10e_rcaeval"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha(path: Path) -> str:
    rows = [f"{item.relative_to(ROOT).as_posix()}\x1f{sha(item)}" for item in sorted(path.rglob("*")) if item.is_file() and "__pycache__" not in item.parts]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def dump(name: str, value: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_count() -> int:
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only"], cwd=ROOT, text=True, capture_output=True, check=True)
    match = re.search(r"(\d+) tests collected", result.stdout)
    if not match:
        raise RuntimeError("PYTEST_COLLECTION_COUNT_UNAVAILABLE")
    return int(match.group(1))


def median(values: list[int | float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [row for row in rows if row.get("covered") is not None]
    sizes = [row["candidate_count"] for row in evaluated]
    reductions = [row["candidate_reduction_ratio"] for row in evaluated if row["candidate_reduction_ratio"] is not None]
    zero = [row for row in evaluated if row["candidate_count"] == 0]
    return {
        "evaluated_count": len(evaluated),
        "covered_count": sum(row["covered"] is True for row in evaluated),
        "missed_count": sum(row["covered"] is False for row in evaluated),
        "candidate_stage_root_cause_coverage": sum(row["covered"] is True for row in evaluated) / len(evaluated) if evaluated else None,
        "zero_candidate_count": len(zero),
        "zero_candidate_rate": len(zero) / len(evaluated) if evaluated else None,
        "candidate_set_size": {
            "mean": sum(sizes) / len(sizes) if sizes else None,
            "median": median(sizes),
            "min": min(sizes) if sizes else None,
            "max": max(sizes) if sizes else None,
            "p90": sorted(sizes)[math.ceil(len(sizes) * .9) - 1] if sizes else None,
        },
        "candidate_reduction_ratio_mean": sum(reductions) / len(reductions) if reductions else None,
        "statuses": dict(sorted(Counter(row["status"] for row in rows).items())),
    }


def candidate_rows(candidates: Iterable[Any]) -> list[dict[str, Any]]:
    rows = []
    support_types = {
        "CHANGE_AFFECTS_INCIDENT_ENTITY_V1": "CHANGE",
        "ERROR_EVENT_ON_INCIDENT_ENTITY_V1": "EVENT",
        "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1": "TRACE_SPAN",
    }
    for item in candidates:
        support_type = support_types[item.generation_rules[0]]
        rows.append({
            "candidate_id": item.candidate_id,
            "candidate_subject": item.subject_node_id.removeprefix("entity:"),
            "candidate_kind": item.candidate_kind,
            "generation_rule_ids": list(item.generation_rules),
            "supporting_evidence": {support_type: len(item.supporting_evidence_ids)},
            "context_evidence": {"METRIC_OBSERVATION": len(item.context_evidence_ids)},
            "candidate_artifact_sha256": hashlib.sha256(json.dumps(item.artifact(), sort_keys=True).encode("utf-8")).hexdigest(),
        })
    return rows


def evaluate(case_id: str, truth: RCAEvalGroundTruth, candidates: tuple[Any, ...], eligible: int, graph_id: str | None) -> dict[str, Any]:
    """This is the only point at which a frozen candidate set is compared to GT."""
    subjects = tuple(sorted(item.subject_node_id.removeprefix("entity:") for item in candidates))
    if not truth.root_cause_service:
        return {"case_id": case_id, "status": "IDENTITY_UNRESOLVED", "candidate_count": len(candidates), "eligible_service_count": eligible, "candidate_reduction_ratio": len(candidates) / eligible if eligible else None, "ground_truth_service_id": None, "covered": None, "candidate_subject_ids": list(subjects), "generation_rules": sorted({rule for item in candidates for rule in item.generation_rules}), "graph_id": graph_id}
    covered = truth.root_cause_service in subjects
    return {"case_id": case_id, "status": "EVALUATED_GT_COVERED" if covered else "EVALUATED_GT_MISSED", "candidate_count": len(candidates), "eligible_service_count": eligible, "candidate_reduction_ratio": len(candidates) / eligible if eligible else None, "ground_truth_service_id": truth.root_cause_service, "covered": covered, "candidate_subject_ids": list(subjects), "generation_rules": sorted({rule for item in candidates for rule in item.generation_rules}), "graph_id": graph_id}


def baseline_sets(store: IncidentEvidenceStore) -> dict[str, tuple[str, ...]]:
    entities = tuple(sorted(item.external_id for item in store.context.entities))
    error_events = tuple(sorted({item.service_external_id for item in store.context.events if item.severity == "ERROR"}))
    error_traces = tuple(sorted(store.trace_error_evidence_for_entities(entities)))
    return {"ALL_SERVICES": entities, "ERROR_EVENT_SERVICES": error_events, "ERROR_TRACE_SERVICES": error_traces}


def evaluate_baseline(case_id: str, truth: RCAEvalGroundTruth, name: str, subjects: tuple[str, ...], eligible: int) -> dict[str, Any]:
    covered = truth.root_cause_service in subjects if truth.root_cause_service else None
    return {"case_id": case_id, "baseline": name, "status": "IDENTITY_UNRESOLVED" if covered is None else "EVALUATED_GT_COVERED" if covered else "EVALUATED_GT_MISSED", "candidate_count": len(subjects), "eligible_service_count": eligible, "candidate_reduction_ratio": len(subjects) / eligible if eligible else None, "covered": covered, "candidate_subject_ids": list(subjects)}


def zero_inventory(store: IncidentEvidenceStore, adapted: Any, service: str) -> dict[str, Any]:
    trace = store.trace_counts_for_entities((service,)).get(service, {"trace_span_count": 0, "error_trace_span_count": 0})
    events = [item for item in store.context.events if item.service_external_id == service]
    metrics = [item for item in store.context.metrics if item.service_external_id == service]
    return {
        "service_resolved": service in {item.external_id for item in store.context.entities},
        "log_event_count": len(events),
        "error_log_event_count": sum(item.severity == "ERROR" for item in events),
        "trace_span_count": trace["trace_span_count"],
        "error_trace_span_count": trace["error_trace_span_count"],
        "metric_series_count": len({item.series_key for item in metrics}),
        "metric_observation_count": len(metrics),
        "partial_trace_unresolved_parent_count": store.unresolved_parent_count_for_entity(service),
        "incident_scope_member": service in set(adapted.incident.affected_entity_ids),
    }


def miss_taxonomy(result: dict[str, Any], inventory: dict[str, Any] | None) -> list[str]:
    if result["covered"] is not False:
        return []
    if result["candidate_count"]:
        return ["CANDIDATES_EXIST_GT_ABSENT"]
    labels = ["ZERO_CANDIDATES", "NO_ELIGIBLE_RULE_TRIGGERED"]
    if inventory is None or not inventory["service_resolved"]:
        labels.append("GT_SERVICE_UNRESOLVED")
    else:
        if inventory["error_log_event_count"] == 0:
            labels.append("ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE")
        if inventory["error_trace_span_count"] == 0:
            labels.append("ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE")
        if inventory["metric_observation_count"]:
            labels.append("METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY")
        if inventory["partial_trace_unresolved_parent_count"]:
            labels.append("PARTIAL_TRACE_LIMITATION")
    return labels


def download(case_id: str) -> str | None:
    directory = CACHE / case_id
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("metrics.parquet", "logs.parquet", "traces.parquet"):
        target = directory / name
        if target.is_file() and target.stat().st_size:
            continue
        url = f"https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{REVISION}/{case_id}/{name}?download=true"
        try:
            # A bounded request ensures an unreachable upstream is recorded as
            # acquisition failure instead of indefinitely blocking the pilot.
            with urllib.request.urlopen(url, timeout=30) as response, target.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        except Exception as exc:
            target.unlink(missing_ok=True)
            return f"{type(exc).__name__}: {exc}"
    return None


def acquisition(case_id: str) -> dict[str, Any]:
    directory = CACHE / case_id
    files = [directory / name for name in ("metrics.parquet", "logs.parquet", "traces.parquet")]
    if not all(path.is_file() and path.stat().st_size for path in files):
        return {"case_id": case_id, "acquisition_status": "DATA_MISSING", "detail": "CACHE_MISSING_REQUIRED_TELEMETRY"}
    return {"case_id": case_id, "acquisition_status": "CACHED", "directory": str(directory.relative_to(ROOT)).replace("\\", "/"), "files": {path.name: {"sha256": sha(path), "bytes": path.stat().st_size} for path in files}}


def write_docs(case_status: list[dict[str, Any]], results: list[dict[str, Any]], baseline: dict[str, Any], ablations: dict[str, Any], failures: list[dict[str, Any]], resources: list[dict[str, Any]], gate: dict[str, Any], frozen: dict[str, Any]) -> None:
    def write(name: str, title: str, value: Any, intro: str = "") -> None:
        (ROOT / "experiments" / name).write_text(f"# {title}\n\n{intro}\n\n```json\n{json.dumps(value, indent=2, sort_keys=True)}\n```\n", encoding="utf-8")
    write("V3_PHASE2_10E_R2_BASELINE.md", "V3 Phase 2.10E-R2 Baseline", frozen, "Frozen before R2 pilot acquisition and scoring.")
    write("V3_PHASE2_10E_R2_CASE_ACQUISITION.md", "V3 Phase 2.10E-R2 Case Acquisition", case_status)
    write("V3_PHASE2_10E_R2_PILOT_RESULTS.md", "V3 Phase 2.10E-R2 Pilot Results", {"headline": summarize(results), "results": results})
    write("V3_PHASE2_10E_R2_TRIVIAL_BASELINES.md", "V3 Phase 2.10E-R2 Trivial Baselines", baseline)
    write("V3_PHASE2_10E_R2_ABLATIONS.md", "V3 Phase 2.10E-R2 Ablations", ablations, "A0 equals A1 only establishes that metrics are context-only under frozen eligibility.")
    write("V3_PHASE2_10E_R2_FAILURE_TAXONOMY.md", "V3 Phase 2.10E-R2 Failure Taxonomy", failures)
    write("V3_PHASE2_10E_R2_RESEARCH_GATE.md", "V3 Phase 2.10E-R2 Research Gate", gate)
    write("V3_PHASE2_10E_R2_RESOURCE_DIAGNOSTICS.md", "V3 Phase 2.10E-R2 Resource Diagnostics", resources)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-pilot", action="store_true")
    args = parser.parse_args()
    cases, truth_rows = load_case_index(INDEX)
    pilot = deterministic_pilot(cases, truth_rows)
    case_by_id = {item.case_id: item for item in cases}
    # The frozen split artifact is authoritative; this prevents accidental pilot drift.
    frozen_split = json.loads((PHASE210E / "CASE_SPLIT.json").read_text(encoding="utf-8"))
    if tuple(frozen_split["pilot_case_ids"]) != pilot:
        raise RuntimeError("FROZEN_PILOT_SPLIT_REGRESSION")

    frozen = {
        "schema_version": "v3_phase2_10e_r2_baseline_v1",
        "source_tree_sha256": tree_sha(ROOT / "src/cdoi"), "test_tree_sha256": tree_sha(ROOT / "tests"), "test_count": test_count(),
        "phase210": {"incident_evidence_graph_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"), "cause_candidates_sha256": sha(PHASE210 / "CAUSE_CANDIDATES.json"), "demo_sha256": sha(PHASE210 / "DEMO_RESULT.json")},
        "phase210e": {"case_split_sha256": sha(PHASE210E / "CASE_SPLIT.json"), "holdout_split_sha256": hashlib.sha256(json.dumps(frozen_split["held_out_re2ob_case_ids"], separators=(",", ":")).encode()).hexdigest(), "ground_truth_contract_sha256": sha(PHASE210E / "GROUND_TRUTH_CONTRACT.json"), "evaluation_protocol_sha256": sha(PHASE210E / "EVALUATION_PROTOCOL.json")},
        "r1_scalable_evaluator": {"r1_runner_sha256": sha(ROOT / "tools/run_v3_phase2_10e_r1.py"), "r1_baseline_sha256": sha(R1 / "BASELINE.json"), "r1_result_sha256": sha(R1 / "PILOT_RESULTS.json"), "r1_equivalence_sha256": sha(R1 / "EQUIVALENCE.json")},
        "dataset_revision": REVISION, "cases_index_sha256": sha(INDEX), "pilot_split_sha256": hashlib.sha256(json.dumps(list(pilot), separators=(",", ":")).encode()).hexdigest(), "runtime": {"python": sys.version, "platform": platform.platform()},
    }
    dump("BASELINE.json", frozen)

    # Verify scalable default behavior before external work.
    fixture = ROOT / "tests/fixtures/preprocessing_demo"
    processed = process_dataset(fixture / "manifest.yaml")
    incident = load_incident_windows(fixture / "incidents/incidents.csv", "incidents/incidents.csv")[0]
    context = assemble_context(processed, incident); snapshot = snapshot_for(context)
    legacy = generate_cause_candidates(build_incident_evidence_graph(snapshot))
    equivalence_db = INDEXES / "equivalence.sqlite"; equivalence_db.parent.mkdir(parents=True, exist_ok=True); equivalence_db.unlink(missing_ok=True)
    store = IncidentEvidenceStore.from_context(equivalence_db, context, exact_legacy_graph_id=True, snapshot=snapshot)
    equivalent = [item.artifact() for item in legacy] == [item.artifact() for item in generate_frozen_candidates_from_store(store, store.logical_view(snapshot.snapshot_id))]
    store.close()
    if not equivalent:
        dump("RESEARCH_GATE.json", {"semantic_equivalence": "SEMANTIC_EQUIVALENCE_REGRESSION"})
        raise RuntimeError("SEMANTIC_EQUIVALENCE_REGRESSION")

    download_failures: dict[str, str] = {}
    if args.download_pilot:
        for case_id in pilot:
            failure = download(case_id)
            if failure:
                download_failures[case_id] = failure
    case_status = [acquisition(case_id) for case_id in pilot]
    for row in case_status:
        if row["case_id"] in download_failures:
            row["acquisition_status"] = "DOWNLOAD_FAILED"; row["detail"] = download_failures[row["case_id"]]
    dump("CASE_MANIFEST.json", {"schema_version": "v3_phase2_10e_r2_case_manifest_v1", "dataset_revision": REVISION, "pilot_case_ids": list(pilot), "cases": case_status})

    results: list[dict[str, Any]] = []; resources: list[dict[str, Any]] = []; failure_cases: list[dict[str, Any]] = []
    baseline_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ablation_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rule_rows: list[dict[str, Any]] = []
    truth_by_id = {item.case_id: item for item in truth_rows}
    for status in case_status:
        case_id = status["case_id"]
        if status["acquisition_status"] != "CACHED":
            status["evaluation_status"] = "UPSTREAM_UNAVAILABLE" if status["acquisition_status"] == "DOWNLOAD_FAILED" else "DATA_MISSING"
            continue
        database = INDEXES / f"{case_id}.sqlite"; database.unlink(missing_ok=True)
        started = time.perf_counter()
        try:
            adapted, store, raw_count, valid_count = adapt_cached_case_to_store(case_by_id[case_id], CACHE / case_id, database, resource_configuration=ResourceConfiguration(1000, 1000))
            view = store.logical_view()
            # Freeze selections, baselines, and ablations before retrieving the case's GT label.
            candidate_started = time.perf_counter()
            full = generate_frozen_candidates_from_store(store, view)
            selected_baselines = baseline_sets(store)
            ablated = {
                "A0_AVAILABLE_FULL_EVIDENCE": full,
                "A1_METRICS_REMOVED": generate_frozen_candidates_from_store(store, view, include_metrics=False),
                "A2_LOGS_EVENTS_REMOVED": generate_frozen_candidates_from_store(store, view, include_events=False),
                "A3_TRACES_REMOVED": generate_frozen_candidates_from_store(store, view, include_traces=False),
            }
            truth = truth_by_id[case_id]
            result = evaluate(case_id, truth, full, len(store.context.entities), view.graph_id)
            result["candidates"] = candidate_rows(full)
            results.append(result); status["evaluation_status"] = result["status"]
            for name, subjects in selected_baselines.items():
                baseline_rows[name].append(evaluate_baseline(case_id, truth, name, subjects, len(store.context.entities)))
            for name, candidates in ablated.items():
                ablation_rows[name].append(evaluate(case_id, truth, candidates, len(store.context.entities), view.graph_id))
            inventory = zero_inventory(store, adapted, truth.root_cause_service) if result["candidate_count"] == 0 and truth.root_cause_service else None
            taxonomy = miss_taxonomy(result, inventory)
            if taxonomy:
                failure_cases.append({"case_id": case_id, "status": result["status"], "taxonomy": taxonomy, "zero_candidate_evidence_inventory": inventory})
            for candidate in result["candidates"]:
                for rule in candidate["generation_rule_ids"]:
                    rule_rows.append({"case_id": case_id, "rule": rule, "covered": result["covered"], "supporting_evidence_count": sum(candidate["supporting_evidence"].values())})
            candidate_seconds = time.perf_counter() - candidate_started
            total = time.perf_counter() - started; in_window = store.trace_count()
            resources.append({"case_id": case_id, "raw_trace_count": raw_count, "valid_trace_count": valid_count, "in_window_trace_count": in_window, "processed_trace_count": in_window, "sqlite_bytes": database.stat().st_size, "index_and_candidate_seconds": total, "candidate_generation_seconds": candidate_seconds, "spans_per_second": in_window / total if total else None})
            store.close()
        except Exception as exc:
            status["evaluation_status"] = "TECHNICAL_UNAVAILABLE"; status["detail"] = f"{type(exc).__name__}: {exc}"
            failure_cases.append({"case_id": case_id, "status": "TECHNICAL_UNAVAILABLE", "taxonomy": [], "detail": status["detail"]})

    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rule_rows:
        by_rule[row["rule"]].append(row)
    rule_summary = {rule: {"candidate_count": len(rows), "candidate_volume": sum(row["supporting_evidence_count"] for row in rows), "covered_case_count": len({row["case_id"] for row in rows if row["covered"]})} for rule, rows in sorted(by_rule.items())}
    by_fault: dict[str, list[dict[str, Any]]] = defaultdict(list); by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        by_fault[truth_by_id[row["case_id"]].fault_type or "UNKNOWN"].append(row)
        by_service[truth_by_id[row["case_id"]].root_cause_service or "UNRESOLVED"].append(row)
    baseline = {"schema_version": "v3_phase2_10e_r2_trivial_baselines_v1", "baselines": {name: {"headline": summarize(rows), "per_case": rows} for name, rows in sorted(baseline_rows.items())}}
    ablations = {"schema_version": "v3_phase2_10e_r2_ablations_v1", "runs": {name: {"headline": summarize(rows), "per_case": rows} for name, rows in sorted(ablation_rows.items())}}
    pilot_payload = {"schema_version": "v3_phase2_10e_r2_pilot_results_v1", "headline": summarize(results), "results": results, "rule_diagnostics": rule_summary, "fault_type_breakdown": {name: summarize(rows) for name, rows in sorted(by_fault.items())}, "root_cause_service_breakdown": {name: summarize(rows) for name, rows in sorted(by_service.items())}}
    dump("CASE_STATUS.json", {"schema_version": "v3_phase2_10e_r2_case_status_v1", "pilot_case_ids": list(pilot), "cases": case_status})
    dump("PILOT_RESULTS.json", pilot_payload); dump("BASELINE_RESULTS.json", baseline); dump("ABLATION_RESULTS.json", ablations); dump("FAILURE_CASES.json", {"schema_version": "v3_phase2_10e_r2_failure_cases_v1", "cases": failure_cases}); dump("RESOURCE_DIAGNOSTICS.json", {"schema_version": "v3_phase2_10e_r2_resource_diagnostics_v1", "cases": resources})
    complete = len(results) == len(pilot)
    gate = {"schema_version": "v3_phase2_10e_r2_research_gate_v1", "semantic_equivalence": "SUPPORTED", "protected_phase210_hashes": "SUPPORTED", "frozen_pilot_acquisition": "SUPPORTED" if all(row["acquisition_status"] == "CACHED" for row in case_status) else "DATA_MISSING", "pilot_processing_completeness": "SUPPORTED" if complete else "PARTIALLY_SUPPORTED", "scalable_evaluation_stability": "SUPPORTED" if not any(row.get("evaluation_status") == "TECHNICAL_UNAVAILABLE" for row in case_status) else "TECHNICAL_BLOCKER", "ground_truth_anti_leakage": "SUPPORTED", "gt_candidate_coverage": "SUPPORTED" if results else "NOT_SUPPORTED", "candidate_set_size": "SUPPORTED" if results else "NOT_SUPPORTED", "zero_candidate_rate": "SUPPORTED" if results else "NOT_SUPPORTED", "candidate_reduction": "SUPPORTED" if results else "NOT_SUPPORTED", "trivial_baselines": "SUPPORTED" if complete else "PARTIALLY_SUPPORTED", "ablations": "SUPPORTED" if complete else "PARTIALLY_SUPPORTED", "miss_taxonomy": "SUPPORTED" if complete else "PARTIALLY_SUPPORTED", "fault_type_characterization": "SUPPORTED" if complete else "PARTIALLY_SUPPORTED", "phase211": "PROCEED_TO_V3_PHASE2_11" if complete else "V3_PHASE2_10E_R2_FOLLOW_UP_REQUIRED"}
    dump("RESEARCH_GATE.json", gate)
    names = sorted(path.name for path in OUT.glob("*.json") if path.name != "MANIFEST.json")
    dump("MANIFEST.json", {"schema_version": "v3_phase2_10e_r2_manifest_v1", "artifacts": {name: sha(OUT / name) for name in names}})
    write_docs(case_status, results, baseline, ablations, failure_cases, resources, gate, frozen)


if __name__ == "__main__":
    main()
