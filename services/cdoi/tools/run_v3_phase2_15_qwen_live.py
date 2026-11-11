"""Bounded, secret-free Phase 2.15 internal-Qwen runtime qualification.

This is a development-only experiment.  It does not read Phase 2.12, mutate
the canonical KG, or change candidate-generation/semantic policies.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import sys
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.model_config import dotenv_state, load_dotenv_file
from cdoi.qwen_rca import INTERNAL_QWEN_PROFILE, QwenRCAAgentModel, QwenRCAConfig, QwenRCAError

OUT = ROOT / "experiments/archive/v3_phase2_15_qwen_live"
FROZEN = {
    "phase212": ROOT / "experiments/archive/v3_phase2_12",
    "phase213": ROOT / "experiments/archive/v3_phase2_13",
    "phase214_rca": ROOT / "experiments/archive/v3_phase2_14_rca_qwen",
    "phase214_semantic": ROOT / "experiments/archive/v3_phase2_14_semantic",
}
REPEATS = 3  # deliberately below a statistical stability claim; bounded live cost


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(archive: Path) -> dict[str, Any]:
    try:
        entries = json.loads((archive / "HASHES.json").read_text(encoding="utf-8"))["artifacts"]
    except (OSError, KeyError, json.JSONDecodeError):
        return {"status": "UNAVAILABLE"}
    mismatches = [name for name, digest in entries.items() if not (archive / name).is_file() or sha(archive / name) != digest]
    return {"status": "PASS" if not mismatches else "FAIL", "entry_count": len(entries), "mismatches": mismatches}


def tool(name: str) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": "Harmless deterministic runtime compatibility probe.", "parameters": {"type": "object", "properties": {"value": {"type": "string"}}, "required": ["value"], "additionalProperties": False}}}


def force(name: str) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name}}


def safe_error(error: Exception) -> dict[str, str]:
    if isinstance(error, QwenRCAError):
        return {"code": error.code, "detail": error.detail or ""}
    return {"code": "UNEXPECTED_RUNTIME_ERROR", "detail": type(error).__name__}


def content_json(result: Mapping[str, Any]) -> bool:
    message = result.get("message", {})
    content = message.get("content") if isinstance(message, Mapping) else None
    try:
        return isinstance(json.loads(content or ""), Mapping)
    except (TypeError, json.JSONDecodeError):
        return False


def simple(model: QwenRCAAgentModel) -> dict[str, Any]:
    result = model.complete([{"role": "user", "content": "Say OK"}])
    message = result["message"]
    return {"status": "PASS" if message.get("content", "").strip() == "OK" else "INVALID_CONTENT", "latency_ms": result["latency_ms"], "retry_count": result["retry_count"], "response_metadata": result["response_metadata"]}


def structured(model: QwenRCAAgentModel) -> dict[str, Any]:
    result = model.complete([{"role": "user", "content": 'Return exactly this JSON object and no prose: {"status":"ok"}'}], response_format={"type": "json_object"})
    valid = content_json(result)
    return {"status": "PASS" if valid else "SCHEMA_FAILURE", "latency_ms": result["latency_ms"], "retry_count": result["retry_count"], "response_metadata": result["response_metadata"]}


def one_tool(model: QwenRCAAgentModel) -> dict[str, Any]:
    spec = tool("get_smoke_value")
    messages: list[Mapping[str, Any]] = [{"role": "user", "content": "Call get_smoke_value with value ping. Then return exactly JSON {\"status\":\"ok\"}."}]
    first = model.complete(messages, tools=[spec], tool_choice=force("get_smoke_value"))
    calls = first["message"].get("tool_calls", [])
    if len(calls) != 1 or calls[0].get("function", {}).get("name") != "get_smoke_value":
        return {"status": "TOOL_PARSE_FAILURE", "latency_ms": first["latency_ms"], "retry_count": first["retry_count"], "response_metadata": first["response_metadata"]}
    try:
        arguments = json.loads(calls[0]["function"].get("arguments", ""))
    except (KeyError, TypeError, json.JSONDecodeError):
        return {"status": "TOOL_PARSE_FAILURE", "latency_ms": first["latency_ms"], "retry_count": first["retry_count"], "response_metadata": first["response_metadata"]}
    if arguments != {"value": "ping"}:
        return {"status": "TOOL_ARGUMENT_VALIDATION_FAILURE", "latency_ms": first["latency_ms"], "retry_count": first["retry_count"], "response_metadata": first["response_metadata"]}
    messages += [first["message"], {"role": "tool", "tool_call_id": calls[0].get("id", "smoke-call-1"), "content": '{"value":"pong"}'}]
    final = model.complete(messages, tools=[spec], response_format={"type": "json_object"})
    return {"status": "PASS" if content_json(final) else "CONTINUATION_SCHEMA_FAILURE", "tool_name": "get_smoke_value", "validated_arguments": arguments, "latency_ms": first["latency_ms"] + final["latency_ms"], "retry_count": first["retry_count"] + final["retry_count"], "response_metadata": final["response_metadata"]}


def multi_tool(model: QwenRCAAgentModel) -> dict[str, Any]:
    specs = [tool("get_smoke_a"), tool("get_smoke_b")]
    messages: list[Mapping[str, Any]] = [{"role": "user", "content": "Use get_smoke_a then get_smoke_b with value ping. Finally return exactly JSON {\"status\":\"ok\"}."}]
    rounds: list[Mapping[str, Any]] = []
    for index, name in enumerate(("get_smoke_a", "get_smoke_b"), 1):
        result = model.complete(messages, tools=specs, tool_choice=force(name))
        calls = result["message"].get("tool_calls", [])
        if len(calls) != 1 or calls[0].get("function", {}).get("name") != name:
            return {"status": "TOOL_PARSE_FAILURE", "completed_tools": index - 1, "rounds": rounds, "response_metadata": result["response_metadata"]}
        try:
            arguments = json.loads(calls[0]["function"].get("arguments", ""))
        except (KeyError, TypeError, json.JSONDecodeError):
            return {"status": "TOOL_PARSE_FAILURE", "completed_tools": index - 1, "rounds": rounds, "response_metadata": result["response_metadata"]}
        if arguments != {"value": "ping"}:
            return {"status": "TOOL_ARGUMENT_VALIDATION_FAILURE", "completed_tools": index - 1, "rounds": rounds, "response_metadata": result["response_metadata"]}
        rounds.append({"tool_name": name, "validated_arguments": arguments, "latency_ms": result["latency_ms"], "retry_count": result["retry_count"]})
        messages += [result["message"], {"role": "tool", "tool_call_id": calls[0].get("id", f"smoke-call-{index}"), "content": json.dumps({"value": f"{name}-result"})}]
    final = model.complete(messages, tools=specs, response_format={"type": "json_object"})
    return {"status": "PASS" if content_json(final) else "CONTINUATION_SCHEMA_FAILURE", "completed_tools": 2, "rounds": rounds, "final_latency_ms": final["latency_ms"], "response_metadata": final["response_metadata"]}


def execute(label: str, action, model: QwenRCAAgentModel) -> dict[str, Any]:
    try:
        return {"stage": label, **action(model)}
    except Exception as error:  # fail closed and persist a sanitized class only
        return {"stage": label, "status": "TECHNICAL_FAILURE", "error": safe_error(error)}


def summarize(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(row.get("status")) for row in rows)
    return {"attempts": len(rows), "successful_interactions": statuses.get("PASS", 0), "status_counts": dict(sorted(statuses.items())), "transport_failures": sum(row.get("error", {}).get("code") == "QWEN_TRANSPORT_FAILURE" for row in rows), "auth_failures": sum(row.get("error", {}).get("code") == "QWEN_AUTH_FAILURE" for row in rows), "model_failures": sum(row.get("error", {}).get("code") == "QWEN_MODEL_UNAVAILABLE" for row in rows), "tool_parse_failures": statuses.get("TOOL_PARSE_FAILURE", 0), "schema_failures": sum("SCHEMA_FAILURE" in str(row.get("status")) for row in rows), "retry_count": sum(int(row.get("retry_count", 0)) for row in rows if isinstance(row.get("retry_count", 0), (int, float)))}


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser(description="Run a bounded, immutable Phase 2.15 Qwen qualification attempt.")
    parser.add_argument("--output", type=Path, help="New archive directory; required when preserving a prior frozen attempt.")
    arguments = parser.parse_args()
    if arguments.output is not None:
        OUT = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    if OUT.exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_PHASE215_LIVE_ARCHIVE")
    frozen_before = {name: verify(path) for name, path in FROZEN.items()}
    dotenv = ROOT / ".env"
    before = dotenv_state("DMP_MERCURY", dotenv)
    # Local file is already a repository configuration convention; process
    # values still win and are never printed or persisted.
    load_dotenv_file(dotenv, override=False)
    config = QwenRCAConfig.from_internal_gateway_environment()
    after = dotenv_state(config.api_key_env, dotenv)
    try:
        dns_ips = sorted({item[4][0] for item in socket.getaddrinfo(config.host_header or "", 80, type=socket.SOCK_STREAM)})
        dns = {"status": "RESOLVED", "address_count": len(dns_ips), "addresses": dns_ips}
    except socket.gaierror as error:
        dns = {"status": "DNS_UNRESOLVED", "error_class": type(error).__name__}
    gateway_ip = os.environ.get("CDOI_QWEN_GATEWAY_IP", "")
    profile = {**config.public_metadata(), "host": config.host_header, "resolved_ip": gateway_ip if gateway_ip and config.base_url and gateway_ip in config.base_url else "CONFIGURED_PRIVATE_IP", "credential_environment": after.as_dict(), "dotenv_loaded_for_child_process": bool(after.dotenv_present and not before.process_present)}
    write(OUT / "PROVIDER_PROFILE.json", {"schema_version": "v3_phase2_15_provider_profile_v1", "profile": profile, "dns": dns})
    write(OUT / "CONFIG.json", {"schema_version": "v3_phase2_15_qwen_config_v1", "provider_profile": INTERNAL_QWEN_PROFILE, "prompt_version": "rca_agent_qwen_v1", "candidate_source": "H1_THEN_H5_FALLBACK", "thinking_mode": "GATEWAY_DEFAULT", "parallel_tool_calls": False, "budget": {"max_reasoning_rounds": 8, "max_tool_calls": 12, "max_candidate_profiles": 6}, "development_only": True})
    if config.status() != "QWEN_LIVE_READY":
        gate = "QWEN_AUTH_NOT_VISIBLE_TO_PROCESS" if not config.api_key() else "QWEN_RUNTIME_NETWORK_BLOCKED"
        runtime_rows: list[Mapping[str, Any]] = []
    else:
        model = QwenRCAAgentModel(config)
        runtime_rows = [execute("simple", simple, model), execute("structured", structured, model), execute("one_tool", one_tool, model), execute("multi_tool", multi_tool, model)]
        # Only repeat after every required native capability has passed once.
        if all(row.get("status") == "PASS" for row in runtime_rows):
            for action, label in ((simple, "simple"), (structured, "structured"), (one_tool, "one_tool"), (multi_tool, "multi_tool")):
                runtime_rows.extend(execute(label, action, model) for _ in range(REPEATS - 1))
        gate = "QWEN_LIVE_RUNTIME_SUPPORTED" if all(row.get("status") == "PASS" for row in runtime_rows) and len(runtime_rows) >= 4 * REPEATS else "QWEN_INTERNAL_GATEWAY_INCOMPATIBLE"
    smoke = runtime_rows[:4]
    write(OUT / "RUNTIME_SMOKE.json", {"schema_version": "v3_phase2_15_qwen_runtime_smoke_v1", "credential_present": bool(config.api_key()), "dns": dns, "stages": smoke, "reasoning_fields": "DISCARDED_BEFORE_ANY_ARTIFACT"})
    reliability = summarize(runtime_rows)
    reliability.update({"schema_version": "v3_phase2_15_qwen_reliability_v1", "planned_repeats_per_stage": REPEATS, "completed_attempts": len(runtime_rows), "thresholds_predeclared": {"simple": 0.95, "structured": 0.90, "one_tool": 0.90, "multi_tool": 0.85, "fail_closed": 1.0}, "stability_claim": "NOT_MADE_SMALL_ENGINEERING_SAMPLE"})
    write(OUT / "RUNTIME_RELIABILITY.json", reliability)
    unavailable = {"schema_version": "v3_phase2_15_development_results_v1", "status": "NOT_RUN_RUNTIME_QUALIFICATION_REQUIRED" if gate != "QWEN_LIVE_RUNTIME_SUPPORTED" else "NOT_RUN_PILOT_REQUIRES_SEPARATE_FROZEN_EXECUTION", "reason": "Phase 2.11 pilot and synthetic quality evaluation are intentionally not started until a dedicated pilot runner freezes its full configuration; this run establishes transport/tool compatibility only."}
    write(OUT / "SYNTHETIC_RESULTS.json", unavailable); write(OUT / "DEVELOPMENT_DATA_MANIFEST.json", {"schema_version": "v3_phase2_15_development_data_v1", "phase211_pilot": "AUTHORIZED_CONSUMED_DEVELOPMENT_DATA_NOT_READ_BY_RUNTIME_QUALIFICATION", "phase212_holdout": "PROHIBITED_NOT_READ"}); write(OUT / "PILOT_RESULTS.json", unavailable); write(OUT / "FALLBACK_ANALYSIS.json", unavailable); write(OUT / "FAILURE_CASES.json", {"schema_version": "v3_phase2_15_failure_cases_v1", "runtime_failures": [row for row in runtime_rows if row.get("status") != "PASS"], "semantic_result": "NOT_APPLICABLE_TO_RUNTIME_COMPATIBILITY"}); write(OUT / "STABILITY_RESULTS.json", {"schema_version": "v3_phase2_15_stability_v1", "status": "NOT_EVALUATED_DEVELOPMENT_PILOT_NOT_RUN", "runtime_repeat_note": "Small capability repeats are in RUNTIME_RELIABILITY; they are not RCA decision stability."})
    write(OUT / "PERFORMANCE.json", {"schema_version": "v3_phase2_15_performance_v1", "live_model_calls": len(runtime_rows), "cost": "COST_NOT_MEASURED", "latency_measurement": "PER_INTERACTION_SANITIZED_IN_RUNTIME_ARTIFACT"})
    frozen_after = {name: verify(path) for name, path in FROZEN.items()}
    write(OUT / "RESEARCH_GATE.json", {"schema_version": "v3_phase2_15_qwen_gate_v1", "decision": gate, "frozen_archives_before": frozen_before, "frozen_archives_after": frozen_after, "runtime": "SUPPORTED" if gate == "QWEN_LIVE_RUNTIME_SUPPORTED" else "NOT_SUPPORTED", "rca_development_quality": "NOT_EVALUATED", "independent_rca_agent_validation": "DATA_MISSING", "phase212_holdout": "NOT_READ", "canonical_kg_mutation": "NONE", "next_step": "Run a separately frozen fixed-configuration synthetic and Phase 2.11 development-only evaluation only if runtime qualification is supported."})
    write(OUT / "EXPERIMENT_MANIFEST.json", {"schema_version": "v3_phase2_15_manifest_v1", "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "runtime": {"python": sys.version, "platform": platform.platform()}, "purpose": "INTERNAL_QWEN_LIVE_RUNTIME_QUALIFICATION_DEVELOPMENT_ONLY", "frozen_archives_verified": frozen_after})
    artifacts = sorted(path for path in OUT.rglob("*.json") if path.name not in {"HASHES.json", "MANIFEST.json"})
    write(OUT / "HASHES.json", {"schema_version": "v3_phase2_15_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})
    artifacts = sorted(path for path in OUT.rglob("*.json") if path.name != "MANIFEST.json")
    write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_15_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})


if __name__ == "__main__":
    main()
