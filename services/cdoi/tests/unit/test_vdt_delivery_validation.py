import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from validate_vdt_delivery import validate


def test_delivery_validator_does_not_read_or_return_label_values(tmp_path):
    (tmp_path / "service-intake-example.csv").write_text("service_id\ns1\n", encoding="utf-8")
    (tmp_path / "dependencies.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "service-id-map.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "logs.jsonl").write_text('{"timestamp":"2026-01-01T00:10:00Z"}\n', encoding="utf-8")
    (tmp_path / "incident.json").write_text(json.dumps({"incidents":[{"service_id":"s1","start_time":"2026-01-01T00:00:00Z","end_time":"2026-01-01T01:00:00Z","rca_status":"secret-label"}]}), encoding="utf-8")
    result = validate(tmp_path)
    assert result["incident_event_overlap_count"] == 1
    assert result["label_values_read"] is False
    assert "secret-label" not in json.dumps(result)
