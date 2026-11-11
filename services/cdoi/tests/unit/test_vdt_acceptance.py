from __future__ import annotations

import hashlib
import json

import pytest

from cdoi.rca_poc import run_package
from cdoi.vdt_acceptance import build_poc_package, coverage_csv_rows, source_inventory, validate


def _fixture(root, *, aligned: bool = True, label: str = "secret-root-label"):
    (root / "service-intake-example.csv").write_text(
        "service_id,service_name,environment,owner_team\ns1,Service One,dev,team-a\ns2,Service Two,dev,team-b\n", encoding="utf-8")
    (root / "dependencies.jsonl").write_text('{"from_service_id":"s1","to_service_id":"s2","relation":"dependsOn"}\n', encoding="utf-8")
    timestamp = "2026-01-01T00:10:00Z" if aligned else "2026-01-02T00:10:00Z"
    (root / "logs.jsonl").write_text(json.dumps({"timestamp": timestamp, "service_id": "s1", "message": "bounded event", "level": "ERROR"}) + "\n", encoding="utf-8")
    (root / "service-id-map.jsonl").write_text('{"service_id":"s1","canonical_id":"c1"}\n', encoding="utf-8")
    (root / "incident.json").write_text(json.dumps({"incidents": [{"incident_id": "internal-1", "service_id": "s1", "start_time": "2026-01-01T00:00:00Z", "end_time": "2026-01-01T01:00:00Z", "cluster": "dev", "rca_status": label}]}), encoding="utf-8")


def test_inventory_is_structural_and_does_not_export_label_values(tmp_path):
    _fixture(tmp_path)
    result = source_inventory(tmp_path)
    rendered = json.dumps(result, sort_keys=True)
    assert "secret-root-label" not in rendered
    incident = next(row for row in result["files"] if row["source_name"] == "incident.json")
    label = next(row for row in incident["fields"] if row["field"] == "rca_status")
    assert label["value_access"] == "EXCLUDED_LABEL_FIELD_VALUE_NOT_READ"


def test_exact_temporal_acceptance_and_no_window_expansion(tmp_path):
    _fixture(tmp_path, aligned=False)
    result = validate(tmp_path)
    row = result["incidents"][0]
    assert row["status"] == "REJECTED_TEMPORAL_ALIGNMENT"
    assert row["modalities"]["logs"] == "PRESENT_NOT_ALIGNED"
    assert result["aggregate"]["minimum_poc_packages"] == 0
    assert result["label_package"]["label_values_read"] is False


def test_builder_is_deterministic_label_free_and_poc_preflight_stops_before_agent(tmp_path, monkeypatch):
    _fixture(tmp_path)
    accepted = validate(tmp_path)
    incident_id = accepted["incidents"][0]["incident_id"]
    first = tmp_path / "first"; second = tmp_path / "second"
    build_poc_package(tmp_path, incident_id, first)
    build_poc_package(tmp_path, incident_id, second)
    first_hashes = {path.relative_to(first).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in first.rglob("*") if path.is_file() and path.name != "BUILD_METADATA.json"}
    second_hashes = {path.relative_to(second).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in second.rglob("*") if path.is_file() and path.name != "BUILD_METADATA.json"}
    assert first_hashes == second_hashes
    assert "secret-root-label" not in "".join(path.read_text(encoding="utf-8") for path in first.rglob("*") if path.is_file())
    monkeypatch.setattr("cdoi.rca_poc.create_live_v24_agent", lambda: pytest.fail("provider must not be constructed"))
    result = run_package(first, tmp_path / "preflight", preflight_only=True)
    assert result.status == "INSUFFICIENT_EVIDENCE"
    artifact = json.loads((tmp_path / "preflight" / "PREFLIGHT_ONLY.json").read_text(encoding="utf-8"))
    assert artifact["provider_invoked"] is False and artifact["live_llm_calls"] == 0
    assert not (tmp_path / "preflight" / "agent_run").exists()


def test_builder_rejects_unaccepted_incident(tmp_path):
    _fixture(tmp_path, aligned=False)
    incident_id = validate(tmp_path)["incidents"][0]["incident_id"]
    with pytest.raises(ValueError, match="INCIDENT_NOT_ACCEPTED_FOR_POC_PREFLIGHT"):
        build_poc_package(tmp_path, incident_id, tmp_path / "package")


def test_coverage_rows_use_explicit_modality_states(tmp_path):
    _fixture(tmp_path)
    row = coverage_csv_rows(validate(tmp_path))[0]
    assert row["logs"] == "PRESENT_ALIGNED"
    assert row["metrics"] == "ABSENT" and row["traces"] == "ABSENT"
    assert row["poc_ready"] is True


def test_duplicate_inventory_and_dangling_topology_are_reported_without_fuzzy_repair(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "service-intake-example.csv").write_text(
        "service_id,service_name,environment\ns1,Service One,dev\ns1,Duplicate,dev\ns2,Service Two,dev\n", encoding="utf-8")
    (tmp_path / "dependencies.jsonl").write_text('{"from_service_id":"s1","to_service_id":"near-s2","relation":"dependsOn"}\n', encoding="utf-8")
    inventory = source_inventory(tmp_path)
    service_file = next(row for row in inventory["files"] if row["source_name"] == "service-intake-example.csv")
    service_key = next(row for row in service_file["unique_identity_keys"] if row["field"] == "service_id")
    assert service_key["duplicate_count"] == 1
    result = validate(tmp_path)
    row = result["incidents"][0]
    assert row["modalities"]["topology"] == "PRESENT_NOT_ALIGNED"
    assert row["status"] == "ACCEPTED_FOR_POC_PREFLIGHT"


def test_invalid_timezone_and_end_before_start_are_rejected_as_schema(tmp_path):
    _fixture(tmp_path)
    (tmp_path / "incident.json").write_text(json.dumps({"incidents": [
        {"incident_id": "i1", "service_id": "s1", "start_time": "2026-01-01T00:00:00", "end_time": "2026-01-01T01:00:00Z"},
        {"incident_id": "i2", "service_id": "s1", "start_time": "2026-01-01T02:00:00Z", "end_time": "2026-01-01T01:00:00Z"},
    ]}), encoding="utf-8")
    result = validate(tmp_path)
    assert result["structurally_valid_incidents"] == 0
    assert result["status_counts"] == {"REJECTED_SCHEMA": 2}
