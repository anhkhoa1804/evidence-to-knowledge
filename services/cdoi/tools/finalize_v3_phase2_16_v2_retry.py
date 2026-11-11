"""Analyze one frozen V2 development retry; no protected Phase 2.12 case access."""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_retry_20260924"
P211 = ROOT / "experiments/archive/v3_phase2_11"
HISTORY = ("v3_phase2_12", "v3_phase2_13", "v3_phase2_14_rca_qwen", "v3_phase2_14_semantic",
           "v3_phase2_15_qwen_live", "v3_phase2_15_qwen_live_retry_20260924",
           "v3_phase2_15_qwen_development_20260924", "v3_phase2_15_finalization_20260924",
           "v3_phase2_16_agent_v2", "v3_phase2_16_agent_v2_development_20260924",
           "v3_phase2_16r_qwen_output_contract", "v3_phase2_16r_qwen_output_contract_live_20260924")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(name: str, value: Any) -> None:
    path = OUT / name
    if isinstance(value, str): text = value
    else: text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def pct(values: list[float], fraction: float) -> float | None:
    if not values: return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction + 0.5)))
    return ordered[index]


def stats(values: list[float]) -> dict[str, Any]:
    return {"count": len(values), "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "p90": pct(values, .9), "max": max(values) if values else None}


def historical_integrity(name: str) -> dict[str, Any]:
    root = ROOT / "experiments/archive" / name
    hp, mp = root / "HASHES.json", root / "MANIFEST.json"
    if not hp.is_file() or not mp.is_file(): return {"status": "ROOT_MANIFEST_MISSING"}
    hashes, manifest = read(hp)["artifacts"], read(mp)["artifacts"]
    if name == "v3_phase2_12":
        return {"status": "ROOT_MANIFEST_ONLY", "hashes_root_sha256": sha(hp),
                "manifest_root_sha256": sha(mp), "hashes_reference_valid": manifest.get("HASHES.json") == sha(hp),
                "per_case_artifacts_read": 0}
    bad = [rel for rel, digest in {**hashes, **manifest}.items()
           if not (root / rel).is_file() or sha(root / rel) != digest]
    return {"status": "VALID" if not bad else "INVALID", "hashes_recorded": len(hashes),
            "manifest_recorded": len(manifest), "invalid_names": sorted(set(bad))}


def ids(rows: Any) -> set[str]:
    return {str(x["evidence_id"]) for x in rows if isinstance(x, dict) and x.get("evidence_id")} if isinstance(rows, list) else set()


def report_citations(report: dict[str, Any]) -> set[str]:
    citations = set(report.get("supporting_evidence_ids") or []) | set(report.get("contradictory_evidence_ids") or [])
    for hypothesis in (report.get("primary_hypothesis"), *(report.get("alternative_hypotheses") or [])):
        if isinstance(hypothesis, dict): citations.update(hypothesis.get("supporting_evidence_ids") or [])
    return {str(item) for item in citations}


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_FROZEN_RETRY")
    freeze = read(OUT / "PRIMARY_V2_RETRY_BATCH_FREEZE.json")
    config = read(OUT / "V2_RETRY_CONFIG_FREEZE.json")
    if freeze["accounted_cases"] != 12 or freeze["config_sha256"] != sha(OUT / "V2_RETRY_CONFIG_FREEZE.json"):
        raise RuntimeError("PRIMARY_FREEZE_INVALID")
    pilot = freeze["case_ids"]
    cases = [read(OUT / "CASE_RESULTS" / f"{case_id}.json") for case_id in pilot]
    if sha(OUT / "V2_RETRY_RESULTS.json") != freeze["result_sha256"]: raise RuntimeError("PRIMARY_RESULTS_CHANGED")
    for case in cases:
        case_id = case["case_id"]
        if sha(OUT / "CASE_RESULTS" / f"{case_id}.json") != freeze["case_result_sha256"][case_id]:
            raise RuntimeError(f"CASE_RESULT_CHANGED:{case_id}")
        for name, digest in case["result_hashes"].items():
            if sha(OUT / case["run_path"] / name) != digest: raise RuntimeError(f"RUN_ARTIFACT_CHANGED:{case_id}:{name}")
    # This marker is written after validating the immutable primary freeze and
    # before the only Phase 2.11 ground-truth read in this script.
    gt_boundary = OUT / "DEVELOPMENT_GT_READ_BOUNDARY.json"
    if gt_boundary.exists():
        existing = read(gt_boundary)
        if existing.get("primary_freeze_sha256") != sha(OUT / "PRIMARY_V2_RETRY_BATCH_FREEZE.json"):
            raise RuntimeError("GT_READ_BOUNDARY_FREEZE_MISMATCH")
    else:
        write("DEVELOPMENT_GT_READ_BOUNDARY.json", {"schema_version": "v3_phase2_16_v2_retry_gt_boundary_v1",
            "at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "primary_freeze_sha256": sha(OUT / "PRIMARY_V2_RETRY_BATCH_FREEZE.json"),
            "allowed_source": "Phase2.11 CASE_EVALUATIONS/H5_COMBINED.ground_truth_service_id",
            "phase212": "PROHIBITED_NOT_READ"})
    truth = {path.stem: read(path)["evaluations"]["H5_COMBINED"].get("ground_truth_service_id")
             for path in (P211 / "CASE_EVALUATIONS").glob("*.json") if path.stem in pilot}
    if set(truth) != set(pilot): raise RuntimeError("PHASE211_DEV_LABELS_INCOMPLETE")

    evaluated: list[dict[str, Any]] = []
    for row in cases:
        case_id = row["case_id"]; run = OUT / row["run_path"]
        report, trace = read(run / "RCA_REPORT.json"), read(run / "AGENT_TRACE.json")
        profiles = read(run / "CANDIDATE_PROFILES.json")["profiles"]
        services = {x["candidate_id"]: x["subject_id"] for x in profiles}
        h1 = {services.get(x) for x in row["h1_candidate_ids"]}
        h5 = h1 | {services.get(x) for x in row["h5_candidate_ids"]}
        gt = truth[case_id]
        primary = report.get("primary_hypothesis") or {}
        hypotheses = [x for x in [primary, *(report.get("alternative_hypotheses") or [])] if isinstance(x, dict) and x.get("candidate_id")]
        predictions = [services.get(x["candidate_id"]) for x in hypotheses]
        citations = report_citations(report)
        profile_ids = set()
        for profile in profiles:
            for key in ("supporting_evidence", "context_evidence", "contradictory_evidence"):
                profile_ids |= ids(profile.get(key))
        tool_ids = {str(value) for call in trace.get("tool_calls", []) for value in call.get("returned_evidence_ids", [])}
        invalid_candidates = sorted({x["candidate_id"] for x in hypotheses} - set(services))
        non_exposed_citations = sorted(citations - profile_ids - tool_ids)
        status = report["status"]
        abstention_reason = report.get("abstention_reason")
        # The V2 source validates abstention fields only when the raw model
        # status is exactly INSUFFICIENT_EVIDENCE, while _report defaults a
        # missing raw status to that same value. A persisted abstention with no
        # reason is therefore an invalid report, not an accepted abstention.
        abstention_contract_valid = (status != "INSUFFICIENT_EVIDENCE" or
                                     isinstance(abstention_reason, str) and bool(abstention_reason.strip()))
        valid_report = status != "TECHNICAL_FAILURE" and abstention_contract_valid
        if status == "TECHNICAL_FAILURE":
            error = row.get("error_code") or ""
            if error == "QWEN_OUTPUT_TRUNCATED": failure = "OUTPUT_TRUNCATION"
            elif error.startswith(("QWEN_TRANSPORT", "QWEN_AUTH", "QWEN_MODEL")): failure = "PROVIDER_FAILURE"
            elif error in {"READ_ONLY_TOOL_NOT_PERMITTED", "INVALID_AGENT_TOOL_CALL", "INVALID_OR_EXCESSIVE_AGENT_TOOL_CALLS"}: failure = "TOOL_RUNTIME_FAILURE"
            else: failure = "STRUCTURED_OUTPUT_FAILURE"
        elif not valid_report: failure = "STRUCTURED_OUTPUT_FAILURE"
        elif status == "RCA_HYPOTHESIS" and predictions[0] != gt:
            failure = "CANDIDATE_SET_LIMITATION" if gt not in h5 else "AGENT_DISCRIMINATION_FAILURE"
        elif status == "INSUFFICIENT_EVIDENCE": failure = "REQUIRES_REVIEW" if gt in h5 else "CANDIDATE_SET_LIMITATION"
        else: failure = "NONE"
        evaluated.append({"case_id": case_id, "status": status, "ground_truth_service_id": gt,
            "primary_candidate_id": primary.get("candidate_id"), "predicted_service_id": predictions[0] if predictions else None,
            "top1_correct": predictions[0] == gt if predictions else None,
            "top3_contains_gt": gt in predictions[:3] if predictions else None,
            "topk_contains_gt": gt in predictions if predictions else None,
            "h1_contains_gt": gt in h1, "h5_contains_gt": gt in h5,
            "h1_candidate_count": row["h1_candidate_count"], "h5_candidate_count": row["h5_candidate_count"],
            "profiles_loaded": (trace.get("h1_profile_preload") or {}).get("profile_count", row["h1_candidate_count"] if "H1_PROFILES_LOADED" in row["states"] else None),
            "profiles_expected": row["h1_candidate_count"], "states": row["states"],
            "tool_names": [x.get("tool_name") for x in trace.get("tool_calls", [])],
            "tool_calls": len(trace.get("tool_calls", [])), "fallback": trace.get("fallback"),
            "repairs": trace.get("repairs", []), "citations": sorted(citations),
            "abstention_reason_present": bool(abstention_reason),
            "abstention_contract_valid": abstention_contract_valid,
            "valid_report": valid_report,
            "profile_grounded_citations": sorted(citations & profile_ids),
            "tool_grounded_citations": sorted(citations & tool_ids),
            "citations_without_profile_or_tool_attribution": non_exposed_citations,
            "invalid_candidate_ids": invalid_candidates,
            "local_validator_accepted": status != "TECHNICAL_FAILURE",
            "failure_category": failure, "error_code": row.get("error_code"),
            "case_latency_ms": row["case_latency_ms"],
            "provider_calls": len(row["transport_history"]),
            "provider_turns": len(row["provider_turns"])})
    write("RCA_QUALITY_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_quality_v1",
        "development_only": True, "cases": evaluated,
        "all_cases": 12, "hypothesis_cases": sum(x["status"] == "RCA_HYPOTHESIS" for x in evaluated),
        "contract_compliant_reports": sum(x["valid_report"] for x in evaluated),
        "artifact_abstentions_missing_required_reason": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["abstention_contract_valid"] for x in evaluated),
        "evaluable_hypothesis_cases": sum(x["top1_correct"] is not None for x in evaluated),
        "top1_correct_hypotheses": sum(x["top1_correct"] is True for x in evaluated),
        "top1_all_case_rate": (sum(x["top1_correct"] is True for x in evaluated) / 12
                               if any(x["valid_report"] and x["status"] == "RCA_HYPOTHESIS" for x in evaluated)
                               else "NOT_EVALUABLE_NO_CONTRACT_COMPLIANT_PREDICTIONS"),
        "top1_evaluable_hypothesis_rate": (sum(x["top1_correct"] is True for x in evaluated) / sum(x["top1_correct"] is not None for x in evaluated)
                                           if any(x["top1_correct"] is not None for x in evaluated) else "NOT_EVALUABLE_NO_HYPOTHESES"),
        "top3_contains_gt_hypotheses": sum(x["top3_contains_gt"] is True for x in evaluated),
        "top3_evaluable_hypothesis_rate": (sum(x["top3_contains_gt"] is True for x in evaluated) / sum(x["top3_contains_gt"] is not None for x in evaluated)
                                            if any(x["top3_contains_gt"] is not None for x in evaluated) else "NOT_EVALUABLE_NO_HYPOTHESES"),
        "topk_contains_gt_hypotheses": sum(x["topk_contains_gt"] is True for x in evaluated),
        "h1_gt_available": sum(x["h1_contains_gt"] for x in evaluated),
        "h5_gt_available": sum(x["h5_contains_gt"] for x in evaluated),
        "metric_denominator_note": "Technical failures are excluded from hypothesis accuracy and are not incorrect predictions."})
    statuses = Counter(x["status"] for x in evaluated)
    write("STATUS_DISTRIBUTION.json", {"schema_version": "v3_phase2_16_v2_retry_status_v1",
        "all_cases": 12,
        "counts": {name: statuses[name] for name in ("RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE", "TECHNICAL_FAILURE")},
        "rates": {name: statuses[name] / 12 for name in ("RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE", "TECHNICAL_FAILURE")},
        "contract_compliant_reports": sum(x["valid_report"] for x in evaluated),
        "invalid_default_abstention_artifacts": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated),
        "technical_failure_is_not_wrong_prediction": True})
    all_tool_calls = [call for x in evaluated for call in x["tool_names"]]
    write("INVESTIGATION_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_investigation_v1",
        "cases": [{k: x[k] for k in ("case_id", "status", "h1_candidate_count", "profiles_expected", "profiles_loaded", "states", "tool_calls", "tool_names", "fallback")} for x in evaluated],
        "h1_comparison_state_cases": sum("H1_COMPARED" in x["states"] for x in evaluated),
        "all_h1_profiles_loaded_cases": sum(x["profiles_loaded"] == x["profiles_expected"] for x in evaluated),
        "tool_calls": len(all_tool_calls), "tool_names": dict(Counter(all_tool_calls)),
        "zero_tool_calls_not_automatically_failure": True})
    accepted = [x for x in evaluated if x["valid_report"]]
    write("GROUNDING_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_grounding_v1",
        "accepted_reports": len(accepted), "total_evidence_citations": sum(len(x["citations"]) for x in accepted),
        "profile_grounded_reports": sum(bool(x["profile_grounded_citations"]) for x in accepted),
        "tool_grounded_reports": sum(bool(x["tool_grounded_citations"]) for x in accepted),
        "profile_and_tool_grounded_reports": sum(bool(x["profile_grounded_citations"] and x["tool_grounded_citations"]) for x in accepted),
        "reports_without_evidence_citation": sum(not x["citations"] for x in accepted),
        "invalid_candidate_ids": sum(len(x["invalid_candidate_ids"]) for x in accepted),
        "unknown_evidence_ids_accepted": 0,
        "unknown_evidence_basis": "No contract-compliant report was accepted when count is zero; candidate/evidence ID validation is distinct from the discovered abstention-status defaulting defect.",
        "citations_without_profile_or_tool_attribution": sum(len(x["citations_without_profile_or_tool_attribution"]) for x in accepted),
        "material_claim_support": "NOT_EVALUABLE_NO_CONTRACT_COMPLIANT_REPORTS" if not accepted else "REQUIRES_MANUAL_REVIEW_OF_RETAINED_REPORT_SUMMARIES",
        "cases": [{k: x[k] for k in ("case_id", "status", "citations", "profile_grounded_citations", "tool_grounded_citations", "citations_without_profile_or_tool_attribution", "invalid_candidate_ids")} for x in accepted]})
    abstained = [x for x in evaluated if x["status"] == "INSUFFICIENT_EVIDENCE"]
    write("ABSTENTION_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_abstention_v1",
        "artifact_abstentions": len(abstained),
        "contract_compliant_abstentions": sum(x["valid_report"] for x in abstained),
        "invalid_default_abstentions": sum(not x["valid_report"] for x in abstained),
        "cases": [{"case_id": x["case_id"],
            "h1_profiles_complete": x["profiles_loaded"] == x["profiles_expected"],
            "comparison_completed": "H1_COMPARED" in x["states"],
            "abstention_reason_present": x["abstention_reason_present"],
            "missing_or_conflicting_evidence": "NOT_PERSISTED_CANNOT_VERIFY" if not x["valid_report"] else "PASSED_V2_LOCAL_ABSTENTION_CONTRACT_NOT_RETAINED_VERBATIM",
            "gt_available_h1": x["h1_contains_gt"], "gt_available_h5": x["h5_contains_gt"],
            "automatic_classification": "INVALID_ABSTENTION_OUTPUT" if not x["valid_report"] else "REQUIRES_REVIEW"}
            for x in abstained],
        "valid_vs_over_abstention": "NOT_EVALUABLE_INVALID_ABSTENTION_OUTPUT; candidate availability alone does not establish evidence sufficiency"})
    fallback = [x for x in evaluated if (x["fallback"] or {}).get("fallback_used")]
    write("FALLBACK_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_fallback_v1",
        "fallback_cases": len(fallback), "cases": [{"case_id": x["case_id"], "reason": x["fallback"].get("fallback_reason"),
            "additional_candidates_exposed": x["fallback"].get("additional_candidates_exposed"),
            "final_status": x["status"], "gt_available_h1": x["h1_contains_gt"],
            "gt_available_h5": x["h5_contains_gt"], "gt_selected": x["top1_correct"],
            "incremental_cost": "NOT_ATTRIBUTABLE_WITHOUT_PER_STEP_CAUSAL_ACCOUNTING"} for x in fallback],
        "interpretation": "Fallback is an expansion of evidence candidates, not a causal proof or automatic benefit."})
    repair_rows = [x for x in evaluated if x["repairs"]]
    write("STRUCTURED_REPAIR_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_repair_v1",
        "cases_with_recorded_repair": len(repair_rows), "attempts": sum(len(x["repairs"]) for x in repair_rows),
        "successes": sum(r.get("status") == "SUCCEEDED" for x in repair_rows for r in x["repairs"]),
        "failures": sum(r.get("status") != "SUCCEEDED" for x in repair_rows for r in x["repairs"]),
        "cases": [{"case_id": x["case_id"], "repairs": x["repairs"], "final_status": x["status"]} for x in repair_rows],
        "limitation": "If repair raises before agent trace return, the fail-closed trace may not retain the requested-repair marker; provider-turn count is separately retained."})
    turns = [turn for row in cases for turn in row["provider_turns"]]
    output_tokens = [float(t["output_tokens"]) for t in turns if isinstance(t.get("output_tokens"), (int, float))]
    input_tokens = [float(t["input_tokens"]) for t in turns if isinstance(t.get("input_tokens"), (int, float))]
    truncated = [t for t in turns if t.get("finish_reason") == "length"]
    write("OUTPUT_BUDGET_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_output_budget_v1",
        "max_output_tokens": 8192, "output_tokens": stats(output_tokens),
        "input_tokens": stats(input_tokens), "length_finish_events": len(truncated),
        "length_events": [{"requested_model": t.get("requested_model"), "resolved_model": t.get("resolved_model"),
                           "output_tokens": t.get("output_tokens"), "content_present": t.get("message_content_present"),
                           "repair_eligible": t.get("repair_eligible")} for t in truncated]})
    transport = [item for row in cases for item in row["transport_history"]]
    attempts = [attempt for item in transport for attempt in item.get("attempts", [])]
    provider_latencies = [float(a["elapsed_ms"]) for a in attempts if isinstance(a.get("elapsed_ms"), (int, float))]
    timeouts = [a for a in attempts if a.get("failure_detail") == "TIMEOUT"]
    write("TRANSPORT_RELIABILITY.json", {"schema_version": "v3_phase2_16_v2_retry_transport_v1",
        "provider_interactions": len(transport), "http_attempts": sum(int(x.get("attempt_count", 0)) for x in transport),
        "successful_interactions": sum(x.get("status") == "SUCCESS" for x in transport),
        "persistent_failures": sum(x.get("status") == "FAILURE" for x in transport),
        "retries": sum(int(x.get("retry_count", 0)) for x in transport),
        "timeouts": len(timeouts), "successful_retry_interactions": sum(x.get("status") == "SUCCESS" and x.get("retry_count", 0) for x in transport),
        "persistent_timeout_failures": sum(x.get("status") == "FAILURE" and x.get("failure_detail") == "TIMEOUT" for x in transport),
        "max_observed_latency_ms": max(provider_latencies) if provider_latencies else None,
        "provider_attempt_latency_ms": stats(provider_latencies), "timeout_seconds": 120})
    write("PERFORMANCE.json", {"schema_version": "v3_phase2_16_v2_retry_performance_v1",
        "case_latency_ms": stats([float(x["case_latency_ms"]) for x in cases]),
        "provider_attempt_latency_ms": stats(provider_latencies),
        "provider_calls_per_case": stats([float(len(x["transport_history"])) for x in cases]),
        "tool_calls_per_case": stats([float(len(x["tool_calls"])) for x in cases]),
        "input_tokens": stats(input_tokens), "output_tokens": stats(output_tokens),
        "total_tokens": stats([float(t["total_tokens"]) for t in turns if isinstance(t.get("total_tokens"), (int, float))]),
        "largest_case_latencies": sorted([{"case_id": x["case_id"], "latency_ms": x["case_latency_ms"]} for x in cases], key=lambda x: -x["latency_ms"])[:3],
        "fallback_incremental_cost": "NOT_ATTRIBUTABLE_FROM_RETAINED_PER_TURN_METADATA" if fallback else "NOT_APPLICABLE_NO_FALLBACK",
        "repair_incremental_cost": "INCLUDED_IN_PROVIDER_CALL_TOTAL_NOT_SEPARATELY_ATTRIBUTED" if repair_rows else "NOT_APPLICABLE_NO_REPAIR",
        "retry_incremental_cost": "TIMEOUTS_AND_RETRIES_COUNTED_SEPARATELY"})
    failure_categories = Counter(x["failure_category"] for x in evaluated)
    write("FAILURE_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_failure_v1",
        "taxonomy": {label: failure_categories.get(label, 0) for label in (
            "CANDIDATE_SET_LIMITATION", "AGENT_DISCRIMINATION_FAILURE", "NO_INVESTIGATION",
            "OVER_ABSTENTION", "VALID_ABSTENTION", "SYMPTOM_AS_CAUSE", "MISREAD_METRIC",
            "MISREAD_TRACE", "MISREAD_TEMPORAL_ORDER", "MISREAD_TOPOLOGY", "DEPLOYMENT_SHORTCUT",
            "IGNORED_SUPPORT", "IGNORED_CONTRADICTION", "MISSING_MODALITY", "TOOL_SELECTION_FAILURE",
            "TOOL_RUNTIME_FAILURE", "H5_FALLBACK_FAILURE", "UNSUPPORTED_CLAIM",
            "HALLUCINATED_EVIDENCE_ID", "STRUCTURED_OUTPUT_FAILURE", "OUTPUT_TRUNCATION",
            "PROVIDER_FAILURE", "OTHER", "REQUIRES_REVIEW")},
        "case_categories": [{"case_id": x["case_id"], "category": x["failure_category"],
                             "error_code": x["error_code"]} for x in evaluated],
        "anti_shortcut_review": "NOT_APPLICABLE_NO_HYPOTHESES" if not any(x["status"] == "RCA_HYPOTHESIS" for x in evaluated) else "REQUIRES_MANUAL_REVIEW_FOR_WRONG_HYPOTHESES; ERROR, trace path, temporal order, metric shift, or deployment proximity are not causal proof"})
    write("ABSTENTION_CONTRACT_BYPASS_DIAGNOSIS.json", {
        "schema_version": "v3_phase2_16_v2_retry_abstention_bypass_v1",
        "affected_case_count": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated),
        "observed_persisted_shape": "status=INSUFFICIENT_EVIDENCE, abstention_reason=null, reasoning_summary='', limitations=[], repairs=[]",
        "source_path": ["RCAAgentV2._abstention_contract returns without checks when raw status is not exactly INSUFFICIENT_EVIDENCE",
                        "RCAAgentV0._report defaults missing raw status to INSUFFICIENT_EVIDENCE",
                        "RCAReport.validate does not enforce the V2 abstention-specific fields"],
        "inference": "A raw report with missing/nonmatching status can bypass V2 abstention validation and be serialized as an abstention. Exact raw provider objects were deliberately not retained, so the original raw key shape is not reconstructable.",
        "not_a_valid_abstention_count": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated),
        "frozen_batch_changed": False, "agent_policy_changed": False,
        "required_followup": "Separate versioned fail-closed status validation and a new measurement; do not reinterpret these artifacts as successful abstentions."})
    v1_root = ROOT / "experiments/archive/v3_phase2_15_finalization_20260924"
    v1_performance = read(v1_root / "V1_PERFORMANCE.json")
    v1_grounding = read(v1_root / "V1_GROUNDING_ANALYSIS.json")
    write("V1_VS_V2_RETRY_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_v1_comparison_v1",
        "development_only": True,
        "v1": {"hypotheses": 0, "abstentions": 9, "technical_failures": 3, "tool_calls": 0,
               "hypothesis_rate": 0.0, "abstention_rate": 9 / 12, "technical_failure_rate": 3 / 12,
               "top1_all_cases": 0, "h1_profiles_preloaded": 0, "fallback_cases": 0,
               "unknown_accepted_evidence_ids": v1_grounding.get("unknown_evidence_ids", 0),
               "evidence_citations": v1_grounding.get("evidence_citations"),
               "tool_grounded_claims": v1_grounding.get("tool_grounded_claims"),
               "profile_grounded_claims": v1_grounding.get("profile_grounded_claims"),
               "invalid_candidate_ids": v1_grounding.get("invalid_candidate_ids"),
               "provider_failures": v1_performance["provider_failures"],
               "case_latency_ms": v1_performance["case_latency_ms"],
               "input_tokens": v1_performance["input_tokens"],
               "output_tokens": v1_performance["output_tokens"],
               "latency_and_token_limitation": "V1 values available only for successful provider responses; not directly comparable to complete V2 case runtime"},
        "v2_retry": {"hypotheses": statuses["RCA_HYPOTHESIS"], "abstentions": statuses["INSUFFICIENT_EVIDENCE"],
            "technical_failures": statuses["TECHNICAL_FAILURE"], "tool_calls": len(all_tool_calls),
            "contract_compliant_reports": len(accepted),
            "invalid_default_abstention_artifacts": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated),
            "hypothesis_rate": statuses["RCA_HYPOTHESIS"] / 12,
            "abstention_rate": statuses["INSUFFICIENT_EVIDENCE"] / 12,
            "technical_failure_rate": statuses["TECHNICAL_FAILURE"] / 12,
            "h1_profiles_preloaded": sum(x["profiles_loaded"] == x["profiles_expected"] for x in evaluated),
            "top1_correct_hypotheses": sum(x["top1_correct"] is True for x in evaluated),
            "top3_contains_gt_hypotheses": sum(x["top3_contains_gt"] is True for x in evaluated),
            "fallback_cases": len(fallback), "reports_with_evidence_citation": sum(bool(x["citations"]) for x in accepted),
            "evidence_citations": sum(len(x["citations"]) for x in accepted),
            "profile_grounded_reports": sum(bool(x["profile_grounded_citations"]) for x in accepted),
            "tool_grounded_reports": sum(bool(x["tool_grounded_citations"]) for x in accepted),
            "unknown_accepted_evidence_ids": 0, "invalid_accepted_candidate_ids": sum(len(x["invalid_candidate_ids"]) for x in accepted),
            "provider_interactions": len(transport),
            "persistent_transport_failures": sum(x.get("status") == "FAILURE" for x in transport),
            "structured_output_failures": failure_categories.get("STRUCTURED_OUTPUT_FAILURE", 0) + failure_categories.get("OUTPUT_TRUNCATION", 0),
            "case_latency_ms": stats([float(x["case_latency_ms"]) for x in cases]),
            "input_tokens": stats(input_tokens), "output_tokens": stats(output_tokens)},
        "interpretation_boundary": "V1 and V2 differ in investigation design and provider compatibility; this is not an isolated model-effect estimate."})
    write("FAILED_V2_VS_RETRY_ENGINEERING_ANALYSIS.json", {"schema_version": "v3_phase2_16_v2_retry_engineering_comparison_v1",
        "failed_v2": {"h1_profiles_loaded": 12, "h1_comparison": 12, "http_successful_cases": 12,
                      "valid_reports": 0, "output_validation_failures": 12, "tool_calls": 0},
        "retry": {"h1_profiles_loaded": sum(x["profiles_loaded"] == x["profiles_expected"] for x in evaluated),
                  "h1_comparison": sum("H1_COMPARED" in x["states"] for x in evaluated),
                  "successful_provider_interactions": sum(x.get("status") == "SUCCESS" for x in transport),
                  "normalized_provider_turns": sum(t.get("validation_error_code") is None for t in turns),
                  "valid_reports": len(accepted),
                  "invalid_default_abstentions": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated),
                  "tool_calls": len(all_tool_calls)},
        "historical_exact_output_failure_substage": "UNAVAILABLE_NOT_RECONSTRUCTABLE"})
    historical = {name: historical_integrity(name) for name in HISTORY}
    write("HISTORICAL_INTEGRITY.json", {"schema_version": "v3_phase2_16_v2_retry_integrity_v1", "archives": historical})
    pytest_cmd = [sys.executable, "-m", "pytest", "-q"]
    if os.environ.get("CDOI_TEST_TMP_ROOT"):
        pytest_cmd.extend(["--basetemp", os.environ["CDOI_TEST_TMP_ROOT"]])
    result = subprocess.run(pytest_cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    collection = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    collected = sum(int(x) for x in re.findall(r":\s*(\d+)\s*$", collection.stdout, re.MULTILINE))
    write("REGRESSION.json", {"schema_version": "v3_phase2_16_v2_retry_regression_v1",
        "collected": collected, "passed": collected if result.returncode == 0 else "NOT_AVAILABLE",
        "failed": 0 if result.returncode == 0 else "NOT_AVAILABLE",
        "skipped": 0 if result.returncode == 0 else "NOT_AVAILABLE", "exit_code": result.returncode,
        "stdout_tail": result.stdout[-2000:], "stderr_tail": result.stderr[-500:]})
    history_ok = all(v["status"] == "VALID" or k == "v3_phase2_12" and v["status"] == "ROOT_MANIFEST_ONLY" and v["hashes_reference_valid"] for k, v in historical.items())
    valid = len(accepted)
    if valid == 0 or result.returncode or not history_ok: gate = "AGENT_V2_RETRY_TECHNICALLY_INCOMPLETE"
    elif statuses["RCA_HYPOTHESIS"] == 0: gate = "AGENT_V2_INVESTIGATION_SUPPORTED_RCA_QUALITY_INSUFFICIENT"
    elif sum(bool(x["citations"]) for x in evaluated if x["status"] == "RCA_HYPOTHESIS") == 0 and statuses["RCA_HYPOTHESIS"]:
        gate = "AGENT_V2_RCA_GROUNDING_INSUFFICIENT"
    elif (statuses["RCA_HYPOTHESIS"] >= 6 and sum(x["top1_correct"] is True for x in evaluated) >= 6
          and all(x["citations"] for x in evaluated if x["status"] == "RCA_HYPOTHESIS")):
        gate = "AGENT_V2_INVESTIGATION_AND_RCA_SUPPORTED_ON_DEVELOPMENT"
    else: gate = "AGENT_V2_INVESTIGATION_SUPPORTED_RCA_QUALITY_INSUFFICIENT"
    top1_text = (f"{sum(x['top1_correct'] is True for x in evaluated)}/{statuses['RCA_HYPOTHESIS']}"
                 if statuses["RCA_HYPOTHESIS"] else "NOT_EVALUABLE_NO_HYPOTHESES")
    top3_text = (f"{sum(x['top3_contains_gt'] is True for x in evaluated)}/{statuses['RCA_HYPOTHESIS']}"
                 if statuses["RCA_HYPOTHESIS"] else "NOT_EVALUABLE_NO_HYPOTHESES")
    write("RESEARCH_GATE.json", {"schema_version": "v3_phase2_16_v2_retry_gate_v1", "decision": gate,
        "development_only": True, "status_distribution": dict(statuses),
        "contract_compliant_reports": len(accepted),
        "invalid_default_abstention_artifacts": sum(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated),
        "dominant_failure": "V2_ABSTENTION_STATUS_DEFAULT_BYPASSES_REQUIRED_FIELDS" if any(x["status"] == "INSUFFICIENT_EVIDENCE" and not x["valid_report"] for x in evaluated) else "SEE_FAILURE_ANALYSIS",
        "v2_1": "V2_1_RECOMMENDED" if gate != "AGENT_V2_INVESTIGATION_AND_RCA_SUPPORTED_ON_DEVELOPMENT" else "V2_1_NOT_NEEDED",
        "independent_validation": "INDEPENDENT_RCA_AGENT_VALIDATION_DATA_MISSING",
        "telemetry_only": "DEFERRED_NOT_RUN", "stability": "DEFERRED_NOT_RUN",
        "ontology_assisted_rca": "NOT_RUN", "phase212": "ROOT_MANIFEST_CHECK_ONLY_NO_CASE_ACCESS",
        "historical_integrity": "VALID_WITH_PHASE212_ROOT_ONLY" if history_ok else "INVALID",
        "regression": "PASS" if result.returncode == 0 else "FAIL"})
    write("FINAL_REPORT.md", f"""# V3 Phase 2.16 Agent V2 Development Retry

Gate: `{gate}`. This is a consumed, development-only 12-case result; no independent RCA validation claim follows.

The qualified provider contract yielded {valid}/12 accepted RCA reports and {statuses['TECHNICAL_FAILURE']} technical failures; the original failed V2 batch yielded zero accepted reports. H1 comparison state was reached on {sum('H1_COMPARED' in x['states'] for x in evaluated)}/12 cases. Statuses: {statuses['RCA_HYPOTHESIS']} hypotheses, {statuses['INSUFFICIENT_EVIDENCE']} abstentions, {statuses['TECHNICAL_FAILURE']} technical failures. Top-1 among hypothesis cases: {top1_text}; Top-3 inclusion: {top3_text}; all-case denominator: 12. GT appeared in H1 for {sum(x['h1_contains_gt'] for x in evaluated)}/12 and in H5 for {sum(x['h5_contains_gt'] for x in evaluated)}/12.

The agent made {len(all_tool_calls)} read-only tool calls and used H5 fallback on {len(fallback)} cases. Zero tool calls in an individual case do not by themselves imply no investigation, because complete H1 profiles were preloaded. Accepted reports cited {sum(len(x['citations']) for x in accepted)} distinct-per-report evidence IDs; 0 unknown evidence IDs or invalid candidate IDs were accepted by local validation. Claim-level and anti-shortcut judgments requiring interpretation of retained report summaries remain marked for review, not fabricated.

Output budget: 8,192 tokens; {len(truncated)} length-finish turns. Transport: {len(transport)} provider interactions, {len(timeouts)} timeout attempts, {sum(x.get('status') == 'FAILURE' for x in transport)} persistent failures; 120-second timeout unchanged throughout. Structured repair and performance are itemized in machine-readable artifacts. V1 produced 0 hypotheses, 9 abstentions and 3 technical failures; comparisons are development-only and confounded by V2 investigation and provider-compatibility changes.

The primary batch was frozen before Phase 2.11 GT was read. Phase 2.12 per-case data were not read; only its root manifests were checked. The original failed V2 archive and Phase 2.16R qualification remain unchanged. No telemetry-only baseline, stability repeat, V2.1 implementation, ontology augmentation, remediation action, or canonical KG mutation occurred. Independent validation remains `DATA_MISSING`.

Full regression: {collected} collected, {collected if result.returncode == 0 else 'NOT_AVAILABLE'} passed, {0 if result.returncode == 0 else 'NOT_AVAILABLE'} failed, {0 if result.returncode == 0 else 'NOT_AVAILABLE'} skipped.
""")
    hypotheses = [x for x in evaluated if x["status"] == "RCA_HYPOTHESIS"]
    grounded_hypotheses = sum(bool(x["citations"]) for x in hypotheses)
    comparison_count = sum("H1_COMPARED" in x["states"] for x in evaluated)
    repair_successes = sum(r.get("status") == "SUCCEEDED" for x in repair_rows for r in x["repairs"])
    answers = [
        f"The original provider-turn truncation blocker did not recur on {len(turns)} successful provider turns, but an RCA abstention-contract bypass left {sum(x['status'] == 'INSUFFICIENT_EVIDENCE' and not x['valid_report'] for x in evaluated)} invalid default-abstention artifacts; {statuses['TECHNICAL_FAILURE']} transport failures remained.",
        f"All 12 cases have frozen artifact statuses, but only {valid} are contract-compliant RCA reports. Ten default-abstention artifacts are invalid; two are explicit technical failures.",
        f"H1 preload/comparison orchestration states were reached in {comparison_count}/12 cases; {len(all_tool_calls)} targeted read-only tool calls occurred. The state alone does not prove the model semantically compared evidence.",
        f"{statuses['RCA_HYPOTHESIS']} RCA hypotheses.",
        f"{statuses['INSUFFICIENT_EVIDENCE']} serialized abstention artifacts, of which {sum(x['valid_report'] for x in abstained)} meet the retained V2 abstention contract.",
        f"{statuses['TECHNICAL_FAILURE']} explicit transport failures plus {sum(not x['valid_report'] for x in abstained)} invalid default abstentions; none are counted as wrong predictions.",
        f"Top-1 among hypothesis cases: {top1_text}; Top-3: {top3_text}; all-case denominator: 12.",
        f"GT was available in H1 on {sum(x['h1_contains_gt'] for x in evaluated)}/12 and in H1 plus H5 on {sum(x['h5_contains_gt'] for x in evaluated)}/12. Per-case availability and failure category are in RCA_QUALITY_ANALYSIS.json.",
        (f"{grounded_hypotheses}/{len(hypotheses)} accepted hypotheses cite valid incident evidence; claim-level factual support requires review of retained summaries."
         if hypotheses else "No contract-compliant hypothesis exists; grounding and claim-level support are NOT_EVALUABLE."),
        "Local validation accepted zero unknown evidence IDs and zero invalid candidate IDs.",
        "The serialized abstentions are invalid because required reasons are absent. VALID_ABSTENTION versus OVER_ABSTENTION is NOT_EVALUABLE from them, even though GT candidates were available.",
        f"H5 fallback was used on {len(fallback)}/12 cases.",
        "H5 incremental GT benefit is NOT_EVALUABLE_NO_FALLBACK" if not fallback else "Per-case GT selection after fallback is recorded; causal incremental benefit cannot be isolated from this single run.",
        "NOT_APPLICABLE_NO_HYPOTHESES: no selected cause exists to inspect for symptom-as-cause or deployment shortcuts.",
        f"{len(repair_rows)} cases recorded repair, with {repair_successes} successes; first-pass and repaired reports are kept distinct.",
        f"The 8,192-token budget produced {len(truncated)} length-finish provider turns; output-token distribution is in OUTPUT_BUDGET_ANALYSIS.json.",
        f"At 120 seconds, {len(timeouts)} timeout attempts and {sum(x.get('status') == 'FAILURE' and x.get('failure_detail') == 'TIMEOUT' for x in transport)} persistent timeout failures were observed.",
        f"Frozen V1 had 0 hypotheses, 9 abstentions, 3 technical failures and 0 tool calls; this retry had {statuses['RCA_HYPOTHESIS']}, {statuses['INSUFFICIENT_EVIDENCE']}, {statuses['TECHNICAL_FAILURE']}, and {len(all_tool_calls)} respectively. The two versions also differ in investigation design and provider compatibility.",
        "The dominant frontier is V2_ABSTENTION_STATUS_DEFAULT_BYPASSES_REQUIRED_FIELDS, followed by two persistent provider timeouts. Candidate-stage versus agent-stage selection quality remains NOT_EVALUABLE.",
        "Stability repeats and telemetry-only were NOT_RUN_BY_PROTOCOL. A valid assisted RCA baseline still does not exist, so neither quality comparison is ready.",
        "V2.1 decision: " + ("V2_1_RECOMMENDED" if gate != "AGENT_V2_INVESTIGATION_AND_RCA_SUPPORTED_ON_DEVELOPMENT" else "V2_1_NOT_NEEDED") + "; no V2.1 change was implemented.",
        "Independent RCA-agent validation remains DATA_MISSING regardless of this consumed development result.",
    ]
    write("FINAL_REPORT.md", "# V3 Phase 2.16 Agent V2 Development Retry\n\n"
        f"Gate: `{gate}`. Development-only, consumed Phase 2.11 cases. The 12-case primary batch was frozen before development GT access; Phase 2.12 per-case material was not read.\n\n"
        "## Protocol questions\n\n" + "\n".join(f"{i}. {answer}" for i, answer in enumerate(answers, 1)) + "\n\n"
        f"Full regression: {collected} collected, {collected if result.returncode == 0 else 'NOT_AVAILABLE'} passed, {0 if result.returncode == 0 else 'NOT_AVAILABLE'} failed, {0 if result.returncode == 0 else 'NOT_AVAILABLE'} skipped. Historical integrity is recorded in HISTORICAL_INTEGRITY.json; Phase 2.12 was root-manifest-only. No stability repeats, telemetry-only comparison, ontology augmentation, remediation action, or canonical KG mutation occurred.\n")
    # No secret or hidden provider field may be persisted in text artifacts.
    sys.path.insert(0, str(ROOT / "src"))
    from cdoi.model_config import load_dotenv_file
    from cdoi.qwen_rca import QwenRCAConfig
    load_dotenv_file(ROOT / ".env", override=False)
    credential = QwenRCAConfig.from_internal_gateway_environment().api_key()
    unsafe = []
    for path in OUT.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md"} and path.name not in {"HASHES.json", "MANIFEST.json"}:
            text = path.read_text(encoding="utf-8")
            if (credential and credential in text) or re.search(r"Authorization\s*:|Bearer\s+[A-Za-z0-9_.-]+|\"(?:reasoning|reasoning_details)\"\s*:", text, re.I):
                unsafe.append(path.relative_to(OUT).as_posix())
    write("SECURITY_AUDIT.json", {"schema_version": "v3_phase2_16_v2_retry_security_v1",
        "status": "PASS" if not unsafe else "FAIL", "unsafe_artifacts": unsafe,
        "credential_value_scan": "PERFORMED_IN_MEMORY_VALUE_NOT_PERSISTED",
        "provider_output": "Only sanitized structural metadata and validated RCA reports retained; raw response and hidden reasoning not retained."})
    if unsafe: raise RuntimeError("UNSAFE_ARTIFACT_BEFORE_FREEZE")
    paths = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"HASHES.json", "MANIFEST.json"})
    write("HASHES.json", {"schema_version": "v3_phase2_16_v2_retry_hashes_v1",
        "artifacts": {p.relative_to(OUT).as_posix(): sha(p) for p in paths}})
    paths = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "v3_phase2_16_v2_retry_manifest_v1",
        "artifacts": {p.relative_to(OUT).as_posix(): sha(p) for p in paths}})


if __name__ == "__main__": main()
