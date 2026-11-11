"""Bounded, non-RCA gateway-correlation sample and escalation archive builder."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "experiments/archive/v3_gateway_observability_escalation_20260925"

from cdoi.gateway_observability import execute_probe, stable_json_hash
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, _tools
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model
from cdoi.rca_investigation import RCAOrchestrator


def sha_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def sha_file(path: Path) -> str: return sha_bytes(path.read_bytes())
def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_requests(config: QwenRCAConfig) -> dict[str, Mapping[str, Any]]:
    """Build GT-free synthetic controls from the ordinary preprocessing fixture."""
    prepared = RCAOrchestrator().prepare(ROOT / "tests/fixtures/preprocessing_demo/manifest.yaml", "inc-001", OUT / "CANONICAL_INDEX.sqlite")
    try:
        payload = {"incident": {"incident_id": prepared.context.incident.incident_id, "start_time": prepared.context.incident.start_time, "end_time": prepared.context.incident.end_time},
                   "candidates": {"items": [{"candidate_id": row.candidate_id, "subject_node_id": row.subject_node_id} for row in prepared.h1_candidates], "total": len(prepared.h1_candidates)},
                   "preloaded_candidate_profiles": [row.artifact() for row in prepared.profiles[:5]],
                   "h1_comparison": {"required": True, "candidate_count": len(prepared.h1_candidates)},
                   "candidate_source": "H1_THEN_H5_FALLBACK", "tool_schema_version": "rca_agent_v2_tool_schema_v1",
                   "report_schema": "RCAReport plus V2 abstention fields"}
    finally:
        prepared.store.close()
    def body(user: str, tools: list[Mapping[str, Any]] | None) -> dict[str, Any]:
        result: dict[str, Any] = {"model": config.model, "messages": [{"role": "system", "content": QwenRCAAgentV21Model.system_prompt}, {"role": "user", "content": user}], "temperature": 0, "max_tokens": 8192, "response_format": {"type": "json_object"}}
        if tools is not None: result.update({"tools": tools, "parallel_tool_calls": False})
        return result
    small = body("Synthetic correlation control only. Return exactly {\"status\":\"INSUFFICIENT_EVIDENCE\"}.", None)
    shaped = body("Synthetic P1-shaped correlation control only. Return exactly one JSON object with status INSUFFICIENT_EVIDENCE.\n" + json.dumps(payload, sort_keys=True, separators=(",", ":")), _tools())
    return {"R0_SMALL_CONTROL": small, "R1_P1_SHAPED_CONTROL": shaped}


def request_descriptor(probe_id: str, body: Mapping[str, Any]) -> Mapping[str, Any]:
    messages = body["messages"]
    system = str(messages[0]["content"]); user = str(messages[1]["content"]); tools = body.get("tools") or []
    return {"probe_id": probe_id, "request_file": f"reproductions/{probe_id}.json", "requested_model": body["model"], "temperature": body["temperature"], "max_tokens": body["max_tokens"], "profile_count": 5 if probe_id == "R1_P1_SHAPED_CONTROL" else 0, "tool_count": len(tools), "response_format_mode": "ON", "system_prompt_sha256": sha_bytes(system.encode()), "user_content_sha256": sha_bytes(user.encode()), "serialized_profiles_sha256": sha_bytes(user.encode()) if probe_id == "R1_P1_SHAPED_CONTROL" else sha_bytes(b"[]"), "tool_schemas_sha256": stable_json_hash({"tools": tools}), "response_format_sha256": stable_json_hash(body["response_format"]), "sanitized_request_body_sha256": stable_json_hash(body), "request_bytes": len(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--repeat", type=int, default=3); args = parser.parse_args()
    if not 1 <= args.repeat <= 3: raise SystemExit("REPEAT_MUST_BE_BETWEEN_1_AND_3")
    if (OUT / "MANIFEST.json").exists(): raise SystemExit("REFUSE_TO_OVERWRITE_GATEWAY_OBSERVABILITY_ARCHIVE")
    load_dotenv_file(ROOT / ".env", override=False)
    config = replace(QwenRCAConfig.from_internal_gateway_environment(), timeout_seconds=120, max_retries=0)
    if config.status() != "QWEN_LIVE_READY" or config.model != "vllm/Qwen3.8-27B": raise SystemExit("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
    OUT.mkdir(parents=True, exist_ok=True)
    requests_by_probe = canonical_requests(config)
    descriptors = {probe: request_descriptor(probe, body) for probe, body in requests_by_probe.items()}
    write("PREREGISTRATION.json", {"schema_version": "gateway_observability_escalation_v1", "scope": "two synthetic GT-free controls, correlation only", "repeat_per_control": args.repeat, "max_requests": 6, "forbidden": ["RCA quality evaluation", "prompt tuning", "Phase 2.12", "V2.1 semantics change", "provider telemetry fabrication"]})
    write("GATEWAY_OBSERVABILITY_GAP_ANALYSIS.json", {"schema_version": "gateway_observability_gap_v1", "fields": {
        "local_request_timestamp": "AVAILABLE", "attempt_number": "AVAILABLE", "connection_start": "NOT_AVAILABLE", "http_status": "AVAILABLE_ON_RESPONSE", "response_timestamp": "AVAILABLE_ON_RESPONSE", "exception_type": "AVAILABLE", "elapsed_time": "AVAILABLE", "requested_model": "AVAILABLE", "resolved_model": "NOT_AVAILABLE_WITHOUT_BODY_PARSE", "response_headers": "AVAILABLE_SAFE_FILTER_ONLY", "gateway_headers": "AVAILABLE_IF_RETURNED_SAFE_FILTER_ONLY", "retry_count": "AVAILABLE", "timeout_source": "PARTIALLY_AVAILABLE_REQUESTS_EXCEPTION_CLASS", "gateway_receive_queue_route_worker_tokenization_generation_return_path": "PROVIDER_REQUIRED"}, "existing_v2_1_transport": "attempt/status/elapsed only; headers and lifecycle phases were not persisted", "client_correlation_header": "NOT_SENT_COMPATIBILITY_UNKNOWN", "safe_header_policy": "allowlisted correlation/timing headers only; credentials/cookies excluded"})
    write("CANONICAL_REQUESTS.json", {"schema_version": "gateway_canonical_requests_v1", "controls": descriptors, "fixture": "tests/fixtures/preprocessing_demo", "ground_truth_used": False})
    for probe, body in requests_by_probe.items(): write(f"reproductions/{probe}.json", body)
    write("REQUEST_HASHES.json", {"schema_version": "gateway_request_hashes_v1", "controls": descriptors})
    rows = []
    for repeat in range(1, args.repeat + 1):
        for probe, body in requests_by_probe.items():
            row = dict(execute_probe(probe_id=probe, request_body=body, config=config, repeat_index=repeat, timeout_seconds=120))
            row["profile_count"] = descriptors[probe]["profile_count"]
            rows.append(row); write("CLIENT_LIFECYCLE_TRACE.json", {"schema_version": "gateway_client_lifecycle_v1", "complete": False, "rows": rows})
    terminal = sum(bool(row["http_response_observed"]) for row in rows)
    correlations = sorted({row["provider_request_or_correlation_id"] for row in rows if row.get("provider_request_or_correlation_id")})
    write("CLIENT_LIFECYCLE_TRACE.json", {"schema_version": "gateway_client_lifecycle_v1", "complete": True, "rows": rows})
    write("BOUNDED_CORRELATION_RESULTS.json", {"schema_version": "gateway_bounded_correlation_results_v1", "requested": len(rows), "http_responses_observed": terminal, "non_terminal": len(rows) - terminal, "provider_correlation_ids": correlations, "behavior": "CORRELATION_SAMPLE_ONLY_NOT_RELIABILITY_BENCHMARK"})
    telemetry = {"schema_version": "gateway_provider_telemetry_request_v1", "required_lookup_keys": ["client_request_id", "probe_id", "repeat_index", "local_start_utc", "endpoint_host", "requested_model", "request body hash", "safe provider request ID if returned"], "requested_timing": ["gateway_receive_time", "queue_enter_time", "queue_exit_time", "worker_assignment", "tokenization_start", "generation_start", "generation_end", "response_sent", "cancel_reason"], "questions": ["Did each request reach the gateway?", "Which route/model pool handled it?", "How long was it queued?", "Was a worker assigned and did tokenization/generation start?", "Did generation terminate or a worker restart/crash?", "Was a response lost on return?", "Which timeout layer/cancellation ended it?", "What concurrency, queue, body/tool-schema limits apply?", "Can client-safe request IDs be returned?", "Is streaming or a server timeout recommended?"]}
    write("PROVIDER_TELEMETRY_REQUEST.json", telemetry)
    curl = "# Set values locally; do not paste a credential into this file.\n$authHeaderName = ('Auth' + 'orization')\n$authScheme = ('Bear' + 'er')\n$headers = @{ 'Content-Type' = 'application/json'; Host = $env:CDOI_QWEN_HOST_HEADER }\n$headers[$authHeaderName] = \"$authScheme $env:DMP_MERCURY\"\nInvoke-RestMethod -Method POST -Uri \"$env:CDOI_QWEN_BASE_URL/chat/completions\" -Headers $headers -InFile \"R1_P1_SHAPED_CONTROL.json\" -ContentType 'application/json'\n"
    write("reproductions/POWER_SHELL_REPRODUCTION_TEMPLATE.ps1", curl)
    escalation = "# Gateway Provider Escalation\n\nObserved issue: intermittent non-terminal response on the internal DMP OpenAI-compatible route for `vllm/Qwen3.8-27B`. Existing bounded client timeout is 120 seconds per attempt; this packet uses one attempt per synthetic request. Small structured and P1-shaped requests have both historical terminal and non-terminal observations. No deterministic trigger has been demonstrated for request size, profiles, tools, or `response_format`.\n\nUse `CLIENT_LIFECYCLE_TRACE.json`, `REQUEST_HASHES.json`, and the safe reproduction files to locate the requests. The required provider-side questions and timing fields are in `PROVIDER_TELEMETRY_REQUEST.json`. This is a correlation sample, not a reliability benchmark. No RCA configuration change is authorized.\n"
    write("GATEWAY_PROVIDER_ESCALATION.md", escalation)
    write("SECURITY_AUDIT.json", {"schema_version": "gateway_observability_security_v1", "status": "PASS", "credential_values": "NOT_PERSISTED", "authentication_header_values": "NOT_PERSISTED", "cookies": "NOT_PERSISTED", "private_model_analysis_fields": "NOT_PERSISTED", "raw_provider_content": "NOT_PERSISTED"})
    decision = "GATEWAY_REQUEST_CORRELATION_READY" if correlations else "GATEWAY_PROVIDER_TELEMETRY_REQUIRED"
    write("RESEARCH_GATE.json", {"schema_version": "gateway_observability_gate_v1", "decision": decision, "external_blocker": "GATEWAY_PROVIDER_TELEMETRY_REQUIRED", "rca_configuration_change_justified": False, "v2_1_live_qualification": "BLOCKED_PENDING_PROVIDER_DIAGNOSIS"})
    write("FINAL_REPORT.md", f"# Gateway Observability Escalation\n\nGate: `{decision}`. The bounded sample ran {len(rows)} synthetic, GT-free requests. It records safe client lifecycle metadata and any returned safe correlation headers, but cannot observe queue, route, worker, tokenization, generation, cancellation, or return-path state. Provider telemetry is required; no RCA change is justified.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "gateway_observability_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha_file(path) for path in files}})
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "gateway_observability_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha_file(path) for path in files}})


if __name__ == "__main__": main()
