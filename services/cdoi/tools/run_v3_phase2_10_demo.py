"""Generate V3 Phase 2.10 incident graph and unranked candidate artifacts."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from pathlib import Path
from cdoi.raw_preprocessing import process_dataset
from cdoi.operational_context import assemble_context,load_incident_windows,snapshot_for
from cdoi.incident_evidence_graph import build_incident_evidence_graph,generate_cause_candidates
ROOT=Path(__file__).resolve().parents[1]; FIXTURE=ROOT/"tests/fixtures/preprocessing_demo"; OUT=ROOT/"experiments/archive/v3_phase2_10"
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->None:
    r=process_dataset(FIXTURE/"manifest.yaml"); i=load_incident_windows(FIXTURE/"incidents/incidents.csv","incidents/incidents.csv")[0]
    snap=snapshot_for(assemble_context(r,i)); graph=build_incident_evidence_graph(snap); candidates=generate_cause_candidates(graph); OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"incident_graphs").mkdir(exist_ok=True)
    graph_text=json.dumps(graph.artifact(),indent=2,sort_keys=True)+"\n"; (OUT/"INCIDENT_EVIDENCE_GRAPH.json").write_text(graph_text,encoding="utf-8"); (OUT/"incident_graphs"/f"{i.incident_id}.json").write_text(graph_text,encoding="utf-8")
    candidate_payload={"schema_version":"cause_candidate_v1","graph_id":graph.graph_id,"incident_id":i.incident_id,"candidates":[x.artifact() for x in candidates]}
    (OUT/"CAUSE_CANDIDATES.json").write_text(json.dumps(candidate_payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    demo={"schema_version":"v3_phase2_10_demo_result_v1","graph_id":graph.graph_id,"snapshot_id":snap.snapshot_id,"node_counts":dict(sorted(Counter(x.node_type for x in graph.nodes).items())),"edge_counts":dict(sorted(Counter(x.edge_type for x in graph.edges).items())),"candidate_count":len(candidates),"candidate_kinds":dict(sorted(Counter(x.candidate_kind for x in candidates).items())),"generation_rules":dict(sorted(Counter(rule for x in candidates for rule in x.generation_rules).items())),"interpretation_boundary":"candidate != cause; association != causality; temporal precedence != causality; trace traversal != causality; ERROR evidence != root cause"}
    (OUT/"DEMO_RESULT.json").write_text(json.dumps(demo,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    gate={"schema_version":"v3_phase2_10_research_gate_v1","statuses":{"graph_construction":"SUPPORTED","cross_modal_integration":"SUPPORTED","graph_determinism":"SUPPORTED","node_identity":"SUPPORTED","edge_identity":"SUPPORTED","provenance":"SUPPORTED","static_topology_preservation":"SUPPORTED","trace_execution_preservation":"SUPPORTED","unresolved_evidence_safety":"SUPPORTED","candidate_representation":"SUPPORTED","candidate_determinism":"SUPPORTED","generation_rule_transparency":"SUPPORTED","contradictory_evidence_readiness":"SUPPORTED","causal_separation_safety":"SUPPORTED","pre_rca_hypothesis_generation_readiness":"PRE_RCA_HYPOTHESIS_GENERATION_ARCHITECTURALLY_READY","rca_reasoning_readiness":"NOT_IMPLEMENTED","rca_evaluation_data":"DATA_MISSING"}}
    (OUT/"RESEARCH_GATE.json").write_text(json.dumps(gate,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    base=ROOT/"experiments/archive/v3_phase2_10_baseline/BASELINE.json"; (OUT/"BASELINE.json").write_text(base.read_text(),encoding="utf-8")
    names=["BASELINE.json","INCIDENT_EVIDENCE_GRAPH.json","CAUSE_CANDIDATES.json","DEMO_RESULT.json","RESEARCH_GATE.json"]
    (OUT/"MANIFEST.json").write_text(json.dumps({"schema_version":"v3_phase2_10_archive_manifest_v1","artifacts":{name:sha(OUT/name) for name in names}},indent=2,sort_keys=True)+"\n",encoding="utf-8")
if __name__=="__main__":main()
