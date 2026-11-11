"""One fixed, resume-safe Phase 2.16 Agent V2 development retry.

No Phase 2.12 case artifact or development ground truth is read here. Analysis
must be run separately after PRIMARY_V2_RETRY_BATCH_FREEZE.json exists.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model, rca_v2_system_prompt
from cdoi.rca_agent_v2 import RCAAgentV2, RCA_AGENT_V2_TOOL_SCHEMA_VERSION, V2AgentBudget
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, RCAOrchestrator
from run_v3_phase2_16_v2_development import (P211, CACHE, INDEX, hash_tools,
                                              prepared_for, revision, sha, write)

OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_retry_20260924"
REQUIRED = ("RUN_MANIFEST.json", "CANDIDATES.json", "CANDIDATE_PROFILES.json",
            "AGENT_TRACE.json", "RCA_REPORT.json")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ObservedV2Model(QwenRCAAgentV2Model):
    """Telemetry-only wrapper; provider calls and model outputs are unchanged."""

    def __init__(self, config: QwenRCAConfig) -> None:
        super().__init__(config, max_output_tokens=8192)
        self.safe_turns: list[Mapping[str, Any]] = []

    def _message(self, response: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            return super()._message(response)
        finally:
            usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
            self.safe_turns.append({**dict(self.last_contract_diagnostic),
                "http_status": 200,
                "attempt_count": self.last_transport_diagnostic.get("attempt_count"),
                "retry_count": self.last_transport_diagnostic.get("retry_count"),
                "latency_ms": (self.last_transport_diagnostic.get("attempts") or [{}])[-1].get("elapsed_ms"),
                "input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "max_output_tokens": self.max_output_tokens})


def current_freeze(config: QwenRCAConfig, pilot: tuple[str, ...]) -> dict[str, Any]:
    budget = V2AgentBudget(max_tool_calls=8, max_h1_profiles=20,
                           max_evidence_per_tool_call=20, max_output_repairs=1)
    sources = ("candidate_evidence_profile.py", "rca_agent_v2.py", "qwen_rca_v2.py",
               "provider_output.py", "hypothesis_generation.py")
    return {"schema_version": "v3_phase2_16_v2_retry_config_freeze_v1",
        "git_revision": revision(), "requested_model": config.model,
        "provider_profile": config.public_metadata(), "temperature": 0,
        "prompt_version": "rca_agent_qwen_v2",
        "prompt_sha256": hashlib.sha256(rca_v2_system_prompt().encode()).hexdigest(),
        "candidate_evidence_profile_schema_version": "candidate_evidence_profile_v1",
        "profile_preload_policy": "COMPLETE_H1_DETERMINISTIC_PRELOAD_V1",
        "investigation_state_machine": "rca_agent_trace_v2",
        "candidate_source_policy": "H1_THEN_H5_FALLBACK",
        "fallback_reasons": ["H1_AMBIGUOUS", "MISSING_DISTINGUISHING_SIGNAL",
                             "CONFLICTING_H1_EVIDENCE", "RELEVANT_MODALITY_MISSING"],
        "tool_schema_version": RCA_AGENT_V2_TOOL_SCHEMA_VERSION,
        "tool_definitions_sha256": hash_tools(),
        "rca_report_schema_version": "rca_report_v1",
        "max_output_tokens": 8192, "timeout_seconds": 120,
        "max_rounds": 8, "max_tool_calls": budget.max_tool_calls,
        "max_h1_profiles": budget.max_h1_profiles,
        "max_evidence_per_tool_call": budget.max_evidence_per_tool_call,
        "repair_limit": budget.max_output_repairs,
        "retry_policy": {"max_retries": config.max_retries},
        "provider_normalizer_version": "provider_output_v1",
        "provider_normalizer_sha256": sha(ROOT / "src/cdoi/provider_output.py"),
        "policy_source_hashes": {name: sha(ROOT / "src/cdoi" / name) for name in sources},
        "development_dataset_manifest_sha256": sha(P211 / "EXPERIMENT_MANIFEST.json"),
        "development_case_ids": list(pilot), "development_only": True,
        "phase212": "PROHIBITED_NO_CASE_ARTIFACT_OR_GROUND_TRUTH_ACCESS"}


def prepare_archive(config: QwenRCAConfig, pilot: tuple[str, ...]) -> dict[str, Any]:
    freeze_path = OUT / "V2_RETRY_CONFIG_FREEZE.json"
    freeze = current_freeze(config, pilot)
    if freeze_path.exists():
        stored = json.loads(freeze_path.read_text(encoding="utf-8"))
        if stored != freeze: raise RuntimeError("FROZEN_RETRY_CONFIG_MISMATCH")
    else:
        if OUT.exists() and any(OUT.iterdir()): raise RuntimeError("RETRY_ARCHIVE_ALREADY_PARTIAL_WITHOUT_FREEZE")
        OUT.mkdir(parents=True, exist_ok=True)
        original = json.loads((ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_20260924/V2_CONFIG_FREEZE.json").read_text(encoding="utf-8"))
        if freeze["prompt_sha256"] != original["prompt_sha256"] or freeze["tool_definitions_sha256"] != original["tool_definitions_sha256"]:
            raise RuntimeError("V2_SCIENTIFIC_PROMPT_OR_TOOLS_CHANGED")
        write(OUT / "PREREGISTRATION.json", {"schema_version": "v3_phase2_16_v2_retry_preregistration_v1",
            "created_at_utc": now(), "development_only": True, "case_count": 12,
            "primary_policy": "ONE_FIXED_RUN_PER_CASE_NO_MID_BATCH_TUNING",
            "ground_truth_boundary": "NO_PHASE211_GT_UNTIL_PRIMARY_FREEZE",
            "excluded": ["Phase2.12 cases and GT", "telemetry-only", "stability repeats", "V2.1 tuning", "ontology augmentation"]})
        write(OUT / "DEVELOPMENT_DATA_MANIFEST.json", {"schema_version": "v3_phase2_16_v2_retry_data_v1",
            "status": "DEVELOPMENT_ONLY", "case_ids": list(pilot), "expected_cases": 12,
            "unique_cases": len(set(pilot)), "phase211_manifest_sha256": sha(P211 / "EXPERIMENT_MANIFEST.json"),
            "case_index_sha256": sha(INDEX), "phase212": "NOT_READ"})
        write(OUT / "V2_RETRY_DELTA_FROM_FAILED_BATCH.json", {"schema_version": "v3_phase2_16_v2_retry_delta_v1",
            "original_config_sha256": sha(ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_20260924/V2_CONFIG_FREEZE.json"),
            "changed": {"max_output_tokens": [512, 8192], "timeout_seconds": [30, 120],
                        "provider_turn_normalization": "Phase2.16R bounded normalization and precise truncation classification",
                        "safe_response_shape_telemetry": "ADDED_OBSERVATION_ONLY"},
            "unchanged": ["requested model", "temperature", "retry count", "H1/H5 generation", "complete H1 profile preload",
                          "V2 reasoning prompt", "V2 state machine", "fallback policy", "tool definitions", "RCAReport validator", "repair limit"],
            "scientific_policy_changed": False})
        write(freeze_path, freeze)
    if (OUT / "PRIMARY_V2_RETRY_BATCH_FREEZE.json").exists():
        raise RuntimeError("PRIMARY_RETRY_ALREADY_FROZEN_NO_RERUN")
    return freeze


def case_completed(case_id: str) -> bool:
    item = OUT / "CASE_RESULTS" / f"{case_id}.json"
    if not item.is_file(): return False
    row = json.loads(item.read_text(encoding="utf-8"))
    run = OUT / row["run_path"]
    if any(not (run / name).is_file() for name in REQUIRED):
        raise RuntimeError(f"COMPLETED_CASE_ARTIFACT_MISSING:{case_id}")
    for name, digest in row["result_hashes"].items():
        if sha(run / name) != digest: raise RuntimeError(f"COMPLETED_CASE_HASH_MISMATCH:{case_id}:{name}")
    return True


def case_path(case_id: str) -> Path:
    path = OUT / "RUNS" / case_id
    if not path.exists(): return path
    index = 1
    while (OUT / "RUNS" / f"{case_id}__resume{index}").exists(): index += 1
    resumed = OUT / "RUNS" / f"{case_id}__resume{index}"
    journal = OUT / "RERUN_JUSTIFICATIONS.json"
    prior = json.loads(journal.read_text(encoding="utf-8"))["entries"] if journal.exists() else []
    prior.append({"case_id": case_id, "reason": "INCOMPLETE_PRIOR_ATTEMPT_NO_CASE_RESULT",
                  "preserved_partial_run": path.relative_to(OUT).as_posix(),
                  "new_run": resumed.relative_to(OUT).as_posix(), "at_utc": now()})
    write(journal, {"schema_version": "v3_phase2_16_v2_retry_rerun_journal_v1", "entries": prior})
    return resumed


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_FROZEN_RETRY_ARCHIVE")
    load_dotenv_file(ROOT / ".env", override=False)
    base = QwenRCAConfig.from_internal_gateway_environment()
    if base.status() != "QWEN_LIVE_READY": raise RuntimeError("QWEN_LIVE_RUNTIME_NOT_READY")
    config = replace(base, timeout_seconds=120)
    if config.model != "vllm/Qwen3.8-27B" or config.max_retries != 1:
        raise RuntimeError("QUALIFIED_MODEL_OR_RETRY_POLICY_MISMATCH")
    import pyarrow.parquet as pq
    pilot = tuple(json.loads((P211 / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))["pilot_case_ids"])
    if len(pilot) != 12 or len(set(pilot)) != 12: raise RuntimeError("INVALID_PHASE211_DEVELOPMENT_CASESET")
    rows = {str(item["case"]): item for item in pq.read_table(INDEX, columns=["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]).to_pylist()}
    if any(case_id not in rows or not (CACHE / case_id).is_dir() for case_id in pilot):
        raise RuntimeError("DEVELOPMENT_CASE_INPUT_MISSING")
    freeze = prepare_archive(config, pilot)
    from cdoi.rcaeval_evaluation import RCAEvalCase
    budget = V2AgentBudget(max_tool_calls=8, max_h1_profiles=20,
                           max_evidence_per_tool_call=20, max_output_repairs=1)
    started_batch = now()
    for case_id in pilot:
        if case_completed(case_id): continue
        row = rows[case_id]
        case = RCAEvalCase(case_id, str(row["dataset"]), str(row["system"]), int(row["inject_time"]),
                          int(row["time_start"]) if row["time_start"] is not None else None,
                          int(row["time_end"]) if row["time_end"] is not None else None,
                          bool(row["has_logs"]), bool(row["has_traces"]))
        run = case_path(case_id)
        prepared = prepared_for(case, OUT / "STORES" / f"{case_id}.sqlite")
        began = now(); timer = perf_counter()
        try:
            model = ObservedV2Model(config)
            agent = RCAAgentV2(model, budget=budget)
            report = RCAOrchestrator().run(prepared, run, InvestigationMode.AGENT,
                CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, model.public_metadata())
            trace = json.loads((run / "AGENT_TRACE.json").read_text(encoding="utf-8"))
            result = {"schema_version": "v3_phase2_16_v2_retry_case_v1", "case_id": case_id,
                "run_path": run.relative_to(OUT).as_posix(), "started_at_utc": began,
                "ended_at_utc": now(), "case_latency_ms": round((perf_counter() - timer) * 1000, 3),
                "status": report.status, "primary_candidate_id": report.primary_hypothesis.candidate_id if report.primary_hypothesis else None,
                "h1_candidate_count": len(prepared.h1_candidates), "h5_candidate_count": len(prepared.h5_candidates),
                "h1_candidate_ids": [x.candidate_id for x in prepared.h1_candidates],
                "h5_candidate_ids": [x.candidate_id for x in prepared.h5_candidates],
                "states": trace.get("states", []), "tool_calls": trace.get("tool_calls", []),
                "fallback": trace.get("fallback"), "repairs": trace.get("repairs", []),
                "error_code": trace.get("error_code"),
                "provider_turns": model.safe_turns, "transport_history": model.transport_history,
                "model_records": list(model.records), "requested_model": config.model,
                "result_hashes": {name: sha(run / name) for name in REQUIRED}}
            write(OUT / "CASE_RESULTS" / f"{case_id}.json", result)
        finally:
            prepared.store.close()
    cases = [json.loads((OUT / "CASE_RESULTS" / f"{case_id}.json").read_text(encoding="utf-8")) for case_id in pilot]
    if len(cases) != 12 or any(not case_completed(case_id) for case_id in pilot):
        raise RuntimeError("PRIMARY_RETRY_NOT_COMPLETE")
    write(OUT / "V2_RETRY_RESULTS.json", {"schema_version": "v3_phase2_16_v2_retry_results_v1",
        "development_only": True, "cases": cases,
        "status_counts": {status: sum(row["status"] == status for row in cases)
                          for status in ("RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE", "TECHNICAL_FAILURE")}})
    write(OUT / "PRIMARY_V2_RETRY_BATCH_FREEZE.json", {
        "schema_version": "v3_phase2_16_v2_retry_primary_freeze_v1", "frozen_at_utc": now(),
        "batch_started_at_utc": started_batch, "case_ids": list(pilot), "accounted_cases": 12,
        "config_sha256": sha(OUT / "V2_RETRY_CONFIG_FREEZE.json"),
        "prompt_sha256": freeze["prompt_sha256"],
        "provider_normalizer_sha256": freeze["provider_normalizer_sha256"],
        "tool_definitions_sha256": freeze["tool_definitions_sha256"],
        "result_sha256": sha(OUT / "V2_RETRY_RESULTS.json"),
        "case_result_sha256": {case_id: sha(OUT / "CASE_RESULTS" / f"{case_id}.json") for case_id in pilot},
        "run_artifact_sha256": {row["case_id"]: row["result_hashes"] for row in cases},
        "requested_model": config.model,
        "resolved_models": sorted({turn.get("resolved_model") for row in cases for turn in row["provider_turns"] if turn.get("resolved_model")}),
        "git_revision": freeze["git_revision"], "development_only": True,
        "ground_truth_read": False})


if __name__ == "__main__": main()
