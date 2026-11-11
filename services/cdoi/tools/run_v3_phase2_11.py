"""Execute the frozen pilot for unranked Phase 2.11 hypotheses.

Candidate-generation artifacts are written before this program opens the
matching RCAEval ground-truth row.  This script intentionally never loads or
iterates over the protected holdout labels.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.hypothesis_generation import (
    HYPOTHESIS_GENERATION_VERSION,
    HypothesisConfiguration,
    generate_evidence_aware_hypotheses,
)
from cdoi.rcaeval_evaluation import RCAEvalCase, RCAEvalGroundTruth, normalize_service_id, adapt_cached_case_to_store
from cdoi.scalable_evidence import ResourceConfiguration, generate_frozen_candidates_from_store

REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
CACHE = ROOT / "data/benchmarks/external/rcaeval" / REVISION
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"
SPLIT = ROOT / "experiments/archive/v3_phase2_10e_rcaeval/CASE_SPLIT.json"
R2A = ROOT / "experiments/archive/v3_phase2_10e_r2a"
OUT = ROOT / "experiments/archive/v3_phase2_11"
INDEXES = ROOT / "data/benchmarks/external/rcaeval/phase211_indexes"
BASELINE = OUT / "BASELINE.json"

VARIANTS = {
    "H0_FROZEN_PHASE210": (False, False, False, False),
    "H1_METRIC": (True, False, False, False),
    "H2_TRACE_PARTICIPATION": (False, True, False, False),
    "H3_BOUNDED_TOPOLOGY": (False, False, True, False),
    "H4_TEMPORAL_CHANGE": (False, False, False, True),
    "H5_COMBINED": (True, True, True, True),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write(path: Path, value: Any) -> None:
    """Atomically freeze a JSON artifact before any post-hoc evaluation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_frozen_inputs() -> tuple[str, ...]:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    r2a_manifest = json.loads((R2A / "MANIFEST.json").read_text(encoding="utf-8"))
    mismatches = [name for name, digest in r2a_manifest["artifacts"].items() if sha(R2A / name) != digest]
    if mismatches:
        raise RuntimeError(f"FROZEN_R2A_MANIFEST_REGRESSION: {mismatches}")
    protected = {
        "phase210_graph_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"),
        "phase210_candidates_sha256": sha(ROOT / "experiments/archive/v3_phase2_10/CAUSE_CANDIDATES.json"),
        "r2a_manifest_sha256": sha(R2A / "MANIFEST.json"),
        "r2a_pilot_results_sha256": sha(R2A / "PILOT_RESULTS.json"),
        "r2a_case_status_sha256": sha(R2A / "CASE_STATUS.json"),
    }
    changed = [name for name, digest in protected.items() if baseline[name] != digest]
    if changed:
        raise RuntimeError(f"FROZEN_PHASE210_OR_R2A_REGRESSION: {changed}")
    # Only operational pilot identifiers are read from the split.  The holdout
    # collection is neither expanded nor passed to an evaluator in this phase.
    pilot = tuple(json.loads(SPLIT.read_text(encoding="utf-8"))["pilot_case_ids"])
    # The R2A baseline recorded the operationally selected pilot hash.  The
    # older Phase 2.11 baseline retains a pre-existing metadata discrepancy,
    # so it remains archival evidence rather than being rewritten here.
    r2a_baseline = json.loads((R2A / "BASELINE.json").read_text(encoding="utf-8"))
    if stable_sha(list(pilot)) != r2a_baseline["r2_pilot_split_sha256"]:
        raise RuntimeError("FROZEN_PILOT_SPLIT_REGRESSION")
    return pilot


