"""Minimal live V2.1 status-contract qualification; never reads RCAEval cases."""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model
from cdoi.rca_agent_v2_1 import RCAAgentV21
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools

OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_1_status_contract"
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"
MODEL = "vllm/Qwen3.8-27B"


def write(name: str, data: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def prepare_tools():
    prepared = RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / "QUALIFICATION_INDEX.sqlite")
    h1 = {item.candidate_id for item in prepared.h1_candidates}
    expanded = tuple(item for item in prepared.h5_candidates if item.candidate_id not in h1)
    return prepared, ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded)


def valid_abstention(request: Mapping[str, Any]) -> dict[str, Any]:
    ids = [item["candidate_id"] for item in request["preloaded_candidate_profiles"]]
    return {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None, "alternative_hypotheses": [],
        "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
        "reasoning_summary": "Synthetic contract qualification only.", "limitations": ["SYNTHETIC_CONTRACT_PROBE"],
        "abstention_reason": "MISSING_DISTINGUISHING_SIGNAL", "investigated_candidate_ids": ids,
        "comparison_completed": True, "missing_or_conflicting_evidence": ["SYNTHETIC_EVIDENCE_GAP"]}


def valid_hypothesis(request: Mapping[str, Any]) -> dict[str, Any]:
    candidate = request["candidates"]["items"][0]["candidate_id"]
    return {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": candidate,
        "statement": "Synthetic non-causal hypothesis only.", "supporting_evidence_ids": [],
        "limitations": ["SYNTHETIC_CONTRACT_PROBE"], "model_self_assessment": "LOW"},
        "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
        "reasoning_summary": "Synthetic contract qualification only.", "limitations": ["SYNTHETIC_CONTRACT_PROBE"]}


class LiveRepairModel:
    """Fixture first turn plus live V2.1 bounded repair, without incident data retention."""
    prompt_version = "rca_agent_qwen_v2_1"
    system_prompt = QwenRCAAgentV21Model.system_prompt

    def __init__(self, live: QwenRCAAgentV21Model, first: Any, repaired: Any, *, live_first: bool = False) -> None:
        self.live, self.first, self.repaired = live, first, repaired
        self.live_first = live_first
        self.request: Mapping[str, Any] | None = None; self.repair_calls = 0

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.request = request
        value = self.first(request) if callable(self.first) else self.first
        if self.live_first:
            response = self.live.complete([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": "Return exactly this JSON object without prose. It is a synthetic contract fixture: " + json.dumps(value, sort_keys=True)},
            ], response_format={"type": "json_object"})
            content = response["message"].get("content")
            if not isinstance(content, str): raise ValueError("QWEN_CONTENT_NORMALIZATION_FAILURE")
            value = json.loads(content)
            if not isinstance(value, Mapping): raise ValueError("QWEN_RCA_SCHEMA_FAILURE")
        return {"report": dict(value)}

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.repair_calls += 1
        wanted = self.repaired(request) if callable(self.repaired) else self.repaired
        response = self.live.complete([
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "Return exactly this JSON object without prose. It is a synthetic contract fixture: " + json.dumps(wanted, sort_keys=True)},
        ], response_format={"type": "json_object"})
        content = response["message"].get("content")
        if not isinstance(content, str): raise ValueError("QWEN_CONTENT_NORMALIZATION_FAILURE")
        parsed = json.loads(content)
        if not isinstance(parsed, Mapping): raise ValueError("QWEN_RCA_SCHEMA_FAILURE")
        return {"report": dict(parsed)}


