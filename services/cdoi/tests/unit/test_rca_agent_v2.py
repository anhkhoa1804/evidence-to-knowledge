"""Synthetic qualification for the separately-versioned RCA Agent V2."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cdoi.rca_agent_v2 import RCAAgentV2, V2AgentBudget
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, RCAOrchestrator

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"


def _prepared(tmp_path):
    return RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", tmp_path / "store.sqlite")


def _abstain(request):
    ids = [item["candidate_id"] for item in request["preloaded_candidate_profiles"]]
    return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                         "alternative_hypotheses": [], "supporting_evidence_ids": [],
                         "contradictory_evidence_ids": [], "reasoning_summary": "Profiles do not distinguish an investigation hypothesis.",
                         "limitations": ["MISSING_DISTINGUISHING_SIGNAL"], "abstention_reason": "MISSING_DISTINGUISHING_SIGNAL",
                         "investigated_candidate_ids": ids, "comparison_completed": True,
                         "missing_or_conflicting_evidence": ["MISSING_TRACE_EVIDENCE"]}}


class AbstainingV2Model:
    prompt_version = "rca_agent_qwen_v2"; system_prompt = "synthetic"
    def __init__(self): self.requests = []
    def generate(self, request):
        self.requests.append(dict(request))
        return _abstain(request) if "preloaded_candidate_profiles" in request else {"report": {}}
    def repair_output(self, raw_output, error_code, request): raise AssertionError("repair should not run")


class PrematureAbstainingV2Model(AbstainingV2Model):
    def generate(self, request):
        self.requests.append(dict(request))
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                            "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
                            "reasoning_summary": "premature", "limitations": [], "abstention_reason": None}}
    def repair_output(self, raw_output, error_code, request):
        assert error_code == "V2_ABSTENTION_H1_COMPARISON_REQUIRED"
        return _abstain(request)


class ToolFallbackV2Model(AbstainingV2Model):
    def __init__(self): super().__init__(); self.calls = 0
    def generate(self, request):
        self.requests.append(dict(request)); self.calls += 1
        if self.calls == 1:
            return {"tool_calls": [{"name": "get_expanded_candidates", "arguments": {
                "incident_id": request["incident"]["incident_id"], "fallback_reason": "H1_AMBIGUOUS"}}]}
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
                            "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
                            "reasoning_summary": "H5 did not resolve H1 ambiguity.", "limitations": ["H1_AMBIGUOUS"],
                            "abstention_reason": "H1_AMBIGUOUS", "investigated_candidate_ids": self.h1_ids,
                            "comparison_completed": True, "missing_or_conflicting_evidence": ["CONFLICTING_H1_EVIDENCE"]}}
    @property
    def h1_ids(self):
        return [item["candidate_id"] for item in self.requests[0]["preloaded_candidate_profiles"]]


class UnknownEvidenceV2Model(AbstainingV2Model):
    def generate(self, request):
        self.requests.append(dict(request))
        result = _abstain(request)
        result["report"]["status"] = "RCA_HYPOTHESIS"
        result["report"]["primary_hypothesis"] = {"candidate_id": request["candidates"]["items"][0]["candidate_id"],
            "statement": "invalid", "supporting_evidence_ids": ["not-real"], "limitations": []}
        result["report"]["supporting_evidence_ids"] = ["not-real"]
        result["report"]["abstention_reason"] = None
        return result
    def repair_output(self, raw_output, error_code, request): raise ValueError(error_code)


class MissingPrimaryV2Model(AbstainingV2Model):
    def generate(self, request):
        self.requests.append(dict(request))
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": None,
                            "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
                            "reasoning_summary": "invalid", "limitations": [], "abstention_reason": None}}
    def repair_output(self, raw_output, error_code, request): raise ValueError(error_code)


class ForbiddenToolV2Model(AbstainingV2Model):
    def generate(self, request):
        self.requests.append(dict(request))
        return {"tool_calls": [{"name": "commit_to_kg", "arguments": {}}]}


def test_v2_preloads_all_h1_profiles_and_records_comparison(tmp_path):
    prepared = _prepared(tmp_path); model = AbstainingV2Model()
    try:
        report, trace = RCAAgentV2(model).investigate(
            __import__("cdoi.rca_investigation", fromlist=["ReadOnlyRCATools"]).ReadOnlyRCATools(
                prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store,
                tuple(item for item in prepared.h5_candidates if item.candidate_id not in {x.candidate_id for x in prepared.h1_candidates})),
            CandidateSourceMode.H1_THEN_H5_FALLBACK)
        assert report.status == "INSUFFICIENT_EVIDENCE"
        assert {item["candidate_id"] for item in model.requests[0]["preloaded_candidate_profiles"]} == {item.candidate_id for item in prepared.h1_candidates}
        assert trace["states"][:3] == ["INITIALIZED", "H1_PROFILES_LOADED", "H1_COMPARED"]
        assert trace["states"][-1] == "ABSTAIN_READY"
    finally: prepared.store.close()


def test_v2_rejects_premature_abstention_then_performs_one_bounded_repair(tmp_path):
    prepared = _prepared(tmp_path); output = tmp_path / "v2"; model = PrematureAbstainingV2Model()
    try:
        report = RCAOrchestrator().run(prepared, output, InvestigationMode.AGENT,
                                       CandidateSourceMode.H1_THEN_H5_FALLBACK, RCAAgentV2(model))
        trace = json.loads((output / "AGENT_TRACE.json").read_text())
        assert report.status == "INSUFFICIENT_EVIDENCE"
        assert trace["repairs"] == [{"attempt": 1, "error_code": "V2_ABSTENTION_H1_COMPARISON_REQUIRED", "status": "SUCCEEDED"}]
    finally: prepared.store.close()


def test_v2_h5_fallback_requires_reason_and_is_accounted(tmp_path):
    prepared = _prepared(tmp_path); model = ToolFallbackV2Model()
    try:
        tools_mod = __import__("cdoi.rca_investigation", fromlist=["ReadOnlyRCATools"])
        expanded = tuple(item for item in prepared.h5_candidates if item.candidate_id not in {x.candidate_id for x in prepared.h1_candidates})
        report, trace = RCAAgentV2(model).investigate(tools_mod.ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded))
        assert report.status == "INSUFFICIENT_EVIDENCE"
        assert trace["fallback"]["fallback_reason"] == "H1_AMBIGUOUS"
        assert trace["tool_calls"][0]["tool_name"] == "get_expanded_candidates"
    finally: prepared.store.close()


def test_v2_unknown_evidence_fails_closed_and_does_not_mutate(tmp_path):
    prepared = _prepared(tmp_path)
    try:
        with pytest.raises(ValueError, match="RCA_REPORT_UNKNOWN_EVIDENCE"):
            RCAAgentV2(UnknownEvidenceV2Model()).investigate(
                __import__("cdoi.rca_investigation", fromlist=["ReadOnlyRCATools"]).ReadOnlyRCATools(
                    prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store))
    finally: prepared.store.close()


def test_v2_profile_budget_and_source_policy_are_explicit(tmp_path):
    prepared = _prepared(tmp_path)
    try:
        tools = __import__("cdoi.rca_investigation", fromlist=["ReadOnlyRCATools"]).ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store)
        with pytest.raises(ValueError, match="V2_REQUIRES_H1_THEN_H5_FALLBACK"):
            RCAAgentV2(AbstainingV2Model()).investigate(tools, CandidateSourceMode.H1_SHORTLIST)
        with pytest.raises(ValueError, match="V2_H1_PROFILE_PRELOAD_BUDGET_EXCEEDED"):
            RCAAgentV2(AbstainingV2Model(), budget=V2AgentBudget(max_h1_profiles=1)).investigate(tools)
    finally: prepared.store.close()


def test_v2_primary_requirement_and_technical_failure_state_are_preserved(tmp_path):
    prepared = _prepared(tmp_path)
    try:
        output = tmp_path / "missing-primary"
        report = RCAOrchestrator().run(prepared, output, InvestigationMode.AGENT,
                                       CandidateSourceMode.H1_THEN_H5_FALLBACK, RCAAgentV2(MissingPrimaryV2Model()))
        assert report.status == "TECHNICAL_FAILURE"
        assert json.loads((output / "AGENT_TRACE.json").read_text())["states"][-1] == "TECHNICAL_FAILURE"
        output = tmp_path / "forbidden-tool"
        report = RCAOrchestrator().run(prepared, output, InvestigationMode.AGENT,
                                       CandidateSourceMode.H1_THEN_H5_FALLBACK, RCAAgentV2(ForbiddenToolV2Model()))
        trace = json.loads((output / "AGENT_TRACE.json").read_text())
        assert report.status == "TECHNICAL_FAILURE" and trace["states"][-1] == "TECHNICAL_FAILURE"
    finally: prepared.store.close()
