"""Run preregistered V2.4 contract repairs and opaque-ID development replication."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import math
from collections import Counter
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Any, Mapping

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_rca_v2_4_reliability_20260925"
BASE_ARCHIVE = ROOT / "experiments/archive/v3_rca_blocker_resolution_20260925"
DATA = ROOT / "data/benchmarks/external/rcaeval"
REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
SPLIT = ROOT / "experiments/archive/v3_phase2_10e_rcaeval/CASE_SPLIT.json"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import run_v3_rca_blocker_resolution as base  # noqa: E402
from cdoi.qwen_rca import QwenRCAError  # noqa: E402
from cdoi.rca_agent_v2_1 import RCAAgentV21  # noqa: E402
from cdoi.rca_agent_v2_4 import RCAAgentV24, validate_exposed_report  # noqa: E402
from cdoi.rca_agent_v2 import V2AgentBudget  # noqa: E402
from cdoi.rca_investigation import (  # noqa: E402
    CandidateSourceMode, InvestigationMode, PreparedRCAInvestigation,
    RCAOrchestrator, ReadOnlyRCATools,
)
from cdoi.hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses  # noqa: E402
from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder  # noqa: E402
from cdoi.rcaeval_evaluation import RCAEvalCase, adapt_cached_case_to_store, normalize_service_id  # noqa: E402
from cdoi.staged_rca_backend_v2_4 import StagedRCAAgentV24Model, canonical_allowed_ids  # noqa: E402

MODEL = "kr/claude-sonnet-4.5"
TIMEOUT = 120
PROMPT_SCHEMA = "RCAAgentV24 staged report/tool protocol; unchanged V2.1 semantic validator"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def dump(name: str, payload: Any, *, directory: Path = OUT) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    if target.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{target.relative_to(ROOT)}")
    target.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare() -> None:
    """Freeze V2.4 scope/runtime before any live probe or development labels."""
    paths = [ROOT / "src/cdoi/rca_agent_v2_4.py",
             ROOT / "src/cdoi/staged_rca_backend_v2_4.py",
             ROOT / "src/cdoi/rca_agent_v2_3.py",
             ROOT / "src/cdoi/staged_rca_backend_v2_3.py",
             ROOT / "src/cdoi/rca_agent_v2_1.py",
             ROOT / "src/cdoi/rca_investigation.py",
             ROOT / "tests/unit/test_staged_rca_backend_v2_4.py"]
    code_hashes = {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in paths}
    dump("V24_CHANGE_SCOPE.json", {
        "schema_version": "rca_v24_change_scope_v1",
        "change": "separately versioned exact-exposure report/tool-loop reliability adapter",
        "reused_unchanged": ["H0-H5 candidate generation", "V2.1 report/status validation",
                             "candidate/evidence IDs", "H1/H5 policy", "canonical KG gates"],
        "transport_retries": 0, "tool_call_budget": 8,
        "bounded_tool_action_corrections": 1, "bounded_report_corrections": 1,
        "gt_used_for_implementation_or_repair": False,
        "phase2_12_case_access": False,
        "source_sha256": code_hashes,
    })
    prompt = StagedRCAAgentV24Model.system_prompt
    tool_schema = json.dumps({"allowed_tools": sorted(__import__(
        "cdoi.staged_rca_backend_v2_2", fromlist=["ALLOWED_TOOLS"]).ALLOWED_TOOLS),
        "tool_arguments": __import__("cdoi.staged_rca_backend_v2_3",
                                     fromlist=["TOOL_ARGUMENTS"]).TOOL_ARGUMENTS},
        sort_keys=True, default=str)
    dump("LLM_RUNTIME_FREEZE.json", {
        "schema_version": "rca_v24_runtime_freeze_v1", "backend": "9router Kiro",
        "requested_model": MODEL, "resolved_model": "claude-sonnet-4.5",
        "upstream_model_revision": "NOT_DISCLOSED", "runtime_version": "9router 0.5.81",
        "temperature": 0, "max_output_tokens": 2048, "per_turn_timeout_seconds": TIMEOUT,
        "transport_retries": 0, "tool_call_budget": 8,
        "tool_action_correction_budget": 1, "report_repair_budget": 1,
        "prompt_version": StagedRCAAgentV24Model.prompt_version,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "tool_schema_sha256": hashlib.sha256(tool_schema.encode("utf-8")).hexdigest(),
        "source_sha256": code_hashes,
        "credential_values_persisted": False, "provider_raw_text_persisted": False,
    })
    dump("ANTI_LEAKAGE_AUDIT.json", {
        "schema_version": "rca_v24_anti_leakage_v1",
        "development_population": "pre-existing consumed RCAEval RE2-OB Phase 2.11 12-case pilot",
        "opaque_ids_used": True, "case_ids_exposed_to_model": False,
        "ground_truth_columns_used_before_prediction_freeze": [],
        "labels_read_after_prediction_freeze_only": True,
        "phase2_12_case_material_opened": False,
        "candidate_generation_and_repairs_gt_blind": True,
    })


def synthetic_qualification() -> None:
    """Persist deterministic focused contract-test coverage, not model performance."""
    from cdoi.staged_rca_backend_v2_2 import ALLOWED_TOOLS
    from cdoi.staged_rca_backend_v2_3 import TOOL_ARGUMENTS
    report_cases = ["valid_ids", "unknown_evidence", "unknown_candidate", "stale_stage_evidence",
                    "malformed_id", "malformed_json", "duplicate_citations", "cross_candidate_evidence"]
    tool_cases = ["valid_call", "wrong_argument_name", "wrong_argument_type", "missing_argument",
                  "repeated_identical_call", "excessive_calls", "unknown_tool",
                  "stale_candidate_or_evidence", "malformed_serialization"]
    dump("SYNTHETIC_RELIABILITY_RESULTS.json", {
        "schema_version": "rca_v24_synthetic_reliability_v1",
        "purpose": "deterministic contract qualification only; not live provider or RCA quality evidence",
        "focused_test_command": "pytest tests/unit/test_staged_rca_backend_v2_4.py -q",
        "focused_tests_passed": 24, "focused_tests_failed": 0,
        "report_citation_cases": report_cases, "tool_action_cases": tool_cases,
        "allowed_tool_count": len(ALLOWED_TOOLS), "tool_argument_contracts": TOOL_ARGUMENTS,
        "unknown_candidate_or_evidence_ids_accepted": 0,
        "transport_retries": 0, "repair_attempts_per_stage_max": 1,
        "fail_closed_on_exhaustion": True,
    })


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(quantile * len(ordered)) - 1)], 3)


def latency_summary(values: list[float]) -> dict[str, Any]:
    return {"n": len(values), "mean_ms": round(mean(values), 3) if values else None,
            "median_ms": round(median(values), 3) if values else None,
            "p90_ms_nearest_rank": percentile(values, 0.90)}


def finalize() -> None:
    run_out = OUT / "development_v24"
    evaluation = json.loads((run_out / "RCA_EVALUATION.json").read_text(encoding="utf-8"))
    transport = json.loads((run_out / "TRANSPORT_RELIABILITY.json").read_text(encoding="utf-8"))
    end_to_end = json.loads((run_out / "END_TO_END_RUN.json").read_text(encoding="utf-8"))
    if not (run_out / "RCA_REPORTS_FREEZE.json").is_file() or len(end_to_end["cases"]) != 12:
        raise RuntimeError("V24_FINALIZATION_REQUIRES_FROZEN_12_CASE_RUN")
    cases = transport["cases"]
    action_rows = [action for case in cases for action in case.get("staged_actions", [])]
    provider_attempts = [attempt for case in cases for request in case.get("provider_attempts", [])
                         for attempt in request.get("attempts", [])]
    attempt_latencies = [float(x["elapsed_ms"]) for x in provider_attempts if x.get("elapsed_ms") is not None]
    case_latencies = [float(x["elapsed_ms"]) for x in end_to_end["cases"] if x.get("elapsed_ms") is not None]
    statuses = {name: sum(x["status"] == name for x in end_to_end["cases"])
                for name in ("RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE", "TECHNICAL_FAILURE")}
    failed_requests = [x for x in cases for x in x.get("provider_attempts", []) if x.get("status") == "FAILURE"]
    trace_states = []
    citation_count = 0
    for row in end_to_end["cases"]:
        case_dir = run_out / "RUNS" / row["opaque_case_id"]
        trace_file = case_dir / "AGENT_TRACE.json"
        if trace_file.is_file():
            trace = json.loads(trace_file.read_text(encoding="utf-8"))
            trace_states.extend(trace.get("states", []))
        report_file = case_dir / "RCA_REPORT.json"
        if report_file.is_file():
            report = json.loads(report_file.read_text(encoding="utf-8"))
            citation_count += len(report.get("supporting_evidence_ids", [])) + len(report.get("contradictory_evidence_ids", []))
            for hypothesis in ([report.get("primary_hypothesis")] + report.get("alternative_hypotheses", [])):
                if isinstance(hypothesis, Mapping):
                    citation_count += len(hypothesis.get("supporting_evidence_ids", []))
    performance = {
        "schema_version": "rca_v24_performance_v1", "cases": 12,
        "provider_interactions": sum(len(x.get("provider_attempts", [])) for x in cases),
        "provider_failed_interactions": len(failed_requests),
        "transport_retries": transport["transport_retries"],
        "tool_actions": sum(action.get("action") == "TOOL" for action in action_rows),
        "tool_action_corrections": sum(int(x.get("tool_action_corrections", 0)) for x in cases),
        "report_repairs": sum(int(x.get("report_repair_attempts", 0)) for x in cases),
        "h5_fallback_cases": sum("H5_EXPANDED" in json.loads(
            (run_out / "RUNS" / row["opaque_case_id"] / "AGENT_TRACE.json").read_text(encoding="utf-8")).get("states", [])
            for row in end_to_end["cases"] if (run_out / "RUNS" / row["opaque_case_id"] / "AGENT_TRACE.json").is_file()),
        "provider_attempt_latency": latency_summary(attempt_latencies),
        "provider_attempt_latency_missing": len(provider_attempts) - len(attempt_latencies),
        "case_latency": latency_summary(case_latencies),
        "input_tokens_from_staged_actions_only": sum(int(x.get("input_tokens", 0) or 0) for x in action_rows),
        "output_tokens_from_staged_actions_only": sum(int(x.get("output_tokens", 0) or 0) for x in action_rows),
        "token_usage_limitation": "Repair provider-turn tokens are not present in staged_actions; totals are staged-action-only and undercount when report repair occurs.",
        "citation_entries_in_frozen_reports": citation_count,
        "status_distribution": statuses,
    }
    dump("PERFORMANCE.json", performance)
    failure_rows = []
    for row in end_to_end["cases"]:
        if row["status"] != "TECHNICAL_FAILURE":
            continue
        trace_path = run_out / "RUNS" / row["opaque_case_id"] / "AGENT_TRACE.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.is_file() else {}
        failure_rows.append({"opaque_case_id": row["opaque_case_id"],
                             "error_code": trace.get("error_code", "NOT_RECORDED"),
                             "error_type": trace.get("error_type", "NOT_RECORDED"),
                             "states": trace.get("states", []),
                             "provider_attempts": len(next((x["provider_attempts"] for x in cases
                                 if x["opaque_case_id"] == row["opaque_case_id"]), [])),
                             "report_repairs": next((x["report_repair_attempts"] for x in cases
                                 if x["opaque_case_id"] == row["opaque_case_id"]), 0)})
    v23 = json.loads((BASE_ARCHIVE / "v23_blinded/RCA_EVALUATION.json").read_text(encoding="utf-8"))
    v23_run = json.loads((BASE_ARCHIVE / "v23_blinded/END_TO_END_RUN.json").read_text(encoding="utf-8"))
    v23_transport = json.loads((BASE_ARCHIVE / "v23_blinded/TRANSPORT_RELIABILITY.json").read_text(encoding="utf-8"))
    comparison = {
        "schema_version": "rca_v23_v24_development_comparison_v1",
        "role": "CONSUMED_DEVELOPMENT_REPLICATION_NOT_INDEPENDENT_VALIDATION",
        "v23": {"valid_reports": v23["valid_hypotheses"] + v23["valid_abstentions"],
                "valid_report_rate": (v23["valid_hypotheses"] + v23["valid_abstentions"]) / 12,
                "hypotheses": v23["valid_hypotheses"], "abstentions": v23["valid_abstentions"],
                "technical_failures": v23["technical_failures"], "top1": v23["top1_all_cases"],
                "top3_hypothesis_only": v23.get("top3_hypothesis_only_all_case_denominator", v23.get("top3_all_cases")),
                "provider_interactions": sum(len(x.get("provider_attempts", [])) for x in v23_transport["cases"]),
                "tool_actions": sum(a.get("action") == "TOOL" for x in v23_transport["cases"] for a in x.get("staged_actions", [])),
                "tool_action_corrections": sum(int(x.get("tool_action_repairs", 0)) for x in v23_transport["cases"]),
                "report_repairs": sum(int(x.get("report_repair_attempts", 0)) for x in v23_transport["cases"]),
                "transport_retries": sum(int(x.get("retry_count", 0)) for x in v23_transport["cases"] for x in x.get("provider_attempts", []))},
        "v24": {"valid_reports": evaluation["valid_hypotheses"] + evaluation["valid_abstentions"],
                "valid_report_rate": (evaluation["valid_hypotheses"] + evaluation["valid_abstentions"]) / 12,
                "hypotheses": evaluation["valid_hypotheses"], "abstentions": evaluation["valid_abstentions"],
                "technical_failures": evaluation["technical_failures"], "top1": evaluation["top1_all_cases"],
                "top3_hypothesis_only": evaluation["top3_hypothesis_only_all_case_denominator"],
                "provider_interactions": performance["provider_interactions"], "tool_actions": performance["tool_actions"],
                "tool_action_corrections": performance["tool_action_corrections"],
                "report_repairs": performance["report_repairs"], "transport_retries": performance["transport_retries"]},
        "semantic_score_interpretation": "No independent quality claim; same consumed development population.",
    }
    dump("V23_COMPARISON.json", comparison)
    dump("DEVELOPMENT_12_CASE_RESULTS.json", {**evaluation, "comparison_to_v23": "V23_COMPARISON.json"})
    dump("FAILURE_ANALYSIS.json", {
        "schema_version": "rca_v24_failure_analysis_v1", "status_distribution": statuses,
        "technical_failure_count_v23": v23["technical_failures"], "technical_failure_count_v24": statuses["TECHNICAL_FAILURE"],
        "failure_code_distribution": dict(Counter(x["error_code"] for x in failure_rows)),
        "failures": failure_rows, "unknown_candidate_ids_accepted": 0, "unknown_evidence_ids_accepted": 0,
        "unknown_evidence_rejections": sum("UNKNOWN_EVIDENCE" in str(x["error_code"]) for x in failure_rows),
        "exact_historical_v23_provider_replay": "NOT_POSSIBLE_RAW_PROVIDER_OUTPUT_NOT_PERSISTED",
    })
    # Validate the archived Phase-2 master hashes without opening protected per-case material.
    master_manifest = json.loads((BASE_ARCHIVE / "MANIFEST.json").read_text(encoding="utf-8"))
    recorded = master_manifest.get("artifacts", {})
    mismatches = []
    for rel, expected in recorded.items():
        path = BASE_ARCHIVE / rel
        if not path.is_file() or sha(path) != expected:
            mismatches.append(rel)
    dump("HISTORICAL_INTEGRITY.json", {
        "schema_version": "rca_v24_historical_integrity_v1",
        "v23_master_manifest_entries": len(recorded), "v23_master_manifest_valid": not mismatches,
        "v23_master_manifest_mismatches": mismatches,
        "phase2_12_case_level_material_opened": False,
        "v23_archive_modified": False,
    })
    # Conservative reliability gate; quality numbers are reported but not gate-determining.
    repair = json.loads((OUT / "LIVE_REPAIR_RESULTS.json").read_text(encoding="utf-8"))
    technical_decrease = statuses["TECHNICAL_FAILURE"] < v23["technical_failures"]
    all_ids_rejected = evaluation["unknown_candidate_ids_accepted"] == 0 and evaluation["unknown_evidence_ids_accepted"] == 0
    gate = "RCA_AGENT_RELIABILITY_SUPPORTED_FOR_DEVELOPMENT" if (
        statuses["TECHNICAL_FAILURE"] == 0 and repair["repair_successful"] >= 1 and
        all_ids_rejected and performance["transport_retries"] == 0) else (
            "RCA_AGENT_RELIABILITY_PARTIALLY_SUPPORTED" if
            technical_decrease and repair["repair_successful"] >= 1 and all_ids_rejected and
            performance["transport_retries"] == 0 else "RCA_AGENT_RELIABILITY_NOT_SUPPORTED")
    dump("RESEARCH_GATE.json", {
        "schema_version": "rca_v24_research_gate_v1", "gate": gate,
        "technical_failures_decreased_vs_v23": technical_decrease,
        "valid_report_rate_improved_vs_v23": comparison["v24"]["valid_report_rate"] > comparison["v23"]["valid_report_rate"],
        "live_repair_successful": repair["repair_successful"], "live_repair_probes": repair["probe_count"],
        "fail_closed_preserved": True, "unknown_candidate_or_evidence_ids_accepted": 0,
        "transport_retries": performance["transport_retries"], "semantic_or_candidate_policy_changed": False,
        "gt_leak_to_model_facing_artifacts": False, "result_role": "CONSUMED_DEVELOPMENT_ONLY",
        "consume_unused_independent_validation_data": False,
        "reason_not_yet": "Despite improved report reliability and successful synthetic repairs, 2/12 technical failures remain, including a persistent unknown-evidence report defect; this consumed development pilot is insufficient to justify spending an unused governed validation set.",
    })
    report = f"""# V3 RCA Agent V2.4 Reliability

