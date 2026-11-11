"""Label-free acceptance checks for a future governed VDT delivery."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED = ("incident.json", "logs.jsonl", "dependencies.jsonl", "service-intake-example.csv", "service-id-map.jsonl")


def _time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip(): return None
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def validate(root: Path) -> dict[str, Any]:
    files = {name: root / name for name in REQUIRED}
    hashes = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items() if path.is_file()}
    missing = sorted(name for name, path in files.items() if not path.is_file())
    if missing: return {"schema_version": "vdt_delivery_acceptance_v1", "status": "REJECT", "missing_required_files": missing, "source_hashes": hashes}
    incidents_doc = json.loads(files["incident.json"].read_text(encoding="utf-8-sig")); incidents = incidents_doc.get("incidents", []) if isinstance(incidents_doc, dict) else []
    logs = [json.loads(line) for line in files["logs.jsonl"].read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    services = list(csv.DictReader(files["service-intake-example.csv"].read_text(encoding="utf-8-sig").splitlines()))
    valid = [(row, _time(row.get("start_time")), _time(row.get("end_time"))) for row in incidents if isinstance(row, dict)]
    valid = [(row, start, end) for row, start, end in valid if start and end and end >= start and row.get("service_id")]
    events = [(row, _time(row.get("timestamp"))) for row in logs if isinstance(row, dict)]
    events = [(row, timestamp) for row, timestamp in events if timestamp]
    overlap = sum(sum(start <= stamp <= end for _, stamp in events) for _, start, end in valid)
    label_fields = sorted({key for row in incidents if isinstance(row, dict) for key in row if key in {"rca_status", "root_service", "root_component", "root_entity", "root_cause_category", "fault_domain", "confirmed_cause"}})
    service_ids = {row.get("service_id") for row in services if row.get("service_id")}
    return {"schema_version": "vdt_delivery_acceptance_v1", "status": "ACCEPTANCE_REVIEW_REQUIRED", "source_hashes": hashes,
            "incident_total": len(incidents), "valid_incident_windows": len(valid), "event_total": len(events),
            "incident_event_overlap_count": overlap, "exact_incident_service_ids_known": sum(row.get("service_id") in service_ids for row, _, _ in valid),
            "potential_label_fields_detected_names_only": label_fields, "label_values_read": False,
            "required_governance_metadata": ["data owner", "collection method/period", "label provenance", "label independence", "export filtering/missing-period documentation"],
            "acceptance_rule": "Do not construct evidence profiles or evaluate labels until temporal overlap, valid windows, exact identity, governed label semantics, and provenance are reviewed."}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("source", type=Path); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    args.output.write_text(json.dumps(validate(args.source), indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