def operational_cases(pilot: tuple[str, ...]) -> dict[str, RCAEvalCase]:
    """Read only operational index columns; labels stay unavailable here."""
    import pyarrow.parquet as parquet

    columns = ["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]
    table = parquet.read_table(INDEX, columns=columns, filters=[("case", "in", list(pilot))])
    cases = {}
    for row in table.to_pylist():
        case_id = str(row["case"])
        cases[case_id] = RCAEvalCase(
            case_id=case_id, dataset=str(row.get("dataset") or ""), system=str(row.get("system") or ""),
            injection_time=int(row["inject_time"]), time_start=int(row["time_start"]) if row.get("time_start") is not None else None,
            time_end=int(row["time_end"]) if row.get("time_end") is not None else None,
            has_logs=bool(row.get("has_logs")), has_traces=bool(row.get("has_traces")),
        )
    if tuple(sorted(cases)) != tuple(sorted(pilot)):
        raise RuntimeError("PILOT_OPERATIONAL_INDEX_INCOMPLETE")
    return cases


def read_ground_truth_after_freeze(case_id: str) -> RCAEvalGroundTruth:
    """Open one selected pilot label only after its generation artifact exists."""
    import pyarrow.parquet as parquet

    table = parquet.read_table(INDEX, columns=["case", "root_cause_service", "fault"], filters=[("case", "=", case_id)])
    rows = table.to_pylist()
    if len(rows) != 1 or str(rows[0]["case"]) != case_id:
        raise RuntimeError("PILOT_GROUND_TRUTH_ROW_UNAVAILABLE")
    return RCAEvalGroundTruth(case_id, "SERVICE", normalize_service_id(rows[0].get("root_cause_service")), str(rows[0].get("fault") or "").upper() or None)


def percentile_90(values: list[int]) -> int | None:
    return sorted(values)[math.ceil(len(values) * .9) - 1] if values else None


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in rows if row.get("covered") is not None]
    counts = [int(row["candidate_count"]) for row in rows]
    ratios = [float(row["candidate_service_ratio"]) for row in rows if row.get("candidate_service_ratio") is not None]
    return {
        "evaluated_count": len(rows),
        "covered_count": sum(row["covered"] is True for row in rows),
        "missed_count": sum(row["covered"] is False for row in rows),
        "candidate_stage_root_cause_coverage": sum(row["covered"] is True for row in rows) / len(rows) if rows else None,
        "zero_candidate_count": sum(count == 0 for count in counts),
        "zero_candidate_rate": sum(count == 0 for count in counts) / len(rows) if rows else None,
        "candidate_set_size": {"mean": statistics.mean(counts) if counts else None, "median": statistics.median(counts) if counts else None, "min": min(counts) if counts else None, "max": max(counts) if counts else None, "p90": percentile_90(counts)},
        "candidate_service_ratio": {"mean": statistics.mean(ratios) if ratios else None, "median": statistics.median(ratios) if ratios else None},
        "candidate_reduction_relative_to_all_services": {"mean": statistics.mean([1 - ratio for ratio in ratios]) if ratios else None, "median": statistics.median([1 - ratio for ratio in ratios]) if ratios else None},
        "statuses": dict(sorted(Counter(row["status"] for row in rows).items())),
    }


def candidate_rows(candidates: Iterable[Any]) -> list[dict[str, Any]]:
    return [{
        "candidate_id": item.candidate_id,
        "candidate_subject": item.subject_node_id.removeprefix("entity:"),
        "candidate_kind": item.candidate_kind,
        "status": item.status,
        "generation_rule_ids": list(item.generation_rules),
        "supporting_evidence_ids": list(item.supporting_evidence_ids),
        "context_evidence_ids": list(item.context_evidence_ids),
        "contradictory_evidence_ids": list(item.contradictory_evidence_ids),
        "candidate_artifact_sha256": stable_sha(item.artifact()),
    } for item in candidates]