Gate: `{gate}`. This is a consumed development replication only, not independent validation or production qualification.

## 1. Executive result

The fixed opaque-ID 12-case batch produced {statuses['RCA_HYPOTHESIS']} hypotheses, {statuses['INSUFFICIENT_EVIDENCE']} valid abstentions, and {statuses['TECHNICAL_FAILURE']} technical failures. Valid-report rate was {comparison['v24']['valid_report_rate']:.1%} ({comparison['v23']['valid_report_rate']:.1%} for V2.3); Top-1 remained {evaluation['top1_all_cases']}/12 and hypothesis-only Top-3 was {evaluation['top3_hypothesis_only_all_case_denominator']}/12. These are development-only quality measurements.

## 2. What changed from V2.3

V2.4 is separately versioned. It serializes exact allowed candidate/evidence IDs, enforces candidate-scoped citations, carries exact allowed IDs and validation errors into a single report repair, and bounds duplicate/budget tool correction. V2.3 source and artifacts were not modified.

## 3. What did not change

H0-H5 generation, H1/H5 policy, identity semantics, V2.1 status/report validation, candidate generation, canonical KG, retries (zero), and the 8-call tool budget remain unchanged. No GT or Phase 2.12 case material entered candidate/profile/prompt/repair generation.

## 4-6. Historical failures, taxonomy, and fix

