"""One-shot protected-holdout validation for frozen Phase 2.11 hypotheses.

This runner has a deliberately hard phase boundary: it creates every
label-free holdout candidate artifact before any RCAEval ground-truth column
is opened.  It must not be repurposed for threshold tuning or new rules.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import shutil
import socket
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.hypothesis_generation import HYPOTHESIS_GENERATION_VERSION, HypothesisConfiguration, generate_evidence_aware_hypotheses
from cdoi.rcaeval_evaluation import RCAEvalCase, RCAEvalGroundTruth, adapt_cached_case_to_store, normalize_service_id
from cdoi.scalable_evidence import ResourceConfiguration, STORE_VERSION, generate_frozen_candidates_from_store

REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
CACHE = ROOT / "data/benchmarks/external/rcaeval" / REVISION
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"
SPLIT = ROOT / "experiments/archive/v3_phase2_10e_rcaeval/CASE_SPLIT.json"
P211 = ROOT / "experiments/archive/v3_phase2_11"
OUT = ROOT / "experiments/archive/v3_phase2_12"
INDEXES = ROOT / "data/benchmarks/external/rcaeval/phase212_indexes"
FILES = ("metrics.parquet", "logs.parquet", "traces.parquet")
VARIANTS = {
    "H0_FROZEN_PHASE210": (False, False, False, False),
    "H1_METRIC": (True, False, False, False),
    "H2_TRACE_PARTICIPATION": (False, True, False, False),
    "H3_BOUNDED_TOPOLOGY": (False, False, True, False),
    "H4_TEMPORAL_CHANGE": (False, False, False, True),
    "H5_COMBINED": (True, True, True, True),
}
INFLATION_BUCKETS = (("1", 1, 1), ("2_3", 2, 3), ("4_6", 4, 6), ("7_9", 7, 9), ("10_PLUS", 10, None))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_once(path: Path, value: Any) -> None:
    """Create immutable protocol artifacts without silently rewriting a run."""
    if path.exists():
        return
    write(path, value)


def percentile(values: list[float], fraction: float) -> float | None:
    return sorted(values)[math.ceil(len(values) * fraction) - 1] if values else None


def parquet_valid(path: Path) -> bool:
    if not path.is_file() or not path.stat().st_size:
        return False
    try:
        import pyarrow.parquet as parquet
        parquet.ParquetFile(path).metadata
        return True
    except Exception:
        return False


def fetch(case_id: str, name: str, *, attempts: int = 3, timeout: int = 60) -> dict[str, Any]:
    """Acquire the pinned raw artifact with bounded, resumable retries."""
    directory = CACHE / case_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    url = f"https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{REVISION}/{case_id}/{name}?download=true"
    if parquet_valid(target):
        return {"name": name, "status": "CACHED", "path": str(target.relative_to(ROOT)).replace("\\", "/"), "bytes": target.stat().st_size, "sha256": sha(target), "url": url}
    part = target.with_suffix(target.suffix + ".part")
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        offset = part.stat().st_size if part.exists() else 0
        request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                resumed = bool(offset and getattr(response, "status", response.getcode()) == 206)
                with part.open("ab" if resumed else "wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                part.replace(target)
                if not parquet_valid(target):
                    target.replace(part)
                    return {"name": name, "status": "DATA_INVALID", "detail": "DOWNLOADED_FILE_IS_NOT_VALID_PARQUET", "url": url}
                return {"name": name, "status": "DOWNLOADED", "path": str(target.relative_to(ROOT)).replace("\\", "/"), "bytes": target.stat().st_size, "sha256": sha(target), "remote_etag": response.headers.get("ETag"), "url": url, "attempt": attempt}
        except Exception as exc:
            last = exc
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    assert last is not None
    detail = "DOWNLOAD_FAILED_TIMEOUT" if isinstance(last, (TimeoutError, socket.timeout)) else "DOWNLOAD_FAILED_CONNECTION" if isinstance(last, urllib.error.URLError) else "ACQUISITION_FAILED"
    return {"name": name, "status": detail, "detail": f"{type(last).__name__}: {last}", "url": url}


def acquire(case_id: str) -> dict[str, Any]:
    artifacts = [fetch(case_id, name) for name in FILES]
    status = "CACHED" if all(row["status"] in {"CACHED", "DOWNLOADED"} for row in artifacts) else next(row["status"] for row in artifacts if row["status"] not in {"CACHED", "DOWNLOADED"})
    return {"case_id": case_id, "acquisition_status": status, "artifacts": artifacts}


def verify_phase211() -> tuple[tuple[str, ...], dict[str, Any], dict[str, Any]]:
    manifest = json.loads((P211 / "MANIFEST.json").read_text(encoding="utf-8"))
    mismatches = [name for name, digest in manifest["artifacts"].items() if sha(P211 / name) != digest]
    if mismatches:
        raise RuntimeError(f"FROZEN_PHASE211_MANIFEST_REGRESSION: {mismatches}")
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    holdout = tuple(split["held_out_re2ob_case_ids"])
    experiment = json.loads((P211 / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
    configuration = HypothesisConfiguration()
    checks = {
        "phase211_manifest": {"status": "PASS", "sha256": sha(P211 / "MANIFEST.json")},
        "phase211_hashes": {"status": "PASS", "sha256": sha(P211 / "HASHES.json")},
        "phase211_configuration": {"status": "PASS" if experiment["configuration"] == asdict(configuration) else "FAIL", "stored": experiment["configuration"], "actual": asdict(configuration)},
        "hypothesis_generator_source": {"status": "DOCUMENTED_PRE_EXISTING_DISCREPANCY", "actual_sha256": sha(ROOT / "src/cdoi/hypothesis_generation.py"), "detail": "Phase 2.11 archive hashes its artifacts but does not contain an individual implementation-source digest; current source is frozen by this Phase 2.12 preregistration."},
        "sqlite_store_source": {"status": "DOCUMENTED_PRE_EXISTING_DISCREPANCY", "actual_sha256": sha(ROOT / "src/cdoi/scalable_evidence.py"), "store_version": STORE_VERSION, "detail": "Phase 2.11 archive does not contain an individual store-source digest."},
        "dataset_revision": {"status": "PASS" if experiment["dataset_revision"] == REVISION else "FAIL", "stored": experiment["dataset_revision"], "expected": REVISION},
        "pilot_split": {"status": "PASS" if stable_sha(split["pilot_case_ids"]) == experiment["pilot_split_sha256"] else "FAIL", "sha256": stable_sha(split["pilot_case_ids"])},
        "holdout_split": {"status": "PASS", "case_count": len(holdout), "sha256": stable_sha(list(holdout))},
        "candidate_schema": {"status": "PASS", "candidate_status": "CANDIDATE_UNEVALUATED", "hypothesis_version": HYPOTHESIS_GENERATION_VERSION},
    }
    if any(value["status"] == "FAIL" for value in checks.values()):
        raise RuntimeError("PRE_HOLDOUT_INTEGRITY_FAILURE")
    return holdout, checks, experiment


def operational_cases(case_ids: tuple[str, ...]) -> dict[str, RCAEvalCase]:
    """Read operational columns only; GT columns are unavailable in phase A."""
    import pyarrow.parquet as parquet
    columns = ["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]
    table = parquet.read_table(INDEX, columns=columns, filters=[("case", "in", list(case_ids))])
    result = {}
    for row in table.to_pylist():
        case_id = str(row["case"])
        result[case_id] = RCAEvalCase(case_id, str(row.get("dataset") or ""), str(row.get("system") or ""), int(row["inject_time"]), int(row["time_start"]) if row.get("time_start") is not None else None, int(row["time_end"]) if row.get("time_end") is not None else None, bool(row.get("has_logs")), bool(row.get("has_traces")))
    if set(result) != set(case_ids):
        raise RuntimeError("HOLDOUT_OPERATIONAL_INDEX_INCOMPLETE")
    return result


def truth_after_generation(case_id: str) -> RCAEvalGroundTruth:
    """The only function that opens a label column, called in phase B only."""
    import pyarrow.parquet as parquet
    table = parquet.read_table(INDEX, columns=["case", "root_cause_service", "fault"], filters=[("case", "=", case_id)])
    rows = table.to_pylist()
    if len(rows) != 1:
        raise RuntimeError("HOLDOUT_GROUND_TRUTH_ROW_UNAVAILABLE")
    row = rows[0]
    return RCAEvalGroundTruth(case_id, "SERVICE", normalize_service_id(row.get("root_cause_service")), str(row.get("fault") or "").upper() or None)


def candidate_rows(candidates: Iterable[Any]) -> list[dict[str, Any]]:
    return [{"candidate_id": item.candidate_id, "subject": item.subject_node_id.removeprefix("entity:"), "candidate_kind": item.candidate_kind, "status": item.status, "generation_rule_ids": list(item.generation_rules), "supporting_evidence_ids": list(item.supporting_evidence_ids), "context_evidence_ids": list(item.context_evidence_ids), "contradictory_evidence_ids": list(item.contradictory_evidence_ids)} for item in candidates]


def frozen_candidate(path: Path, case_id: str) -> dict[str, Any]:
    """Validate a label-free Phase-A artifact before reusing it on resume."""
    candidate = json.loads(path.read_text(encoding="utf-8"))
    prohibited = ("ground_truth", "root_cause", "fault_type", '"covered"')
    if candidate.get("schema_version") != "v3_phase2_12_holdout_candidates_v1":
        raise RuntimeError(f"FROZEN_CANDIDATE_SCHEMA_INVALID: {path.name}")
    if candidate.get("case_id") != case_id:
        raise RuntimeError(f"FROZEN_CANDIDATE_CASE_MISMATCH: {path.name}")
    if set(candidate.get("variants", {})) != set(VARIANTS):
        raise RuntimeError(f"FROZEN_CANDIDATE_VARIANTS_INVALID: {path.name}")
    if any(token in json.dumps(candidate, sort_keys=True).casefold() for token in prohibited):
        raise RuntimeError(f"FROZEN_CANDIDATE_CONTAINS_GROUND_TRUTH: {path.name}")
    return candidate


def phase_a_freeze(
    holdout_ids: tuple[str, ...],
    status_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Freeze globally accounted label-free candidate generation before Phase B."""
    candidate_dir = OUT / "HOLDOUT_CANDIDATES"
    expected = set(holdout_ids)
    by_case = {row["case_id"]: row for row in status_rows}
    if set(by_case) != expected or len(by_case) != len(status_rows):
        raise RuntimeError("PHASE_A_CASE_ACCOUNTING_INCOMPLETE")
    candidate_hashes: dict[str, str] = {}
    failures = []
    for case_id in holdout_ids:
        row = by_case[case_id]
        path = candidate_dir / f"{case_id}.json"
        if row["generation_status"] in {"HYPOTHESES_GENERATED", "CANDIDATE_ARTIFACT_FROZEN"}:
            frozen_candidate(path, case_id)
            candidate_hashes[path.name] = sha(path)
        elif row["generation_status"] not in {
            "DATA_INVALID",
            "DOWNLOAD_FAILED_TIMEOUT",
            "DOWNLOAD_FAILED_CONNECTION",
            "ACQUISITION_FAILED",
            "TECHNICAL_UNAVAILABLE",
        }:
            raise RuntimeError(f"PHASE_A_STATUS_NOT_FINAL: {case_id}")
        else:
            failures.append(row)
    evaluation_dir = OUT / "HOLDOUT_EVALUATIONS"
    if evaluation_dir.exists() and any(evaluation_dir.glob("*.json")):
        raise RuntimeError("PHASE_A_FREEZE_REFUSES_PREEXISTING_GROUND_TRUTH_EVALUATIONS")
    freeze = {
        "schema_version": "v3_phase2_12_phase_a_freeze_v1",
        "phase": "A_LABEL_FREE_CANDIDATE_GENERATION",
        "expected_holdout_count": len(holdout_ids),
        "expected_case_set_sha256": stable_sha(list(holdout_ids)),
        "candidate_artifact_count": len(candidate_hashes),
        "candidate_artifacts": dict(sorted(candidate_hashes.items())),
        "technical_or_data_failures": failures,
        "source_revision": REVISION,
        "generator_configuration_sha256": stable_sha(manifest["configuration"]),
        "phase211_rule_sha256": sha(P211 / "RULES.json"),
        "experiment_manifest_sha256": sha(OUT / "EXPERIMENT_MANIFEST.json"),
        "holdout_evaluations_empty": True,
        "completed_at_utc": datetime.now().astimezone().isoformat(),
    }
    existing = OUT / "PHASE_A_FREEZE.json"
    if existing.exists():
        stored = json.loads(existing.read_text(encoding="utf-8"))
        if stored["candidate_artifacts"] != freeze["candidate_artifacts"] or stored["expected_case_set_sha256"] != freeze["expected_case_set_sha256"]:
            raise RuntimeError("PHASE_A_FREEZE_IMMUTABILITY_VIOLATION")
        return stored
    write(existing, freeze)
    return freeze


def selection_payload(store: Any, view: Any, configuration: HypothesisConfiguration) -> dict[str, Any]:
    selections = {}
    for name, flags in VARIANTS.items():
        if name == "H0_FROZEN_PHASE210":
            candidates, aggregates = generate_frozen_candidates_from_store(store, view), []
        else:
            result = generate_evidence_aware_hypotheses(store, view, configuration=configuration, include_metric=flags[0], include_trace=flags[1], include_topology=flags[2], include_temporal_change=flags[3])
            candidates, aggregates = result.candidates, [item.artifact() for item in result.aggregate_evidence]
        selections[name] = {"candidate_count": len(candidates), "candidates": candidate_rows(candidates), "aggregate_evidence": aggregates}
    return selections


def characterize(adapted: Any, store: Any, raw_count: int, valid_count: int) -> dict[str, Any]:
    metrics = adapted.preprocessing.metrics
    grouped: dict[tuple[str, str], list[Any]] = defaultdict(list)
    by_name: dict[str, list[float]] = defaultdict(list)
    for item in metrics:
        grouped[(item.service_external_id, item.series_key)].append(item); by_name[item.metric_name].append(item.value)
    counts = [len(value) for value in grouped.values()]
    maximum = max(counts, default=0)
    intervals = []
    for values in grouped.values():
        timestamps = sorted(datetime.fromisoformat(item.observed_at.replace("Z", "+00:00")) for item in values)
        intervals.extend((timestamps[index + 1] - timestamps[index]).total_seconds() for index in range(len(timestamps) - 1))
    return {"case_id": adapted.case.case_id, "eligible_service_count": len(store.context.entities), "metric": {"observation_count": len(metrics), "series_count": len(grouped), "metric_names": sorted(by_name), "metric_kinds": dict(sorted(Counter(item.metric_kind for item in metrics).items())), "units": sorted({item.unit for item in metrics}), "value_ranges": {name: {"min": min(values), "max": max(values)} for name, values in sorted(by_name.items())}, "series_observation_counts": {"min": min(counts, default=0), "median": statistics.median(counts) if counts else None, "max": maximum}, "sampling_interval_seconds": {"min": min(intervals) if intervals else None, "median": statistics.median(intervals) if intervals else None, "max": max(intervals) if intervals else None}, "relative_series_missingness": {"definition": "1 - observations / maximum series observations within case; no schedule is assumed", "mean": statistics.mean([1 - value / maximum for value in counts]) if maximum else None, "max": max((1 - value / maximum for value in counts), default=None)}, "unit_conflict_series_count": sum(len({item.unit for item in values}) > 1 for values in grouped.values())}, "traces": {"raw_span_count": raw_count, "valid_span_count": valid_count, "in_window_span_count": store.trace_count(), "resolved_service_count": len(store.context.entities), "unresolved_parent_span_count": sum(store.unresolved_parent_count_for_entity(item.external_id) for item in store.context.entities)}, "topology": {"available": bool(store.context.relations), "edge_count": len(store.context.relations), "service_coverage": len({service for relation in store.context.relations for service in (relation.source_external_id, relation.target_external_id)})}, "changes": {"available": bool(store.context.changes), "event_count": len(store.context.changes), "service_coverage": len({item.target_external_id for item in store.context.changes})}}


def evaluate(case_id: str, truth: RCAEvalGroundTruth, selection: dict[str, Any], eligible: int) -> dict[str, Any]:
    subjects = [row["subject"] for row in selection["candidates"]]
    covered = truth.root_cause_service in subjects if truth.root_cause_service else None
    return {"case_id": case_id, "status": "IDENTITY_UNRESOLVED" if covered is None else "EVALUATED_GT_COVERED" if covered else "EVALUATED_GT_MISSED", "candidate_count": len(subjects), "eligible_service_count": eligible, "candidate_service_ratio": len(subjects) / eligible if eligible else None, "covered": covered, "ground_truth_service_id": truth.root_cause_service, "candidate_subject_ids": subjects, "generation_rules": sorted({rule for row in selection["candidates"] for rule in row["generation_rule_ids"]})}


def summary(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in rows if row.get("covered") is not None]
    counts = [row["candidate_count"] for row in rows]
    ratios = [row["candidate_service_ratio"] for row in rows if row.get("candidate_service_ratio") is not None]
    covered = sum(row["covered"] is True for row in rows)
    n = len(rows)
    # Wilson 95% interval avoids a degenerate normal approximation at 0 or 1.
    z, denominator = 1.959963984540054, 1 + 1.959963984540054 ** 2 / n if n else None
    center = ((covered / n) + z ** 2 / (2 * n)) / denominator if n else None
    half = z * math.sqrt((covered / n * (1 - covered / n) + z ** 2 / (4 * n)) / n) / denominator if n else None
    return {"evaluated_count": n, "covered_count": covered, "missed_count": n - covered, "candidate_stage_root_cause_coverage": covered / n if n else None, "coverage_wilson_95_interval": [max(0, center - half), min(1, center + half)] if center is not None and half is not None else None, "zero_candidate_count": sum(value == 0 for value in counts), "zero_candidate_rate": sum(value == 0 for value in counts) / n if n else None, "candidate_set_size": {"mean": statistics.mean(counts) if counts else None, "median": statistics.median(counts) if counts else None, "min": min(counts) if counts else None, "max": max(counts) if counts else None, "p90": percentile(counts, .90), "p95": percentile(counts, .95)}, "candidate_service_ratio": {"mean": statistics.mean(ratios) if ratios else None, "median": statistics.median(ratios) if ratios else None}, "candidate_reduction_relative_to_all_services": {"mean": statistics.mean([1 - value for value in ratios]) if ratios else None, "median": statistics.median([1 - value for value in ratios]) if ratios else None}, "statuses": dict(sorted(Counter(row["status"] for row in rows).items()))}


