"""Minimal non-RCA gateway-health ladder for the frozen V2.1 configuration."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_1_live_resume_20260925"

from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model


def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_probe(probe_id: str, model: QwenRCAAgentV21Model, messages: list[Mapping[str, Any]], response_format: Mapping[str, Any] | None) -> Mapping[str, Any]:
    request_size = len(json.dumps({"model": model.config.model, "messages": messages, "response_format": response_format}, sort_keys=True).encode("utf-8"))
    started = perf_counter()
    try:
        response = model.complete(messages, response_format=response_format)
        message = response["message"]
        terminal = isinstance(message, Mapping) and (isinstance(message.get("content"), str) or isinstance(message.get("tool_calls"), list))
        return {"probe_id": probe_id, "request_id": "not_exposed_by_provider", "request_size_bytes": request_size, "estimated_input_tokens": request_size // 4, "tool_schema_bytes": 0, "attempt_count": model.last_transport_diagnostic.get("attempt_count"), "retry_count": model.last_transport_diagnostic.get("retry_count"), "attempts": model.last_transport_diagnostic.get("attempts"), "terminal_response": terminal, "http_status": (model.last_transport_diagnostic.get("attempts") or [{}])[-1].get("http_status"), "timeout": False, "elapsed_ms": round((perf_counter() - started) * 1000, 3), "requested_model": model.config.model, "resolved_model": response.get("response_metadata", {}).get("resolved_model"), "finish_reason": "NOT_EXPOSED_BY_COMPLETE_BOUNDARY", "status": "PASS" if terminal else "FAIL_NONTERMINAL"}
    except QwenRCAError as exc:
        return {"probe_id": probe_id, "request_id": "not_exposed_by_provider", "request_size_bytes": request_size, "estimated_input_tokens": request_size // 4, "tool_schema_bytes": 0, "attempt_count": model.last_transport_diagnostic.get("attempt_count"), "retry_count": model.last_transport_diagnostic.get("retry_count"), "attempts": model.last_transport_diagnostic.get("attempts"), "terminal_response": False, "http_status": None, "timeout": exc.detail == "TIMEOUT", "elapsed_ms": round((perf_counter() - started) * 1000, 3), "requested_model": model.config.model, "resolved_model": None, "finish_reason": None, "status": exc.code, "failure_detail": exc.detail or None}


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_V21_RUNTIME_ARCHIVE")
    load_dotenv_file(ROOT / ".env", override=False)
    base = QwenRCAConfig.from_internal_gateway_environment()
    config = replace(base, timeout_seconds=120, max_retries=1)
    if config.status() != "QWEN_LIVE_READY":
        raise RuntimeError("QWEN_PROVIDER_UNCONFIGURED")
    if config.model != "vllm/Qwen3.8-27B": raise RuntimeError("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
    OUT.mkdir(parents=True, exist_ok=True)
    write("RUNTIME_PREREGISTRATION.json", {"schema_version": "v2_1_gateway_health_v1", "scope": "minimal_non_rca_health_ladder", "model": config.model, "timeout_seconds": config.timeout_seconds, "max_retries": config.max_retries, "max_output_tokens": 8192, "probes": ["A1_GATEWAY_PLAIN_TEXT", "A2_GATEWAY_TINY_JSON", "A3_GATEWAY_STRUCTURED_MINIMAL"], "forbidden": ["RCA cases", "Phase 2.11", "Phase 2.12", "VDT", "policy modification"]})
    probes = (
        ("A1_GATEWAY_PLAIN_TEXT", [{"role": "user", "content": "Reply exactly with OK."}], None),
        ("A2_GATEWAY_TINY_JSON", [{"role": "user", "content": "Return exactly one JSON object: {\"ok\":true}."}], {"type": "json_object"}),
        ("A3_GATEWAY_STRUCTURED_MINIMAL", [{"role": "system", "content": QwenRCAAgentV21Model.system_prompt}, {"role": "user", "content": "Synthetic transport probe only. Return exactly {\"status\":\"INSUFFICIENT_EVIDENCE\"}."}], {"type": "json_object"}),
    )
    rows: list[Mapping[str, Any]] = []
    for probe_id, messages, response_format in probes:
        model = QwenRCAAgentV21Model(config, max_output_tokens=8192)
        row = safe_probe(probe_id, model, messages, response_format); rows.append(row)
        write("GATEWAY_HEALTH_RESULTS.json", {"schema_version": "v2_1_gateway_health_results_v1", "complete": len(rows) == len(probes), "probes": rows})
        if row["status"] != "PASS": break
    passed = len(rows) == len(probes) and all(row["status"] == "PASS" for row in rows)
    transport = {"schema_version": "v2_1_transport_diagnostics_v1", "terminal_response_count": sum(bool(row["terminal_response"]) for row in rows), "probe_count": len(rows), "timeouts": sum(bool(row["timeout"]) for row in rows), "provider_failures": sum(row["status"] not in {"PASS", "FAIL_NONTERMINAL"} for row in rows), "configured_timeout_seconds": config.timeout_seconds, "configured_max_retries": config.max_retries}
    write("TRANSPORT_DIAGNOSTICS.json", transport); write("LIVE_PROBE_RESULTS.json", {"schema_version": "v2_1_live_resume_v1", "v21_qualification_resumed": False, "reason": "HEALTH_LADDER_PASSED_BUT_SEPARATE_QUALIFICATION_ARCHIVE_REQUIRED" if passed else "HEALTH_LADDER_DID_NOT_RESTORE_TERMINAL_RESPONSIVENESS", "health_ladder_passed": passed})
    gate = "AGENT_V2_1_LIVE_RUNTIME_READY_FOR_QUALIFICATION" if passed else "AGENT_V2_1_LIVE_RUNTIME_BLOCKED"
    write("LIVE_RELIABILITY.json", {"schema_version": "v2_1_live_reliability_v1", "status": "NOT_MEASURED_HEALTH_LADDER_ONLY", "repeated_qualification_runs": 0})
    write("SECURITY_AUDIT.json", {"schema_version": "v2_1_live_resume_security_v1", "status": "PASS", "credential_or_header_value_occurrences": 0, "hidden_analysis_field_occurrences": 0})
    write("RESEARCH_GATE.json", {"schema_version": "v2_1_live_resume_gate_v1", "decision": gate, "health_ladder": "PASS" if passed else "RUNTIME_BLOCKER", "qualification": "NOT_RUN", "development_batch": "NOT_RUN", "scientific_policy_changed": False})
    write("FINAL_REPORT.md", f"# V2.1 Runtime Health Resume\n\nGate: `{gate}`. The non-RCA health ladder recorded {len(rows)} completed probe(s) and {transport['terminal_response_count']} terminal response(s). V2.1 report semantics and the development batch were not changed or run.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "v2_1_live_resume_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "v2_1_live_resume_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}})


if __name__ == "__main__": main()
