import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

from cdoi.evidence_schema import EvidenceSchemaInducer
from cdoi.operational_context import TopologyScope, assemble_context, load_incident_windows, snapshot_for
from cdoi.raw_preprocessing import trace_by_id, trace_spans_for_entity, process_dataset, write_artifacts
from cdoi.trace_evidence import execution_graph_for_trace, execution_graphs


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"


def _result():
    return process_dataset(FIXTURE / "manifest.yaml")


def _incident():
    return load_incident_windows(FIXTURE / "incidents" / "incidents.csv", "incidents/incidents.csv")[0]


def test_trace_jsonl_parsing_preserves_explicit_trace_span_service_identity_and_duration():
    traces = {(item.trace_id, item.span_id): item for item in _result().traces}
    payment = traces[("trace-001", "span-payment")]
    assert len(traces) == 14
    assert (payment.parent_span_id, payment.service_external_id, payment.operation, payment.duration_ms, payment.status, payment.span_kind) == ("span-order", "payment-service", "POST /payments", 600.0, "ERROR", "CLIENT")
    assert payment.evidence_id.startswith("ev-") and payment.metadata == {"attributes_present": False}


def test_trace_invalid_duplicate_unresolved_service_and_missing_parent_are_explicit():
    result = _result()
    statuses = {item.status for item in result.unresolved}
    assert {"DUPLICATE_SPAN_ID", "INVALID_SPAN_DURATION", "UNRESOLVED_TRACE_ENTITY", "UNRESOLVED_PARENT_SPAN", "TRACE_PARENT_CYCLE"}.issubset(statuses)
    audit = next(item for item in result.traces if item.span_id == "span-audit")
    missing = next(item for item in result.traces if item.span_id == "span-missing-parent")
    assert audit.correlation_status == "UNRESOLVED_TRACE_ENTITY"
    assert missing.parent_resolution_status == "UNRESOLVED_PARENT"


def test_trace_required_fields_and_declared_duration_end_conflict_fail_closed(tmp_path: Path):
    dataset = tmp_path / "dataset"; shutil.copytree(FIXTURE, dataset)
    spans = dataset / "traces" / "spans.jsonl"
    with spans.open("a", encoding="utf-8") as handle:
        handle.write("\n{\"span_id\":\"missing-trace\",\"service_id\":\"payment-service\",\"start_time\":\"2026-09-18T10:00:00Z\"}")
        handle.write("\n{\"trace_id\":\"trace-conflict\",\"span_id\":\"conflict\",\"service_id\":\"payment-service\",\"start_time\":\"2026-09-18T10:00:00Z\",\"duration_ms\":10,\"end_time\":\"2026-09-18T10:00:01Z\"}")
    statuses = {item.status for item in process_dataset(dataset / "manifest.yaml").unresolved}
    assert {"MISSING_REQUIRED_FIELD", "SPAN_TIME_CONFLICT"}.issubset(statuses)


def test_trace_ordering_raw_identity_and_time_contract_are_deterministic():
    first, second = _result(), _result()
    assert [(item.trace_id, item.span_id, item.evidence_id) for item in first.traces] == [(item.trace_id, item.span_id, item.evidence_id) for item in second.traces]
    overlap = next(item for item in first.traces if item.span_id == "span-overlap-start")
    assert overlap.observed_at == "2026-09-18T09:49:59Z" and overlap.end_time == "2026-09-18T09:50:01Z"
    assert [item.span_id for item in trace_by_id(first.traces, "trace-001")] == ["span-order", "span-payment", "span-db", "span-audit", "span-payment-retry"]


def test_execution_graph_preserves_declared_parent_edges_branching_retries_and_partial_states():
    result = _result()
    graph = execution_graph_for_trace(result.traces, "trace-001")
    assert len(graph.nodes) == 5 and len(graph.edges) == 4 and graph.branch_count == 2
    assert graph.status == "PARTIAL_UNRESOLVED_SERVICE"
    assert len({item.span_id for item in graph.nodes if item.operation == "POST /payments"}) == 2
    missing = execution_graph_for_trace(result.traces, "trace-002")
    cycle = execution_graph_for_trace(result.traces, "trace-004")
    assert missing.status == "PARTIAL_MISSING_PARENT" and missing.missing_parent_evidence_ids
    assert cycle.status == "PARTIAL_PARENT_CYCLE" and cycle.edges == ()


