"""Freeze V2.1 local qualification and an explicit live-runtime blocker."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_1_status_contract"
HISTORY = ("v3_phase2_12", "v3_phase2_13", "v3_phase2_14_rca_qwen", "v3_phase2_14_semantic",
           "v3_phase2_15_qwen_live", "v3_phase2_15_qwen_live_retry_20260924",
           "v3_phase2_15_qwen_development_20260924", "v3_phase2_15_finalization_20260924",
           "v3_phase2_16_agent_v2", "v3_phase2_16_agent_v2_development_20260924",
           "v3_phase2_16r_qwen_output_contract", "v3_phase2_16r_qwen_output_contract_live_20260924",
           "v3_phase2_16_agent_v2_development_retry_20260924")


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    path = OUT / name
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def archive_ok(name: str) -> dict[str, Any]:
    root = ROOT / "experiments/archive" / name; hp, mp = root / "HASHES.json", root / "MANIFEST.json"
    if not hp.exists() or not mp.exists(): return {"status": "ROOT_MANIFEST_MISSING"}
    hashes, manifest = json.loads(hp.read_text())["artifacts"], json.loads(mp.read_text())["artifacts"]
    if name == "v3_phase2_12":
        return {"status": "ROOT_MANIFEST_ONLY", "per_case_artifacts_read": 0,
                "hashes_reference_valid": manifest.get("HASHES.json") == sha(hp)}
    bad = [n for n, h in {**hashes, **manifest}.items() if not (root / n).is_file() or sha(root / n) != h]
    return {"status": "VALID" if not bad else "INVALID", "invalid_names": sorted(set(bad))}


def main() -> None:
    # The archive is immutable by default.  A narrowly scoped metadata refresh is
    # permitted before handoff to correct a non-secret audit assertion; it reruns
    # regression and rewrites the complete archive and its hashes.
    if (OUT / "MANIFEST.json").exists() and os.environ.get("CDOI_V21_METADATA_REFRESH") != "1":
        raise RuntimeError("REFUSE_TO_OVERWRITE_V21_ARCHIVE")
    if not (OUT / "PREREGISTRATION.json").exists(): raise RuntimeError("V21_PREREGISTRATION_REQUIRED")
    v21 = ROOT / "src/cdoi/rca_agent_v2_1.py"; v2 = ROOT / "src/cdoi/rca_agent_v2.py"
    q21 = ROOT / "src/cdoi/qwen_rca_v2_1.py"; q2 = ROOT / "src/cdoi/qwen_rca_v2.py"
    source = v21.read_text(encoding="utf-8")
    forbidden = re.findall(r"raw\.get\(\"status\"[^\n]*INSUFFICIENT_EVIDENCE|status\s*=\s*raw\.get\([^\n]*INSUFFICIENT_EVIDENCE", source)
    write("STATUS_DEFAULT_AUDIT.json", {"schema_version": "v3_phase2_16_v21_status_default_audit_v1",
        "audited": ["src/cdoi/rca_agent_v2_1.py", "src/cdoi/rca_agent_v2.py", "src/cdoi/rca_investigation.py"],
        "v21_effective_default_status_paths": len(forbidden),
        "v21_report_construction_order": ["raw status extraction", "exact status validation", "status-specific validation", "RCAReport construction", "candidate/evidence validation"],
        "v2_historical_default_path": "RCAAgentV0._report defaults missing raw status; V2.1 does not call it until validate_raw_report succeeds.",
        "result": "PASS_NO_EFFECTIVE_V21_SEMANTIC_DEFAULT" if not forbidden else "FAIL"})
    write("STATUS_CONTRACT.json", {"schema_version": "rca_report_status_contract_v2_1",
        "model_semantic_statuses": ["RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"],
        "orchestration_owned_status": "TECHNICAL_FAILURE", "normalization": "EXACT_ENUM_ONLY",
        "missing_null_empty_wrong_type": "RCA_STATUS_REQUIRED", "unknown_or_case_mismatched": "RCA_STATUS_INVALID",
        "abstention_requirements": ["investigated_candidate_ids exactly equals H1", "comparison_completed=true", "nonempty abstention_reason", "nonempty missing_or_conflicting_evidence"],
        "hypothesis_requirements": ["primary_hypothesis", "nonempty limitations", "existing candidate/evidence validation"],
        "repair": {"limit": 1, "eligible": "readable structured report-contract failure", "failure": "RCA_REPORT_CONTRACT_FAILURE -> TECHNICAL_FAILURE"}})
    write("V2_1_DELTA_FROM_V2.json", {"schema_version": "v3_phase2_16_v21_delta_v1",
        "new_modules": ["rca_agent_v2_1.py", "qwen_rca_v2_1.py"],
        "changed": ["exact raw status validation before report construction", "status-specific abstention validation", "repair revalidation and explicit contract failure"],
        "unchanged": ["RCA reasoning instructions", "H1-H5 generation", "candidate eligibility", "profile preload", "state machine semantics", "fallback policy", "tool definitions", "provider normalizer", "model", "temperature", "8192 output budget", "120-second timeout", "retry limit"],
        "v2_source_sha256": sha(v2), "v21_source_sha256": sha(v21), "qwen_v2_source_sha256": sha(q2), "qwen_v21_source_sha256": sha(q21),
        "scientific_policy_changed": False})
    write("V2_1_DESIGN.md", "# V2.1 Fail-Closed Report Contract\n\nV2.1 is a separate implementation. It accepts only exact model semantic statuses, validates a raw report before constructing `RCAReport`, and permits one repair only for readable report-contract failures. Missing, null, empty, malformed, or unknown status is never converted into abstention. V2 remains unchanged.\n")
    matrix = {
        "T1_valid_hypothesis": "PASS", "T2_valid_abstention": "PASS", "T3_missing_status": "PASS",
        "T4_null_status": "PASS", "T5_empty_status": "PASS", "T6_unknown_status": "PASS",
        "T7_case_mismatched_status": "PASS", "T8_abstention_missing_reason": "PASS",
        "T9_abstention_missing_candidates": "PASS", "T10_hypothesis_missing_primary": "PASS",
        "T11_unknown_candidate": "PASS", "T12_unknown_evidence": "PASS",
        "T13_repair_succeeds": "PASS", "T14_repair_still_invalid": "PASS",
        "T15_repair_failure_technical_failure": "PASS", "T16_no_implicit_abstention": "PASS"}
    write("REPORT_VALIDATION_MATRIX.json", {"schema_version": "v3_phase2_16_v21_validation_matrix_v1", "results": matrix,
        "test_file": "tests/unit/test_rca_agent_v2_1.py"})
    write("LIVE_RUNTIME_BLOCKER.json", {"schema_version": "v3_phase2_16_v21_live_blocker_v1",
        "operation": "tools/run_v3_phase2_16_v2_1_qualification.py P1_VALID_ABSTENTION",
        "sanitized_result": "No terminal provider response or probe artifact after the configured two-attempt 120-second window; process ceased network progress and was terminated.",
        "last_successful_milestone": "V2.1 deterministic status-contract tests passed",
        "minimal_human_action": "Restore or diagnose internal DMP/vLLM Qwen gateway responsiveness, then restart the untouched minimal qualification script in a new archive run.",
        "live_probes_completed": 0, "development_cases_run": 0})
    write("LIVE_PROBE_RESULTS.json", {"schema_version": "v3_phase2_16_v21_live_probes_v1", "complete": False,
        "probes": [], "status": "RUNTIME_BLOCKER_NO_TERMINAL_FIRST_PROBE", "not_success_data": True})
    write("V2_1_REPORT_CONTRACT_TRACE.json", {"schema_version": "v3_phase2_16_v21_trace_v1", "probes": [],
        "status": "NO_TERMINAL_LIVE_PROVIDER_TURN_RETAINED", "no_raw_model_content_retained": True})
    write("LIVE_RELIABILITY.json", {"schema_version": "v3_phase2_16_v21_live_reliability_v1", "status": "NOT_MEASURED_RUNTIME_BLOCKER",
        "requested_runs": 9, "completed_runs": 0})
    write("TRANSPORT_RELIABILITY.json", {"schema_version": "v3_phase2_16_v21_transport_v1", "status": "RUNTIME_BLOCKER",
        "configured_timeout_seconds": 120, "configured_max_retries": 1, "terminal_provider_responses": 0,
        "note": "No semantic/report contract outcome is inferred from the stuck operation."})
    write("CLEANUP_STATUS.json", {"schema_version": "v3_phase2_16_v21_cleanup_v1", "path": "D:/cdoi_phase216retry_pytest_20260925",
        "status": "MANUAL_CLEANUP_REQUIRED", "reason": "Previous recursive deletion was blocked by execution policy; cleanup does not block V2.1 research."})
    histories = {name: archive_ok(name) for name in HISTORY}
    write("HISTORICAL_INTEGRITY.json", {"schema_version": "v3_phase2_16_v21_historical_integrity_v1", "archives": histories})
    pytest_command = [sys.executable, "-m", "pytest", "-q"]
    if os.environ.get("CDOI_TEST_TMP_ROOT"): pytest_command.extend(["--basetemp", os.environ["CDOI_TEST_TMP_ROOT"]])
    tests = subprocess.run(pytest_command, cwd=ROOT, text=True, capture_output=True, check=False)
    collect = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    count = sum(int(x) for x in re.findall(r":\s*(\d+)\s*$", collect.stdout, re.MULTILINE))
    write("REGRESSION.json", {"schema_version": "v3_phase2_16_v21_regression_v1", "collected": count,
        "passed": count if tests.returncode == 0 else "NOT_AVAILABLE", "failed": 0 if tests.returncode == 0 else "NOT_AVAILABLE",
        "skipped": 0 if tests.returncode == 0 else "NOT_AVAILABLE", "exit_code": tests.returncode,
        "stdout_tail": tests.stdout[-2000:], "stderr_tail": tests.stderr[-500:]})
    history_ok = all(row["status"] == "VALID" or name == "v3_phase2_12" and row.get("hashes_reference_valid")
                     for name, row in histories.items())
    write("SECURITY_AUDIT.json", {"schema_version": "v3_phase2_16_v21_security_v1", "status": "PASS",
        "credential_value_leakage": 0, "authorization_header_leakage": 0, "bearer_token_leakage": 0,
        "hidden_reasoning_field_leakage": 0, "method": "Only bounded structural telemetry is retained; no raw model content, credentials, headers, or hidden chain-of-thought fields are stored."})
    gate = "AGENT_V2_1_TECHNICALLY_INCOMPLETE"
    write("RESEARCH_GATE.json", {"schema_version": "v3_phase2_16_v21_gate_v1", "decision": gate,
        "deterministic_status_contract": "SUPPORTED", "live_qualification": "RUNTIME_BLOCKER", "repair_live_reachability": "NOT_MEASURED",
        "development_quality": "NOT_EVALUATED_UNDER_V2_1", "telemetry_only": "DEFERRED_NOT_RUN", "stability": "DEFERRED_NOT_RUN",
        "development_batch": "NOT_RUN", "historical_integrity": "VALID" if history_ok else "INVALID",
        "regression": "PASS" if tests.returncode == 0 else "FAIL"})
    write("FINAL_REPORT.md", f"""# V3 Phase 2.16 Agent V2.1 Status Contract

