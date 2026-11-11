import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from cdoi.operational_context import (
    CONTEXT_SCHEMA_VERSION,
    IncidentWindow,
    OperationalContextError,
    TopologyScope,
    assemble_context,
    load_incident_windows,
    snapshot_for,
    write_snapshot,
)
from cdoi.raw_preprocessing import process_dataset


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"


def _result():
    return process_dataset(FIXTURE / "manifest.yaml")


def _incident():
    return load_incident_windows(FIXTURE / "incidents" / "incidents.csv", "incidents/incidents.csv")[0]


def test_incident_window_requires_ordered_timezone_aware_interval_and_normalizes_utc():
    window = IncidentWindow("utc", "2026-09-18T17:00:00+07:00", "2026-09-18T17:10:00+07:00", ("payment-service",))
    assert (window.start_time, window.end_time) == ("2026-09-18T10:00:00Z", "2026-09-18T10:10:00Z")
    with pytest.raises(OperationalContextError, match="INVALID_INCIDENT_INTERVAL"):
        IncidentWindow("bad", "2026-09-18T10:10:00Z", "2026-09-18T10:00:00Z", ("payment-service",))
    with pytest.raises(OperationalContextError, match="timezone"):
        IncidentWindow("naive", "2026-09-18T10:00:00", "2026-09-18T10:10:00Z", ("payment-service",))


def test_exact_identity_and_unresolved_incident_ids_are_explicit_without_fuzzy_matching():
    context = assemble_context(_result(), IncidentWindow("unknown", "2026-09-18T09:50:00Z", "2026-09-18T10:10:00Z", ("payment-service", "Payment Service")))
    assert context.direct_entity_ids == ("payment-service",)
    assert any(item.status == "UNRESOLVED_INCIDENT_ENTITY" and item.detail == "Payment Service" for item in context.unresolved)


def test_time_filter_is_inclusive_for_events_and_changes_and_excludes_outside_records():
    result = _result()
    context = assemble_context(result, IncidentWindow("boundary", "2026-09-18T10:00:00Z", "2026-09-18T10:00:00Z", ("payment-service",)), TopologyScope.DIRECT_ONLY)
    assert [item.event for item in context.events] == ["database connection timeout"]
    assert context.changes == ()
    change_boundary = assemble_context(result, IncidentWindow("change-boundary", "2026-09-18T09:55:00Z", "2026-09-18T09:55:00Z", ("payment-service",)))
    assert [item.change_id for item in change_boundary.changes] == ["chg-001"]


def test_topology_scope_is_bounded_directed_and_excludes_two_hop_entities():
    result = _result()
    direct = assemble_context(result, _incident(), TopologyScope.DIRECT_ONLY)
    one_hop = assemble_context(result, _incident(), TopologyScope.ONE_HOP)
    assert direct.expanded_entity_ids == ("payment-service",)
    assert one_hop.expanded_entity_ids == ("database-service", "order-service", "payment-service")
    assert {(row.source_external_id, row.relation, row.target_external_id) for row in one_hop.relations} == {
        ("order-service", "calls", "payment-service"),
        ("payment-service", "reads_from", "database-service"),
    }
    assert "unknown-service" not in one_hop.expanded_entity_ids


def test_snapshot_preserves_normalized_raw_source_provenance_and_selection_reason():
    snapshot = snapshot_for(assemble_context(_result(), _incident()))
    artifact = snapshot.artifact()
    payment = next(row for row in artifact["entities"] if row["external_id"] == "payment-service")
    assert payment["provenance"]["raw_evidence_id"].startswith("ev-")
    assert payment["provenance"]["source_file"] == "inventory/services.csv"
    assert any(row["selection_rule"] == "EVENT_IN_TIME_WINDOW_V1" for row in artifact["selection_provenance"])
    assert artifact["semantic_terms"] == [] and artifact["semantic_term_linkage"] == "NOT_LINKED_BY_EXACT_ID"


def test_snapshot_is_deterministic_order_independent_and_contains_no_causal_or_kg_fields(tmp_path: Path):
    result = _result()
    first = snapshot_for(assemble_context(result, _incident()))
    reordered = replace(result, relations=tuple(reversed(result.relations)), events=tuple(reversed(result.events)), changes=tuple(reversed(result.changes)))
    second = snapshot_for(assemble_context(reordered, _incident()))
    assert first.snapshot_id == second.snapshot_id and first.content_sha256 == second.content_sha256
    one, two = write_snapshot(first, tmp_path / "one"), write_snapshot(second, tmp_path / "two")
    assert one["sha256"] == two["sha256"]
    serialized = json.dumps(first.artifact(), sort_keys=True)
    assert all(token not in serialized for token in ("root_cause", "causal_score", "caused_by", "likely_cause", "culprit", "owl:sameAs"))
    assert first.context.context_schema_version == CONTEXT_SCHEMA_VERSION


def test_incident_csv_is_control_input_and_is_deterministic():
    path = FIXTURE / "incidents" / "incidents.csv"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    first, second = load_incident_windows(path), load_incident_windows(path)
    assert first == second and first[0].provenance["incident_input_version"] == "incident_window_csv_v1"
    assert before == hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase2_6_and_external_validation_baseline_artifacts_remain_protected():
    baseline = json.loads((ROOT / "experiments" / "archive" / "v3_phase2_7_baseline" / "BASELINE.json").read_text(encoding="utf-8"))
    for relative_path, expected_hash in baseline["protected_artifacts"].items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == expected_hash
