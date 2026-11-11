import hashlib
from pathlib import Path

from cdoi.rcaeval_evaluation import (
    ORACLE_WINDOW,
    RCAEvalCase,
    adapt_case_rows,
    deterministic_pilot,
    evaluate_frozen_candidates,
    normalize_service_id,
    split_index_rows,
    trivial_baselines,
)


def _index_rows():
    rows = []
    for fault in ("cpu", "delay"):
        for service in ("alpha", "beta", "gamma"):
            rows.append({"case": f"re2ob_{service}_{fault}_1", "dataset": "RE2-OB", "system": "ob", "root_cause_service": service, "fault": fault, "inject_time": 1700000000, "has_logs": True, "has_traces": True})
    return rows


def _adapted():
    case, truth = split_index_rows([_index_rows()[0]])
    return adapt_case_rows(
        case[0],
        [{"time": 1700000000, "alpha_cpu": 1.0, "beta_cpu": 2.0}],
        [{"time": 1700000001, "service": "alpha", "message": "error", "level": "ERROR"}],
        [{"time": 1700000002, "serviceName": "alpha", "traceId": "t-1", "spanId": "s-1", "duration": 5, "status": "ERROR"}],
    ), truth[0]


def test_index_ground_truth_is_split_from_operational_case_metadata():
    cases, truth = split_index_rows(_index_rows())
    assert all(not hasattr(item, "root_cause_service") for item in cases)
    assert {item.subject_type for item in truth} == {"SERVICE"}
    assert deterministic_pilot(cases, truth) == deterministic_pilot(tuple(reversed(cases)), tuple(reversed(truth)))


def test_service_mapping_is_syntactic_and_unmapped_values_remain_unresolved():
    assert normalize_service_id("default/Payment.SVC.CLUSTER.LOCAL") == "payment"
    assert normalize_service_id(" ") is None


def test_adapter_does_not_accept_or_encode_ground_truth_and_marks_unspecified_metrics_honestly():
    adapted, truth = _adapted()
    assert adapted.window_mode == ORACLE_WINDOW
    assert all("root" not in str(item.provenance).casefold() for item in (*adapted.preprocessing.entities, *adapted.preprocessing.metrics, *adapted.preprocessing.events, *adapted.preprocessing.traces))
    assert {item.unit for item in adapted.preprocessing.metrics} == {"UNIT_UNSPECIFIED"}
    assert {item.metric_kind for item in adapted.preprocessing.metrics} == {"METRIC_KIND_UNSPECIFIED"}
    assert truth.root_cause_service == "alpha"


def test_external_case_reuses_frozen_graph_and_candidate_coverage_is_scored_after_generation():
    adapted, truth = _adapted()
    coverage = evaluate_frozen_candidates(adapted, truth)
    assert coverage.status == "GROUND_TRUTH_COVERED"
    assert coverage.candidate_count == 2
    assert coverage.eligible_service_count == 2
    assert coverage.reduction_ratio == 1.0
    assert set(coverage.generation_rules) == {"ERROR_EVENT_ON_INCIDENT_ENTITY_V1", "ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1"}


def test_ablation_and_trivial_baselines_are_deterministic_and_do_not_turn_technical_states_into_misses():
    adapted, truth = _adapted()
    first = evaluate_frozen_candidates(adapted, truth, remove_metrics=True)
    second = evaluate_frozen_candidates(adapted, truth, remove_metrics=True)
    assert first == second and first.covered is True
    assert evaluate_frozen_candidates(adapted, truth, remove_events=True).candidate_count == 1
    refs = trivial_baselines(adapted, truth)
    assert refs["ALL_SERVICES"].candidate_count == 2
    assert refs["ERROR_EVENT_SERVICES"].candidate_subject_ids == ("alpha",)
    assert refs["ERROR_TRACE_SERVICES"].candidate_subject_ids == ("alpha",)


def test_case_directory_name_is_opaque_to_adapter_and_phase210_artifact_remains_unchanged():
    adapted, truth = _adapted()
    coverage = evaluate_frozen_candidates(adapted, truth)
    assert all("cpu" not in rule.casefold() and "alpha" not in rule.casefold() for rule in coverage.generation_rules)
    root = Path(__file__).resolve().parents[2]
    assert hashlib.sha256((root / "src/cdoi/incident_evidence_graph.py").read_bytes()).hexdigest() == "3e4a8ac8e2b33b72f042a3730c8d31130220079a9420df635843588bfa981bd0"
    assert hashlib.sha256((root / "experiments/archive/v3_phase2_10/CAUSE_CANDIDATES.json").read_bytes()).hexdigest() == "7d51568eece5c4dcb5365869cf783e0f640e7493ef5185177a5348cc3e998f30"
