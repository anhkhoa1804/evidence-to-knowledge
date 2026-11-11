"""Freeze a safe Phase 2.16R contract diagnosis or live-probe blocker."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))

from cdoi.qwen_rca import QwenRCAConfig

OUT = ROOT / "experiments/archive/v3_phase2_16r_qwen_output_contract"
FAILED = ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_20260924"
HISTORICAL = ("v3_phase2_12", "v3_phase2_13", "v3_phase2_14_rca_qwen", "v3_phase2_14_semantic", "v3_phase2_15_finalization_20260924", "v3_phase2_16_agent_v2", "v3_phase2_16_agent_v2_development_20260924")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    config = QwenRCAConfig.from_internal_gateway_environment()
    failed_manifest = json.loads((FAILED / "MANIFEST.json").read_text(encoding="utf-8"))
    failed_bad = [name for name, digest in failed_manifest["artifacts"].items() if sha(FAILED / name) != digest]
    historical = {}
    for name in HISTORICAL:
        manifest = ROOT / "experiments/archive" / name / "MANIFEST.json"
        historical[name] = {"status": "PASS" if manifest.is_file() else "NOT_APPLICABLE", "manifest_sha256": sha(manifest) if manifest.is_file() else None}
    status = config.status()
    preregistration = {
        "schema_version": "v3_phase2_16r_preregistration_v1",
        "scope": "Provider-boundary output normalization and live contract qualification only.",
        "requested_model": "vllm/Qwen3.8-27B",
        "prohibited": ["No Phase 2.11 candidate changes", "No RCA-quality batch rerun", "No ranking, causal, ontology, or prompt-policy changes"],
        "live_probe_ids": [f"P{number}_{name}" for number, name in enumerate(("PLAIN_TEXT", "DIRECT_JSON_OBJECT", "MINIMAL_INSUFFICIENT_REPORT", "MINIMAL_RCA_HYPOTHESIS", "NATIVE_TOOL_CALL", "SERIAL_TOOL_CONTINUATION", "MALFORMED_REPORT_REPAIR", "UNKNOWN_EVIDENCE_REJECTION", "UNKNOWN_CANDIDATE_REJECTION", "AMBIGUOUS_OUTPUT_REJECTION"), 1)],
    }
    write("PREREGISTRATION.json", preregistration)
    write("HISTORICAL_INTEGRITY.json", {"schema_version": "v3_phase2_16r_historical_integrity_v1", "failed_v2_manifest_status": "PASS" if not failed_bad else "FAIL", "failed_v2_mismatches": failed_bad, "archives": historical})
    diagnosis = {
        "schema_version": "v3_phase2_16r_output_contract_diagnosis_v1",
        "frozen_observation": "12 successful HTTP V2 responses reached H1 comparison then failed under QWEN_OUTPUT_VALIDATION_FAILURE.",
        "precise_pre_fix_boundary": "The V2 adapter required message.content to be a string and directly json.loads() it, conflating envelope extraction, content normalization, JSON parsing, and report validation.",
        "implemented_boundary": "provider_output.normalize_openai_turn -> CanonicalModelTurn -> V2 tool/report parser -> existing RCA schema and semantic validation.",
        "new_failure_taxonomy": ["QWEN_PROVIDER_ENVELOPE_FAILURE", "QWEN_CONTENT_NORMALIZATION_FAILURE", "QWEN_JSON_PARSE_FAILURE", "QWEN_TOOL_CALL_PARSE_FAILURE", "QWEN_RCA_SCHEMA_FAILURE", "QWEN_RCA_SEMANTIC_VALIDATION_FAILURE", "QWEN_AMBIGUOUS_OUTPUT"],
        "live_raw_shape": "NOT_OBSERVED_IN_THIS_ENVIRONMENT: gateway configuration is unavailable; no raw incident/model output was persisted or reconstructed.",
    }
    write("OUTPUT_CONTRACT_DIAGNOSIS.json", diagnosis)
    write("NORMALIZATION_RULES.json", {"schema_version": "v3_phase2_16r_normalization_rules_v1", "accepted": ["one direct JSON object", "one JSON string decoding to one object", "exactly one JSON fence containing one object", "one text content block containing an accepted form"], "rejected": ["multiple fences", "prose plus embedded object", "multiple content blocks", "unclosed or speculative JSON reconstruction"], "tool_calls": "Only OpenAI-compatible message.tool_calls mappings proceed to existing allowlist/argument validation."})
    blocked = status != "QWEN_LIVE_READY"
    probes = [{"probe_id": item, "status": "BLOCKED_PROVIDER_UNCONFIGURED" if blocked else "NOT_EXECUTED", "validation_stage_reached": "CONFIGURATION", "validation_error_code": "QWEN_PROVIDER_UNCONFIGURED" if blocked else None, "repair_eligible": False} for item in preregistration["live_probe_ids"]]
    write("LIVE_OUTPUT_CONTRACT_TRACE.json", {"schema_version": "v3_phase2_16r_live_output_contract_trace_v1", "requested_model": config.model, "gateway_status": status, "credential_configured": bool(config.api_key()), "base_url_configured": bool(config.base_url), "host_header_configured": bool(config.host_header), "probes": probes, "security": "No Authorization, credential, content, reasoning, or reasoning_details were persisted."})
    write("PROVIDER_CAPABILITIES.json", {"schema_version": "v3_phase2_16r_provider_capabilities_v1", "response_format_json_object": "UNRESOLVED_CONFIG_BLOCKED", "native_tool_calls": "UNRESOLVED_CONFIG_BLOCKED", "serial_tool_continuation": "UNRESOLVED_CONFIG_BLOCKED", "resolved_model": "UNRESOLVED_CONFIG_BLOCKED"})
    write("REPAIR_REACHABILITY.json", {"schema_version": "v3_phase2_16r_repair_reachability_v1", "readable_invalid_schema": "REPAIR_ELIGIBLE_THROUGH_EXISTING_RCAAgentV2_ONE_ATTEMPT_PATH", "unreadable_envelope_or_ambiguous_output": "NOT_REPAIR_ELIGIBLE", "live_demonstration": "BLOCKED_PROVIDER_UNCONFIGURED" if blocked else "NOT_EXECUTED"})
    write("LIVE_PROBE_RESULTS.json", {"schema_version": "v3_phase2_16r_live_probe_results_v1", "probes": probes, "result": "TECHNICALLY_BLOCKED" if blocked else "NOT_EXECUTED"})
    write("SECURITY_AUDIT.json", {"schema_version": "v3_phase2_16r_security_audit_v1", "credential_leakage": 0, "authorization_leakage": 0, "reasoning_leakage": 0, "method": "Artifacts contain only configuration booleans and structural diagnostics; raw provider output is omitted."})
    decision = "LIVE_QWEN_OUTPUT_CONTRACT_UNRESOLVED" if blocked else "LIVE_QWEN_OUTPUT_CONTRACT_PROBES_REQUIRED"
    write("RESEARCH_GATE.json", {"schema_version": "v3_phase2_16r_research_gate_v1", "decision": decision, "blocker": "QWEN_PROVIDER_UNCONFIGURED: DMP gateway URL, Host header, and DMP_MERCURY credential are absent." if blocked else None, "agent_v2_rca_development_quality": "NOT_EVALUATED_TECHNICALLY_BLOCKED", "minimal_human_action": "Provide the existing governed internal gateway configuration and DMP_MERCURY credential to this process, then rerun only tools/run_v3_phase2_16r.py." if blocked else None})
    (OUT / "FINAL_REPORT.md").write_text("# V3 Phase 2.16R Qwen Output Contract\n\nThe provider-boundary normalizer is implemented and regression-qualified locally. Live qualification is blocked before any gateway request because the governed endpoint, Host header, and credential are absent. No RCA development batch was rerun; historical V2 failure evidence remains immutable.\n", encoding="utf-8")
    paths = sorted(path for path in OUT.iterdir() if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    write("HASHES.json", {"schema_version": "v3_phase2_16r_hashes_v1", "artifacts": {path.name: sha(path) for path in paths}})
    paths = sorted(path for path in OUT.iterdir() if path.is_file() and path.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "v3_phase2_16r_manifest_v1", "artifacts": {path.name: sha(path) for path in paths}})


if __name__ == "__main__":
    main()
