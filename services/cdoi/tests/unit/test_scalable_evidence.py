from pathlib import Path

from cdoi.incident_evidence_graph import build_incident_evidence_graph, generate_cause_candidates
from cdoi.operational_context import assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import process_dataset
from cdoi.scalable_evidence import IncidentEvidenceStore, ResourceConfiguration, generate_frozen_candidates_from_store

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"


def _context():
    result = process_dataset(FIXTURE / "manifest.yaml")
    incident = load_incident_windows(FIXTURE / "incidents/incidents.csv", "incidents/incidents.csv")[0]
    context = assemble_context(result, incident)
    return context, snapshot_for(context)


def test_store_is_deterministic_complete_and_resolves_trace_provenance(tmp_path: Path):
    context, snapshot = _context()
    one = IncidentEvidenceStore.from_context(tmp_path / "one.sqlite", context, resource_configuration=ResourceConfiguration(1, 2), exact_legacy_graph_id=True, snapshot=snapshot)
    two = IncidentEvidenceStore.from_context(tmp_path / "two.sqlite", context, resource_configuration=ResourceConfiguration(100, 100), exact_legacy_graph_id=True, snapshot=snapshot)
    assert one.trace_count() == two.trace_count() == len(context.traces)
    assert list(one.trace_spans_for_entities(context.expanded_entity_ids)) == list(two.trace_spans_for_entities(context.expanded_entity_ids))
    first = context.traces[0]
    assert one.trace_provenance(first.evidence_id)["raw_evidence_id"] == first.evidence_id
    one.close(); two.close()


def test_indexed_candidate_path_is_exactly_equivalent_to_frozen_exhaustive_small_fixture(tmp_path: Path):
    context, snapshot = _context()
    legacy_graph = build_incident_evidence_graph(snapshot)
    legacy = generate_cause_candidates(legacy_graph)
    store = IncidentEvidenceStore.from_context(tmp_path / "store.sqlite", context, exact_legacy_graph_id=True, snapshot=snapshot)
    scalable = generate_frozen_candidates_from_store(store, store.logical_view(snapshot.snapshot_id))
    assert [item.artifact() for item in scalable] == [item.artifact() for item in legacy]
    store.close()


def test_store_does_not_need_to_materialize_all_trace_rows_for_error_query(tmp_path: Path):
    context, snapshot = _context()
    store = IncidentEvidenceStore.from_context(tmp_path / "store.sqlite", context, resource_configuration=ResourceConfiguration(2, 1), snapshot=snapshot)
    errors = store.trace_error_evidence_for_entities(context.expanded_entity_ids)
    assert set(errors) == {"database-service", "payment-service"}
    assert sum(len(value) for value in errors.values()) == 3
    assert store.logical_view().trace_count == len(context.traces)
    store.close()


def test_index_input_order_does_not_change_logical_view_or_candidate_output(tmp_path: Path):
    context, snapshot = _context()
    forward = IncidentEvidenceStore(tmp_path / "forward.sqlite", context)
    reverse = IncidentEvidenceStore(tmp_path / "reverse.sqlite", context)
    forward.add_trace_spans(context.traces)
    reverse.add_trace_spans(reversed(context.traces))
    assert forward.logical_view().graph_id == reverse.logical_view().graph_id
    assert generate_frozen_candidates_from_store(forward, forward.logical_view()) == generate_frozen_candidates_from_store(reverse, reverse.logical_view())
    forward.close(); reverse.close()
