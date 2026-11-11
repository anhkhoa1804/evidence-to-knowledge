import json
import pytest

from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.rca_agent_v2_4 import RCAAgentV24, validate_exposed_report
from cdoi.rca_investigation import RCAHypothesis, RCAReport
from cdoi.staged_rca_backend_v2_3 import TOOL_ARGUMENTS
from cdoi.staged_rca_backend_v2_4 import (
    StagedRCAAgentV24Model, canonical_allowed_ids, collect_ids, parse_action,
    tool_call_signature, validate_tool_references,
)

C1 = "candidate-1"
C2 = "candidate-2"
E1 = "evidence-1"
E2 = "evidence-2"


def report(*, status="RCA_HYPOTHESIS", candidate=C1, evidence=E1):
    hypothesis = RCAHypothesis(candidate, "A bounded non-causal hypothesis", (evidence,),
                               ("Evidence remains incomplete",), "LOW")
    return RCAReport("incident-opaque", status, hypothesis, (), (evidence,), (),
                     "A grounded report summary", ("Not causal proof",), None, 0, {})


def test_allowed_id_serialization_is_sorted_and_order_independent():
    left = canonical_allowed_ids({C2, C1}, {E2, E1})
    right = canonical_allowed_ids({C1, C2}, {E1, E2})
    assert left == right == {"candidate_ids": [C1, C2], "evidence_ids": [E1, E2]}


def test_collect_ids_reads_singular_and_list_ids_without_coercion():
    value = {"candidate_id": C1, "supporting_evidence_ids": [E2, 5, E1]}
    assert collect_ids(value, frozenset({"candidate_id", "supporting_evidence_ids"})) == {C1, E1, E2}


def test_report_with_exposed_candidate_scoped_ids_is_accepted():
    validate_exposed_report(report(), {C1}, {E1}, {C1: {E1}})


@pytest.mark.parametrize("bad", [
    report(candidate="candidate-unknown"),
    report(evidence="fabricated-id-999"),
    report(evidence="bad id / malformed"),
    report(evidence="phase211-trace-stale-stage"),
    report(evidence="valid-looking-but-unexposed"),
    report(evidence=E2),
])
def test_unknown_or_wrong_scope_ids_are_rejected(bad):
    with pytest.raises(ValueError):
        validate_exposed_report(bad, {C1}, {E1, E2}, {C1: {E1}})


def test_malformed_json_action_is_rejected_without_normalization():
    with pytest.raises(QwenRCAError, match="V24_ACTION_JSON_INVALID"):
        parse_action('{"action":"REPORT",')


def test_tool_signature_is_deterministic_and_argument_sensitive():
    assert tool_call_signature("get_evidence_by_id", {"evidence_id": E1}) == tool_call_signature(
        "get_evidence_by_id", {"evidence_id": E1})
    assert tool_call_signature("get_evidence_by_id", {"evidence_id": E1}) != tool_call_signature(
        "get_evidence_by_id", {"evidence_id": E2})


def test_duplicate_valid_citations_are_not_silently_removed():
    duplicate = RCAReport("incident-opaque", "RCA_HYPOTHESIS",
                          RCAHypothesis(C1, "claim", (E1, E1), ("limitation",), "LOW"), (),
                          (E1, E1), (), "summary", ("limitation",), None, 0, {})
    validate_exposed_report(duplicate, {C1}, {E1}, {C1: {E1}})
    assert duplicate.primary_hypothesis.supporting_evidence_ids == (E1, E1)
    assert duplicate.supporting_evidence_ids == (E1, E1)


@pytest.mark.parametrize("name,args", [
    ("get_candidate_profile", {"candidate_id": C1}),
    ("get_metric_evidence", {"incident_id": "i", "service_id": 1}),
    ("missing_tool", {"incident_id": "i"}),
])
def test_invalid_tool_name_or_arguments_reject(name, args):
    from cdoi.staged_rca_backend_v2_3 import validate_tool_action
    with pytest.raises(QwenRCAError):
        validate_tool_action(name, args)


@pytest.mark.parametrize("name,args", [
    ("get_candidate_profile", {"incident_id": "i", "candidate_id": "stale-candidate"}),
    ("get_evidence_by_id", {"evidence_id": "stale-evidence"}),
])
def test_stale_tool_references_fail_before_dispatch(name, args):
    with pytest.raises(QwenRCAError, match="V24_TOOL_UNKNOWN_"):
        validate_tool_references(name, args, {C1}, {E1})


def test_every_v23_tool_signature_remains_the_v24_allowlist():
    assert set(TOOL_ARGUMENTS) == {
        "get_incident_summary", "get_candidates", "get_expanded_candidates", "get_candidate_profile",
        "get_metric_evidence", "get_trace_evidence", "get_event_evidence", "get_change_evidence",
        "get_topology_context", "get_evidence_by_id",
    }


