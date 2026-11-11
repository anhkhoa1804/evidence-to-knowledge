"""Research-only RCAEval qualification and frozen-candidate evaluation.

This module is deliberately outside production preprocessing.  It adapts
external benchmark telemetry into the existing immutable evidence contracts,
then invokes the frozen Phase 2.10 graph and candidate generator unchanged.
Ground-truth labels are represented separately and are never supplied to the
adapter, context assembler, graph, or candidate generator.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .incident_evidence_graph import IncidentEvidenceGraph, build_incident_evidence_graph, generate_cause_candidates
from .operational_context import IncidentWindow, TopologyScope, assemble_context, snapshot_for
from .raw_preprocessing import (
    DatasetManifest,
    NormalizedEntityEvidence,
    NormalizedEventEvidence,
    NormalizedMetricEvidence,
    NormalizedTraceSpanEvidence,
    PreprocessingResult,
    SourceSpec,
)
from .trace_evidence import execution_graphs
from .scalable_evidence import IncidentEvidenceStore, ResourceConfiguration, generate_frozen_candidates_from_store

RCAEVAL_ADAPTER_VERSION = "rcaeval_research_adapter_v1"
RCAEVAL_EVALUATION_VERSION = "v3_phase2_10e_candidate_coverage_v1"
ORACLE_WINDOW = "ORACLE_WINDOW"
PRE_WINDOW_SECONDS = 300
POST_WINDOW_SECONDS = 600
UNIT_UNSPECIFIED = "UNIT_UNSPECIFIED"
METRIC_KIND_UNSPECIFIED = "METRIC_KIND_UNSPECIFIED"


class RCAEvalQualificationError(ValueError):
    """Raised when external metadata or telemetry cannot be adapted honestly."""


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _id(kind: str, *parts: object) -> str:
    return f"rcaeval-{kind}-{_sha([str(item) for item in parts])[:24]}"


def _text(value: object | None) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").split())


def _utc(value: object) -> str:
    numeric = _epoch_seconds(value)
    if numeric is not None:
        return datetime.fromtimestamp(numeric, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    text = _text(value)
    if text.isdigit():
        return _utc(int(text))
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RCAEvalQualificationError(f"RCAEVAL_TIMESTAMP_TIMEZONE_UNSPECIFIED: {value}")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _epoch_seconds(value: object) -> float | None:
    if isinstance(value, (int, float)):
        numeric = float(value)
    else:
        text = _text(value)
        if not text.isdigit():
            return None
        numeric = float(text)
    # RCAEval metrics use seconds while traces expose epoch microseconds.
    if numeric >= 10**14:
        numeric /= 1_000_000
    elif numeric >= 10**11:
        numeric /= 1_000
    return numeric


def normalize_service_id(value: object) -> str | None:
    """Use only documented syntactic normalization, never lexical matching."""
    item = _text(value).casefold()
    if not item:
        return None
    for prefix in ("service/", "services/", "default/"):
        if item.startswith(prefix):
            item = item[len(prefix):]
    for suffix in (".svc.cluster.local", ".svc"):
        if item.endswith(suffix):
            item = item[:-len(suffix)]
    return item or None


@dataclass(frozen=True)
class RCAEvalCase:
    """Operational case metadata; deliberately excludes root-cause labels."""

    case_id: str
    dataset: str
    system: str
    injection_time: int
    time_start: int | None = None
    time_end: int | None = None
    has_logs: bool = False
    has_traces: bool = False


@dataclass(frozen=True)
class RCAEvalGroundTruth:
    """Evaluation-only benchmark labels; never accepted by the adapter."""

    case_id: str
    subject_type: str
    root_cause_service: str | None
    fault_type: str | None


@dataclass(frozen=True)
class AdaptedRCAEvalCase:
    case: RCAEvalCase
    preprocessing: PreprocessingResult
    incident: IncidentWindow
    window_mode: str
    window_rationale: str


@dataclass(frozen=True)
class CandidateCoverage:
    case_id: str
    status: str
    candidate_count: int
    eligible_service_count: int
    ground_truth_service_id: str | None
    covered: bool | None
    candidate_subject_ids: tuple[str, ...]
    generation_rules: tuple[str, ...]
    graph_id: str | None = None

    @property
    def reduction_ratio(self) -> float | None:
        return self.candidate_count / self.eligible_service_count if self.eligible_service_count else None


def split_index_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[tuple[RCAEvalCase, ...], tuple[RCAEvalGroundTruth, ...]]:
    """Split an index into operational metadata and evaluation-only labels."""
    cases: list[RCAEvalCase] = []
    truth: list[RCAEvalGroundTruth] = []
    for row in rows:
        case_id = _text(row.get("case"))
        if not case_id:
            raise RCAEvalQualificationError("RCAEVAL_INDEX_CASE_ID_REQUIRED")
        injection = row.get("inject_time")
        if injection is None:
            raise RCAEvalQualificationError(f"RCAEVAL_INDEX_INJECTION_TIME_REQUIRED: {case_id}")
        cases.append(RCAEvalCase(
            case_id=case_id, dataset=_text(row.get("dataset")), system=_text(row.get("system")),
            injection_time=int(injection), time_start=int(row["time_start"]) if row.get("time_start") is not None else None,
            time_end=int(row["time_end"]) if row.get("time_end") is not None else None,
            has_logs=bool(row.get("has_logs")), has_traces=bool(row.get("has_traces")),
        ))
        truth.append(RCAEvalGroundTruth(
            case_id=case_id, subject_type="SERVICE", root_cause_service=normalize_service_id(row.get("root_cause_service")),
            fault_type=_text(row.get("fault")).upper() or None,
        ))
    return tuple(sorted(cases, key=lambda item: item.case_id)), tuple(sorted(truth, key=lambda item: item.case_id))


def load_case_index(path: Path) -> tuple[tuple[RCAEvalCase, ...], tuple[RCAEvalGroundTruth, ...]]:
    """Load cases.parquet through an optional research dependency."""
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RCAEvalQualificationError("RCAEVAL_PARQUET_READER_UNAVAILABLE: install pyarrow in the research environment") from exc
    return split_index_rows(parquet.read_table(path).to_pylist())


def deterministic_pilot(case_rows: Sequence[RCAEvalCase], truth_rows: Sequence[RCAEvalGroundTruth]) -> tuple[str, ...]:
    """Select two repetitions per fault without looking at telemetry or coverage."""
    truth = {item.case_id: item for item in truth_rows}
    grouped: dict[str, list[RCAEvalCase]] = {}
    for case in case_rows:
        if case.dataset == "RE2-OB":
            grouped.setdefault(truth[case.case_id].fault_type or "UNKNOWN", []).append(case)
    selected: list[str] = []
    for fault_index, fault in enumerate(sorted(grouped)):
        rows = sorted(grouped[fault], key=lambda item: (truth[item.case_id].root_cause_service or "", item.case_id))
        services = sorted({truth[item.case_id].root_cause_service or "" for item in rows})
        if len(services) < 2:
            raise RCAEvalQualificationError(f"RCAEVAL_PILOT_STRATIFICATION_IMPOSSIBLE: {fault}")
        for service in (services[(2 * fault_index) % len(services)], services[(2 * fault_index + 2) % len(services)]):
            selected.append(next(item.case_id for item in rows if truth[item.case_id].root_cause_service == service and item.case_id.endswith("_1")))
    return tuple(sorted(selected))


def _rows(path: Path) -> list[Mapping[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RCAEvalQualificationError("RCAEVAL_PARQUET_READER_UNAVAILABLE: install pyarrow in the research environment") from exc
    return list(parquet.read_table(path).to_pylist())


def _field(row: Mapping[str, Any], *names: str) -> object | None:
    lowered = {str(key).casefold(): value for key, value in row.items()}
    for name in names:
        if name.casefold() in lowered and lowered[name.casefold()] is not None:
            return lowered[name.casefold()]
    return None


def _metric_service_and_name(column: str) -> tuple[str | None, str]:
    value = _text(column)
    if "_" not in value:
        return None, value
    service, name = value.split("_", 1)
    return normalize_service_id(service), name


def _trace_status(value: object | None) -> str | None:
    """Map the OpenTelemetry numeric status encoding without inferring errors."""
    if value is None or _text(value) == "":
        return None
    try:
        return {0: "UNSET", 1: "OK", 2: "ERROR"}[int(value)]
    except (TypeError, ValueError, KeyError):
        return _text(value).upper() or None


def adapt_case_rows(
    case: RCAEvalCase,
    metric_rows: Sequence[Mapping[str, Any]],
    log_rows: Sequence[Mapping[str, Any]],
    trace_rows: Sequence[Mapping[str, Any]],
) -> AdaptedRCAEvalCase:
    """Adapt supplied telemetry rows without accepting any ground-truth argument."""
    metrics: list[NormalizedMetricEvidence] = []
    events: list[NormalizedEventEvidence] = []
    traces: list[NormalizedTraceSpanEvidence] = []
    observed_services: set[str] = set()
    window_start = case.injection_time - PRE_WINDOW_SECONDS
    window_end = case.injection_time + POST_WINDOW_SECONDS
    for row_number, row in enumerate(metric_rows, 1):
        time_value = _field(row, "time", "timestamp")
        time_seconds = _epoch_seconds(time_value)
        if time_seconds is not None and not window_start <= time_seconds <= window_end:
            continue
        timestamp = _utc(time_value)
        for column, value in sorted(row.items()):
            if str(column).casefold() in {"time", "timestamp"} or value is None:
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            service, name = _metric_service_and_name(str(column))
            if not service:
                continue
            observed_services.add(service)
            evidence_id = _id("metric", case.case_id, row_number, column, timestamp)
            provenance = MappingProxyType({"adapter_version": RCAEVAL_ADAPTER_VERSION, "source_file": "metrics.parquet", "source_record_id": str(row_number), "raw_evidence_id": evidence_id, "external_case_id": case.case_id})
            metrics.append(NormalizedMetricEvidence(evidence_id, "RCAEVAL_RESEARCH", evidence_id, service, name, numeric, UNIT_UNSPECIFIED, UNIT_UNSPECIFIED, METRIC_KIND_UNSPECIFIED, None, None, None, None, str(column), None, _id("series", service, name), timestamp, str(_field(row, "time", "timestamp")), "RESOLVED_EXACT_ID", MappingProxyType({}), provenance))
    for row_number, row in enumerate(log_rows, 1):
        service = normalize_service_id(_field(row, "service", "service_name", "container", "container_name"))
        timestamp_value = _field(row, "time", "timestamp", "ts")
        message = _text(_field(row, "message", "log", "content"))
        if not service or timestamp_value is None:
            continue
        time_seconds = _epoch_seconds(timestamp_value)
        if time_seconds is not None and not window_start <= time_seconds <= window_end:
            continue
        observed_services.add(service); timestamp = _utc(timestamp_value); evidence_id = _id("log", case.case_id, row_number, timestamp, service)
        events.append(NormalizedEventEvidence(evidence_id, "RCAEVAL_RESEARCH", service, message or "RCAEVAL_LOG_EVENT", timestamp, str(timestamp_value), _text(_field(row, "level", "severity")).upper() or None, "RESOLVED_EXACT_ID", MappingProxyType({}), MappingProxyType({"adapter_version": RCAEVAL_ADAPTER_VERSION, "source_file": "logs.parquet", "source_record_id": str(row_number), "raw_evidence_id": evidence_id, "external_case_id": case.case_id})))
    for row_number, row in enumerate(trace_rows, 1):
        service = normalize_service_id(_field(row, "service", "service_name", "serviceName", "container"))
        start = _field(row, "timestamp", "start_time", "startTime", "startTimeMillis", "time")
        trace_id, span_id = _text(_field(row, "trace_id", "traceid", "traceId")), _text(_field(row, "span_id", "spanid", "spanId"))
        if not service or start is None or not trace_id or not span_id:
            continue
        time_seconds = _epoch_seconds(start)
        if time_seconds is not None and not window_start <= time_seconds <= window_end:
            continue
        observed_services.add(service); timestamp = _utc(start); duration = _field(row, "duration_ms", "duration", "durationMs")
        try: duration_value = float(duration) if duration is not None else None
        except (TypeError, ValueError): duration_value = None
        end = _field(row, "end_time", "endTime")
        end_time = _utc(end) if end is not None else _utc(datetime.fromisoformat(timestamp.replace("Z", "+00:00")) + timedelta(milliseconds=duration_value or 0))
        evidence_id = _id("trace", case.case_id, row_number, trace_id, span_id)
        traces.append(NormalizedTraceSpanEvidence(evidence_id, "RCAEVAL_RESEARCH", trace_id, span_id, _text(_field(row, "parent_span_id", "parentid", "parentSpanId")) or None, service, _text(_field(row, "operation", "method", "methodName", "name")) or None, timestamp, str(start), end_time, str(end) if end is not None else None, duration_value, "DECLARED_END" if end is not None else "DERIVED_FROM_DURATION", _trace_status(_field(row, "status", "status_code", "statusCode")), None, None, None, "RESOLVED_EXACT_ID", "ROOT" if not _text(_field(row, "parent_span_id", "parentid", "parentSpanId")) else "PENDING_PARENT_RESOLUTION", MappingProxyType({}), MappingProxyType({"adapter_version": RCAEVAL_ADAPTER_VERSION, "source_file": "traces.parquet", "source_record_id": str(row_number), "raw_evidence_id": evidence_id, "external_case_id": case.case_id})))
    entities = tuple(NormalizedEntityEvidence(_id("entity", case.case_id, service), "RCAEVAL_RESEARCH", service, service, None, MappingProxyType({"adapter_declared_type": "observed_service"}), MappingProxyType({"adapter_version": RCAEVAL_ADAPTER_VERSION, "source_file": "telemetry", "source_record_id": service, "raw_evidence_id": _id("entity", case.case_id, service), "external_case_id": case.case_id})) for service in sorted(observed_services))
    trace_ids = {(item.trace_id, item.span_id) for item in traces}
    traces = [replace(item, parent_resolution_status=("ROOT" if not item.parent_span_id else "RESOLVED_PARENT" if (item.trace_id, item.parent_span_id) in trace_ids else "UNRESOLVED_PARENT")) for item in traces]
    manifest = DatasetManifest(f"rcaeval:{case.case_id}", None, "UTC", (SourceSpec("rcaeval_research_adapter", "research_only", case.case_id),))
    manifest_hash = _sha({"adapter": RCAEVAL_ADAPTER_VERSION, "case_id": case.case_id, "modalities": {"metrics": len(metrics), "logs": len(events), "traces": len(traces)}})
    result = PreprocessingResult(manifest, manifest_hash, (), (), entities, (), tuple(sorted(events, key=lambda item: (item.observed_at, item.evidence_id))), (), (), (), tuple(sorted(metrics, key=lambda item: (item.observed_at, item.evidence_id))), tuple(sorted(traces, key=lambda item: (item.trace_id, item.observed_at, item.span_id))))
    injection = datetime.fromtimestamp(case.injection_time, tz=timezone.utc)
    incident = IncidentWindow(f"rcaeval:{case.case_id}", (injection - timedelta(seconds=PRE_WINDOW_SECONDS)).isoformat().replace("+00:00", "Z"), (injection + timedelta(seconds=POST_WINDOW_SECONDS)).isoformat().replace("+00:00", "Z"), tuple(item.external_id for item in entities), source=ORACLE_WINDOW, external_incident_id=case.case_id, provenance={"adapter_version": RCAEVAL_ADAPTER_VERSION, "window_mode": ORACLE_WINDOW, "external_case_id": case.case_id})
    return AdaptedRCAEvalCase(case, result, incident, ORACLE_WINDOW, "Predeclared neutral window: 5 minutes before and 10 minutes after benchmark injection time; injection time is evaluation-only oracle anchoring, not a production detector.")


def adapt_cached_case(case: RCAEvalCase, case_dir: Path) -> AdaptedRCAEvalCase:
    return adapt_case_rows(case, _rows(case_dir / "metrics.parquet"), _rows(case_dir / "logs.parquet"), _rows(case_dir / "traces.parquet"))


def cached_window_trace_count(case: RCAEvalCase, case_dir: Path) -> int:
    """Count traces in the predeclared window without materializing evidence."""
    try:
        import pyarrow.compute as compute
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RCAEvalQualificationError("RCAEVAL_PARQUET_READER_UNAVAILABLE: install pyarrow in the research environment") from exc
    path = case_dir / "traces.parquet"
    schema = parquet.read_schema(path)
    name = next((item for item in ("startTime", "start_time", "timestamp", "time") if item in schema.names), None)
    if not name:
        raise RCAEvalQualificationError("RCAEVAL_TRACE_TIMESTAMP_COLUMN_UNAVAILABLE")
    values = parquet.read_table(path, columns=[name])[name]
    numeric = values.cast("double")
    maximum = compute.max(numeric).as_py() or 0
    if maximum >= 10**14:
        numeric = compute.divide(numeric, 1_000_000)
    elif maximum >= 10**11:
        numeric = compute.divide(numeric, 1_000)
    return int(compute.sum(compute.and_(compute.greater_equal(numeric, case.injection_time - PRE_WINDOW_SECONDS), compute.less_equal(numeric, case.injection_time + POST_WINDOW_SECONDS))).as_py() or 0)


def adapt_cached_case_to_store(case: RCAEvalCase, case_dir: Path, database: Path, *, resource_configuration: ResourceConfiguration = ResourceConfiguration()) -> tuple[AdaptedRCAEvalCase, IncidentEvidenceStore, int, int]:
    """Stream every valid in-window Parquet trace into SQLite, without a Python graph."""
    try:
        import pyarrow.parquet as parquet
    except ImportError as exc:
        raise RCAEvalQualificationError("RCAEVAL_PARQUET_READER_UNAVAILABLE: install pyarrow in the research environment") from exc
    # The RE2-OB logs expose no severity column, so they retain an explicit
    # unspecified severity and cannot activate an ERROR-only frozen rule.
    # They remain normalized evidence for R2 modality and miss diagnostics.
    adapted = adapt_case_rows(case, _rows(case_dir / "metrics.parquet"), _rows(case_dir / "logs.parquet"), ())
    trace_file = parquet.ParquetFile(case_dir / "traces.parquet")
    service_names: set[str] = set()
    for batch in trace_file.iter_batches(batch_size=resource_configuration.trace_chunk_size, columns=["serviceName"]):
        for row in batch.to_pylist():
            service = normalize_service_id(row.get("serviceName"))
            if service:
                service_names.add(service)
    existing = {item.external_id for item in adapted.preprocessing.entities}
    additions = tuple(NormalizedEntityEvidence(_id("entity", case.case_id, service), "RCAEVAL_RESEARCH", service, service, None, MappingProxyType({"adapter_declared_type": "observed_service"}), MappingProxyType({"adapter_version": RCAEVAL_ADAPTER_VERSION, "source_file": "traces.parquet", "source_record_id": service, "raw_evidence_id": _id("entity", case.case_id, service), "external_case_id": case.case_id})) for service in sorted(service_names - existing))
    result = replace(adapted.preprocessing, entities=tuple(sorted((*adapted.preprocessing.entities, *additions), key=lambda item: item.external_id)))
    incident = replace(adapted.incident, affected_entity_ids=tuple(item.external_id for item in result.entities))
    adapted = AdaptedRCAEvalCase(case, result, incident, adapted.window_mode, adapted.window_rationale)
    context = assemble_context(result, incident, TopologyScope.DIRECT_ONLY)
    store = IncidentEvidenceStore(database, context, resource_configuration=resource_configuration)
    raw_count = trace_file.metadata.num_rows
    valid_count = 0
    window_start, window_end = case.injection_time - PRE_WINDOW_SECONDS, case.injection_time + POST_WINDOW_SECONDS
    def spans():
        nonlocal valid_count
        row_number = 0
        columns = ["traceID", "spanID", "parentSpanID", "serviceName", "methodName", "startTime", "duration", "statusCode"]
        for batch in trace_file.iter_batches(batch_size=resource_configuration.trace_chunk_size, columns=columns):
            for row in batch.to_pylist():
                row_number += 1
                service = normalize_service_id(row.get("serviceName")); start = row.get("startTime")
                trace_id, span_id = _text(row.get("traceID")), _text(row.get("spanID"))
                seconds = _epoch_seconds(start)
                if not service or start is None or not trace_id or not span_id or seconds is None:
                    continue
                valid_count += 1
                if not window_start <= seconds <= window_end:
                    continue
                timestamp = _utc(start); duration = row.get("duration")
                duration_value = float(duration) if duration is not None else None
                end_time = _utc(datetime.fromisoformat(timestamp.replace("Z", "+00:00")) + timedelta(milliseconds=duration_value or 0))
                evidence_id = _id("trace", case.case_id, row_number, trace_id, span_id)
                yield NormalizedTraceSpanEvidence(evidence_id, "RCAEVAL_RESEARCH", trace_id, span_id, _text(row.get("parentSpanID")) or None, service, _text(row.get("methodName")) or None, timestamp, str(start), end_time, None, duration_value, "DERIVED_FROM_DURATION", _trace_status(row.get("statusCode")), None, None, None, "RESOLVED_EXACT_ID", "ROOT" if not _text(row.get("parentSpanID")) else "PENDING_PARENT_RESOLUTION", MappingProxyType({}), MappingProxyType({"adapter_version": RCAEVAL_ADAPTER_VERSION, "source_file": "traces.parquet", "source_record_id": str(row_number), "raw_evidence_id": evidence_id, "external_case_id": case.case_id}))
    store.add_trace_spans(spans())
    return adapted, store, raw_count, valid_count


def evaluate_frozen_candidates_from_store(adapted: AdaptedRCAEvalCase, store: IncidentEvidenceStore, truth: RCAEvalGroundTruth) -> CandidateCoverage:
    """Score only after the indexed store has generated frozen candidates."""
    if truth.case_id != adapted.case.case_id or truth.subject_type != "SERVICE":
        raise RCAEvalQualificationError("RCAEVAL_GROUND_TRUTH_CONTRACT_MISMATCH")
    view = store.logical_view()
    candidates = generate_frozen_candidates_from_store(store, view)
    subjects = tuple(sorted(item.subject_node_id.removeprefix("entity:") for item in candidates))
    if not truth.root_cause_service:
        return CandidateCoverage(adapted.case.case_id, "IDENTITY_UNRESOLVED", len(candidates), len(store.context.entities), None, None, subjects, tuple(sorted({rule for item in candidates for rule in item.generation_rules})), view.graph_id)
    covered = truth.root_cause_service in subjects
    return CandidateCoverage(adapted.case.case_id, "GROUND_TRUTH_COVERED" if covered else "GROUND_TRUTH_MISSED", len(candidates), len(store.context.entities), truth.root_cause_service, covered, subjects, tuple(sorted({rule for item in candidates for rule in item.generation_rules})), view.graph_id)


def evaluate_frozen_candidates(adapted: AdaptedRCAEvalCase, truth: RCAEvalGroundTruth, *, remove_metrics: bool = False, remove_events: bool = False, remove_traces: bool = False) -> CandidateCoverage:
    """Run only the frozen generator, then compare its subjects after generation."""
    if truth.case_id != adapted.case.case_id or truth.subject_type != "SERVICE":
        raise RCAEvalQualificationError("RCAEVAL_GROUND_TRUTH_CONTRACT_MISMATCH")
    result = replace(adapted.preprocessing, metrics=() if remove_metrics else adapted.preprocessing.metrics, events=() if remove_events else adapted.preprocessing.events, traces=() if remove_traces else adapted.preprocessing.traces)
    try:
        context = assemble_context(result, adapted.incident, TopologyScope.DIRECT_ONLY)
        graph = build_incident_evidence_graph(snapshot_for(context))
        candidates = generate_cause_candidates(graph)
    except Exception as exc:
        return CandidateCoverage(adapted.case.case_id, "TECHNICAL_UNAVAILABLE", 0, 0, truth.root_cause_service, None, (), (), None)
    subjects = tuple(sorted({node.removeprefix("entity:") for node in (item.subject_node_id for item in candidates)}))
    if not truth.root_cause_service:
        return CandidateCoverage(adapted.case.case_id, "IDENTITY_UNRESOLVED", len(candidates), len(context.entities), None, None, subjects, tuple(sorted({rule for item in candidates for rule in item.generation_rules})), graph.graph_id)
    covered = truth.root_cause_service in subjects
    return CandidateCoverage(adapted.case.case_id, "GROUND_TRUTH_COVERED" if covered else "GROUND_TRUTH_MISSED", len(candidates), len(context.entities), truth.root_cause_service, covered, subjects, tuple(sorted({rule for item in candidates for rule in item.generation_rules})), graph.graph_id)


def trivial_baselines(adapted: AdaptedRCAEvalCase, truth: RCAEvalGroundTruth) -> Mapping[str, CandidateCoverage]:
    """Transparent reference candidate sets; no ground truth participates in selection."""
    service_ids = tuple(item.external_id for item in adapted.preprocessing.entities)
    event_ids = tuple(sorted({item.service_external_id for item in adapted.preprocessing.events if item.severity == "ERROR"}))
    trace_ids = tuple(sorted({item.service_external_id for item in adapted.preprocessing.traces if item.status == "ERROR"}))
    def result(name: str, ids: tuple[str, ...]) -> CandidateCoverage:
        covered = truth.root_cause_service in ids if truth.root_cause_service else None
        return CandidateCoverage(adapted.case.case_id, "GROUND_TRUTH_COVERED" if covered else "GROUND_TRUTH_MISSED", len(ids), len(service_ids), truth.root_cause_service, covered, ids, (name,), None)
    return MappingProxyType({"ALL_SERVICES": result("ALL_SERVICES", service_ids), "ERROR_EVENT_SERVICES": result("ERROR_EVENT_SERVICES", event_ids), "ERROR_TRACE_SERVICES": result("ERROR_TRACE_SERVICES", trace_ids)})
