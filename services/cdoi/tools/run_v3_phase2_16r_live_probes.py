"""Synthetic-only live gateway qualification for the V2 provider boundary.

This script does not load RCAEval or Phase 2.11/2.12 case data. It persists
structural response metadata and validated statuses, never raw model text.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.model_config import load_dotenv_file
from cdoi.provider_output import ProviderOutputError, normalize_openai_turn
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model
from cdoi.rca_agent_v2 import RCAAgentV2, V2AgentBudget
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools

OUT = ROOT / "experiments/archive/v3_phase2_16r_qwen_output_contract_live_20260924"
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"
MODEL = "vllm/Qwen3.8-27B"


def write(name: str, data: Any) -> None:
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def response_shape(response: Mapping[str, Any], *, probe_id: str, response_format: Any,
                   latency_ms: float, retries: int) -> dict[str, Any]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") if isinstance(choice, Mapping) else None
    content = message.get("content") if isinstance(message, Mapping) else None
    result: dict[str, Any] = {
        "probe_id": probe_id, "requested_model": MODEL,
        "resolved_model": response.get("model") if isinstance(response.get("model"), str) else None,
        "http_status": 200,
        "finish_reason": choice.get("finish_reason") if isinstance(choice, Mapping) else None,
        "message_present": isinstance(message, Mapping),
        "message_content_present": content is not None,
        "message_content_type": type(content).__name__ if content is not None else None,
        "message_content_length": len(content) if isinstance(content, (str, list)) else None,
        "tool_calls_present": bool(message.get("tool_calls")) if isinstance(message, Mapping) else False,
        "tool_call_count": len(message.get("tool_calls") or []) if isinstance(message, Mapping) and isinstance(message.get("tool_calls") or [], list) else None,
        "response_format_requested": response_format,
        "json_parseable": False, "parsed_top_level_type": None,
        "markdown_fence_detected": "```" in content if isinstance(content, str) else False,
        "leading_text_detected": bool(content.strip()) and not content.lstrip().startswith(("{", "\"", "```")) if isinstance(content, str) else False,
        "trailing_text_detected": bool(content.strip()) and not content.rstrip().endswith(("}", "\"", "```")) if isinstance(content, str) else False,
        "provider_attempt_count": retries + 1, "latency_ms": latency_ms,
        "completion_tokens": (response.get("usage") or {}).get("completion_tokens") if isinstance(response.get("usage"), Mapping) else None,
    }
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            result["json_parseable"] = True
            result["parsed_top_level_type"] = type(parsed).__name__
        except json.JSONDecodeError:
            pass
    try:
        turn = normalize_openai_turn(response, MODEL)
        result.update({"normalization_path": turn.normalization_path,
                       "validation_stage_reached": "CONTENT_NORMALIZED", "validation_error_code": None,
                       "validation_error_path": None, "repair_eligible": bool(turn.content and not turn.tool_calls)})
    except ProviderOutputError as exc:
        result.update({"normalization_path": None, "validation_stage_reached": "PROVIDER_NORMALIZATION",
                       "validation_error_code": exc.code, "validation_error_path": exc.path, "repair_eligible": False})
    return result


def report_fixture(status: str, candidate_id: str = "synthetic-candidate-1", evidence_id: str = "synthetic-evidence-1") -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": status, "primary_hypothesis": None, "alternative_hypotheses": [],
        "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
        "reasoning_summary": "Synthetic contract probe; no causal conclusion.",
        "limitations": ["SYNTHETIC_CONTRACT_PROBE"], "abstention_reason": None,
    }
    if status == "INSUFFICIENT_EVIDENCE":
        report.update({"abstention_reason": "MISSING_DISTINGUISHING_SIGNAL",
                       "investigated_candidate_ids": [candidate_id], "comparison_completed": True,
                       "missing_or_conflicting_evidence": ["SYNTHETIC_EVIDENCE_IS_NOT_A_CAUSAL_TEST"]})
    else:
        report["primary_hypothesis"] = {"candidate_id": candidate_id,
            "statement": "Synthetic evidence-backed hypothesis only.",
            "supporting_evidence_ids": [evidence_id],
            "limitations": ["NOT_CAUSALLY_PROVEN"], "model_self_assessment": "LOW"}
        report["supporting_evidence_ids"] = [evidence_id]
    return report


def validate_report(raw: Mapping[str, Any], status: str, *, candidate_id: str = "synthetic-candidate-1", evidence_id: str = "synthetic-evidence-1") -> None:
    agent = RCAAgentV2(QwenRCAAgentV2Model.__new__(QwenRCAAgentV2Model))
    if status == "INSUFFICIENT_EVIDENCE": agent._abstention_contract(raw, {candidate_id})
    report = agent._report("synthetic-incident", raw, 0, {"provider": "DMP_INTERNAL_QWEN"})
    report.validate({candidate_id}, {evidence_id})
    if report.status != status: raise ValueError("UNEXPECTED_REPORT_STATUS")


class ForcedToolModel(QwenRCAAgentV2Model):
    """V2 adapter with only synthetic tool-choice control for qualification."""
    def __init__(self, config: QwenRCAConfig, sequence: tuple[str, ...]) -> None:
        super().__init__(config, max_output_tokens=8192)
        self.sequence = sequence
        self.round_number = 0

    def _body(self) -> dict[str, Any]:
        body = super()._body()
        if self.round_number < len(self.sequence):
            body["tool_choice"] = {"type": "function", "function": {"name": self.sequence[self.round_number]}}
        else:
            body["tool_choice"] = "none"
        self.round_number += 1
        return body


class FixtureThenLiveRepair:
    prompt_version = "rca_agent_qwen_v2"
    system_prompt = QwenRCAAgentV2Model.system_prompt

    def __init__(self, live: QwenRCAAgentV2Model):
        self.live = live
        self.initial: Mapping[str, Any] | None = None
        self.repair_calls = 0

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.initial = request
        ids = [p["candidate_id"] for p in request["preloaded_candidate_profiles"]]
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                            "alternative_hypotheses": [], "supporting_evidence_ids": [],
                            "contradictory_evidence_ids": [], "reasoning_summary": "Synthetic malformed report.",
                            "limitations": ["SYNTHETIC_FIXTURE"], "abstention_reason": "MISSING_DISTINGUISHING_SIGNAL",
                            "investigated_candidate_ids": ids, "missing_or_conflicting_evidence": ["SYNTHETIC_EVIDENCE_GAP"]}}

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.repair_calls += 1
        return self.live.repair_output(raw_output, error_code, request)


def prepared_tools():
    prepared = RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / "SYNTHETIC_INDEX.sqlite")
    h1 = {c.candidate_id for c in prepared.h1_candidates}
    expanded = tuple(c for c in prepared.h5_candidates if c.candidate_id not in h1)
    tools = ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded)
    return prepared, tools


def main() -> None:
    if (OUT / "LIVE_PROBE_RESULTS.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_COMPLETED_LIVE_PROBES")
    load_dotenv_file(ROOT / ".env", override=False)
    base = QwenRCAConfig.from_internal_gateway_environment()
    if base.status() != "QWEN_LIVE_READY": raise RuntimeError("QWEN_PROVIDER_UNCONFIGURED")
    if base.model != MODEL: raise RuntimeError("UNEXPECTED_MODEL_ROUTE")
    config = replace(base, timeout_seconds=120)
    OUT.mkdir(parents=True, exist_ok=True)
    write("PREREGISTRATION.json", {"schema_version": "v3_phase2_16r_live_preregistration_v1", "scope": "SYNTHETIC_ONLY_PROVIDER_CONTRACT", "model": MODEL,
        "temperature": 0, "output_token_limit": 8192, "timeout_seconds": 120, "max_retries": config.max_retries,
        "probe_ids": [f"P{i}" for i in range(1, 11)], "forbidden": "NO_PHASE211_OR_PHASE212_CASE_ACCESS_NO_RCA_QUALITY_BATCH"})
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    model = QwenRCAAgentV2Model(config, max_output_tokens=8192)

    def run_simple(probe_id: str, prompt: str, response_format: Mapping[str, Any] | None, expected: str) -> None:
        payload: dict[str, Any] = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 8192}
        if response_format: payload["response_format"] = dict(response_format)
        response, latency, retries = model._post(payload)
        trace = response_shape(response, probe_id=probe_id, response_format=response_format, latency_ms=latency, retries=retries)
        traces.append(trace)
        try:
            turn = normalize_openai_turn(response, MODEL)
            if expected == "PLAIN":
                if not turn.content or not turn.content.strip(): raise ValueError("EMPTY_PLAIN_TEXT")
            elif expected == "JSON":
                if not isinstance(json.loads(turn.content or ""), dict): raise ValueError("JSON_OBJECT_REQUIRED")
            else:
                parsed = json.loads(turn.content or "")
                validate_report(parsed, expected)
            status, error = "PASS", None
        except (ProviderOutputError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            status, error = "FAIL", str(exc) if isinstance(exc, (ProviderOutputError, ValueError)) else type(exc).__name__
        rows.append({"probe_id": probe_id, "status": status, "validation_error_code": error, "resolved_model": trace["resolved_model"], "provider_attempt_count": retries + 1, "latency_ms": latency})
        write("LIVE_PROBE_RESULTS.json", {"schema_version": "v3_phase2_16r_live_probes_v1", "probes": rows, "complete": False})
        write("LIVE_OUTPUT_CONTRACT_TRACE.json", {"schema_version": "v3_phase2_16r_trace_v1", "probes": traces})

    run_simple("P1_PLAIN_TEXT", "Reply with exactly OK.", None, "PLAIN")
    run_simple("P2_DIRECT_JSON_OBJECT", 'Return exactly this JSON object and no prose: {"probe":"ok"}.', {"type": "json_object"}, "JSON")
    insufficient = report_fixture("INSUFFICIENT_EVIDENCE")
    hypothesis = report_fixture("RCA_HYPOTHESIS")
    run_simple("P3_MINIMAL_INSUFFICIENT_REPORT", "Return exactly this JSON object without changes: " + json.dumps(insufficient, sort_keys=True), {"type": "json_object"}, "INSUFFICIENT_EVIDENCE")
    run_simple("P4_MINIMAL_RCA_HYPOTHESIS", "Return exactly this JSON object without changes: " + json.dumps(hypothesis, sort_keys=True), {"type": "json_object"}, "RCA_HYPOTHESIS")

    prepared, tools = prepared_tools()
    try:
        for probe_id, sequence in (("P5_NATIVE_TOOL_CALL", ("get_incident_summary",)),
                                   ("P6_SERIAL_TOOL_CONTINUATION", ("get_incident_summary", "get_candidates"))):
            live = ForcedToolModel(config, sequence)
            try:
                report, agent_trace = RCAAgentV2(live).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK, live.public_metadata())
                names = [call["tool_name"] for call in agent_trace["tool_calls"]]
                status = "PASS" if names == list(sequence) and report.status in {"INSUFFICIENT_EVIDENCE", "RCA_HYPOTHESIS"} else "FAIL"
                error = None if status == "PASS" else "TOOL_SEQUENCE_OR_REPORT_INVALID"
            except (QwenRCAError, ValueError, KeyError, TypeError) as exc:
                status, error, names = "FAIL", str(exc), []
            rows.append({"probe_id": probe_id, "status": status, "validation_error_code": error,
                         "tool_names": names, "provider_calls": live.round_number,
                         "provider_attempt_count": live.last_transport_diagnostic.get("attempt_count"),
                         "resolved_model": live.last_response_metadata.get("resolved_model")})
            traces.append({"probe_id": probe_id, **live.last_contract_diagnostic, "tool_names": names,
                           "provider_attempt_count": live.last_transport_diagnostic.get("attempt_count"),
                           "response_format_requested": {"type": "json_object"}})
            write("LIVE_PROBE_RESULTS.json", {"schema_version": "v3_phase2_16r_live_probes_v1", "probes": rows, "complete": False})
            write("LIVE_OUTPUT_CONTRACT_TRACE.json", {"schema_version": "v3_phase2_16r_trace_v1", "probes": traces})

        repair_live = QwenRCAAgentV2Model(config, max_output_tokens=8192)
        fixture_model = FixtureThenLiveRepair(repair_live)
        try:
            report, agent_trace = RCAAgentV2(fixture_model).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK, repair_live.public_metadata())
            repair_status = agent_trace["repairs"][0]["status"] if agent_trace["repairs"] else "NOT_REACHED"
            status = "PASS" if report.status == "INSUFFICIENT_EVIDENCE" and fixture_model.repair_calls == 1 and repair_status == "SUCCEEDED" else "FAIL"
            error = None if status == "PASS" else "REPAIR_NOT_ACCEPTED"
        except (QwenRCAError, ValueError, KeyError, TypeError) as exc:
            status, error, repair_status = "FAIL", str(exc), "FAILED"
        rows.append({"probe_id": "P7_MALFORMED_REPORT_REPAIR", "status": status, "validation_error_code": error,
                     "repair_attempted": fixture_model.repair_calls == 1, "repair_success": repair_status == "SUCCEEDED",
                     "repair_error_code": "V2_ABSTENTION_H1_COMPARISON_REQUIRED",
                     "resolved_model": repair_live.last_response_metadata.get("resolved_model"),
                     "provider_attempt_count": repair_live.last_transport_diagnostic.get("attempt_count")})
        traces.append({"probe_id": "P7_MALFORMED_REPORT_REPAIR", **repair_live.last_contract_diagnostic,
                       "response_format_requested": {"type": "json_object"},
                       "provider_attempt_count": repair_live.last_transport_diagnostic.get("attempt_count")})
    finally:
        prepared.store.close()

    for probe_id, raw in (("P8_UNKNOWN_EVIDENCE_REJECTION", {**hypothesis, "supporting_evidence_ids": ["unknown-evidence"]}),
                          ("P9_UNKNOWN_CANDIDATE_REJECTION", {**hypothesis, "primary_hypothesis": {**hypothesis["primary_hypothesis"], "candidate_id": "unknown-candidate"}})):
        try:
            validate_report(raw, "RCA_HYPOTHESIS")
            status, error = "FAIL", "UNKNOWN_ID_ACCEPTED"
        except ValueError as exc:
            status, error = "PASS", str(exc)
        rows.append({"probe_id": probe_id, "status": status, "validation_error_code": error,
                     "execution": "DETERMINISTIC_LOCAL_SEMANTIC_VALIDATOR"})
    try:
        normalize_openai_turn({"choices": [{"message": {"content": '{"a":1} {"b":2}'}}]}, MODEL)
        status, error = "FAIL", "AMBIGUOUS_OUTPUT_ACCEPTED"
    except ProviderOutputError as exc:
        status, error = "PASS", exc.code
    rows.append({"probe_id": "P10_AMBIGUOUS_OUTPUT_REJECTION", "status": status, "validation_error_code": error,
                 "execution": "DETERMINISTIC_PROVIDER_NORMALIZER"})
    write("LIVE_PROBE_RESULTS.json", {"schema_version": "v3_phase2_16r_live_probes_v1", "probes": rows,
         "complete": True, "passed": sum(row["status"] == "PASS" for row in rows), "total": len(rows)})
    write("LIVE_OUTPUT_CONTRACT_TRACE.json", {"schema_version": "v3_phase2_16r_trace_v1", "probes": traces})


if __name__ == "__main__":
    main()
