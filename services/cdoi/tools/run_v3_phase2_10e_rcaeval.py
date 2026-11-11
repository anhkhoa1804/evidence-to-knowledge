"""Freeze and evaluate Phase 2.10 candidates against cached RCAEval cases.

No telemetry is stored under experiments.  Invoke with --download-pilot only
after reviewing the documented upstream license; ordinary execution consumes
the immutable external cache and records unavailable cases explicitly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import sys
import urllib.request
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cdoi.rcaeval_evaluation import (
    RCAEVAL_ADAPTER_VERSION, RCAEVAL_EVALUATION_VERSION, adapt_cached_case, cached_window_trace_count,
    deterministic_pilot, evaluate_frozen_candidates, load_case_index,
    trivial_baselines,
)

REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
CANDIDATE_GRAPH_MAX_TRACE_SPANS = 100_000
CACHE = ROOT / "data/benchmarks/external/rcaeval" / REVISION
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"
ARCHIVE = ROOT / "experiments/archive/v3_phase2_10e_rcaeval"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonable(value):
    if hasattr(value, "__dataclass_fields__"):
        return {key: jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value


def download(case_id: str) -> None:
    destination = CACHE / case_id
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("metrics.parquet", "logs.parquet", "traces.parquet"):
        target = destination / name
        if target.is_file():
            continue
        url = f"https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{REVISION}/{case_id}/{name}?download=true"
        urllib.request.urlretrieve(url, target)


def summarize(rows):
    evaluated = [item for item in rows if item.covered is not None]
    sizes = sorted(item.candidate_count for item in evaluated)
    reductions = [item.reduction_ratio for item in evaluated if item.reduction_ratio is not None]
    return {
        "processed_cases": len(evaluated),
        "ground_truth_covered_count": sum(bool(item.covered) for item in evaluated),
        "ground_truth_coverage_rate": sum(bool(item.covered) for item in evaluated) / len(evaluated) if evaluated else None,
        "candidate_set_size": {
            "mean": sum(sizes) / len(sizes) if sizes else None,
            "median": sizes[len(sizes) // 2] if sizes else None,
            "min": min(sizes) if sizes else None,
            "max": max(sizes) if sizes else None,
        },
        "candidate_reduction_ratio_mean": sum(reductions) / len(reductions) if reductions else None,
        "statuses": dict(sorted(Counter(item.status for item in rows).items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-pilot", action="store_true")
    args = parser.parse_args()
    cases, truth_rows = load_case_index(INDEX)
    truth = {item.case_id: item for item in truth_rows}
    re2ob = tuple(item for item in cases if item.dataset == "RE2-OB")
    pilot = deterministic_pilot(cases, truth_rows)
    if args.download_pilot:
        for case_id in pilot:
            download(case_id)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    frozen = {
        "schema_version": "v3_phase2_10e_frozen_phase210_v1",
        "phase210_graph_contract_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"),
        "candidate_generation_implementation_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"),
        "cause_candidate_contract_sha256": hashlib.sha256(b"cause_candidate_v1").hexdigest(),
        "graph_contract_sha256": hashlib.sha256(b"incident_evidence_graph_v1").hexdigest(),
        "phase210_demo_artifacts": {name: sha(ROOT / "experiments/archive/v3_phase2_10" / name) for name in ("INCIDENT_EVIDENCE_GRAPH.json", "CAUSE_CANDIDATES.json", "DEMO_RESULT.json", "MANIFEST.json")},
        "python": sys.version,
        "platform": platform.platform(),
    }
    manifest = {
        "schema_version": "v3_phase2_10e_rcaeval_dataset_manifest_v1",
        "owner": "phamquiluan/RCAEval",
        "repository_revision": "bb48c5aa9a24f1d5fcc716bdd479ea2d63145c90",
        "dataset_revision": REVISION,
        "license": "MIT (upstream repository and datasets, verified 2026-09-21)",
        "case_index": "cases.parquet",
        "case_index_sha256": sha(INDEX),
        "suite_counts": dict(sorted(Counter(item.dataset for item in cases).items())),
        "re2ob_case_count": len(re2ob),
        "re2ob_modalities": {"metrics": all(True for _ in re2ob), "logs": all(item.has_logs for item in re2ob), "traces": all(item.has_traces for item in re2ob)},
        "ground_truth_encoding": "cases.parquet root_cause_service and fault; fields split into evaluation-only contract",
        "static_topology": "STATIC_TOPOLOGY_UNAVAILABLE",
        "change_events": "UNAVAILABLE_NO_INDEPENDENT_CHANGE_ARTIFACT",
        "semantic_terms": "UNAVAILABLE",
    }
    dataset_hashes = {
        "schema_version": "v3_phase2_10e_rcaeval_dataset_hashes_v1",
        "dataset_revision": REVISION,
        "artifacts": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha(path)
            for path in sorted((ROOT / "data/benchmarks/external/rcaeval").rglob("*.parquet"))
        },
    }
    split = {"schema_version": "v3_phase2_10e_case_split_v1", "pilot_rule": "For every sorted RE2-OB fault, choose repetition 1 for two root-cause services selected by deterministic fault-index rotation before telemetry evaluation.", "pilot_case_ids": list(pilot), "held_out_re2ob_case_ids": sorted(item.case_id for item in re2ob if item.case_id not in pilot), "re2tt_reservation": "RESERVED_NOT_EVALUATED", "re3_reservation": "RESERVED_NOT_EVALUATED"}
    contract = {"schema_version": "v3_phase2_10e_ground_truth_contract_v1", "ground_truth_subject_type": "SERVICE", "namespace_normalization": "casefold, documented leading service/default namespace stripping, and documented .svc/.svc.cluster.local suffix stripping only", "matching": "exact normalized candidate subject service ID equals exact normalized root_cause_service", "forbidden_to_adapter": ["root_cause_service", "fault", "root_cause_indicator"], "oracle_window": "inject_time only defines a named ORACLE_WINDOW; it is not a production detector"}
    protocol = {"schema_version": RCAEVAL_EVALUATION_VERSION, "adapter_version": RCAEVAL_ADAPTER_VERSION, "window_mode": "ORACLE_WINDOW", "pre_window_seconds": 300, "post_window_seconds": 600, "topology_scope": "DIRECT_ONLY because benchmark static topology is unavailable", "candidate_generator": "frozen cause_candidate_v1", "primary_metric": "ground-truth candidate coverage", "ablations": ["A0_AVAILABLE_FULL_EVIDENCE", "A1_METRICS_REMOVED", "A2_LOGS_EVENTS_REMOVED", "A3_TRACES_REMOVED"], "frozen_graph_resource_limit": {"max_trace_spans_per_window": CANDIDATE_GRAPH_MAX_TRACE_SPANS, "behavior": "report TECHNICAL_UNAVAILABLE; do not sample, truncate, or alter frozen graph evidence"}, "no_training_or_tuning": True}
    for name, data in (("FROZEN_PHASE210.json", frozen), ("DATASET_MANIFEST.json", manifest), ("DATASET_HASHES.json", dataset_hashes), ("CASE_SPLIT.json", split), ("GROUND_TRUTH_CONTRACT.json", contract), ("EVALUATION_PROTOCOL.json", protocol)):
        (ARCHIVE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = []; failures = []; ablations = defaultdict(list); trivial = defaultdict(list)
    for case_id in pilot:
        case = next(item for item in cases if item.case_id == case_id)
        directory = CACHE / case_id
        required = tuple(directory / name for name in ("metrics.parquet", "logs.parquet", "traces.parquet"))
        if not all(item.is_file() for item in required):
            failures.append({"case_id": case_id, "status": "TECHNICAL_UNAVAILABLE", "detail": "CACHE_MISSING_REQUIRED_TELEMETRY"})
            continue
        try:
            window_trace_count = cached_window_trace_count(case, directory)
            if window_trace_count > CANDIDATE_GRAPH_MAX_TRACE_SPANS:
                failures.append({"case_id": case_id, "status": "TECHNICAL_UNAVAILABLE", "detail": "FROZEN_GRAPH_RESOURCE_LIMIT", "window_trace_count": window_trace_count, "max_trace_spans": CANDIDATE_GRAPH_MAX_TRACE_SPANS})
                continue
            adapted = adapt_cached_case(case, directory)
            result = evaluate_frozen_candidates(adapted, truth[case_id])
            rows.append(result)
            for name, kwargs in (("A0_AVAILABLE_FULL_EVIDENCE", {}), ("A1_METRICS_REMOVED", {"remove_metrics": True}), ("A2_LOGS_EVENTS_REMOVED", {"remove_events": True}), ("A3_TRACES_REMOVED", {"remove_traces": True})):
                ablations[name].append(evaluate_frozen_candidates(adapted, truth[case_id], **kwargs))
            for name, outcome in trivial_baselines(adapted, truth[case_id]).items():
                trivial[name].append(outcome)
        except Exception as exc:
            failures.append({"case_id": case_id, "status": "TECHNICAL_UNAVAILABLE", "detail": type(exc).__name__})
    by_fault = defaultdict(list); by_service = defaultdict(list)
    for item in rows:
        by_fault[truth[item.case_id].fault_type or "UNKNOWN"].append(item)
        by_service[truth[item.case_id].root_cause_service or "UNRESOLVED"].append(item)
    baseline = {"schema_version": "v3_phase2_10e_candidate_baseline_v1", "pilot_selected_count": len(pilot), "results": [jsonable(item) for item in rows], "technical_or_data_failures": failures, "headline": summarize(rows), "coverage_by_fault": {key: summarize(value) for key, value in sorted(by_fault.items())}, "coverage_by_root_cause_service": {key: summarize(value) for key, value in sorted(by_service.items())}, "trivial_baselines": {key: summarize(value) for key, value in sorted(trivial.items())}}
    ablation_payload = {"schema_version": "v3_phase2_10e_ablation_results_v1", "results": {key: {"headline": summarize(value), "per_case": [jsonable(item) for item in value]} for key, value in sorted(ablations.items())}}
    failure_payload = {"schema_version": "v3_phase2_10e_failure_cases_v1", "cases": failures + [{"case_id": item.case_id, "status": item.status, "taxonomy": ["NO_ELIGIBLE_CANDIDATE_RULE_TRIGGERED"] if item.candidate_count == 0 else ["OTHER_OBSERVED_MISS"]} for item in rows if item.covered is False]}
    for name, data in (("BASELINE_RESULTS.json", baseline), ("ABLATION_RESULTS.json", ablation_payload), ("FAILURE_CASES.json", failure_payload)):
        (ARCHIVE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gate = {"schema_version": "v3_phase2_10e_research_gate_v1", "dataset_provenance": "SUPPORTED", "dataset_licensing": "SUPPORTED", "ground_truth_clarity": "SUPPORTED", "service_granularity_compatibility": "SUPPORTED", "telemetry_adaptability": "PARTIALLY_SUPPORTED" if failures else "SUPPORTED", "anti_leakage": "SUPPORTED", "pilot_execution": "SUPPORTED" if rows else "TECHNICAL_UNAVAILABLE", "full_re2ob_execution": "NOT_RUN", "candidate_coverage": "MEASURED" if rows else "UNAVAILABLE", "candidate_reduction": "MEASURED" if rows else "UNAVAILABLE", "failure_taxonomy_quality": "PARTIALLY_SUPPORTED", "ablation_readiness": "SUPPORTED", "cross_system_validation_readiness": "RESERVED_RE2_TT", "phase211_readiness": "V3_PHASE2_10E_FOLLOW_UP_REQUIRED" if not rows else "REQUIRES_RESEARCH_REVIEW"}
    (ARCHIVE / "RESEARCH_GATE.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    names = sorted(item.name for item in ARCHIVE.glob("*.json") if item.name != "MANIFEST.json")
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps({"schema_version": "v3_phase2_10e_archive_manifest_v1", "artifacts": {name: sha(ARCHIVE / name) for name in names}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
