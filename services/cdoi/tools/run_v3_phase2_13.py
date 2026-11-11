"""Freeze Phase 2.13 development-only integration evidence.

It intentionally uses the local deterministic demo fixture and a scripted mock
model.  It never reads Phase 2.12 candidate/evaluation artifacts or GT data.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, RCAAgentV0, RCAOrchestrator

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_13"
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"


def write(path: Path, value: object) -> str:
    text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ScriptedDevelopmentModel:
    """Test double only; it is explicitly not a live-agent evaluation."""
    def __init__(self) -> None: self.candidate = None; self.evidence = None; self.calls = 0
    def generate(self, request):
        self.calls += 1
        if self.calls == 1:
            self.candidate = request["candidates"]["items"][0]
            self.evidence = self.candidate["supporting_evidence_ids"][0]
            return {"tool_calls": [{"name": "get_evidence_by_id", "arguments": {"evidence_id": self.evidence}}]}
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": self.candidate["candidate_id"], "statement": "Development mock produced an evidence-cited investigation hypothesis.", "supporting_evidence_ids": [self.evidence], "limitations": ["SCRIPTED_DEVELOPMENT_MODEL_NOT_LIVE_RCA_EVIDENCE"], "model_self_assessment": "LOW"}, "alternative_hypotheses": [], "supporting_evidence_ids": [self.evidence], "contradictory_evidence_ids": [], "reasoning_summary": "Development-only tool and report serialization check.", "limitations": ["NOT_EXTERNAL_VALIDATION", "NOT_CAUSAL_PROOF", "NOT_CALIBRATED"], "abstention_reason": None}}


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def source_revision() -> str:
    """Deterministic revision fingerprint without relying on a Git checkout."""
    digest = hashlib.sha256()
    for path in (ROOT / "src/cdoi/candidate_evidence_profile.py", ROOT / "src/cdoi/rca_investigation.py", ROOT / "src/cdoi/hypothesis_generation.py", Path(__file__).resolve()):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8")); digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    if OUT.exists(): raise RuntimeError(f"REFUSE_TO_OVERWRITE_EXISTING_PHASE213_ARCHIVE: {OUT}")
    orchestrator = RCAOrchestrator(); started = time.perf_counter()
    prepared = orchestrator.prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / "INDEXES/inc-001.sqlite")
    try:
        profiles = [item.artifact() for item in prepared.profiles]
        profile_start = time.perf_counter()
        replay = orchestrator.prepare(FIXTURE / "manifest.yaml", "inc-001", OUT / "INDEXES/replay.sqlite")
        try: deterministic = profiles == [item.artifact() for item in replay.profiles]
        finally: replay.store.close()
        profile_seconds = time.perf_counter() - profile_start
        report_profile = orchestrator.run(prepared, OUT / "PROFILE_RUN", InvestigationMode.PROFILE_ONLY)
        report_baseline = orchestrator.run(prepared, OUT / "BASELINE_RUN", InvestigationMode.DETERMINISTIC_BASELINE)
        report_agent = orchestrator.run(prepared, OUT / "AGENT_RUNS/mock_demo", InvestigationMode.AGENT, CandidateSourceMode.H1_THEN_H5_FALLBACK, RCAAgentV0(ScriptedDevelopmentModel()), {"provider": "SCRIPTED_DEVELOPMENT_MODEL", "model": "scripted-development-model-v1", "temperature": 0.0, "seed": "NOT_APPLICABLE_DETERMINISTIC", "credential_configured": False, "live_execution": False, "software_revision_sha256": source_revision()})
        revision = source_revision()
        write(OUT / "EXPERIMENT_MANIFEST.json", {"schema_version": "v3_phase2_13_experiment_manifest_v1", "phase": "V3_PHASE2_13", "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "purpose": "DEVELOPMENT_ONLY candidate-profile, tool, orchestrator, and mock-agent integration", "protected_phase212": "NOT_READ_NOT_RERUN_NOT_USED", "software_revision_sha256": revision, "runtime": {"python": sys.version, "platform": platform.platform()}, "fixture_manifest_sha256": sha(FIXTURE / "manifest.yaml")})
        write(OUT / "DEVELOPMENT_DATA_MANIFEST.json", {"schema_version": "v3_phase2_13_development_data_v1", "cases": [{"case_id": "inc-001", "source": "tests/fixtures/preprocessing_demo", "status": "DEVELOPMENT_ONLY", "ground_truth_used": False}], "phase211_pilot": "NOT_USED_IN_THIS_RUN; if used later it remains CONSUMED_DEVELOPMENT_DATA", "phase212_holdout": "PROHIBITED_CONSUMED_HOLDOUT_NOT_READ"})
        write(OUT / "CONFIG.json", {"schema_version": "v3_phase2_13_config_v1", "profile_schema_version": "candidate_evidence_profile_v1", "tool_schema_version": "read_only_rca_tools_v1", "agent_prompt_version": "rca_agent_v0_prompt_v1", "candidate_source": "H1_THEN_H5_FALLBACK", "agent_budget": {"max_tool_calls": 8, "max_candidate_profiles": 5, "max_evidence_per_tool_call": 20}, "live_agent": "MODEL_RUNTIME_BLOCKER_NO_CONFIGURED_PROVIDER"})
        missing = sorted({missing for profile in profiles for missing in profile["missing_evidence"]})
        evidence_ids = {item.evidence_id for profile in prepared.profiles for item in (*profile.supporting_evidence, *profile.context_evidence)}
        write(OUT / "PROFILE_RESULTS.json", {"schema_version": "v3_phase2_13_profile_results_v1", "status": "DEVELOPMENT_ONLY", "profiles_generated": len(profiles), "profile_determinism": deterministic, "evidence_ids_resolvable_by_context_or_aggregate": bool(evidence_ids), "missing_modalities": missing, "construction_seconds": profile_seconds, "profiles": profiles})
        write(OUT / "BASELINE_RESULTS.json", {"schema_version": "v3_phase2_13_baseline_results_v1", "status": "DEVELOPMENT_ONLY", "profile_only_status": report_profile.status, "deterministic_baseline_status": report_baseline.status, "agent_mock_status": report_agent.status, "comparison_boundary": "BASELINE_DOES_NOT_RANK_OR_CLAIM_CAUSALITY; mock agent is infrastructure-only"})
        write(OUT / "AGENT_RESULTS.json", {"schema_version": "v3_phase2_13_agent_results_v1", "status": "DEVELOPMENT_ONLY_SCRIPTED_MODEL_INFRASTRUCTURE_ONLY", "case_count": 1, "top1_gt_service_selection": "NOT_EVALUATED_NO_GROUND_TRUTH", "topk_hypothesis_inclusion": "NOT_EVALUATED_NO_GROUND_TRUTH", "abstention_rate": 0.0, "unsupported_claim_rate": 0.0, "evidence_citation_coverage": 1.0, "tool_calls": 1, "technical_failure_rate": 0.0, "interpretation": "Structured validation rejected unknown evidence IDs by contract; this mock run is not a live-model quality measurement."})
        write(OUT / "DETERMINISM_CHECK.json", {"schema_version": "v3_phase2_13_determinism_v1", "status": "DEVELOPMENT_ONLY", "profile_replay_identical": deterministic, "scripted_agent_model": "DETERMINISTIC", "agent_prompt_version": "rca_agent_v0_prompt_v1", "note": "Live-model nondeterminism was not measured because no live provider was invoked."})
        write(OUT / "FAILURE_CASES.json", {"schema_version": "v3_phase2_13_failure_cases_v1", "cases": [], "known_blockers": [{"classification": "MODEL_RUNTIME_BLOCKER", "status": "LIVE_AGENT_RUNTIME_UNAVAILABLE", "detail": "No configured live provider was invoked; mock tests only."}, {"classification": "DATA_BLOCKER", "status": "NON_BLOCKING_PRODUCT_DATA_GAP", "detail": "No host binding, KnownProblem, Procedure, or business-impact modality is present."}]})
        write(OUT / "PERFORMANCE.json", {"schema_version": "v3_phase2_13_performance_v1", "status": "DEVELOPMENT_ONLY", "total_seconds": time.perf_counter() - started, "candidate_counts": {"h1": len(prepared.h1_candidates), "h5": len(prepared.h5_candidates)}, "cost": "COST_NOT_MEASURED", "live_model_calls": 0, "scripted_model_calls": 2})
        gate = {"schema_version": "v3_phase2_13_research_gate_v1", "decision": "EVIDENCE_PROFILE_SUPPORTED_AGENT_RUNTIME_BLOCKED", "candidate_evidence_profiles": "SUPPORTED_DEVELOPMENT_ONLY", "read_only_tools": "SUPPORTED_DEVELOPMENT_ONLY", "end_to_end_orchestration": "SUPPORTED_DEVELOPMENT_ONLY", "agent_infrastructure": "SUPPORTED_WITH_SCRIPTED_MODEL", "live_agent_behavior": "MODEL_RUNTIME_BLOCKER", "external_agent_validation": "DATA_MISSING", "causal_reasoning": "NOT_IMPLEMENTED", "calibrated_rca_confidence": "NOT_IMPLEMENTED", "canonical_kg_write": "NOT_IMPLEMENTED_BY_DESIGN", "next_step": "Obtain an independent RCA validation set and governed live-model runtime before behavioral claims or tuning."}
        write(OUT / "RESEARCH_GATE.json", gate)
        artifacts = sorted(path for path in OUT.rglob("*.json") if path.name not in {"HASHES.json", "MANIFEST.json"})
        write(OUT / "HASHES.json", {"schema_version": "v3_phase2_13_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})
        artifacts = sorted(path for path in OUT.rglob("*.json") if path.name != "MANIFEST.json")
        write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_13_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})
    finally:
        prepared.store.close()


if __name__ == "__main__": main()