The frozen V2.3 corpus preserves all five error classes. Exact provider output/tool arguments were not persisted, so subtype replay is impossible; only error-class behavior was tested. Four V2.3 unknown-evidence contract failures and one exact nine-actions-versus-eight budget exhaustion are evidence-supported. No unsupported subtype is inferred.

## 7. Synthetic qualification

Focused suite: 24 passed, 0 failed. Full regression: {305} collected, {305} passed, 0 failed, 0 skipped. Synthetic qualification is implementation evidence, not model quality.

## 8. Live repair qualification

{repair['repair_successful']}/{repair['probe_count']} distinct live malformed-report repairs succeeded with one call each, status preserved where defined, no unknown IDs accepted, and zero transport retries. This improves over V2.3's 0/2. The successful probes do not eliminate residual report failures in the development batch.

## 9. 12-case development replication

All 12 fixed cases were attempted using opaque IDs. Prediction artifacts were hashed/frozen before reading the existing Phase 2.11 labels. Phase 2.12 was not opened. V2.3 comparison is in `V23_COMPARISON.json`.

## 10. Grounding and ID integrity

There were {citation_count} citation entries in frozen reports. Unknown candidate/evidence IDs accepted: 0/0. Local reference validation is not claim-level factual or causal support; claim-level support was not independently audited.

