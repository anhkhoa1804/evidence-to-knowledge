"""Minimal synthetic Qwen response-shape probe; prints structural metadata only."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.model_config import load_dotenv_file
from cdoi.provider_output import ProviderOutputError, normalize_openai_turn
from cdoi.qwen_rca import QwenRCAConfig
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model
from cdoi.rca_agent_v2 import _profile_view
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools


def safe_shape(response, requested_model, *, response_format_requested, latency_ms, retries):
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    shape = {
        "requested_model": requested_model,
        "resolved_model": response.get("model") if isinstance(response.get("model"), str) else None,
        "http_status": 200,
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
        "message_present": isinstance(message, dict),
        "message_content_present": content is not None,
        "message_content_type": type(content).__name__ if content is not None else None,
        "message_content_length": len(content) if isinstance(content, (str, list)) else None,
        "tool_calls_present": bool(message.get("tool_calls")) if isinstance(message, dict) else False,
        "tool_call_count": len(message.get("tool_calls") or []) if isinstance(message, dict) else 0,
        "response_format_requested": response_format_requested,
        "provider_attempt_count": retries + 1,
        "latency_ms": latency_ms,
        "usage_completion_tokens": (response.get("usage") or {}).get("completion_tokens") if isinstance(response.get("usage"), dict) else None,
    }
    if isinstance(content, str):
        shape.update({
            "markdown_fence_detected": "```" in content,
            "leading_text_detected": bool(content.strip()) and not content.lstrip().startswith(("{", "\"", "```")),
            "trailing_text_detected": bool(content.strip()) and not content.rstrip().endswith(("}", "\"", "```")),
        })
        try:
            parsed = json.loads(content)
            shape["json_parseable"] = True
            shape["parsed_top_level_type"] = type(parsed).__name__
        except json.JSONDecodeError:
            shape["json_parseable"] = False
            shape["parsed_top_level_type"] = None
    try:
        turn = normalize_openai_turn(response, requested_model)
        shape["normalization_path"] = turn.normalization_path
        shape["validation_stage_reached"] = "CONTENT_NORMALIZED"
        shape["validation_error_code"] = None
        shape["validation_error_path"] = None
    except ProviderOutputError as exc:
        shape["normalization_path"] = None
        shape["validation_stage_reached"] = "PROVIDER_NORMALIZATION"
        shape["validation_error_code"] = exc.code
        shape["validation_error_path"] = exc.path
    return shape


def main() -> None:
    load_dotenv_file(ROOT / ".env", override=False)
    config = QwenRCAConfig.from_internal_gateway_environment()
    if config.status() != "QWEN_LIVE_READY":
        print(json.dumps({"status": config.status()}))
        return
    model = QwenRCAAgentV2Model(config)
    requests = () if any(flag in sys.argv for flag in ("--large", "--large4096", "--no-thinking", "--omit-limit")) else (
        ("P1_PLAIN_TEXT", "Reply with exactly OK.", None),
        ("P2_DIRECT_JSON_OBJECT", 'Return exactly this JSON object: {"probe":"ok"}.', {"type": "json_object"}),
    )
    for probe_id, prompt, response_format in requests:
        payload = {"model": config.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 512}
        if response_format is not None:
            payload["response_format"] = response_format
        response, latency, retries = model._post(payload)
        print(json.dumps({"probe_id": probe_id, **safe_shape(response, config.model, response_format_requested=response_format, latency_ms=latency, retries=retries)}, sort_keys=True))
    fixture = ROOT / "tests/fixtures/preprocessing_demo"
    prepared = RCAOrchestrator().prepare(fixture / "manifest.yaml", "inc-001", ROOT / "experiments/archive/v3_phase2_16r_qwen_output_contract/PROBE_INDEX.sqlite")
    try:
        tools = ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store)
        incident_id = prepared.context.incident.incident_id
        h1_ids = sorted(item.candidate_id for item in prepared.h1_candidates)
        request = {
            "incident": tools.get_incident_summary(incident_id),
            "candidates": tools.get_candidates(incident_id, limit=20),
            "preloaded_candidate_profiles": [_profile_view(p) for p in tools.profiles if p.candidate_id in h1_ids],
            "h1_comparison": {"compared_candidate_ids": h1_ids, "comparison_basis": "PRELOADED_H1_CANDIDATE_EVIDENCE_PROFILES"},
            "candidate_source": CandidateSourceMode.H1_THEN_H5_FALLBACK.value,
            "tool_schema_version": "read_only_rca_tools_v2",
            "report_schema": "RCAReport plus V2 abstention fields",
        }
        model._messages = [{"role": "system", "content": model.system_prompt}, {"role": "user", "content": json.dumps(request, sort_keys=True)}]
        budgets = (4096,) if "--large4096" in sys.argv else (2048,) if "--large" in sys.argv else (512,)
        if any(flag in sys.argv for flag in ("--large", "--large4096", "--omit-limit")):
            model.config = replace(config, timeout_seconds=90, max_retries=0)
        for budget in budgets:
            body = model._body()
            body["max_tokens"] = budget
            if "--omit-limit" in sys.argv:
                body.pop("max_tokens")
            if "--no-thinking" in sys.argv:
                body["enable_thinking"] = False
            response, latency, retries = model._post(body)
            print(json.dumps({"probe_id": "P0_SYNTHETIC_V2_FIRST_TURN", "max_tokens": budget, "enable_thinking_requested": body.get("enable_thinking"), **safe_shape(response, config.model, response_format_requested={"type": "json_object"}, latency_ms=latency, retries=retries)}, sort_keys=True))
    finally:
        prepared.store.close()


if __name__ == "__main__":
    main()
