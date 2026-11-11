"""Read-only, deterministic adapter for the bounded VDT source package.

This adapter deliberately produces existing CDOI normalized evidence types.  It
does not read a label value into the evidence path, perform fuzzy identity
resolution, claim causality, write a KG, or mutate the VDT source directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .operational_context import IncidentWindow, OperationalContextError
from .raw_preprocessing import (
    DatasetManifest, NormalizedEntityEvidence, NormalizedEventEvidence,
    NormalizedRelationEvidence, PreprocessingIssue, PreprocessingResult,
    RawEvidenceRecord, SourceSpec,
)

VDT_ADAPTER_VERSION = "vdt_operational_adapter_v1"
VDT_DATASET_ID = "vdt_read_only_operational_v1"
_FILES = ("dependencies.jsonl", "incident.json", "logs.jsonl", "service-id-map.jsonl", "service-intake-example.csv")
_RELATIONS = {"dependsOn": "depends_on"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").split())


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _id(*parts: object) -> str:
    return "vdt-" + _sha("\x1f".join(str(part) for part in parts).encode("utf-8"))[:24]


def public_identifier(value: str) -> str:
    """Stable reporting pseudonym; raw VDT identifiers never enter reports."""
    return "vdt-id-" + _sha(value.encode("utf-8"))[:16]


def _time(value: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_jsonl(path: Path) -> tuple[list[tuple[int, Mapping[str, Any]]], int]:
    rows: list[tuple[int, Mapping[str, Any]]] = []
    malformed = 0
    for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(value, Mapping):
            malformed += 1
            continue
        rows.append((index, dict(value)))
    return rows, malformed


def _inventory_row(path: Path) -> Mapping[str, Any]:
    raw = path.read_bytes()
    base: dict[str, Any] = {"relative_path": path.name, "extension": path.suffix, "size_bytes": len(raw), "sha256": _sha(raw), "encoding": "utf-8-sig"}
    if path.suffix == ".csv":
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
        base.update({"parseability": "PARSEABLE", "record_count": len(rows), "top_level_schema": list(rows[0]) if rows else [], "likely_modality": "service_metadata"})
        return base
    if path.suffix == ".jsonl":
        rows, malformed = _read_jsonl(path)
        keys = sorted({key for _, row in rows for key in row})
        modality = "logs_events" if path.name == "logs.jsonl" else "topology_dependencies" if path.name == "dependencies.jsonl" else "identity_mapping"
        timestamp_keys = [key for key in ("timestamp", "observed_at", "collected_at") if key in keys]
        ranges: dict[str, Mapping[str, str]] = {}
        for key in timestamp_keys:
            values = sorted(_clean(row.get(key)) for _, row in rows if _clean(row.get(key)))
            if values:
                ranges[key] = {"min": values[0], "max": values[-1]}
        base.update({"parseability": "PARSEABLE" if not malformed else "PARSEABLE_WITH_MALFORMED_RECORDS", "record_count": len(rows), "malformed_record_count": malformed, "top_level_schema": keys, "likely_modality": modality, "time_ranges": ranges})
        return base
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {**base, "parseability": "UNPARSEABLE", "record_count": None, "top_level_schema": [], "likely_modality": "unknown"}
    if path.name == "incident.json" and isinstance(value, Mapping):
        incidents = value.get("incidents") if isinstance(value.get("incidents"), list) else []
        keys = sorted({key for row in incidents if isinstance(row, Mapping) for key in row})
        dates = {key: sorted(_clean(row.get(key)) for row in incidents if isinstance(row, Mapping) and _clean(row.get(key))) for key in ("start_time", "end_time")}
        base.update({"parseability": "PARSEABLE", "record_count": len(incidents), "top_level_schema": keys, "likely_modality": "incident_records", "time_ranges": {key: {"min": rows[0], "max": rows[-1]} for key, rows in dates.items() if rows}})
        return base
    return {**base, "parseability": "PARSEABLE", "record_count": 1, "top_level_schema": sorted(value) if isinstance(value, Mapping) else [], "likely_modality": "unknown"}


def source_inventory(root: Path) -> Mapping[str, Any]:
    """Structural, hash-based inventory; it does not expose record values."""
    rows = []
    for name in _FILES:
        path = root / name
        rows.append(_inventory_row(path) if path.is_file() else {"relative_path": name, "parseability": "MISSING", "likely_modality": "unknown"})
    return {"schema_version": "vdt_source_inventory_v1", "source_root_class": "EXTERNAL_READ_ONLY", "files": rows}


def _source_files(root: Path) -> tuple[Mapping[str, Any], ...]:
    rows = []
    for name in _FILES:
        path = root / name
        if path.is_file():
            raw = path.read_bytes(); rows.append({"source_id": name, "source_type": "vdt_source", "relative_path": name, "sha256": _sha(raw), "size": len(raw)})
    return tuple(rows)


def _manifest(root: Path) -> DatasetManifest:
    specs = (
        SourceSpec("vdt_services", "service_inventory_csv", "service-intake-example.csv"),
        SourceSpec("vdt_dependencies", "dependency_jsonl", "dependencies.jsonl"),
        SourceSpec("vdt_logs", "log_jsonl", "logs.jsonl"),
        SourceSpec("vdt_service_map", "identity_map_jsonl", "service-id-map.jsonl"),
    )
    return DatasetManifest(VDT_DATASET_ID, None, "UTC", specs)


def _raw(source_id: str, source_type: str, source_file: str, record_id: str, index: int, payload: Mapping[str, Any]) -> RawEvidenceRecord:
    return RawEvidenceRecord(_id(VDT_DATASET_ID, source_id, record_id, index), source_type, source_id, source_file, record_id, _clean(payload.get("timestamp") or payload.get("observed_at")) or None, dict(payload), {"dataset_id": VDT_DATASET_ID, "dataset_timezone": "UTC", "source_adapter": VDT_ADAPTER_VERSION, "normalization_version": VDT_ADAPTER_VERSION, "record_index": index})


def _provenance(raw: RawEvidenceRecord) -> Mapping[str, Any]:
    return {"dataset_id": VDT_DATASET_ID, "source_type": raw.source_type, "source_file": raw.source_file, "source_record_id": raw.source_record_id, "source_record_index": raw.provenance["record_index"], "raw_evidence_id": raw.evidence_id, "source_adapter": VDT_ADAPTER_VERSION}


@dataclass(frozen=True)
class VDTNormalized:
    result: PreprocessingResult
    quality: Mapping[str, Any]


def normalize(root: Path) -> VDTNormalized:
    """Normalize VDT in memory using exact identifiers only."""
    required = (root / "service-intake-example.csv", root / "dependencies.jsonl", root / "logs.jsonl", root / "service-id-map.jsonl")
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("VDT_REQUIRED_SOURCE_MISSING")
    manifest = _manifest(root); raw_rows: list[RawEvidenceRecord] = []; entities: list[NormalizedEntityEvidence] = []; relations: list[NormalizedRelationEvidence] = []; events: list[NormalizedEventEvidence] = []; issues: list[PreprocessingIssue] = []
    services = list(csv.DictReader((root / "service-intake-example.csv").read_text(encoding="utf-8-sig").splitlines()))
    known: set[str] = set()
    for index, row in enumerate(services, 2):
        service_id, label = _clean(row.get("service_id")), _clean(row.get("service_name"))
        record = _raw("vdt_services", "service_inventory_csv", "service-intake-example.csv", service_id or str(index), index, row); raw_rows.append(record)
        if not service_id or not label:
            issues.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", "vdt_services", record.source_file, str(index), "service_id/service_name required", record.evidence_id)); continue
        if service_id in known:
            issues.append(PreprocessingIssue("DUPLICATE_EXTERNAL_ID", "vdt_services", record.source_file, service_id, "duplicate service_id", record.evidence_id)); continue
        known.add(service_id)
        metadata = {key: _clean(row.get(key)) for key in ("environment", "namespace", "cluster", "kind", "runtime_type") if _clean(row.get(key))}
        entities.append(NormalizedEntityEvidence(record.evidence_id, "vdt_services", service_id, label, None, metadata, _provenance(record)))
    dep_rows, dep_bad = _read_jsonl(root / "dependencies.jsonl")
    for index, row in dep_rows:
        source_id, target_id = _clean(row.get("from_service_id")), _clean(row.get("to_service_id")); relation = _RELATIONS.get(_clean(row.get("relation")))
        record = _raw("vdt_dependencies", "dependency_jsonl", "dependencies.jsonl", f"{source_id}->{target_id}", index, row); raw_rows.append(record)
        if not source_id or not target_id or not relation:
            issues.append(PreprocessingIssue("MALFORMED_RECORD", "vdt_dependencies", record.source_file, str(index), "unsupported or missing dependency fields", record.evidence_id)); continue
        resolved = source_id in known and target_id in known
        relations.append(NormalizedRelationEvidence(record.evidence_id, "vdt_dependencies", source_id, relation, target_id, "RESOLVED_EXACT_ID" if resolved else "UNRESOLVED_REFERENCE", _provenance(record)))
        if not resolved: issues.append(PreprocessingIssue("UNKNOWN_ENTITY_REFERENCE", "vdt_dependencies", record.source_file, str(index), "dependency endpoint unresolved", record.evidence_id))
    log_rows, log_bad = _read_jsonl(root / "logs.jsonl"); missing_log_identity_or_message = 0; invalid_log_timestamp = 0
    for index, row in log_rows:
        service_id, message, timestamp = _clean(row.get("service_id")), _clean(row.get("message")), _clean(row.get("timestamp")); record = _raw("vdt_logs", "log_jsonl", "logs.jsonl", str(index), index, row); raw_rows.append(record)
        normalized_time = _time(timestamp)
        if not service_id or not message:
            missing_log_identity_or_message += 1
            issues.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", "vdt_logs", record.source_file, str(index), "service_id/message required", record.evidence_id)); continue
        if not normalized_time:
            invalid_log_timestamp += 1
            issues.append(PreprocessingIssue("INVALID_TIMESTAMP", "vdt_logs", record.source_file, str(index), "timestamp invalid or timezone-free", record.evidence_id)); continue
        correlation = "RESOLVED_EXACT_ID" if service_id in known else "UNRESOLVED_REFERENCE"
        events.append(NormalizedEventEvidence(record.evidence_id, "vdt_logs", service_id, message, normalized_time, timestamp, _clean(row.get("level")) or None, correlation, {key: _clean(row.get(key)) for key in ("canonical_id", "namespace", "pod") if _clean(row.get(key))}, _provenance(record)))
        if correlation != "RESOLVED_EXACT_ID": issues.append(PreprocessingIssue("UNKNOWN_ENTITY_REFERENCE", "vdt_logs", record.source_file, str(index), "log service unresolved", record.evidence_id))
    map_rows, map_bad = _read_jsonl(root / "service-id-map.jsonl")
    for index, row in map_rows:
        service_id = _clean(row.get("service_id")); record = _raw("vdt_service_map", "identity_map_jsonl", "service-id-map.jsonl", service_id or str(index), index, row); raw_rows.append(record)
        if not service_id or service_id not in known: issues.append(PreprocessingIssue("UNKNOWN_ENTITY_REFERENCE", "vdt_service_map", record.source_file, str(index), "identity-map service unresolved", record.evidence_id))
    for source_id, path, count in (("vdt_dependencies", "dependencies.jsonl", dep_bad), ("vdt_logs", "logs.jsonl", log_bad), ("vdt_service_map", "service-id-map.jsonl", map_bad)):
        for index in range(count): issues.append(PreprocessingIssue("MALFORMED_RECORD", source_id, path, f"malformed-{index + 1}", "invalid JSONL record"))
    files = _source_files(root); manifest_hash = _sha(json.dumps({"dataset_id": VDT_DATASET_ID, "source_hashes": [(row["relative_path"], row["sha256"]) for row in files]}, sort_keys=True).encode("utf-8"))
    result = PreprocessingResult(manifest, manifest_hash, files, tuple(sorted(raw_rows, key=lambda row: row.evidence_id)), tuple(sorted(entities, key=lambda row: row.evidence_id)), tuple(sorted(relations, key=lambda row: row.evidence_id)), tuple(sorted(events, key=lambda row: row.evidence_id)), (), (), tuple(sorted(issues, key=lambda row: (row.source_file, row.source_record_id, row.status))), (), ())
    quality = {"services_input": len(services), "services_normalized": len(entities), "dependencies_input": len(dep_rows), "dependencies_normalized": len(relations), "logs_input": len(log_rows), "logs_normalized": len(events), "identity_map_input": len(map_rows), "malformed_jsonl": {"dependencies": dep_bad, "logs": log_bad, "service_map": map_bad}, "missing_log_identity_or_message": missing_log_identity_or_message, "invalid_log_timestamp": invalid_log_timestamp, "issues": len(issues), "exact_log_service_resolution": sum(row.correlation_status == "RESOLVED_EXACT_ID" for row in events)}
    return VDTNormalized(result, quality)


def load_incidents(root: Path) -> tuple[tuple[IncidentWindow, ...], Mapping[str, Any]]:
    """Load label-free incident windows and describe, but never expose, labels."""
    payload = json.loads((root / "incident.json").read_text(encoding="utf-8-sig"))
    rows = payload.get("incidents") if isinstance(payload, Mapping) and isinstance(payload.get("incidents"), list) else []
    windows: list[IncidentWindow] = []; invalid = 0; label_present = 0; invalid_reasons: dict[str, int] = {}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            invalid += 1; invalid_reasons["NON_OBJECT_INCIDENT"] = invalid_reasons.get("NON_OBJECT_INCIDENT", 0) + 1; continue
        if "rca_status" in row and row.get("rca_status") is not None: label_present += 1
        try:
            incident_id, service_id = _clean(row.get("incident_id")), _clean(row.get("service_id"))
            if not incident_id or not service_id: raise OperationalContextError("missing incident/service identity")
            windows.append(IncidentWindow(incident_id, _clean(row.get("start_time")), _clean(row.get("end_time")), (service_id,), source="VDT_INCIDENT_MANIFEST_V1", external_incident_id=incident_id, provenance={"source_file": "incident.json", "source_record_id": str(index), "source_adapter": VDT_ADAPTER_VERSION}, original_start_time=_clean(row.get("start_time")), original_end_time=_clean(row.get("end_time"))))
        except (OperationalContextError, ValueError) as exc:
            invalid += 1
            reason = "MISSING_INCIDENT_ID_OR_SERVICE" if "missing incident/service" in str(exc) else "INVALID_INCIDENT_WINDOW"
            invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
    labels = {"schema_version": "vdt_label_risk_v1", "potential_label_fields": [{"source_file": "incident.json", "field": "rca_status", "coverage": label_present, "value_type": "UNKNOWN_NOT_READ", "classification": "POTENTIAL_LABEL_FIELD", "leakage_risk": "HIGH_EXCLUDED_FROM_PREPROCESSING_AND_PILOT"}], "incident_records": len(rows), "invalid_incident_records": invalid, "invalid_incident_reasons": dict(sorted(invalid_reasons.items()))}
    return tuple(sorted(windows, key=lambda row: (row.start_time, row.incident_id))), labels
