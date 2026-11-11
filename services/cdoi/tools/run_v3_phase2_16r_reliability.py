"""Repeated synthetic live contract probes under the qualified provider config."""
from __future__ import annotations

import json
import statistics
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model
from cdoi.rca_agent_v2 import RCAAgentV2
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools
from run_v3_phase2_16r_live_probes import (OUT, FIXTURE, ForcedToolModel, FixtureThenLiveRepair,
                                           report_fixture, validate_report, write)

SCHEDULE = (
    "VALID_INSUFFICIENT_1", "VALID_HYPOTHESIS_1", "NATIVE_TOOL_1",
    "MALFORMED_REPAIR_1", "VALID_INSUFFICIENT_2", "NATIVE_TOOL_2",
    "VALID_HYPOTHESIS_2", "SERIAL_CONTINUATION_1", "MALFORMED_REPAIR_2",
)


def summarize_transport(history):
    return {
        "provider_interactions": len(history),
        "attempts": sum(int(row.get("attempt_count", 0)) for row in history),
        "retries": sum(int(row.get("retry_count", 0)) for row in history),
        "transport_failures": sum(row.get("status") == "FAILURE" for row in history),
        "timeouts": sum(item.get("failure_detail") == "TIMEOUT" for row in history for item in row.get("attempts", [])),
        "latencies_ms": [item["elapsed_ms"] for row in history for item in row.get("attempts", []) if "elapsed_ms" in item],
    }


def main() -> None:
    if not (OUT / "LIVE_PROBE_RESULTS.json").exists(): raise RuntimeError("BASE_LIVE_PROBES_REQUIRED")
    load_dotenv_file(ROOT / ".env", override=False)
    base = QwenRCAConfig.from_internal_gateway_environment()
    if base.status() != "QWEN_LIVE_READY": raise RuntimeError("QWEN_PROVIDER_UNCONFIGURED")
    config = replace(base, timeout_seconds=120)
    progress_file = OUT / "RELIABILITY_PROGRESS.json"
    prior = json.loads(progress_file.read_text(encoding="utf-8"))["runs"] if progress_file.exists() else []
    completed = {row["probe_id"] for row in prior}
    prepared = RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / "RELIABILITY_INDEX.sqlite")
    h1 = {item.candidate_id for item in prepared.h1_candidates}
    expanded = tuple(item for item in prepared.h5_candidates if item.candidate_id not in h1)
    tools = ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded)
    try:
        for probe_id in SCHEDULE:
            if probe_id in completed: continue
            model = None; repair_calls = 0; tool_names = []
            try:
                if probe_id.startswith("VALID_"):
                    status = "INSUFFICIENT_EVIDENCE" if "INSUFFICIENT" in probe_id else "RCA_HYPOTHESIS"
                    model = QwenRCAAgentV2Model(config, max_output_tokens=8192)
                    result = model.complete([{"role": "user", "content": "Return exactly this JSON object without changes: " + json.dumps(report_fixture(status), sort_keys=True)}], response_format={"type": "json_object"})
                    raw = json.loads(result["message"]["content"])
                    validate_report(raw, status)
                elif probe_id.startswith("NATIVE_TOOL") or probe_id.startswith("SERIAL_CONTINUATION"):
                    sequence = ("get_incident_summary", "get_candidates") if probe_id.startswith("SERIAL") else ("get_incident_summary",)
                    model = ForcedToolModel(config, sequence)
                    report, trace = RCAAgentV2(model).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK, model.public_metadata())
                    tool_names = [row["tool_name"] for row in trace["tool_calls"]]
                    if tool_names != list(sequence) or report.status not in {"INSUFFICIENT_EVIDENCE", "RCA_HYPOTHESIS"}:
                        raise ValueError("TOOL_SEQUENCE_OR_REPORT_INVALID")
                else:
                    model = QwenRCAAgentV2Model(config, max_output_tokens=8192)
                    fixture = FixtureThenLiveRepair(model)
                    report, trace = RCAAgentV2(fixture).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK, model.public_metadata())
                    repair_calls = fixture.repair_calls
                    if report.status != "INSUFFICIENT_EVIDENCE" or repair_calls != 1 or trace["repairs"][0]["status"] != "SUCCEEDED":
                        raise ValueError("BOUNDED_REPAIR_NOT_ACCEPTED")
                outcome, code = "PASS", None
            except (QwenRCAError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                outcome, code = "FAIL", str(exc) if isinstance(exc, (QwenRCAError, ValueError)) else type(exc).__name__
            transport = summarize_transport(model.transport_history if model is not None else [])
            row = {"probe_id": probe_id, "status": outcome, "failure_code": code,
                   "tool_names": tool_names, "repair_calls": repair_calls,
                   "provider_interactions": transport["provider_interactions"],
                   "attempts": transport["attempts"], "retries": transport["retries"],
                   "transport_failures": transport["transport_failures"], "timeouts": transport["timeouts"],
                   "latencies_ms": transport["latencies_ms"],
                   "normalization_error_code": model.last_contract_diagnostic.get("validation_error_code") if model else None}
            prior.append(row)
            write("RELIABILITY_PROGRESS.json", {"schema_version": "v3_phase2_16r_reliability_progress_v1", "runs": prior, "complete": False})
    finally:
        prepared.store.close()
    interactions = sum(row["provider_interactions"] for row in prior)
    latencies = [value for row in prior for value in row["latencies_ms"]]
    write("CONTRACT_RELIABILITY.json", {"schema_version": "v3_phase2_16r_contract_reliability_v1",
        "schedule": list(SCHEDULE), "runs": prior, "probe_runs": len(prior),
        "provider_interactions": interactions, "successful_probe_runs": sum(row["status"] == "PASS" for row in prior),
        "failed_probe_runs": sum(row["status"] == "FAIL" for row in prior),
        "attempts": sum(row["attempts"] for row in prior), "retries": sum(row["retries"] for row in prior),
        "transport_failures": sum(row["transport_failures"] for row in prior),
        "timeouts": sum(row["timeouts"] for row in prior),
        "normalization_failures": sum(bool(row["normalization_error_code"]) for row in prior),
        "repair_runs": sum(row["repair_calls"] > 0 for row in prior),
        "mean_successful_response_latency_ms": statistics.mean(latencies) if latencies else None,
        "median_successful_response_latency_ms": statistics.median(latencies) if latencies else None,
        "qualification_boundary": "SYNTHETIC_PROVIDER_CONTRACT_ONLY_NO_RCA_QUALITY_CLAIM"})
    write("RELIABILITY_PROGRESS.json", {"schema_version": "v3_phase2_16r_reliability_progress_v1", "runs": prior, "complete": True})


if __name__ == "__main__":
    main()
