"""Build a label-free, provenance-limited corpus from frozen V2.3 artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "experiments/archive/v3_rca_blocker_resolution_20260925"
OUT = ROOT / "experiments/archive/v3_rca_v2_4_reliability_20260925"
sys.path.insert(0, str(ROOT / "src"))
from cdoi.staged_rca_backend_v2_3 import TOOL_ARGUMENTS  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(name: str, payload: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if path.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{name}")
    path.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ids(value: Any, key_names: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in key_names and isinstance(item, str):
                found.add(item)
            else:
                found.update(ids(item, key_names))
    elif isinstance(value, list):
        for item in value:
            found.update(ids(item, key_names))
    return found


def main() -> None:
    if (OUT / "PREREGISTRATION.json").exists():
        raise RuntimeError("V24_ARCHIVE_ALREADY_INITIALIZED")
    freeze_path = SOURCE / "v23_blinded/RCA_REPORTS_FREEZE.json"
    if not freeze_path.is_file():
        raise RuntimeError("V23_OPAQUE_ID_FREEZE_MISSING")
    run = json.loads((SOURCE / "v23_blinded/END_TO_END_RUN.json").read_text(encoding="utf-8"))
    transport = json.loads((SOURCE / "v23_blinded/TRANSPORT_RELIABILITY.json").read_text(encoding="utf-8"))
    freezes = json.loads(freeze_path.read_text(encoding="utf-8"))
    ordered_ids = [row["case_id"] for row in run["cases"]]
    transport_by_case = {row["case_id"]: row for row in transport["cases"]}
    failures = []
    for ordinal, row in enumerate(run["cases"], 1):
        if row["status"] != "TECHNICAL_FAILURE":
            continue
        opaque = f"case-{ordinal:03d}"
        case_dir = SOURCE / "v23_blinded/RUNS" / row["case_id"]
        trace_path = case_dir / "AGENT_TRACE.json"
        report_path = case_dir / "RCA_REPORT.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.is_file() else {}
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
        attempts = transport_by_case[row["case_id"]]["provider_attempts"]
        actions = transport_by_case[row["case_id"]]["staged_actions"]
        candidates = json.loads((case_dir / "CANDIDATES.json").read_text(encoding="utf-8"))
        profiles = json.loads((case_dir / "CANDIDATE_PROFILES.json").read_text(encoding="utf-8"))
        candidate_ids = ids(candidates, {"candidate_id"}) | ids(profiles, {"candidate_id"})
        evidence_ids = ids(candidates, {"evidence_id", "supporting_evidence_id", "contradictory_evidence_id"})
        evidence_ids |= ids(profiles, {"evidence_id", "aggregate_evidence_id"})
        err = str(trace.get("error_code", report.get("abstention_reason", "NOT_PERSISTED")))
        unknown_evidence = "RCA_REPORT_UNKNOWN_EVIDENCE" in err
        excessive = "INVALID_OR_EXCESSIVE_AGENT_TOOL_CALLS" in err
        failures.append({
            "opaque_incident_id": opaque,
            "source_case_id_persisted": False,
            "stage": "REPORT_VALIDATION" if unknown_evidence else "TOOL_BUDGET_GUARD" if excessive else "UNKNOWN_FROM_FROZEN_TRACE",
            "stage_turn_number": len(actions),
            "model_visible_candidate_ids": sorted(candidate_ids),
            "model_visible_evidence_ids": sorted(evidence_ids),
            "tool_schemas_available": {name: {"required": list(req), "optional": list(opt)}
                                        for name, (req, opt) in TOOL_ARGUMENTS.items()},
            "raw_provider_output": "NOT_PERSISTED_BY_V23_AND_NOT_RECOVERABLE_FROM_FROZEN_ARTIFACTS",
            "normalized_provider_output": "NOT_PERSISTED_BY_V23",
            "tool_call_arguments": "NOT_PERSISTED_BY_V23",
            "parser_result": "ACTION_OR_REPORT_PARSING_SUCCEEDED_BEFORE_RECORDED_GUARD" if excessive or unknown_evidence else "NOT_AVAILABLE",
            "validator_result": err,
            "repair_attempted": bool(unknown_evidence and len(attempts) > len(actions)),
            "repair_attempt_evidence": "PROVIDER_INTERACTION_COUNT_EXCEEDS_STAGED_ACTION_COUNT_BY_ONE" if unknown_evidence and len(attempts) > len(actions) else "NOT_OBSERVABLE",
            "repair_input": "NOT_PERSISTED_BY_V23",
            "repair_raw_output": "NOT_PERSISTED_BY_V23",
            "final_fail_closed_status": "TECHNICAL_FAILURE",
            "artifacts": {
                "trace_sha256": sha(trace_path) if trace_path.is_file() else None,
                "report_sha256": sha(report_path) if report_path.is_file() else None,
                "candidate_sha256": sha(case_dir / "CANDIDATES.json"),
                "profile_sha256": sha(case_dir / "CANDIDATE_PROFILES.json")
            },
        })
    dump("PREREGISTRATION.json", {
        "schema_version": "rca_v24_reliability_preregistration_v1",
        "objective": "Reduce report/tool-loop technical failures while retaining exact fail-closed validation.",
        "baseline_archive": "v3_rca_blocker_resolution_20260925/v23_blinded",
        "baseline_run_manifest_sha256": sha(freeze_path),
        "population_count": len(ordered_ids),
        "development_only": True,
        "primary_reliability_measure": "valid reports / all 12 fixed cases; technical failures are separate outcomes",
        "must_not_change": ["H0-H5 candidate generation", "exact ID checks", "V2.1 status semantics", "transport retries=0", "tool-call budget=8", "Phase 2.12", "VDT"],
        "live_probe_plan": ["valid and invalid report references", "bounded report repair with status preservation", "tool signature defects", "tool budget exhausted final-report transition"],
        "replication_rule": "Run same fixed 12 consumed development cases only after focused tests and full regression pass; freeze predictions before labels.",
        "ground_truth_access_before_prediction_freeze": False,
        "phase2_12_per_case_access": False,
        "raw_provider_output_policy": "Never fabricate absent V2.3 raw content; mark unavailable because it was not persisted.",
    })
    dump("V23_FAILURE_CORPUS.json", {
        "schema_version": "rca_v23_failure_corpus_v1",
        "source_run": "v23_blinded",
        "failure_count": len(failures),
        "raw_outputs_recoverable": False,
        "cases": failures,
    })
    categories = {
        "schema_version": "rca_v23_failure_taxonomy_v1",
        "counts": {
            "unknown_evidence": sum("RCA_REPORT_UNKNOWN_EVIDENCE" in str(x["validator_result"]) for x in failures),
            "tool_budget_or_excessive_call": sum(x["stage"] == "TOOL_BUDGET_GUARD" for x in failures),
        },
        "unknown_evidence_subtypes": {name: "UNRESOLVED_RAW_OUTPUT_NOT_PERSISTED" for name in (
            "FABRICATED_ID", "MALFORMED_ID", "VALID_LOOKING_NOT_EXPOSED", "WRONG_CANDIDATE_SCOPE",
            "SERIALIZATION_ESCAPING_CORRUPTION", "STALE_STAGE_ID")},
        "tool_subtypes": {**{name: "UNRESOLVED_ARGUMENT_TRACE_NOT_PERSISTED" for name in (
            "UNKNOWN_TOOL", "INVALID_ARGUMENT_NAME", "INVALID_ARGUMENT_TYPE", "MISSING_REQUIRED_ARGUMENT",
            "REPEATED_CALL", "DUPLICATE_SEMANTIC_CALL", "SERIALIZATION_DEFECT")},
            "TOOL_BUDGET_EXHAUSTION": "EVIDENCE_SUPPORTED_EXACT_ACTION_COUNT_EXCEEDS_FROZEN_BUDGET"},
        "evidence_supported_categories": [
            {"category": "TOOL_BUDGET_EXHAUSTION", "count": sum(x["stage"] == "TOOL_BUDGET_GUARD" for x in failures),
             "basis": "Exact orchestrator error code INVALID_OR_EXCESSIVE_AGENT_TOOL_CALLS; nine TOOL actions were recorded against the frozen budget of eight."}
        ],
        "limitations": "Unknown-reference subtype and tool-argument subtype cannot be recovered because V2.3 persisted neither raw provider content nor tool arguments.",
    }
    dump("V23_FAILURE_TAXONOMY.json", categories)
    dump("V23_FAILURE_REPLAY_RESULTS.json", {
        "schema_version": "rca_v23_failure_replay_results_v1",
        "historical_exact_raw_replay": "NOT_POSSIBLE_RAW_OUTPUT_NOT_PERSISTED",
        "contract_level_replay": "PENDING_V24_FOCUSED_TESTS",
        "cases": [{"opaque_incident_id": x["opaque_incident_id"], "frozen_failure_code": x["validator_result"],
                   "reproduction_scope": "ERROR_CLASS_ONLY; NOT_EXACT_MODEL_OUTPUT"} for x in failures],
    })
    print(json.dumps({"failure_count": len(failures), "out": str(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