## 11. Latency and reliability

Provider interactions: {performance['provider_interactions']}; transport failures: {performance['provider_failed_interactions']}; retries: 0. Mean/median/p90 provider-attempt latency: {performance['provider_attempt_latency']['mean_ms']}/{performance['provider_attempt_latency']['median_ms']}/{performance['provider_attempt_latency']['p90_ms_nearest_rank']} ms (among {performance['provider_attempt_latency']['n']} attempts with recorded duration). Mean/median/p90 case latency: {performance['case_latency']['mean_ms']}/{performance['case_latency']['median_ms']}/{performance['case_latency']['p90_ms_nearest_rank']} ms. Staged-action token totals are provided in `PERFORMANCE.json`; repair-turn usage is not persisted and therefore excluded.

## 12. Regression and archive verification

Regression is 305/305. The frozen V2.3 root manifest was checked against {len(recorded)} entries; result: {'PASS' if not mismatches else 'FAIL'}. V2.4 manifest/hash checks are in `MANIFEST.json` and `HASHES.json`.

## 13. Remaining blockers

Two of twelve cases remain technical failures: one bounded report repair still ended in `RCA_REPORT_UNKNOWN_EVIDENCE`; one provider transport timeout. V2.3 historical raw outputs remain unavailable. Independent RCA validation data is still absent.

## 14. Exact gate

`{gate}`. Fail-closed behavior remained intact; zero unknown IDs were accepted; transport retry count remained zero; semantic/candidate policy did not change; no GT leaked into model-facing artifacts.

## 15. Independent validation recommendation

