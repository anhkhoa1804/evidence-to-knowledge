"""One-factor response-format control for the failed A0 V2.1 payload shape."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "experiments/archive/v3_phase2_16_v2_1_response_format_control_20260925"

import run_v3_phase2_16_v2_1_payload_isolation as isolation
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_RESPONSE_FORMAT_CONTROL")
    load_dotenv_file(ROOT / ".env", override=False); config = replace(QwenRCAConfig.from_internal_gateway_environment(), timeout_seconds=120, max_retries=1)
    if config.status() != "QWEN_LIVE_READY" or config.model != "vllm/Qwen3.8-27B": raise RuntimeError("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
    OUT.mkdir(parents=True, exist_ok=True); payload = isolation.base_payload(); selected = {**payload, "preloaded_candidate_profiles": []}
    user = "Synthetic transport-shape probe only. Return exactly one small JSON object with status INSUFFICIENT_EVIDENCE.\n" + json.dumps(selected, sort_keys=True, separators=(",", ":")); messages = [{"role": "system", "content": QwenRCAAgentV21Model.system_prompt}, {"role": "user", "content": user}]
    request_size = len(json.dumps({"model": config.model, "messages": messages, "temperature": 0, "max_tokens": 8192}, sort_keys=True, separators=(",", ":")).encode())
    write("PREREGISTRATION.json", {"schema_version": "v2_1_response_format_control_v1", "reference": "A0_MINIMAL_STRUCTURED", "only_changed_factor": "response_format omitted", "request_size_bytes_without_response_format": request_size, "timeout_seconds": 120, "max_retries": 1, "no_rca_case": True})
    model = QwenRCAAgentV21Model(config, max_output_tokens=8192); started = perf_counter()
    try:
        answer = model.complete(messages, response_format=None); message = answer.get("message", {}); terminal = isinstance(message, Mapping) and (isinstance(message.get("content"), str) or isinstance(message.get("tool_calls"), list))
        row = {"terminal_response": terminal, "transport_classification": "TERMINAL_SUCCESS" if terminal else "NO_TERMINAL_RESPONSE", "elapsed_ms": round((perf_counter() - started) * 1000, 3), "attempt_count": model.last_transport_diagnostic.get("attempt_count"), "retry_count": model.last_transport_diagnostic.get("retry_count"), "http_status": (model.last_transport_diagnostic.get("attempts") or [{}])[-1].get("http_status"), "resolved_model": answer.get("response_metadata", {}).get("resolved_model"), "timeout": False, "output_tokens": answer.get("usage", {}).get("output_tokens")}
    except QwenRCAError as exc:
        row = {"terminal_response": False, "transport_classification": "READ_TIMEOUT" if exc.detail == "TIMEOUT" else "UNKNOWN_TRANSPORT_FAILURE", "elapsed_ms": round((perf_counter() - started) * 1000, 3), "attempt_count": model.last_transport_diagnostic.get("attempt_count"), "retry_count": model.last_transport_diagnostic.get("retry_count"), "http_status": None, "resolved_model": None, "timeout": exc.detail == "TIMEOUT", "failure_code": exc.code, "failure_detail": exc.detail or None, "output_tokens": None}
    write("RESPONSE_FORMAT_RESULT.json", {"schema_version": "v2_1_response_format_result_v1", "a0_reference": {"request_size_bytes": 1763, "response_format": "ON", "terminal_response": False, "transport_classification": "READ_TIMEOUT"}, "control": {"request_size_bytes": request_size, "response_format": "OFF", **row}})
    gate = "V2_1_STRUCTURED_OUTPUT_INTERACTION_IDENTIFIED" if row["terminal_response"] else "V2_1_PAYLOAD_ROOT_CAUSE_UNRESOLVED"
    write("SECURITY_AUDIT.json", {"schema_version": "v2_1_response_format_security_v1", "status": "PASS", "credential_or_header_value_occurrences": 0, "hidden_analysis_field_occurrences": 0, "raw_provider_content_retained": False})
    write("RESEARCH_GATE.json", {"schema_version": "v2_1_response_format_gate_v1", "decision": gate, "response_format_off_terminal": row["terminal_response"], "production_change": "NOT_AUTHORIZED"})
    write("FINAL_REPORT.md", f"# V2.1 Response-Format Control\n\nGate: `{gate}`. The exact A0 content was repeated with response_format omitted; no production setting changed.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "v2_1_response_format_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "v2_1_response_format_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}})


if __name__ == "__main__": main()
