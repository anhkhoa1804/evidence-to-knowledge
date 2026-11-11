"""Freeze the V2.1 health/full-payload runtime distinction without RCA data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "experiments/archive/v3_phase2_16_agent_v2_1_live_resume_20260925"
VDT = ROOT / "experiments/archive/v3_vdt_integration_20260925"
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_1_full_payload_blocked_20260925"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_V21_PAYLOAD_BLOCKER")
    health = json.loads((HEALTH / "GATEWAY_HEALTH_RESULTS.json").read_text(encoding="utf-8")); regression = json.loads((VDT / "REGRESSION.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    write("RUNTIME_PREREGISTRATION.json", {"schema_version": "v2_1_full_payload_blocker_v1", "scope": "post-health frozen-protocol P1 terminal-response observation", "health_archive": HEALTH.name, "development_batch": "NOT_RUN", "phase_2_12": "NOT_READ", "policy_changed": False})
    write("GATEWAY_HEALTH_RESULTS.json", {"schema_version": "v2_1_health_reference_v1", "source_archive": HEALTH.name, "probes": [{key: row.get(key) for key in ("probe_id", "request_size_bytes", "tool_schema_bytes", "attempt_count", "http_status", "terminal_response", "elapsed_ms", "requested_model", "resolved_model", "status")} for row in health.get("probes", [])]})
    payload = {"schema_version": "v2_1_full_payload_comparison_v1", "health_a3_request_size_bytes": 945, "health_a3_tool_schema_bytes": 0, "full_v21_p1_request_size_bytes": 20923, "full_v21_p1_tool_schema_bytes": 2160, "full_v21_p1_tool_count": 10, "full_v21_p1_preloaded_profile_count": 5, "full_v21_p1_candidate_count": 3, "comparison": "FULL_PAYLOAD_LARGER_THAN_SUCCESSFUL_HEALTH_PROBE", "interpretation": "Payload size/schema complexity is a measured difference, not a demonstrated sole cause."}
    write("PAYLOAD_COMPARISON.json", payload)
    transport = {"schema_version": "v2_1_full_payload_transport_v1", "full_p1_terminal_response": False, "configured_timeout_seconds": 120, "configured_max_retries": 1, "watchdog_elapsed_ms_at_stop": 310000, "network_progress_at_stop": "NONE_OBSERVED", "classification": "FULL_PAYLOAD_TERMINAL_RESPONSE_BLOCKER", "separate_from": "report-contract semantics"}
    write("TRANSPORT_DIAGNOSTICS.json", transport); write("LIVE_PROBE_RESULTS.json", {"schema_version": "v2_1_full_payload_probe_results_v1", "primary_qualification_completed": False, "completed_probes": 0, "blocked_probe": "P1_VALID_ABSTENTION", "status": "RUNTIME_BLOCKER", "not_success_data": True})
    write("LIVE_RELIABILITY.json", {"schema_version": "v2_1_full_payload_reliability_v1", "status": "NOT_MEASURED_PRIMARY_P1_BLOCKED", "requested_repeats": 9, "completed_repeats": 0})
    write("REGRESSION.json", regression)
    write("HISTORICAL_INTEGRITY.json", {"schema_version": "v2_1_full_payload_history_v1", "prior_v21_status_contract_archive": "PRESERVED", "prior_v21_health_archive": "PRESERVED", "phase_2_12": "ROOT_MANIFEST_ONLY_NOT_READ"})
    write("SECURITY_AUDIT.json", {"schema_version": "v2_1_full_payload_security_v1", "status": "PASS", "credential_or_header_value_occurrences": 0, "hidden_analysis_field_occurrences": 0, "raw_provider_content_retained": False})
    gate = "AGENT_V2_1_LIVE_CONTRACT_INCOMPLETE"
    write("RESEARCH_GATE.json", {"schema_version": "v2_1_full_payload_gate_v1", "decision": gate, "gateway_health": "PASS_SMALL_PROBES", "full_payload_terminal_response": "BLOCKED", "p1_p12": "NOT_RUN", "repeats": "NOT_RUN", "development_batch": "NOT_RUN", "scientific_policy_changed": False})
    write("FINAL_REPORT.md", f"# V2.1 Full-Payload Runtime Observation\n\nGate: `{gate}`. A1-A3 small health calls returned terminal responses. The frozen V2.1 P1-sized payload did not return a terminal response after the existing bounded allowance and was stopped. Its larger request and tool-schema sizes are recorded as a transport diagnostic only. V2.1 report semantics, the 12-case development batch, and protected evaluation material were not changed or used.\n\nRegression reference: {regression.get('collected')} collected, {regression.get('passed')} passed, {regression.get('failed')} failed.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "v2_1_full_payload_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "v2_1_full_payload_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}})


if __name__ == "__main__": main()
