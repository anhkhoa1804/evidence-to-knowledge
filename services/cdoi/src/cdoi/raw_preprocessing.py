"""Conservative, deterministic MVP intake for small customer data packages.

This module is deliberately upstream of ontology integration. It parses only
the documented constrained manifest source types and never writes an ontology or a KG.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .extraction import StructuredExtractor
from .models import Provenance, SemanticCandidateGraph
from .preprocessing import preprocess
from .schema import DeterministicSchemaInducer


SCHEMA_VERSION = "cdoi_preprocessing_v1"
ADAPTER_VERSION = "cdoi_raw_evidence_mvp_v1"
SUPPORTED_SOURCE_TYPES = {"service_inventory_csv", "dependency_jsonl", "log_jsonl", "glossary_yaml", "deployment_change_csv", "metric_observation_csv", "trace_span_jsonl"}
CHANGE_TYPES = {"DEPLOYMENT", "ROLLBACK", "CONFIG_CHANGE", "RESTART", "VERSION_CHANGE", "FEATURE_CHANGE", "OTHER_DECLARED_CHANGE"}
CHANGE_TYPE_ALIASES = {"DEPLOY": "DEPLOYMENT", "DEPLOYMENT": "DEPLOYMENT", "ROLLBACK": "ROLLBACK", "CONFIG_CHANGE": "CONFIG_CHANGE", "CONFIGURATION_CHANGE": "CONFIG_CHANGE", "RESTART": "RESTART", "VERSION_CHANGE": "VERSION_CHANGE", "FEATURE_CHANGE": "FEATURE_CHANGE", "OTHER_DECLARED_CHANGE": "OTHER_DECLARED_CHANGE"}
METRIC_KINDS = {"GAUGE", "COUNTER", "HISTOGRAM_SAMPLE", "SUMMARY_SAMPLE", "OTHER_DECLARED"}
METRIC_KIND_ALIASES = {item: item for item in METRIC_KINDS} | {"HISTOGRAM": "HISTOGRAM_SAMPLE", "SUMMARY": "SUMMARY_SAMPLE"}
SUPPORTED_METRIC_UNITS = {"ms", "s", "bytes", "percent", "ratio", "count", "requests_per_second"}
TRACE_SPAN_KINDS = {"SERVER", "CLIENT", "PRODUCER", "CONSUMER", "INTERNAL", "OTHER_DECLARED"}
TRACE_STATUSES = {"OK", "ERROR", "UNSET", "OTHER_DECLARED"}


class PreprocessingError(ValueError):
    """A fail-closed manifest or output location error."""


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    source_type: str
    relative_path: str


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    environment: str | None
    timezone: str | None
    sources: tuple[SourceSpec, ...]


@dataclass(frozen=True)
class RawEvidenceRecord:
    evidence_id: str
    source_type: str
    source_system: str
    source_file: str
    source_record_id: str
    observed_at: str | None
    payload: Mapping[str, Any]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedEntityEvidence:
    evidence_id: str
    source_system: str
    external_id: str
    label: str
    description: str | None
    metadata: Mapping[str, str]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedRelationEvidence:
    evidence_id: str
    source_system: str
    source_external_id: str
    relation: str
    target_external_id: str
    resolution_status: str
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedEventEvidence:
    evidence_id: str
    source_system: str
    service_external_id: str
    event: str
    observed_at: str
    original_timestamp: str
    severity: str | None
    correlation_status: str
    metadata: Mapping[str, Any]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedChangeEventEvidence:
    evidence_id: str
    source_system: str
    change_id: str
    target_external_id: str
    change_type: str
    observed_at: str
    original_timestamp: str
    version_before: str | None
    version_after: str | None
    config_key: str | None
    config_before: str | None
    config_after: str | None
    description: str | None
    environment: str | None
    rollback_of: str | None
    rollback_status: str | None
    correlation_status: str
    metadata: Mapping[str, Any]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedMetricEvidence:
    evidence_id: str
    source_system: str
    metric_id: str
    service_external_id: str
    metric_name: str
    value: float
    unit: str
    normalized_unit: str
    metric_kind: str
    aggregation: str | None
    sampling_interval: str | None
    window_start: str | None
    window_end: str | None
    source_metric_name: str | None
    environment: str | None
    series_key: str
    observed_at: str
    original_timestamp: str
    correlation_status: str
    metadata: Mapping[str, Any]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedTraceSpanEvidence:
    evidence_id: str
    source_system: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    service_external_id: str
    operation: str | None
    observed_at: str
    original_start_time: str
    end_time: str
    declared_end_time: str | None
    duration_ms: float | None
    end_time_source: str
    status: str | None
    span_kind: str | None
    sampled: bool | None
    error_code: str | None
    correlation_status: str
    parent_resolution_status: str
    metadata: Mapping[str, Any]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class NormalizedSemanticTerm:
    evidence_id: str
    source_system: str
    external_id: str
    label: str
    definition: str | None
    aliases: tuple[str, ...]
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class PreprocessingIssue:
    status: str
    source_id: str
    source_file: str
    source_record_id: str
    detail: str
    raw_evidence_id: str | None = None


@dataclass(frozen=True)
class PreprocessingResult:
    manifest: DatasetManifest
    manifest_hash: str
    source_files: tuple[Mapping[str, Any], ...]
    raw_records: tuple[RawEvidenceRecord, ...]
    entities: tuple[NormalizedEntityEvidence, ...]
    relations: tuple[NormalizedRelationEvidence, ...]
    events: tuple[NormalizedEventEvidence, ...]
    changes: tuple[NormalizedChangeEventEvidence, ...]
    semantic_terms: tuple[NormalizedSemanticTerm, ...]
    unresolved: tuple[PreprocessingIssue, ...]
    metrics: tuple[NormalizedMetricEvidence, ...] = ()
    traces: tuple[NormalizedTraceSpanEvidence, ...] = ()


def _clean(value: object) -> str:
    return " ".join(str(value).replace("\ufeff", "").split())


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_id(*parts: object) -> str:
    return "ev-" + _sha256_bytes("\x1f".join(str(part) for part in parts).encode("utf-8"))[:24]


def _as_json(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _as_json(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_as_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _as_json(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return float(value)
    return value


def _metric_series_key(entity_id: str, metric_name: str, unit: str, metric_kind: str, aggregation: str | None) -> str:
    signature = "\x1f".join((entity_id, metric_name, unit, metric_kind, aggregation or ""))
    return "metric-series-" + _sha256_bytes(signature.encode("utf-8"))[:24]


def load_manifest(path: Path) -> DatasetManifest:
    try:
        source = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PreprocessingError(f"INVALID_MANIFEST: {exc}") from exc
    if not isinstance(source, dict) or not _clean(source.get("dataset_id", "")) or not isinstance(source.get("sources"), list):
        raise PreprocessingError("INVALID_MANIFEST: dataset_id and sources are required")
    specs: list[SourceSpec] = []
    seen: set[str] = set()
    for item in source["sources"]:
        if not isinstance(item, dict):
            raise PreprocessingError("INVALID_MANIFEST: each source must be a mapping")
        source_id, source_type, relative_path = (_clean(item.get(key, "")) for key in ("id", "type", "path"))
        if not source_id or not source_type or not relative_path:
            raise PreprocessingError("INVALID_MANIFEST: source id, type, and path are required")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise PreprocessingError(f"UNSUPPORTED_SOURCE_TYPE: {source_type}")
        if source_id in seen:
            raise PreprocessingError(f"DUPLICATE_EXTERNAL_ID: source {source_id}")
        seen.add(source_id); specs.append(SourceSpec(source_id, source_type, relative_path))
    return DatasetManifest(_clean(source["dataset_id"]), _clean(source.get("environment", "")) or None, _clean(source.get("timezone", "")) or None, tuple(specs))


def _record(manifest: DatasetManifest, spec: SourceSpec, relative_path: str, record_id: str, payload: Mapping[str, Any], index: int) -> RawEvidenceRecord:
    evidence_id = _stable_id(manifest.dataset_id, spec.source_id, spec.source_type, record_id, index)
    observed_at = _clean(payload.get("timestamp", "")) or None
    return RawEvidenceRecord(evidence_id, spec.source_type, spec.source_id, relative_path, record_id, observed_at, dict(payload), {"dataset_id": manifest.dataset_id, "dataset_timezone": manifest.timezone, "source_adapter": ADAPTER_VERSION, "normalization_version": SCHEMA_VERSION, "record_index": index})


def _provenance(raw: RawEvidenceRecord) -> Mapping[str, Any]:
    return {"dataset_id": raw.provenance["dataset_id"], "declared_dataset_timezone": raw.provenance["dataset_timezone"], "source_type": raw.source_type, "source_file": raw.source_file, "source_adapter": raw.provenance["source_adapter"], "source_record_id": raw.source_record_id, "source_record_index": raw.provenance["record_index"], "raw_evidence_id": raw.evidence_id, "normalization_version": raw.provenance["normalization_version"]}


def _read_jsonl(path: Path, manifest: DatasetManifest, spec: SourceSpec) -> tuple[list[RawEvidenceRecord], list[PreprocessingIssue]]:
    records: list[RawEvidenceRecord] = []; issues: list[PreprocessingIssue] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("JSON value must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            issues.append(PreprocessingIssue("MALFORMED_RECORD", spec.source_id, spec.relative_path, str(index), str(exc)))
            continue
        record_id = _clean(payload.get("id") or payload.get("source_id") or payload.get("service_id") or index)
        records.append(_record(manifest, spec, spec.relative_path, record_id, payload, index))
    return records, issues


def _read_trace_jsonl(path: Path, manifest: DatasetManifest, spec: SourceSpec) -> tuple[list[RawEvidenceRecord], list[PreprocessingIssue]]:
    """Read raw trace records with valid trace/span identity independent of line order."""
    records: list[RawEvidenceRecord] = []; issues: list[PreprocessingIssue] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("JSON value must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            issues.append(PreprocessingIssue("MALFORMED_RECORD", spec.source_id, spec.relative_path, str(index), str(exc)))
            continue
        trace_id, span_id = _clean(payload.get("trace_id", "")), _clean(payload.get("span_id", ""))
        record_id = f"{trace_id}\x1f{span_id}" if trace_id and span_id else str(index)
        evidence_id = _stable_id(manifest.dataset_id, spec.source_id, spec.source_type, record_id)
        observed_at = _clean(payload.get("start_time", "")) or None
        records.append(RawEvidenceRecord(evidence_id, spec.source_type, spec.source_id, spec.relative_path, record_id, observed_at, dict(payload), {"dataset_id": manifest.dataset_id, "dataset_timezone": manifest.timezone, "source_adapter": ADAPTER_VERSION, "normalization_version": SCHEMA_VERSION, "record_index": index}))
    return records, issues


def _parse_timestamp(value: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def _time_key(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _timestamp_with_duration(start_time: str, duration_ms: float) -> str:
    parsed = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    return (parsed + timedelta(milliseconds=duration_ms)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_optional_bool(value: str) -> bool | None:
    cleaned = _clean(value).casefold()
    if not cleaned:
        return None
    if cleaned in {"true", "1", "yes"}:
        return True
    if cleaned in {"false", "0", "no"}:
        return False
    raise ValueError(cleaned)


def _trace_cycle_span_ids(spans: Sequence[NormalizedTraceSpanEvidence]) -> set[str]:
    """Return spans participating in declared parent cycles; never infer links."""
    by_id = {item.span_id: item for item in spans}
    parents = {item.span_id: item.parent_span_id for item in spans if item.parent_span_id in by_id}
    colors: dict[str, int] = {}; stack: list[str] = []; cycle_ids: set[str] = set()
    def visit(span_id: str) -> None:
        colors[span_id] = 1; stack.append(span_id)
        parent = parents.get(span_id)
        if parent:
            if colors.get(parent) == 1:
                cycle_ids.update(stack[stack.index(parent):])
            elif colors.get(parent, 0) == 0:
                visit(parent)
        stack.pop(); colors[span_id] = 2
    for span_id in sorted(by_id):
        if colors.get(span_id, 0) == 0:
            visit(span_id)
    return cycle_ids


def process_dataset(manifest_path: Path) -> PreprocessingResult:
    """Parse a manifest package without modifying any input file."""
    manifest = load_manifest(manifest_path); base = manifest_path.parent; manifest_bytes = manifest_path.read_bytes()
    raw: list[RawEvidenceRecord] = []; entities: list[NormalizedEntityEvidence] = []; relations: list[NormalizedRelationEvidence] = []; events: list[NormalizedEventEvidence] = []; changes: list[NormalizedChangeEventEvidence] = []; metrics: list[NormalizedMetricEvidence] = []; traces: list[NormalizedTraceSpanEvidence] = []; terms: list[NormalizedSemanticTerm] = []; unresolved: list[PreprocessingIssue] = []; source_files: list[Mapping[str, Any]] = []
    inventory_ids: set[str] = set()
    for spec in sorted(manifest.sources, key=lambda item: (item.source_type != "service_inventory_csv", item.source_id)):
        path = base / spec.relative_path
        if not path.is_file():
            unresolved.append(PreprocessingIssue("SOURCE_NOT_FOUND", spec.source_id, spec.relative_path, "", "manifest source does not exist")); continue
        contents = path.read_bytes(); source_files.append({"source_id": spec.source_id, "source_type": spec.source_type, "relative_path": spec.relative_path, "sha256": _sha256_bytes(contents), "size": len(contents)})
        if spec.source_type == "service_inventory_csv":
            reader = csv.DictReader(contents.decode("utf-8-sig").splitlines())
            if not reader.fieldnames or not {"service_id", "name"}.issubset(reader.fieldnames):
                unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, "header", "service_id and name columns are required")); continue
            for index, payload in enumerate(reader, 2):
                service_id, label = _clean(payload.get("service_id", "")), _clean(payload.get("name", "")); record = _record(manifest, spec, spec.relative_path, service_id or str(index), payload, index); raw.append(record)
                if not service_id or not label:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, str(index), "service_id and name are required", record.evidence_id)); continue
                if service_id in inventory_ids:
                    unresolved.append(PreprocessingIssue("DUPLICATE_EXTERNAL_ID", spec.source_id, spec.relative_path, service_id, "duplicate service_id", record.evidence_id)); continue
                inventory_ids.add(service_id); entities.append(NormalizedEntityEvidence(record.evidence_id, spec.source_id, service_id, label, _clean(payload.get("description", "")) or None, {key: _clean(payload[key]) for key in ("owner", "environment") if _clean(payload.get(key, ""))}, _provenance(record)))
        elif spec.source_type == "dependency_jsonl":
            records, issues = _read_jsonl(path, manifest, spec); raw.extend(records); unresolved.extend(issues)
            for record in records:
                source_id, relation, target_id = (_clean(record.payload.get(key, "")) for key in ("source_id", "relation", "target_id"))
                if not source_id or not relation or not target_id:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, record.source_record_id, "source_id, relation, target_id are required", record.evidence_id)); continue
                if relation not in {"calls", "depends_on", "reads_from", "writes_to", "publishes_to", "consumes_from"}:
                    unresolved.append(PreprocessingIssue("MALFORMED_RECORD", spec.source_id, spec.relative_path, record.source_record_id, f"unsupported relation {relation}", record.evidence_id)); continue
                resolved = source_id in inventory_ids and target_id in inventory_ids
                relations.append(NormalizedRelationEvidence(record.evidence_id, spec.source_id, source_id, relation, target_id, "RESOLVED_EXACT_ID" if resolved else "UNRESOLVED_REFERENCE", _provenance(record)))
                if not resolved:
                    unresolved.append(PreprocessingIssue("UNKNOWN_ENTITY_REFERENCE", spec.source_id, spec.relative_path, record.source_record_id, f"{source_id} -> {target_id}", record.evidence_id))
        elif spec.source_type == "log_jsonl":
            records, issues = _read_jsonl(path, manifest, spec); raw.extend(records); unresolved.extend(issues)
            for record in records:
                timestamp, service_id, event = (_clean(record.payload.get(key, "")) for key in ("timestamp", "service_id", "event"))
                if not timestamp or not service_id or not event:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, record.source_record_id, "timestamp, service_id, event are required", record.evidence_id)); continue
                normalized_time = _parse_timestamp(timestamp)
                if not normalized_time:
                    unresolved.append(PreprocessingIssue("INVALID_TIMESTAMP", spec.source_id, spec.relative_path, record.source_record_id, timestamp, record.evidence_id)); continue
                correlation = "RESOLVED_EXACT_ID" if service_id in inventory_ids else "UNRESOLVED_REFERENCE"
                events.append(NormalizedEventEvidence(record.evidence_id, spec.source_id, service_id, event, normalized_time, timestamp, _clean(record.payload.get("severity", "")) or None, correlation, {key: value for key, value in record.payload.items() if key in {"trace_id", "request_id", "host_id", "pod_id", "attributes"}}, _provenance(record)))
                if correlation != "RESOLVED_EXACT_ID": unresolved.append(PreprocessingIssue("UNKNOWN_ENTITY_REFERENCE", spec.source_id, spec.relative_path, record.source_record_id, service_id, record.evidence_id))
        elif spec.source_type == "deployment_change_csv":
            reader = csv.DictReader(contents.decode("utf-8-sig").splitlines())
            required = {"change_id", "timestamp", "service_id", "change_type"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, "header", "change_id, timestamp, service_id, change_type columns are required")); continue
            seen_changes: set[str] = set()
            for index, payload in enumerate(reader, 2):
                change_id, timestamp, service_id, declared_type = (_clean(payload.get(key, "")) for key in ("change_id", "timestamp", "service_id", "change_type")); record = _record(manifest, spec, spec.relative_path, change_id or str(index), payload, index); raw.append(record)
                if not change_id or not timestamp or not service_id or not declared_type:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, str(index), "change_id, timestamp, service_id, change_type are required", record.evidence_id)); continue
                if change_id in seen_changes:
                    unresolved.append(PreprocessingIssue("DUPLICATE_EXTERNAL_ID", spec.source_id, spec.relative_path, change_id, "duplicate change_id", record.evidence_id)); continue
                seen_changes.add(change_id); change_type = CHANGE_TYPE_ALIASES.get(declared_type.replace("-", "_").replace(" ", "_").upper())
                if change_type not in CHANGE_TYPES:
                    unresolved.append(PreprocessingIssue("UNKNOWN_DECLARED_CHANGE_TYPE", spec.source_id, spec.relative_path, change_id, declared_type, record.evidence_id)); continue
                normalized_time = _parse_timestamp(timestamp)
                if not normalized_time:
                    unresolved.append(PreprocessingIssue("INVALID_TIMESTAMP", spec.source_id, spec.relative_path, change_id, timestamp, record.evidence_id)); continue
                correlation = "RESOLVED_EXACT_ID" if service_id in inventory_ids else "UNRESOLVED_CHANGE_TARGET"
                if correlation != "RESOLVED_EXACT_ID": unresolved.append(PreprocessingIssue("UNRESOLVED_CHANGE_TARGET", spec.source_id, spec.relative_path, change_id, service_id, record.evidence_id))
                changes.append(NormalizedChangeEventEvidence(record.evidence_id, spec.source_id, change_id, service_id, change_type, normalized_time, timestamp, _clean(payload.get("version_before", "")) or None, _clean(payload.get("version_after", "")) or None, _clean(payload.get("config_key", "")) or None, _clean(payload.get("config_before", "")) or None, _clean(payload.get("config_after", "")) or None, _clean(payload.get("description", "")) or None, _clean(payload.get("environment", "")) or None, _clean(payload.get("rollback_of", "")) or None, None, correlation, {key: value for key, value in payload.items() if key in {"actor", "deployment_id", "commit_id", "attributes"}}, _provenance(record)))
        elif spec.source_type == "metric_observation_csv":
            reader = csv.DictReader(contents.decode("utf-8-sig").splitlines())
            required = {"metric_id", "timestamp", "service_id", "metric_name", "value", "unit", "metric_kind"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, "header", "metric_id, timestamp, service_id, metric_name, value, unit, metric_kind columns are required")); continue
            seen_metrics: set[str] = set()
            for index, payload in enumerate(reader, 2):
                metric_id, timestamp, service_id, metric_name, value_text, unit, declared_kind = (_clean(payload.get(key, "")) for key in ("metric_id", "timestamp", "service_id", "metric_name", "value", "unit", "metric_kind"))
                record = _record(manifest, spec, spec.relative_path, metric_id or str(index), payload, index); raw.append(record)
                if not metric_id or not timestamp or not service_id or not metric_name or not value_text or not unit or not declared_kind:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, str(index), "metric_id, timestamp, service_id, metric_name, value, unit, metric_kind are required", record.evidence_id)); continue
                if metric_id in seen_metrics:
                    unresolved.append(PreprocessingIssue("DUPLICATE_EXTERNAL_ID", spec.source_id, spec.relative_path, metric_id, "duplicate metric_id", record.evidence_id)); continue
                seen_metrics.add(metric_id)
                normalized_time = _parse_timestamp(timestamp)
                if not normalized_time:
                    unresolved.append(PreprocessingIssue("INVALID_TIMESTAMP", spec.source_id, spec.relative_path, metric_id, timestamp, record.evidence_id)); continue
                try:
                    numeric_value = float(Decimal(value_text))
                except (InvalidOperation, ValueError):
                    unresolved.append(PreprocessingIssue("INVALID_METRIC_VALUE", spec.source_id, spec.relative_path, metric_id, value_text, record.evidence_id)); continue
                if not isfinite(numeric_value):
                    unresolved.append(PreprocessingIssue("INVALID_METRIC_VALUE", spec.source_id, spec.relative_path, metric_id, value_text, record.evidence_id)); continue
                metric_kind = METRIC_KIND_ALIASES.get(declared_kind.replace("-", "_").replace(" ", "_").upper())
                if metric_kind not in METRIC_KINDS:
                    unresolved.append(PreprocessingIssue("UNSUPPORTED_METRIC_KIND", spec.source_id, spec.relative_path, metric_id, declared_kind, record.evidence_id)); continue
                if unit not in SUPPORTED_METRIC_UNITS:
                    unresolved.append(PreprocessingIssue("UNSUPPORTED_METRIC_UNIT", spec.source_id, spec.relative_path, metric_id, unit, record.evidence_id)); continue
                aggregation = _clean(payload.get("aggregation", "")) or None
                correlation = "RESOLVED_EXACT_ID" if service_id in inventory_ids else "UNRESOLVED_METRIC_TARGET"
                if correlation != "RESOLVED_EXACT_ID":
                    unresolved.append(PreprocessingIssue("UNRESOLVED_METRIC_TARGET", spec.source_id, spec.relative_path, metric_id, service_id, record.evidence_id))
                metrics.append(NormalizedMetricEvidence(record.evidence_id, spec.source_id, metric_id, service_id, metric_name, numeric_value, unit, unit, metric_kind, aggregation, _clean(payload.get("sampling_interval", "")) or None, _clean(payload.get("window_start", "")) or None, _clean(payload.get("window_end", "")) or None, _clean(payload.get("source_metric_name", "")) or None, _clean(payload.get("environment", "")) or None, _metric_series_key(service_id, metric_name, unit, metric_kind, aggregation), normalized_time, timestamp, correlation, {key: value for key, value in payload.items() if key in {"attributes"}}, _provenance(record)))
        elif spec.source_type == "trace_span_jsonl":
            records, issues = _read_trace_jsonl(path, manifest, spec); raw.extend(records); unresolved.extend(issues)
            seen_spans: set[tuple[str, str]] = set()
            for record in records:
                trace_id, span_id, service_id, start_time = (_clean(record.payload.get(key, "")) for key in ("trace_id", "span_id", "service_id", "start_time"))
                if not trace_id or not span_id or not service_id or not start_time:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, str(record.provenance["record_index"]), "trace_id, span_id, service_id, start_time are required", record.evidence_id)); continue
                key = (trace_id, span_id)
                if key in seen_spans:
                    unresolved.append(PreprocessingIssue("DUPLICATE_SPAN_ID", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", "duplicate span_id within trace", record.evidence_id)); continue
                seen_spans.add(key)
                normalized_start = _parse_timestamp(start_time)
                if not normalized_start:
                    unresolved.append(PreprocessingIssue("INVALID_TIMESTAMP", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", start_time, record.evidence_id)); continue
                duration_text, end_text = _clean(record.payload.get("duration_ms", "")), _clean(record.payload.get("end_time", ""))
                duration: float | None = None
                if duration_text:
                    try:
                        duration = float(Decimal(duration_text))
                    except (InvalidOperation, ValueError):
                        unresolved.append(PreprocessingIssue("INVALID_SPAN_DURATION", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", duration_text, record.evidence_id)); continue
                    if not isfinite(duration) or duration < 0:
                        unresolved.append(PreprocessingIssue("INVALID_SPAN_DURATION", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", duration_text, record.evidence_id)); continue
                declared_end = _parse_timestamp(end_text) if end_text else None
                if end_text and not declared_end:
                    unresolved.append(PreprocessingIssue("INVALID_SPAN_END_TIME", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", end_text, record.evidence_id)); continue
                derived_end = _timestamp_with_duration(normalized_start, duration) if duration is not None else None
                if declared_end and derived_end and declared_end != derived_end:
                    unresolved.append(PreprocessingIssue("SPAN_TIME_CONFLICT", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", f"{declared_end} != {derived_end}", record.evidence_id)); continue
                end_time, end_source = (declared_end, "DECLARED_END_TIME") if declared_end else (derived_end, "DERIVED_FROM_DURATION") if derived_end else (normalized_start, "START_TIME_ONLY")
                span_kind_text, status_text = _clean(record.payload.get("kind", "")), _clean(record.payload.get("status", ""))
                span_kind = span_kind_text.replace("-", "_").replace(" ", "_").upper() if span_kind_text else None
                status = status_text.replace("-", "_").replace(" ", "_").upper() if status_text else None
                if span_kind and span_kind not in TRACE_SPAN_KINDS:
                    span_kind = "OTHER_DECLARED"
                if status and status not in TRACE_STATUSES:
                    status = "OTHER_DECLARED"
                try:
                    sampled = _parse_optional_bool(str(record.payload.get("sampled", "")))
                except ValueError:
                    unresolved.append(PreprocessingIssue("INVALID_SAMPLED_FLAG", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", str(record.payload.get("sampled")), record.evidence_id)); continue
                correlation = "RESOLVED_EXACT_ID" if service_id in inventory_ids else "UNRESOLVED_TRACE_ENTITY"
                if correlation != "RESOLVED_EXACT_ID":
                    unresolved.append(PreprocessingIssue("UNRESOLVED_TRACE_ENTITY", spec.source_id, spec.relative_path, f"{trace_id}:{span_id}", service_id, record.evidence_id))
                parent_span_id = _clean(record.payload.get("parent_span_id", "")) or None
                traces.append(NormalizedTraceSpanEvidence(record.evidence_id, spec.source_id, trace_id, span_id, parent_span_id, service_id, _clean(record.payload.get("operation", "")) or None, normalized_start, start_time, end_time, declared_end, duration, end_source, status, span_kind, sampled, _clean(record.payload.get("error_code", "")) or None, correlation, "ROOT" if not parent_span_id else "PENDING_PARENT_RESOLUTION", {"attributes_present": bool(record.payload.get("attributes"))}, _provenance(record)))
        else:
            try:
                payload = yaml.safe_load(contents.decode("utf-8")) or {}
                rows = payload.get("terms", []) if isinstance(payload, dict) else []
            except yaml.YAMLError as exc:
                unresolved.append(PreprocessingIssue("MALFORMED_RECORD", spec.source_id, spec.relative_path, "", str(exc))); continue
            if not isinstance(rows, list):
                unresolved.append(PreprocessingIssue("MALFORMED_RECORD", spec.source_id, spec.relative_path, "terms", "terms must be a list")); continue
            seen_terms: set[str] = set()
            for index, payload in enumerate(rows, 1):
                if not isinstance(payload, dict):
                    unresolved.append(PreprocessingIssue("MALFORMED_RECORD", spec.source_id, spec.relative_path, str(index), "term must be a mapping")); continue
                term_id, label = _clean(payload.get("id", "")), _clean(payload.get("label", "")); record = _record(manifest, spec, spec.relative_path, term_id or str(index), payload, index); raw.append(record)
                if not term_id or not label:
                    unresolved.append(PreprocessingIssue("MISSING_REQUIRED_FIELD", spec.source_id, spec.relative_path, str(index), "id and label are required", record.evidence_id)); continue
                if term_id in seen_terms:
                    unresolved.append(PreprocessingIssue("DUPLICATE_EXTERNAL_ID", spec.source_id, spec.relative_path, term_id, "duplicate glossary id", record.evidence_id)); continue
                seen_terms.add(term_id); aliases = tuple(sorted({_clean(value) for value in payload.get("aliases", []) if _clean(value)})) if isinstance(payload.get("aliases", []), list) else ()
                terms.append(NormalizedSemanticTerm(record.evidence_id, spec.source_id, term_id, label, _clean(payload.get("definition", "")) or None, aliases, _provenance(record)))
    change_ids = {item.change_id for item in changes}; finalized_changes = []
    for item in changes:
        rollback_status = "RESOLVED_CHANGE_REFERENCE" if item.rollback_of and item.rollback_of in change_ids else "UNRESOLVED_CHANGE_REFERENCE" if item.rollback_of else None
        if rollback_status == "UNRESOLVED_CHANGE_REFERENCE": unresolved.append(PreprocessingIssue("UNRESOLVED_CHANGE_REFERENCE", item.source_system, str(item.provenance["source_file"]), item.change_id, str(item.rollback_of), item.evidence_id))
        finalized_changes.append(replace(item, rollback_status=rollback_status))
    metric_units: dict[tuple[str, str, str, str | None], set[str]] = {}
    for metric in metrics:
        metric_units.setdefault((metric.service_external_id, metric.metric_name, metric.metric_kind, metric.aggregation), set()).add(metric.unit)
    for metric in metrics:
        units = metric_units[(metric.service_external_id, metric.metric_name, metric.metric_kind, metric.aggregation)]
        if len(units) > 1:
            unresolved.append(PreprocessingIssue("METRIC_UNIT_CONFLICT", metric.source_system, str(metric.provenance["source_file"]), metric.metric_id, ",".join(sorted(units)), metric.evidence_id))
    finalized_traces: list[NormalizedTraceSpanEvidence] = []
    for trace_id in sorted({item.trace_id for item in traces}):
        group = [item for item in traces if item.trace_id == trace_id]
        by_span_id = {item.span_id: item for item in group}
        cycle_ids = _trace_cycle_span_ids(group)
        for item in group:
            if item.span_id in cycle_ids:
                status = "PARENT_CYCLE"
                unresolved.append(PreprocessingIssue("TRACE_PARENT_CYCLE", item.source_system, str(item.provenance["source_file"]), f"{item.trace_id}:{item.span_id}", "declared parent cycle", item.evidence_id))
            elif not item.parent_span_id:
                status = "ROOT"
            elif item.parent_span_id not in by_span_id:
                status = "UNRESOLVED_PARENT"
                unresolved.append(PreprocessingIssue("UNRESOLVED_PARENT_SPAN", item.source_system, str(item.provenance["source_file"]), f"{item.trace_id}:{item.span_id}", item.parent_span_id, item.evidence_id))
            else:
                status = "RESOLVED_PARENT"
            finalized_traces.append(replace(item, parent_resolution_status=status))
    return PreprocessingResult(manifest, _sha256_bytes(manifest_bytes), tuple(sorted(source_files, key=lambda item: item["source_id"])), tuple(raw), tuple(sorted(entities, key=lambda item: item.evidence_id)), tuple(sorted(relations, key=lambda item: item.evidence_id)), tuple(sorted(events, key=lambda item: item.evidence_id)), tuple(sorted(finalized_changes, key=lambda item: item.evidence_id)), tuple(sorted(terms, key=lambda item: item.evidence_id)), tuple(sorted(unresolved, key=lambda item: (item.source_file, item.source_record_id, item.status))), tuple(sorted(metrics, key=lambda item: (item.service_external_id, item.series_key, item.observed_at, item.evidence_id)),), tuple(sorted(finalized_traces, key=lambda item: (item.trace_id, _time_key(item.observed_at), item.span_id, item.evidence_id))))


def write_artifacts(result: PreprocessingResult, output: Path) -> Mapping[str, Any]:
    """Write deterministic generated artifacts outside the source package."""
    output.mkdir(parents=True, exist_ok=True)
    from .evidence_schema import EvidenceSchemaInducer, induction_diagnostics
    induced = EvidenceSchemaInducer().induce(result)
    files = {"raw_evidence.jsonl": result.raw_records, "entities.jsonl": result.entities, "relations.jsonl": result.relations, "events.jsonl": result.events, "semantic_terms.jsonl": result.semantic_terms, "unresolved.jsonl": result.unresolved}
    if any(spec.source_type == "deployment_change_csv" for spec in result.manifest.sources): files["changes.jsonl"] = result.changes
    if any(spec.source_type == "metric_observation_csv" for spec in result.manifest.sources): files["metrics.jsonl"] = result.metrics
    if any(spec.source_type == "trace_span_jsonl" for spec in result.manifest.sources): files["traces.jsonl"] = result.traces
    hashes = {}
    for name, rows in files.items():
        text = "".join(json.dumps(_as_json(row), sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
        (output / name).write_text(text, encoding="utf-8"); hashes[name] = _sha256_bytes(text.encode("utf-8"))
    candidate_text = "".join(json.dumps(item.artifact(), sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for item in induced)
    (output / "schema_candidates.jsonl").write_text(candidate_text, encoding="utf-8"); hashes["schema_candidates.jsonl"] = _sha256_bytes(candidate_text.encode("utf-8"))
    envelope = {"schema_version": SCHEMA_VERSION, "dataset_id": result.manifest.dataset_id, "concepts": [{"id": term.external_id, "label": term.label, "definition": term.definition or "", "aliases": list(term.aliases), "type_hint": "glossary_term", "relations": [], "preprocessing_provenance": term.provenance} for term in result.semantic_terms]}
    envelope_text = json.dumps(envelope, sort_keys=True, ensure_ascii=False, indent=2) + "\n"; (output / "semantic_envelope.json").write_text(envelope_text, encoding="utf-8"); hashes["semantic_envelope.json"] = _sha256_bytes(envelope_text.encode("utf-8"))
    provenance = {"schema_version": SCHEMA_VERSION, "dataset_id": result.manifest.dataset_id, "manifest_path_identity": result.manifest_hash, "trace": "normalized record -> raw_evidence_id -> source_file -> dataset manifest", "source_files": result.source_files}
    provenance_text = json.dumps(provenance, sort_keys=True, ensure_ascii=False, indent=2) + "\n"; (output / "provenance.json").write_text(provenance_text, encoding="utf-8"); hashes["provenance.json"] = _sha256_bytes(provenance_text.encode("utf-8"))
    raw_changes = sum(item.source_type == "deployment_change_csv" for item in result.raw_records)
    change_report = {"raw_change_records": raw_changes, "valid_changes": len(result.changes), "invalid_changes": raw_changes - len(result.changes), "resolved_change_targets": sum(item.correlation_status == "RESOLVED_EXACT_ID" for item in result.changes), "unresolved_change_targets": sum(item.correlation_status != "RESOLVED_EXACT_ID" for item in result.changes), "change_types": {kind: sum(item.change_type == kind for item in result.changes) for kind in sorted(CHANGE_TYPES) if any(item.change_type == kind for item in result.changes)}, "rollback_references": sum(bool(item.rollback_of) for item in result.changes), "invalid_rollback_references": sum(item.rollback_status == "UNRESOLVED_CHANGE_REFERENCE" for item in result.changes)}
    metric_report = {"raw_metric_records": sum(item.source_type == "metric_observation_csv" for item in result.raw_records), "valid_metric_observations": len(result.metrics), "invalid_metric_observations": sum(item.source_type == "metric_observation_csv" for item in result.raw_records) - len(result.metrics), "resolved_metric_targets": sum(item.correlation_status == "RESOLVED_EXACT_ID" for item in result.metrics), "unresolved_metric_targets": sum(item.correlation_status != "RESOLVED_EXACT_ID" for item in result.metrics), "metric_series_count": len({item.series_key for item in result.metrics}), "gauge_count": sum(item.metric_kind == "GAUGE" for item in result.metrics), "counter_count": sum(item.metric_kind == "COUNTER" for item in result.metrics), "unit_distribution": {unit: sum(item.unit == unit for item in result.metrics) for unit in sorted({item.unit for item in result.metrics})}, "unit_conflicts": sum(item.status == "METRIC_UNIT_CONFLICT" for item in result.unresolved), "aggregation_distribution": {str(aggregation or "UNSPECIFIED"): sum(item.aggregation == aggregation for item in result.metrics) for aggregation in sorted({item.aggregation for item in result.metrics}, key=lambda item: item or "")}, "sampling_metadata_coverage": sum(item.sampling_interval is not None for item in result.metrics)}
    trace_groups = {trace_id: [item for item in result.traces if item.trace_id == trace_id] for trace_id in sorted({item.trace_id for item in result.traces})}
    trace_report = {"raw_span_records": sum(item.source_type == "trace_span_jsonl" for item in result.raw_records), "valid_spans": len(result.traces), "invalid_spans": sum(item.source_type == "trace_span_jsonl" for item in result.raw_records) - len(result.traces), "resolved_services": sum(item.correlation_status == "RESOLVED_EXACT_ID" for item in result.traces), "unresolved_services": sum(item.correlation_status != "RESOLVED_EXACT_ID" for item in result.traces), "trace_count": len(trace_groups), "root_span_count": sum(item.parent_resolution_status == "ROOT" for item in result.traces), "multi_root_traces": sum(sum(item.parent_resolution_status == "ROOT" for item in rows) > 1 for rows in trace_groups.values()), "missing_parent_spans": sum(item.parent_resolution_status == "UNRESOLVED_PARENT" for item in result.traces), "partial_traces": sum(any(item.parent_resolution_status in {"UNRESOLVED_PARENT", "PARENT_CYCLE"} or item.correlation_status != "RESOLVED_EXACT_ID" for item in rows) for rows in trace_groups.values()), "error_spans": sum(item.status == "ERROR" for item in result.traces), "ok_spans": sum(item.status == "OK" for item in result.traces), "cross_service_parent_child_edges": sum(item.parent_resolution_status == "RESOLVED_PARENT" and next(parent for parent in trace_groups[item.trace_id] if parent.span_id == item.parent_span_id).service_external_id != item.service_external_id for item in result.traces), "same_service_parent_child_edges": sum(item.parent_resolution_status == "RESOLVED_PARENT" and next(parent for parent in trace_groups[item.trace_id] if parent.span_id == item.parent_span_id).service_external_id == item.service_external_id for item in result.traces)}
    report = {"schema_version": SCHEMA_VERSION, "adapter_version": ADAPTER_VERSION, "dataset_id": result.manifest.dataset_id, "environment": result.manifest.environment, "declared_timezone": result.manifest.timezone, "manifest_sha256": result.manifest_hash, "source_files": result.source_files, "counts": {"raw_records": len(result.raw_records), "entities": len(result.entities), "relations": len(result.relations), "events": len(result.events), "changes": len(result.changes), "metrics": len(result.metrics), "traces": len(result.traces), "semantic_terms": len(result.semantic_terms), "unresolved": len(result.unresolved)}, "change_diagnostics": change_report, "metric_diagnostics": metric_report, "trace_diagnostics": trace_report, "schema_induction": induction_diagnostics(induced, result), "artifacts": hashes}
    report_text = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n"; (output / "manifest.json").write_text(report_text, encoding="utf-8"); hashes["manifest.json"] = _sha256_bytes(report_text.encode("utf-8")); return report


def bridge_to_existing_core(output: Path, domain: str) -> tuple[SemanticCandidateGraph, list[Any]]:
    """Use the existing JSON extractor and schema inducer; glossary terms only enter TBox induction."""
    envelope = output / "semantic_envelope.json"
    if not envelope.is_file():
        raise PreprocessingError("SOURCE_NOT_FOUND: semantic_envelope.json")
    graph = StructuredExtractor().extract(envelope, domain, preprocess(envelope, "preprocessed_semantic_envelope"))
    provenance = Provenance(input_domain=domain, model="preprocessing-envelope-adapter", model_version=ADAPTER_VERSION)
    return graph, DeterministicSchemaInducer().induce(graph.entities, domain, provenance)


def changes_for_entity(changes: Sequence[NormalizedChangeEventEvidence], entity_id: str, start_time: str, end_time: str) -> tuple[NormalizedChangeEventEvidence, ...]:
    """Return exact-ID change evidence in the inclusive UTC interval [start, end]."""
    start, end = _parse_timestamp(start_time), _parse_timestamp(end_time)
    if not start or not end or start > end: raise PreprocessingError("INVALID_TIMESTAMP: interval requires ordered timezone-aware timestamps")
    return tuple(sorted((item for item in changes if item.target_external_id == entity_id and start <= item.observed_at <= end), key=lambda item: (item.observed_at, item.evidence_id)))


def metrics_for_entity(metrics: Sequence[NormalizedMetricEvidence], entity_id: str, start_time: str, end_time: str) -> tuple[NormalizedMetricEvidence, ...]:
    """Return exact-ID metric observations in the inclusive UTC interval [start, end]."""
    start, end = _parse_timestamp(start_time), _parse_timestamp(end_time)
    if not start or not end or start > end: raise PreprocessingError("INVALID_TIMESTAMP: interval requires ordered timezone-aware timestamps")
    return tuple(sorted((item for item in metrics if item.service_external_id == entity_id and start <= item.observed_at <= end), key=lambda item: (item.service_external_id, item.series_key, item.observed_at, item.evidence_id)))


def trace_spans_for_entity(traces: Sequence[NormalizedTraceSpanEvidence], entity_id: str, start_time: str, end_time: str) -> tuple[NormalizedTraceSpanEvidence, ...]:
    """Return exact-ID span observations overlapping the inclusive UTC interval."""
    start, end = _parse_timestamp(start_time), _parse_timestamp(end_time)
    if not start or not end or start > end: raise PreprocessingError("INVALID_TIMESTAMP: interval requires ordered timezone-aware timestamps")
    return tuple(sorted((item for item in traces if item.service_external_id == entity_id and _time_key(item.observed_at) <= _time_key(end) and _time_key(item.end_time) >= _time_key(start)), key=lambda item: (item.trace_id, _time_key(item.observed_at), item.span_id, item.evidence_id)))


def trace_by_id(traces: Sequence[NormalizedTraceSpanEvidence], trace_id: str) -> tuple[NormalizedTraceSpanEvidence, ...]:
    """Return one trace's spans in deterministic start/span order."""
    return tuple(sorted((item for item in traces if item.trace_id == trace_id), key=lambda item: (_time_key(item.observed_at), item.span_id, item.evidence_id)))
