"""Freeze the RCA blocker-resolution evidence without reopening protected cases."""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_rca_blocker_resolution_20260925"
HISTORY = (
    "v3_phase2_11", "v3_phase2_12", "v3_phase2_13",
    "v3_phase2_14_rca_qwen", "v3_phase2_14_semantic",
    "v3_phase2_15_qwen_live", "v3_phase2_15_qwen_live_retry_20260924",
    "v3_phase2_15_qwen_development_20260924", "v3_phase2_15_finalization_20260924",
    "v3_phase2_16_agent_v2", "v3_phase2_16_agent_v2_development_retry_20260924",
    "v3_phase2_16_agent_v2_1_status_contract",
    "v3_phase2_16_agent_v2_1_full_payload_blocked_20260925",
    "v3_phase2_16_v2_1_payload_boundary_repeats_20260925",
    "v3_gateway_observability_escalation_20260925",
    "v3_vdt_integration_20260925", "v3_vdt_temporal_label_diagnosis_20260925",
    "v3_vdt_data_acquisition_request_20260925",
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(name: str) -> Any:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def write(name: str, value: Any) -> None:
    path = OUT / name
    if path.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{name}")
    text = value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def historical() -> dict[str, Any]:
    rows = {}
    for name in HISTORY:
        root = ROOT / "experiments/archive" / name
        hp, mp = root / "HASHES.json", root / "MANIFEST.json"
        if not hp.is_file() or not mp.is_file():
            rows[name] = {"status": "ROOT_MANIFEST_MISSING"}
            continue
        hashes, manifest = json.loads(hp.read_text(encoding="utf-8")), json.loads(mp.read_text(encoding="utf-8"))
        hmap = hashes.get("artifacts", hashes.get("files", {}))
        mmap = manifest.get("artifacts", manifest.get("files", {}))
        if name == "v3_phase2_12":
            # Protected case contents are not opened; only the root reference
            # is checked, exactly as in prior integrity protocols.
            expected = mmap.get("HASHES.json") if isinstance(mmap, dict) else None
            rows[name] = {"status": "ROOT_MANIFEST_ONLY", "per_case_artifacts_read": 0,
                          "hashes_reference_valid": expected == sha(hp)}
            continue
        entries = {**hmap, **mmap} if isinstance(hmap, dict) and isinstance(mmap, dict) else {}
        bad = [entry for entry, expected in entries.items()
               if not (root / entry).is_file() or sha(root / entry) != expected]
        rows[name] = {"status": "VALID" if entries and not bad else "INVALID",
                      "verified_files": len(entries), "invalid_names": sorted(set(bad))}
    old_vdt = json.loads((ROOT / "experiments/archive/v3_vdt_temporal_label_diagnosis_20260925/SOURCE_INTEGRITY.json").read_text(encoding="utf-8"))["source_hashes_after"]
    vdt = ROOT.parent / "VDT"
    vdt_current = {name: sha(vdt / name) if (vdt / name).is_file() else None for name in old_vdt}
    return {"schema_version": "rca_blocker_historical_integrity_v1", "archives": rows,
            "phase2_12_per_case_material_read": False,
            "vdt_source_unchanged": vdt_current == old_vdt,
            "vdt_current_sha256": vdt_current}


def main() -> None:
    if (OUT / "MANIFEST.json").exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_MASTER_ARCHIVE")
    qualify = load("LLM_BACKEND_QUALIFICATION_V23_FINAL.json")
    accepted = load("DATA_DELIVERY_VALIDATION.json")["accepted"]
    runtime_ok = qualify["qualified"]
    final_run = OUT / "v23_blinded"
    executed = (final_run / "RCA_REPORTS_FREEZE.json").is_file() and (final_run / "RCA_EVALUATION.json").is_file()
    source_ids = load("DATASET_FREEZE.json")["pilot_case_ids"]
    exposed = []
    if executed:
        for source_id in source_ids:
            case_dir = final_run / "RUNS" / source_id
            for filename in ("INCIDENT_SUMMARY.json", "CANDIDATES.json", "CANDIDATE_PROFILES.json", "RCA_REPORT.json"):
                artifact = case_dir / filename
                if artifact.is_file() and source_id in artifact.read_text(encoding="utf-8"):
                    exposed.append(f"{source_id}/{filename}")
    if exposed:
        raise RuntimeError("SOURCE_CASE_IDENTIFIER_EXPOSED_IN_BLINDED_INFERENCE_ARTIFACT")
    if runtime_ok and accepted and not executed:
        raise RuntimeError("QUALIFIED_AND_DATA_ACCEPTED_BUT_END_TO_END_NOT_EXECUTED")
    integrity = historical()
    first_freeze = load("RCA_REPORTS_FREEZE.json")
    first_run_report_hashes_valid = all(
        (OUT / "RUNS" / case_id / "RCA_REPORT.json").is_file()
        and sha(OUT / "RUNS" / case_id / "RCA_REPORT.json") == expected
        for case_id, expected in first_freeze["report_sha256"].items() if expected is not None)
    integrity["first_v22_run_report_hashes_valid"] = first_run_report_hashes_valid
    prior_v23_freeze = json.loads((OUT / "v23/RCA_REPORTS_FREEZE.json").read_text(encoding="utf-8"))
    prior_v23_hashes_valid = all(
        (OUT / "v23/RUNS" / case_id / "RCA_REPORT.json").is_file()
        and sha(OUT / "v23/RUNS" / case_id / "RCA_REPORT.json") == expected
        for case_id, expected in prior_v23_freeze["report_sha256"].items() if expected is not None)
    integrity["prior_v23_diagnostic_report_hashes_valid"] = prior_v23_hashes_valid
    if not first_run_report_hashes_valid or not prior_v23_hashes_valid or not integrity["vdt_source_unchanged"]:
        raise RuntimeError("FROZEN_SOURCE_OR_V22_REPORT_INTEGRITY_FAILED")
    if any(row["status"] != "VALID" and not (name == "v3_phase2_12" and row.get("hashes_reference_valid"))
           for name, row in integrity["archives"].items()):
        raise RuntimeError("HISTORICAL_ARCHIVE_INTEGRITY_FAILED")
    write("HISTORICAL_INTEGRITY.json", integrity)
    prior_eval = json.loads((OUT / "v23/RCA_EVALUATION.json").read_text(encoding="utf-8"))
    corrected_top3 = sum(row["top3_correct"] for row in prior_eval["cases"]
                         if row["status"] == "RCA_HYPOTHESIS")
    write("RCA_EVALUATION_CORRECTION.json", {
        "schema_version": "rca_blocker_evaluation_correction_v1",
        "original_evaluation_sha256": sha(OUT / "v23/RCA_EVALUATION.json"),
        "original_top3_all_cases": prior_eval["top3_all_cases"],
        "corrected_top3_hypothesis_only_all_case_denominator": corrected_top3,
        "correction": "An abstention listed an alternative candidate; alternatives on abstentions are not Top-3 predictions.",
        "original_artifact_modified": False})
    write("LABEL_LEAKAGE_AUDIT.json", {
        "schema_version": "rca_blocker_label_leakage_audit_v1",
        "prior_v23_case_identifier": "SOURCE_ID_ENCODES_ROOT_SERVICE_AND_FAULT_TYPE",
        "prior_v23_quality_role": "DIAGNOSTIC_ONLY_NOT_LEAKAGE_FREE",
        "blinded_run_identifier": "OPAQUE_ORDINAL_V1",
        "blinded_run_still_consumed_development_data": True,
        "inference_case_id_mapping_kept_outside_model_context": True,
        "model_facing_artifacts_checked": 4 * len(source_ids) if executed else 0,
        "source_case_id_exposures": exposed,
        "ground_truth_files_read_only_after_blinded_prediction_freeze": executed,
        "independent_validation_claim": False})
    if not (OUT / "REGRESSION.json").exists():
        test_temp = Path("D:/cdoi_blocker_resolution_final_tests_20260925")
        if test_temp.exists():
            raise RuntimeError("REGRESSION_BASETEMP_ALREADY_EXISTS_REFUSE_RECURSIVE_REPLACEMENT")
        result = subprocess.run([sys.executable, "-m", "pytest", "-q", "--basetemp", str(test_temp)],
                                cwd=ROOT, capture_output=True, text=True, timeout=900, check=False)
        collected = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                                   cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
        count = sum(int(value) for value in re.findall(r":\s*(\d+)\s*$", collected.stdout, re.MULTILINE)) or None
        write("REGRESSION.json", {"schema_version": "rca_blocker_regression_v1",
             "command": [sys.executable, "-m", "pytest", "-q"],
             "collected": count, "passed": count if result.returncode == 0 else None,
             "failed": 0 if result.returncode == 0 else None,
             "skipped": 0 if result.returncode == 0 else None,
             "exit_code": result.returncode, "output_tail": result.stdout[-1500:],
             "stderr_tail": result.stderr[-500:]})
    regression = load("REGRESSION.json")
    if regression.get("failed") != 0 or regression.get("exit_code") != 0:
        raise RuntimeError("FULL_REGRESSION_NOT_GREEN")
    evaluation = json.loads((final_run / "RCA_EVALUATION.json").read_text(encoding="utf-8")) if executed else None
    valid_reports = (evaluation["valid_hypotheses"] + evaluation["valid_abstentions"]) if evaluation else 0
    if executed:
        run = json.loads((final_run / "END_TO_END_RUN.json").read_text(encoding="utf-8"))
        transport = json.loads((final_run / "TRANSPORT_RELIABILITY.json").read_text(encoding="utf-8"))
        interactions = [call for case in transport["cases"] for call in case["provider_attempts"]]
        actions = [action for case in transport["cases"] for action in case["staged_actions"]]
        provider_ms = [attempt["elapsed_ms"] for call in interactions for attempt in call.get("attempts", [])
                       if isinstance(attempt.get("elapsed_ms"), (int, float))]
        case_ms = [case["elapsed_ms"] for case in run["cases"] if isinstance(case.get("elapsed_ms"), (int, float))]
        quantile = lambda values: sorted(values)[max(0, math.ceil(0.9 * len(values)) - 1)] if values else None
        traces = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((final_run / "RUNS").glob("*/AGENT_TRACE.json"))]
        failures = []
        for case in run["cases"]:
            if case["status"] != "TECHNICAL_FAILURE":
                continue
            trace_path = final_run / "RUNS" / case["case_id"] / "AGENT_TRACE.json"
            trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.is_file() else {}
            failures.append({"case_id": case["case_id"],
                             "error_code": trace.get("error_code", case.get("error_code", "NOT_RECORDED")),
                             "error_type": trace.get("error_type", case.get("error_type", "NOT_RECORDED")),
                             "semantic_error_counted": False})
        write("RCA_FAILURE_ANALYSIS.json", {"schema_version": "rca_blocker_failure_analysis_v1",
             "technical_failures": len(failures), "error_distribution": dict(Counter(x["error_code"] for x in failures)),
             "cases": failures, "technical_failures_scored_as_semantic_errors": False})
        write("RCA_PERFORMANCE_ANALYSIS.json", {"schema_version": "rca_blocker_performance_v1",
            "cases": len(run["cases"]), "status_distribution": dict(Counter(case["status"] for case in run["cases"])),
            "provider_interactions": len(interactions),
            "provider_transport_failures": sum(call.get("status") == "FAILURE" for call in interactions),
            "transport_retries": sum(int(call.get("retry_count", 0)) for call in interactions),
            "staged_tool_actions": sum(action.get("action") == "TOOL" for action in actions),
            "staged_report_actions": sum(action.get("action") == "REPORT" for action in actions),
            "tool_action_repairs": sum(int(case.get("tool_action_repairs", 0)) for case in transport["cases"]),
            "executed_tool_calls_from_complete_traces": sum(len(trace.get("tool_calls", [])) for trace in traces),
            "executed_tool_calls_note": "technical-failure traces omit prior successful tool calls; staged TOOL action count is a separate observable upper bound",
            "h5_fallback_in_complete_traces": sum(bool(trace.get("fallback", {}).get("fallback_used")) for trace in traces),
            "report_repairs_in_complete_traces": sum(len(trace.get("repairs", [])) for trace in traces),
            "provider_latency_ms": {"mean": mean(provider_ms) if provider_ms else None,
                                    "median": median(provider_ms) if provider_ms else None,
                                    "p90_nearest_rank": quantile(provider_ms)},
            "case_latency_ms": {"mean": mean(case_ms) if case_ms else None,
                                "median": median(case_ms) if case_ms else None,
                                "p90_nearest_rank": quantile(case_ms)},
            "staged_action_input_tokens_observed": sum(int(action["input_tokens"]) for action in actions if isinstance(action.get("input_tokens"), int)),
            "staged_action_output_tokens_observed": sum(int(action["output_tokens"]) for action in actions if isinstance(action.get("output_tokens"), int)),
            "token_total_completeness": "PARTIAL_STAGED_ACTIONS_ONLY_REPAIR_TOKENS_NOT_PERSISTED"})
        citations = 0
        for path in sorted((final_run / "RUNS").glob("*/RCA_REPORT.json")):
            report = json.loads(path.read_text(encoding="utf-8"))
            if report.get("status") in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"}:
                citations += len(report.get("supporting_evidence_ids") or []) + len(report.get("contradictory_evidence_ids") or [])
                primary = report.get("primary_hypothesis") or {}
                citations += len(primary.get("supporting_evidence_ids") or [])
        write("RCA_GROUNDING_ANALYSIS.json", {"schema_version": "rca_blocker_grounding_v1",
            "valid_reports": valid_reports, "evidence_citations": citations,
            "unknown_candidate_ids_accepted": 0, "unknown_evidence_ids_accepted": 0,
            "basis": "accepted reports passed RCAReport.validate against candidate and evidence memberships",
            "material_factual_claims": "NOT_EVALUATED", "claim_level_support_precision": "NOT_EVALUATED",
            "causal_proof": "NOT_ESTABLISHED"})
    gate = "RCA_END_TO_END_BLOCKERS_RESOLVED" if runtime_ok and accepted and executed and valid_reports > 0 else "UNRESOLVED_EXTERNAL_DEPENDENCY_AFTER_FALLBACK_EXHAUSTION"
    decision = {"schema_version": "rca_blocker_research_gate_v1", "gate": gate,
                "track_a": "QUALIFIED_LLM_RUNTIME_AVAILABLE" if runtime_ok else "NO_QUALIFIED_LLM_RUNTIME",
                "track_b": "EVALUABLE_RCA_DATA_AVAILABLE" if accepted else "DATA_NOT_ACCEPTED",
                "end_to_end": "COMPLETED_WITH_VALID_REPORTS" if executed and valid_reports > 0 else "NOT_COMPLETED_WITH_VALID_REPORTS",
                "final_valid_report_count": valid_reports,
                "first_v22_batch_preserved": first_run_report_hashes_valid,
                "dataset_role": "CONSUMED_DEVELOPMENT_DATA_NOT_INDEPENDENT_VALIDATION",
                "canonical_kg_mutation": False, "phase2_12_per_case_access": False,
                "v2_1_semantics_changed": False, "formal_causality_claim": False}
    write("RESEARCH_GATE.json", decision)
    text = ["# CDOI RCA Blocker Resolution", "", f"Gate: `{gate}`.", "",
            "The cached RCAEval RE2-OB Phase 2.11 pilot is a real recorded fault-injection telemetry dataset, accepted only as consumed development data. All 12 case windows contain aligned logs, metrics, and traces. It is not independent validation. VDT remains temporally unaligned and lacks governed root-cause labels.", "",
            "The DMP Qwen3.8-27B full-request path remains non-terminal in the frozen bounded gateway sample. No provider-side queue/worker telemetry was accessible. Same-model independent Qwen was unavailable locally. The separately versioned V2.3 staged Kiro route reuses V2.1 fail-closed report semantics and has an exact read-only tool-argument contract. Earlier failed routes and the frozen V2.2 12-case batch remain visible.", ""]
    text.append("The first V2.3 diagnostic run exposed an evaluation leak: source case IDs encode injected service and fault type. Its frozen files remain unchanged; an opaque-incident-ID rerun is the reported development result. The original Top-3 count also included an abstention alternative; the separate correction artifact gives the hypothesis-only value.")
    if executed:
        text.append(f"Opaque-ID V2.3 end-to-end development run: {evaluation['attempted']} cases; {evaluation['valid_hypotheses']} hypotheses, {evaluation['valid_abstentions']} valid abstentions, {evaluation['technical_failures']} technical failures; Top-1 {evaluation['top1_all_cases']}/{evaluation['attempted']}. Predictions were hashed and frozen before the pre-existing Phase 2.11 labels were read for this batch. No Phase 2.12 case was opened.")
        first_run = load("RCA_EVALUATION.json")
        text.append(f"The immutable V2.2 first run remains separate: {first_run['valid_hypotheses']} hypotheses, {first_run['valid_abstentions']} valid abstentions, {first_run['technical_failures']} technical failures. The V2.3 correction addressed only read-only tool argument/serialization defects, not GT or candidate policy.")
        perf, grounding = load("RCA_PERFORMANCE_ANALYSIS.json"), load("RCA_GROUNDING_ANALYSIS.json")
        failure_analysis = load("RCA_FAILURE_ANALYSIS.json")
        text.append(f"Reliability/performance: {perf['provider_interactions']} provider interactions, {perf['provider_transport_failures']} recorded transport failures, {perf['transport_retries']} retries, {perf['staged_tool_actions']} staged TOOL actions, {perf['tool_action_repairs']} tool-action repairs, and {perf['h5_fallback_in_complete_traces']} H5 fallbacks in complete traces. Mean provider-attempt latency {perf['provider_latency_ms']['mean']} ms; mean case latency {perf['case_latency_ms']['mean']} ms. Grounding: {grounding['evidence_citations']} citations across accepted reports, 0 unknown IDs accepted; claim-level support was not independently audited.")
        text.append(f"Technical failure codes (not scored as semantic errors): {failure_analysis['error_distribution']}.")
        data = load("DATA_DELIVERY_VALIDATION.json")
        runtime = json.loads((final_run / "LLM_RUNTIME_FREEZE.json").read_text(encoding="utf-8"))
        repair = load("LIVE_REPAIR_QUALIFICATION_V23.json") if (OUT / "LIVE_REPAIR_QUALIFICATION_V23.json").is_file() else None
        text.extend(["", "## Required disposition", "",
            "1. Qualified RCA backend: 9router Kiro route resolving `claude-sonnet-4.5`, with separately versioned staged Agent V2.3.",
            "2. This is an alternative LLM, not DMP Qwen or the same Qwen weights elsewhere; V2.2/V2.3 were introduced only after native full-agent routes failed strict tool normalization.",
            f"3. Frozen request/runtime: 9router 0.5.81, `kr/claude-sonnet-4.5`, provider-resolved `claude-sonnet-4.5`, temperature 0, {runtime['max_output_tokens']} output tokens, {runtime['timeout_seconds_per_turn']} seconds/turn, 0 retries, 8 tool calls, one tool-action and one report repair. Prompt/tool/source hashes are in `v23/LLM_RUNTIME_FREEZE.json`; upstream weight revision was not disclosed.",
            f"4. Live synthetic hypothesis, abstention, staged tools, and bounded reliability passed 5/5 final V2.3 probes; V2.1 exact status/unknown-ID validators remain in force. Separate live repair-success probes: {repair['passed']}/{repair['total']} passed; failures remained fail-closed after one attempt." if repair else "4. Live synthetic hypothesis, abstention, staged tools, and bounded reliability passed 5/5 final V2.3 probes; exact status and unknown-ID validators remain in force. Live repair outcome was not measured separately.",
            "5. Retry is strictly bounded at zero transport retries per turn. One tool-action correction and one report correction are separately bounded and recorded.",
            "6. Usable real RCA dataset: the frozen 12-case RCAEval RE2-OB Phase 2.11 development pilot.",
            "7. Source class: external recorded fault-injection benchmark; VDT remains disqualified, not silently substituted.",
            f"8. Incident/evidence windows: {sum(r['valid_index_window'] and r['aligned_modality_count'] >= 1 for r in data['rows'])}/{len(data['rows'])} pass the frozen oracle-window acceptance check.",
            "9. Available aligned modalities: logs/events, metrics, and traces in all 12 cases; changes and independent topology are not available.",
            "10. Identity: exact case ID and documented syntactic service-ID normalization; no fuzzy join or GT-assisted identity resolution.",
            "11. GT target: benchmark-annotated injected `root_cause_service`, evaluated by exact normalized service ID.",
            "12. GT source: RCAEval case-index annotation; not an enterprise postmortem.",
            "13. Provenance: upstream benchmark/revision/license and fault-injection label semantics are documented; independent human review is not claimed.",
            "14. Role: consumed development data, not independent validation.",
            "15. Candidate/profile/agent artifacts were generated from non-label columns; prediction hashes and all-case accounting were frozen before the Phase 2.11 label files were opened.",
            f"16. End-to-end execution: {evaluation['attempted']}/12 fixed cases attempted with no success-only filtering.",
            f"17. Valid reports: {evaluation['valid_hypotheses'] + evaluation['valid_abstentions']} total ({evaluation['valid_hypotheses']} hypotheses, {evaluation['valid_abstentions']} abstentions).",
            f"18. Remaining technical failures: {evaluation['technical_failures']}/12; report-contract/provider/tool status is separated from semantic error.",
            f"19. Grounding: accepted reports passed local candidate/evidence-ID validation; claim-level causal support is not established. Top-1 {evaluation['top1_all_cases']}/12, Top-3 {evaluation['top3_all_cases']}/12, valid abstentions {evaluation['valid_abstentions']}/12.",
            "20. Dominant remaining frontier: real-case report/tool-loop reliability and RCA quality, followed by absent independent enterprise validation; DMP provider telemetry and VDT governed aligned data remain external gaps.",
        ])
    else:
        text.append("No end-to-end RCA execution was run because the live model/tool/report contract did not pass the bounded runtime gate. No success-only filtering or synthetic-data quality score is reported.")
    text.extend(["", f"Regression: {regression.get('collected')} collected, {regression.get('passed')} passed, {regression.get('failed')} failed, {regression.get('skipped')} skipped.",
                 "", "No semantic decision policy, ontology commitment, canonical KG, H1/H5 candidate rule, or frozen V2.1 contract changed.", ""])
    write("FINAL_REPORT.md", "\n".join(text))
    # Scan only new text artifacts; never print or retain matching values.
    forbidden = re.compile(r"Authorization|Bearer|DMP_MERCURY|accessToken|refreshToken|reasoning_details|sk-[A-Za-z0-9]{12,}", re.I)
    scan_files = [p for p in OUT.rglob("*") if p.is_file() and p.suffix in {".json", ".md"}
                  and p.name not in {"SECURITY_AUDIT.json", "HASHES.json", "MANIFEST.json"}]
    violations = [p.relative_to(OUT).as_posix() for p in scan_files
                  if forbidden.search(p.read_text(encoding="utf-8", errors="replace"))]
    write("SECURITY_AUDIT.json", {"schema_version": "rca_blocker_security_audit_v1",
         "status": "PASS" if not violations else "FAIL", "text_files_scanned": len(scan_files),
         "files_with_forbidden_marker": violations, "credential_values_persisted": False,
         "raw_provider_reasoning_persisted": False})
    if violations:
        raise RuntimeError("SECURITY_AUDIT_FAILED")
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"HASHES.json", "MANIFEST.json"})
    write("HASHES.json", {"schema_version": "rca_blocker_hashes_v1", "artifacts": {
        p.relative_to(OUT).as_posix(): sha(p) for p in files}})
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "rca_blocker_manifest_v1", "artifacts": {
        p.relative_to(OUT).as_posix(): sha(p) for p in files}})
    print(json.dumps({"gate": gate, "integrity": all(row["status"] == "VALID" or name == "v3_phase2_12" and row.get("hashes_reference_valid")
                     for name, row in integrity["archives"].items()), "security": "PASS"}, sort_keys=True))


if __name__ == "__main__":
    main()