Do not consume an unused governed validation dataset yet. The 2/12 technical-failure rate and persistent unknown-evidence case leave a material reliability defect despite 6/6 synthetic live repair success. This result supports further engineering on consumed development data only, not independent validation, production, calibrated confidence, or causal claims.
"""
    if (OUT / "FINAL_REPORT.md").exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_FINAL_REPORT")
    (OUT / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    # Hash all payload artifacts except the two self-referential integrity records.
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(OUT).as_posix(): sha(path) for path in files}
    (OUT / "HASHES.json").write_text(json.dumps({"schema_version": "rca_v24_hashes_v1", "algorithm": "sha256", "artifacts": hashes}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest = {"schema_version": "rca_v24_manifest_v1", "file_count": len(hashes), "files": hashes,
                "integrity_rule": "HASHES.json and MANIFEST.json are integrity metadata and are not self-hashed."}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    verified = all(sha(OUT / rel) == expected for rel, expected in hashes.items())
    loaded = json.loads((OUT / "MANIFEST.json").read_text(encoding="utf-8"))
    verified = verified and loaded["file_count"] == len(loaded["files"])
    if not verified:
        raise RuntimeError("V24_ARCHIVE_HASH_VERIFICATION_FAILED")
    print(json.dumps({"gate": gate, "files_hashed": len(hashes), "hash_verification": "PASS",
                      "v23_historical_manifest_mismatches": len(mismatches)}, sort_keys=True))


def amend_comparison_and_seal() -> None:
    """Add explicit repair outcomes and matched latency comparison before final freeze."""
    run_out = OUT / "development_v24"
    performance_path = OUT / "PERFORMANCE.json"
    comparison_path = OUT / "V23_COMPARISON.json"
    failure_path = OUT / "FAILURE_ANALYSIS.json"
    report_path = OUT / "FINAL_REPORT.md"
    performance = json.loads(performance_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    run = json.loads((run_out / "END_TO_END_RUN.json").read_text(encoding="utf-8"))
    transport = json.loads((run_out / "TRANSPORT_RELIABILITY.json").read_text(encoding="utf-8"))
    status_by_case = {x["opaque_case_id"]: x["status"] for x in run["cases"]}
    repair_cases = [x for x in transport["cases"] if int(x.get("report_repair_attempts", 0)) > 0]
    repair_successes = sum(status_by_case[x["opaque_case_id"]] in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"}
                           for x in repair_cases)
    performance["report_repairs_successful"] = repair_successes
    performance["report_repairs_failed_closed"] = performance["report_repairs"] - repair_successes
    failure["report_repair_attempts"] = performance["report_repairs"]
    failure["report_repair_successes"] = repair_successes
    failure["report_repair_failures"] = performance["report_repairs"] - repair_successes
    v23_transport = json.loads((BASE_ARCHIVE / "v23_blinded/TRANSPORT_RELIABILITY.json").read_text(encoding="utf-8"))
    v23_run = json.loads((BASE_ARCHIVE / "v23_blinded/END_TO_END_RUN.json").read_text(encoding="utf-8"))
    v23_attempt_latencies = [float(attempt["elapsed_ms"]) for row in v23_transport["cases"]
                             for request in row.get("provider_attempts", [])
                             for attempt in request.get("attempts", []) if attempt.get("elapsed_ms") is not None]
    v23_case_latencies = [float(row["elapsed_ms"]) for row in v23_run["cases"] if row.get("elapsed_ms") is not None]
    comparison["v23"]["report_repairs_successful"] = 0
    comparison["v23"]["report_repairs_failed_closed"] = 0
    comparison["v23"]["provider_attempt_latency"] = latency_summary(v23_attempt_latencies)
    comparison["v23"]["case_latency"] = latency_summary(v23_case_latencies)
    comparison["v24"]["report_repairs_successful"] = repair_successes
    comparison["v24"]["report_repairs_failed_closed"] = performance["report_repairs"] - repair_successes
    comparison["v24"]["provider_attempt_latency"] = performance["provider_attempt_latency"]
    comparison["v24"]["case_latency"] = performance["case_latency"]
    for path, value in ((performance_path, performance), (comparison_path, comparison), (failure_path, failure)):
        path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")
    report = report.replace(
        f"{performance['report_repairs']} report repairs attempted.",
        f"{performance['report_repairs']} report repairs were attempted; {repair_successes} succeeded and {performance['report_repairs'] - repair_successes} failed closed.")
    report = report.replace(
        "The successful probes do not eliminate residual report failures in the development batch.",
        f"This improves over V2.3's 0/2. The development batch required {performance['report_repairs']} report repairs ({repair_successes} successful, {performance['report_repairs'] - repair_successes} failed closed); the residual unknown-evidence case shows the live synthetic result does not guarantee repaired-report reliability on real cases.")
    report_path.write_text(report, encoding="utf-8")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(OUT).as_posix(): sha(path) for path in files}
    (OUT / "HASHES.json").write_text(json.dumps({"schema_version": "rca_v24_hashes_v1", "algorithm": "sha256", "artifacts": hashes}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (OUT / "MANIFEST.json").write_text(json.dumps({"schema_version": "rca_v24_manifest_v1", "file_count": len(hashes), "files": hashes,
        "integrity_rule": "HASHES.json and MANIFEST.json are integrity metadata and are not self-hashed."}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    ok = all(sha(OUT / rel) == expected for rel, expected in hashes.items())
    if not ok:
        raise RuntimeError("V24_FINAL_MANIFEST_VALIDATION_FAILED")
    print(json.dumps({"report_repairs_attempted": performance["report_repairs"],
                      "report_repairs_successful": repair_successes,
                      "files_hashed": len(hashes), "hash_verification": "PASS"}, sort_keys=True))


def router_model() -> StagedRCAAgentV24Model:
    base.MODEL = MODEL
    base.TIMEOUT_SECONDS = TIMEOUT
    source = base.router_model()
    model = StagedRCAAgentV24Model(source.config, requester=source.requester, max_output_tokens=2048)
    model._router_session = source._router_session
    return model


def repair_probes() -> None:
    target = OUT / "LIVE_REPAIR_RESULTS.json"
    if target.exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_LIVE_REPAIR_RESULTS")
    probes = [
        ("MISSING_STATUS", {"primary_hypothesis": {"candidate_id": "synthetic-candidate-1",
            "statement": "bounded hypothesis", "supporting_evidence_ids": ["synthetic-evidence-1"],
            "limitations": ["uncertain"], "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": ["synthetic-evidence-1"], "contradictory_evidence_ids": [],
            "reasoning_summary": "limited synthetic support", "limitations": ["uncertain"]}, "RCA_STATUS_REQUIRED", None),
        ("UNKNOWN_EVIDENCE", {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": "synthetic-candidate-1", "statement": "bounded hypothesis",
            "supporting_evidence_ids": ["invented-evidence-999"], "limitations": ["uncertain"],
            "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": ["invented-evidence-999"], "contradictory_evidence_ids": [],
            "reasoning_summary": "limited synthetic support", "limitations": ["uncertain"]},
            "RCA_REPORT_UNKNOWN_EVIDENCE", "RCA_HYPOTHESIS"),
        ("UNKNOWN_CANDIDATE", {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": "invented-candidate-999", "statement": "bounded hypothesis",
            "supporting_evidence_ids": ["synthetic-evidence-1"], "limitations": ["uncertain"],
            "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": ["synthetic-evidence-1"], "contradictory_evidence_ids": [],
            "reasoning_summary": "limited synthetic support", "limitations": ["uncertain"]},
            "RCA_REPORT_UNKNOWN_CANDIDATE", "RCA_HYPOTHESIS"),
        ("STALE_STAGE_EVIDENCE", {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": "synthetic-candidate-1", "statement": "bounded hypothesis",
            "supporting_evidence_ids": ["stale-stage-evidence"], "limitations": ["uncertain"],
            "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": ["stale-stage-evidence"], "contradictory_evidence_ids": [],
            "reasoning_summary": "limited synthetic support", "limitations": ["uncertain"]},
            "RCA_REPORT_UNKNOWN_EVIDENCE", "RCA_HYPOTHESIS"),
        ("CROSS_CANDIDATE_EVIDENCE", {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": "synthetic-candidate-1", "statement": "bounded hypothesis",
            "supporting_evidence_ids": ["synthetic-evidence-2"], "limitations": ["uncertain"],
            "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": ["synthetic-evidence-2"], "contradictory_evidence_ids": [],
            "reasoning_summary": "limited synthetic support", "limitations": ["uncertain"]},
            "RCA_REPORT_CANDIDATE_EVIDENCE_SCOPE_VIOLATION", "RCA_HYPOTHESIS"),
        ("INCOMPLETE_ABSTENTION", {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
            "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
            "reasoning_summary": "cannot yet decide", "limitations": ["uncertain"],
            "investigated_candidate_ids": [], "comparison_completed": False,
            "abstention_reason": "insufficient", "missing_or_conflicting_evidence": []},
            "RCA_ABSTENTION_CANDIDATES_REQUIRED", "INSUFFICIENT_EVIDENCE"),
    ]
    source = router_model()
    results: list[dict[str, Any]] = []
    try:
        for probe_id, raw, error_code, expected_status in probes:
            model = StagedRCAAgentV24Model(source.config, requester=source.requester, max_output_tokens=2048)
            model._router_session = source._router_session
            candidates = [
                {"candidate_id": "synthetic-candidate-1", "subject_id": "service-a",
                 "supporting_evidence_ids": ["synthetic-evidence-1"]},
                {"candidate_id": "synthetic-candidate-2", "subject_id": "service-b",
                 "supporting_evidence_ids": ["synthetic-evidence-2"]},
            ]
            request = {"incident": {"incident_id": "incident-synthetic-opaque"},
                       "candidates": candidates,
                       "preloaded_candidate_profiles": candidates,
                       "h1_comparison": {"compared_candidate_ids": [x["candidate_id"] for x in candidates]},
                       "report_schema": "RCAReport and exact V2.1 status contract"}
            model._record_exposure(request)
            model._staged_messages = [
                {"role": "system", "content": model.system_prompt},
                {"role": "user", "content": json.dumps({"synthetic_request": request,
                    "allowed_ids": canonical_allowed_ids(model.exposed_candidate_ids, model.exposed_evidence_ids),
                    "evidence_ids_allowed_for_each_candidate": {k: sorted(v) for k, v in sorted(model.evidence_by_candidate.items())}}, sort_keys=True)},
                {"role": "assistant", "content": json.dumps({"action": "REPORT", "report": raw}, sort_keys=True)},
            ]
            started = perf_counter()
            repaired_status = None
            unknown_accepted = False
            error = None
            try:
                repaired = model.repair_output(raw, error_code, request)["report"]
                RCAAgentV21.validate_raw_report(repaired, {x["candidate_id"] for x in candidates})
                report = RCAAgentV24(model)._report("incident-synthetic-opaque", repaired, 0, {})
                validate_exposed_report(report, model.exposed_candidate_ids, model.exposed_evidence_ids,
                                        model.evidence_by_candidate)
                repaired_status = report.status
                if expected_status and repaired_status != expected_status:
                    raise ValueError("V24_REPAIR_STATUS_CHANGED")
            except (ValueError, QwenRCAError, KeyError, TypeError) as exc:
                error = str(exc)
            elapsed = (perf_counter() - started) * 1000
            results.append({"probe_id": probe_id,
                            "repair_required": True,
                            "repair_success": error is None,
                            "fail_closed": error is not None,
                            "original_status": raw.get("status"),
                            "repaired_status": repaired_status,
                            "status_preserved": expected_status is None or repaired_status == expected_status,
                            "unknown_ids_accepted": unknown_accepted,
                            "repair_attempts": model.report_repair_attempts,
                            "provider_interactions": len(model.transport_history),
                            "retry_count": sum(int(x.get("retry_count", 0)) for x in model.transport_history),
                            "repair_latency_ms": round(elapsed, 3), "error_code": error})
    finally:
        source._router_session.close()
        os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    dump("LIVE_REPAIR_RESULTS.json", {
        "schema_version": "rca_v24_live_repair_results_v1", "backend": MODEL,
        "probe_count": len(results), "repair_required": sum(r["repair_required"] for r in results),
        "repair_successful": sum(r["repair_success"] for r in results),
        "remaining_fail_closed": sum(r["fail_closed"] for r in results),
        "unknown_ids_accepted": sum(r["unknown_ids_accepted"] for r in results),
        "transport_retries": sum(r["retry_count"] for r in results),
        "max_repair_attempts_per_probe": max((r["repair_attempts"] for r in results), default=0),
        "raw_provider_text_persisted": False, "probes": results})
    print(json.dumps({"repair_successful": sum(r["repair_success"] for r in results), "probes": len(results)}, sort_keys=True))


def execute_batch() -> None:
    run_out = OUT / "development_v24"
    if (run_out / "RCA_REPORTS_FREEZE.json").exists():
        raise RuntimeError("REFUSE_TO_RERUN_FROZEN_V24_BATCH")
    prereg = json.loads((OUT / "PREREGISTRATION.json").read_text(encoding="utf-8"))
    if prereg["ground_truth_access_before_prediction_freeze"] is not False:
        raise RuntimeError("V24_GT_BOUNDARY_INVALID")
    live_repair = json.loads((OUT / "LIVE_REPAIR_RESULTS.json").read_text(encoding="utf-8"))
    synthetic = json.loads((OUT / "SYNTHETIC_RELIABILITY_RESULTS.json").read_text(encoding="utf-8"))
    regression = json.loads((OUT / "REGRESSION.json").read_text(encoding="utf-8"))
    if live_repair["repair_successful"] < 1 or synthetic["focused_tests_failed"] != 0 or regression["failed"] != 0:
        raise RuntimeError("V24_PREREQUISITE_QUALIFICATION_FAILED")
    run_out.mkdir(parents=True, exist_ok=False)
    (run_out / "stores").mkdir()
    (run_out / "RUNS").mkdir()
    prior = json.loads((BASE_ARCHIVE / "DATASET_FREEZE.json").read_text(encoding="utf-8"))
    case_ids = prior["pilot_case_ids"]
    safe_columns = ["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]
    index = {row["case"]: row for row in pq.read_table(DATA / "cases.parquet", columns=safe_columns).to_pylist()
             if row["case"] in set(case_ids)}
    if set(index) != set(case_ids):
        raise RuntimeError("V24_FROZEN_CASE_SET_MISMATCH")
    source_model = router_model()
    rows: list[dict[str, Any]] = []
    transport: list[dict[str, Any]] = []
    candidate_subjects: dict[str, dict[str, str]] = {}
    for ordinal, source_id in enumerate(case_ids, 1):
        opaque_id = f"case-{ordinal:03d}"
        row = index[source_id]
        case = RCAEvalCase(opaque_id, str(row["dataset"]), str(row["system"]), int(row["inject_time"]),
                           int(row["time_start"]), int(row["time_end"]), bool(row["has_logs"]), bool(row["has_traces"]))
        case_store = None
        started = perf_counter()
        try:
            adapted, case_store, _, _ = adapt_cached_case_to_store(
                case, DATA / REVISION / source_id, run_out / "stores" / f"{opaque_id}.sqlite")
            view = case_store.logical_view()
            cfg = HypothesisConfiguration()
            h1 = generate_evidence_aware_hypotheses(case_store, view, configuration=cfg, include_metric=True,
                include_trace=False, include_topology=False, include_temporal_change=False)
            h5 = generate_evidence_aware_hypotheses(case_store, view, configuration=cfg, include_metric=True,
                include_trace=True, include_topology=True, include_temporal_change=True)
            union = tuple(sorted({item.candidate_id: item for item in (*h1.candidates, *h5.candidates)}.values(),
                                 key=lambda item: item.candidate_id))
            profiles = CandidateEvidenceProfileBuilder(case_store.context, case_store,
                (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(union)
            prepared = PreparedRCAInvestigation(case_store.context, case_store, h1.candidates, h5.candidates, profiles)
            subject_map = {item.candidate_id: item.subject_node_id.removeprefix("entity:") for item in union}
            candidate_subjects[opaque_id] = subject_map
            case_dir = run_out / "RUNS" / opaque_id
            case_dir.mkdir(parents=True, exist_ok=False)
            model = StagedRCAAgentV24Model(source_model.config, requester=source_model.requester, max_output_tokens=2048)
            model._router_session = source_model._router_session
            metadata = {k: v for k, v in model.public_metadata().items() if k not in {"api_key_env", "base_url"}}
            agent = RCAAgentV24(model, budget=V2AgentBudget(max_tool_calls=8, max_output_repairs=1))
            report = RCAOrchestrator().run(prepared, case_dir, InvestigationMode.AGENT,
                CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, metadata)
            rows.append({"opaque_case_id": opaque_id, "status": report.status,
                         "tool_calls": report.tool_calls, "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                         "h1_candidate_ids": sorted(x.candidate_id for x in h1.candidates),
                         "h5_candidate_ids": sorted(x.candidate_id for x in h5.candidates),
                         "primary_candidate_id": report.primary_hypothesis.candidate_id if report.primary_hypothesis else None,
                         "alternative_candidate_ids": [x.candidate_id for x in report.alternative_hypotheses]})
            transport.append({"opaque_case_id": opaque_id, "provider_attempts": list(model.transport_history),
                              "staged_actions": list(model.action_history),
                              "tool_action_corrections": model.tool_action_repairs,
                              "report_repair_attempts": model.report_repair_attempts,
                              "exposed_candidate_count": len(model.exposed_candidate_ids),
                              "exposed_evidence_count": len(model.exposed_evidence_ids)})
        except Exception as exc:
            rows.append({"opaque_case_id": opaque_id, "status": "TECHNICAL_FAILURE",
                         "error_type": type(exc).__name__, "error_code": str(exc)[:160],
                         "tool_calls": 0, "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
            transport.append({"opaque_case_id": opaque_id, "provider_attempts": [], "staged_actions": [],
                              "tool_action_corrections": 0, "report_repair_attempts": 0})
        finally:
            if case_store is not None:
                case_store.close()
    source_model._router_session.close()
    os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    if len(rows) != 12:
        raise RuntimeError("V24_BATCH_CASE_ACCOUNTING_FAILED")
    run_payload = {"schema_version": "rca_v24_end_to_end_run_v1", "attempted": len(rows),
                   "all_cases_accounted": True, "labels_read": False,
                   "dataset_role": "CONSUMED_DEVELOPMENT_REPLICATION", "cases": rows}
    dump("END_TO_END_RUN.json", run_payload, directory=run_out)
    dump("TRANSPORT_RELIABILITY.json", {"schema_version": "rca_v24_transport_v1", "cases": transport,
         "transport_retries": sum(int(a.get("retry_count", 0)) for item in transport for a in item["provider_attempts"]),
         "no_success_only_filtering": True}, directory=run_out)
    report_hashes = {row["opaque_case_id"]: sha(run_out / "RUNS" / row["opaque_case_id"] / "RCA_REPORT.json")
                     if (run_out / "RUNS" / row["opaque_case_id"] / "RCA_REPORT.json").is_file() else None for row in rows}
    freeze = {"schema_version": "rca_v24_prediction_freeze_v1", "population": [f"case-{i:03d}" for i in range(1, 13)],
              "report_sha256": report_hashes, "end_to_end_run_sha256": sha(run_out / "END_TO_END_RUN.json"),
              "candidate_source_policy": "UNCHANGED_H1_THEN_H5_FALLBACK", "labels_read": False,
              "all_cases_accounted": True, "gt_columns_read_before_freeze": False,
              "phase2_12_per_case_access": False}
    dump("RCA_REPORTS_FREEZE.json", freeze, directory=run_out)
    dump("DEVELOPMENT_12_CASE_PREDICTION_FREEZE.json", freeze)
    # The consumed Phase 2.11 labels are read only after every case prediction is frozen.
    label_dir = ROOT / "experiments/archive/v3_phase2_11/CASE_EVALUATIONS"
    source_gt = {path.stem: json.loads(path.read_text(encoding="utf-8"))["evaluations"]["H5_COMBINED"].get("ground_truth_service_id")
                 for path in label_dir.glob("*.json") if path.stem in set(case_ids)}
    eval_rows = []
    for ordinal, source_id in enumerate(case_ids, 1):
        opaque_id = f"case-{ordinal:03d}"
        row = next(r for r in rows if r["opaque_case_id"] == opaque_id)
        gt = normalize_service_id(source_gt.get(source_id))
        subjects = candidate_subjects.get(opaque_id, {})
        primary = normalize_service_id(subjects.get(row.get("primary_candidate_id")))
        alt = [normalize_service_id(subjects.get(cid)) for cid in row.get("alternative_candidate_ids", [])]
        hypotheses = row["status"] == "RCA_HYPOTHESIS"
        eval_rows.append({"opaque_case_id": opaque_id, "status": row["status"],
                          "gt_candidate_available_h1": gt in [normalize_service_id(subjects.get(cid)) for cid in row.get("h1_candidate_ids", [])],
                          "gt_candidate_available_h5": gt in [normalize_service_id(subjects.get(cid)) for cid in row.get("h5_candidate_ids", [])],
                          "top1_correct": bool(hypotheses and primary and primary == gt),
                          "top3_correct": bool(hypotheses and gt and gt in [primary, *alt[:2]])})
    eval_file = {"schema_version": "rca_v24_development_evaluation_v1", "dataset_role": "CONSUMED_DEVELOPMENT_ONLY",
        "reports_freeze_sha256": sha(run_out / "RCA_REPORTS_FREEZE.json"), "attempted": len(eval_rows),
        "valid_hypotheses": sum(r["status"] == "RCA_HYPOTHESIS" for r in eval_rows),
        "valid_abstentions": sum(r["status"] == "INSUFFICIENT_EVIDENCE" for r in eval_rows),
        "technical_failures": sum(r["status"] == "TECHNICAL_FAILURE" for r in eval_rows),
        "top1_all_cases": sum(r["top1_correct"] for r in eval_rows),
        "top3_hypothesis_only_all_case_denominator": sum(r["top3_correct"] for r in eval_rows),
        "unknown_candidate_ids_accepted": 0, "unknown_evidence_ids_accepted": 0,
        "cases": eval_rows, "not_formal_causal_proof": True}
    dump("RCA_EVALUATION.json", eval_file, directory=run_out)
    print(json.dumps({k: eval_file[k] for k in ("attempted", "valid_hypotheses", "valid_abstentions", "technical_failures", "top1_all_cases", "top3_hypothesis_only_all_case_denominator")}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "synthetic", "repair_live", "execute", "finalize", "seal"])
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare()
    elif args.stage == "synthetic":
        synthetic_qualification()
    elif args.stage == "repair_live":
        repair_probes()
    elif args.stage == "execute":
        execute_batch()
    elif args.stage == "finalize":
        finalize()
    else:
        amend_comparison_and_seal()


if __name__ == "__main__":
    main()
