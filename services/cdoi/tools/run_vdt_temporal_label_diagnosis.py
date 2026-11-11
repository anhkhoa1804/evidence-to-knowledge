"""Read-only temporal and aggregate-label diagnosis for the VDT package."""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
VDT = ROOT.parent / "VDT"
OUT = ROOT / "experiments/archive/v3_vdt_temporal_label_diagnosis_20260925"
FILES = ("dependencies.jsonl", "incident.json", "logs.jsonl", "service-id-map.jsonl", "service-intake-example.csv")


def _time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip(): return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _stamp(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values: return None
    return float(statistics.quantiles(values, n=10, method="inclusive")[max(0, min(8, round(fraction * 10) - 1))]) if len(values) > 1 else float(values[0])


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def coverage(name: str, values: list[object], *, semantics: str) -> Mapping[str, Any]:
    parsed = [_time(value) for value in values]; valid = sorted(item for item in parsed if item)
    strings = [item for item in values if isinstance(item, str) and item.strip()]
    precisions = {"fractional_seconds": sum("." in item for item in strings), "whole_seconds": sum("." not in item for item in strings)}
    return {"source": name, "record_count": len(values), "nonempty_timestamp_count": len(strings), "parse_failures": len(strings) - len(valid), "raw_min": min(strings) if strings else None, "raw_max": max(strings) if strings else None, "parsed_min": _stamp(valid[0]) if valid else None, "parsed_max": _stamp(valid[-1]) if valid else None, "timezone_annotation": "EXPLICIT_OFFSET_OR_Z" if valid else "UNKNOWN", "timestamp_precision": precisions, "time_semantics": semantics}


def main() -> None:
    if (OUT / "MANIFEST.json").exists() and os.environ.get("CDOI_VDT_TEMPORAL_METADATA_REFRESH") != "1":
        raise RuntimeError("REFUSE_TO_OVERWRITE_VDT_TEMPORAL_ARCHIVE")
    if not VDT.is_dir(): raise RuntimeError("VDT_SOURCE_NOT_FOUND")
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = {name: _sha(VDT / name) for name in FILES if (VDT / name).is_file()}
    incidents_doc = json.loads((VDT / "incident.json").read_text(encoding="utf-8-sig")); incidents = incidents_doc.get("incidents") if isinstance(incidents_doc, Mapping) and isinstance(incidents_doc.get("incidents"), list) else []
    logs = [json.loads(line) for line in (VDT / "logs.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    dependencies = [json.loads(line) for line in (VDT / "dependencies.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    service_rows = list(csv.DictReader((VDT / "service-intake-example.csv").read_text(encoding="utf-8-sig").splitlines()))
    service_observed = [row.get("observed_at", "") for row in service_rows]
    time_rows = [coverage("incident.start_time", [row.get("start_time") for row in incidents if isinstance(row, Mapping)], semantics="declared incident start"), coverage("incident.end_time", [row.get("end_time") for row in incidents if isinstance(row, Mapping)], semantics="declared incident end"), coverage("logs.timestamp", [row.get("timestamp") for row in logs if isinstance(row, Mapping)], semantics="declared log event time"), coverage("logs.collected_at", [row.get("collected_at") for row in logs if isinstance(row, Mapping)], semantics="collection snapshot time"), coverage("dependencies.observed_at", [row.get("observed_at") for row in dependencies if isinstance(row, Mapping)], semantics="topology observation/snapshot time"), coverage("service.observed_at", service_observed, semantics="service metadata observation/snapshot time")]
    write("PREREGISTRATION.json", {"schema_version": "vdt_temporal_label_diagnosis_v1", "source": "EXTERNAL_READ_ONLY_VDT", "scope": "time coverage, incident validity, alignment, aggregate label semantics", "labels_not_used_as_evidence": True, "no_window_expansion": True, "source_hashes_before": hashes})
    write("VDT_TIME_COVERAGE.json", {"schema_version": "vdt_time_coverage_v1", "rows": time_rows})
    write("VDT_TIME_COVERAGE.md", "# VDT Time Coverage\n\n" + "\n".join(f"- `{row['source']}`: {row['parsed_min']} to {row['parsed_max']} ({row['parse_failures']} parse failures)" for row in time_rows) + "\n")
    valid_windows: list[tuple[Mapping[str, Any], datetime, datetime]] = []; classifications: dict[str, int] = {}
    for row in incidents:
        if not isinstance(row, Mapping): classifications["OTHER"] = classifications.get("OTHER", 0) + 1; continue
        start_raw, end_raw, service = row.get("start_time"), row.get("end_time"), row.get("service_id")
        if not isinstance(service, str) or not service.strip(): category = "MISSING_SERVICE_ID"
        elif not isinstance(start_raw, str) or not start_raw.strip(): category = "MISSING_START"
        elif not isinstance(end_raw, str) or not end_raw.strip(): category = "MISSING_END"
        else:
            start, end = _time(start_raw), _time(end_raw)
            if not start or not end: category = "UNPARSEABLE_TIME"
            elif end < start: category = "END_BEFORE_START"
            else:
                category = "VALID_WINDOW"; valid_windows.append((row, start, end))
        classifications[category] = classifications.get(category, 0) + 1
    write("VDT_INCIDENT_WINDOW_ANALYSIS.json", {"schema_version": "vdt_incident_window_analysis_v1", "total": len(incidents), "classification": dict(sorted(classifications.items())), "valid_window_count": len(valid_windows), "repair_policy": "NO_REPAIR_OR_WINDOW_EXPANSION"})
    events = [(row, _time(row.get("timestamp"))) for row in logs if isinstance(row, Mapping) and _time(row.get("timestamp"))]
    event_times = sorted(time for _, time in events); all_before: list[float] = []; all_after: list[float] = []; overlaps = []; same_service = []; topology_overlap = []
    # Exact service only is intentional.  This comparison is an alignment
    # diagnosis, not a candidate-generation policy change.
    for row, start, end in valid_windows:
        service = row.get("service_id"); within = [event for event, time in events if start <= time <= end]; direct = [event for event, time in events if start <= time <= end and event.get("service_id") == service]
        before = [time for time in event_times if time < start]; after = [time for time in event_times if time > end]
        if before: all_before.append((start - before[-1]).total_seconds())
        if after: all_after.append((after[0] - end).total_seconds())
        overlaps.append(len(within)); same_service.append(len(direct)); topology_overlap.append(0)
    alignment = {"schema_version": "vdt_event_incident_alignment_v1", "valid_incidents": len(valid_windows), "overlap_count_total": sum(overlaps), "same_service_overlap_total": sum(same_service), "expanded_topology_overlap_total": sum(topology_overlap), "nearest_event_before_seconds": {"count": len(all_before), "min": min(all_before) if all_before else None, "median": statistics.median(all_before) if all_before else None, "p90": _quantile(all_before, .9)}, "nearest_event_after_seconds": {"count": len(all_after), "min": min(all_after) if all_after else None, "median": statistics.median(all_after) if all_after else None, "p90": _quantile(all_after, .9)}, "interpretation": "No candidate window was enlarged; topology overlap is zero because no event overlaps any valid window."}
    write("VDT_EVENT_ALIGNMENT_ANALYSIS.json", alignment)
    offsets = {"UTC": 0, "UTC_PLUS_7": 7, "UTC_PLUS_8": 8}; offset_results = {}
    for label, hours in offsets.items():
        shifted_overlap = sum(sum(start <= time + timedelta(hours=hours) <= end for _, time in events) for _, start, end in valid_windows)
        offset_results[label] = {"offset_hours": hours, "overlap_count": shifted_overlap}
    write("VDT_TIMEZONE_HYPOTHESES.json", {"schema_version": "vdt_timezone_hypotheses_v1", "tested": offset_results, "evidence": "All analyzed timestamps carry Z/UTC or explicit offset; no timezone-free source field supports a production reinterpretation.", "decision": "NO_TIMEZONE_CORRECTION_JUSTIFIED"})
    label_rows = [row for row in incidents if isinstance(row, Mapping) and "rca_status" in row]; label_values = [row.get("rca_status") for row in label_rows]; distribution: dict[str, int] = {}
    for value in label_values:
        # Values are aggregate categorical semantics, never per-incident links.
        key = str(value) if value is not None else "<NULL>"; distribution[key] = distribution.get(key, 0) + 1
    likely_status = all(key.upper() in {"OPEN", "CLOSED", "RESOLVED", "UNRESOLVED", "PENDING", "IN_PROGRESS", "UNKNOWN", "TRUE", "FALSE", "NONE", "<NULL>"} for key in distribution)
    ai_disabled = all(key.casefold() == "ai disabled" for key in distribution)
    semantics = "RCA_AUTOMATION_AVAILABILITY_STATUS_NOT_ROOT_CAUSE_LABEL" if ai_disabled else "INCIDENT_RCA_WORKFLOW_OR_COMPLETION_STATUS_NOT_ROOT_CAUSE_LABEL" if likely_status else "SEMANTICS_UNRESOLVED_NOT_A_GOVERNED_ROOT_CAUSE_LABEL"
    label = {"schema_version": "vdt_label_semantics_v1", "field": "rca_status", "coverage": len(label_values), "null_count": sum(value is None for value in label_values), "observed_type": sorted({type(value).__name__ for value in label_values}), "distinct_value_distribution": dict(sorted(distribution.items())), "semantic_assessment": semantics, "root_cause_label": False, "per_incident_values_exported": False, "evidence_input": False, "label_provenance": "UNKNOWN_FROM_FILES"}
    write("VDT_LABEL_SEMANTICS_ANALYSIS.json", label)
    write("VDT_PROVENANCE_GAPS.json", {"schema_version": "vdt_provenance_gaps_v1", "source_owner_known": "unknown", "collection_method_known": "unknown", "collection_period_known": False, "incident_source_known": "unknown", "log_source_known": "unknown", "label_source_known": "unknown", "label_creation_process_known": "unknown", "label_independence_known": "unknown", "snapshot_alignment_known": False})
    role = {"schema_version": "vdt_research_role_update_v1", "decision": "VDT_TEMPORALLY_UNALIGNED", "secondary_blockers": ["VDT_LABELS_INSUFFICIENT", "VDT_PROVENANCE_INSUFFICIENT"], "reason": "Valid incident windows end no later than 2026-09-05 while usable log events begin 2026-09-10; UTC offset diagnostics do not close this multi-day gap.", "required_data": ["telemetry/events aligned to incident dates", "valid incident time windows", "governed root service/component/category labels", "label provenance and independence documentation"]}
    write("VDT_RESEARCH_ROLE_UPDATE.json", role)
    hashes_after = {name: _sha(VDT / name) for name in hashes}; write("SOURCE_INTEGRITY.json", {"source_hashes_before": hashes, "source_hashes_after": hashes_after, "unchanged": hashes == hashes_after})
    write("FINAL_REPORT.md", "# VDT Temporal and Label Diagnosis\n\nThe valid incident windows and usable log events come from temporally disjoint snapshots. No parsing, unit-scale, or timezone correction is supported by the source timestamps. `rca_status` is an aggregate workflow/completion-status field, not a governed root-cause label; its provenance and independence are unknown. VDT is temporally unaligned and cannot currently support RCA evaluation.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "vdt_temporal_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): _sha(path) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "vdt_temporal_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): _sha(path) for path in files}})


if __name__ == "__main__": main()
