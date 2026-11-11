from __future__ import annotations

import json

import pytest
import requests

from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model


class Response:
    def __init__(self, body, status=200): self.body, self.status_code = body, status
    def json(self): return self.body


def _config(monkeypatch, **changes):
    monkeypatch.setenv("QWEN_API_KEY", "test-key-not-persisted")
    values = {"base_url": "https://example.invalid/v1", "api_key_env": "QWEN_API_KEY", "model": "vllm/Qwen3.8-27B", "max_retries": 1}
    values.update(changes); return QwenRCAConfig(**values)


def test_v2_sends_profiles_and_explicit_output_budget_without_reasoning(monkeypatch):
    calls = []
    report = {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None, "alternative_hypotheses": [],
              "supporting_evidence_ids": [], "contradictory_evidence_ids": [], "reasoning_summary": "x", "limitations": ["x"],
              "abstention_reason": "x", "investigated_candidate_ids": [], "comparison_completed": True,
              "missing_or_conflicting_evidence": ["x"]}
    def requester(*args, **kwargs):
        calls.append(kwargs); return Response({"model": "Qwen3.8-27B", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(report), "reasoning": "hidden"}}]})
    model = QwenRCAAgentV2Model(_config(monkeypatch), requester=requester)
    assert model.generate({"incident": {"incident_id": "synthetic"}, "candidates": {"items": []},
                           "preloaded_candidate_profiles": [{"candidate_id": "c"}], "h1_comparison": {},
                           "candidate_source": "H1_THEN_H5_FALLBACK"})["report"]["status"] == "INSUFFICIENT_EVIDENCE"
    request_payload = json.loads(calls[0]["json"]["messages"][1]["content"])
    assert request_payload["preloaded_candidate_profiles"] == [{"candidate_id": "c"}]
    assert calls[0]["json"]["max_tokens"] == 512
    assert "hidden" not in json.dumps(model._messages)
    assert model.records[0]["finish_reason"] == "stop"


def test_v2_transport_is_bounded_and_safe(monkeypatch):
    attempts = []
    def timeout(*args, **kwargs): attempts.append(1); raise requests.Timeout()
    model = QwenRCAAgentV2Model(_config(monkeypatch, max_retries=1), requester=timeout)
    with pytest.raises(QwenRCAError, match="QWEN_TRANSPORT_FAILURE"):
        model.generate({"incident": {}, "candidates": {}, "preloaded_candidate_profiles": [], "h1_comparison": {}, "candidate_source": "H1_THEN_H5_FALLBACK"})
    assert len(attempts) == 2
    assert model.last_transport_diagnostic["attempt_count"] == 2
    assert "test-key" not in json.dumps(model.last_transport_diagnostic)


def test_v2_accepts_a_single_json_fence_but_rejects_ambiguous_content(monkeypatch):
    report = {"status": "INSUFFICIENT_EVIDENCE"}
    def fenced(*args, **kwargs):
        return Response({"choices": [{"message": {"content": "```json\n" + json.dumps(report) + "\n```"}}]})
    model = QwenRCAAgentV2Model(_config(monkeypatch), requester=fenced)
    assert model.generate({"incident": {}, "candidates": {}, "preloaded_candidate_profiles": [], "h1_comparison": {}, "candidate_source": "H1_THEN_H5_FALLBACK"})["report"] == report
    assert model.last_contract_diagnostic["normalization_path"] == "JSON_FENCED_OBJECT"
    def ambiguous(*args, **kwargs):
        return Response({"choices": [{"message": {"content": 'before {"a":1} after'}}]})
    model = QwenRCAAgentV2Model(_config(monkeypatch), requester=ambiguous)
    with pytest.raises(QwenRCAError, match="QWEN_AMBIGUOUS_OUTPUT"):
        model.generate({"incident": {}, "candidates": {}, "preloaded_candidate_profiles": [], "h1_comparison": {}, "candidate_source": "H1_THEN_H5_FALLBACK"})


def test_live_observed_truncated_empty_turn_is_precisely_classified(monkeypatch):
    def truncated(*args, **kwargs):
        return Response({"model": "Qwen3.8-27B", "choices": [{"finish_reason": "length", "message": {"content": None, "reasoning": "hidden"}}]})
    model = QwenRCAAgentV2Model(_config(monkeypatch), requester=truncated)
    with pytest.raises(QwenRCAError, match="QWEN_OUTPUT_TRUNCATED"):
        model.generate({"incident": {}, "candidates": {}, "preloaded_candidate_profiles": [],
                        "h1_comparison": {}, "candidate_source": "H1_THEN_H5_FALLBACK"})
    assert model.last_contract_diagnostic["finish_reason"] == "length"
    assert model.last_contract_diagnostic["message_content_present"] is False
    assert "hidden" not in json.dumps(model.last_contract_diagnostic)


def test_live_tool_shape_is_sanitized_before_serial_continuation(monkeypatch):
    def tool_response(*args, **kwargs):
        return Response({"model": "Qwen3.8-27B", "choices": [{"finish_reason": "tool_calls", "message": {
            "content": None, "reasoning_details": "hidden",
            "tool_calls": [{"id": "call-1", "type": "function", "function": {
                "name": "get_incident_summary", "arguments": '{"incident_id":"inc-001"}', "reasoning": "hidden"}}]}}]})
    model = QwenRCAAgentV2Model(_config(monkeypatch), requester=tool_response)
    result = model.generate({"incident": {}, "candidates": {}, "preloaded_candidate_profiles": [],
                             "h1_comparison": {}, "candidate_source": "H1_THEN_H5_FALLBACK"})
    assert result["tool_calls"] == [{"name": "get_incident_summary", "arguments": {"incident_id": "inc-001"}}]
    assert "hidden" not in json.dumps(model._messages)
