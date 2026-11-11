"""Bounded, label-free data acceptance and alternate-backend qualification.

This runner never opens Phase 2.12 material.  `data` reads only non-label
columns of the consumed Phase 2.11 RCAEval pilot.  `runtime` uses synthetic
preprocessing fixtures and the already-configured local OpenAI-compatible
router; its credential is read in-process and never written to an artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError  # noqa: E402
from cdoi.qwen_rca_v2_1 import QwenRCAAgentV21Model  # noqa: E402
from cdoi.rca_agent_v2_1 import RCAAgentV21  # noqa: E402
from cdoi.rca_agent_v2_2 import RCAAgentV22  # noqa: E402
from cdoi.staged_rca_backend_v2_2 import StagedRCAAgentV22Model  # noqa: E402
from cdoi.rca_agent_v2_3 import RCAAgentV23  # noqa: E402
from cdoi.staged_rca_backend_v2_3 import StagedRCAAgentV23Model, TOOL_ARGUMENTS  # noqa: E402
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools  # noqa: E402
from cdoi.rca_investigation import InvestigationMode, PreparedRCAInvestigation  # noqa: E402
from cdoi.rcaeval_evaluation import RCAEvalCase, adapt_cached_case_to_store, normalize_service_id  # noqa: E402
from cdoi.hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses  # noqa: E402
from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder  # noqa: E402
from cdoi.rca_agent_v2 import V2AgentBudget  # noqa: E402
from cdoi.staged_rca_backend_v2_2 import ALLOWED_TOOLS  # noqa: E402

OUT = ROOT / "experiments/archive/v3_rca_blocker_resolution_20260925"
DATA = ROOT / "data/benchmarks/external/rcaeval"
REVISION = "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e"
SPLIT = ROOT / "experiments/archive/v3_phase2_10e_rcaeval/CASE_SPLIT.json"
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"
ROUTER_DB = Path(os.environ.get("APPDATA", "")) / "9router/db/data.sqlite"
MODEL = os.environ.get("CDOI_RESOLUTION_MODEL", "kr/qwen3-coder-next")
TOOL_ROUND_FORMAT = os.environ.get("CDOI_RESOLUTION_TOOL_FORMAT", "frozen_json_object")
TIMEOUT_SECONDS = int(os.environ.get("CDOI_RESOLUTION_TIMEOUT_SECONDS", "45"))


def dump(name: str, value: Any) -> None:
    dump_in(OUT, name, value)


def dump_in(directory: Path, name: str, value: Any) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    if target.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{name}")
    target.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def overlap(path: Path, column: str, lo: int, hi: int, *, millis: bool = False) -> tuple[int, int]:
    table = pq.read_table(path, columns=[column])
    values = table[column]
    if millis:
        lo, hi = lo * 1000, hi * 1000 + 999
    bounded = pc.and_(pc.greater_equal(values, lo), pc.less_equal(values, hi))
    return len(table), int(pc.sum(pc.cast(bounded, "int64")).as_py() or 0)


def validate_data() -> None:
    if not SPLIT.exists() or not (DATA / "cases.parquet").exists():
        raise RuntimeError("RCA_EVAL_DEVELOPMENT_SOURCE_MISSING")
    pilot = json.loads(SPLIT.read_text(encoding="utf-8"))["pilot_case_ids"]
    pilot_set = set(pilot)
    if len(pilot) != 12 or len(pilot_set) != 12:
        raise RuntimeError("FROZEN_PILOT_POPULATION_MISMATCH")
    # Explicit column projection prevents the root-cause/fault columns from
    # entering the evidence path or any pre-evaluation artifact.
    safe_columns = ["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]
    rows = {row["case"]: row for row in pq.read_table(DATA / "cases.parquet", columns=safe_columns).to_pylist()
            if row["case"] in pilot_set}
    if set(rows) != pilot_set:
        raise RuntimeError("PILOT_CASE_INDEX_MISMATCH")
    records, hashes = [], {"cases.parquet": digest(DATA / "cases.parquet"), "CASE_SPLIT.json": digest(SPLIT)}
    for case_id in pilot:
        row = rows[case_id]
        injection = row["inject_time"]
        if not isinstance(injection, int):
            raise RuntimeError(f"INVALID_INJECTION_TIME:{case_id}")
        lo, hi = injection - 300, injection + 600
        source = DATA / REVISION / case_id
        modality = {}
        for name, column, millis in (("logs", "timestamp", False), ("metrics", "time", False),
                                     ("traces", "startTimeMillis", True)):
            path = source / f"{name}.parquet"
            if not path.is_file():
                modality[name] = {"status": "MISSING", "rows": 0, "window_rows": 0}
                continue
            total, matched = overlap(path, column, lo, hi, millis=millis)
            modality[name] = {"status": "PRESENT", "rows": total, "window_rows": matched}
            hashes[str(path.relative_to(DATA)).replace("\\", "/")] = digest(path)
        valid_window = isinstance(row["time_start"], int) and isinstance(row["time_end"], int) and row["time_start"] <= lo <= hi <= row["time_end"]
        records.append({"case_id": case_id, "dataset": row["dataset"], "system": row["system"],
                        "window_start": lo, "window_end": hi, "valid_index_window": valid_window,
                        "modalities": modality, "aligned_modality_count": sum(v["window_rows"] > 0 for v in modality.values())})
    accepted = all(r["valid_index_window"] and r["aligned_modality_count"] >= 1 for r in records)
    freeze = {"schema_version": "rca_blocker_dataset_freeze_v1", "dataset": "RCAEval RE2-OB",
              "dataset_revision": REVISION, "role": "CONSUMED_DEVELOPMENT_DATA",
              "pilot_case_ids": pilot, "case_count": len(pilot), "case_index_sha256": hashes["cases.parquet"],
              "split_sha256": hashes["CASE_SPLIT.json"], "evidence_file_sha256": hashes,
              "window_policy": "ORACLE_WINDOW_INJECT_MINUS_300_PLUS_600_SECONDS",
              "label_columns_excluded": ["root_cause_service", "fault", "root_cause_indicator"],
              "labels_opened": False, "protected_phase2_12_opened": False,
              "selection_policy": "PREEXISTING_FROZEN_PHASE2_11_PILOT_NO_NEW_SELECTION"}
    dump("DATASET_FREEZE.json", freeze)
    dump("DATA_DELIVERY_VALIDATION.json", {"schema_version": "rca_blocker_data_validation_v1",
         "accepted": accepted, "status": "EVALUABLE_RCA_DATA_AVAILABLE" if accepted else "DATA_NOT_ACCEPTED",
         "rows": records, "label_free": True,
         "modalities_with_aligned_evidence": dict(Counter(name for r in records for name, v in r["modalities"].items() if v["window_rows"] > 0))})
    dump("ANTI_LEAKAGE_AUDIT.json", {"schema_version": "rca_blocker_anti_leakage_v1",
         "pre_freeze_case_index_columns": safe_columns, "ground_truth_columns_read": [],
         "ground_truth_available_only_after_prediction_freeze": True,
         "phase2_12_protected_per_case_access": False,
         "dataset_role": "CONSUMED_DEVELOPMENT_DATA_NOT_INDEPENDENT_VALIDATION"})
    dump("DATA_PROVENANCE.json", {"schema_version": "rca_blocker_data_provenance_v1",
         "source": "phamquiluan/RCAEval", "source_url": "https://github.com/phamquiluan/RCAEval",
         "dataset_revision": REVISION, "repository_revision": "bb48c5aa9a24f1d5fcc716bdd479ea2d63145c90",
         "license": "MIT per upstream repository", "population": "RE2-OB frozen 12-case Phase 2.11 pilot",
         "telemetry_origin": "recorded Online Boutique fault-injection benchmark, not handcrafted synthetic fixture",
         "label_semantics": "annotated injected root-cause service, evaluation only",
         "label_independence": "BENCHMARK_ANNOTATION_NOT_INDEPENDENT_VALIDATION",
         "limitations": ["injection-time oracle window", "consumed development population", "controlled injected faults"]})
    print(json.dumps({"accepted": accepted, "cases": len(records),
                      "aligned_modalities": dict(Counter(name for r in records for name, v in r["modalities"].items() if v["window_rows"] > 0))}, sort_keys=True))


def router_model() -> QwenRCAAgentV21Model:
    if not ROUTER_DB.is_file():
        raise RuntimeError("LOCAL_ROUTER_CONFIGURATION_MISSING")
    db = sqlite3.connect(f"file:{ROUTER_DB.as_posix()}?mode=ro", uri=True)
    try:
        result = db.execute("SELECT key FROM apiKeys WHERE isActive=1 LIMIT 1").fetchone()
    finally:
        db.close()
    if not result:
        raise RuntimeError("LOCAL_ROUTER_KEY_MISSING")
    os.environ["CDOI_ROUTER_SESSION_KEY"] = result[0]
    session = requests.Session()
    session.trust_env = False  # localhost must not traverse the enterprise proxy

    def requester(method: str, url: str, **kwargs: Any) -> requests.Response:
        # 9router otherwise defaults to SSE; this is transport-only adaptation.
        kwargs["json"] = {**kwargs["json"], "stream": False}
        return session.request(method, url, **kwargs)

    config = QwenRCAConfig(provider="9router-kiro", provider_profile="LOCAL_ROUTER",
                           model=MODEL, base_url="http://127.0.0.1:20128/v1",
                           api_key_env="CDOI_ROUTER_SESSION_KEY", enable_thinking=None,
                           timeout_seconds=TIMEOUT_SECONDS, max_retries=0)
    model = QwenRCAAgentV21Model(config, requester=requester, max_output_tokens=2048)
    model._router_session = session  # keep transport alive for serial calls
    return model


def prepare_tools(index_tag: str = "qualification") -> tuple[Any, ReadOnlyRCATools]:
    suffix = MODEL.replace("/", "_").replace("-", "_").replace(".", "_")
    prepared = RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / f"SYNTHETIC_{index_tag.upper()}_INDEX_{suffix}.sqlite")
    h1 = {item.candidate_id for item in prepared.h1_candidates}
    expanded = tuple(item for item in prepared.h5_candidates if item.candidate_id not in h1)
    return prepared, ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded)


def qualify_runtime() -> None:
    result_name = "LLM_BACKEND_QUALIFICATION.json" if MODEL == "kr/qwen3-coder-next" else (
        "LLM_BACKEND_QUALIFICATION_" + MODEL.upper().replace("/", "_").replace("-", "_").replace(".", "_") + ".json")
    if TOOL_ROUND_FORMAT != "frozen_json_object":
        if TOOL_ROUND_FORMAT != "tool_only_envelope":
            raise RuntimeError("UNSUPPORTED_TOOL_ROUND_FORMAT")
        result_name = result_name.removesuffix(".json") + "_TOOL_ONLY_ENVELOPE.json"
    if (OUT / result_name).exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_RUNTIME_QUALIFICATION")
    model = router_model()
    prepared, tools = prepare_tools()
    probes: list[dict[str, Any]] = []
    try:
        ids = sorted(item.candidate_id for item in tools.candidates)
        def valid_abstention() -> dict[str, Any]:
            return {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                    "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
                    "reasoning_summary": "Synthetic contract probe.", "limitations": ["SYNTHETIC_PROBE"],
                    "investigated_candidate_ids": ids, "comparison_completed": True,
                    "abstention_reason": "MISSING_DISTINGUISHING_SIGNAL",
                    "missing_or_conflicting_evidence": ["SYNTHETIC_EVIDENCE_GAP"]}
        def valid_hypothesis() -> dict[str, Any]:
            return {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": ids[0],
                    "statement": "Synthetic non-causal hypothesis.", "supporting_evidence_ids": [],
                    "limitations": ["SYNTHETIC_PROBE"], "model_self_assessment": "LOW"},
                    "alternative_hypotheses": [], "supporting_evidence_ids": [],
                    "contradictory_evidence_ids": [], "reasoning_summary": "Synthetic contract probe.",
                    "limitations": ["SYNTHETIC_PROBE"]}
        # Live provider must reproduce both valid report shapes through the
        # unchanged validator. Raw text is never persisted.
        for probe_id, wanted in (("VALID_ABSTENTION", valid_abstention()),
                                 ("VALID_HYPOTHESIS", valid_hypothesis())):
            started = perf_counter()
            try:
                turn = model.complete([{"role": "system", "content": model.system_prompt},
                    {"role": "user", "content": "Return this synthetic contract JSON unchanged: " + json.dumps(wanted, sort_keys=True)}],
                    response_format={"type": "json_object"})
                raw = json.loads(turn["message"]["content"])
                RCAAgentV21.validate_raw_report(raw, set(ids))
                report = RCAAgentV21(model)._validated_report("inc-001", raw, 0, {}, tools, set(ids))
                probes.append({"probe_id": probe_id, "status": "PASS" if report.status == wanted["status"] else "FAIL",
                               "report_status": report.status, "latency_ms": turn["latency_ms"],
                               "resolved_model": turn["response_metadata"].get("resolved_model")})
            except (ValueError, QwenRCAError, KeyError, TypeError) as exc:
                probes.append({"probe_id": probe_id, "status": "FAIL", "error_code": str(exc),
                               "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
        # Local strict rejection cannot be delegated to provider behavior.
        invalid = [("MISSING_STATUS", {k: v for k, v in valid_abstention().items() if k != "status"}),
                   ("UNKNOWN_STATUS", {**valid_abstention(), "status": "ABSTAIN"}),
                   ("ABSTENTION_MISSING_REASON", {k: v for k, v in valid_abstention().items() if k != "abstention_reason"}),
                   ("HYPOTHESIS_MISSING_PRIMARY", {**valid_hypothesis(), "primary_hypothesis": None}),
                   ("UNKNOWN_CANDIDATE", {**valid_hypothesis(), "primary_hypothesis": {**valid_hypothesis()["primary_hypothesis"], "candidate_id": "unknown"}}),
                   ("UNKNOWN_EVIDENCE", {**valid_hypothesis(), "supporting_evidence_ids": ["unknown"]})]
        for probe_id, raw in invalid:
            try:
                RCAAgentV21(model)._validated_report("inc-001", raw, 0, {}, tools, set(ids))
                probes.append({"probe_id": probe_id, "status": "FAIL", "error_code": "INVALID_ACCEPTED"})
            except ValueError as exc:
                probes.append({"probe_id": probe_id, "status": "PASS", "error_code": str(exc)})
        # The bounded live repair path is the frozen model adapter's method.
        for probe_id, invalid_report, desired in (("REPAIR_INVALID_STATUS", {"status": "ABSTAIN"}, valid_abstention()),
                                                   ("REPAIR_ABSTENTION", {"status": "INSUFFICIENT_EVIDENCE"}, valid_abstention())):
            try:
                repaired = model.repair_output(invalid_report, "RCA_STATUS_INVALID", {"report_schema": json.dumps(desired, sort_keys=True)})["report"]
                RCAAgentV21(model)._validated_report("inc-001", repaired, 0, {}, tools, set(ids))
                probes.append({"probe_id": probe_id, "status": "PASS", "repair_calls": 1})
            except (ValueError, QwenRCAError, KeyError, TypeError) as exc:
                probes.append({"probe_id": probe_id, "status": "FAIL", "error_code": str(exc), "repair_calls": 1})
        # Actual V2.1 model call with native tool schema. Force one read-only
        # synthetic tool to distinguish provider tool capability from free text.
        class ForcedTool(type(model)):
            def __init__(self, base: QwenRCAAgentV21Model) -> None:
                super().__init__(base.config, requester=base.requester, max_output_tokens=2048)
                self.round = 0
            def _body(self) -> dict[str, Any]:
                body = super()._body()
                body["tool_choice"] = ({"type": "function", "function": {"name": "get_incident_summary"}}
                                       if self.round == 0 else "none")
                if self.round == 0 and TOOL_ROUND_FORMAT == "tool_only_envelope":
                    body.pop("response_format", None)
                self.round += 1
                return body
        tool_model = ForcedTool(model)
        try:
            report, trace = RCAAgentV21(tool_model).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK,
                                                                tool_model.public_metadata())
            names = [item["tool_name"] for item in trace["tool_calls"]]
            probes.append({"probe_id": "NATIVE_TOOL_AND_REPORT", "status": "PASS" if names == ["get_incident_summary"] else "FAIL",
                           "tool_names": names, "report_status": report.status,
                           "provider_interactions": len(tool_model.transport_history)})
        except (ValueError, QwenRCAError) as exc:
            probes.append({"probe_id": "NATIVE_TOOL_AND_REPORT", "status": "FAIL", "error_code": str(exc),
                           "provider_interactions": len(tool_model.transport_history),
                           "normalization_error_path": tool_model.last_contract_diagnostic.get("validation_error_path")})
    finally:
        prepared.store.close()
        os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    pass_count = sum(row["status"] == "PASS" for row in probes)
    dump(result_name, {"schema_version": "rca_blocker_backend_qualification_v1",
         "backend": "9router Kiro " + MODEL + " (not DMP Qwen3.8-27B)", "probes": probes,
         "passed": pass_count, "total": len(probes), "qualified": pass_count == len(probes),
         "fixture_type": "SYNTHETIC_CONTRACT_QUALIFICATION_NOT_RCA_QUALITY",
         "tool_round_format": TOOL_ROUND_FORMAT,
         "bounded_timeout_seconds": 45, "max_retries": 0,
         "raw_model_text_persisted": False, "credentials_persisted": False})
    print(json.dumps({"passed": pass_count, "total": len(probes), "qualified": pass_count == len(probes)}, sort_keys=True))


def qualify_v22() -> None:
    if MODEL != "kr/claude-sonnet-4.5":
        raise RuntimeError("V22_PREREGISTERED_BACKEND_MISMATCH")
    tag = os.environ.get("CDOI_RESOLUTION_V22_TAG", "INITIAL")
    if tag not in {"INITIAL", "REFINED", "FINAL_120S", "MANDATORY_SUMMARY_120S"}:
        raise RuntimeError("INVALID_V22_QUALIFICATION_TAG")
    result_name = {"INITIAL": "LLM_BACKEND_QUALIFICATION_V22.json",
                   "REFINED": "LLM_BACKEND_QUALIFICATION_V22_REFINED.json",
                   "FINAL_120S": "LLM_BACKEND_QUALIFICATION_V22_FINAL_120S.json",
                   "MANDATORY_SUMMARY_120S": "LLM_BACKEND_QUALIFICATION_V22_MANDATORY_SUMMARY_120S.json"}[tag]
    if tag in {"FINAL_120S", "MANDATORY_SUMMARY_120S"} and TIMEOUT_SECONDS != 120:
        raise RuntimeError("FINAL_V22_TIMEOUT_MISMATCH")
    if (OUT / result_name).exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_V22_QUALIFICATION")
    base = router_model()
    prepared, tools = prepare_tools("v22_" + tag.lower())
    probes: list[dict[str, Any]] = []
    try:
        probe_rows = (("MANDATORY_SUMMARY_1", ""), ("MANDATORY_SUMMARY_2", ""),
                      ("MANDATORY_SUMMARY_3", ""), ("MANDATORY_SUMMARY_4", "")) if tag == "MANDATORY_SUMMARY_120S" else (
                      ("REAL_STAGED_REPORT", ""),
                      ("FORCED_STAGED_TOOL", "For this synthetic qualification, first request get_incident_summary with incident_id inc-001. After its result, return a valid REPORT action. "),
                      ("FORCED_STAGED_TOOL_REPEAT_2", "For this synthetic qualification, first request get_incident_summary with incident_id inc-001. After its result, return a valid REPORT action. "),
                      ("FORCED_STAGED_TOOL_REPEAT_3", "For this synthetic qualification, first request get_incident_summary with incident_id inc-001. After its result, return a valid REPORT action. "))
        for probe_id, extra in probe_rows:
            staged = StagedRCAAgentV22Model(base.config, requester=base.requester, max_output_tokens=2048)
            if extra:
                staged.system_prompt = extra + staged.system_prompt
            started = perf_counter()
            try:
                report, trace = RCAAgentV22(staged).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK,
                                                                {"backend": MODEL, "protocol": "STAGED_V2_2"})
                names = [item["tool_name"] for item in trace["tool_calls"]]
                tool_ok = not extra and tag != "MANDATORY_SUMMARY_120S" or names[:1] == ["get_incident_summary"]
                probes.append({"probe_id": probe_id, "status": "PASS" if tool_ok else "FAIL",
                               "report_status": report.status, "tool_names": names,
                               "repair_count": len(trace["repairs"]), "action_count": len(staged.action_history),
                               "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                               "resolved_model": staged.last_response_metadata.get("resolved_model")})
            except (ValueError, QwenRCAError) as exc:
                probes.append({"probe_id": probe_id, "status": "FAIL", "error_code": str(exc),
                               "action_count": len(staged.action_history),
                               "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
        # The live V2.1 Sonnet run independently established valid hypothesis,
        # valid abstention, strict ID rejection, and one-call repair. Recheck
        # the same inherited validator locally rather than fabricating output.
        inherited = json.loads((OUT / "LLM_BACKEND_QUALIFICATION_KR_CLAUDE_SONNET_4_5.json").read_text(encoding="utf-8"))
        inherited_required = {"VALID_ABSTENTION", "VALID_HYPOTHESIS", "MISSING_STATUS", "UNKNOWN_STATUS",
                              "ABSTENTION_MISSING_REASON", "HYPOTHESIS_MISSING_PRIMARY", "UNKNOWN_CANDIDATE",
                              "UNKNOWN_EVIDENCE", "REPAIR_INVALID_STATUS", "REPAIR_ABSTENTION"}
        inherited_pass = {item["probe_id"] for item in inherited["probes"] if item["status"] == "PASS"}
        inherited_ok = inherited_required <= inherited_pass
    finally:
        prepared.store.close()
        os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    qualified = inherited_ok and all(row["status"] == "PASS" for row in probes)
    dump(result_name, {"schema_version": "rca_blocker_v22_qualification_v1",
         "backend": "9router Kiro " + MODEL, "agent_version": "V2.2_STAGED_PROVIDER_PROTOCOL",
         "qualification_tag": tag,
         "v2_1_report_validator_reused": True, "inherited_contract_pass": inherited_ok,
         "inherited_required_probe_ids": sorted(inherited_required), "live_staged_probes": probes,
         "qualified": qualified, "timeout_seconds_per_turn": TIMEOUT_SECONDS, "max_retries_per_turn": 0,
         "max_tool_calls": 8, "max_output_repairs": 1, "raw_text_persisted": False,
         "interpretation": "Synthetic runtime/contract qualification only; not RCA quality."})
    print(json.dumps({"qualified": qualified, "live_staged_passed": sum(x["status"] == "PASS" for x in probes),
                      "live_staged_total": len(probes)}, sort_keys=True))


def qualify_v23() -> None:
    if MODEL != "kr/claude-sonnet-4.5" or TIMEOUT_SECONDS != 120:
        raise RuntimeError("V23_FROZEN_PROVIDER_CONFIG_MISMATCH")
    tag = os.environ.get("CDOI_RESOLUTION_V23_TAG", "INITIAL")
    if tag not in {"INITIAL", "FINAL"}:
        raise RuntimeError("INVALID_V23_QUALIFICATION_TAG")
    result_name = "LLM_BACKEND_QUALIFICATION_V23.json" if tag == "INITIAL" else "LLM_BACKEND_QUALIFICATION_V23_FINAL.json"
    if (OUT / result_name).exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_V23_QUALIFICATION")
    base = router_model()
    prepared, tools = prepare_tools("v23_" + tag.lower())
    probes: list[dict[str, Any]] = []
    try:
        for probe_id, force_metric in (("NATURAL_1", False), ("NATURAL_2", False),
                                       ("METRIC_TOOL_1", True), ("METRIC_TOOL_2", True),
                                       ("METRIC_TOOL_3", True)):
            model = StagedRCAAgentV23Model(base.config, requester=base.requester, max_output_tokens=2048)
            if force_metric:
                model.system_prompt = ("For this synthetic contract qualification: first request get_incident_summary with incident_id inc-001, "
                                       "then request get_metric_evidence with incident_id inc-001 and service_id payment-service, "
                                       "then return a valid REPORT action. Use exact argument keys. " + model.system_prompt)
            started = perf_counter()
            try:
                report, trace = RCAAgentV23(model).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK,
                                                               {"backend": MODEL, "protocol": "STAGED_V2_3"})
                names = [item["tool_name"] for item in trace["tool_calls"]]
                required = ["get_incident_summary", "get_metric_evidence"] if force_metric else ["get_incident_summary"]
                ok = names[:len(required)] == required
                probes.append({"probe_id": probe_id, "status": "PASS" if ok else "FAIL",
                               "report_status": report.status, "tool_names": names,
                               "tool_action_repairs": model.tool_action_repairs,
                               "report_repairs": len(trace["repairs"]),
                               "provider_interactions": len(model.transport_history),
                               "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                               "resolved_model": model.last_response_metadata.get("resolved_model")})
            except (ValueError, QwenRCAError) as exc:
                probes.append({"probe_id": probe_id, "status": "FAIL", "error_code": str(exc),
                               "tool_action_repairs": model.tool_action_repairs,
                               "provider_interactions": len(model.transport_history),
                               "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
        inherited = json.loads((OUT / "LLM_BACKEND_QUALIFICATION_V22_MANDATORY_SUMMARY_120S.json").read_text(encoding="utf-8"))
        inherited_ok = inherited["qualified"]
    finally:
        prepared.store.close()
        os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    qualified = inherited_ok and all(row["status"] == "PASS" for row in probes)
    dump(result_name, {"schema_version": "rca_blocker_v23_qualification_v1",
         "backend": "9router Kiro " + MODEL, "agent_version": "V2.3_STAGED_EXACT_TOOL_ARGUMENTS",
         "qualification_tag": tag,
         "qualified_source_sha256": {name: digest(ROOT / name) for name in (
             "src/cdoi/rca_agent_v2_3.py", "src/cdoi/staged_rca_backend_v2_3.py", "src/cdoi/rca_investigation.py")},
         "v2_1_report_validator_reused": True, "v22_contract_qualification_sha256": digest(OUT / "LLM_BACKEND_QUALIFICATION_V22_MANDATORY_SUMMARY_120S.json"),
         "v22_contract_pass": inherited_ok, "live_probes": probes,
         "tool_argument_signatures": {name: {"required": list(required), "optional": list(optional)}
                                      for name, (required, optional) in TOOL_ARGUMENTS.items()},
         "qualified": qualified, "timeout_seconds_per_turn": 120, "max_retries_per_turn": 0,
         "max_tool_calls": 8, "tool_action_repair_limit": 1, "report_repair_limit": 1,
         "raw_model_text_persisted": False, "credential_values_persisted": False})
    print(json.dumps({"qualified": qualified, "passed": sum(x["status"] == "PASS" for x in probes),
                      "total": len(probes)}, sort_keys=True))


def qualify_v23_repair() -> None:
    if MODEL != "kr/claude-sonnet-4.5" or TIMEOUT_SECONDS != 120:
        raise RuntimeError("V23_REPAIR_PROVIDER_CONFIG_MISMATCH")
    if (OUT / "LIVE_REPAIR_QUALIFICATION_V23.json").exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_V23_REPAIR_QUALIFICATION")
    base = router_model()
    prepared, tools = prepare_tools("v23_repair")
    h1_ids = sorted(item.candidate_id for item in tools.candidates)
    request = {"preloaded_candidate_profiles": [{"candidate_id": value} for value in h1_ids],
               "report_schema": "RCAReport plus V2.1 explicit status contract; for abstention require exact H1 IDs, comparison_completed=true, nonempty reason and evidence gap; for hypothesis require a supplied primary candidate and limitations"}
    rows = []
    try:
        for probe_id, raw, error in (("MISSING_STATUS", {"primary_hypothesis": None}, "RCA_STATUS_REQUIRED"),
                                     ("ABSTENTION_MISSING_FIELDS", {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None}, "RCA_ABSTENTION_CANDIDATES_REQUIRED")):
            model = StagedRCAAgentV23Model(base.config, requester=base.requester, max_output_tokens=2048)
            started = perf_counter()
            try:
                repaired = model.repair_output(raw, error, request)["report"]
                report = RCAAgentV23(model)._validated_report("inc-001", repaired, 0, {}, tools, set(h1_ids))
                rows.append({"probe_id": probe_id, "status": "PASS", "final_status": report.status,
                             "provider_interactions": len(model.transport_history), "repair_attempt_count": 1,
                             "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
            except (ValueError, QwenRCAError) as exc:
                rows.append({"probe_id": probe_id, "status": "FAIL", "error_code": str(exc),
                             "provider_interactions": len(model.transport_history), "repair_attempt_count": 1,
                             "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
    finally:
        prepared.store.close()
        os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    dump("LIVE_REPAIR_QUALIFICATION_V23.json", {"schema_version": "rca_blocker_v23_live_repair_v1",
         "backend": MODEL, "probes": rows, "passed": sum(row["status"] == "PASS" for row in rows),
         "total": len(rows), "one_repair_per_probe": True, "max_retries_per_provider_call": 0,
         "raw_provider_content_persisted": False})
    print(json.dumps({"passed": sum(row["status"] == "PASS" for row in rows), "total": len(rows)}, sort_keys=True))


def execute_development(variant: str = "v22") -> None:
    if variant not in {"v22", "v23", "v23_blinded"}:
        raise RuntimeError("INVALID_DEVELOPMENT_VARIANT")
    use_v23 = variant in {"v23", "v23_blinded"}
    run_out = OUT / variant if use_v23 else OUT
    qualification = OUT / ("LLM_BACKEND_QUALIFICATION_V23_FINAL.json" if use_v23
                           else "LLM_BACKEND_QUALIFICATION_V22_MANDATORY_SUMMARY_120S.json")
    acceptance = OUT / "DATA_DELIVERY_VALIDATION.json"
    if not qualification.is_file() or not acceptance.is_file():
        raise RuntimeError("PREREQUISITE_ARTIFACT_MISSING")
    if not json.loads(qualification.read_text(encoding="utf-8"))["qualified"]:
        raise RuntimeError("LIVE_BACKEND_NOT_QUALIFIED")
    if not json.loads(acceptance.read_text(encoding="utf-8"))["accepted"]:
        raise RuntimeError("DATASET_NOT_ACCEPTED")
    if (run_out / "RCA_REPORTS_FREEZE.json").exists() or (run_out / "RCA_EVALUATION.json").exists():
        raise RuntimeError("REFUSE_TO_RERUN_FROZEN_DEVELOPMENT")
    if MODEL != "kr/claude-sonnet-4.5":
        raise RuntimeError("FROZEN_BACKEND_MISMATCH")
    if TIMEOUT_SECONDS != 120:
        raise RuntimeError("FROZEN_TIMEOUT_MISMATCH")
    frozen_data = json.loads((OUT / "DATASET_FREEZE.json").read_text(encoding="utf-8"))
    model = router_model()
    model_class = StagedRCAAgentV23Model if use_v23 else StagedRCAAgentV22Model
    agent_class = RCAAgentV23 if use_v23 else RCAAgentV22
    prompt = model_class.system_prompt
    source_names = ("src/cdoi/rca_agent_v2_1.py", "src/cdoi/rca_agent_v2_2.py",
                    "src/cdoi/staged_rca_backend_v2_2.py", "src/cdoi/qwen_rca_v2_1.py")
    if use_v23:
        source_names += ("src/cdoi/rca_agent_v2_3.py", "src/cdoi/staged_rca_backend_v2_3.py",
                         "src/cdoi/rca_investigation.py")
    runtime = {"schema_version": "rca_blocker_runtime_freeze_v1", "agent": agent_class.__name__,
               "provider": "9router Kiro", "requested_model": MODEL, "resolved_model": "claude-sonnet-4.5",
               "model_revision": "PROVIDER_NOT_DISCLOSED", "provider_profile": "LOCAL_ROUTER",
               "router_package_version": "0.5.81", "transport_envelope": "OpenAI-compatible stream=false",
               "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
               "tool_schema_sha256": hashlib.sha256(json.dumps(
                   {name: [list(required), list(optional)] for name, (required, optional) in TOOL_ARGUMENTS.items()}
                   if use_v23 else sorted(ALLOWED_TOOLS), sort_keys=True).encode("utf-8")).hexdigest(),
               "max_output_tokens": 2048, "timeout_seconds_per_turn": 120, "max_retries_per_turn": 0,
               "max_tool_calls": 8, "max_output_repairs": 1,
               "max_tool_action_repairs": 1 if use_v23 else 0, "temperature": 0,
               "candidate_source": "H1_THEN_H5_FALLBACK", "case_split_sha256": frozen_data["split_sha256"],
               "case_index_sha256": frozen_data["case_index_sha256"],
               "source_sha256": {name: digest(ROOT / name) for name in source_names},
               "incident_identifier_policy": "OPAQUE_ORDINAL_V1" if variant == "v23_blinded" else "SOURCE_CASE_ID",
               "ground_truth_access_before_reports_freeze": False}
    dump_in(run_out, "LLM_RUNTIME_FREEZE.json", runtime)
    dump_in(run_out, "MASTER_PREREGISTRATION.json", {"schema_version": "rca_blocker_preregistration_v1",
         "population": frozen_data["pilot_case_ids"], "dataset_role": "CONSUMED_DEVELOPMENT_DATA",
         "evaluation_target": "exact normalized root-cause service match, not causal proof",
         "prediction_freeze_before_gt": True, "phase2_12_access": "PROHIBITED",
         "agent": agent_class.__name__, "runtime_freeze_sha256": digest(run_out / "LLM_RUNTIME_FREEZE.json"),
         "no_mid_batch_tuning": True, "prior_v22_batch_preserved": use_v23,
         "incident_identifier_policy": runtime["incident_identifier_policy"],
         "prior_v23_diagnostic_batch_preserved": variant == "v23_blinded",
         "development_cases_previously_consumed": True})
    # Read only non-label case-index columns until RCA_REPORTS_FREEZE exists.
    safe_columns = ["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]
    index = {row["case"]: row for row in pq.read_table(DATA / "cases.parquet", columns=safe_columns).to_pylist()
             if row["case"] in frozen_data["pilot_case_ids"]}
    statuses, transport = [], []
    orchestrator = RCAOrchestrator()
    for case_number, case_id in enumerate(frozen_data["pilot_case_ids"], 1):
        row = index[case_id]
        inference_case_id = f"case-{case_number:03d}" if variant == "v23_blinded" else case_id
        case = RCAEvalCase(inference_case_id, str(row["dataset"]), str(row["system"]), int(row["inject_time"]),
                           int(row["time_start"]), int(row["time_end"]), bool(row["has_logs"]), bool(row["has_traces"]))
        case_store = None
        started = perf_counter()
        try:
            adapted, case_store, _, _ = adapt_cached_case_to_store(case, DATA / REVISION / case_id,
                                                            run_out / "stores" / f"{case_id}.sqlite")
            view = case_store.logical_view()
            cfg = HypothesisConfiguration()
            h1 = generate_evidence_aware_hypotheses(case_store, view, configuration=cfg, include_metric=True,
                                                     include_trace=False, include_topology=False, include_temporal_change=False)
            h5 = generate_evidence_aware_hypotheses(case_store, view, configuration=cfg, include_metric=True,
                                                     include_trace=True, include_topology=True, include_temporal_change=True)
            union = tuple(sorted({item.candidate_id: item for item in (*h1.candidates, *h5.candidates)}.values(),
                                 key=lambda item: item.candidate_id))
            profiles = CandidateEvidenceProfileBuilder(case_store.context, case_store,
                        (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(union)
            prepared = PreparedRCAInvestigation(case_store.context, case_store, h1.candidates, h5.candidates, profiles)
            if variant == "v23_blinded" and case_id in str(case_store.context):
                raise RuntimeError("SOURCE_CASE_ID_LEAKED_INTO_INFERENCE_CONTEXT")
            candidate_subjects = {item.candidate_id: item.subject_node_id.removeprefix("entity:") for item in union}
            model_i = model_class(model.config, requester=model.requester, max_output_tokens=2048)
            agent = agent_class(model_i, budget=V2AgentBudget(max_tool_calls=8, max_output_repairs=1))
            metadata = {k: v for k, v in model_i.public_metadata().items() if k not in {"api_key_env", "base_url"}}
            report = orchestrator.run(prepared, run_out / "RUNS" / case_id, InvestigationMode.AGENT,
                                      CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, metadata)
            statuses.append({"case_id": case_id, "status": report.status,
                             "candidate_subjects": candidate_subjects,
                             "h1_candidate_ids": sorted(item.candidate_id for item in h1.candidates),
                             "h5_candidate_ids": sorted(item.candidate_id for item in h5.candidates),
                             "primary_candidate_id": report.primary_hypothesis.candidate_id if report.primary_hypothesis else None,
                             "alternative_candidate_ids": [item.candidate_id for item in report.alternative_hypotheses],
                             "tool_calls": report.tool_calls,
                             "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
            transport.append({"case_id": case_id, "provider_attempts": list(model_i.transport_history),
                              "staged_actions": list(model_i.action_history),
                              "tool_action_repairs": getattr(model_i, "tool_action_repairs", 0)})
        except Exception as exc:
            # Pre-agent failures remain explicit technical outcomes; never
            # silently drop a case or count it as semantic abstention.
            statuses.append({"case_id": case_id, "status": "TECHNICAL_FAILURE",
                             "error_type": type(exc).__name__, "error_code": str(exc)[:120],
                             "elapsed_ms": round((perf_counter() - started) * 1000, 3)})
            transport.append({"case_id": case_id, "provider_attempts": [], "staged_actions": []})
        finally:
            if case_store is not None:
                case_store.close()
    dump_in(run_out, "END_TO_END_RUN.json", {"schema_version": "rca_blocker_end_to_end_v1",
         "case_count": len(statuses), "cases": statuses, "labels_read": False,
         "technical_failures": sum(item["status"] == "TECHNICAL_FAILURE" for item in statuses)})
    dump_in(run_out, "TRANSPORT_RELIABILITY.json", {"schema_version": "rca_blocker_transport_v1", "cases": transport,
         "no_success_only_filtering": True})
    report_hashes = {item["case_id"]: digest(run_out / "RUNS" / item["case_id"] / "RCA_REPORT.json")
                     if (run_out / "RUNS" / item["case_id"] / "RCA_REPORT.json").is_file() else None for item in statuses}
    dump_in(run_out, "RCA_REPORTS_FREEZE.json", {"schema_version": "rca_blocker_reports_freeze_v1",
         "population": frozen_data["pilot_case_ids"], "report_sha256": report_hashes,
         "end_to_end_run_sha256": digest(run_out / "END_TO_END_RUN.json"),
         "labels_read": False, "prediction_freeze_complete": True,
         "all_cases_accounted": len(statuses) == len(frozen_data["pilot_case_ids"])})
    # Only now read the already-consumed Phase 2.11 development labels.
    truth_dir = ROOT / "experiments/archive/v3_phase2_11/CASE_EVALUATIONS"
    ground_truth = {path.stem: json.loads(path.read_text(encoding="utf-8"))["evaluations"]["H5_COMBINED"].get("ground_truth_service_id")
                    for path in truth_dir.glob("*.json") if path.stem in set(frozen_data["pilot_case_ids"])}
    evaluations = []
    for item in statuses:
        gt = normalize_service_id(ground_truth.get(item["case_id"]))
        subjects = item.get("candidate_subjects", {})
        primary = normalize_service_id(subjects.get(item.get("primary_candidate_id")))
        alternatives = [normalize_service_id(subjects.get(candidate_id)) for candidate_id in item.get("alternative_candidate_ids", [])]
        evaluations.append({"case_id": item["case_id"], "status": item["status"],
                            "gt_service_id": gt, "gt_in_h1": gt in [normalize_service_id(subjects.get(x)) for x in item.get("h1_candidate_ids", [])],
                            "gt_in_h5": gt in [normalize_service_id(subjects.get(x)) for x in item.get("h5_candidate_ids", [])],
                            "primary_service_id": primary, "top1_correct": bool(primary and primary == gt),
                            "top3_correct": bool(item["status"] == "RCA_HYPOTHESIS" and gt and gt in [primary, *alternatives[:2]]),
                            "hypothesis_count": int(item["status"] == "RCA_HYPOTHESIS")})
    dump_in(run_out, "RCA_EVALUATION.json", {"schema_version": "rca_blocker_evaluation_v1",
         "dataset_role": "CONSUMED_DEVELOPMENT_DATA_NOT_INDEPENDENT_VALIDATION",
         "reports_freeze_sha256": digest(run_out / "RCA_REPORTS_FREEZE.json"),
         "cases": evaluations, "attempted": len(evaluations),
         "valid_hypotheses": sum(x["status"] == "RCA_HYPOTHESIS" for x in evaluations),
         "valid_abstentions": sum(x["status"] == "INSUFFICIENT_EVIDENCE" for x in evaluations),
         "technical_failures": sum(x["status"] == "TECHNICAL_FAILURE" for x in evaluations),
         "top1_all_cases": sum(x["top1_correct"] for x in evaluations),
         "top3_all_cases": sum(x["top3_correct"] for x in evaluations),
         "not_formal_causal_proof": True})
    os.environ.pop("CDOI_ROUTER_SESSION_KEY", None)
    print(json.dumps({"end_to_end_cases": len(statuses),
                      "valid_hypotheses": sum(x["status"] == "RCA_HYPOTHESIS" for x in evaluations),
                      "technical_failures": sum(x["status"] == "TECHNICAL_FAILURE" for x in evaluations)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["data", "runtime", "v22", "v23", "v23_repair", "execute", "execute_v23", "execute_v23_blinded"])
    args = parser.parse_args()
    {"data": validate_data, "runtime": qualify_runtime, "v22": qualify_v22,
     "v23": qualify_v23, "v23_repair": qualify_v23_repair,
     "execute": execute_development,
     "execute_v23": lambda: execute_development("v23"),
     "execute_v23_blinded": lambda: execute_development("v23_blinded")}[args.stage]()


if __name__ == "__main__":
    main()
