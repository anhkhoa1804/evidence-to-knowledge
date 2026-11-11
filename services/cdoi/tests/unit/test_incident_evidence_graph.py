import hashlib,json
from dataclasses import replace
from pathlib import Path
import pytest
from cdoi.raw_preprocessing import process_dataset
from cdoi.operational_context import assemble_context,load_incident_windows,snapshot_for
from cdoi.incident_evidence_graph import build_incident_evidence_graph,generate_cause_candidates,evidence_bundle_for_entity,IncidentEvidenceGraph,EvidenceGraphEdge

ROOT=Path(__file__).resolve().parents[2]; FIXTURE=ROOT/"tests/fixtures/preprocessing_demo"
def build():
    result=process_dataset(FIXTURE/"manifest.yaml"); incident=load_incident_windows(FIXTURE/"incidents/incidents.csv","incidents/incidents.csv")[0]
    return build_incident_evidence_graph(snapshot_for(assemble_context(result,incident)))
def test_graph_is_deterministic_and_integrates_all_snapshot_modalities():
    graph=build(); again=build()
    assert graph.graph_id==again.graph_id and graph.artifact()==again.artifact()
    counts={kind:sum(x.node_type==kind for x in graph.nodes) for kind in ("INCIDENT","ENTITY","EVENT","CHANGE","METRIC_OBSERVATION","TRACE_SPAN")}
    assert counts=={"INCIDENT":1,"ENTITY":3,"EVENT":2,"CHANGE":2,"METRIC_OBSERVATION":7,"TRACE_SPAN":12}
def test_static_trace_and_association_edges_remain_distinct_and_provenanced():
    graph=build(); kinds={edge.edge_type for edge in graph.edges}
    assert {"STATIC_RELATION","TRACE_PARENT_CHILD","ENTITY_HAS_EVENT","ENTITY_HAS_CHANGE","ENTITY_HAS_METRIC_OBSERVATION","ENTITY_HAS_TRACE_SPAN"}.issubset(kinds)
    event=next(x for x in graph.nodes if x.node_type=="EVENT")
    assert event.provenance["raw_evidence_id"].startswith("ev-") and event.provenance["source_file"]=="telemetry/logs.jsonl"
def test_graph_integrity_rejects_dangling_edges_and_entity_bundle_is_typed():
    graph=build()
    bad=IncidentEvidenceGraph(graph.graph_id,graph.incident_id,graph.nodes,graph.edges+(EvidenceGraphEdge("bad","STATIC_RELATION","missing","entity:payment-service",()),),graph.snapshot_id)
    with pytest.raises(ValueError,match="dangling"): bad.validate()
    bundle=evidence_bundle_for_entity(graph,"payment-service")
    assert len(bundle["EVENT"])==1 and len(bundle["CHANGE"])==1 and len(bundle["METRIC_OBSERVATION"])==6 and len(bundle["TRACE_SPAN"])==8
def test_unranked_candidates_are_deterministic_aggregated_and_keep_evidence_roles():
    graph=build(); candidates=generate_cause_candidates(graph)
    assert len(candidates)==5
    assert all(item.status=="CANDIDATE_UNEVALUATED" and item.contradictory_evidence_ids==() for item in candidates)
    trace_payment=[x for x in candidates if x.subject_node_id=="entity:payment-service" and x.generation_rules==("ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1",)][0]
    assert len(trace_payment.supporting_evidence_ids)==2 and len(trace_payment.context_evidence_ids)==6
    serialized=json.dumps([x.artifact() for x in candidates]).casefold()
    assert all(word not in serialized for word in ("score","rank","probability","root_cause","likely"))
def test_metrics_are_context_only_and_old_snapshot_without_trace_or_metric_is_supported():
    result=process_dataset(FIXTURE/"manifest.yaml"); incident=load_incident_windows(FIXTURE/"incidents/incidents.csv")[0]
    graph=build_incident_evidence_graph(snapshot_for(assemble_context(replace(result,metrics=(),traces=()),incident)))
    assert not any(x.node_type=="METRIC_OBSERVATION" for x in graph.nodes)
    assert graph.nodes and generate_cause_candidates(graph)
def test_phase29_artifacts_remain_protected():
    baseline=json.loads((ROOT/"experiments/archive/v3_phase2_10_baseline/BASELINE.json").read_text())
    for path,expected in baseline["protected_artifacts"].items(): assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected
