"""Resume the frozen RCAEval pilot without changing R2 candidate semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import shutil
import socket
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
R2_HELPERS = runpy.run_path(str(ROOT / "tools/run_v3_phase2_10e_r2.py"))

from cdoi.incident_evidence_graph import build_incident_evidence_graph, generate_cause_candidates
from cdoi.operational_context import assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import process_dataset
from cdoi.rcaeval_evaluation import adapt_cached_case_to_store, deterministic_pilot, load_case_index
from cdoi.scalable_evidence import IncidentEvidenceStore, ResourceConfiguration, generate_frozen_candidates_from_store

REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
CACHE = ROOT / "data/benchmarks/external/rcaeval" / REVISION
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"
R2 = ROOT / "experiments/archive/v3_phase2_10e_r2"
OUT = ROOT / "experiments/archive/v3_phase2_10e_r2a"
INDEXES = ROOT / "data/benchmarks/external/rcaeval/r2a_indexes"
PHASE210 = ROOT / "experiments/archive/v3_phase2_10"
PHASE210E = ROOT / "experiments/archive/v3_phase2_10e_rcaeval"
FILES = ("metrics.parquet", "logs.parquet", "traces.parquet")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha(path: Path) -> str:
    rows = [f"{item.relative_to(ROOT).as_posix()}\x1f{sha(item)}" for item in sorted(path.rglob("*")) if item.is_file() and "__pycache__" not in item.parts]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def write(name: str, value: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def parquet_valid(path: Path) -> bool:
    """Validate cached artifacts before treating them as reusable benchmark data."""
    if not path.is_file() or not path.stat().st_size:
        return False
    try:
        import pyarrow.parquet as parquet
        parquet.ParquetFile(path).metadata
        return True
    except Exception:
        return False


def status_for_exception(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 404:
            return "ARTIFACT_NOT_FOUND"
        if 500 <= exc.code < 600:
            return "UPSTREAM_UNAVAILABLE"
    text = str(exc).casefold()
    if isinstance(exc, (TimeoutError, socket.timeout)) or "timed out" in text or "10060" in text:
        return "DOWNLOAD_FAILED_TIMEOUT"
    if isinstance(exc, urllib.error.URLError) or "connection" in text:
        return "DOWNLOAD_FAILED_CONNECTION"
    return "UPSTREAM_UNAVAILABLE"


def fetch_file(case_id: str, name: str, *, attempts: int, timeout: int, sleeper=time.sleep) -> dict[str, Any]:
    """Retry a pinned upstream artifact and atomically promote only valid Parquet."""
    directory = CACHE / case_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    url = f"https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{REVISION}/{case_id}/{name}?download=true"
    if parquet_valid(target):
        return {"artifact": name, "status": "CACHED", "url": url, "path": portable_path(target), "bytes": target.stat().st_size, "sha256": sha(target), "timestamp": now(), "method": "validated_local_cache"}
    part = target.with_suffix(target.suffix + ".part")
    if target.exists():
        target.replace(part)
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        start = part.stat().st_size if part.exists() else 0
        request = urllib.request.Request(url, headers={"Range": f"bytes={start}-"} if start else {})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                resumed = bool(start and getattr(response, "status", response.getcode()) == 206)
                mode = "ab" if resumed else "wb"
                if not resumed:
                    start = 0
                with part.open(mode) as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                part.replace(target)
                if not parquet_valid(target):
                    target.replace(part)
                    return {"artifact": name, "status": "DATA_INVALID", "url": url, "path": portable_path(part), "detail": "DOWNLOADED_FILE_IS_NOT_VALID_PARQUET", "timestamp": now(), "method": "range_resume" if resumed else "full_download"}
                return {"artifact": name, "status": "DOWNLOADED", "url": url, "path": portable_path(target), "bytes": target.stat().st_size, "sha256": sha(target), "remote_etag": response.headers.get("ETag"), "timestamp": now(), "method": "range_resume" if resumed else "full_download"}
        except Exception as exc:
            last = exc
            if attempt < attempts:
                sleeper(2 ** (attempt - 1))
    assert last is not None
    return {"artifact": name, "status": status_for_exception(last), "url": url, "path": portable_path(part if part.exists() else target), "detail": f"{type(last).__name__}: {last}", "attempts": attempts, "timestamp": now(), "method": "range_resume" if part.exists() else "full_download"}


def acquire_case(case_id: str, *, attempts: int, timeout: int) -> dict[str, Any]:
    artifacts = [fetch_file(case_id, name, attempts=attempts, timeout=timeout) for name in FILES]
    statuses = {item["status"] for item in artifacts}
    case_status = "CACHED" if statuses <= {"CACHED", "DOWNLOADED"} else next(item["status"] for item in artifacts if item["status"] not in {"CACHED", "DOWNLOADED"})
    return {"case_id": case_id, "acquisition_status": case_status, "artifacts": artifacts}


def verify_r2_manifest() -> None:
    manifest = json.loads((R2 / "MANIFEST.json").read_text(encoding="utf-8"))
    mismatches = [name for name, digest in manifest["artifacts"].items() if sha(R2 / name) != digest]
    if mismatches:
        raise RuntimeError(f"FROZEN_BASELINE_REGRESSION: R2_MANIFEST_MISMATCH {mismatches}")


def verify_equivalence() -> None:
    fixture = ROOT / "tests/fixtures/preprocessing_demo"
    processed = process_dataset(fixture / "manifest.yaml")
    incident = load_incident_windows(fixture / "incidents/incidents.csv", "incidents/incidents.csv")[0]
    context = assemble_context(processed, incident); snapshot = snapshot_for(context)
    legacy = generate_cause_candidates(build_incident_evidence_graph(snapshot))
    database = INDEXES / "equivalence.sqlite"; database.parent.mkdir(parents=True, exist_ok=True); database.unlink(missing_ok=True)
    store = IncidentEvidenceStore.from_context(database, context, exact_legacy_graph_id=True, snapshot=snapshot)
    equivalent = [item.artifact() for item in legacy] == [item.artifact() for item in generate_frozen_candidates_from_store(store, store.logical_view(snapshot.snapshot_id))]
    store.close()
    if not equivalent:
        raise RuntimeError("FROZEN_BASELINE_REGRESSION: SCALABLE_EQUIVALENCE")


def baseline(cases: tuple[Any, ...], truth: tuple[Any, ...]) -> dict[str, Any]:
    split = json.loads((PHASE210E / "CASE_SPLIT.json").read_text(encoding="utf-8"))
    pilot = deterministic_pilot(cases, truth)
    previous = json.loads((R2 / "CASE_STATUS.json").read_text(encoding="utf-8"))
    missing = [row["case_id"] for row in previous["cases"] if row["acquisition_status"] != "CACHED"]
    return {"schema_version": "v3_phase2_10e_r2a_baseline_v1", "source_tree_sha256": tree_sha(ROOT / "src/cdoi"), "test_tree_sha256": tree_sha(ROOT / "tests"), "phase210": {"incident_evidence_graph_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"), "cause_candidates_sha256": sha(PHASE210 / "CAUSE_CANDIDATES.json"), "demo_sha256": sha(PHASE210 / "DEMO_RESULT.json")}, "phase210e_protocol_sha256": sha(PHASE210E / "EVALUATION_PROTOCOL.json"), "r1_scalable_implementation_sha256": sha(ROOT / "src/cdoi/scalable_evidence.py"), "r2_pilot_split_sha256": hashlib.sha256(json.dumps(list(pilot), separators=(",", ":")).encode()).hexdigest(), "r2_holdout_split_sha256": hashlib.sha256(json.dumps(split["held_out_re2ob_case_ids"], separators=(",", ":")).encode()).hexdigest(), "r2_existing_five_result_sha256": sha(R2 / "PILOT_RESULTS.json"), "dataset_revision": REVISION, "case_index_sha256": sha(INDEX), "missing_case_ids": missing, "current_test_count": R2_HELPERS["test_count"]()}


def evaluate_new(case: Any, truth: Any) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], dict[str, Any], list[dict[str, Any]]]:
    """Generate and freeze candidates before this function compares them to GT."""
    database = INDEXES / f"{case.case_id}.sqlite"; database.unlink(missing_ok=True)
    started = time.perf_counter()
    adapted, store, raw_count, valid_count = adapt_cached_case_to_store(case, CACHE / case.case_id, database, resource_configuration=ResourceConfiguration(1000, 1000))
    view = store.logical_view(); candidate_started = time.perf_counter()
    full = generate_frozen_candidates_from_store(store, view)
    selected_baselines = R2_HELPERS["baseline_sets"](store)
    ablated = {"A0_AVAILABLE_FULL_EVIDENCE": full, "A1_METRICS_REMOVED": generate_frozen_candidates_from_store(store, view, include_metrics=False), "A2_LOGS_EVENTS_REMOVED": generate_frozen_candidates_from_store(store, view, include_events=False), "A3_TRACES_REMOVED": generate_frozen_candidates_from_store(store, view, include_traces=False)}
    # No truth object is passed to any adapter/store/generator above this line.
    result = R2_HELPERS["evaluate"](case.case_id, truth, full, len(store.context.entities), view.graph_id)
    result["candidates"] = R2_HELPERS["candidate_rows"](full)
    baselines = {name: [R2_HELPERS["evaluate_baseline"](case.case_id, truth, name, subjects, len(store.context.entities))] for name, subjects in selected_baselines.items()}
    ablations = {name: [R2_HELPERS["evaluate"](case.case_id, truth, candidates, len(store.context.entities), view.graph_id)] for name, candidates in ablated.items()}
    inventory = R2_HELPERS["zero_inventory"](store, adapted, truth.root_cause_service) if result["candidate_count"] == 0 and truth.root_cause_service else None
    failures = []
    taxonomy = R2_HELPERS["miss_taxonomy"](result, inventory)
    if taxonomy:
        failures.append({"case_id": case.case_id, "status": result["status"], "taxonomy": taxonomy, "zero_candidate_evidence_inventory": inventory})
    candidate_seconds = time.perf_counter() - candidate_started; total = time.perf_counter() - started; count = store.trace_count()
    resource = {"case_id": case.case_id, "raw_trace_count": raw_count, "valid_trace_count": valid_count, "in_window_trace_count": count, "processed_trace_count": count, "sqlite_bytes": database.stat().st_size, "index_and_candidate_seconds": total, "candidate_generation_seconds": candidate_seconds, "spans_per_second": count / total if total else None}
    store.close()
    return result, baselines, ablations, resource, failures


def persist(case_status: list[dict[str, Any]], results: list[dict[str, Any]], baselines: dict[str, list[dict[str, Any]]], ablations: dict[str, list[dict[str, Any]]], failures: list[dict[str, Any]], resources: list[dict[str, Any]], truth_by_id: dict[str, Any], *, complete: bool) -> None:
    summarize = R2_HELPERS["summarize"]
    by_fault: dict[str, list[dict[str, Any]]] = defaultdict(list); by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        truth = truth_by_id[row["case_id"]]; by_fault[truth.fault_type or "UNKNOWN"].append(row); by_service[truth.root_cause_service or "UNRESOLVED"].append(row)
    pilot = {"schema_version": "v3_phase2_10e_r2a_pilot_results_v1", "headline": summarize(results), "results": results, "fault_type_breakdown": {name: summarize(rows) for name, rows in sorted(by_fault.items())}, "root_cause_service_breakdown": {name: summarize(rows) for name, rows in sorted(by_service.items())}}
    base = {"schema_version": "v3_phase2_10e_r2a_baselines_v1", "baselines": {name: {"headline": summarize(rows), "per_case": rows} for name, rows in sorted(baselines.items())}}
    ablation = {"schema_version": "v3_phase2_10e_r2a_ablations_v1", "runs": {name: {"headline": summarize(rows), "per_case": rows} for name, rows in sorted(ablations.items())}}
    gate = {"schema_version": "v3_phase2_10e_r2a_research_gate_v1", "frozen_semantics": "SUPPORTED", "split_and_holdout": "SUPPORTED", "anti_leakage": "SUPPORTED", "acquisition_complete": "SUPPORTED" if complete else "TECHNICAL_BLOCKER", "pilot_evaluated": "SUPPORTED" if complete else "PARTIALLY_SUPPORTED", "phase211": "PROCEED_TO_V3_PHASE2_11" if complete else "V3_PHASE2_10E_R2_FOLLOW_UP_REQUIRED"}
    write("CASE_STATUS.json", {"schema_version": "v3_phase2_10e_r2a_case_status_v1", "cases": case_status}); write("PILOT_RESULTS.json", pilot); write("BASELINE_RESULTS.json", base); write("ABLATION_RESULTS.json", ablation); write("FAILURE_CASES.json", {"schema_version": "v3_phase2_10e_r2a_failure_cases_v1", "cases": failures}); write("RESOURCE_DIAGNOSTICS.json", {"schema_version": "v3_phase2_10e_r2a_resource_diagnostics_v1", "cases": resources}); write("RESEARCH_GATE.json", gate)


def docs() -> None:
    files = {"V3_PHASE2_10E_R2A_BASELINE.md": ("Baseline", "BASELINE.json"), "V3_PHASE2_10E_R2A_ACQUISITION.md": ("Acquisition", "ACQUISITION_MANIFEST.json"), "V3_PHASE2_10E_R2A_PILOT_RESULTS.md": ("Pilot Results", "PILOT_RESULTS.json"), "V3_PHASE2_10E_R2A_BASELINES.md": ("Baselines", "BASELINE_RESULTS.json"), "V3_PHASE2_10E_R2A_ABLATIONS.md": ("Ablations", "ABLATION_RESULTS.json"), "V3_PHASE2_10E_R2A_FAILURE_CHARACTERIZATION.md": ("Failure Characterization", "FAILURE_CASES.json"), "V3_PHASE2_10E_R2A_RESEARCH_GATE.md": ("Research Gate", "RESEARCH_GATE.json")}
    for filename, (title, artifact) in files.items():
        value = json.loads((OUT / artifact).read_text(encoding="utf-8"))
        (ROOT / "experiments" / filename).write_text(f"# V3 Phase 2.10E-R2A {title}\n\n```json\n{json.dumps(value, indent=2, sort_keys=True)}\n```\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--baseline-only", action="store_true"); parser.add_argument("--attempts", type=int, default=3); parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()
    cases, truths = load_case_index(INDEX); truth_by_id = {item.case_id: item for item in truths}; case_by_id = {item.case_id: item for item in cases}
    verify_r2_manifest(); verify_equivalence()
    frozen = baseline(cases, truths); write("BASELINE.json", frozen)
    if args.baseline_only:
        write("MANIFEST.json", {"schema_version": "v3_phase2_10e_r2a_manifest_v1", "artifacts": {"BASELINE.json": sha(OUT / "BASELINE.json")}}); (ROOT / "experiments/V3_PHASE2_10E_R2A_BASELINE.md").write_text("# V3 Phase 2.10E-R2A Baseline\n\n```json\n" + json.dumps(frozen, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8"); return
    r2_status = json.loads((R2 / "CASE_STATUS.json").read_text(encoding="utf-8")); r2_results = json.loads((R2 / "PILOT_RESULTS.json").read_text(encoding="utf-8"))["results"]
    r2_base = json.loads((R2 / "BASELINE_RESULTS.json").read_text(encoding="utf-8"))["baselines"]; r2_ablation = json.loads((R2 / "ABLATION_RESULTS.json").read_text(encoding="utf-8"))["runs"]; r2_failures = json.loads((R2 / "FAILURE_CASES.json").read_text(encoding="utf-8"))["cases"]; r2_resources = json.loads((R2 / "RESOURCE_DIAGNOSTICS.json").read_text(encoding="utf-8"))["cases"]
    existing = {row["case_id"]: row for row in r2_results}; results = list(r2_results); baselines = {name: list(value["per_case"]) for name, value in r2_base.items()}; ablations = {name: list(value["per_case"]) for name, value in r2_ablation.items()}; failures = list(r2_failures); resources = list(r2_resources)
    # Resume previously completed R2A cases rather than regenerating their
    # frozen candidate outputs when only another case needs acquisition.
    prior_r2a: dict[str, dict[str, Any]] = {}
    if (OUT / "PILOT_RESULTS.json").is_file() and (OUT / "CASE_STATUS.json").is_file():
        prior_payload = json.loads((OUT / "PILOT_RESULTS.json").read_text(encoding="utf-8"))
        prior_r2a = {row["case_id"]: row for row in prior_payload["results"] if row["case_id"] not in existing}
        results.extend(prior_r2a.values())
        prior_base = json.loads((OUT / "BASELINE_RESULTS.json").read_text(encoding="utf-8"))["baselines"]
        prior_ablation = json.loads((OUT / "ABLATION_RESULTS.json").read_text(encoding="utf-8"))["runs"]
        for name, value in prior_base.items():
            baselines.setdefault(name, []).extend(row for row in value["per_case"] if row["case_id"] in prior_r2a)
        for name, value in prior_ablation.items():
            ablations.setdefault(name, []).extend(row for row in value["per_case"] if row["case_id"] in prior_r2a)
        failures.extend(row for row in json.loads((OUT / "FAILURE_CASES.json").read_text(encoding="utf-8"))["cases"] if row["case_id"] in prior_r2a)
        resources.extend(row for row in json.loads((OUT / "RESOURCE_DIAGNOSTICS.json").read_text(encoding="utf-8"))["cases"] if row["case_id"] in prior_r2a)
    case_status = []
    for old in r2_status["cases"]:
        case_id = old["case_id"]
        record = {"case_id": case_id, "fault_type": truth_by_id[case_id].fault_type, "last_r2_acquisition_status": old["acquisition_status"], "last_failure_reason": old.get("detail")}
        if case_id in existing:
            record.update({"acquisition_status": "CACHED", "evaluation_status": existing[case_id]["status"], "preserved_r2_result": True})
        else:
            record.update(acquire_case(case_id, attempts=args.attempts, timeout=args.timeout))
            if record["acquisition_status"] == "CACHED":
                if case_id in prior_r2a:
                    record.update({"evaluation_status": prior_r2a[case_id]["status"], "preserved_r2a_result": True})
                else:
                    try:
                        result, new_base, new_ablation, resource, new_failures = evaluate_new(case_by_id[case_id], truth_by_id[case_id])
                        results.append(result); resources.append(resource); failures.extend(new_failures); record["evaluation_status"] = result["status"]
                        for name, rows in new_base.items(): baselines.setdefault(name, []).extend(rows)
                        for name, rows in new_ablation.items(): ablations.setdefault(name, []).extend(rows)
                        # Persist every completed case before continuing acquisition.
                        persist(case_status + [record], results, baselines, ablations, failures, resources, truth_by_id, complete=False)
                    except Exception as exc:
                        record["evaluation_status"] = "TECHNICAL_UNAVAILABLE"; record["detail"] = f"{type(exc).__name__}: {exc}"
            else:
                record["evaluation_status"] = "UPSTREAM_UNAVAILABLE"
        case_status.append(record)
    write("ACQUISITION_MANIFEST.json", {"schema_version": "v3_phase2_10e_r2a_acquisition_manifest_v1", "dataset_revision": REVISION, "cases": case_status})
    complete = len(results) == 12
    persist(case_status, results, baselines, ablations, failures, resources, truth_by_id, complete=complete)
    names = sorted(path.name for path in OUT.glob("*.json") if path.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "v3_phase2_10e_r2a_manifest_v1", "artifacts": {name: sha(OUT / name) for name in names}}); docs()


if __name__ == "__main__":
    main()
