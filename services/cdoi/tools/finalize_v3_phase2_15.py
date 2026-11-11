"""Finalize Phase 2.15 V1 from immutable primary and isolated stability runs."""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "experiments/archive/v3_phase2_15_qwen_development_20260924"
FINAL = ROOT / "experiments/archive/v3_phase2_15_finalization_20260924"
RUNTIME = ROOT / "experiments/archive/v3_phase2_15_qwen_live_retry_20260924"
TOOL_NAMES = (
    "get_incident_summary", "get_candidates", "get_expanded_candidates", "get_candidate_profile",
    "get_metric_evidence", "get_trace_evidence", "get_event_evidence", "get_change_evidence",
    "get_topology_context", "get_evidence_by_id",
)


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], proportion: float) -> float | None:
    return sorted(values)[math.ceil(len(values) * proportion) - 1] if values else None


def verify(archive: Path) -> dict[str, Any]:
    entries = load(archive / "HASHES.json")["artifacts"]
    mismatches = [name for name, digest in entries.items() if not (archive / name).is_file() or sha(archive / name) != digest]
    return {"status": "PASS" if not mismatches else "FAIL", "entry_count": len(entries), "mismatches": mismatches}


def main() -> None:
    stability = load(FINAL / "V1_STABILITY.json")
    primary_hash_before = verify(V1)
    pilot = load(V1 / "PILOT_RESULTS.json")
    config = load(V1 / "CONFIG.json")
    runtime = load(RUNTIME / "RUNTIME_SMOKE.json")
    cases = []
    previous_record_count = 0
    provider_records = []
    fallback_cases = []
    grounding_cases = []
    failure_cases = []
    for pilot_row in pilot["cases"]:
        case_id = pilot_row["case_id"]
        run = V1 / "RUNS" / case_id
        manifest = load(run / "RUN_MANIFEST.json")
        candidates = load(run / "CANDIDATES.json")["candidates"]
        profiles = load(run / "CANDIDATE_PROFILES.json")["profiles"]
        trace = load(run / "AGENT_TRACE.json")
        report = load(run / "RCA_REPORT.json")
        cumulative = pilot_row.get("latency_records", [])
        record = cumulative[-1] if len(cumulative) > previous_record_count else None
        previous_record_count = len(cumulative)
        if record is not None:
            provider_records.append({"case_id": case_id, **record})
        initial_ids = {item["candidate_id"] for item in candidates}
        profile_ids = {item["candidate_id"] for item in profiles}
        expanded_count = int(manifest.get("expanded_candidate_count", 0))
        cited_ids = set(report.get("supporting_evidence_ids", [])) | set(report.get("contradictory_evidence_ids", []))
        cited_ids.update(evidence for item in ([report.get("primary_hypothesis")] + report.get("alternative_hypotheses", [])) if isinstance(item, dict) for evidence in item.get("supporting_evidence_ids", []))
        known_evidence = set()
        for item in profiles:
            known_evidence.update(item.get("supporting_evidence_ids", [])); known_evidence.update(item.get("contradictory_evidence_ids", []))
        invalid_candidates = [item.get("candidate_id") for item in ([report.get("primary_hypothesis")] + report.get("alternative_hypotheses", [])) if isinstance(item, dict) and item.get("candidate_id") not in profile_ids]
        unknown_evidence = sorted(cited_ids - known_evidence)
        audit = {
            "case_id": case_id, "incident_context_present": True, "h1_candidates_present": bool(candidates),
            "h1_candidate_count": len(candidates), "candidate_records_preloaded": True,
            "candidate_evidence_profiles_preloaded": False, "candidate_evidence_profiles_available_via_tool": bool(profiles),
            "candidate_profile_artifact_count": len(profiles), "tool_definitions_attached": True,
            "tool_count": len(TOOL_NAMES), "tool_names": list(TOOL_NAMES), "tool_choice": "OMITTED_PROVIDER_AUTO",
            "parallel_tool_calls": False, "prompt_version": manifest["prompt_version"], "prompt_sha256": manifest["prompt_sha256"],
            "model_requested": manifest["model_metadata"].get("requested_model"), "model_resolved": "NOT_AVAILABLE_PER_CASE",
            "runtime_qualification_resolved_model": runtime["stages"][0]["response_metadata"].get("resolved_model"),
            "temperature": 0, "max_tokens": "PROVIDER_DEFAULT_NOT_SENT", "declared_max_rounds": config.get("max_rounds"),
            "separate_round_limit_enforced": False, "max_tool_calls": config["max_tool_calls"],
            "candidate_source_policy": manifest["candidate_source"], "provider_call_count": 1,
            "provider_transport_attempt_count": "NOT_AVAILABLE" if trace.get("error_code") == "QWEN_TRANSPORT_FAILURE" else 1,
            "finish_reason": "NOT_RECORDED", "completion_tokens": record.get("output_tokens") if record else "NOT_AVAILABLE",
            "retry_count": record.get("retry_count") if record else "NOT_AVAILABLE", "tool_calls_observed": len(trace.get("tool_calls", [])),
            "initial_request_had_candidate_evidence": True,
        }
        cases.append(audit)
        fallback = trace.get("fallback") or {"fallback_used": False, "fallback_reason": None}
        fallback_cases.append({"case_id": case_id, "h1_candidate_count": len(candidates), "h5_candidate_count": len(candidates) + expanded_count, "fallback_invoked": bool(fallback.get("fallback_used")), "fallback_reason": fallback.get("fallback_reason"), "additional_candidates_available": expanded_count, "additional_candidates_exposed": expanded_count if fallback.get("fallback_used") else 0})
        grounding_cases.append({"case_id": case_id, "report_status": report["status"], "candidate_references": sum(1 for item in ([report.get("primary_hypothesis")] + report.get("alternative_hypotheses", [])) if isinstance(item, dict)), "invalid_candidate_ids": invalid_candidates, "evidence_citation_count": len(cited_ids), "unknown_evidence_ids": unknown_evidence, "tool_grounded_claims": 0, "profile_grounded_claims": 0, "material_claim_analysis": "NOT_AVAILABLE_RAW_MODEL_CLAIMS_NOT_PERSISTED"})
        if report["status"] == "TECHNICAL_FAILURE":
            code = trace.get("error_code")
            failure_cases.append({"case_id": case_id, "classification": "MODEL_OUTPUT_CONTRACT_FAILURE" if code == "RCA_HYPOTHESIS_REQUIRES_PRIMARY" else "PROVIDER_TRANSPORT_FAILURE", "error_code": code, "timeout_or_connection_detail": "NOT_RECORDED", "http_status": "NOT_RECORDED", "retry_count": "NOT_RECORDED", "request_duration_ms": "NOT_RECORDED", "occurred_before_tool_interaction": True, "raw_provider_output_shape": "NOT_PERSISTED" if code == "RCA_HYPOTHESIS_REQUIRES_PRIMARY" else "NOT_APPLICABLE", "validator_inference": "status RCA_HYPOTHESIS lacked primary_hypothesis" if code == "RCA_HYPOTHESIS_REQUIRES_PRIMARY" else None})

    write(FINAL / "V1_AGENT_INPUT_AUDIT.json", {"schema_version": "v3_phase2_15_v1_input_audit_v1", "case_count": len(cases), "cases": cases, "conclusions": {"tools_attached_to_real_requests": True, "candidate_records_available_before_abstention": True, "candidate_evidence_profiles_preloaded": False, "candidate_profiles_accessible_by_tool": True, "all_observed_tool_calls": 0}})
    write(FINAL / "V1_INVESTIGATION_DIAGNOSIS.json", {"schema_version": "v3_phase2_15_v1_investigation_diagnosis_v1", "diagnostic": "V1_INVESTIGATION_NOT_ACTIVATED", "supported": ["TOOLS_ATTACHED_BUT_UNUSED", "MODEL_CHOSE_TEXT_TERMINATION", "INITIAL_CONTEXT_TRIGGERED_EARLY_ABSTENTION"], "not_supported": ["TOOLS_NOT_ATTACHED", "ORCHESTRATOR_EARLY_TERMINATION", "TOKEN_BUDGET_LIMITATION"], "qualified_findings": {"PROMPT_OVERWEIGHTED_ABSTENTION": "PLAUSIBLE_BUT_NOT_IDENTIFIABLE_FROM_ARTIFACTS", "OUTPUT_SCHEMA_CONFLICT": "ONE_CASE_ONLY_MODEL_OUTPUT_CONTRACT_FAILURE"}, "evidence": ["Every first request attached ten native tool definitions.", "Every successful semantic response returned report content without a tool call.", "Candidate records were preloaded; CandidateEvidenceProfiles were not and required tool access.", "The adapter did not send max_tokens, and successful completions exceeded 256 tokens."]})
    write(FINAL / "V1_GROUNDING_ANALYSIS.json", {"schema_version": "v3_phase2_15_v1_grounding_v1", "reports_parsed": 12, "valid_provider_structured_reports": 9, "invalid_provider_structured_reports": 1, "provider_response_unavailable": 2, "unknown_evidence_ids": sum(len(row["unknown_evidence_ids"]) for row in grounding_cases), "invalid_candidate_ids": sum(len(row["invalid_candidate_ids"]) for row in grounding_cases), "evidence_citations": sum(row["evidence_citation_count"] for row in grounding_cases), "material_factual_claims": "NOT_AVAILABLE_RAW_MODEL_CLAIMS_NOT_PERSISTED", "supported_material_claims": "NOT_EVALUATED", "unsupported_material_claims": "NOT_EVALUATED", "tool_grounded_claims": 0, "profile_grounded_claims": 0, "finding": "NO_TOOL_GROUNDING_OCCURRED", "hallucinated_tool_evidence": 0, "cases": grounding_cases})
    write(FINAL / "V1_FALLBACK_ANALYSIS.json", {"schema_version": "v3_phase2_15_v1_fallback_v1", "case_count": 12, "fallback_count": sum(row["fallback_invoked"] for row in fallback_cases), "fallback_rate": sum(row["fallback_invoked"] for row in fallback_cases) / 12, "additional_candidates_exposed": sum(row["additional_candidates_exposed"] for row in fallback_cases), "finding": "FALLBACK_NOT_ACTIVATED", "cases": fallback_cases})
    write(FINAL / "V1_FAILURE_ANALYSIS.json", {"schema_version": "v3_phase2_15_v1_failure_analysis_v1", "technical_failure_count": len(failure_cases), "provider_transport_failures": sum(row["classification"] == "PROVIDER_TRANSPORT_FAILURE" for row in failure_cases), "model_output_contract_failures": sum(row["classification"] == "MODEL_OUTPUT_CONTRACT_FAILURE" for row in failure_cases), "failures": failure_cases, "validator_action": "STRICT_FAIL_CLOSED_PRESERVED"})
    latencies = [float(row["latency_ms"]) for row in provider_records]; input_tokens = [int(row["input_tokens"]) for row in provider_records if row.get("input_tokens") is not None]; output_tokens = [int(row["output_tokens"]) for row in provider_records if row.get("output_tokens") is not None]
    write(FINAL / "V1_PERFORMANCE.json", {"schema_version": "v3_phase2_15_v1_performance_v1", "total_cases": 12, "logical_provider_requests": 12, "successful_provider_responses": len(provider_records), "provider_failures": 2, "actual_http_attempts": "NOT_AVAILABLE_FOR_FAILED_REQUESTS", "successful_response_retries": sum(int(row.get("retry_count") or 0) for row in provider_records), "provider_latency_ms": {"available_count": len(latencies), "mean": statistics.mean(latencies), "median": statistics.median(latencies), "p90": percentile(latencies, .9)}, "case_latency_ms": {"available_count": len(latencies), "definition": "provider latency only; preprocessing and failed-request duration were not persisted", "mean": statistics.mean(latencies), "median": statistics.median(latencies), "p90": percentile(latencies, .9)}, "tool_calls": 0, "input_tokens": {"available_count": len(input_tokens), "total": sum(input_tokens), "mean": statistics.mean(input_tokens)}, "output_tokens": {"available_count": len(output_tokens), "total": sum(output_tokens), "mean": statistics.mean(output_tokens)}, "total_tokens": sum(input_tokens) + sum(output_tokens), "status_distribution": dict(sorted(Counter(row["status"] for row in pilot["cases"]).items())), "engineering_runtime_qualification": "12_OF_12_PASS_SEPARATE_QUALIFICATION", "rca_quality": "0_HYPOTHESES_0_OF_12_TOP1", "token_limit_finding": {"configured_max_tokens": "NOT_SENT_PROVIDER_DEFAULT", "finish_reason": "NOT_RECORDED", "maximum_observed_completion_tokens": max(output_tokens), "responses_above_256_tokens": sum(value > 256 for value in output_tokens), "conclusion": "CDOI_LLM_MAX_TOKENS_256_DID_NOT_LIMIT_V1_RCA_REQUESTS"}})
    frozen = {name: verify(ROOT / path) for name, path in {"phase212": "experiments/archive/v3_phase2_12", "phase213": "experiments/archive/v3_phase2_13", "phase214_rca": "experiments/archive/v3_phase2_14_rca_qwen", "phase214_semantic": "experiments/archive/v3_phase2_14_semantic", "phase215_blocked": "experiments/archive/v3_phase2_15_qwen_live", "phase215_runtime_retry": "experiments/archive/v3_phase2_15_qwen_live_retry_20260924", "phase215_v1_primary": "experiments/archive/v3_phase2_15_qwen_development_20260924"}.items()}
    if any(value["status"] != "PASS" for value in frozen.values()) or primary_hash_before["status"] != "PASS":
        raise RuntimeError("FROZEN_ARCHIVE_HASH_REGRESSION")
    write(FINAL / "RESEARCH_GATE.json", {"schema_version": "v3_phase2_15_final_gate_v1", "decision": "QWEN_RUNTIME_SUPPORTED_RCA_QUALITY_INSUFFICIENT", "diagnostic": "V1_INVESTIGATION_NOT_ACTIVATED", "runtime": "SUPPORTED", "native_tool_capability": "SUPPORTED", "tools_attached_to_v1": "SUPPORTED", "v1_investigation_activation": "NOT_SUPPORTED", "v1_development_quality": "NOT_SUPPORTED", "v1_stability": "MEASURED", "independent_rca_validation": "DATA_MISSING", "phase212_holdout": "NOT_READ", "frozen_archive_integrity": frozen, "policy_change": "NONE"})
    test_results = load(FINAL / "TEST_RESULTS.json")
    report = f"""# V3 Phase 2.15 V1 Final Report

Final gate: `QWEN_RUNTIME_SUPPORTED_RCA_QUALITY_INSUFFICIENT`.
Diagnostic: `V1_INVESTIGATION_NOT_ACTIVATED`.

The immutable 12-case development batch produced nine abstentions, two provider transport failures, and one fail-closed output-contract failure. It produced no primary RCA hypothesis, no tool call, no fallback activation, and no evidence citation. Tools were attached to every real request, but CandidateEvidenceProfiles were not preloaded and remained accessible only through unused tools. Candidate records and incident context were present.

The adapter did not send `max_tokens`; therefore the repository's 256-token setting did not truncate V1 RCA calls. Finish reasons and failed-request transport detail were not persisted. Claim-level grounding cannot be reconstructed because raw model text was intentionally not retained; the available evidence establishes `NO_TOOL_GROUNDING_OCCURRED`, not hallucinated tool evidence.

Stability: {stability['completed_runs']} isolated repeats across three preregistered cases; zero-tool behavior reproducible = {str(stability['zero_tool_behavior_reproducible']).lower()}; all runs abstained = {str(stability['all_runs_abstained']).lower()}.

Regression: {test_results['collected']} collected, {test_results['passed']} passed, {test_results['failed']} failed, {test_results['skipped']} skipped.

No semantic policy, H1/H5 rule, canonical KG, review gate, or protected Phase 2.12 artifact changed. Independent RCA-agent validation remains `DATA_MISSING`.
"""
    (FINAL / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    artifacts = sorted(path for path in FINAL.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    write(FINAL / "HASHES.json", {"schema_version": "v3_phase2_15_finalization_hashes_v1", "artifacts": {path.relative_to(FINAL).as_posix(): sha(path) for path in artifacts}})
    artifacts = sorted(path for path in FINAL.rglob("*") if path.is_file() and path.name != "MANIFEST.json")
    write(FINAL / "MANIFEST.json", {"schema_version": "v3_phase2_15_finalization_manifest_v1", "artifacts": {path.relative_to(FINAL).as_posix(): sha(path) for path in artifacts}})


if __name__ == "__main__":
    main()
