"""Fail-closed V2.1 status/report contract qualification."""
from __future__ import annotations

import pytest

from cdoi.rca_agent_v2_1 import RCAAgentV21
from cdoi.rca_investigation import CandidateSourceMode, RCAOrchestrator, ReadOnlyRCATools

from test_rca_agent_v2 import FIXTURE, _abstain

MISSING = object()


def _prepared(tmp_path):
    return RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", tmp_path / "store.sqlite")


def _tools(prepared):
    expanded = tuple(x for x in prepared.h5_candidates if x.candidate_id not in {y.candidate_id for y in prepared.h1_candidates})
    return ReadOnlyRCATools(prepared.context, prepared.h1_candidates, prepared.profiles, prepared.store, expanded)


class Model:
    prompt_version = "rca_agent_qwen_v2_1"; system_prompt = "synthetic"
    def __init__(self, first, repair=None): self.first, self.repair, self.requests, self.errors = first, repair, [], []
    def generate(self, request):
        self.requests.append(dict(request))
        if "prior_tool_results" in request: return {"report": _abstain(self.requests[0])["report"]}
        return {"report": self.first(request) if callable(self.first) else dict(self.first)}
    def repair_output(self, raw_output, error_code, request):
        self.errors.append(error_code)
        if isinstance(self.repair, Exception): raise self.repair
        if self.repair is None: raise ValueError(error_code)
        return {"report": self.repair(request) if callable(self.repair) else dict(self.repair)}


def _valid_hypothesis(request):
    candidate = request["candidates"]["items"][0]["candidate_id"]
    return {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": candidate,
        "statement": "synthetic evidence-backed hypothesis", "supporting_evidence_ids": [], "limitations": ["synthetic"]},
        "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
        "reasoning_summary": "synthetic", "limitations": ["synthetic"]}


def _run(tmp_path, first, repair=None):
    prepared = _prepared(tmp_path); model = Model(first, repair)
    try: return RCAAgentV21(model).investigate(_tools(prepared), CandidateSourceMode.H1_THEN_H5_FALLBACK), model
    finally: prepared.store.close()


def test_v21_accepts_explicit_valid_abstention_and_hypothesis(tmp_path):
    (report, _), _model = _run(tmp_path, lambda req: _abstain(req)["report"])
    assert report.status == "INSUFFICIENT_EVIDENCE"
    (report, _), _model = _run(tmp_path, _valid_hypothesis)
    assert report.status == "RCA_HYPOTHESIS"


@pytest.mark.parametrize("status,error", [
    (MISSING, "RCA_STATUS_REQUIRED"), (None, "RCA_STATUS_REQUIRED"), ("", "RCA_STATUS_REQUIRED"),
    ("ABSTAIN", "RCA_STATUS_INVALID"), ("insufficient_evidence", "RCA_STATUS_INVALID"),
])
def test_v21_missing_null_empty_unknown_or_case_mismatched_status_never_defaults(tmp_path, status, error):
    raw = {"status": status} if status is not MISSING else {}
    with pytest.raises(ValueError, match="RCA_REPORT_CONTRACT_FAILURE"):
        _run(tmp_path, raw)
    # The direct V2.1 raw-contract validator reports the precise initial cause.
    with pytest.raises(ValueError, match=error):
        RCAAgentV21.validate_raw_report(raw, {"candidate"})


@pytest.mark.parametrize("mutate,error", [
    (lambda raw: raw.pop("abstention_reason"), "RCA_ABSTENTION_REASON_REQUIRED"),
    (lambda raw: raw.pop("investigated_candidate_ids"), "RCA_ABSTENTION_CANDIDATES_REQUIRED"),
])
def test_v21_invalid_abstention_is_repaired_or_fails_closed(tmp_path, mutate, error):
    def invalid(req):
        raw = _abstain(req)["report"]; mutate(raw); return raw
    (report, trace), model = _run(tmp_path, invalid, lambda req: _abstain(req)["report"])
    assert report.status == "INSUFFICIENT_EVIDENCE"
    assert trace["repairs"] == [{"attempt": 1, "error_code": error, "status": "SUCCEEDED"}]
    assert model.errors == [error]


def test_v21_missing_primary_unknown_candidate_and_unknown_evidence_fail_closed(tmp_path):
    def missing_primary(req): return {"status": "RCA_HYPOTHESIS", "primary_hypothesis": None, "limitations": ["x"]}
    with pytest.raises(ValueError, match="RCA_REPORT_CONTRACT_FAILURE:RCA_HYPOTHESIS_REQUIRES_PRIMARY"):
        _run(tmp_path, missing_primary)
    def unknown_candidate(req):
        raw = _valid_hypothesis(req); raw["primary_hypothesis"]["candidate_id"] = "unknown"; return raw
    with pytest.raises(ValueError, match="RCA_REPORT_CONTRACT_FAILURE:RCA_REPORT_UNKNOWN_CANDIDATE"):
        _run(tmp_path, unknown_candidate)
    def unknown_evidence(req):
        raw = _valid_hypothesis(req); raw["supporting_evidence_ids"] = ["unknown-evidence"]; return raw
    with pytest.raises(ValueError, match="RCA_REPORT_CONTRACT_FAILURE:RCA_REPORT_UNKNOWN_EVIDENCE"):
        _run(tmp_path, unknown_evidence)


def test_v21_missing_status_repair_and_repair_failure_becomes_technical(tmp_path):
    (report, trace), _model = _run(tmp_path, {}, lambda req: _abstain(req)["report"])
    assert report.status == "INSUFFICIENT_EVIDENCE" and trace["repairs"][0]["error_code"] == "RCA_STATUS_REQUIRED"
    prepared = _prepared(tmp_path); output = tmp_path / "technical"
    try:
        report = RCAOrchestrator().run(prepared, output, __import__("cdoi.rca_investigation", fromlist=["InvestigationMode"]).InvestigationMode.AGENT,
            CandidateSourceMode.H1_THEN_H5_FALLBACK, RCAAgentV21(Model({}, {"status": "ABSTAIN"})))
        assert report.status == "TECHNICAL_FAILURE"
    finally: prepared.store.close()


def test_v21_tool_then_valid_report_remains_supported(tmp_path):
    class ToolModel(Model):
        def __init__(self): super().__init__(None); self.round = 0
        def generate(self, request):
            self.requests.append(dict(request)); self.round += 1
            if self.round == 1:
                return {"tool_calls": [{"name": "get_incident_summary", "arguments": {"incident_id": request["incident"]["incident_id"]}}]}
            return {"report": _abstain(self.requests[0])["report"]}
    prepared = _prepared(tmp_path); model = ToolModel()
    try:
        report, trace = RCAAgentV21(model).investigate(_tools(prepared))
        assert report.status == "INSUFFICIENT_EVIDENCE"
        assert trace["tool_calls"][0]["tool_name"] == "get_incident_summary"
    finally: prepared.store.close()
