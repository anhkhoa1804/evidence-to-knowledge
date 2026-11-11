"""Deterministic, label-isolated VDT-to-POC acceptance and packaging layer.

This module is intentionally upstream of RCA reasoning.  It inventories a
read-only VDT delivery, validates exact identity and time overlap, and builds
the existing RCA POC V0 package format only for accepted incidents.  It never
uses a live model, reads a label value, widens an incident window, or changes a
candidate-generation rule.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from .vdt_ingestion import normalize, public_identifier

ACCEPTANCE_VERSION = "vdt_poc_acceptance_v1"
POC_SCHEMA_VERSION = "cdoi_rca_poc_v0"
REQUIRED = ("incident.json", "logs.jsonl", "dependencies.jsonl", "service-intake-example.csv", "service-id-map.jsonl")
LABEL_KEYS = frozenset({"rca_status", "root_service", "root_component", "root_entity", "root_cause", "root_cause_category", "confirmed_cause", "fault_domain", "verified_by", "verified_at"})
MODALITIES = ("logs", "metrics", "traces", "changes", "topology", "provenance")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> tuple[list[Mapping[str, Any]], int]:
    rows: list[Mapping[str, Any]] = []
    malformed = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(row, Mapping):
            rows.append(row)
        else:
            malformed += 1
    return rows, malformed


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    return type(value).__name__


def _field_inventory(rows: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows = list(rows)
    names = sorted({str(key) for row in rows for key in row})
    result: list[Mapping[str, Any]] = []
    for name in names:
        if name.casefold() in LABEL_KEYS:
            result.append({"field": name, "value_access": "EXCLUDED_LABEL_FIELD_VALUE_NOT_READ", "null_count": "NOT_READ", "primitive_types": []})
            continue
        values = [row[name] for row in rows if name in row]
        nulls = sum(value is None or (isinstance(value, str) and not value.strip()) for value in values)
        result.append({"field": name, "value_access": "STRUCTURAL", "null_count": nulls + len(rows) - len(values), "primitive_types": sorted({_type_name(value) for value in values})})
    return result


def _key_profile(rows: Iterable[Mapping[str, Any]], candidates: Iterable[str]) -> list[Mapping[str, Any]]:
    rows = list(rows)
    profiles: list[Mapping[str, Any]] = []
    for key in candidates:
        values = [str(row[key]).strip() for row in rows if key in row and row[key] is not None and str(row[key]).strip()]
        if not values:
            continue
        counts = Counter(values)
        profiles.append({"field": key, "non_null_count": len(values), "unique_count": len(counts), "duplicate_count": sum(count - 1 for count in counts.values() if count > 1)})
    return profiles


def _time_profile(rows: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Mapping[str, Mapping[str, Any]]:
    rows = list(rows)
    answer: dict[str, Mapping[str, Any]] = {}
    for key in keys:
        values = [_parse_time(row.get(key)) for row in rows if key not in LABEL_KEYS]
        parsed = [value for value in values if value is not None]
        supplied = sum(1 for row in rows if key in row and row.get(key) not in (None, ""))
        if supplied or parsed:
            answer[key] = {"parseable_count": len(parsed), "invalid_or_timezone_free_count": supplied - len(parsed), "earliest_timestamp": _utc(min(parsed)) if parsed else None, "latest_timestamp": _utc(max(parsed)) if parsed else None, "timezone_policy": "EXPLICIT_OFFSET_REQUIRED"}
    return answer


def _records_for(path: Path) -> tuple[list[Mapping[str, Any]], int, str]:
    if path.suffix == ".csv":
        return list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines())), 0, "csv"
    if path.suffix == ".jsonl":
        rows, malformed = _read_jsonl(path)
        return rows, malformed, "jsonl"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if path.name == "incident.json" and isinstance(payload, Mapping) and isinstance(payload.get("incidents"), list):
        return [row for row in payload["incidents"] if isinstance(row, Mapping)], sum(not isinstance(row, Mapping) for row in payload["incidents"]), "json_object.incidents"
    return ([payload] if isinstance(payload, Mapping) else []), 0, "json"


def source_inventory(root: Path) -> Mapping[str, Any]:
    """Return a deterministic inventory without serializing enterprise values."""
    files: list[Mapping[str, Any]] = []
    for name in REQUIRED:
        path = root / name
        if not path.is_file():
            files.append({"source_name": name, "physical_path": name, "format": "UNKNOWN", "status": "MISSING"})
            continue
        rows, malformed, fmt = _records_for(path)
        likely = {"incident.json": "incidents", "logs.jsonl": "logs", "dependencies.jsonl": "topology", "service-intake-example.csv": "service_inventory", "service-id-map.jsonl": "identity_map"}.get(name, "unknown")
        fields = _field_inventory(rows)
        label_names = sorted(row["field"] for row in fields if row["value_access"] == "EXCLUDED_LABEL_FIELD_VALUE_NOT_READ")
        files.append({"source_name": name, "physical_path": name, "format": fmt, "status": "PARSEABLE" if malformed == 0 else "PARSEABLE_WITH_MALFORMED_ROWS", "record_count": len(rows), "malformed_row_count": malformed, "size_bytes": path.stat().st_size, "sha256": _sha(path), "likely_modality": likely, "fields": fields, "timestamp_coverage": _time_profile(rows, ("timestamp", "start_time", "end_time", "observed_at", "collected_at")), "unique_identity_keys": _key_profile(rows, ("incident_id", "service_id", "canonical_id", "coroot_application_id", "from_service_id", "to_service_id", "trace_id", "span_id", "change_id", "metric_id")), "candidate_foreign_keys": sorted(key for key in ("service_id", "from_service_id", "to_service_id", "canonical_id", "coroot_application_id", "parent_span_id") if any(key in row for row in rows)), "label_like_field_names_only": label_names, "provenance_metadata_fields": sorted(key for key in ("source", "snapshot", "collected_at", "observed_at", "environment", "cluster", "namespace") if any(key in row for row in rows))})
    return {"schema_version": "vdt_source_inventory_v2", "source_root_class": "EXTERNAL_READ_ONLY", "files": files, "inventory_policy": "STRUCTURAL_ONLY_NO_LABEL_VALUES_OR_RAW_ENTERPRISE_RECORDS"}


def _incidents(root: Path) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    payload = json.loads((root / "incident.json").read_text(encoding="utf-8-sig"))
    rows = payload.get("incidents") if isinstance(payload, Mapping) and isinstance(payload.get("incidents"), list) else []
    valid: list[Mapping[str, Any]] = []
    invalid: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            invalid.append({"source_row": index, "reason": "NON_OBJECT_INCIDENT"}); continue
        incident_id = row.get("incident_id")
        service_id = row.get("service_id")
        start, end = _parse_time(row.get("start_time")), _parse_time(row.get("end_time"))
        if not isinstance(incident_id, str) or not incident_id.strip():
            invalid.append({"source_row": index, "reason": "MISSING_INCIDENT_ID"}); continue
        public_id = public_identifier(incident_id)
        if not isinstance(service_id, str) or not service_id.strip():
            invalid.append({"incident_id": public_id, "source_row": index, "reason": "MISSING_SERVICE_ID"}); continue
        if not start or not end or end < start:
            invalid.append({"incident_id": public_id, "source_row": index, "reason": "INVALID_INCIDENT_WINDOW"}); continue
        valid.append({"source_row": index, "source_incident_id": incident_id, "incident_id": public_id, "service_id": service_id.strip(), "start": start, "end": end, "environment": str(row.get("cluster") or "") or None})
    return valid, invalid


def _modality_status(delivered: bool, valid_count: int, aligned_count: int) -> str:
    if not delivered:
        return "ABSENT"
    if valid_count == 0:
        return "INVALID"
    return "PRESENT_ALIGNED" if aligned_count else "PRESENT_NOT_ALIGNED"


def validate(root: Path) -> Mapping[str, Any]:
    """Run exact-ID, no-window-expansion acceptance for the current VDT layout."""
    inventory = source_inventory(root)
    missing = [row["source_name"] for row in inventory["files"] if row.get("status") == "MISSING"]
    if missing:
        return {"schema_version": ACCEPTANCE_VERSION, "status": "REJECTED_SCHEMA", "reason_codes": ["MISSING_REQUIRED_SOURCE"], "missing_sources": missing, "incidents": [], "inventory": inventory}
    normalized = normalize(root).result
    known = {row.external_id for row in normalized.entities}
    valid, invalid = _incidents(root)
    events = [row for row in normalized.events if row.correlation_status == "RESOLVED_EXACT_ID"]
    relations = [row for row in normalized.relations if row.resolution_status == "RESOLVED_EXACT_ID"]
    provenance_ok = all(row.get("sha256") for row in inventory["files"])
    coverage: list[Mapping[str, Any]] = []
    for incident in valid:
        start, end, service_id = incident["start"], incident["end"], incident["service_id"]
        direct_events = [row for row in events if row.service_external_id == service_id]
        aligned_events = [row for row in direct_events if start <= _parse_time(row.observed_at) <= end]
        topology = [row for row in relations if service_id in {row.source_external_id, row.target_external_id}]
        identity = "PRESENT_ALIGNED" if service_id in known else "INVALID"
        logs = _modality_status(True, len(direct_events), len(aligned_events))
        topology_status = "PRESENT_ALIGNED" if topology and identity == "PRESENT_ALIGNED" else "PRESENT_NOT_ALIGNED"
        modalities = {"identity": identity, "logs": logs, "metrics": "ABSENT", "traces": "ABSENT", "changes": "ABSENT", "topology": topology_status, "provenance": "PRESENT_ALIGNED" if provenance_ok else "ABSENT"}
        if identity != "PRESENT_ALIGNED":
            status, reasons = "REJECTED_IDENTITY", ["INCIDENT_SERVICE_NOT_IN_EXACT_INVENTORY"]
        elif logs == "PRESENT_ALIGNED":
            status, reasons = "ACCEPTED_FOR_POC_PREFLIGHT", []
        elif logs == "PRESENT_NOT_ALIGNED":
            status, reasons = "REJECTED_TEMPORAL_ALIGNMENT", ["LOGS_PRESENT_NOT_ALIGNED"]
        else:
            status, reasons = "REJECTED_NO_USABLE_EVIDENCE", ["NO_PARSEABLE_LOG_EVIDENCE"]
        coverage.append({"incident_id": incident["incident_id"], "service_id": service_id, "start_time": _utc(start), "end_time": _utc(end), "status": status, "reason_codes": reasons, "modalities": modalities, "counts": {"logs_total_exact_service": len(direct_events), "logs_aligned": len(aligned_events), "metrics_aligned": 0, "traces_aligned": 0, "changes_aligned": 0, "topology_edges_exact_service": len(topology)}, "temporal_coverage": {"logs": _temporal_coverage(direct_events, "observed_at", start, end)}})
    all_rows = coverage + [{"incident_id": row.get("incident_id"), "status": "REJECTED_SCHEMA" if row["reason"] == "INVALID_INCIDENT_WINDOW" else "REJECTED_IDENTITY", "reason_codes": [row["reason"]]} for row in invalid]
    status_counts = Counter(row["status"] for row in all_rows)
    source_hashes = {row["source_name"]: row.get("sha256") for row in inventory["files"] if row.get("sha256")}
    return {"schema_version": ACCEPTANCE_VERSION, "source_root": "EXTERNAL_READ_ONLY", "source_hashes": source_hashes, "incident_total": len(valid) + len(invalid), "structurally_valid_incidents": len(valid), "invalid_incidents": invalid, "incidents": sorted(all_rows, key=lambda row: str(row.get("incident_id") or "")), "status_counts": dict(sorted(status_counts.items())), "aggregate": {"exact_resolvable_identity": sum(row["modalities"]["identity"] == "PRESENT_ALIGNED" for row in coverage), "aligned_logs": sum(row["modalities"]["logs"] == "PRESENT_ALIGNED" for row in coverage), "aligned_metrics": 0, "aligned_traces": 0, "aligned_changes": 0, "usable_topology": sum(row["modalities"]["topology"] == "PRESENT_ALIGNED" for row in coverage), "minimum_poc_packages": sum(row["status"] == "ACCEPTED_FOR_POC_PREFLIGHT" for row in coverage)}, "label_package": {"label_values_read": False, "detected_field_names_only": sorted({field for row in inventory["files"] for field in row.get("label_like_field_names_only", [])}), "policy": "LABELS_MUST_BE_PHYSICALLY_AND_LOGICALLY_SEPARATE_FROM_EVIDENCE"}, "policy": {"exact_identity_only": True, "window_expansion": "PROHIBITED", "timezone_reinterpretation": "PROHIBITED", "live_model_calls": 0}}


def _temporal_coverage(rows: Iterable[Any], field: str, start: datetime, end: datetime) -> Mapping[str, Any]:
    values = sorted(value for value in (_parse_time(getattr(row, field, None)) for row in rows) if value)
    if not values:
        return {"earliest_timestamp": None, "latest_timestamp": None, "incident_start": _utc(start), "incident_end": _utc(end), "overlap_duration_seconds": 0, "pre_window_records": 0, "incident_records": 0, "post_window_records": 0}
    inside = [value for value in values if start <= value <= end]
    return {"earliest_timestamp": _utc(values[0]), "latest_timestamp": _utc(values[-1]), "incident_start": _utc(start), "incident_end": _utc(end), "overlap_duration_seconds": max(0, int((min(end, values[-1]) - max(start, values[0])).total_seconds())) if inside else 0, "pre_window_records": sum(value < start for value in values), "incident_records": len(inside), "post_window_records": sum(value > end for value in values)}


def coverage_csv_rows(acceptance: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for item in acceptance.get("incidents", []):
        modal = item.get("modalities", {})
        rows.append({"incident_id": item.get("incident_id"), "status": item.get("status"), "identity": modal.get("identity", "INVALID"), "logs": modal.get("logs", "ABSENT"), "metrics": modal.get("metrics", "ABSENT"), "traces": modal.get("traces", "ABSENT"), "changes": modal.get("changes", "ABSENT"), "topology": modal.get("topology", "ABSENT"), "provenance": modal.get("provenance", "ABSENT"), "poc_ready": item.get("status") == "ACCEPTED_FOR_POC_PREFLIGHT", "reason_codes": ";".join(item.get("reason_codes", []))})
    return rows


def _safe_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def build_poc_package(root: Path, incident_public_id: str, output: Path) -> Mapping[str, Any]:
    """Build one existing POC V0 package only after acceptance has passed."""
    acceptance = validate(root)
    row = next((row for row in acceptance.get("incidents", []) if row.get("incident_id") == incident_public_id), None)
    if row is None:
        raise ValueError("UNKNOWN_INCIDENT_ID")
    if row["status"] != "ACCEPTED_FOR_POC_PREFLIGHT":
        raise ValueError("INCIDENT_NOT_ACCEPTED_FOR_POC_PREFLIGHT")
    if output.exists():
        raise FileExistsError("REFUSE_TO_OVERWRITE_POC_PACKAGE")
    source_incident = next(item for item in _incidents(root)[0] if item["incident_id"] == incident_public_id)
    output.mkdir(parents=True)
    services = list(csv.DictReader((root / "service-intake-example.csv").read_text(encoding="utf-8-sig").splitlines()))
    inventory_target = output / "inventory" / "services.csv"; inventory_target.parent.mkdir(parents=True)
    with inventory_target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("service_id", "name", "environment", "owner", "description")); writer.writeheader()
        for item in services:
            writer.writerow({"service_id": item.get("service_id", ""), "name": item.get("service_name", ""), "environment": item.get("environment", ""), "owner": item.get("owner_team", ""), "description": ""})
    dependencies, _ = _read_jsonl(root / "dependencies.jsonl")
    dep_target = output / "topology" / "dependencies.jsonl"; dep_target.parent.mkdir(parents=True)
    with dep_target.open("w", encoding="utf-8") as handle:
        for item in dependencies:
            source, target = item.get("from_service_id"), item.get("to_service_id")
            if isinstance(source, str) and isinstance(target, str):
                handle.write(json.dumps({"source_id": source, "target_id": target, "relation": "depends_on"}, sort_keys=True) + "\n")
    logs, _ = _read_jsonl(root / "logs.jsonl")
    start, end = source_incident["start"], source_incident["end"]
    log_target = output / "telemetry" / "logs.jsonl"; log_target.parent.mkdir(parents=True)
    with log_target.open("w", encoding="utf-8") as handle:
        for item in logs:
            stamp = _parse_time(item.get("timestamp"))
            if stamp and start <= stamp <= end and isinstance(item.get("service_id"), str) and isinstance(item.get("message"), str):
                handle.write(json.dumps({"timestamp": _utc(stamp), "service_id": item["service_id"], "event": item["message"], "severity": item.get("level")}, sort_keys=True) + "\n")
    manifest = {"schema_version": POC_SCHEMA_VERSION, "incident_id": incident_public_id, "environment": source_incident.get("environment"), "sources": [{"id": "vdt_inventory", "type": "service_inventory_csv", "path": "inventory/services.csv"}, {"id": "vdt_dependencies", "type": "dependency_jsonl", "path": "topology/dependencies.jsonl"}, {"id": "vdt_logs", "type": "log_jsonl", "path": "telemetry/logs.jsonl"}]}
    incident = {"incident_id": incident_public_id, "start_time": _utc(start), "end_time": _utc(end), "affected_service_ids": [source_incident["service_id"]], "environment": source_incident.get("environment"), "summary": "VDT incident package; no RCA label included."}
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (output / "incident.json").write_text(json.dumps(incident, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    hashes = {path.relative_to(output).as_posix(): _sha(path) for path in sorted(output.rglob("*")) if path.is_file()}
    metadata = {"schema_version": "vdt_poc_package_build_v1", "incident_id": incident_public_id, "source_incident_id": "NOT_EXPORTED", "label_values_read": False, "source_hashes": acceptance["source_hashes"], "package_hashes": hashes, "identity_policy": "EXACT_ID_ONLY", "timestamp_policy": "UTC_NORMALIZED_NO_WINDOW_EXPANSION"}
    (output / "BUILD_METADATA.json").write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return metadata


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cdoi.vdt_acceptance", description="Run deterministic VDT data acceptance; no model is invoked.")
    commands = parser.add_subparsers(dest="command", required=True)
    validate_cmd = commands.add_parser("validate"); validate_cmd.add_argument("source", type=Path); validate_cmd.add_argument("--output", type=Path, required=True)
    build_cmd = commands.add_parser("build-poc-package"); build_cmd.add_argument("incident_id"); build_cmd.add_argument("--source", type=Path, required=True); build_cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "validate":
        _write_json(args.output, validate(args.source)); return 0
    try:
        _write_json(args.output / "BUILD_RESULT.json", build_poc_package(args.source, args.incident_id, args.output))
    except (ValueError, FileExistsError) as exc:
        _write_json(args.output / "BUILD_RESULT.json", {"schema_version": "vdt_poc_package_build_v1", "status": "NOT_BUILT", "reason": str(exc), "live_llm_calls": 0})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
