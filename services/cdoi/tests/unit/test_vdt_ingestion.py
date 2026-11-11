from __future__ import annotations

import hashlib
import json

from cdoi.vdt_ingestion import load_incidents, normalize, source_inventory


def _write_fixture(root):
    (root / "service-intake-example.csv").write_text("service_id,service_name,environment\ns1,Service One,dev\ns2,Service Two,dev\n", encoding="utf-8")
    (root / "dependencies.jsonl").write_text('{"from_service_id":"s1","to_service_id":"s2","relation":"dependsOn"}\n', encoding="utf-8")
    (root / "logs.jsonl").write_text('{"service_id":"s1","timestamp":"2026-01-01T00:00:00Z","message":"bounded event","level":"ERROR"}\n', encoding="utf-8")
    (root / "service-id-map.jsonl").write_text('{"service_id":"s1","canonical_id":"c1"}\n', encoding="utf-8")
    (root / "incident.json").write_text(json.dumps({"incidents": [{"incident_id":"i1","service_id":"s1","start_time":"2026-01-01T00:00:00Z","end_time":"2026-01-01T01:00:00Z","rca_status":"hidden-label"}]}), encoding="utf-8")


def test_vdt_normalization_is_deterministic_and_exact_id_only(tmp_path):
    _write_fixture(tmp_path)
    before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in tmp_path.iterdir()}
    first, second = normalize(tmp_path), normalize(tmp_path)
    assert [(row.external_id, row.label) for row in first.result.entities] == [("s1", "Service One"), ("s2", "Service Two")]
    assert [(row.source_external_id, row.relation, row.target_external_id, row.resolution_status) for row in first.result.relations] == [("s1", "depends_on", "s2", "RESOLVED_EXACT_ID")]
    assert first.result.manifest_hash == second.result.manifest_hash
    assert before == {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in tmp_path.iterdir()}


def test_vdt_incident_labels_are_classified_but_never_enter_windows(tmp_path):
    _write_fixture(tmp_path)
    windows, labels = load_incidents(tmp_path)
    assert len(windows) == 1 and windows[0].incident_id == "i1"
    assert "rca_status" not in windows[0].provenance
    assert labels["potential_label_fields"][0]["classification"] == "POTENTIAL_LABEL_FIELD"


def test_vdt_inventory_is_structural_and_reports_modalities(tmp_path):
    _write_fixture(tmp_path)
    inventory = source_inventory(tmp_path)
    by_name = {row["relative_path"]: row for row in inventory["files"]}
    assert by_name["logs.jsonl"]["likely_modality"] == "logs_events"
    assert by_name["incident.json"]["likely_modality"] == "incident_records"
    assert "bounded event" not in json.dumps(inventory)