def test_report_repair_receives_exact_sorted_ids_and_staged_tool_history():
    model = StagedRCAAgentV24Model(QwenRCAConfig())
    model._staged_messages = [{"role": "assistant", "content": "prior validated tool action"}]
    model.exposed_candidate_ids = {C1}
    model.exposed_evidence_ids = {E1, E2}
    model.evidence_by_candidate = {C1: {E1}}
    captured = {}

    def complete(messages, **kwargs):
        captured["messages"] = messages
        prompt = json.loads(messages[-1]["content"])
        captured["prompt"] = prompt
        valid = {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": C1, "statement": "bounded hypothesis", "supporting_evidence_ids": [E1],
            "limitations": ["uncertainty"], "model_self_assessment": "LOW"},
            "alternative_hypotheses": [], "supporting_evidence_ids": [E1],
            "contradictory_evidence_ids": [], "reasoning_summary": "summary", "limitations": ["uncertainty"]}
        return {"message": {"content": json.dumps(valid)}, "latency_ms": 1, "retry_count": 0, "usage": {}}

    model.complete = complete
    result = model.repair_output({"status": "RCA_HYPOTHESIS", "primary_hypothesis": {}},
                                 "RCA_REPORT_UNKNOWN_EVIDENCE", {
                                     "preloaded_candidate_profiles": [{"candidate_id": C1, "supporting_evidence_ids": [E1]}]})
    assert result["report"]["status"] == "RCA_HYPOTHESIS"
    assert captured["prompt"]["validation_error"] == "RCA_REPORT_UNKNOWN_EVIDENCE"
    assert captured["prompt"]["allowed_ids"] == {"candidate_ids": [C1], "evidence_ids": [E1, E2]}
    assert captured["messages"][0]["content"] == "prior validated tool action"
    assert captured["prompt"]["preserve_original_status"] == "RCA_HYPOTHESIS"


def test_missing_status_can_be_repaired_but_no_status_default_is_applied():
    model = StagedRCAAgentV24Model(QwenRCAConfig())
    model.exposed_candidate_ids = {C1}
    model.exposed_evidence_ids = {E1}
    model.evidence_by_candidate = {C1: {E1}}
    captured = {}

    def complete(messages, **kwargs):
        captured["prompt"] = json.loads(messages[-1]["content"])
        return {"message": {"content": json.dumps({"status": "INSUFFICIENT_EVIDENCE"})},
                "latency_ms": 1, "retry_count": 0, "usage": {}}

    model.complete = complete
    raw = {"primary_hypothesis": None}
    repaired = model.repair_output(raw, "RCA_STATUS_REQUIRED", {})["report"]
    assert repaired["status"] == "INSUFFICIENT_EVIDENCE"
    assert captured["prompt"]["preserve_original_status"] is None
    assert raw == {"primary_hypothesis": None}


def test_budget_exhaustion_allows_one_report_correction_without_executing_ninth_tool(monkeypatch):
    model = StagedRCAAgentV24Model(QwenRCAConfig())
    model.action_history = [{"action": "TOOL"} for _ in range(8)]
    model._staged_messages = [{"role": "assistant", "content": "eight tool calls completed"}]
    valid = {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None}
    model.complete = lambda *a, **k: {"message": {"content": json.dumps({"action": "REPORT", "report": valid})},
                                     "latency_ms": 2, "retry_count": 0, "usage": {}}
    def ninth_tool(self, request):
        self.action_history.append({"action": "TOOL"})
        return {"tool_calls": [{"name": "get_metric_evidence",
                                "arguments": {"incident_id": "i", "service_id": "s"}}]}

    monkeypatch.setattr("cdoi.staged_rca_backend_v2_4.StagedRCAAgentV23Model.generate", ninth_tool)
    result = model.generate({"prior_tool_results": []})
    assert result == {"report": valid}
    assert model.tool_action_repairs == 1
    assert sum(a.get("action") == "TOOL" for a in model.action_history) == 9  # ninth provider action was rejected, never dispatched


def test_duplicate_tool_action_gets_one_bounded_correction(monkeypatch):
    model = StagedRCAAgentV24Model(QwenRCAConfig())
    original = {"name": "get_incident_summary", "arguments": {"incident_id": "incident-opaque"}}
    signature = tool_call_signature(**original)
    model.tool_call_signatures.add(signature)
    monkeypatch.setattr("cdoi.staged_rca_backend_v2_4.StagedRCAAgentV23Model.generate",
                        lambda self, request: {"tool_calls": [original]})
    model.complete = lambda *a, **k: {"message": {"content": json.dumps({
        "action": "REPORT", "report": {"status": "INSUFFICIENT_EVIDENCE"}})},
        "latency_ms": 1, "retry_count": 0, "usage": {}}
    result = model.generate({"prior_tool_results": []})
    assert result["report"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert model.tool_action_repairs == 1


def test_repair_exhaustion_fails_closed():
    model = StagedRCAAgentV24Model(QwenRCAConfig())
    model.report_repair_attempts = 1
    with pytest.raises(QwenRCAError, match="V24_REPORT_REPAIR_EXHAUSTED"):
        model.repair_output({}, "RCA_STATUS_REQUIRED", {})


def test_report_status_preservation_is_enforced_by_agent_repair():
    model = StagedRCAAgentV24Model(QwenRCAConfig())
    agent = RCAAgentV24(model)
    model.repair_output = lambda *a, **k: {"report": {"status": "INSUFFICIENT_EVIDENCE"}}
    with pytest.raises(ValueError, match="V24_REPAIR_STATUS_CHANGED"):
        agent._repair({"status": "RCA_HYPOTHESIS"}, ValueError("RCA_REPORT_UNKNOWN_EVIDENCE"), {})
