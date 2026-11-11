import json
import runpy
from pathlib import Path

from cdoi.incident_evidence_graph import build_incident_evidence_graph, generate_cause_candidates
from cdoi.operational_context import assemble_context, snapshot_for
from cdoi.raw_preprocessing import process_dataset
from cdoi.rcaeval_evaluation import RCAEvalGroundTruth, deterministic_pilot, load_case_index
from cdoi.scalable_evidence import IncidentEvidenceStore, generate_frozen_candidates_from_store


ROOT = Path(__file__).resolve().parents[2]
R2 = runpy.run_path(str(ROOT / "tools/run_v3_phase2_10e_r2.py"))


def test_r2_frozen_pilot_and_holdout_membership_match_the_original_split():
    cases, truth = load_case_index(ROOT / "data/benchmarks/external/rcaeval/cases.parquet")
    split = json.loads((ROOT / "experiments/archive/v3_phase2_10e_rcaeval/CASE_SPLIT.json").read_text(encoding="utf-8"))
    assert list(deterministic_pilot(cases, truth)) == split["pilot_case_ids"]
    assert len(split["pilot_case_ids"]) == 12
    assert len(split["held_out_re2ob_case_ids"]) == 78


def test_r2_default_scalable_path_is_equivalent_and_ablations_are_explicit(tmp_path: Path):
    fixture = ROOT / "tests/fixtures/preprocessing_demo"
    processed = process_dataset(fixture / "manifest.yaml")
    incident = __import__("cdoi.operational_context", fromlist=["load_incident_windows"]).load_incident_windows(fixture / "incidents/incidents.csv", "incidents/incidents.csv")[0]
    context = assemble_context(processed, incident); snapshot = snapshot_for(context)
    store = IncidentEvidenceStore.from_context(tmp_path / "store.sqlite", context, exact_legacy_graph_id=True, snapshot=snapshot)
    assert [item.artifact() for item in generate_frozen_candidates_from_store(store, store.logical_view(snapshot.snapshot_id))] == [item.artifact() for item in generate_cause_candidates(build_incident_evidence_graph(snapshot))]
    no_metrics = generate_frozen_candidates_from_store(store, store.logical_view(), include_metrics=False)
    assert len(no_metrics) == len(generate_frozen_candidates_from_store(store, store.logical_view()))
    assert all(not item.context_evidence_ids for item in no_metrics)
    store.close()


def test_r2_scores_only_a_precomputed_candidate_set_and_keeps_technical_states_out_of_misses():
    candidates = ()
    truth = RCAEvalGroundTruth("case-1", "SERVICE", "alpha", "CPU")
    scored = R2["evaluate"]("case-1", truth, candidates, 2, "graph-1")
    assert scored["status"] == "EVALUATED_GT_MISSED"
    headline = R2["summarize"]([scored, {"status": "TECHNICAL_UNAVAILABLE", "covered": None}])
    assert headline["evaluated_count"] == 1
    assert headline["missed_count"] == 1


def test_r2_zero_candidate_taxonomy_and_resource_counts_are_deterministic(tmp_path: Path):
    result = {"covered": False, "candidate_count": 0}
    inventory = {"service_resolved": True, "error_log_event_count": 0, "error_trace_span_count": 0, "metric_observation_count": 1, "partial_trace_unresolved_parent_count": 0}
    assert R2["miss_taxonomy"](result, inventory) == ["ZERO_CANDIDATES", "NO_ELIGIBLE_RULE_TRIGGERED", "ERROR_EVENT_NOT_OBSERVED_ON_GT_SERVICE", "ERROR_TRACE_NOT_OBSERVED_ON_GT_SERVICE", "METRIC_SIGNAL_PRESENT_BUT_CONTEXT_ONLY"]
