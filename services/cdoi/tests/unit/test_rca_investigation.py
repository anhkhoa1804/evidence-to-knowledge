from pathlib import Path
import hashlib

import pytest

from cdoi.rca_investigation import (
    CandidateSourceMode, InvestigationMode, RCAAgentV0, RCAOrchestrator,
    RCAReport, ReadOnlyRCATools,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"


class ScriptedModel:
    def __init__(self): self.candidate = None; self.evidence = None; self.calls = 0
    def generate(self, request):
        self.calls += 1
        if self.calls == 1:
            self.candidate = request["candidates"]["items"][0]
            self.evidence = self.candidate["supporting_evidence_ids"][0]
            return {"tool_calls": [{"name": "get_evidence_by_id", "arguments": {"evidence_id": self.evidence}}]}
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": self.candidate["candidate_id"], "statement": "A leading investigation hypothesis based on cited evidence.", "supporting_evidence_ids": [self.evidence], "limitations": ["NOT_CAUSALLY_PROVEN"], "model_self_assessment": "LOW"}, "supporting_evidence_ids": [self.evidence], "contradictory_evidence_ids": [], "reasoning_summary": "Evidence-backed hypothesis only.", "limitations": ["NOT_CALIBRATED"], "abstention_reason": None}}


class AbstainingModel:
    def generate(self, request):
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None, "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [], "reasoning_summary": "Competing hypotheses remain unresolved.", "limitations": ["SPARSE_MODALITIES"], "abstention_reason": "MULTIPLE_PLAUSIBLE_CANDIDATES"}}


class InvalidModel:
    def generate(self, request):
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": "unknown", "statement": "invalid", "supporting_evidence_ids": []}}}


def _tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            digest.update(item.relative_to(path).as_posix().encode()); digest.update(item.read_bytes())
    return digest.hexdigest()


def _prepared(tmp_path):
    return RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", tmp_path / "store.sqlite")


def test_read_only_tools_are_bounded_and_preserve_provenance(tmp_path):
    prepared = _prepared(tmp_path)
    tools = ReadOnlyRCATools(prepared.context, prepared.h5_candidates, prepared.profiles, prepared.store)
    first = tools.get_candidates("inc-001", limit=1)
    assert first["truncated"] is True and first["total"] == len(prepared.h5_candidates)
    profile = tools.get_candidate_profile("inc-001", first["items"][0]["candidate_id"])
    assert profile["profile"]["candidate_id"] == first["items"][0]["candidate_id"]
    assert tools.get_evidence_by_id(first["items"][0]["supporting_evidence_ids"][0])["status"] == "FOUND"
    with pytest.raises(ValueError, match="READ_ONLY_TOOL_NOT_PERMITTED"):
        tools.call("commit_to_kg", {})
    prepared.store.close()


def test_agent_mock_is_auditable_and_report_rejects_unknown_evidence(tmp_path):
    prepared = _prepared(tmp_path)
    output = tmp_path / "agent"
    report = RCAOrchestrator().run(prepared, output, InvestigationMode.AGENT, CandidateSourceMode.H5_EXPANDED, RCAAgentV0(ScriptedModel()))
    assert report.status == "RCA_HYPOTHESIS"
    assert (output / "AGENT_TRACE.json").exists()
    assert report.primary_hypothesis.model_self_assessment == "LOW"
    invalid = RCAReport("inc-001", "RCA_HYPOTHESIS", report.primary_hypothesis, (), ("invented-evidence",), (), "", (), None, 0, {})
    with pytest.raises(ValueError, match="UNKNOWN_EVIDENCE"):
        invalid.validate({item.candidate_id for item in prepared.h5_candidates}, set())
    prepared.store.close()


def test_profile_and_baseline_modes_do_not_select_or_rank(tmp_path):
    prepared = _prepared(tmp_path)
    report = RCAOrchestrator().run(prepared, tmp_path / "baseline", InvestigationMode.DETERMINISTIC_BASELINE)
    assert report.status == "INSUFFICIENT_EVIDENCE"
    assert report.primary_hypothesis is None
    assert "NO_CAUSAL_OR_CALIBRATED_RANKING" in report.abstention_reason
    prepared.store.close()


def test_agent_can_abstain_and_missing_agent_is_explicit_technical_failure(tmp_path):
    prepared = _prepared(tmp_path)
    orchestrator = RCAOrchestrator()
    abstained = orchestrator.run(prepared, tmp_path / "abstain", InvestigationMode.AGENT, agent=RCAAgentV0(AbstainingModel()))
    unavailable = orchestrator.run(prepared, tmp_path / "unavailable", InvestigationMode.AGENT)
    assert abstained.status == "INSUFFICIENT_EVIDENCE" and abstained.primary_hypothesis is None
    assert unavailable.status == "TECHNICAL_FAILURE"
    assert unavailable.abstention_reason == "NO_AGENT_MODEL_CONFIGURED"
    prepared.store.close()


def test_invalid_agent_output_fails_closed_and_agent_does_not_mutate_canonical_state(tmp_path):
    prepared = _prepared(tmp_path)
    # Agent V0 is not allowed to reach the persisted canonical ontology state.
    # Exclude model caches and other large non-canonical test data deliberately.
    canonical = ROOT / "data" / "ontology_versions"
    before = _tree_hash(canonical)
    report = RCAOrchestrator().run(prepared, tmp_path / "invalid", InvestigationMode.AGENT, agent=RCAAgentV0(InvalidModel()))
    assert report.status == "TECHNICAL_FAILURE"
    assert report.abstention_reason == "INVALID_AGENT_OUTPUT"
    assert _tree_hash(canonical) == before
    prepared.store.close()
