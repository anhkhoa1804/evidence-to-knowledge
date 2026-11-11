"""CDOI RCA POC V0: one-package, read-only orchestration over frozen RCA parts.

The module deliberately adapts existing preprocessing, evidence, candidate, and
V2.4 contracts.  It has no ground-truth input, no write tool, no remediation,
and no path to canonical knowledge state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from .candidate_evidence_profile import CandidateEvidenceProfileBuilder
from .hypothesis_generation import HypothesisConfiguration, generate_evidence_aware_hypotheses
from .incident_evidence_graph import build_incident_evidence_graph
from .operational_context import IncidentWindow, TopologyScope, assemble_context, snapshot_for
from .qwen_rca import QwenRCAConfig
from .rca_agent_v2 import V2AgentBudget
from .rca_agent_v2_4 import RCAAgentV24
from .rca_investigation import CandidateSourceMode, InvestigationMode, PreparedRCAInvestigation, RCAOrchestrator, RCAReport
from .raw_preprocessing import SUPPORTED_SOURCE_TYPES, PreprocessingResult, process_dataset
from .scalable_evidence import IncidentEvidenceStore
from .staged_rca_backend_v2_4 import StagedRCAAgentV24Model, TOOL_BUDGET

POC_VERSION = "cdoi_rca_poc_v0"
RESULT_VERSION = "cdoi_rca_poc_result_v0"
FORBIDDEN_LABEL_KEYS = frozenset({
    "root_service", "root_cause", "root_component", "root_entity", "root_cause_category",
    "ground_truth", "expected_answer", "confirmed_diagnosis", "evaluation_label", "verified_by", "verified_at",
})
PUBLIC_CODES = frozenset({
    "INPUT_SCHEMA_ERROR", "TEMPORAL_ALIGNMENT_ERROR", "IDENTITY_RESOLUTION_ERROR", "NO_USABLE_EVIDENCE",
    "CANDIDATE_GENERATION_ERROR", "PROVIDER_TIMEOUT", "PROVIDER_TRANSPORT_ERROR", "TOOL_CONTRACT_FAILURE",
    "REPORT_CONTRACT_FAILURE", "UNKNOWN_EVIDENCE_REFERENCE", "UNKNOWN_CANDIDATE_REFERENCE", "INTERNAL_ERROR",
})


class POCPackageError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(code)
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class POCResult:
    incident_id: str | None
    status: str
    summary: str
    hypotheses: tuple[Mapping[str, Any], ...]
    candidates_considered: tuple[Mapping[str, Any], ...]
    evidence_references: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    data_quality_warnings: tuple[str, ...]
    technical_warnings: tuple[str, ...]
    runtime: Mapping[str, Any]
    limitations: tuple[str, ...]
    public_error_code: str | None = None

    def artifact(self) -> dict[str, Any]:
        return {
            "schema_version": RESULT_VERSION, "incident_id": self.incident_id, "status": self.status,
            "summary": self.summary, "hypotheses": list(self.hypotheses),
            "candidates_considered": list(self.candidates_considered),
            "evidence_references": list(self.evidence_references), "missing_modalities": list(self.missing_modalities),
            "data_quality_warnings": list(self.data_quality_warnings),
            "technical_warnings": list(self.technical_warnings), "runtime": dict(self.runtime),
            "limitations": list(self.limitations), "public_error_code": self.public_error_code,
            "interpretation_boundary": "RCA hypothesis is not causal proof, calibrated probability, remediation, or canonical KG knowledge.",
        }


def _json(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json(item) for item in value]
    return value


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json(value), sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parse_utc(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise POCPackageError("INPUT_SCHEMA_ERROR", f"{field} must be an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise POCPackageError("INPUT_SCHEMA_ERROR", f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise POCPackageError("INPUT_SCHEMA_ERROR", f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            clean = str(key).strip().casefold()
            current = f"{prefix}.{key}" if prefix else str(key)
            if clean in FORBIDDEN_LABEL_KEYS:
                found.append(current)
            found.extend(_forbidden_keys(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise POCPackageError("INPUT_SCHEMA_ERROR", f"{label} must be readable JSON") from exc
    if not isinstance(value, Mapping):
        raise POCPackageError("INPUT_SCHEMA_ERROR", f"{label} must be a JSON object")
    return value


def _safe_relative(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise POCPackageError("INPUT_SCHEMA_ERROR", "source path is required")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise POCPackageError("INPUT_SCHEMA_ERROR", "source path must remain inside the package")
    return path.as_posix()


def load_package(package: Path) -> tuple[Mapping[str, Any], IncidentWindow, list[Mapping[str, str]], Mapping[str, str]]:
    """Validate the external contract without reading labels or source content."""
    manifest_path, incident_path = package / "manifest.json", package / "incident.json"
    if not manifest_path.is_file() or not incident_path.is_file():
        raise POCPackageError("INPUT_SCHEMA_ERROR", "manifest.json and incident.json are required")
    manifest, incident = _load_json(manifest_path, "manifest.json"), _load_json(incident_path, "incident.json")
    forbidden = sorted(set(_forbidden_keys(manifest, "manifest") + _forbidden_keys(incident, "incident")))
    if forbidden:
        raise POCPackageError("INPUT_SCHEMA_ERROR", "forbidden evaluation/label fields: " + ", ".join(forbidden))
    if manifest.get("schema_version") != POC_VERSION:
        raise POCPackageError("INPUT_SCHEMA_ERROR", f"manifest.schema_version must be {POC_VERSION}")
    incident_id = incident.get("incident_id")
    if not isinstance(incident_id, str) or not incident_id.strip() or manifest.get("incident_id") != incident_id:
        raise POCPackageError("INPUT_SCHEMA_ERROR", "manifest and incident must have the same nonempty incident_id")
    start, end = _parse_utc(incident.get("start_time"), "incident.start_time"), _parse_utc(incident.get("end_time"), "incident.end_time")
    if start > end:
        raise POCPackageError("INPUT_SCHEMA_ERROR", "incident.start_time must be <= incident.end_time")
    affected = incident.get("affected_service_ids")
    if isinstance(affected, str):
        affected = [affected]
    if not isinstance(affected, list) or not all(isinstance(item, str) and item.strip() for item in affected):
        raise POCPackageError("INPUT_SCHEMA_ERROR", "incident.affected_service_ids must be a nonempty string list")
    window = IncidentWindow(incident_id, start, end, tuple(affected),
                            environment=str(incident.get("environment") or manifest.get("environment") or "") or None,
                            summary=str(incident.get("summary") or "") or None,
                            source="CDOI_RCA_POC_V0_PACKAGE",
                            provenance={"source_file": "incident.json", "poc_version": POC_VERSION})
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise POCPackageError("INPUT_SCHEMA_ERROR", "manifest.sources must contain at least service inventory")
    normalized: list[Mapping[str, str]] = []
    seen_ids, types = set(), set()
    for row in sources:
        if not isinstance(row, Mapping):
            raise POCPackageError("INPUT_SCHEMA_ERROR", "each source must be an object")
        source_id, source_type = row.get("id"), row.get("type")
        if not isinstance(source_id, str) or not source_id.strip() or source_id in seen_ids:
            raise POCPackageError("INPUT_SCHEMA_ERROR", "source IDs must be unique nonempty strings")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise POCPackageError("INPUT_SCHEMA_ERROR", f"unsupported source type: {source_type}")
        relative = _safe_relative(row.get("path"))
        if not (package / relative).is_file():
            raise POCPackageError("INPUT_SCHEMA_ERROR", f"source file is missing: {relative}")
        seen_ids.add(source_id); types.add(source_type)
        normalized.append({"id": source_id, "type": str(source_type), "path": relative})
    if "service_inventory_csv" not in types:
        raise POCPackageError("INPUT_SCHEMA_ERROR", "service_inventory_csv is required for exact identity")
    hashes = {"manifest.json": _digest(manifest_path), "incident.json": _digest(incident_path)}
    hashes.update({row["path"]: _digest(package / row["path"]) for row in normalized})
    return manifest, window, sorted(normalized, key=lambda row: row["id"]), hashes


def _internal_manifest(package: Path, output: Path, manifest: Mapping[str, Any], sources: Sequence[Mapping[str, str]], incident: IncidentWindow) -> Path:
    internal = output / "internal_input"
    internal.mkdir(parents=True, exist_ok=True)
    # Files are read in place; only the contract adaptation is materialized here.
    generated = {"dataset_id": "poc-" + incident.incident_id, "environment": manifest.get("environment"),
                 "timezone": manifest.get("timezone", "UTC"), "sources": [dict(row) for row in sources]}
    target = internal / "manifest.yaml"
    target.write_text(yaml.safe_dump(generated, sort_keys=True), encoding="utf-8")
    # Existing preprocessing resolves source paths relative to its manifest.
    for row in sources:
        destination = internal / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(package / row["path"], destination)
    with (internal / "incident.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("incident_id", "start_time", "end_time", "affected_service_ids", "environment", "summary", "source"))
        writer.writeheader(); writer.writerow({"incident_id": incident.incident_id, "start_time": incident.start_time,
            "end_time": incident.end_time, "affected_service_ids": "|".join(incident.affected_entity_ids),
            "environment": incident.environment or "", "summary": incident.summary or "", "source": incident.source})
    return target


def _coverage(rows: Sequence[Any], time_field: str, start: str, end: str) -> Mapping[str, Any]:
    values = sorted(str(getattr(row, time_field)) for row in rows if getattr(row, time_field, None))
    return {"valid_records": len(rows), "earliest_timestamp": values[0] if values else None,
            "latest_timestamp": values[-1] if values else None,
            "incident_overlap": bool(values), "incident_start": start, "incident_end": end}


def _preflight(result: PreprocessingResult, context: Any) -> Mapping[str, Any]:
    rejected_by_source: dict[str, int] = {}
    for issue in result.unresolved:
        rejected_by_source[issue.source_id] = rejected_by_source.get(issue.source_id, 0) + 1
    rows = {
        "logs": _coverage(context.events, "observed_at", context.incident.start_time, context.incident.end_time),
        "metrics": _coverage(context.metrics, "observed_at", context.incident.start_time, context.incident.end_time),
        "traces": _coverage(context.traces, "observed_at", context.incident.start_time, context.incident.end_time),
        "changes": _coverage(context.changes, "observed_at", context.incident.start_time, context.incident.end_time),
        "topology": {"nodes": len(context.entities), "edges": len(context.relations), "incident_overlap": "NOT_TIME_SCOPED"},
    }
    for name, summary in rows.items():
        if name != "topology": summary["rejected_records"] = sum(rejected_by_source.values())
    unresolved_identity = sorted({issue.detail for issue in context.unresolved if issue.status in {"UNKNOWN_ENTITY_REFERENCE", "UNRESOLVED_INCIDENT_ENTITY"}})
    return {"schema_version": "cdoi_rca_poc_preflight_v0", "incident": {"valid": True, "incident_id": context.incident.incident_id,
            "start_time": context.incident.start_time, "end_time": context.incident.end_time},
            "identity": {"resolved_services": list(context.expanded_entity_ids), "unresolved_ids": unresolved_identity},
            "modalities": rows, "missing_modalities": sorted(name.upper() for name in ("logs", "metrics", "traces", "changes") if not rows[name]["valid_records"]),
            "preprocessing_issue_count": len(result.unresolved), "preprocessing_issues_by_source": rejected_by_source}


def _public_code(error: Exception) -> str:
    code = str(error)
    if isinstance(error, POCPackageError): return error.code
    if "NO_AGENT_MODEL_CONFIGURED" in code or "LIVE_AGENT_RUNTIME_UNAVAILABLE" in code:
        return "PROVIDER_TRANSPORT_ERROR"
    if "TIMEOUT" in code: return "PROVIDER_TIMEOUT"
    if "TRANSPORT" in code or "PROVIDER" in code: return "PROVIDER_TRANSPORT_ERROR"
    if "UNKNOWN_EVIDENCE" in code: return "UNKNOWN_EVIDENCE_REFERENCE"
    if "UNKNOWN_CANDIDATE" in code: return "UNKNOWN_CANDIDATE_REFERENCE"
    if "TOOL" in code: return "TOOL_CONTRACT_FAILURE"
    if "REPORT" in code or "STATUS" in code or "AGENT" in code: return "REPORT_CONTRACT_FAILURE"
    return "INTERNAL_ERROR"


def _runtime_metadata(agent: Any | None) -> Mapping[str, Any]:
    if agent is None:
        return {"agent": "NOT_CONFIGURED", "transport_retries": 0, "tool_call_budget": TOOL_BUDGET,
                "tool_action_correction_budget": 1, "report_repair_budget": 1}
    model = agent.model
    public = dict(getattr(model, "public_metadata", lambda: {})())
    return {key: value for key, value in {**public, "agent_version": "V2.4", "transport_retries": 0,
        "tool_call_budget": TOOL_BUDGET, "tool_action_correction_budget": 1, "report_repair_budget": 1,
        "prompt_version": getattr(model, "prompt_version", "UNKNOWN")}.items()
        if key not in {"api_key", "authorization", "token", "secret", "password", "base_url"}}


def create_live_v24_agent() -> RCAAgentV24:
    """Create an explicit one-provider V2.4 agent; no fallback or hidden retry."""
    key_env = os.environ.get("CDOI_POC_RCA_API_KEY_ENV", "CDOI_RCA_POC_API_KEY")
    if not key_env.isidentifier() or key_env not in os.environ:
        raise POCPackageError("PROVIDER_TRANSPORT_ERROR", "configured CDOI_POC_RCA_API_KEY_ENV is unavailable")
    config = QwenRCAConfig(provider="poc-openai-compatible", provider_profile="POC_EXPLICIT",
        model=os.environ.get("CDOI_POC_RCA_MODEL", "kr/claude-sonnet-4.5"),
        base_url=os.environ.get("CDOI_POC_RCA_BASE_URL"), api_key_env=key_env,
        host_header=os.environ.get("CDOI_POC_RCA_HOST_HEADER"), enable_thinking=None,
        timeout_seconds=int(os.environ.get("CDOI_POC_RCA_TIMEOUT_SECONDS", "120")), max_retries=0)
    if config.status() != "QWEN_LIVE_READY":
        raise POCPackageError("PROVIDER_TRANSPORT_ERROR", "explicit POC provider configuration is incomplete")
    model = StagedRCAAgentV24Model(config, max_output_tokens=int(os.environ.get("CDOI_POC_RCA_MAX_OUTPUT_TOKENS", "2048")))
    return RCAAgentV24(model, budget=V2AgentBudget(max_tool_calls=8, max_output_repairs=1))


def _result_from_report(report: RCAReport, candidates: Sequence[Any], preflight: Mapping[str, Any], runtime: Mapping[str, Any], trace: Mapping[str, Any] | None) -> POCResult:
    references = sorted(set((*report.supporting_evidence_ids, *report.contradictory_evidence_ids,
        *(evidence_id for hypothesis in (report.primary_hypothesis, *report.alternative_hypotheses)
          if hypothesis for evidence_id in hypothesis.supporting_evidence_ids))))
    hypotheses = []
    for item in (report.primary_hypothesis, *report.alternative_hypotheses):
        if item:
            hypotheses.append({"candidate_id": item.candidate_id, "statement": item.statement,
                "supporting_evidence_ids": list(item.supporting_evidence_ids), "limitations": list(item.limitations)})
    technical = []
    public_error = None
    if report.status == "TECHNICAL_FAILURE":
        raw_code = str((trace or {}).get("error_code") or report.abstention_reason or "INTERNAL_ERROR")
        public_error = _public_code(ValueError(raw_code)); technical.append(raw_code)
    return POCResult(report.incident_id, report.status, report.reasoning_summary,
        tuple(hypotheses), tuple({"candidate_id": item.candidate_id, "subject_id": item.subject_node_id.removeprefix("entity:"),
            "candidate_kind": item.candidate_kind, "generation_rules": list(item.generation_rules)} for item in candidates),
        tuple(references), tuple(preflight["missing_modalities"]), tuple(preflight["identity"]["unresolved_ids"]),
        tuple(technical), runtime, tuple(report.limitations), public_error)


def _markdown(result: POCResult, preflight: Mapping[str, Any]) -> str:
    lines = ["# CDOI RCA POC V0 Report", "", "## Incident", "", f"- Incident: `{result.incident_id}`", f"- Result: `{result.status}`", "", "## Evidence availability", ""]
    for name, data in preflight.get("modalities", {}).items():
        if name == "topology": lines.append(f"- {name}: {data.get('nodes', 0)} nodes, {data.get('edges', 0)} edges")
        else: lines.append(f"- {name}: {data['valid_records']} in-window records; overlap={data['incident_overlap']}")
    lines += ["", "## Candidates considered", ""]
    lines += [f"- `{row['candidate_id']}` ({row['subject_id']}; {row['candidate_kind']})" for row in result.candidates_considered] or ["- None"]
    lines += ["", "## Result", "", result.summary or "No accepted RCA hypothesis was produced."]
    if result.hypotheses:
        lines += ["", "## Hypotheses", ""]
        for row in result.hypotheses: lines += [f"- `{row['candidate_id']}`: {row['statement']}"]
    lines += ["", "## Evidence references", ""] + ([f"- `{item}`" for item in result.evidence_references] or ["- None"])
    lines += ["", "## Technical and data limitations", ""]
    lines += [f"- {item}" for item in (*result.missing_modalities, *result.data_quality_warnings, *result.technical_warnings, *result.limitations)] or ["- None recorded"]
    lines += ["", "## Audit metadata", "", "This is a read-only, development POC result. It is a hypothesis or abstention, not causal proof, calibrated confidence, remediation, ontology commitment, or canonical KG mutation."]
    return "\n".join(lines) + "\n"


def _seal(output: Path) -> None:
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(output).as_posix(): _digest(path) for path in files}
    _write(output / "HASHES.json", {"schema_version": "cdoi_rca_poc_hashes_v0", "algorithm": "sha256", "artifacts": hashes})
    _write(output / "MANIFEST.json", {"schema_version": "cdoi_rca_poc_manifest_v0", "file_count": len(hashes), "files": hashes,
        "integrity_rule": "HASHES.json and MANIFEST.json are not self-hashed."})


def run_package(package: Path, output: Path, *, agent: Any | None = None, use_live_agent: bool = False, preflight_only: bool = False) -> POCResult:
    """Run one package. Every terminal path writes FINAL_RESULT and a sealed audit."""
    package, output = package.resolve(), output.resolve()
    if output.exists(): raise FileExistsError(f"POC_OUTPUT_ALREADY_EXISTS:{output}")
    output.mkdir(parents=True)
    runtime = _runtime_metadata(agent)
    incident_id: str | None = None
    preflight: Mapping[str, Any] = {"modalities": {}, "missing_modalities": [], "identity": {"unresolved_ids": []}}
    store: IncidentEvidenceStore | None = None
    try:
        manifest, incident, sources, input_hashes = load_package(package); incident_id = incident.incident_id
        _write(output / "INPUT_VALIDATION.json", {"status": "PASS", "schema_version": "cdoi_rca_poc_input_validation_v0",
            "package": str(package.name), "incident_id": incident_id, "source_hashes": input_hashes,
            "ground_truth_fields_read": [], "forbidden_label_fields": [], "exact_identity_policy": "NO_FUZZY_OR_ALIAS_RESOLUTION"})
        internal_manifest = _internal_manifest(package, output, manifest, sources, incident)
        processed = process_dataset(internal_manifest)
        context = assemble_context(processed, incident, TopologyScope.ONE_HOP)
        preflight = _preflight(processed, context)
        _write(output / "NORMALIZATION_SUMMARY.json", {"schema_version": "cdoi_rca_poc_normalization_summary_v0",
            "raw_records": len(processed.raw_records), "entities": len(processed.entities), "relations": len(processed.relations),
            "events": len(processed.events), "changes": len(processed.changes), "metrics": len(processed.metrics),
            "traces": len(processed.traces), "unresolved": len(processed.unresolved), "source_files": list(processed.source_files)})
        _write(output / "INPUT_PREFLIGHT.json", preflight)
        if not context.direct_entity_ids:
            raise POCPackageError("IDENTITY_RESOLUTION_ERROR", "declared affected service does not resolve by exact ID")
        timed = [preflight["modalities"][name]["valid_records"] for name in ("logs", "metrics", "traces", "changes")]
        if not any(timed):
            raise POCPackageError("TEMPORAL_ALIGNMENT_ERROR", "no operational evidence overlaps the declared incident window")
        snapshot = snapshot_for(context); graph = build_incident_evidence_graph(snapshot)
        _write(output / "EVIDENCE_SNAPSHOT_SUMMARY.json", {"snapshot_id": snapshot.snapshot_id, "content_sha256": snapshot.content_sha256,
            "entity_count": len(context.entities), "event_count": len(context.events), "metric_count": len(context.metrics),
            "trace_count": len(context.traces), "change_count": len(context.changes), "selection_count": len(context.selections)})
        _write(output / "INCIDENT_EVIDENCE_GRAPH.json", graph.artifact())
        store = IncidentEvidenceStore.from_context(output / "evidence.sqlite", context, exact_legacy_graph_id=True, snapshot=snapshot)
        view = store.logical_view(snapshot.snapshot_id); config = HypothesisConfiguration()
        h1 = generate_evidence_aware_hypotheses(store, view, configuration=config, include_metric=True, include_trace=False, include_topology=False, include_temporal_change=False)
        h5 = generate_evidence_aware_hypotheses(store, view, configuration=config, include_metric=True, include_trace=True, include_topology=True, include_temporal_change=True)
        candidates = tuple(sorted({item.candidate_id: item for item in (*h1.candidates, *h5.candidates)}.values(), key=lambda item: item.candidate_id))
        profiles = CandidateEvidenceProfileBuilder(context, store, (*h1.aggregate_evidence, *h5.aggregate_evidence)).build_all(candidates)
        _write(output / "CANDIDATES.json", {"h1": [_json(item) for item in h1.candidates], "h5": [_json(item) for item in h5.candidates],
            "candidate_count": len(candidates), "policy": "FROZEN_H1_THEN_H5_FALLBACK"})
        _write(output / "CANDIDATE_PROFILES.json", {"profiles": [_json(item) for item in profiles], "profile_count": len(profiles)})
        prepared = PreparedRCAInvestigation(context, store, h1.candidates, h5.candidates, profiles)
        if preflight_only:
            live_gate = "READY_FOR_LIVE_AGENT" if candidates and profiles else "NO_AGENT_VALUE_NO_CANDIDATES"
            preflight_artifact = {"schema_version": "cdoi_rca_poc_preflight_only_v1", "status": live_gate,
                "provider_invoked": False, "live_llm_calls": 0, "generation_tokens": 0,
                "candidate_count": len(candidates), "profile_count": len(profiles),
                "minimum_usable_operational_evidence": True, "exact_identity_resolved": True,
                "ground_truth_read": False, "stop_boundary": "BEFORE_AGENT_MODEL_OR_TOOL_INVOCATION"}
            _write(output / "PREFLIGHT_ONLY.json", preflight_artifact)
            runtime = {**runtime, "execution_mode": "PREFLIGHT_ONLY", "provider_invoked": False}
            result = POCResult(incident_id, "INSUFFICIENT_EVIDENCE",
                "Deterministic preflight completed; no provider, model, tool, or RCA report generation was invoked.", (),
                tuple({"candidate_id": item.candidate_id, "subject_id": item.subject_node_id.removeprefix("entity:"),
                       "candidate_kind": item.candidate_kind, "generation_rules": list(item.generation_rules)} for item in candidates), (),
                tuple(preflight["missing_modalities"]), tuple(preflight["identity"]["unresolved_ids"]), (), runtime,
                ("PREFLIGHT_ONLY_NOT_A_SEMANTIC_ABSTENTION", live_gate))
        else:
            if use_live_agent and agent is None:
                agent = create_live_v24_agent(); runtime = _runtime_metadata(agent)
            agent_output = output / "agent_run"; orchestrator = RCAOrchestrator()
            if not candidates:
                report = orchestrator.run(prepared, agent_output, InvestigationMode.DETERMINISTIC_BASELINE)
            else:
                report = orchestrator.run(prepared, agent_output, InvestigationMode.AGENT, CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, runtime)
            trace_path = agent_output / "AGENT_TRACE.json"; trace = _load_json(trace_path, "agent trace") if trace_path.is_file() else None
            if trace is not None: _write(output / "AGENT_TRACE.json", trace)
            result = _result_from_report(report, candidates, preflight, runtime, trace)
    except Exception as exc:
        if not (output / "INPUT_VALIDATION.json").exists():
            _write(output / "INPUT_VALIDATION.json", {"status": "FAIL", "schema_version": "cdoi_rca_poc_input_validation_v0",
                "ground_truth_fields_read": [], "error_code": _public_code(exc), "detail": getattr(exc, "detail", str(exc))})
        result = POCResult(incident_id, "TECHNICAL_FAILURE", "The POC could not safely complete the requested investigation.", (), (), (),
            tuple(preflight.get("missing_modalities", [])), tuple(preflight.get("identity", {}).get("unresolved_ids", [])),
            (str(exc),), runtime, ("No RCA hypothesis was accepted after this technical/data failure.",), _public_code(exc))
    finally:
        if store is not None: store.close()
    _write(output / "RUNTIME.json", runtime)
    _write(output / "FINAL_RESULT.json", result.artifact())
    (output / "RCA_REPORT.md").write_text(_markdown(result, preflight), encoding="utf-8")
    _seal(output)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cdoi.rca_poc", description="Run one CDOI RCA POC V0 incident package.")
    sub = parser.add_subparsers(dest="command", required=True); run = sub.add_parser("run")
    run.add_argument("package", type=Path); run.add_argument("--output", type=Path, required=True)
    run.add_argument("--live", action="store_true", help="Use the explicitly configured V2.4 provider; otherwise produce an explicit technical outcome.")
    run.add_argument("--preflight-only", action="store_true", help="Stop after deterministic normalization, snapshot, graph, candidates, and profiles; never invoke a provider.")
    args = parser.parse_args(argv)
    try:
        if args.live and args.preflight_only:
            parser.error("--live and --preflight-only cannot be combined")
        result = run_package(args.package, args.output, use_live_agent=args.live, preflight_only=args.preflight_only)
    except FileExistsError as exc:
        print(f"Result: TECHNICAL_FAILURE\nCode: INTERNAL_ERROR\n{exc}", file=sys.stderr); return 2
    print("CDOI RCA POC V0")
    print(f"Incident: {result.incident_id or 'UNKNOWN'}")
    print(f"Result: {result.status}")
    if result.public_error_code: print(f"Code: {result.public_error_code}")
    print(f"Full report: {args.output / 'RCA_REPORT.md'}")
    print(f"Audit bundle: {args.output}")
    return 0 if result.status != "TECHNICAL_FAILURE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
