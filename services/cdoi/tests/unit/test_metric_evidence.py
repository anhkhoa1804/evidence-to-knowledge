import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

from cdoi.evidence_schema import EvidenceSchemaInducer
from cdoi.operational_context import TopologyScope, assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import metrics_for_entity, process_dataset, write_artifacts


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"


def _result():
    return process_dataset(FIXTURE / "manifest.yaml")


def _incident():
    return load_incident_windows(FIXTURE / "incidents" / "incidents.csv", "incidents/incidents.csv")[0]


def test_metric_csv_parses_typed_observations_and_preserves_gauge_counter_distinction():
    metrics = {item.metric_id: item for item in _result().metrics}
    assert len(metrics) == 10
    assert (metrics["m-004"].value, metrics["m-004"].unit, metrics["m-004"].metric_kind) == (0.18, "ratio", "GAUGE")
    assert (metrics["m-005"].value, metrics["m-005"].unit, metrics["m-005"].metric_kind) == (10420.0, "count", "COUNTER")
    assert not hasattr(metrics["m-005"], "window_total")


def test_metric_required_numeric_and_unit_failures_are_explicit_and_raw_rows_remain_preserved():
    result = _result()
    statuses = {item.status for item in result.unresolved}
    assert {"INVALID_METRIC_VALUE", "UNSUPPORTED_METRIC_UNIT"}.issubset(statuses)
    raw_metric_ids = {item.source_record_id for item in result.raw_records if item.source_type == "metric_observation_csv"}
    assert {"m-011", "m-012"}.issubset(raw_metric_ids)


def test_metric_exact_identity_timestamp_normalization_and_inclusive_query_boundaries():
    result = _result()
    metrics = {item.metric_id: item for item in result.metrics}
    assert metrics["m-002"].observed_at == "2026-09-18T09:50:00Z"
    assert metrics["m-009"].correlation_status == "UNRESOLVED_METRIC_TARGET"
    selected = metrics_for_entity(result.metrics, "payment-service", "2026-09-18T09:50:00Z", "2026-09-18T10:10:00Z")
    assert {item.metric_id for item in selected} == {"m-002", "m-003", "m-004", "m-005", "m-006", "m-010"}
    assert "m-001" not in {item.metric_id for item in selected} and "m-007" not in {item.metric_id for item in selected}


def test_metric_series_identity_preserves_unit_kind_aggregation_and_sampling_metadata():
    metrics = {item.metric_id: item for item in _result().metrics}
    assert metrics["m-003"].sampling_interval == "15s"
    assert metrics["m-003"].aggregation == "avg"
    assert metrics["m-003"].window_start == "2026-09-18T09:57:45Z"
    assert metrics["m-003"].series_key == metrics["m-002"].series_key
    assert metrics["m-006"].series_key != metrics["m-003"].series_key
    assert metrics["m-010"].series_key != metrics["m-003"].series_key


def test_unit_conflicts_are_reported_without_combining_observations():
    result = _result()
    conflicts = [item for item in result.unresolved if item.status == "METRIC_UNIT_CONFLICT"]
    assert len(conflicts) == 5
    metrics = {item.metric_id: item for item in result.metrics}
    assert metrics["m-003"].unit == "ms" and metrics["m-010"].unit == "bytes"


def test_metric_artifacts_and_diagnostics_are_deterministic_and_do_not_expand_schema(tmp_path: Path):
    first, second = _result(), _result()
    one, two = write_artifacts(first, tmp_path / "one"), write_artifacts(second, tmp_path / "two")
    assert one["artifacts"]["metrics.jsonl"] == two["artifacts"]["metrics.jsonl"]
    assert one["metric_diagnostics"]["metric_series_count"] == 7
    assert one["metric_diagnostics"]["gauge_count"] == 9 and one["metric_diagnostics"]["counter_count"] == 1
    schema_text = (tmp_path / "one" / "schema_candidates.jsonl").read_text(encoding="utf-8")
    assert "request_latency" not in schema_text and len(EvidenceSchemaInducer().induce(first)) == 6


def test_snapshot_selects_direct_and_one_hop_metrics_by_exact_scope_and_time_only():
    result = _result()
    direct = snapshot_for(assemble_context(result, _incident(), TopologyScope.DIRECT_ONLY)).artifact()
    one_hop = snapshot_for(assemble_context(result, _incident(), TopologyScope.ONE_HOP)).artifact()
    assert {item["metric_id"] for item in direct["metrics"]} == {"m-002", "m-003", "m-004", "m-005", "m-006", "m-010"}
    assert {item["metric_id"] for item in one_hop["metrics"]} == {"m-002", "m-003", "m-004", "m-005", "m-006", "m-008", "m-010"}
    reasons = {(item["evidence_id"], item["selection_rule"]) for item in one_hop["selection_provenance"]}
    assert (next(item.evidence_id for item in result.metrics if item.metric_id == "m-008"), "METRIC_ONE_HOP_ENTITY_IN_WINDOW_V1") in reasons


def test_metric_snapshot_provenance_and_serialization_are_deterministic_under_input_reordering():
    result = _result()
    first = snapshot_for(assemble_context(result, _incident()))
    reordered = replace(result, metrics=tuple(reversed(result.metrics)))
    second = snapshot_for(assemble_context(reordered, _incident()))
    assert first.snapshot_id == second.snapshot_id and first.artifact() == second.artifact()
    metric = next(item for item in first.artifact()["metrics"] if item["metric_id"] == "m-003")
    assert metric["provenance"]["raw_evidence_id"] == metric["evidence_id"]
    assert metric["provenance"]["source_file"] == "metrics/metrics.csv"


def test_metric_snapshot_contains_observations_not_anomaly_causal_or_kg_fields():
    serialized = json.dumps(snapshot_for(assemble_context(_result(), _incident())).artifact(), sort_keys=True).casefold()
    assert all(token not in serialized for token in ("anomalous", "likely_cause", "causal_score", "root_cause", "owl:sameas", "approved"))


def test_manifest_without_metrics_remains_valid_and_has_no_metrics_artifact(tmp_path: Path):
    dataset = tmp_path / "dataset"; shutil.copytree(FIXTURE, dataset)
    manifest_path = dataset / "manifest.yaml"
    manifest_path.write_text(manifest_path.read_text(encoding="utf-8").replace("  - id: service_metrics\n    type: metric_observation_csv\n    path: metrics/metrics.csv\n", ""), encoding="utf-8")
    result = process_dataset(manifest_path)
    write_artifacts(result, tmp_path / "output")
    assert result.metrics == () and not (tmp_path / "output" / "metrics.jsonl").exists()


def test_phase2_7_context_remains_valid_when_metrics_are_absent():
    result = replace(_result(), metrics=())
    snapshot = snapshot_for(assemble_context(result, _incident())).artifact()
    assert snapshot["metrics"] == [] and snapshot["schema_version"] == "operational_evidence_context_v1"


def test_metric_fixture_is_read_only_and_phase2_7_artifacts_match_pre_metrics_baseline():
    metric_path = FIXTURE / "metrics" / "metrics.csv"
    before = hashlib.sha256(metric_path.read_bytes()).hexdigest()
    _result()
    assert before == hashlib.sha256(metric_path.read_bytes()).hexdigest()
    baseline = json.loads((ROOT / "experiments" / "archive" / "v3_phase2_8_baseline" / "BASELINE.json").read_text(encoding="utf-8"))
    for relative_path, expected_hash in baseline["protected_artifacts"].items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == expected_hash
