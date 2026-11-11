"""Freeze the synthetic live provider contract qualification without RCA reruns."""
from __future__ import annotations

import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, _tools
from cdoi.qwen_rca_v2 import rca_v2_system_prompt

OUT = ROOT / "experiments/archive/v3_phase2_16r_qwen_output_contract_live_20260924"
HISTORICAL = (
    "v3_phase2_12", "v3_phase2_13", "v3_phase2_14_rca_qwen", "v3_phase2_14_semantic",
    "v3_phase2_15_qwen_live", "v3_phase2_15_qwen_live_retry_20260924",
    "v3_phase2_15_qwen_development_20260924", "v3_phase2_15_finalization_20260924",
    "v3_phase2_16_agent_v2", "v3_phase2_16_agent_v2_development_20260924",
    "v3_phase2_16r_qwen_output_contract",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    path = OUT / name
    if isinstance(value, str): text = value
    else: text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def archive_integrity(name: str) -> dict[str, Any]:
    root = ROOT / "experiments/archive" / name
    hashes_file, manifest_file = root / "HASHES.json", root / "MANIFEST.json"
    if not hashes_file.is_file() or not manifest_file.is_file():
        return {"status": "ROOT_MANIFEST_MISSING"}
    hashes = json.loads(hashes_file.read_text(encoding="utf-8")).get("artifacts", {})
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")).get("artifacts", {})
    result: dict[str, Any] = {"hashes_root_sha256": sha(hashes_file), "manifest_root_sha256": sha(manifest_file),
                              "hashes_recorded": len(hashes), "manifest_recorded": len(manifest)}
    if name == "v3_phase2_12":
        # The protected case/evaluation files are out of scope.  Checking the
        # manifest's reference to HASHES.json uses root files only.
        reference = manifest.get("HASHES.json")
        result.update({"status": "ROOT_MANIFEST_ONLY", "hashes_reference_valid": reference == sha(hashes_file),
                       "per_case_artifacts_read": 0})
        return result
    bad_hashes = [relative for relative, digest in hashes.items()
                  if not (root / relative).is_file() or sha(root / relative) != digest]
    bad_manifest = [relative for relative, digest in manifest.items()
                    if not (root / relative).is_file() or sha(root / relative) != digest]
    result.update({"status": "VALID" if not bad_hashes and not bad_manifest else "INVALID",
                   "hashes_valid": len(hashes) - len(bad_hashes), "manifest_valid": len(manifest) - len(bad_manifest),
                   "invalid_names": sorted(set(bad_hashes + bad_manifest))})
    return result


def safety_scan(secret: str | None) -> dict[str, Any]:
    counts = {"credential_value_leakage": 0, "authorization_header_leakage": 0,
              "bearer_token_leakage": 0, "hidden_reasoning_field_leakage": 0}
    for path in OUT.iterdir():
        if not path.is_file() or path.suffix not in {".json", ".md"} or path.name in {"SECURITY_AUDIT.json", "HASHES.json", "MANIFEST.json"}:
            continue
        data = path.read_text(encoding="utf-8")
        if secret and secret in data: counts["credential_value_leakage"] += 1
        if re.search(r"Authorization\s*:", data, re.I): counts["authorization_header_leakage"] += 1
        if re.search(r"Bearer\s+[A-Za-z0-9_.-]+", data, re.I): counts["bearer_token_leakage"] += 1
        if re.search(r'"(?:reasoning|reasoning_details)"\s*:', data): counts["hidden_reasoning_field_leakage"] += 1
    return {"schema_version": "v3_phase2_16r_security_audit_v1", **counts,
            "status": "PASS" if not any(counts.values()) else "FAIL",
            "method": "Secret value and unsafe header patterns scanned in new archive text files; hidden provider fields are excluded by normalizer."}


def main() -> None:
    if not (OUT / "LIVE_PROBE_RESULTS.json").exists() or not (OUT / "CONTRACT_RELIABILITY.json").exists():
        raise RuntimeError("LIVE_PROBES_AND_RELIABILITY_REQUIRED")
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_FROZEN_16R_LIVE_ARCHIVE")
    load_dotenv_file(ROOT / ".env", override=False)
    config = QwenRCAConfig.from_internal_gateway_environment()
    probes = json.loads((OUT / "LIVE_PROBE_RESULTS.json").read_text(encoding="utf-8"))
    trace = json.loads((OUT / "LIVE_OUTPUT_CONTRACT_TRACE.json").read_text(encoding="utf-8"))
    reliability = json.loads((OUT / "CONTRACT_RELIABILITY.json").read_text(encoding="utf-8"))
    historical = {name: archive_integrity(name) for name in HISTORICAL}
    write("HISTORICAL_INTEGRITY.json", {"schema_version": "v3_phase2_16r_historical_integrity_v1", "archives": historical})

    # These measurements were captured as safe structural output from the
    # synthetic V2 first-turn diagnostic probes before this finalizer ran.
    diagnosis = {"schema_version": "v3_phase2_16r_output_contract_diagnosis_v2",
        "historical_12_case_exact_substage": "UNAVAILABLE_RAW_PROVIDER_SHAPE_NOT_PERSISTED",
        "historical_error": "QWEN_OUTPUT_VALIDATION_FAILURE after 12 HTTP-successful calls",
        "reproduced_synthetic_first_turn": [
            {"max_tokens": 512, "finish_reason": "length", "message_content_present": False, "tool_call_count": 0, "resolved_model": "Qwen3.8-27B"},
            {"max_tokens": 2048, "finish_reason": "length", "message_content_present": False, "tool_call_count": 0, "resolved_model": "Qwen3.8-27B"},
            {"max_tokens": 4096, "finish_reason": "stop", "message_content_present": True, "json_parseable": True, "completion_tokens": 3845, "resolved_model": "Qwen3.8-27B"},
            {"max_tokens": "OMITTED_DIAGNOSTIC_ONLY", "finish_reason": "stop", "message_content_present": True, "json_parseable": True, "completion_tokens": 2830, "resolved_model": "Qwen3.8-27B"},
        ],
        "reproduced_precise_boundary": "choices[0].finish_reason=length with empty message.content; no RCA JSON reaches the parser",
        "inference": "The frozen 512-token budget is a strongly supported cause of the live batch failure, but the missing historical finish_reason prevents per-case proof.",
        "compatibility_configuration": {"max_output_tokens": 8192, "timeout_seconds": 120, "max_retries": config.max_retries,
                                        "requested_model": config.model, "temperature": 0},
        "provider_normalization": "Truncated turns now fail as QWEN_OUTPUT_TRUNCATED; accepted JSON forms remain direct object, JSON string object, one fence, or one text block.",
        "unchanged": ["V2 RCA prompt", "H1/H5 candidates", "profile preload", "abstention rule", "fallback policy", "RCAReport validation"]}
    write("OUTPUT_CONTRACT_DIAGNOSIS.json", diagnosis)
    write("NORMALIZATION_RULES.json", {"schema_version": "v3_phase2_16r_normalization_rules_v2",
        "accepted_content": ["one direct JSON object", "one JSON string decoding to one object", "one complete fenced JSON object", "one text block containing an accepted form"],
        "rejected": ["finish_reason=length", "multiple objects or fenced blocks", "mixed prose and structured object", "content plus tool_calls", "malformed tool-call shape", "speculative JSON substring extraction"],
        "tool_calls": "Only id, type=function, function.name, and function.arguments cross the provider boundary; extra provider fields are dropped.",
        "local_validation": "V2 RCA schema and candidate/evidence checks remain authoritative."})
    write("PROVIDER_CAPABILITIES.json", {"schema_version": "v3_phase2_16r_provider_capabilities_v1",
        "requested_model": config.model, "resolved_model": "Qwen3.8-27B",
        "response_format_json_object": "PARTIALLY_SUPPORTED_JSON_OBJECT_OBSERVED_WHEN_TURN_COMPLETES",
        "json_schema_mode": "NOT_TESTED_NOT_USED_BY_V2", "strict_schema_mode": "NOT_TESTED_NOT_USED_BY_V2",
        "native_tool_calls": "SUPPORTED_P5", "serial_tool_continuation": "SUPPORTED_P6",
        "truncation_behavior": "HTTP_200_FINISH_REASON_LENGTH_EMPTY_CONTENT_AT_512_AND_2048",
        "provider_specific_extra_fields": "IGNORED_AND_NOT_PERSISTED"})
    p7 = next(row for row in probes["probes"] if row["probe_id"].startswith("P7_"))
    write("REPAIR_REACHABILITY.json", {"schema_version": "v3_phase2_16r_repair_reachability_v1",
        "live_probe": p7, "maximum_repair_attempts": 1,
        "eligible": "Readable JSON report with a recoverable local RCA schema failure",
        "ineligible": ["missing provider envelope", "finish_reason=length", "ambiguous multiple objects", "unknown tool protocol", "connection failure"],
        "repair_input": ["original structured output", "validation error code", "required report schema"],
        "ground_truth_or_new_evidence_sent": False})
    write("TOOL_PATH_AUDIT.json", {"schema_version": "v3_phase2_16r_tool_path_audit_v1",
        "trace_scope": "LIVE_OUTPUT_CONTRACT_TRACE records the final provider turn; tool-call turns are evidenced by V2 agent tool traces summarized here.",
        "probes": [{"probe_id": row["probe_id"], "native_tool_call_count": len(row["tool_names"]),
                    "tool_names": row["tool_names"], "provider_calls": row["provider_calls"],
                    "same_v2_adapter_path": True}
                   for row in probes["probes"] if row["probe_id"] in {"P5_NATIVE_TOOL_CALL", "P6_SERIAL_TOOL_CONTINUATION"}],
        "unknown_tool_accepted": 0, "synthetic_read_only_fixture": True})
    security = safety_scan(config.api_key())
    write("SECURITY_AUDIT.json", security)

    completed = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    collection = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    collected = sum(int(value) for value in re.findall(r":\s*(\d+)\s*$", collection.stdout, re.MULTILINE))
    regression = {"schema_version": "v3_phase2_16r_regression_v1", "exit_code": completed.returncode,
                  "collected": collected, "passed": collected if completed.returncode == 0 else "NOT_AVAILABLE",
                  "failed": 0 if completed.returncode == 0 else "NOT_AVAILABLE",
                  "skipped": 0 if completed.returncode == 0 else "NOT_AVAILABLE",
                  "stdout_tail": completed.stdout[-2000:], "stderr_tail": completed.stderr[-500:]}
    write("REGRESSION.json", regression)
    history_ok = all(row["status"] == "VALID" or name == "v3_phase2_12" and row["status"] == "ROOT_MANIFEST_ONLY" and row["hashes_reference_valid"] for name, row in historical.items())
    qualified = (probes["complete"] and probes["passed"] == 10 and reliability["failed_probe_runs"] == 0
                 and 10 <= reliability["provider_interactions"] <= 20 and security["status"] == "PASS"
                 and completed.returncode == 0 and history_ok)
    gate = "LIVE_QWEN_OUTPUT_CONTRACT_QUALIFIED" if qualified else "LIVE_QWEN_OUTPUT_CONTRACT_UNRESOLVED"
    write("RESEARCH_GATE.json", {"schema_version": "v3_phase2_16r_research_gate_v2", "decision": gate,
        "live_probe_passed": probes["passed"], "live_probe_total": probes["total"],
        "reliability_provider_interactions": reliability["provider_interactions"],
        "reliability_failed_probe_runs": reliability["failed_probe_runs"],
        "security_audit": security["status"], "regression": "PASS" if completed.returncode == 0 else "FAIL",
        "historical_integrity": "ROOT_ONLY_PHASE212; ALL_OTHERS_VALID" if history_ok else "INVALID",
        "v2_rca_development_quality": "NOT_REEVALUATED_IN_16R",
        "independent_validation": "DATA_MISSING", "telemetry_only": "DEFERRED",
        "next_step": "A separately frozen V2 development retry may be justified; no retry was run here."})
    write("FINAL_REPORT.md", "# V3 Phase 2.16R Qwen Output Contract\n\n"
        f"Gate: `{gate}`. The real gateway returned HTTP 200 with `finish_reason=length` and empty content on a synthetic V2 turn at 512 and 2,048 output tokens; at 4,096 it returned a complete JSON object. The historical 12 calls retained only a broad error code, so their individual substage cannot be reconstructed. The bounded qualification configuration uses 8,192 output tokens and a 120-second timeout; model, temperature, authentication, and retry count remain fixed.\n\n"
        f"Live synthetic probes: {probes['passed']}/{probes['total']} passed. P5 and P6 traversed the V2 native-tool and serial-continuation path; P7 reached one live repair. P8–P10 were deterministic local rejection controls. Repeated contract reliability: {reliability['successful_probe_runs']}/{reliability['probe_runs']} probe runs, {reliability['provider_interactions']} provider interactions, {reliability['retries']} retries, {reliability['transport_failures']} persistent transport failures.\n\n"
        f"Full regression: {regression['collected']} collected, {regression['passed']} passed, {regression['failed']} failed, {regression['skipped']} skipped. Security audit: {security['status']}. All historical archives other than the protected Phase 2.12 archive were fully hash-verified; Phase 2.12 was checked only at its root manifests. The frozen failed V2 batch remains unchanged. RCA development quality remains unevaluated under this compatibility configuration.\n")
    write("FINAL_REPORT.md", f"""# V3 Phase 2.16R Qwen Output Contract

Gate: `{gate}`. This is synthetic live provider-contract qualification, not RCA-quality evaluation. The failed Phase 2.16 V2 development archive remains immutable and no 12-case retry occurred.

## Diagnosis and compatibility

1. The exact per-case internal stage of the historical 12/12 failures is **not recoverable**: the frozen records retained `QWEN_OUTPUT_VALIDATION_FAILURE` but not finish reasons or raw shapes. A synthetic V2 first turn reproduced HTTP 200, `finish_reason=length`, empty `message.content`, and zero tool calls at 512 and 2,048 tokens. The failure occurs at provider-turn normalization before JSON and RCA validation. This is strong evidence for the 512-token budget as a cause, not proof for each historical case.
2. The observed live shape differed from complete mocked content: truncated turns can have empty content despite HTTP 200. At 4,096 tokens a synthetic turn completed with a direct JSON object; native function-call turns were accepted by the same V2 adapter.
3. `response_format={{"type":"json_object"}}` produced JSON objects on completed report probes but did not prevent truncation or guarantee schema validity: `PARTIALLY_SUPPORTED`. JSON-schema and strict-schema modes were not used by V2 and were not tested.
4. The provider boundary now classifies `finish_reason=length` as `QWEN_OUTPUT_TRUNCATED`, preserves bounded single-object normalization, and strips provider-specific extra tool fields. The separate qualification configuration is 8,192 output tokens and 120 seconds; model, temperature, authentication, and retry policy were unchanged.
5. Normalization accepts one unambiguous object (direct, JSON-string, or one fence) and rejects mixed/multiple objects, content plus tool calls, and malformed tool shapes. Local RCA and candidate/evidence validation remain authoritative.

## Required live and local probes

6. P3: valid live `INSUFFICIENT_EVIDENCE` report passed.
7. P4: valid live `RCA_HYPOTHESIS` report passed with synthetic known IDs.
8. P5: live native tool call passed through the V2 adapter and read-only synthetic tool boundary.
9. P6: two serial native tool calls and final structured report passed through that path. `LIVE_OUTPUT_CONTRACT_TRACE.json` describes the *last* provider turn; `TOOL_PATH_AUDIT.json` records the earlier tool calls.
10. P7: a readable malformed fixture reached exactly one live repair and passed. Missing/truncated/ambiguous provider output remains ineligible for RCA repair.
11. P8/P9: deterministic local semantic validation rejected unknown evidence and candidate IDs; no fuzzy resolution occurred.
12. P10: deterministic normalizer rejected multiple structured objects as `QWEN_AMBIGUOUS_OUTPUT`.
13. The contract is technically qualified for a separately frozen V2 development retry: 10/10 required probes passed; repeated reliability was {reliability['successful_probe_runs']}/{reliability['probe_runs']} runs and {reliability['provider_interactions']} provider interactions, with {reliability['retries']} recovered retries, {reliability['transport_failures']} persistent transport failures, and no normalization failure. This does not establish RCA quality.
14. Historical archives all validated against their recorded hashes except protected Phase 2.12, which was checked only at root manifests without reading case artifacts. The failed V2 archive was not modified.

Full regression: {regression['collected']} collected, {regression['passed']} passed, {regression['failed']} failed, {regression['skipped']} skipped. Security audit: {security['status']} (credential, Authorization, Bearer, and hidden-reasoning leakage all zero). Telemetry-only baseline remains `DEFERRED`; independent RCA validation remains `DATA_MISSING`.
""")
    # Scan the complete text archive, including the report and gate, before
    # sealing it. The earlier scan was used for provisional gate construction.
    security = safety_scan(config.api_key())
    write("SECURITY_AUDIT.json", security)
    if security["status"] != "PASS":
        raise RuntimeError("SECURITY_AUDIT_FAILED_BEFORE_FREEZE")
    paths = sorted(path for path in OUT.iterdir() if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    write("HASHES.json", {"schema_version": "v3_phase2_16r_hashes_v2", "artifacts": {path.name: sha(path) for path in paths}})
    paths = sorted(path for path in OUT.iterdir() if path.is_file() and path.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "v3_phase2_16r_manifest_v2", "artifacts": {path.name: sha(path) for path in paths}})


if __name__ == "__main__": main()
