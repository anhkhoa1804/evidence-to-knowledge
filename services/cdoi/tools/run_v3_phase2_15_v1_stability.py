"""Run the preregistered Phase 2.15 V1 stability repeats.

This script is isolated from the immutable V1 primary batch.  It reuses the
exact V1 prompt, model adapter, candidate policy, budgets, and report contract.
It never reads Phase 2.12 or any protected-holdout artifact.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder
from cdoi.hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAAgentModel, QwenRCAConfig
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, PreparedRCAInvestigation, RCAAgentV0, RCAOrchestrator
from cdoi.rcaeval_evaluation import RCAEvalCase, adapt_cached_case_to_store

OUT = ROOT / "experiments/archive/v3_phase2_15_finalization_20260924"
CACHE = ROOT / "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"
SELECTED = (
    ("re2ob_checkoutservice_cpu_1", "ORDINARY_ONE_CANDIDATE_ABSTENTION"),
    ("re2ob_currencyservice_loss_1", "LARGE_NINE_CANDIDATE_ABSTENTION"),
    ("re2ob_checkoutservice_mem_1", "PRIOR_TRANSPORT_FAILURE"),
)
REPEATS = 3


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    run_root = OUT / "STABILITY_RUNS"
    if run_root.exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_V1_STABILITY_RUNS")
    load_dotenv_file(ROOT / ".env", override=False)
    config = QwenRCAConfig.from_internal_gateway_environment()
    if config.status() != "QWEN_LIVE_READY":
        raise RuntimeError("QWEN_LIVE_RUNTIME_NOT_READY")
    import pyarrow.parquet as parquet

    selected_ids = {case_id for case_id, _ in SELECTED}
    rows = {str(row["case"]): row for row in parquet.read_table(
        INDEX,
        columns=["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"],
        filters=[("case", "in", sorted(selected_ids))],
    ).to_pylist()}
    write(OUT / "V1_STABILITY_PREREGISTRATION.json", {
        "schema_version": "v3_phase2_15_v1_stability_preregistration_v1",
        "selected_before_repeat_results": True,
        "cases": [{"case_id": case_id, "selection_reason": reason} for case_id, reason in SELECTED],
        "repeats_per_case": REPEATS,
        "configuration": {"prompt_version": "rca_agent_qwen_v1", "candidate_source": "H1_THEN_H5_FALLBACK", "max_tool_calls": 12, "max_candidate_profiles": 6, "temperature": 0, "max_tokens": "PROVIDER_DEFAULT_NOT_SENT"},
        "phase212_holdout": "NOT_READ",
    })
    results = []
    orchestrator = RCAOrchestrator()
    for case_id, selection_reason in SELECTED:
        row = rows[case_id]
        case = RCAEvalCase(case_id, str(row["dataset"]), str(row["system"]), int(row["inject_time"]), int(row["time_start"]) if row["time_start"] is not None else None, int(row["time_end"]) if row["time_end"] is not None else None, bool(row["has_logs"]), bool(row["has_traces"]))
        adapted, store, _, _ = adapt_cached_case_to_store(case, CACHE / case_id, OUT / "STABILITY_STORES" / f"{case_id}.sqlite")
        view = store.logical_view(); hypothesis_config = HypothesisConfiguration()
        h1 = generate_evidence_aware_hypotheses(store, view, configuration=hypothesis_config, include_metric=True, include_trace=False, include_topology=False, include_temporal_change=False)
        h5 = generate_evidence_aware_hypotheses(store, view, configuration=hypothesis_config, include_metric=True, include_trace=True, include_topology=True, include_temporal_change=True)
        union = tuple(sorted({item.candidate_id: item for item in (*h1.candidates, *h5.candidates)}.values(), key=lambda item: item.candidate_id))
        profiles = CandidateEvidenceProfileBuilder(store.context, store, (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(union)
        prepared = PreparedRCAInvestigation(store.context, store, h1.candidates, h5.candidates, profiles)
        for repeat in range(1, REPEATS + 1):
            model = QwenRCAAgentModel(config)
            agent = RCAAgentV0(model, max_tool_calls=12, max_candidate_profiles=6)
            output = run_root / case_id / f"repeat_{repeat}"
            report = orchestrator.run(prepared, output, InvestigationMode.AGENT, CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, model.public_metadata())
            trace = json.loads((output / "AGENT_TRACE.json").read_text(encoding="utf-8"))
            record = model.records[-1] if model.records else {}
            results.append({
                "case_id": case_id, "selection_reason": selection_reason, "repeat": repeat,
                "status": report.status, "primary_candidate_id": report.primary_hypothesis.candidate_id if report.primary_hypothesis else None,
                "tool_calls": report.tool_calls, "fallback_used": bool(trace.get("fallback", {}).get("fallback_used")),
                "provider_call_records": len(model.records), "latency_ms": record.get("latency_ms"),
                "input_tokens": record.get("input_tokens"), "output_tokens": record.get("output_tokens"),
                "retry_count": record.get("retry_count"), "technical_error": trace.get("error_code"),
                "resolved_model": model.last_response_metadata.get("resolved_model"),
            })
        store.close()
    by_case = {}
    for case_id, _ in SELECTED:
        case_rows = [row for row in results if row["case_id"] == case_id]
        latencies = [row["latency_ms"] for row in case_rows if isinstance(row["latency_ms"], (int, float))]
        by_case[case_id] = {
            "statuses": [row["status"] for row in case_rows],
            "status_agreement": len({row["status"] for row in case_rows}) == 1,
            "tool_call_agreement": len({row["tool_calls"] for row in case_rows}) == 1,
            "primary_hypothesis_agreement": len({row["primary_candidate_id"] for row in case_rows}) == 1,
            "fallback_agreement": len({row["fallback_used"] for row in case_rows}) == 1,
            "latency_ms": {"values": latencies, "mean": statistics.mean(latencies) if latencies else None},
        }
    write(OUT / "V1_STABILITY.json", {
        "schema_version": "v3_phase2_15_v1_stability_v1", "attempted_runs": len(results),
        "completed_runs": len(results), "results": results, "by_case": by_case,
        "zero_tool_behavior_reproducible": all(row["tool_calls"] == 0 for row in results),
        "all_runs_abstained": all(row["status"] == "INSUFFICIENT_EVIDENCE" for row in results),
        "phase212_holdout": "NOT_READ",
    })
    write(OUT / "V1_STABILITY_RUN_HASHES.json", {
        "schema_version": "v3_phase2_15_v1_stability_run_hashes_v1",
        "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(run_root.rglob("*")) if path.is_file()},
    })


if __name__ == "__main__":
    main()
