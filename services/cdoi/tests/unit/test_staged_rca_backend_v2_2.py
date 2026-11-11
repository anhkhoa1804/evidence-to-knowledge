import json

import pytest

from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.staged_rca_backend_v2_2 import StagedRCAAgentV22Model


def _model(turns):
    model = StagedRCAAgentV22Model(QwenRCAConfig())
    pending = iter(turns)
    model.complete = lambda *args, **kwargs: {"message": {"content": json.dumps(next(pending))},
                                             "latency_ms": 1, "retry_count": 0,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}}
    return model


def test_staged_tool_then_report_is_serial_and_read_only():
    report = {"status": "INSUFFICIENT_EVIDENCE"}
    model = _model([{"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {"incident_id": "inc-1"}},
                    {"action": "REPORT", "report": report}])
    first = model.generate({"incident": {"incident_id": "inc-1"}, "candidates": {"items": []}})
    assert first == {"tool_calls": [{"name": "get_incident_summary", "arguments": {"incident_id": "inc-1"}}]}
    assert model.generate({"prior_tool_results": [{"tool": "get_incident_summary", "result": {"items": []}}]}) == {"report": report}
    assert [item["action"] for item in model.action_history] == ["TOOL", "REPORT"]


def test_first_turn_report_cannot_skip_required_read_only_summary():
    with pytest.raises(QwenRCAError, match="V22_FIRST_TURN_SUMMARY_REQUIRED"):
        _model([{"action": "REPORT", "report": {"status": "INSUFFICIENT_EVIDENCE"}}]).generate(
            {"incident": {"incident_id": "inc-1"}, "candidates": {"items": []}})


def test_staged_repair_returns_report_without_action_wrapper():
    model = _model([])
    calls = []
    def complete(messages, **kwargs):
        calls.append((messages, kwargs))
        return {"message": {"content": json.dumps({"status": "INSUFFICIENT_EVIDENCE"})}}
    model.complete = complete
    repaired = model.repair_output({"status": "ABSTAIN"}, "RCA_STATUS_INVALID",
                                   {"preloaded_candidate_profiles": [{"candidate_id": "c1"}],
                                    "report_schema": "RCAReport"})
    assert repaired == {"report": {"status": "INSUFFICIENT_EVIDENCE"}}
    assert len(calls) == 1
    assert calls[0][1]["response_format"] == {"type": "json_object"}


def test_native_tool_envelope_in_staged_mode_fails_closed():
    model = _model([])
    model.complete = lambda *args, **kwargs: {"message": {"content": "{}", "tool_calls": [{"id": "x"}]}}
    with pytest.raises(QwenRCAError, match="V22_UNEXPECTED_NATIVE_TOOL_CALL"):
        model.generate({"incident": {"incident_id": "inc-1"}, "candidates": {"items": []}})


@pytest.mark.parametrize("action", [
    {}, {"action": "ABSTAIN"},
    {"action": "TOOL", "tool_name": "delete_kg", "arguments": {}},
    {"action": "REPORT", "report": "not-object"},
    {"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {}, "extra": 1},
])
def test_staged_actions_fail_closed(action):
    with pytest.raises(QwenRCAError):
        _model([action]).generate({"incident": {}, "candidates": {"items": []}})