class UnrecoverableModel(LiveRepairModel):
    def repair_output(self, raw_output: Mapping[str, Any], error_code: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.repair_calls += 1
        return {"report": {"status": "ABSTAIN"}}


class ForcedToolV21(QwenRCAAgentV21Model):
    """Live native-tool transport with a synthetic forced first tool choice."""
    def __init__(self, config: QwenRCAConfig) -> None:
        super().__init__(config, max_output_tokens=8192); self.round_number = 0
    def _body(self) -> dict[str, Any]:
        body = super()._body()
        body["tool_choice"] = ({"type": "function", "function": {"name": "get_incident_summary"}}
                               if self.round_number == 0 else "none")
        self.round_number += 1
        return body


def safe_trace(probe_id: str, model: Any, raw: Mapping[str, Any] | None, *, repair_attempted: bool,
               repair_result: str | None, final_status: str | None, technical: str | None) -> dict[str, Any]:
    raw_status = raw.get("status") if isinstance(raw, Mapping) and "status" in raw else None
    diag = getattr(model, "last_contract_diagnostic", {})
    return {"probe_id": probe_id, "raw_top_level_keys": sorted(raw) if isinstance(raw, Mapping) else [],
        "raw_status_present": isinstance(raw, Mapping) and "status" in raw,
        "raw_status_type": type(raw_status).__name__ if raw_status is not None else None,
        "normalized_status": raw_status if isinstance(raw_status, str) and raw_status in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"} else None,
        "required_field_presence": {name: isinstance(raw, Mapping) and name in raw for name in ("status", "primary_hypothesis", "abstention_reason", "investigated_candidate_ids", "comparison_completed", "missing_or_conflicting_evidence", "limitations")},
        "tool_calls_present": bool((diag or {}).get("tool_call_count")), "validation_error": technical,
        "repair_eligible": bool(isinstance(raw, Mapping)), "repair_attempted": repair_attempted,
        "repair_result": repair_result, "final_status": final_status, "report_accepted": final_status in {"RCA_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"},
        "technical_failure_code": technical}


def run_fixture_probe(probe_id: str, tools: ReadOnlyRCATools, config: QwenRCAConfig, first: Any, repaired: Any,
                      *, expected: str, live_first: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    live = QwenRCAAgentV21Model(config, max_output_tokens=8192)
    model: Any = UnrecoverableModel(live, first, repaired) if expected == "TECHNICAL_FAILURE" else LiveRepairModel(live, first, repaired, live_first=live_first)
    initial = first if isinstance(first, Mapping) else None
    try:
        report, trace = RCAAgentV21(model).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK, live.public_metadata())
        repair = (trace.get("repairs") or [{}])[0]
        good = report.status == expected and (expected == "TECHNICAL_FAILURE" or (model.repair_calls == 1 if initial != repaired else True))
        result = {"probe_id": probe_id, "status": "PASS" if good else "FAIL", "final_status": report.status,
                  "repair_attempted": model.repair_calls == 1, "repair_result": repair.get("status"),
                  "validation_error_code": repair.get("error_code"), "resolved_model": live.last_response_metadata.get("resolved_model"),
                  "provider_interactions": len(live.transport_history), "error": None if good else "UNEXPECTED_FINAL_STATUS"}
        return result, safe_trace(probe_id, live, initial, repair_attempted=model.repair_calls == 1,
                                  repair_result=repair.get("status"), final_status=report.status, technical=None)
    except (ValueError, QwenRCAError, json.JSONDecodeError) as exc:
        code = str(exc)
        good = expected == "TECHNICAL_FAILURE" and "RCA_REPORT_CONTRACT_FAILURE" in code
        return {"probe_id": probe_id, "status": "PASS" if good else "FAIL", "final_status": "TECHNICAL_FAILURE",
                "repair_attempted": model.repair_calls == 1, "repair_result": "FAILED", "validation_error_code": code,
                "resolved_model": live.last_response_metadata.get("resolved_model"), "provider_interactions": len(live.transport_history),
                "error": None if good else code}, safe_trace(probe_id, live, initial, repair_attempted=model.repair_calls == 1,
                    repair_result="FAILED", final_status="TECHNICAL_FAILURE", technical=code)


def main() -> None:
    if (OUT / "LIVE_PROBE_RESULTS.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_V21_QUALIFICATION")
    load_dotenv_file(ROOT / ".env", override=False)
    base = QwenRCAConfig.from_internal_gateway_environment()
    if base.status() != "QWEN_LIVE_READY": raise RuntimeError("QWEN_PROVIDER_UNCONFIGURED")
    config = replace(base, timeout_seconds=120)
    if config.model != MODEL or config.max_retries != 1: raise RuntimeError("QUALIFIED_PROVIDER_CONFIG_MISMATCH")
    OUT.mkdir(parents=True, exist_ok=True)
    write("PREREGISTRATION.json", {"schema_version": "v3_phase2_16_v21_preregistration_v1", "scope": "SYNTHETIC_MINIMAL_LIVE_STATUS_CONTRACT_ONLY",
        "model": MODEL, "temperature": 0, "max_output_tokens": 8192, "timeout_seconds": 120, "max_retries": 1,
        "probes": [f"P{i}" for i in range(1, 13)], "forbidden": ["Phase2.11 development batch", "Phase2.12", "telemetry-only", "stability", "policy tuning"]})
    prepared, tools = prepare_tools(); rows: list[dict[str, Any]] = []; traces: list[dict[str, Any]] = []
    try:
        # P1/P2 use a direct live completion as first turn; all malformed
        # report probes deliberately traverse the live bounded repair path.
        for probe_id, factory, expected in (("P1_VALID_ABSTENTION", valid_abstention, "INSUFFICIENT_EVIDENCE"),
                                           ("P2_VALID_HYPOTHESIS", valid_hypothesis, "RCA_HYPOTHESIS")):
            result, trace = run_fixture_probe(probe_id, tools, config, factory, factory, expected=expected, live_first=True)
            rows.append(result); traces.append(trace)
        rows_trace = [
            ("P3_MISSING_STATUS", {}, valid_abstention, "INSUFFICIENT_EVIDENCE"),
            ("P4_UNKNOWN_STATUS", {"status": "ABSTAIN"}, valid_abstention, "INSUFFICIENT_EVIDENCE"),
            ("P5_ABSTENTION_MISSING_REASON", lambda req: {k: v for k, v in valid_abstention(req).items() if k != "abstention_reason"}, valid_abstention, "INSUFFICIENT_EVIDENCE"),
            ("P6_HYPOTHESIS_MISSING_PRIMARY", {"status": "RCA_HYPOTHESIS", "primary_hypothesis": None, "limitations": ["synthetic"]}, valid_hypothesis, "RCA_HYPOTHESIS"),
            ("P7_REPAIRABLE_INVALID_STATUS", {"status": "UNKNOWN"}, valid_abstention, "INSUFFICIENT_EVIDENCE"),
            ("P8_REPAIRABLE_ABSTENTION", lambda req: {k: v for k, v in valid_abstention(req).items() if k != "missing_or_conflicting_evidence"}, valid_abstention, "INSUFFICIENT_EVIDENCE"),
            ("P9_UNRECOVERABLE_INVALID_REPORT", {"status": "ABSTAIN"}, {"status": "ABSTAIN"}, "TECHNICAL_FAILURE"),
        ]
        for probe_id, first, repaired, expected in rows_trace:
            result, trace = run_fixture_probe(probe_id, tools, config, first, repaired, expected=expected)
            rows.append(result); traces.append(trace)
        # P10/P11 prove semantic validation is still strict through V2.1.
        for probe_id, builder, expected_error in (("P10_UNKNOWN_EVIDENCE", lambda req: {**valid_hypothesis(req), "supporting_evidence_ids": ["unknown-evidence"]}, "RCA_REPORT_UNKNOWN_EVIDENCE"),
                                                   ("P11_UNKNOWN_CANDIDATE", lambda req: {**valid_hypothesis(req), "primary_hypothesis": {**valid_hypothesis(req)["primary_hypothesis"], "candidate_id": "unknown-candidate"}}, "RCA_REPORT_UNKNOWN_CANDIDATE")):
            try:
                report, _ = RCAAgentV21(LiveRepairModel(QwenRCAAgentV21Model(config, max_output_tokens=8192), builder, builder)).investigate(tools)
                rows.append({"probe_id": probe_id, "status": "FAIL", "error": "UNKNOWN_ID_ACCEPTED", "final_status": report.status})
                traces.append(safe_trace(probe_id, None, None, repair_attempted=False, repair_result=None, final_status=report.status, technical="UNKNOWN_ID_ACCEPTED"))
            except ValueError as exc:
                rows.append({"probe_id": probe_id, "status": "PASS" if expected_error in str(exc) else "FAIL", "validation_error_code": str(exc), "execution": "V21_LOCAL_SEMANTIC_VALIDATOR"})
                traces.append(safe_trace(probe_id, None, None, repair_attempted=True, repair_result="FAILED", final_status="TECHNICAL_FAILURE", technical=str(exc)))
        # P12 is the real native tool envelope and V2.1 agent loop.
        live_tool = ForcedToolV21(config)
        try:
            report, trace = RCAAgentV21(live_tool).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK, live_tool.public_metadata())
            names = [x["tool_name"] for x in trace["tool_calls"]]
            ok = names == ["get_incident_summary"] and report.status in {"INSUFFICIENT_EVIDENCE", "RCA_HYPOTHESIS"}
            rows.append({"probe_id": "P12_NATIVE_TOOL_THEN_VALID_REPORT", "status": "PASS" if ok else "FAIL", "tool_names": names,
                         "final_status": report.status, "resolved_model": live_tool.last_response_metadata.get("resolved_model"),
                         "provider_interactions": len(live_tool.transport_history), "error": None if ok else "TOOL_OR_REPORT_INVALID"})
            traces.append(safe_trace("P12_NATIVE_TOOL_THEN_VALID_REPORT", live_tool, None, repair_attempted=False,
                                     repair_result=None, final_status=report.status, technical=None if ok else "TOOL_OR_REPORT_INVALID"))
        except (ValueError, QwenRCAError) as exc:
            rows.append({"probe_id": "P12_NATIVE_TOOL_THEN_VALID_REPORT", "status": "FAIL", "error": str(exc)})
            traces.append(safe_trace("P12_NATIVE_TOOL_THEN_VALID_REPORT", live_tool, None, repair_attempted=False,
                                     repair_result=None, final_status="TECHNICAL_FAILURE", technical=str(exc)))
    finally:
        prepared.store.close()
    write("LIVE_PROBE_RESULTS.json", {"schema_version": "v3_phase2_16_v21_live_probes_v1", "probes": rows,
        "passed": sum(x["status"] == "PASS" for x in rows), "total": len(rows), "complete": True})
    write("V2_1_REPORT_CONTRACT_TRACE.json", {"schema_version": "v3_phase2_16_v21_trace_v1", "probes": traces})


if __name__ == "__main__": main()
