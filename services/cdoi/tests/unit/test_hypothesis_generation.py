from dataclasses import replace
import inspect
from pathlib import Path
from types import MappingProxyType

from cdoi.hypothesis_generation import (
    HypothesisConfiguration,
    METRIC_LEVEL_SHIFT_RULE,
    TOPOLOGY_ADJACENCY_RULE,
    TRACE_VOLUME_SHIFT_RULE,
    generate_evidence_aware_hypotheses,
)
from cdoi.operational_context import TopologyScope, assemble_context
from cdoi.raw_preprocessing import NormalizedRelationEvidence
from cdoi.rcaeval_evaluation import RCAEvalCase, adapt_case_rows
from cdoi.scalable_evidence import IncidentEvidenceStore


def _adapted(*, degraded: bool = True, traces=(), error_trace: bool = False):
    case = RCAEvalCase("opaque-case", "RE2-OB", "ob", 1000)
    metrics = [{"time": timestamp, "alpha_cpu": 1.0, "beta_cpu": 1.0} for timestamp in range(700, 760)]
    metrics += [{"time": timestamp, "alpha_cpu": 3.0 if degraded else 1.0, "beta_cpu": 1.0} for timestamp in range(1000, 1060)]
    rows = list(traces)
    if error_trace:
        rows.append({"startTime": 1000, "serviceName": "alpha", "traceID": "error", "spanID": "error", "statusCode": 2, "duration": 1})
    return adapt_case_rows(case, metrics, (), rows)


def _result(tmp_path: Path, adapted, configuration: HypothesisConfiguration, **flags):
    context = assemble_context(adapted.preprocessing, adapted.incident, TopologyScope.DIRECT_ONLY)
    store = IncidentEvidenceStore.from_context(tmp_path / "store.sqlite", context)
    result = generate_evidence_aware_hypotheses(store, store.logical_view(), configuration=configuration, **flags)
    store.close()
    return result


def test_metric_level_shift_creates_unranked_hypothesis_without_error_evidence(tmp_path: Path):
    result = _result(tmp_path, _adapted(), HypothesisConfiguration(metric_minimum_observations=10))
    assert [item.subject_node_id for item in result.candidates] == ["entity:alpha"]
    assert result.candidates[0].generation_rules == (METRIC_LEVEL_SHIFT_RULE,)
    assert result.candidates[0].status == "CANDIDATE_UNEVALUATED"
    assert result.aggregate_evidence[0].attributes["relative_median_shift"] == 2.0


def test_metric_presence_without_persistent_shift_creates_no_hypothesis(tmp_path: Path):
    result = _result(tmp_path, _adapted(degraded=False), HypothesisConfiguration(metric_minimum_observations=10), include_trace=False)
    assert result.candidates == ()


def test_counter_and_unit_conflict_are_not_silently_interpreted_as_level_shift(tmp_path: Path):
    adapted = _adapted()
    counter = replace(adapted.preprocessing, metrics=tuple(replace(item, metric_kind="COUNTER") for item in adapted.preprocessing.metrics))
    assert _result(tmp_path / "counter", replace(adapted, preprocessing=counter), HypothesisConfiguration(metric_minimum_observations=10), include_trace=False).candidates == ()
    conflict = replace(adapted.preprocessing, metrics=tuple(replace(item, unit="bytes") if index % 2 else item for index, item in enumerate(adapted.preprocessing.metrics)))
    assert _result(tmp_path / "conflict", replace(adapted, preprocessing=conflict), HypothesisConfiguration(metric_minimum_observations=10), include_trace=False).candidates == ()


def test_trace_participation_shift_is_explicit_and_merges_with_metric_provenance(tmp_path: Path):
    traces = []
    for number in range(3):
        traces.append({"startTime": 700, "serviceName": "alpha", "traceID": f"before-{number}", "spanID": "s", "duration": 1})
    for number in range(9):
        traces.append({"startTime": 1000, "serviceName": "alpha", "traceID": f"after-{number}", "spanID": "s", "duration": 1})
    result = _result(tmp_path, _adapted(traces=traces), HypothesisConfiguration(metric_minimum_observations=10, trace_minimum_spans_per_partition=3))
    assert len(result.candidates) == 1
    assert set(result.candidates[0].generation_rules) == {METRIC_LEVEL_SHIFT_RULE, TRACE_VOLUME_SHIFT_RULE}
    assert len(result.aggregate_evidence) == 2


def test_bounded_topology_uses_declared_relation_without_recursive_expansion(tmp_path: Path):
    adapted = _adapted(degraded=False, error_trace=True)
    context = assemble_context(adapted.preprocessing, adapted.incident, TopologyScope.DIRECT_ONLY)
    relation = NormalizedRelationEvidence("relation-1", "test", "alpha", "DEPENDS_ON", "beta", "RESOLVED_EXACT_ID", MappingProxyType({}))
    store = IncidentEvidenceStore.from_context(tmp_path / "store.sqlite", replace(context, relations=(relation,)))
    result = generate_evidence_aware_hypotheses(store, store.logical_view(), include_metric=False, include_trace=False)
    store.close()
    beta = next(item for item in result.candidates if item.subject_node_id == "entity:beta")
    assert beta.generation_rules == (TOPOLOGY_ADJACENCY_RULE,)


def test_opaque_case_rename_does_not_change_subject_or_rule_selection(tmp_path: Path):
    one = _adapted(); two = replace(one, case=replace(one.case, case_id="different-opaque-id"))
    one_result = _result(tmp_path / "one", one, HypothesisConfiguration(metric_minimum_observations=10))
    two_result = _result(tmp_path / "two", two, HypothesisConfiguration(metric_minimum_observations=10))
    assert [(item.subject_node_id, item.generation_rules) for item in one_result.candidates] == [(item.subject_node_id, item.generation_rules) for item in two_result.candidates]


def test_generation_contract_has_no_ground_truth_input_and_artifact_is_deterministic(tmp_path: Path):
    adapted = _adapted()
    configuration = HypothesisConfiguration(metric_minimum_observations=10)
    one = _result(tmp_path / "one", adapted, configuration)
    two = _result(tmp_path / "two", adapted, configuration)
    assert "truth" not in inspect.signature(generate_evidence_aware_hypotheses).parameters
    assert one.artifact() == two.artifact()
    assert "root_cause" not in str(one.artifact()).casefold()