def baseline_rows(case_id: str, truth: RCAEvalGroundTruth, candidates: dict[str, Any], eligible: int) -> dict[str, dict[str, Any]]:
    subjects = {
        "ALL_SERVICES": tuple(sorted(candidates["eligible_services"])),
        "ERROR_EVENT_SERVICES": tuple(sorted(candidates["error_event_services"])),
        "ERROR_TRACE_SERVICES": tuple(sorted(candidates["error_trace_services"])),
    }
    output = {}
    for name, values in subjects.items():
        covered = truth.root_cause_service in values if truth.root_cause_service else None
        output[name] = {"case_id": case_id, "baseline": name, "status": "IDENTITY_UNRESOLVED" if covered is None else "EVALUATED_GT_COVERED" if covered else "EVALUATED_GT_MISSED", "candidate_count": len(values), "eligible_service_count": eligible, "candidate_service_ratio": len(values) / eligible if eligible else None, "covered": covered, "candidate_subject_ids": list(values)}
    return output


def main() -> None:
    holdout_ids, integrity, phase211 = verify_phase211()
    configuration = HypothesisConfiguration()
    preregistration = {"schema_version": "v3_phase2_12_preregistration_v1", "primary_system": "H5_COMBINED", "secondary_systems": list(VARIANTS), "primary_question": "Does frozen H5 retain root-cause candidate coverage while meaningfully reducing the candidate set relative to ALL_SERVICES on the protected holdout?", "frozen_phase211_manifest_sha256": sha(P211 / "MANIFEST.json"), "holdout_case_count": len(holdout_ids), "holdout_split_sha256": stable_sha(list(holdout_ids)), "configuration": asdict(configuration), "determinism_case_ids": list(sorted(holdout_ids)[:3]), "candidate_inflation_buckets": [{"name": name, "minimum": low, "maximum": high} for name, low, high in INFLATION_BUCKETS], "prohibitions": ["No threshold/rule/identity/window/candidate-semantic changes after this artifact.", "No GT read until all label-free holdout candidate artifacts and data characterization are frozen.", "H5 remains primary regardless of secondary results."]}
    write_once(OUT / "PREREGISTRATION.json", preregistration)
    write_once(OUT / "PRE_HOLDOUT_INTEGRITY.json", {"schema_version": "v3_phase2_12_pre_holdout_integrity_v1", "overall_status": "PASS", "checks": integrity})
    write_once(OUT / "BASELINE_HASH_DISCREPANCY_NOTE.json", {"schema_version": "v3_phase2_12_baseline_hash_discrepancy_v1", "status": "DOCUMENTED_PRE_EXISTING_DISCREPANCY", "phase211_baseline_stored_pilot_hash": phase211["baseline_pilot_hash_metadata"]["stored"], "authoritative_r2a_pilot_hash": phase211["baseline_pilot_hash_metadata"]["authoritative_r2a"], "current_split_pilot_hash": stable_sha(json.loads(SPLIT.read_text(encoding="utf-8"))["pilot_case_ids"]), "resolution": "The current split equals the authoritative R2A value. Historical Phase 2.11 files are not rewritten; the discrepancy does not change the pilot or protected-holdout membership."})
    performance211 = json.loads((P211 / "PERFORMANCE.json").read_text(encoding="utf-8"))
    write_once(OUT / "PERFORMANCE_DISCREPANCY_NOTE.json", {"schema_version": "v3_phase2_12_performance_discrepancy_note_v1", "authoritative_artifact": "experiments/archive/v3_phase2_11/PERFORMANCE.json", "sha256": sha(P211 / "PERFORMANCE.json"), "total_seconds": performance211["headline"]["total_seconds"], "mean_spans_per_second": performance211["headline"]["mean_spans_per_second"], "mean_sqlite_bytes": performance211["headline"]["mean_sqlite_bytes"], "alternate_reported_numbers": "The checked Phase 2.11 report embeds the same frozen performance artifact; no competing frozen artifact was identified."})
    manifest = {"schema_version": "v3_phase2_12_experiment_manifest_v1", "phase211_manifest_sha256": sha(P211 / "MANIFEST.json"), "preregistration_sha256": sha(OUT / "PREREGISTRATION.json"), "dataset_revision": REVISION, "holdout_case_count": len(holdout_ids), "holdout_split_sha256": stable_sha(list(holdout_ids)), "configuration": asdict(configuration), "variants": {name: list(value) for name, value in VARIANTS.items()}, "source_sha256": {"hypothesis_generation.py": sha(ROOT / "src/cdoi/hypothesis_generation.py"), "scalable_evidence.py": sha(ROOT / "src/cdoi/scalable_evidence.py")}, "runtime": {"python": sys.version, "platform": platform.platform()}, "execution_protocol": "PHASE_A_ALL_LABEL_FREE_CANDIDATES_THEN_PHASE_B_GROUND_TRUTH_EVALUATION"}
    write_once(OUT / "EXPERIMENT_MANIFEST.json", manifest)
    write_once(OUT / "PHASE_A_BOUNDARY_CORRECTION.json", {
        "schema_version": "v3_phase2_12_phase_a_boundary_correction_v1",
        "status": "CORRECTED_BEFORE_HOLDOUT_GROUND_TRUTH_ACCESS",
        "pre_existing_runner_issue": "Phase B was reachable after all available artifacts, rather than after every expected holdout case had a final Phase-A status.",
        "correction": "Existing label-free artifacts are validated and preserved; Phase B is gated on PHASE_A_FREEZE.json covering every expected case and an empty evaluation directory.",
        "historical_artifacts_rewritten": False,
    })
    cases = operational_cases(holdout_ids)
    characterizations, acquisition_rows, performance_rows, status_rows = [], [], [], []
    # Phase A: this loop never calls truth_after_generation or opens a GT column.
    for case_id in holdout_ids:
        candidate_path = OUT / "HOLDOUT_CANDIDATES" / f"{case_id}.json"
        if candidate_path.exists():
            frozen_candidate(candidate_path, case_id)
            acquisition = acquire(case_id); acquisition_rows.append(acquisition)
            if acquisition["acquisition_status"] == "CACHED":
                database = INDEXES / f"{case_id}.sqlite"; database.unlink(missing_ok=True)
                started = time.perf_counter()
                try:
                    adapted, store, raw_count, valid_count = adapt_cached_case_to_store(cases[case_id], CACHE / case_id, database, resource_configuration=ResourceConfiguration(1000, 1000))
                    characterizations.append(characterize(adapted, store, raw_count, valid_count))
                    total = time.perf_counter() - started
                    performance_rows.append({"case_id": case_id, "raw_span_count": raw_count, "valid_span_count": valid_count, "in_window_span_count": store.trace_count(), "sqlite_bytes": database.stat().st_size, "candidate_generation_seconds": None, "total_seconds": total, "spans_per_second": store.trace_count() / total if total else None, "candidate_artifact_reused": True})
                    store.close()
                except Exception as exc:
                    acquisition["frozen_candidate_characterization"] = f"UNAVAILABLE: {type(exc).__name__}: {exc}"
            else:
                # Candidate generation is already immutable; retain the artifact but
                # make missing raw data visible in Phase-A diagnostics.
                acquisition["frozen_candidate_characterization"] = "UNAVAILABLE"
            status_rows.append({"case_id": case_id, "generation_status": "CANDIDATE_ARTIFACT_FROZEN", "candidate_artifact_sha256": sha(candidate_path)})
            continue
        acquisition = acquire(case_id); acquisition_rows.append(acquisition)
        if acquisition["acquisition_status"] != "CACHED":
            status_rows.append({"case_id": case_id, "generation_status": acquisition["acquisition_status"]}); continue
        database = INDEXES / f"{case_id}.sqlite"; database.unlink(missing_ok=True)
        started = time.perf_counter()
        try:
            adapted, store, raw_count, valid_count = adapt_cached_case_to_store(cases[case_id], CACHE / case_id, database, resource_configuration=ResourceConfiguration(1000, 1000))
            view = store.logical_view(); generation_started = time.perf_counter(); selections = selection_payload(store, view, configuration); generation_seconds = time.perf_counter() - generation_started
            eligible_services = tuple(sorted(item.external_id for item in store.context.entities))
            artifact = {"schema_version": "v3_phase2_12_holdout_candidates_v1", "case_id": case_id, "input_manifest_hash": adapted.preprocessing.manifest_hash, "incident_window": {"start_time": adapted.incident.start_time, "end_time": adapted.incident.end_time, "mode": adapted.window_mode}, "eligible_service_count": len(eligible_services), "eligible_services": list(eligible_services), "error_event_services": sorted({item.service_external_id for item in store.context.events if item.severity == "ERROR"}), "error_trace_services": sorted(store.trace_error_evidence_for_entities(eligible_services)), "technical_status": "HYPOTHESES_GENERATED", "variants": selections, "serialization_order": "subject ID then deterministic candidate ID; this is not RCA ranking"}
            write(candidate_path, artifact)
            characterizations.append(characterize(adapted, store, raw_count, valid_count))
            total = time.perf_counter() - started
            performance_rows.append({"case_id": case_id, "raw_span_count": raw_count, "valid_span_count": valid_count, "in_window_span_count": store.trace_count(), "sqlite_bytes": database.stat().st_size, "candidate_generation_seconds": generation_seconds, "total_seconds": total, "spans_per_second": store.trace_count() / total if total else None})
            status_rows.append({"case_id": case_id, "generation_status": "HYPOTHESES_GENERATED", "candidate_artifact_sha256": sha(candidate_path)})
            store.close()
        except Exception as exc:
            status_rows.append({"case_id": case_id, "generation_status": "TECHNICAL_UNAVAILABLE", "detail": f"{type(exc).__name__}: {exc}"})
    data_characterization = {"schema_version": "v3_phase2_12_data_characterization_v1", "label_access": "NO_GROUND_TRUTH_COLUMNS_READ", "case_count": len(characterizations), "cases": characterizations, "aggregate": {"eligible_service_count": {"mean": statistics.mean([row["eligible_service_count"] for row in characterizations]) if characterizations else None, "min": min((row["eligible_service_count"] for row in characterizations), default=None), "max": max((row["eligible_service_count"] for row in characterizations), default=None)}, "metric_kinds": dict(sorted(Counter(kind for row in characterizations for kind, count in row["metric"]["metric_kinds"].items() for _ in range(count)).items())), "units": sorted({unit for row in characterizations for unit in row["metric"]["units"]}), "topology_available_case_count": sum(row["topology"]["available"] for row in characterizations), "change_available_case_count": sum(row["changes"]["available"] for row in characterizations)}}
    write(OUT / "ACQUISITION.json", {"schema_version": "v3_phase2_12_acquisition_v1", "cases": acquisition_rows})
    write(OUT / "DATA_CHARACTERIZATION.json", data_characterization)
    write(OUT / "CASE_STATUS.json", {"schema_version": "v3_phase2_12_case_status_v1", "cases": status_rows})
    # Global, not merely per-case, phase boundary. This never opens a GT column.
    candidate_paths = sorted((OUT / "HOLDOUT_CANDIDATES").glob("*.json"))
    write(OUT / "PRE_EVALUATION_CANDIDATE_HASHES.json", {"schema_version": "v3_phase2_12_pre_evaluation_candidate_hashes_v1", "candidate_artifacts": {path.name: sha(path) for path in candidate_paths}, "generated_count": len(candidate_paths), "holdout_count": len(holdout_ids)})
    phase_a_freeze(holdout_ids, status_rows, manifest)
    # Phase B starts only after every expected case has an explicit Phase-A status.
    variant_rows: dict[str, list[dict[str, Any]]] = defaultdict(list); baseline: dict[str, list[dict[str, Any]]] = defaultdict(list); evaluations = []; fault_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for status in status_rows:
        case_id = status["case_id"]
        if status["generation_status"] not in {"HYPOTHESES_GENERATED", "CANDIDATE_ARTIFACT_FROZEN"}:
            continue
        candidate = json.loads((OUT / "HOLDOUT_CANDIDATES" / f"{case_id}.json").read_text(encoding="utf-8"))
        truth = truth_after_generation(case_id)
        result = {name: evaluate(case_id, truth, value, candidate["eligible_service_count"]) for name, value in candidate["variants"].items()}
        for name, row in result.items(): variant_rows[name].append(row)
        bases = baseline_rows(case_id, truth, candidate, candidate["eligible_service_count"])
        for name, row in bases.items(): baseline[name].append(row)
        evaluation_artifact = {"schema_version": "v3_phase2_12_holdout_evaluation_v1", "case_id": case_id, "candidate_artifact_sha256": sha(OUT / "HOLDOUT_CANDIDATES" / f"{case_id}.json"), "ground_truth_service_id": truth.root_cause_service, "fault_type": truth.fault_type, "variants": result, "baselines": bases}
        write(OUT / "HOLDOUT_EVALUATIONS" / f"{case_id}.json", evaluation_artifact)
        evaluations.append(evaluation_artifact); fault_rows[truth.fault_type or "UNKNOWN"].append(result["H5_COMBINED"])
    h5 = variant_rows["H5_COMBINED"]
    fault_results = {fault: summary(rows) for fault, rows in sorted(fault_rows.items())}
    h1 = {row["case_id"]: row for row in variant_rows["H1_METRIC"]}; h5_by = {row["case_id"]: row for row in h5}
    h1_h5 = {"schema_version": "v3_phase2_12_h1_vs_h5_v1", "both_cover": sorted(case for case in h1 if h1[case]["covered"] and h5_by[case]["covered"]), "only_h1": sorted(case for case in h1 if h1[case]["covered"] and not h5_by[case]["covered"]), "only_h5": sorted(case for case in h1 if h5_by[case]["covered"] and not h1[case]["covered"]), "neither": sorted(case for case in h1 if not h1[case]["covered"] and not h5_by[case]["covered"]), "mean_candidate_expansion_h5_minus_h1": statistics.mean([h5_by[case]["candidate_count"] - h1[case]["candidate_count"] for case in h1]) if h1 else None, "h5_gt_recoveries_beyond_h1": sorted(case for case in h1 if h5_by[case]["covered"] and not h1[case]["covered"])}
    trace_detail = {row["case_id"]: json.loads((OUT / "HOLDOUT_CANDIDATES" / f"{row['case_id']}.json").read_text(encoding="utf-8")) for row in h5}
    trace_incremental = {"schema_version": "v3_phase2_12_trace_incremental_value_v1", "h5_gt_recoveries_beyond_h1": h1_h5["h5_gt_recoveries_beyond_h1"], "case_count_trace_adds_gt": len(h1_h5["h5_gt_recoveries_beyond_h1"]), "mean_additional_candidates_h5_minus_h1": h1_h5["mean_candidate_expansion_h5_minus_h1"], "cases_trace_adds_only_non_gt_candidates": sorted(case for case in h1 if trace_detail[case]["variants"]["H5_COMBINED"]["candidate_count"] > trace_detail[case]["variants"]["H1_METRIC"]["candidate_count"] and h5_by[case]["covered"] == h1[case]["covered"]), "interpretation_boundary": "Additional candidates are not characterized as false causes or causal effects."}
    metric_aggregates = [aggregate for candidate in trace_detail.values() for aggregate in candidate["variants"]["H1_METRIC"]["aggregate_evidence"]]
    metric_rule = {"schema_version": "v3_phase2_12_metric_rule_analysis_v1", "triggered_service_count": len({item["service_external_id"] for item in metric_aggregates}), "triggered_series_count": len(metric_aggregates), "series_keys": dict(sorted(Counter(item["attributes"]["series_key"] for item in metric_aggregates).items())), "median_relative_median_shift": statistics.median([item["attributes"]["relative_median_shift"] for item in metric_aggregates]) if metric_aggregates else None, "median_persistent_post_fraction": statistics.median([item["attributes"]["persistent_post_fraction"] for item in metric_aggregates]) if metric_aggregates else None, "per_case_triggered_series": {case: len(candidate["variants"]["H1_METRIC"]["aggregate_evidence"]) for case, candidate in sorted(trace_detail.items())}, "interpretation_boundary": "Aggregate magnitude is descriptive evidence only; it is not a causal score or candidate rank."}
    topology_change = {"schema_version": "v3_phase2_12_topology_change_availability_v1", "topology_available_case_count": sum(row["topology"]["available"] for row in characterizations), "change_available_case_count": sum(row["changes"]["available"] for row in characterizations), "h3_candidate_count": sum(row["candidate_count"] for row in variant_rows["H3_BOUNDED_TOPOLOGY"]), "h4_candidate_count": sum(row["candidate_count"] for row in variant_rows["H4_TEMPORAL_CHANGE"]), "external_utility": "UNRESOLVED when the corresponding external modality is unavailable."}
    failures = []
    for evaluation_artifact in evaluations:
        row = evaluation_artifact["variants"]["H5_COMBINED"]
        if row["covered"] is not False:
            continue
        candidate = json.loads((OUT / "HOLDOUT_CANDIDATES" / f"{row['case_id']}.json").read_text(encoding="utf-8")); gt = row["ground_truth_service_id"]
        flags = {name: gt in result["candidate_subject_ids"] for name, result in evaluation_artifact["variants"].items()}
        failures.append({"case_id": row["case_id"], "ground_truth_service_id": gt, "gt_resolved": bool(gt), "gt_in_eligible_universe": gt in candidate["eligible_services"], "variant_gt_candidate": flags, "taxonomy": ["NO_METRIC_TRIGGER" if not flags["H1_METRIC"] else "CANDIDATE_GENERATED_GT_ABSENT"], "observational_note": "No causal conclusion is drawn from candidate absence."})
    inflation = {}
    for name, low, high in INFLATION_BUCKETS:
        rows = [row for row in h5 if row["candidate_count"] >= low and (high is None or row["candidate_count"] <= high)]
        associated = [item for item in evaluations if item["case_id"] in {row["case_id"] for row in rows}]
        inflation[name] = {"case_count": len(rows), "coverage": summary(rows)["candidate_stage_root_cause_coverage"], "fault_type_composition": dict(sorted(Counter(item["fault_type"] or "UNKNOWN" for item in associated).items())), "rule_family_composition": dict(sorted(Counter(rule for row in rows for rule in row["generation_rules"]).items()))}
    # Rerun three preregistered opaque IDs without opening labels and compare
    # deterministic candidate payloads, rather than variable runtime fields.
    deterministic = []
    for case_id in preregistration["determinism_case_ids"]:
        original = json.loads((OUT / "HOLDOUT_CANDIDATES" / f"{case_id}.json").read_text(encoding="utf-8"))
        database = INDEXES / f"determinism-{case_id}.sqlite"; database.unlink(missing_ok=True)
        adapted, store, _, _ = adapt_cached_case_to_store(cases[case_id], CACHE / case_id, database, resource_configuration=ResourceConfiguration(1000, 1000)); rerun = selection_payload(store, store.logical_view(), configuration); store.close()
        deterministic.append({"case_id": case_id, "original_selection_sha256": stable_sha(original["variants"]), "rerun_selection_sha256": stable_sha(rerun), "match": stable_sha(original["variants"]) == stable_sha(rerun)})
    ablations = {"schema_version": "v3_phase2_12_ablation_results_v1", "runs": {name: {"headline": summary(rows), "per_case": rows, "unique_gt_recoveries_relative_to_h0": sorted(row["case_id"] for row in rows if row["covered"] and not next(base for base in variant_rows["H0_FROZEN_PHASE210"] if base["case_id"] == row["case_id"])["covered"]), "unique_gt_misses_relative_to_h5": sorted(case_id for case_id, primary_row in h5_by.items() if primary_row["covered"] and not next(item for item in rows if item["case_id"] == case_id)["covered"])} for name, rows in sorted(variant_rows.items())}, "baselines": {name: {"headline": summary(rows), "per_case": rows} for name, rows in sorted(baseline.items())}}
    perf = {"schema_version": "v3_phase2_12_performance_v1", "cases": performance_rows, "headline": {"total_seconds": sum(row["total_seconds"] for row in performance_rows), "mean_seconds": statistics.mean([row["total_seconds"] for row in performance_rows]) if performance_rows else None, "median_seconds": statistics.median([row["total_seconds"] for row in performance_rows]) if performance_rows else None, "p90_seconds": percentile([row["total_seconds"] for row in performance_rows], .90), "mean_spans_per_second": statistics.mean([row["spans_per_second"] for row in performance_rows]) if performance_rows else None, "mean_sqlite_bytes": statistics.mean([row["sqlite_bytes"] for row in performance_rows]) if performance_rows else None, "max_sqlite_bytes": max((row["sqlite_bytes"] for row in performance_rows), default=None), "boundedness": "SQLite indexed trace aggregation; no full trace execution graph materialized."}}
    primary = summary(h5)
    complete = len(h5) == len(holdout_ids)
    if not complete:
        decision = "HOLDOUT_VALIDATION_TECHNICALLY_INCOMPLETE"
    elif primary["candidate_stage_root_cause_coverage"] < .75:
        decision = "PILOT_GENERALIZATION_NOT_SUPPORTED"
    elif primary["candidate_reduction_relative_to_all_services"]["mean"] < .25:
        decision = "HOLDOUT_RECALL_SUPPORTED_REDUCTION_INSUFFICIENT"
    elif not h1_h5["h5_gt_recoveries_beyond_h1"] and h1_h5["mean_candidate_expansion_h5_minus_h1"] > 0:
        decision = "METRIC_HYPOTHESIS_GENERALIZES_TRACE_INCREMENTAL_VALUE_NOT_SUPPORTED"
    else:
        decision = "EVIDENCE_AWARE_HYPOTHESIS_GENERATION_SUPPORTED_BY_HOLDOUT"
    results = {"schema_version": "v3_phase2_12_holdout_results_v1", "primary_system": "H5_COMBINED", "headline": primary, "results": h5, "candidate_count_distribution": dict(sorted(Counter(row["candidate_count"] for row in h5).items())), "holdout_completion": {"total_frozen_holdout_cases": len(holdout_ids), "evaluated": len(h5), "technical_unavailable": sum(row["generation_status"] == "TECHNICAL_UNAVAILABLE" for row in status_rows), "other_non_evaluated": len(holdout_ids) - len(h5)}, "candidate_inflation": inflation}
    gate = {"schema_version": "v3_phase2_12_research_gate_v1", "decision": decision, "primary_endpoint": "H5_COMBINED", "holdout_consumed_once": True, "no_phase211_tuning": "SUPPORTED", "holdout_generation_before_gt": "SUPPORTED", "next_step": "Preserve this holdout result. Do not tune Phase 2.11 on these cases."}
    write(OUT / "CASE_STATUS.json", {"schema_version": "v3_phase2_12_case_status_v1", "cases": status_rows})
    write(OUT / "HOLDOUT_RESULTS.json", results); write(OUT / "ABLATION_RESULTS.json", ablations); write(OUT / "FAULT_GROUP_RESULTS.json", {"schema_version": "v3_phase2_12_fault_group_results_v1", "groups": fault_results}); write(OUT / "H1_VS_H5_ANALYSIS.json", h1_h5); write(OUT / "TRACE_INCREMENTAL_VALUE.json", trace_incremental); write(OUT / "METRIC_RULE_ANALYSIS.json", metric_rule); write(OUT / "TOPOLOGY_CHANGE_AVAILABILITY.json", topology_change); write(OUT / "FAILURE_CASES.json", {"schema_version": "v3_phase2_12_failure_cases_v1", "cases": failures}); write(OUT / "PERFORMANCE.json", perf); write(OUT / "DETERMINISM_CHECK.json", {"schema_version": "v3_phase2_12_determinism_check_v1", "cases": deterministic, "all_match": all(row["match"] for row in deterministic)}); write(OUT / "RESEARCH_GATE.json", gate)
    paths = sorted(path for path in OUT.rglob("*.json") if path.name not in {"HASHES.json", "MANIFEST.json"})
    write(OUT / "HASHES.json", {"schema_version": "v3_phase2_12_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in paths}})
    paths = sorted(path for path in OUT.rglob("*.json") if path.name != "MANIFEST.json")
    write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_12_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in paths}})
    report = "# V3 Phase 2.12 Protected Holdout Validation\n\nThis is a one-shot validation of frozen, unranked Phase 2.11 candidate generation. It does not rank candidates or establish causality. Every holdout candidate artifact was frozen before its GT evaluation artifact was written.\n\n```json\n" + json.dumps({"integrity": integrity, "primary_h5": primary, "ablations": {name: value["headline"] for name, value in ablations["runs"].items()}, "h1_vs_h5": h1_h5, "trace_incremental_value": trace_incremental, "fault_groups": fault_results, "performance": perf["headline"], "research_gate": gate}, indent=2, sort_keys=True) + "\n```\n\nThe holdout is consumed and must not be used to tune Phase 2.11. Non-GT candidates are candidate expansion, not causal false positives.\n"
    (ROOT / "experiments/V3_PHASE2_12_REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
