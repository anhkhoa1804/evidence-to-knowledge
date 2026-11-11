import json

import pytest

from cdoi.provider_output import ProviderOutputError, normalize_openai_turn


def _response(content, *, tool_calls=None):
    return {"model": "Qwen3.8-27B", "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content, "tool_calls": tool_calls or []}}]}


@pytest.mark.parametrize(("content", "path"), [
    ('{"status":"INSUFFICIENT_EVIDENCE"}', "DIRECT_JSON_OBJECT"),
    (json.dumps(json.dumps({"status": "INSUFFICIENT_EVIDENCE"})), "JSON_STRING_OBJECT"),
    ('```json\n{"status":"INSUFFICIENT_EVIDENCE"}\n```', "JSON_FENCED_OBJECT"),
    ([{"type": "text", "text": '{"status":"INSUFFICIENT_EVIDENCE"}'}], "CONTENT_BLOCK_DIRECT_JSON_OBJECT"),
])
def test_normalizes_only_explicit_unambiguous_object_forms(content, path):
    turn = normalize_openai_turn(_response(content), "vllm/Qwen3.8-27B")
    assert turn.normalization_path == path
    assert json.loads(turn.content) == {"status": "INSUFFICIENT_EVIDENCE"}


@pytest.mark.parametrize("content", [
    'before {"a":1} after',
    '```json\n{"a":1}\n```\n```json\n{"b":2}\n```',
    [{"type": "text", "text": "one"}, {"type": "text", "text": "two"}],
])
def test_rejects_ambiguous_or_unbounded_content(content):
    with pytest.raises(ProviderOutputError) as error:
        normalize_openai_turn(_response(content), "model")
    assert error.value.code in {"QWEN_AMBIGUOUS_OUTPUT", "QWEN_CONTENT_NORMALIZATION_FAILURE"}


def test_preserves_tool_turn_without_hidden_reasoning_fields():
    calls = [{"id": "call-1", "type": "function", "function": {"name": "get_candidates", "arguments": "{}"}}]
    turn = normalize_openai_turn(_response(None, tool_calls=calls), "model")
    assert turn.content is None and turn.tool_calls == tuple(calls)
    assert "reasoning" not in json.dumps(turn.safe_metadata())


def test_tool_call_normalization_drops_provider_extras():
    calls = [{"id": "call-1", "type": "function", "reasoning_details": "hidden",
              "function": {"name": "get_candidates", "arguments": "{}", "reasoning": "hidden"}}]
    turn = normalize_openai_turn(_response(None, tool_calls=calls), "model")
    assert turn.tool_calls == ({"id": "call-1", "type": "function", "function": {"name": "get_candidates", "arguments": "{}"}},)
    assert "hidden" not in json.dumps(turn.tool_calls)


def test_live_observed_length_with_empty_content_is_a_precise_failure():
    response = {"model": "Qwen3.8-27B", "choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": None}}]}
    with pytest.raises(ProviderOutputError) as error:
        normalize_openai_turn(response, "vllm/Qwen3.8-27B")
    assert error.value.code == "QWEN_OUTPUT_TRUNCATED"
    assert error.value.path == "choices[0].finish_reason"
