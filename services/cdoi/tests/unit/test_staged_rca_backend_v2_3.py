import inspect
import json
from dataclasses import dataclass
from types import MappingProxyType

import pytest

from cdoi.qwen_rca import QwenRCAConfig, QwenRCAError
from cdoi.rca_investigation import ReadOnlyRCATools, _json
from cdoi.staged_rca_backend_v2_3 import StagedRCAAgentV23Model, TOOL_ARGUMENTS, validate_tool_action


@dataclass(frozen=True)
class ImmutableEvidence:
    attributes: object


def test_read_only_serialization_handles_nested_mapping_proxy():
    value = ImmutableEvidence(MappingProxyType({"nested": MappingProxyType({"x": 1})}))
    assert _json(value) == {"attributes": {"nested": {"x": 1}}}


def test_tool_signatures_match_dispatcher_without_hidden_aliases():
    for name, (required, optional) in TOOL_ARGUMENTS.items():
        signature = inspect.signature(getattr(ReadOnlyRCATools, name))
        actual = {key for key in signature.parameters if key != "self"}
        assert actual == (set(required) | set(optional)) - {"fallback_reason"}
        assert {key for key, value in signature.parameters.items()
                if key != "self" and value.default is inspect.Parameter.empty} == set(required) - {"fallback_reason"}


@pytest.mark.parametrize("name,args", [
    ("get_metric_evidence", {"incident_id": "inc-1", "aggregate_evidence_id": "x"}),
    ("get_event_evidence", {"incident_id": "inc-1", "service_id": "svc", "evidence_ids": []}),
    ("get_candidate_profile", {"candidate_id": "c1"}),
    ("get_expanded_candidates", {"incident_id": "inc-1"}),
])
def test_unsupported_or_missing_tool_arguments_fail_closed(name, args):
    with pytest.raises(QwenRCAError, match="V23_TOOL_ARGUMENTS_INVALID"):
        validate_tool_action(name, args)


def test_one_bounded_tool_argument_repair():
    model = StagedRCAAgentV23Model(QwenRCAConfig())
    turns = iter([
        {"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {"evidence_ids": ["x"]}},
        {"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {"incident_id": "inc-1"}},
    ])
    model.complete = lambda *args, **kwargs: {"message": {"content": json.dumps(next(turns))},
                                             "latency_ms": 1, "retry_count": 0,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}}
    result = model.generate({"incident": {"incident_id": "inc-1"}, "candidates": {"items": []}})
    assert result == {"tool_calls": [{"name": "get_incident_summary", "arguments": {"incident_id": "inc-1"}}]}
    assert model.tool_action_repairs == 1


def test_failed_tool_argument_repair_does_not_execute():
    model = StagedRCAAgentV23Model(QwenRCAConfig())
    turns = iter([
        {"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {"evidence_ids": ["x"]}},
        {"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {"evidence_ids": ["x"]}},
    ])
    model.complete = lambda *args, **kwargs: {"message": {"content": json.dumps(next(turns))},
                                             "latency_ms": 1, "retry_count": 0,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}}
    with pytest.raises(QwenRCAError, match="V23_TOOL_ARGUMENTS_INVALID"):
        model.generate({"incident": {"incident_id": "inc-1"}, "candidates": {"items": []}})
    assert model.tool_action_repairs == 1


def test_first_tool_repair_cannot_switch_away_from_incident_summary():
    model = StagedRCAAgentV23Model(QwenRCAConfig())
    turns = iter([
        {"action": "TOOL", "tool_name": "get_incident_summary", "arguments": {"evidence_ids": ["x"]}},
        {"action": "TOOL", "tool_name": "get_metric_evidence", "arguments": {"incident_id": "inc-1", "service_id": "svc"}},
    ])
    model.complete = lambda *args, **kwargs: {"message": {"content": json.dumps(next(turns))},
                                             "latency_ms": 1, "retry_count": 0,
                                             "usage": {"input_tokens": 1, "output_tokens": 1}}
    with pytest.raises(QwenRCAError, match="V23_FIRST_TOOL_MUST_BE_INCIDENT_SUMMARY"):
        model.generate({"incident": {"incident_id": "inc-1"}, "candidates": {"items": []}})
