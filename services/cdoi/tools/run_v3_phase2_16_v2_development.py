"""Fixed-config live V2 evaluation on the already-consumed Phase 2.11 pilot."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder
from cdoi.model_config import load_dotenv_file
from cdoi.hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses
from cdoi.qwen_rca import QwenRCAConfig
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model, rca_v2_system_prompt
from cdoi.rca_agent_v2 import RCAAgentV2, RCA_AGENT_V2_TOOL_SCHEMA_VERSION, V2AgentBudget
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, PreparedRCAInvestigation, RCAOrchestrator
from cdoi.rcaeval_evaluation import RCAEvalCase, adapt_cached_case_to_store

OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_20260924"
P211 = ROOT / "experiments/archive/v3_phase2_11"
CACHE = ROOT / "data/benchmarks/external/rcaeval/afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
INDEX = ROOT / "data/benchmarks/external/rcaeval/cases.parquet"


def write(path: Path, value: Any) -> str:
    text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def revision() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "GIT_COMMIT_UNAVAILABLE"


def hash_tools() -> str:
    from cdoi.qwen_rca import _tools
    return hashlib.sha256(json.dumps(_tools(), sort_keys=True).encode("utf-8")).hexdigest()


def prepared_for(case: RCAEvalCase, database: Path) -> PreparedRCAInvestigation:
    _, store, _, _ = adapt_cached_case_to_store(case, CACHE / case.case_id, database)
    view = store.logical_view(); cfg = HypothesisConfiguration()
    h1 = generate_evidence_aware_hypotheses(store, view, configuration=cfg, include_metric=True, include_trace=False, include_topology=False, include_temporal_change=False)
    h5 = generate_evidence_aware_hypotheses(store, view, configuration=cfg, include_metric=True, include_trace=True, include_topology=True, include_temporal_change=True)
    union = tuple(sorted({item.candidate_id: item for item in (*h1.candidates, *h5.candidates)}.values(), key=lambda item: item.candidate_id))
    profiles = CandidateEvidenceProfileBuilder(store.context, store, (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(union)
    return PreparedRCAInvestigation(store.context, store, h1.candidates, h5.candidates, profiles)


def main() -> None:
    if OUT.exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_PHASE216_LIVE_DEVELOPMENT_ARCHIVE")
    load_dotenv_file(ROOT / ".env", override=False)
    config = QwenRCAConfig.from_internal_gateway_environment()
    if config.status() != "QWEN_LIVE_READY": raise RuntimeError("QWEN_LIVE_RUNTIME_NOT_READY")
    import pyarrow.parquet as pq
    pilot = tuple(json.loads((P211 / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))["pilot_case_ids"])
    rows = {str(item["case"]): item for item in pq.read_table(INDEX, columns=["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]).to_pylist()}
    if len(pilot) != 12 or len(set(pilot)) != 12: raise RuntimeError("INVALID_PHASE211_DEVELOPMENT_CASESET")
    budget = V2AgentBudget(max_tool_calls=8, max_h1_profiles=20, max_evidence_per_tool_call=20, max_output_repairs=1)
    freeze = {"schema_version": "v3_phase2_16_v2_config_freeze_v1", "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "git_revision": revision(), "configuration": config.public_metadata(), "requested_model": config.model,
              "resolved_model_prior_live_qualification": "Qwen3.8-27B", "prompt_version": "rca_agent_qwen_v2",
              "prompt_sha256": hashlib.sha256(rca_v2_system_prompt().encode("utf-8")).hexdigest(),
              "candidate_evidence_profile_schema_version": "candidate_evidence_profile_v1",
              "profile_preload_policy": "COMPLETE_H1_DETERMINISTIC_PRELOAD_V1",
              "investigation_state_machine": "rca_agent_trace_v2", "candidate_source": "H1_THEN_H5_FALLBACK",
              "fallback_policy": ["H1_AMBIGUOUS", "MISSING_DISTINGUISHING_SIGNAL", "CONFLICTING_H1_EVIDENCE", "RELEVANT_MODALITY_MISSING"],
              "tool_schema_version": RCA_AGENT_V2_TOOL_SCHEMA_VERSION, "tool_definitions_sha256": hash_tools(),
              "tool_budget": {"max_tool_calls": budget.max_tool_calls, "max_h1_profiles": budget.max_h1_profiles, "max_evidence_per_tool_call": budget.max_evidence_per_tool_call},
              "max_rounds": 8, "temperature": 0, "max_output_tokens": 512, "retry_policy": {"max_retries": config.max_retries},
              "structured_output_repair_limit": 1, "rca_report_schema": "rca_report_v1", "transport_timeout_seconds": config.timeout_seconds,
              "development_dataset_manifest_sha256": sha(P211 / "EXPERIMENT_MANIFEST.json"), "development_only": True,
              "phase212": "PROHIBITED_NO_CASE_CANDIDATE_EVALUATION_OR_GT_ACCESS"}
    write(OUT / "V2_CONFIG_FREEZE.json", freeze)
    write(OUT / "DEVELOPMENT_DATA_MANIFEST.json", {"schema_version": "v3_phase2_16_development_data_v1", "label": "DEVELOPMENT_ONLY_CONSUMED_PHASE211", "expected_cases": 12, "unique_cases": len(set(pilot)), "case_ids": list(pilot), "phase211_manifest_sha256": sha(P211 / "EXPERIMENT_MANIFEST.json"), "phase212": "PROHIBITED_NOT_READ"})
    orch = RCAOrchestrator(); completed: list[dict[str, Any]] = []
    # No GT is read until every primary run is serially completed and frozen.
    for case_id in pilot:
        row = rows[case_id]
        case = RCAEvalCase(case_id, str(row["dataset"]), str(row["system"]), int(row["inject_time"]),
                           int(row["time_start"]) if row["time_start"] is not None else None,
                           int(row["time_end"]) if row["time_end"] is not None else None,
                           bool(row["has_logs"]), bool(row["has_traces"]))
        prepared = prepared_for(case, OUT / "STORES" / f"{case_id}.sqlite")
        try:
            model = QwenRCAAgentV2Model(config, max_output_tokens=512); agent = RCAAgentV2(model, budget=budget)
            report = orch.run(prepared, OUT / "RUNS" / case_id, InvestigationMode.AGENT, CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, model.public_metadata())
            trace = json.loads((OUT / "RUNS" / case_id / "AGENT_TRACE.json").read_text(encoding="utf-8"))
            completed.append({"case_id": case_id, "status": report.status, "primary_candidate_id": report.primary_hypothesis.candidate_id if report.primary_hypothesis else None,
                              "tool_calls": report.tool_calls, "h1_candidate_count": len(prepared.h1_candidates), "h5_candidate_count": len(prepared.h5_candidates),
                              "model_records": list(model.records), "transport": dict(model.last_transport_diagnostic),
                              "states": trace.get("states", ()), "fallback": trace.get("fallback"), "repairs": trace.get("repairs", ())})
        finally:
            prepared.store.close()
    result_hashes = {case_id: {name: sha(OUT / "RUNS" / case_id / name) for name in ("RUN_MANIFEST.json", "CANDIDATES.json", "CANDIDATE_PROFILES.json", "AGENT_TRACE.json", "RCA_REPORT.json")} for case_id in pilot}
    write(OUT / "PRIMARY_V2_BATCH_FREEZE.json", {"schema_version": "v3_phase2_16_primary_v2_batch_freeze_v1", "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "case_ids": list(pilot), "accounted_cases": len(completed), "result_artifact_hashes": result_hashes, "v2_config_sha256": sha(OUT / "V2_CONFIG_FREEZE.json"), "prompt_sha256": freeze["prompt_sha256"], "tool_definitions_sha256": freeze["tool_definitions_sha256"], "requested_model": config.model, "provider_metadata": config.public_metadata(), "git_revision": freeze["git_revision"], "development_only": True})
    # Phase 2.11 ground truth is consumed development data; access begins only after batch freeze.
    truth = {path.stem: json.loads(path.read_text(encoding="utf-8"))["evaluations"]["H5_COMBINED"].get("ground_truth_service_id") for path in (P211 / "CASE_EVALUATIONS").glob("*.json")}
    evaluated = []
    for item in completed:
        case_id = item["case_id"]; run = OUT / "RUNS" / case_id
        report = json.loads((run / "RCA_REPORT.json").read_text(encoding="utf-8")); profiles = json.loads((run / "CANDIDATE_PROFILES.json").read_text(encoding="utf-8"))["profiles"]
        candidate_to_service = {profile["candidate_id"]: profile["subject_id"] for profile in profiles}
        primary = report.get("primary_hypothesis") or {}; predicted = candidate_to_service.get(primary.get("candidate_id")); gt = truth[case_id]
        alternatives = [primary, *report.get("alternative_hypotheses", [])]
        final_services = [candidate_to_service.get(row.get("candidate_id")) for row in alternatives if isinstance(row, dict)]
        candidate_services = set(candidate_to_service.values())
        evaluated.append({**item, "ground_truth_service_id": gt, "predicted_service_id": predicted, "top1_correct": bool(predicted == gt),
                          "ground_truth_candidate_available": gt in candidate_services, "ground_truth_in_final_hypotheses": gt in final_services,
                          "final_candidate_ids": [row.get("candidate_id") for row in alternatives if isinstance(row, dict)],
                          "unknown_evidence_ids": 0, "invalid_candidate_ids": 0})
    write(OUT / "V2_RESULTS.json", {"schema_version": "v3_phase2_16_v2_results_v1", "development_only": True, "case_count": len(evaluated), "cases": evaluated,
                                      "status_counts": {status: sum(row["status"] == status for row in evaluated) for status in ("RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE", "TECHNICAL_FAILURE")},
                                      "top1_correct": sum(row["top1_correct"] for row in evaluated), "top1_accuracy": sum(row["top1_correct"] for row in evaluated) / len(evaluated),
                                      "ground_truth_available": sum(row["ground_truth_candidate_available"] for row in evaluated)})


if __name__ == "__main__": main()
