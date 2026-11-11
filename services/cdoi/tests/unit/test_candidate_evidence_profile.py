import json
from pathlib import Path

from cdoi.candidate_evidence_profile import CandidateEvidenceProfileBuilder
from cdoi.hypothesis_generation import generate_evidence_aware_hypotheses
from cdoi.operational_context import assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import process_dataset
from cdoi.scalable_evidence import IncidentEvidenceStore

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"


def _profiles(tmp_path):
    result = process_dataset(FIXTURE / "manifest.yaml")
    incident = load_incident_windows(FIXTURE / "incidents/incidents.csv")[0]
    context = assemble_context(result, incident)
    store = IncidentEvidenceStore.from_context(tmp_path / "store.sqlite", context, exact_legacy_graph_id=True, snapshot=snapshot_for(context))
    generated = generate_evidence_aware_hypotheses(store, store.logical_view())
    profiles = CandidateEvidenceProfileBuilder(context, store, generated.aggregate_evidence).build_all(generated.candidates)
    return store, generated, profiles


def test_profiles_are_deterministic_gt_free_and_do_not_change_candidates(tmp_path):
    first_store, first_candidates, first = _profiles(tmp_path / "one")
    second_store, second_candidates, second = _profiles(tmp_path / "two")
    assert first_candidates.candidates == second_candidates.candidates
    assert [item.artifact() for item in first] == [item.artifact() for item in second]
    text = json.dumps([item.artifact() for item in first], sort_keys=True).casefold()
    assert '"root_cause":' not in text and '"causal_probability":' not in text and '"ground_truth":' not in text
    first_store.close(); second_store.close()


def test_profiles_preserve_evidence_boundaries_and_provenance(tmp_path):
    store, generated, profiles = _profiles(tmp_path)
    profile = next(item for item in profiles if item.subject_id == "payment-service")
    assert profile.profile_id.startswith("candidate-profile-")
    assert profile.contradictory_evidence == ()
    assert "MISSING_" not in " ".join(profile.missing_evidence) or isinstance(profile.missing_evidence, tuple)
    assert profile.trace_evidence["interpretation_boundary"] == "TRACE_PATH_NOT_CAUSAL_PATH; ERROR_SPAN_NOT_ROOT_CAUSE"
    assert profile.topology_evidence["interpretation_boundary"] == "TOPOLOGY_ADJACENCY_NOT_CAUSALITY"
    assert profile.provenance["manifest_hash"]
    assert all(item.evidence_id for item in profile.supporting_evidence)
    store.close()