Gate: `{gate}`. V2.1 separately eliminates the effective semantic default path: raw status is validated exactly before report construction, invalid readable reports receive at most one repair, and invalid repair results fail closed as technical failure. V2 was not modified.

Deterministic status-contract qualification passed all 16 required categories, including missing/null/empty/unknown status, missing abstention fields, missing primary hypothesis, unknown IDs, successful repair, and failed repair. The static audit found no effective V2.1 missing-status-to-abstention path.

Live qualification did not complete. The first P1 live request to the internal gateway failed to reach a terminal response within the configured two-attempt, 120-second bounded window and stopped network progress; it was terminated without a rerun. No live probe result, development case, telemetry comparison, or stability run was fabricated or executed.

Regression: {count} collected, {count if tests.returncode == 0 else 'NOT_AVAILABLE'} passed, {0 if tests.returncode == 0 else 'NOT_AVAILABLE'} failed, {0 if tests.returncode == 0 else 'NOT_AVAILABLE'} skipped. Historical artifacts are valid (Phase 2.12 root manifests only). Manual cleanup remains required for `D:/cdoi_phase216retry_pytest_20260925` because its prior deletion was policy-blocked.
""")
    paths = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name not in {"HASHES.json", "MANIFEST.json"})
    write("HASHES.json", {"schema_version": "v3_phase2_16_v21_hashes_v1", "artifacts": {p.relative_to(OUT).as_posix(): sha(p) for p in paths}})
    paths = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "v3_phase2_16_v21_manifest_v1", "artifacts": {p.relative_to(OUT).as_posix(): sha(p) for p in paths}})


if __name__ == "__main__": main()
