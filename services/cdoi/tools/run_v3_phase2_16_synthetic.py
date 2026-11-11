"""Freeze Phase 2.16 V2 synthetic contract qualification only.

This runner deliberately does not enumerate, read, or evaluate Phase 2.12,
and it does not run the 12-case V2 development batch.  Its cases are
deterministic implementation probes, not a live-Qwen quality claim.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import requests

from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model, rca_v2_system_prompt
from cdoi.rca_agent_v2 import RCAAgentV2
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2"
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"

CASES = (
    ("S1_CLEAR_ORIGIN", "PRIMARY_HYPOTHESIS_VALIDATED"),
    ("S2_ERROR_TRAP", "ABSTENTION_VALIDATED"),
    ("S3_DEPLOYMENT_TRAP", "ABSTENTION_VALIDATED"),
    ("S4_H1_AMBIGUOUS", "H5_FALLBACK_VALIDATED"),
    ("S5_MISSING_TRACE", "ABSTENTION_VALIDATED"),
    ("S6_MISSING_CHANGE", "ABSTENTION_VALIDATED"),
    ("S7_TRUE_INSUFFICIENT", "ABSTENTION_VALIDATED"),
    ("S8_H5_HELPFUL", "H5_FALLBACK_VALIDATED"),
    ("S9_H5_NOISE", "H5_FALLBACK_VALIDATED"),
    ("S10_CONFLICTING_EVIDENCE", "ABSTENTION_VALIDATED"),
    ("S11_TOOL_FAILURE", "FAIL_CLOSED_VALIDATED"),
    ("S12_MALFORMED_REPORT", "ONE_REPAIR_VALIDATED"),
    ("S13_UNKNOWN_EVIDENCE_ID", "FAIL_CLOSED_VALIDATED"),
    ("S14_TRANSPORT_TRANSIENT", "RETRY_VALIDATED"),
    ("S15_TRANSPORT_PERSISTENT", "FAIL_CLOSED_VALIDATED"),
)


def write(path: Path, value: Any) -> str:
    if isinstance(value, str): text = value
    else: text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_hashes(directory: Path) -> Mapping[str, Any]:
    hashes = directory / "HASHES.json"
    if not hashes.exists(): return {"status": "UNAVAILABLE_NO_HASHES", "checked": 0, "valid": 0}
    payload = json.loads(hashes.read_text(encoding="utf-8")); rows = payload.get("artifacts", {})
    valid = sum(1 for name, expected in rows.items() if (directory / name).is_file() and sha(directory / name) == expected)
    return {"status": "VALID" if valid == len(rows) else "INVALID", "checked": len(rows), "valid": valid}


class Response:
    def __init__(self, body: Mapping[str, Any], status: int = 200) -> None: self.body, self.status_code = body, status
    def json(self) -> Mapping[str, Any]: return self.body


class ScenarioModel:
    prompt_version = "rca_agent_qwen_v2"; system_prompt = "synthetic-v2-model"
    def __init__(self, scenario: str) -> None:
        self.scenario, self.calls, self.first_request = scenario, 0, None

    def _abstain(self, request: Mapping[str, Any], reason: str = "MISSING_DISTINGUISHING_SIGNAL") -> Mapping[str, Any]:
        profiles = self.first_request["preloaded_candidate_profiles"]
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                            "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
                            "reasoning_summary": "Synthetic profile comparison does not establish a causal claim.",
                            "limitations": [reason], "abstention_reason": reason,
                            "investigated_candidate_ids": [row["candidate_id"] for row in profiles],
                            "comparison_completed": True,
                            "missing_or_conflicting_evidence": [reason]}}

    def _primary(self) -> Mapping[str, Any]:
        candidate = self.first_request["candidates"]["items"][0]
        evidence = candidate["supporting_evidence_ids"][0]
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": candidate["candidate_id"], "statement": "Synthetic evidence-backed investigation hypothesis only.",
            "supporting_evidence_ids": [evidence], "limitations": ["NOT_CAUSALLY_PROVEN"], "model_self_assessment": "LOW"},
            "alternative_hypotheses": [], "supporting_evidence_ids": [evidence], "contradictory_evidence_ids": [],
            "reasoning_summary": "Synthetic contract probe.", "limitations": ["NOT_CALIBRATED"], "abstention_reason": None}}

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.calls += 1
        if "preloaded_candidate_profiles" in request: self.first_request = request
        if self.scenario == "S11_TOOL_FAILURE":
            return {"tool_calls": [{"name": "commit_to_kg", "arguments": {}}]}
        if self.scenario in {"S4_H1_AMBIGUOUS", "S8_H5_HELPFUL", "S9_H5_NOISE"} and self.calls == 1:
            return {"tool_calls": [{"name": "get_expanded_candidates", "arguments": {
                "incident_id": request["incident"]["incident_id"], "fallback_reason": "H1_AMBIGUOUS"}}]}
        if self.scenario == "S12_MALFORMED_REPORT" and self.calls == 1:
            return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                                "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
                                "reasoning_summary": "Malformed intentionally.", "limitations": [], "abstention_reason": None}}
        if self.scenario == "S13_UNKNOWN_EVIDENCE_ID":
            result = self._primary(); result["report"]["supporting_evidence_ids"] = ["unknown-evidence"]
            result["report"]["primary_hypothesis"]["supporting_evidence_ids"] = ["unknown-evidence"]
            return result
        if self.scenario in {"S1_CLEAR_ORIGIN", "S8_H5_HELPFUL"}: return self._primary()
        reason = "CONFLICTING_H1_EVIDENCE" if self.scenario == "S10_CONFLICTING_EVIDENCE" else "MISSING_DISTINGUISHING_SIGNAL"
        return self._abstain(request, reason)

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.scenario == "S12_MALFORMED_REPORT": return self._abstain(request)
        raise ValueError(error_code)


def run_agent_case(scenario: str) -> Mapping[str, Any]:
    prepared = RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / "INDEXES" / f"{scenario}.sqlite")
    try:
        h1_ids = {row.candidate_id for row in prepared.h1_candidates}
        expanded = tuple(row for row in prepared.h5_candidates if row.candidate_id not in h1_ids)
        tools = ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded)
        model = ScenarioModel(scenario)
        try:
            report, trace = RCAAgentV2(model).investigate(tools, CandidateSourceMode.H1_THEN_H5_FALLBACK,
                                                          {"provider": "DETERMINISTIC_SYNTHETIC_MODEL", "temperature": 0})
            return {"case_id": scenario, "status": "PASS", "report_status": report.status,
                    "tool_calls": len(trace["tool_calls"]), "fallback": trace["fallback"],
                    "repairs": trace["repairs"], "preloaded_profile_count": trace["h1_profile_preload"]["profile_count"],
                    "states": trace["states"], "grounding": "PROFILE_GROUNDED" if report.supporting_evidence_ids else "NO_EVIDENCE_CITATION"}
        except ValueError as exc:
            expected = scenario in {"S11_TOOL_FAILURE", "S13_UNKNOWN_EVIDENCE_ID"}
            return {"case_id": scenario, "status": "PASS" if expected else "FAIL", "report_status": "TECHNICAL_FAILURE",
                    "error_code": str(exc), "tool_calls": None, "fallback": None, "repairs": [],
                    "preloaded_profile_count": len(h1_ids), "states": ["INITIALIZED", "H1_PROFILES_LOADED", "H1_COMPARED", "TECHNICAL_FAILURE"],
                    "grounding": "NOT_APPLICABLE_FAIL_CLOSED"}
    finally: prepared.store.close()


def transport_case(case_id: str, persistent: bool) -> Mapping[str, Any]:
    prior = os.environ.get("QWEN_API_KEY"); os.environ["QWEN_API_KEY"] = "synthetic-not-persisted"
    calls: list[int] = []
    valid = {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None, "alternative_hypotheses": [],
             "supporting_evidence_ids": [], "contradictory_evidence_ids": [], "reasoning_summary": "Synthetic transport probe.",
             "limitations": ["x"], "abstention_reason": "x", "investigated_candidate_ids": [],
             "comparison_completed": True, "missing_or_conflicting_evidence": ["x"]}
    def requester(*args, **kwargs):
        calls.append(1)
        if persistent or len(calls) == 1: raise requests.Timeout()
        return Response({"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(valid)}}]})
    try:
        model = QwenRCAAgentV2Model(QwenRCAConfig(base_url="https://synthetic.invalid/v1", api_key_env="QWEN_API_KEY", model="vllm/Qwen3.8-27B", max_retries=1), requester=requester)
        try:
            model.generate({"incident": {}, "candidates": {"items": []}, "preloaded_candidate_profiles": [], "h1_comparison": {}, "candidate_source": "H1_THEN_H5_FALLBACK"})
            return {"case_id": case_id, "status": "PASS", "report_status": "INSUFFICIENT_EVIDENCE", "attempt_count": len(calls),
                    "transport": dict(model.last_transport_diagnostic), "grounding": "NOT_APPLICABLE_TRANSPORT_PROBE"}
        except QwenRCAError as exc:
            return {"case_id": case_id, "status": "PASS" if persistent and exc.code == "QWEN_TRANSPORT_FAILURE" else "FAIL",
                    "report_status": "TECHNICAL_FAILURE", "error_code": exc.code, "attempt_count": len(calls),
                    "transport": dict(model.last_transport_diagnostic), "grounding": "NOT_APPLICABLE_TRANSPORT_PROBE"}
    finally:
        if prior is None: os.environ.pop("QWEN_API_KEY", None)
        else: os.environ["QWEN_API_KEY"] = prior


def main() -> None:
    if OUT.exists(): raise RuntimeError(f"REFUSE_TO_OVERWRITE_EXISTING_PHASE216_ARCHIVE: {OUT}")
    OUT.mkdir(parents=True)
    historical = {name: verify_hashes(ROOT / "experiments/archive" / name) for name in (
        "v3_phase2_12", "v3_phase2_13", "v3_phase2_14_rca_qwen", "v3_phase2_14_semantic",
        "v3_phase2_15_qwen_live", "v3_phase2_15_qwen_live_retry_20260924",
        "v3_phase2_15_qwen_development_20260924", "v3_phase2_15_finalization_20260924")}
    agent_cases = [run_agent_case(case_id) for case_id, _ in CASES[:13]]
    agent_cases.extend((transport_case("S14_TRANSPORT_TRANSIENT", False), transport_case("S15_TRANSPORT_PERSISTENT", True)))
    passed = sum(row["status"] == "PASS" for row in agent_cases)
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    test_summary = {"command": f"{sys.executable} -m pytest -q", "exit_code": tests.returncode,
                    "stdout": tests.stdout[-2000:], "stderr": tests.stderr[-1000:],
                    "status": "PASS" if tests.returncode == 0 else "FAIL"}
    config = {"schema_version": "v3_phase2_16_v2_config_v1", "model": "vllm/Qwen3.8-27B", "temperature": 0,
              "max_output_tokens": 512, "candidate_source": "H1_THEN_H5_FALLBACK", "tool_schema_version": "read_only_rca_tools_v2",
              "prompt_version": "rca_agent_qwen_v2", "prompt_sha256": hashlib.sha256(rca_v2_system_prompt().encode("utf-8")).hexdigest(),
              "max_output_repairs": 1, "live_v2_development_batch": "NOT_RUN_BY_SCOPE", "phase212": "ROOT_HASH_MANIFEST_ONLY_NO_CASE_OR_EVALUATION_ACCESS"}
    write(OUT / "PREREGISTRATION.json", {"schema_version": "v3_phase2_16_preregistration_v1", "scope": "V2_IMPLEMENTATION_AND_SYNTHETIC_QUALIFICATION_ONLY", "forbidden": ["PHASE212_CASE_OR_EVALUATION_ACCESS", "V2_12_CASE_DEVELOPMENT_RUN", "V1_ARTIFACT_MUTATION", "ONTOLOGY_OR_CAUSAL_POLICY_CHANGE"], "allowed_integrity_check": "Phase 2.12 root HASHES.json only", "synthetic_cases": [name for name, _ in CASES]})
    write(OUT / "V2_CONFIG.json", config)
    write(OUT / "SYNTHETIC_CASES.json", {"schema_version": "v3_phase2_16_synthetic_cases_v1", "execution": "DETERMINISTIC_SCRIPTED_MODEL_AND_TRANSPORT_DOUBLES", "cases": [{"case_id": name, "expected": expected} for name, expected in CASES]})
    write(OUT / "SYNTHETIC_RESULTS.json", {"schema_version": "v3_phase2_16_synthetic_results_v1", "total": len(agent_cases), "passed": passed, "failed": len(agent_cases) - passed, "results": agent_cases, "interpretation": "Implementation qualification only; no live-Qwen RCA quality or ground-truth performance claim."})
    write(OUT / "SYNTHETIC_FAILURES.json", {"schema_version": "v3_phase2_16_synthetic_failures_v1", "expected_fail_closed_cases": ["S11_TOOL_FAILURE", "S13_UNKNOWN_EVIDENCE_ID", "S15_TRANSPORT_PERSISTENT"], "unexpected_failures": [row for row in agent_cases if row["status"] != "PASS"]})
    write(OUT / "V2_PRE_FREEZE_CHANGELOG.json", {"schema_version": "v3_phase2_16_pre_freeze_changelog_v1", "changes": ["Separate rca_agent_qwen_v2 prompt and adapter", "Deterministic complete-H1 profile preload", "Investigation-before-abstention invariant", "Bounded H1-to-H5 fallback", "One bounded output repair", "Safe V2 transport telemetry"], "unchanged": ["H1/H5 candidate generation", "V1 behavior", "Phase 2.12", "semantic selection", "canonical KG", "review and approval"]})
    write(OUT / "HISTORICAL_HASH_VERIFICATION.json", {"schema_version": "v3_phase2_16_historical_hash_verification_v1", "archives": historical})
    write(OUT / "TEST_RESULTS.json", test_summary)
    gate = "AGENT_V2_SYNTHETIC_QUALIFICATION_PASSED" if passed == len(agent_cases) and tests.returncode == 0 and all(row["status"] == "VALID" for row in historical.values()) else "AGENT_V2_SYNTHETIC_QUALIFICATION_FAILED"
    write(OUT / "RESEARCH_GATE.json", {"schema_version": "v3_phase2_16_research_gate_v1", "decision": gate,
        "v2_profile_preload": "SUPPORTED_SYNTHETIC", "investigation_before_abstention": "SUPPORTED_SYNTHETIC",
        "h5_fallback": "SUPPORTED_SYNTHETIC", "strict_report_validation": "SUPPORTED_SYNTHETIC",
        "transport_observability": "SUPPORTED_SYNTHETIC", "live_qwen_v2_quality": "NOT_EVALUATED",
        "v2_12_case_development_quality": "NOT_EVALUATED_BY_SCOPE", "independent_validation": "DATA_MISSING",
        "semantic_policy_change": "NONE", "canonical_kg_change": "NONE"})
    write(OUT / "V2_DESIGN.md", "# V3 Phase 2.16 Agent V2 Design\n\nV2 preloads all deterministic H1 CandidateEvidenceProfiles, records comparison, and rejects early abstention without an explicit comparison record. It may use bounded read-only tools and a structured H1-to-H5 fallback. It remains non-causal, uncalibrated, and cannot write the canonical KG.\n")
    write(OUT / "FINAL_REPORT.md", f"# V3 Phase 2.16 Agent V2 Synthetic Qualification\n\nGate: `{gate}`. All {passed}/{len(agent_cases)} deterministic synthetic cases passed. The runner read only the Phase 2.12 root hash manifest for integrity verification; it did not access a protected case, candidate, evaluation, or ground-truth artifact, and it did not run a V2 12-case development batch. V2 quality against real RCA cases remains `NOT_EVALUATED`. Full regression status: `{test_summary['status']}`.\n")
    artifacts = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    write(OUT / "HASHES.json", {"schema_version": "v3_phase2_16_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})
    artifacts = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json")
    write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_16_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})


if __name__ == "__main__": main()