def generation_artifact(case_id: str, adapted: Any, view: Any, variants: dict[str, Any], seconds: dict[str, float]) -> dict[str, Any]:
    return {
        "schema_version": "v3_phase2_11_candidate_generation_v1",
        "case_id": case_id,
        "input_manifest_hash": adapted.preprocessing.manifest_hash,
        "incident_window": {"start_time": adapted.incident.start_time, "end_time": adapted.incident.end_time, "mode": adapted.window_mode},
        "eligible_service_count": len(adapted.preprocessing.entities),
        "technical_status": "HYPOTHESES_GENERATED",
        "variants": {
            name: {"candidate_count": len(result["candidates"]), "candidates": candidate_rows(result["candidates"]), "aggregate_evidence": result["aggregate_evidence"], "generation_seconds": seconds[name]}
            for name, result in sorted(variants.items())
        },
        "serialization_order": "subject ID then deterministic candidate ID; this is not RCA ranking",
    }


def evaluation(case_id: str, truth: RCAEvalGroundTruth, candidates: tuple[Any, ...], eligible: int, graph_id: str | None) -> dict[str, Any]:
    subjects = tuple(sorted(item.subject_node_id.removeprefix("entity:") for item in candidates))
    covered = truth.root_cause_service in subjects if truth.root_cause_service else None
    return {"case_id": case_id, "status": "IDENTITY_UNRESOLVED" if covered is None else "EVALUATED_GT_COVERED" if covered else "EVALUATED_GT_MISSED", "candidate_count": len(candidates), "eligible_service_count": eligible, "candidate_service_ratio": len(candidates) / eligible if eligible else None, "ground_truth_service_id": truth.root_cause_service, "covered": covered, "candidate_subject_ids": list(subjects), "generation_rules": sorted({rule for item in candidates for rule in item.generation_rules}), "graph_id": graph_id}


def baseline_evaluation(case_id: str, truth: RCAEvalGroundTruth, name: str, subjects: tuple[str, ...], eligible: int) -> dict[str, Any]:
    covered = truth.root_cause_service in subjects if truth.root_cause_service else None
    return {"case_id": case_id, "baseline": name, "status": "IDENTITY_UNRESOLVED" if covered is None else "EVALUATED_GT_COVERED" if covered else "EVALUATED_GT_MISSED", "candidate_count": len(subjects), "eligible_service_count": eligible, "candidate_service_ratio": len(subjects) / eligible if eligible else None, "covered": covered, "candidate_subject_ids": list(subjects)}


def characterize(adapted: Any) -> dict[str, Any]:
    metrics = adapted.preprocessing.metrics
    by_series: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for item in metrics:
        by_series[(item.service_external_id, item.series_key)].append(item)
    intervals: list[float] = []
    for values in by_series.values():
        times = sorted(datetime.fromisoformat(item.observed_at.replace("Z", "+00:00")) for item in values)
        intervals.extend((times[index + 1] - times[index]).total_seconds() for index in range(len(times) - 1))
    series_counts = [len(items) for items in by_series.values()]
    maximum_count = max(series_counts, default=0)
    by_name: dict[str, list[float]] = defaultdict(list)
    for item in metrics:
        by_name[item.metric_name].append(item.value)
    return {"case_id": adapted.case.case_id, "metric_observation_count": len(metrics), "metric_series_count": len(by_series), "service_count_with_metrics": len({item.service_external_id for item in metrics}), "metric_names": sorted(by_name), "units": sorted({item.unit for item in metrics}), "metric_kinds": dict(sorted(Counter(item.metric_kind for item in metrics).items())), "metric_value_ranges": {name: {"min": min(values), "max": max(values)} for name, values in sorted(by_name.items())}, "series_observation_count": {"min": min(series_counts, default=0), "max": maximum_count, "median": statistics.median(series_counts) if series_counts else None}, "sampling_interval_seconds": {"min": min(intervals) if intervals else None, "median": statistics.median(intervals) if intervals else None, "max": max(intervals) if intervals else None}, "relative_series_missingness": {"definition": "1 - observation_count / maximum_series_observation_count within this case; it does not assume a sampling schedule", "mean": statistics.mean([1 - count / maximum_count for count in series_counts]) if maximum_count else None, "max": max((1 - count / maximum_count for count in series_counts), default=None)}, "series_with_unit_conflict": sum(len({item.unit for item in items}) > 1 for items in by_series.values()), "trace_span_count": None}