def test_multiple_declared_roots_and_zero_duration_are_preserved_not_repaired():
    graph = execution_graph_for_trace(_result().traces, "trace-003")
    assert len(graph.root_evidence_ids) == 2
    assert all(item.duration_ms == 0.0 for item in graph.nodes)


def test_exact_entity_overlap_query_includes_crossing_boundaries_and_excludes_outside_span():
    spans = trace_spans_for_entity(_result().traces, "payment-service", "2026-09-18T09:50:00Z", "2026-09-18T10:10:00Z")
    names = {item.span_id for item in spans}
    assert {"span-overlap-start", "span-overlap-end"}.issubset(names)
    assert "span-outside" not in names


def test_snapshot_trace_membership_obeys_direct_one_hop_scope_without_trace_driven_expansion():
    result = _result()
    direct = snapshot_for(assemble_context(result, _incident(), TopologyScope.DIRECT_ONLY)).artifact()
    one_hop = snapshot_for(assemble_context(result, _incident(), TopologyScope.ONE_HOP)).artifact()
    direct_ids = {item["span_id"] for item in direct["traces"]}
    one_hop_ids = {item["span_id"] for item in one_hop["traces"]}
    assert "span-order" not in direct_ids and "span-order" in one_hop_ids
    assert "span-audit" not in one_hop_ids and "span-outside" not in one_hop_ids
    assert len(one_hop_ids) == 12


def test_snapshot_graph_and_trace_selection_provenance_are_deterministic_and_noncausal():
    result = _result()
    first = snapshot_for(assemble_context(result, _incident()))
    second = snapshot_for(assemble_context(replace(result, traces=tuple(reversed(result.traces))), _incident()))
    assert first.snapshot_id == second.snapshot_id and first.artifact() == second.artifact()
    artifact = first.artifact()
    assert any(item["selection_rule"] == "TRACE_DIRECT_ENTITY_OVERLAPS_WINDOW_V1" for item in artifact["selection_provenance"])
    assert any(item["selection_rule"] == "TRACE_ONE_HOP_ENTITY_OVERLAPS_WINDOW_V1" for item in artifact["selection_provenance"])
    serialized = json.dumps(artifact, sort_keys=True).casefold()
    assert all(token not in serialized for token in ("caused_by", "root_cause", "culprit", "causal_weight", "anomalous", "approved"))


def test_trace_artifacts_diagnostics_and_schema_boundary_are_deterministic(tmp_path: Path):
    first, second = _result(), _result()
    one, two = write_artifacts(first, tmp_path / "one"), write_artifacts(second, tmp_path / "two")
    assert one["artifacts"]["traces.jsonl"] == two["artifacts"]["traces.jsonl"]
    assert one["trace_diagnostics"]["trace_count"] == 7
    assert one["trace_diagnostics"]["partial_traces"] == 3
    schema = (tmp_path / "one" / "schema_candidates.jsonl").read_text(encoding="utf-8")
    assert "POST /payments" not in schema and len(EvidenceSchemaInducer().induce(first)) == 6


def test_manifest_without_traces_and_phase2_8_context_without_traces_remain_valid(tmp_path: Path):
    dataset = tmp_path / "dataset"; shutil.copytree(FIXTURE, dataset)
    manifest = dataset / "manifest.yaml"
    manifest.write_text(manifest.read_text(encoding="utf-8").replace("  - id: distributed_traces\n    type: trace_span_jsonl\n    path: traces/spans.jsonl\n", ""), encoding="utf-8")
    result = process_dataset(manifest)
    write_artifacts(result, tmp_path / "output")
    assert result.traces == () and not (tmp_path / "output" / "traces.jsonl").exists()
    snapshot = snapshot_for(assemble_context(replace(_result(), traces=()), _incident())).artifact()
    assert snapshot["traces"] == [] and snapshot["trace_execution_graphs"] == []


def test_trace_fixture_is_read_only_and_phase2_7_8_artifacts_remain_protected():
    path = FIXTURE / "traces" / "spans.jsonl"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    _result()
    assert before == hashlib.sha256(path.read_bytes()).hexdigest()
    baseline = json.loads((ROOT / "experiments" / "archive" / "v3_phase2_9_baseline" / "BASELINE.json").read_text(encoding="utf-8"))
    for relative_path, expected_hash in baseline["protected_artifacts"].items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == expected_hash
