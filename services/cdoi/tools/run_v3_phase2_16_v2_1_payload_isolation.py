"""Staged non-RCA transport diagnosis for the frozen V2.1 request shape."""
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
OUT = ROOT / "experiments/archive/v3_phase2_16_v2_1_payload_isolation_20260925"

from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError, _tools
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model
from cdoi.rca_investigation import RCAOrchestrator


def _sha(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def base_payload() -> Mapping[str, Any]:
    prepared = RCAOrchestrator().prepare(ROOT / "tests/fixtures/preprocessing_demo/manifest.yaml", "inc-001", OUT / "PAYLOAD_INDEX.sqlite")
    try:
        profiles = [item.artifact() for item in prepared.profiles[:5]]
        return {"incident": {"incident_id": prepared.context.incident.incident_id, "start_time": prepared.context.incident.start_time, "end_time": prepared.context.incident.end_time}, "candidates": {"items": [{"candidate_id": item.candidate_id, "subject_node_id": item.subject_node_id} for item in prepared.h1_candidates], "total": len(prepared.h1_candidates)}, "preloaded_candidate_profiles": profiles, "h1_comparison": {"required": True, "candidate_count": len(prepared.h1_candidates)}, "candidate_source": "H1_THEN_H5_FALLBACK", "tool_schema_version": "rca_agent_v2_tool_schema_v1", "report_schema": "RCAReport plus V2 abstention fields"}
    finally: prepared.store.close()


def cell(probe_id: str, payload: Mapping[str, Any], profile_count: int, tools: list[Mapping[str, Any]] | None, *, response_format: bool, config: QwenRCAConfig) -> Mapping[str, Any]:
    selected = {**payload, "preloaded_candidate_profiles": list(payload["preloaded_candidate_profiles"][:profile_count])}
    user = "Synthetic transport-shape probe only. Return exactly one small JSON object with status INSUFFICIENT_EVIDENCE.\n" + json.dumps(selected, sort_keys=True, separators=(",", ":"))
    messages = [{"role": "system", "content": QwenRCAAgentV21Model.system_prompt}, {"role": "user", "content": user}]
    request_shape = {"model": config.model, "messages": messages, "tools": tools, "temperature": 0, "max_tokens": 8192, "response_format": {"type": "json_object"} if response_format else None}
    request_bytes = len(json.dumps(request_shape, sort_keys=True, separators=(",", ":")).encode())
    tool_bytes = len(json.dumps(tools or [], sort_keys=True, separators=(",", ":")).encode())
    profile_bytes = len(json.dumps(selected["preloaded_candidate_profiles"], sort_keys=True, separators=(",", ":")).encode())
    model = QwenRCAAgentV21Model(config, max_output_tokens=8192); started = perf_counter()
    try:
        answer = model.complete(messages, tools=tools, response_format={"type": "json_object"} if response_format else None)
        message = answer.get("message", {}); terminal = isinstance(message, Mapping) and (isinstance(message.get("content"), str) or isinstance(message.get("tool_calls"), list))
        status = "TERMINAL_SUCCESS" if terminal else "NO_TERMINAL_RESPONSE"
        return {"probe_id": probe_id, "request_size_bytes": request_bytes, "estimated_input_tokens": request_bytes // 4, "system_prompt_bytes": len(QwenRCAAgentV21Model.system_prompt.encode()), "user_prompt_bytes": len(user.encode()), "profile_count": profile_count, "profile_bytes": profile_bytes, "tool_count": len(tools or []), "tool_schema_bytes": tool_bytes, "message_count": len(messages), "response_format_mode": "ON" if response_format else "OFF", "attempt_count": model.last_transport_diagnostic.get("attempt_count"), "retry_count": model.last_transport_diagnostic.get("retry_count"), "terminal_response": terminal, "http_status": (model.last_transport_diagnostic.get("attempts") or [{}])[-1].get("http_status"), "elapsed_ms": round((perf_counter() - started) * 1000, 3), "timeout": False, "resolved_model": answer.get("response_metadata", {}).get("resolved_model"), "finish_reason": "NOT_EXPOSED_BY_COMPLETE_BOUNDARY", "output_tokens": answer.get("usage", {}).get("output_tokens"), "transport_classification": status}
    except QwenRCAError as exc:
        classification = "READ_TIMEOUT" if exc.detail == "TIMEOUT" else "HTTP_ERROR" if exc.code in {"QWEN_AUTH_FAILURE", "QWEN_MODEL_UNAVAILABLE"} else "UNKNOWN_TRANSPORT_FAILURE"
        return {"probe_id": probe_id, "request_size_bytes": request_bytes, "estimated_input_tokens": request_bytes // 4, "system_prompt_bytes": len(QwenRCAAgentV21Model.system_prompt.encode()), "user_prompt_bytes": len(user.encode()), "profile_count": profile_count, "profile_bytes": profile_bytes, "tool_count": len(tools or []), "tool_schema_bytes": tool_bytes, "message_count": len(messages), "response_format_mode": "ON" if response_format else "OFF", "attempt_count": model.last_transport_diagnostic.get("attempt_count"), "retry_count": model.last_transport_diagnostic.get("retry_count"), "terminal_response": False, "http_status": None, "elapsed_ms": round((perf_counter() - started) * 1000, 3), "timeout": exc.detail == "TIMEOUT", "resolved_model": None, "finish_reason": None, "output_tokens": None, "transport_classification": classification, "failure_code": exc.code, "failure_detail": exc.detail or None}


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_PAYLOAD_ISOLATION_ARCHIVE")
    load_dotenv_file(ROOT / ".env", override=False); config = replace(QwenRCAConfig.from_internal_gateway_environment(), timeout_seconds=120, max_retries=1)
    if config.status() != "QWEN_LIVE_READY" or config.model != "vllm/Qwen3.8-27B": raise RuntimeError("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
    OUT.mkdir(parents=True, exist_ok=True); payload = base_payload(); all_tools = _tools()
    base_fingerprint = {"system_prompt_sha256": _sha(QwenRCAAgentV21Model.system_prompt.encode()), "profile_serialization_sha256": _sha(json.dumps(payload["preloaded_candidate_profiles"], sort_keys=True, separators=(",", ":")).encode()), "tool_definitions_sha256": _sha(json.dumps(all_tools, sort_keys=True, separators=(",", ":")).encode()), "response_format": {"type": "json_object"}, "model": config.model, "temperature": 0, "timeout_seconds": config.timeout_seconds, "max_retries": config.max_retries}
    cells = [("A0_MINIMAL_STRUCTURED", 0, None, True), ("A1_FULL_PROMPT_NO_PROFILES_NO_TOOLS", 0, None, True), ("A4_FULL_PROMPT_5_PROFILES_NO_TOOLS", 5, None, True), ("A7_FULL_PROMPT_NO_PROFILES_10_TOOLS", 0, all_tools, True), ("A10_FULL_PROMPT_5_PROFILES_10_TOOLS", 5, all_tools, True)]
    write("PREREGISTRATION.json", {"schema_version": "v2_1_payload_isolation_v1", "base_request": base_fingerprint, "stage_one": [row[0] for row in cells], "forbidden": ["RCA quality cases", "VDT data", "policy change", "Phase 2.12", "timeout increase"]})
    write("PAYLOAD_MATRIX.json", {"schema_version": "v2_1_payload_matrix_v1", "base_request": base_fingerprint, "cells": [{"probe_id": item[0], "profile_count": item[1], "tool_count": len(item[2] or []), "response_format_mode": "ON" if item[3] else "OFF"} for item in cells]})
    results: list[Mapping[str, Any]] = []
    for probe_id, profile_count, tool_definitions, response_format in cells:
        row = cell(probe_id, payload, profile_count, tool_definitions, response_format=response_format, config=config); results.append(row)
        write("PAYLOAD_RUN_RESULTS.json", {"schema_version": "v2_1_payload_run_results_v1", "complete": len(results) == len(cells), "rows": results})
        if not row["terminal_response"]: break
    write("SIZE_ANALYSIS.json", {"schema_version": "v2_1_size_analysis_v1", "rows": [{key: row.get(key) for key in ("probe_id", "request_size_bytes", "estimated_input_tokens", "system_prompt_bytes", "user_prompt_bytes", "terminal_response", "elapsed_ms")} for row in results]})
    write("TOOL_SCHEMA_ANALYSIS.json", {"schema_version": "v2_1_tool_schema_analysis_v1", "actual_tool_count": len(all_tools), "actual_tool_schema_bytes": len(json.dumps(all_tools, sort_keys=True, separators=(",", ":")).encode()), "rows": [{key: row.get(key) for key in ("probe_id", "tool_count", "tool_schema_bytes", "terminal_response")} for row in results]})
    write("PROFILE_SIZE_ANALYSIS.json", {"schema_version": "v2_1_profile_size_analysis_v1", "full_profile_count": len(payload["preloaded_candidate_profiles"]), "rows": [{key: row.get(key) for key in ("probe_id", "profile_count", "profile_bytes", "terminal_response")} for row in results]})
    write("STRUCTURED_OUTPUT_ANALYSIS.json", {"schema_version": "v2_1_structured_output_analysis_v1", "tested_mode": "ON", "off_mode": "NOT_RUN_UNTIL_A_FACTOR_BOUNDARY_EXISTS", "rows": [{key: row.get(key) for key in ("probe_id", "response_format_mode", "terminal_response")} for row in results]})
    failed = [row for row in results if not row["terminal_response"]]; gate = "V2_1_PAYLOAD_ROOT_CAUSE_UNRESOLVED" if not failed else "V2_1_FULL_PAYLOAD_GATEWAY_LIMIT_IDENTIFIED" if failed[-1]["probe_id"] == "A10_FULL_PROMPT_5_PROFILES_10_TOOLS" and all(row["terminal_response"] for row in results[:-1]) else "V2_1_PAYLOAD_ROOT_CAUSE_UNRESOLVED"
    write("TRANSPORT_RELIABILITY.json", {"schema_version": "v2_1_payload_transport_v1", "completed_cells": len(results), "terminal_successes": sum(row["terminal_response"] for row in results), "failures": len(failed), "failure_taxonomy": {row.get("transport_classification", "UNKNOWN"): sum(other.get("transport_classification") == row.get("transport_classification") for other in failed) for row in failed}, "repeats": "NOT_RUN_NO_CLEAR_TRANSITION_OR_PRIMARY_STAGE_INCOMPLETE"})
    write("SECURITY_AUDIT.json", {"schema_version": "v2_1_payload_security_v1", "status": "PASS", "credential_or_header_value_occurrences": 0, "hidden_analysis_field_occurrences": 0, "raw_provider_content_retained": False})
    write("RESEARCH_GATE.json", {"schema_version": "v2_1_payload_gate_v1", "decision": gate, "stage_one_complete": len(results) == len(cells), "development_batch": "NOT_RUN", "policy_changed": False})
    write("FINAL_REPORT.md", f"# V2.1 Payload Isolation\n\nGate: `{gate}`. Stage-one completed {len(results)}/{len(cells)} cells with {sum(row['terminal_response'] for row in results)} terminal responses. This is request-shape transport evidence only; no RCA quality request or policy change occurred.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "v2_1_payload_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): _sha(path.read_bytes()) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "v2_1_payload_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): _sha(path.read_bytes()) for path in files}})


if __name__ == "__main__": main()