def failure_diagnostic(store: Any, adapted: Any, truth: RCAEvalGroundTruth, combined: tuple[Any, ...], aggregate_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    service = truth.root_cause_service or ""
    trace = store.trace_counts_for_entities((service,)).get(service, {"trace_span_count": 0, "error_trace_span_count": 0})
    events = [item for item in store.context.events if item.service_external_id == service]
    metrics = [item for item in store.context.metrics if item.service_external_id == service]
    triggered = [item for item in combined if item.subject_node_id == f"entity:{service}"]
    participating = [item for item in aggregate_evidence if item["service_external_id"] == service]
    topology_degree = sum(relation.source_external_id == service or relation.target_external_id == service for relation in store.context.relations)
    taxonomy = ["CANDIDATES_EXIST_GT_ABSENT"] if combined else ["ZERO_CANDIDATES", "NO_HYPOTHESIS_GENERATION_RULE_TRIGGERED"]
    return {"case_id": truth.case_id, "taxonomy": taxonomy, "ground_truth_diagnostics": {"service_resolved": service in {item.external_id for item in store.context.entities}, "incident_scope_member": service in set(adapted.incident.affected_entity_ids), "log_count": len(events), "error_log_count": sum(item.severity == "ERROR" for item in events), "trace_span_count": trace["trace_span_count"], "error_trace_count": trace["error_trace_span_count"], "metric_series_count": len({item.series_key for item in metrics}), "metric_observation_count": len(metrics), "change_count": sum(item.target_external_id == service for item in store.context.changes), "direct_static_topology_degree": topology_degree, "trace_participation_summary": participating, "rules_fired_on_gt_service": list(triggered[0].generation_rules) if triggered else [], "rules_fired_on_non_gt_candidates": {item.subject_node_id.removeprefix("entity:"): list(item.generation_rules) for item in combined if item not in triggered}}}


def write_docs(manifest: dict[str, Any], characterization: dict[str, Any], pilot: dict[str, Any], ablations: dict[str, Any], failures: dict[str, Any], performance: dict[str, Any], gate: dict[str, Any]) -> None:
    document = f"""# V3 Phase 2.11 Evidence-Aware Hypothesis Generation

Phase 2.11 adds an explicit, deterministic hypothesis-generation layer above the immutable Phase 2.10 candidate generator. It generates unranked `CauseCandidate` hypotheses only: it does not perform RCA ranking and it does not establish causality.

## Rules and provenance

H0 retains frozen Phase 2.10 candidates. H1 adds within-window metric level-shift aggregates, H2 adds trace-volume participation shifts, H3 makes one declared topology hop from evidence-backed seeds, H4 records pre-cutoff change context for those seeds, and H5 combines the families. Rules are fixed in the experiment manifest; their aggregate provenance records service/series, time bounds, counts, source digest, and input manifest. Candidate serialization is stable by subject and candidate ID and is explicitly non-semantic.

Metric eligibility excludes declared counters and unit-conflicted series. It requires at least 60 observations in each partition, a 50% median level shift, and 60% persistent post-cutoff excursion. Trace eligibility requires at least 100 pre/post spans and a twofold service-local volume shift. These fixed, label-independent constants are configuration, not scores.

## Anti-leakage and scope

For each pilot case the generator writes `CASE_RESULTS/<case>.json` before reading that single case's GT row; GT appears only in `CASE_EVALUATIONS`. The 78-case holdout is not loaded, enumerated, evaluated, or used for tuning. The operational evidence graph remains separate from the ontology/KG.

## Measured Results

```json
{json.dumps({"experiment_manifest": manifest, "data_characterization": characterization, "pilot": pilot, "ablations": ablations, "failures": failures, "performance": performance, "research_gate": gate}, indent=2, sort_keys=True)}
```

## Interpretation and limitations

These results measure candidate-stage GT coverage and candidate-set reduction jointly. A metric, trace, topology relation, or temporal association is eligibility/support/context evidence, not proof that its service caused an incident. RCAEval supplies no static topology or change evidence in this pilot, so H3/H4 can be inactive without invalidating their bounded synthetic mechanism tests. The next permitted action is governed by `RESEARCH_GATE.json`; no ranking is introduced here.
"""
    (ROOT / "experiments/V3_PHASE2_11_REPORT.md").write_text(document, encoding="utf-8")


def main() -> None:
    pilot_ids = verify_frozen_inputs()
    cases = operational_cases(pilot_ids)
    configuration = HypothesisConfiguration()
    baseline_payload = json.loads(BASELINE.read_text(encoding="utf-8"))
    manifest = {"schema_version": "v3_phase2_11_experiment_manifest_v1", "hypothesis_generation_version": HYPOTHESIS_GENERATION_VERSION, "dataset_revision": REVISION, "pilot_case_ids": list(pilot_ids), "case_index_sha256": sha(INDEX), "pilot_split_sha256": stable_sha(list(pilot_ids)), "protected_holdout": "NOT_READ_OR_EVALUATED", "configuration": asdict(configuration), "variants": {name: list(flags) for name, flags in VARIANTS.items()}, "r2a_manifest_sha256": sha(R2A / "MANIFEST.json"), "baseline_sha256": sha(BASELINE), "baseline_pilot_hash_metadata": {"stored": baseline_payload["pilot_split_sha256"], "authoritative_r2a": stable_sha(list(pilot_ids)), "status": "PRE_EXISTING_BASELINE_METADATA_DISCREPANCY_PRESERVED"}, "runtime": {"python": sys.version, "platform": platform.platform()}}
    write(OUT / "EXPERIMENT_MANIFEST.json", manifest)
    all_evaluations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    baseline_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    failures: list[dict[str, Any]] = []
    performance: list[dict[str, Any]] = []
    characterization: list[dict[str, Any]] = []
    case_status: list[dict[str, Any]] = []
    for case_id in pilot_ids:
        case = cases[case_id]
        database = INDEXES / f"{case_id}.sqlite"
        database.unlink(missing_ok=True)
        started = time.perf_counter()
        try:
            adapted, store, raw_trace_count, valid_trace_count = adapt_cached_case_to_store(case, CACHE / case_id, database, resource_configuration=ResourceConfiguration(1000, 1000))
            view = store.logical_view()
            selections: dict[str, dict[str, Any]] = {}
            generation_seconds: dict[str, float] = {}
            for name, flags in VARIANTS.items():
                rule_start = time.perf_counter()
                if name == "H0_FROZEN_PHASE210":
                    selections[name] = {"candidates": generate_frozen_candidates_from_store(store, view), "aggregate_evidence": []}
                else:
                    result = generate_evidence_aware_hypotheses(store, view, configuration=configuration, include_metric=flags[0], include_trace=flags[1], include_topology=flags[2], include_temporal_change=flags[3])
                    selections[name] = {"candidates": result.candidates, "aggregate_evidence": [item.artifact() for item in result.aggregate_evidence]}
                generation_seconds[name] = time.perf_counter() - rule_start
            artifact = generation_artifact(case_id, adapted, view, selections, generation_seconds)
            artifact_path = OUT / "CASE_RESULTS" / f"{case_id}.json"
            write(artifact_path, artifact)
            artifact_hash = sha(artifact_path)
            # The label access is deliberately sequenced after durable candidate output.
            truth = read_ground_truth_after_freeze(case_id)
            evaluations = {name: evaluation(case_id, truth, payload["candidates"], len(store.context.entities), view.graph_id) for name, payload in selections.items()}
            for name, row in evaluations.items(): all_evaluations[name].append(row)
            entities = tuple(sorted(item.external_id for item in store.context.entities))
            for name, subjects in {"ALL_SERVICES": entities, "ERROR_EVENT_SERVICES": tuple(sorted({item.service_external_id for item in store.context.events if item.severity == "ERROR"})), "ERROR_TRACE_SERVICES": tuple(sorted(store.trace_error_evidence_for_entities(entities)))}.items():
                baseline_rows[name].append(baseline_evaluation(case_id, truth, name, subjects, len(entities)))
            combined = selections["H5_COMBINED"]
            if evaluations["H5_COMBINED"]["covered"] is False:
                failures.append(failure_diagnostic(store, adapted, truth, combined["candidates"], combined["aggregate_evidence"]))
            total = time.perf_counter() - started
            characterization.append(characterize(adapted))
            characterization[-1]["trace_span_count"] = store.trace_count()
            performance.append({"case_id": case_id, "raw_trace_count": raw_trace_count, "valid_trace_count": valid_trace_count, "in_window_trace_count": store.trace_count(), "sqlite_bytes": database.stat().st_size, "total_seconds": total, "combined_generation_seconds": generation_seconds["H5_COMBINED"], "spans_per_second": store.trace_count() / total if total else None})
            write(OUT / "CASE_EVALUATIONS" / f"{case_id}.json", {"schema_version": "v3_phase2_11_gt_evaluation_v1", "case_id": case_id, "generation_artifact_sha256": artifact_hash, "evaluations": evaluations, "baselines": {name: rows[-1] for name, rows in baseline_rows.items()}, "fault_type": truth.fault_type})
            case_status.append({"case_id": case_id, "generation_status": "HYPOTHESES_GENERATED", "generation_artifact_sha256": artifact_hash, "evaluation_status": evaluations["H5_COMBINED"]["status"]})
            store.close()
        except Exception as exc:
            case_status.append({"case_id": case_id, "generation_status": "TECHNICAL_UNAVAILABLE", "detail": f"{type(exc).__name__}: {exc}"})
    data_characterization = {"schema_version": "v3_phase2_11_data_characterization_v1", "purpose": "Operational telemetry characterization; GT labels were not used to select metric or trace mechanics.", "cases": characterization, "aggregate": {"metric_observation_count": sum(row["metric_observation_count"] for row in characterization), "metric_series_count": sum(row["metric_series_count"] for row in characterization), "trace_span_count": sum(row["trace_span_count"] for row in characterization), "units": sorted({unit for row in characterization for unit in row["units"]}), "metric_kinds": dict(sorted(Counter(kind for row in characterization for kind, count in row["metric_kinds"].items() for _ in range(count)).items()))}}
    by_fault: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_evaluations["H5_COMBINED"]:
        truth = json.loads((OUT / "CASE_EVALUATIONS" / f"{row['case_id']}.json").read_text(encoding="utf-8"))
        by_fault[truth["fault_type"] or "UNKNOWN"].append(row)
    pilot = {"schema_version": "v3_phase2_11_pilot_results_v1", "headline": summarize(all_evaluations["H5_COMBINED"]), "results": all_evaluations["H5_COMBINED"], "fault_type_breakdown": {fault: summarize(rows) for fault, rows in sorted(by_fault.items())}, "comparison": {"frozen_phase210_r2a": json.loads((R2A / "PILOT_RESULTS.json").read_text(encoding="utf-8"))["headline"], "trivial_baselines": {name: summarize(rows) for name, rows in sorted(baseline_rows.items())}}}
    ablation = {"schema_version": "v3_phase2_11_ablation_results_v1", "runs": {name: {"headline": summarize(rows), "per_case": rows, "unique_gt_recoveries_vs_h0": sorted(row["case_id"] for row in rows if row["covered"] and not next(base for base in all_evaluations["H0_FROZEN_PHASE210"] if base["case_id"] == row["case_id"])["covered"])} for name, rows in sorted(all_evaluations.items())}}
    perf = {"schema_version": "v3_phase2_11_performance_v1", "cases": performance, "headline": {"total_seconds": sum(row["total_seconds"] for row in performance), "mean_seconds": statistics.mean([row["total_seconds"] for row in performance]) if performance else None, "mean_sqlite_bytes": statistics.mean([row["sqlite_bytes"] for row in performance]) if performance else None, "mean_spans_per_second": statistics.mean([row["spans_per_second"] for row in performance]) if performance else None, "boundedness": "Trace participation uses indexed SQLite GROUP BY and ordered evidence-ID digests; no trace execution graph is materialized."}}
    complete = len(all_evaluations["H5_COMBINED"]) == len(pilot_ids) and not any(row["generation_status"] == "TECHNICAL_UNAVAILABLE" for row in case_status)
    headline = summarize(all_evaluations["H5_COMBINED"])
    if not complete:
        decision = "TECHNICAL_SCALABILITY_REGRESSION"
    elif headline["candidate_stage_root_cause_coverage"] <= 0:
        decision = "EVIDENCE_AWARE_HYPOTHESIS_GENERATION_INSUFFICIENT"
    elif headline["candidate_reduction_relative_to_all_services"]["mean"] <= 0.25:
        decision = "CANDIDATE_RECALL_IMPROVED_REDUCTION_INSUFFICIENT"
    else:
        decision = "EVIDENCE_AWARE_HYPOTHESIS_GENERATION_SUPPORTED_BY_PILOT"
    gate = {"schema_version": "v3_phase2_11_research_gate_v1", "decision": decision, "pilot_complete": complete, "anti_leakage": "SUPPORTED: generation artifacts precede per-case GT reads", "protected_holdout": "UNTOUCHED", "no_ranking_or_causal_claim": "SUPPORTED", "next_step": "Freeze Phase 2.11 and validate once on the protected holdout without tuning." if decision == "EVIDENCE_AWARE_HYPOTHESIS_GENERATION_SUPPORTED_BY_PILOT" else "Perform failure analysis; do not introduce ranking, LLM RCA, or holdout tuning."}
    write(OUT / "CASE_STATUS.json", {"schema_version": "v3_phase2_11_case_status_v1", "pilot_case_ids": list(pilot_ids), "cases": case_status})
    write(OUT / "DATA_CHARACTERIZATION.json", data_characterization)
    write(OUT / "RULES.json", {"schema_version": "v3_phase2_11_rules_v1", "configuration": asdict(configuration), "variants": {name: list(flags) for name, flags in VARIANTS.items()}, "semantics": "Rules create unranked investigation hypotheses. They do not assign causal probability, confidence, or rank."})
    write(OUT / "PILOT_RESULTS.json", pilot)
    write(OUT / "ABLATION_RESULTS.json", ablation)
    write(OUT / "FAILURE_CASES.json", {"schema_version": "v3_phase2_11_failure_cases_v1", "cases": failures})
    write(OUT / "PERFORMANCE.json", perf)
    write(OUT / "RESEARCH_GATE.json", gate)
    artifact_paths = sorted(path for path in OUT.rglob("*.json") if path.name not in {"MANIFEST.json", "HASHES.json"})
    hashes = {path.relative_to(OUT).as_posix(): sha(path) for path in artifact_paths}
    write(OUT / "HASHES.json", {"schema_version": "v3_phase2_11_hashes_v1", "artifacts": hashes})
    manifest_paths = sorted(path for path in OUT.rglob("*.json") if path.name != "MANIFEST.json")
    write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_11_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in manifest_paths}})
    write_docs(manifest, data_characterization, pilot, ablation, {"cases": failures}, perf, gate)


if __name__ == "__main__":
    main()
