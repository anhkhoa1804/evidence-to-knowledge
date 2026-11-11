"""Incident-scoped evidence fusion and unranked hypothesis eligibility.

This is neither a causal graph nor canonical KG material.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import asdict, dataclass
from typing import Any, Mapping
from .operational_context import EvidenceSnapshot

GRAPH_VERSION = "incident_evidence_graph_v1"
CANDIDATE_VERSION = "cause_candidate_v1"
UNEVALUATED = "CANDIDATE_UNEVALUATED"

def _id(prefix: str, *parts: str) -> str:
    return prefix + "-" + hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:24]
def _json(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"): return {key:_json(item) for key,item in asdict(value).items()}
    if isinstance(value, tuple): return [_json(item) for item in value]
    if isinstance(value, dict): return {str(key):_json(item) for key,item in value.items()}
    return value

@dataclass(frozen=True)
class EvidenceGraphNode:
    node_id: str
    node_type: str
    evidence_ids: tuple[str, ...]
    attributes: Mapping[str, Any]
    provenance: Mapping[str, Any]

@dataclass(frozen=True)
class EvidenceGraphEdge:
    edge_id: str
    edge_type: str
    source_node_id: str
    target_node_id: str
    evidence_ids: tuple[str, ...]

@dataclass(frozen=True)
class IncidentEvidenceGraph:
    graph_id: str
    incident_id: str
    nodes: tuple[EvidenceGraphNode, ...]
    edges: tuple[EvidenceGraphEdge, ...]
    snapshot_id: str
    schema_version: str = GRAPH_VERSION
    def validate(self) -> None:
        ids = {item.node_id for item in self.nodes}
        if len(ids) != len(self.nodes) or len({item.edge_id for item in self.edges}) != len(self.edges):
            raise ValueError("INVALID_INCIDENT_EVIDENCE_GRAPH: duplicate node or edge ID")
        if any(edge.source_node_id not in ids or edge.target_node_id not in ids for edge in self.edges):
            raise ValueError("INVALID_INCIDENT_EVIDENCE_GRAPH: dangling edge")
    def artifact(self) -> dict[str, Any]:
        return {"schema_version":self.schema_version,"graph_id":self.graph_id,"incident_id":self.incident_id,"snapshot_id":self.snapshot_id,"nodes":_json(self.nodes),"edges":_json(self.edges)}

@dataclass(frozen=True)
class CauseCandidate:
    candidate_id: str
    incident_id: str
    graph_id: str
    subject_node_id: str
    candidate_kind: str
    generation_rules: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    context_evidence_ids: tuple[str, ...]
    contradictory_evidence_ids: tuple[str, ...]
    status: str = UNEVALUATED
    schema_version: str = CANDIDATE_VERSION
    def artifact(self) -> dict[str, Any]: return _json(self)

def _node(kind: str, evidence: Any, attrs: Mapping[str, Any]) -> EvidenceGraphNode:
    evidence_id = evidence.evidence_id
    return EvidenceGraphNode(f"{kind.lower()}:{evidence_id}", kind, (evidence_id,), dict(attrs), dict(evidence.provenance))
def _edge(kind: str, source: str, target: str, evidence_ids: tuple[str,...]=()) -> EvidenceGraphEdge:
    return EvidenceGraphEdge(_id("edge", kind, source, target, *evidence_ids), kind, source, target, evidence_ids)

def build_incident_evidence_graph(snapshot: EvidenceSnapshot) -> IncidentEvidenceGraph:
    """Fuse snapshot membership with typed association, topology, and execution edges."""
    context = snapshot.context; incident = f"incident:{context.incident.incident_id}"
    nodes = [EvidenceGraphNode(incident, "INCIDENT", (), {"start_time":context.incident.start_time,"end_time":context.incident.end_time}, dict(context.incident.provenance))]
    edges: list[EvidenceGraphEdge] = []; entity_nodes: dict[str,str] = {}
    for item in context.entities:
        node = EvidenceGraphNode(f"entity:{item.external_id}", "ENTITY", (item.evidence_id,), {"external_id":item.external_id,"label":item.label}, dict(item.provenance))
        entity_nodes[item.external_id] = node.node_id; nodes.append(node); edges.append(_edge("INCIDENT_HAS_ENTITY",incident,node.node_id,(item.evidence_id,)))
    def add_owned(kind: str, collection: tuple[Any,...], attrs) -> None:
        for item in collection:
            node = _node(kind,item,attrs(item)); nodes.append(node)
            owner = getattr(item,"service_external_id",getattr(item,"target_external_id",None))
            if owner in entity_nodes: edges.append(_edge(f"ENTITY_HAS_{kind}",entity_nodes[owner],node.node_id,(item.evidence_id,)))
            else: edges.append(_edge("ORPHAN_EVIDENCE",incident,node.node_id,(item.evidence_id,)))
            membership = {"EVENT":"EVENT_WITHIN_INCIDENT","CHANGE":"CHANGE_WITHIN_INCIDENT","METRIC_OBSERVATION":"METRIC_WITHIN_INCIDENT","TRACE_SPAN":"TRACE_SPAN_OVERLAPS_INCIDENT"}[kind]
            edges.append(_edge(membership,incident,node.node_id,(item.evidence_id,)))
    add_owned("EVENT",context.events,lambda x:{"timestamp":x.observed_at,"event":x.event,"severity":x.severity})
    add_owned("CHANGE",context.changes,lambda x:{"timestamp":x.observed_at,"change_type":x.change_type,"rollback_of":x.rollback_of})
    add_owned("METRIC_OBSERVATION",context.metrics,lambda x:{"timestamp":x.observed_at,"series_key":x.series_key,"value":x.value,"unit":x.unit,"metric_kind":x.metric_kind,"aggregation":x.aggregation,"sampling_interval":x.sampling_interval})
    add_owned("TRACE_SPAN",context.traces,lambda x:{"trace_id":x.trace_id,"span_id":x.span_id,"operation":x.operation,"status":x.status,"start_time":x.observed_at,"end_time":x.end_time,"duration_ms":x.duration_ms,"partial_status":x.parent_resolution_status})
    for item in context.relations:
        source,target=entity_nodes.get(item.source_external_id),entity_nodes.get(item.target_external_id)
        if source and target: edges.append(_edge("STATIC_RELATION",source,target,(item.evidence_id,)))
    trace_nodes={item.evidence_id:f"trace_span:{item.evidence_id}" for item in context.traces}
    for graph in context.trace_execution_graphs:
        for edge in graph.edges:
            if edge.parent_evidence_id in trace_nodes and edge.child_evidence_id in trace_nodes:
                edges.append(_edge("TRACE_PARENT_CHILD",trace_nodes[edge.parent_evidence_id],trace_nodes[edge.child_evidence_id],(edge.parent_evidence_id,edge.child_evidence_id)))
    ordered_nodes=tuple(sorted(nodes,key=lambda x:x.node_id)); ordered_edges=tuple(sorted(edges,key=lambda x:x.edge_id))
    fingerprint=json.dumps({"incident":context.incident.incident_id,"snapshot":snapshot.snapshot_id,"nodes":_json(ordered_nodes),"edges":_json(ordered_edges)},sort_keys=True,separators=(",",":"))
    graph=IncidentEvidenceGraph("ieg-"+hashlib.sha256(fingerprint.encode()).hexdigest()[:24],context.incident.incident_id,ordered_nodes,ordered_edges,snapshot.snapshot_id)
    graph.validate(); return graph

def generate_cause_candidates(graph: IncidentEvidenceGraph) -> tuple[CauseCandidate,...]:
    """Create only observable, unranked eligibility hypotheses."""
    by_id={node.node_id:node for node in graph.nodes}; ownership={edge.target_node_id:edge.source_node_id for edge in graph.edges if edge.edge_type.startswith("ENTITY_HAS_")}
    metrics_by_entity: dict[str,list[str]]={}
    for edge in graph.edges:
        if edge.edge_type=="ENTITY_HAS_METRIC_OBSERVATION": metrics_by_entity.setdefault(edge.source_node_id,[]).extend(edge.evidence_ids)
    groups: dict[tuple[str,str,str],list[str]]={}
    rules={"CHANGE":"CHANGE_AFFECTS_INCIDENT_ENTITY_V1","EVENT":"ERROR_EVENT_ON_INCIDENT_ENTITY_V1","TRACE_SPAN":"ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1"}
    for node in graph.nodes:
        owner=ownership.get(node.node_id)
        if not owner: continue
        eligible = node.node_type=="CHANGE" or (node.node_type=="EVENT" and node.attributes.get("severity")=="ERROR") or (node.node_type=="TRACE_SPAN" and node.attributes.get("status")=="ERROR")
        if not eligible: continue
        kind={"CHANGE":"CHANGE_EVENT_CANDIDATE","EVENT":"OBSERVED_ERROR_CANDIDATE","TRACE_SPAN":"OBSERVED_ERROR_CANDIDATE"}[node.node_type]
        rule=rules[node.node_type]; support=tuple(sorted(node.evidence_ids)); context_ids=tuple(sorted(metrics_by_entity.get(owner,[])))
        groups.setdefault((kind,owner,rule),[]).extend(support)
    rows = [CauseCandidate(_id("candidate",graph.incident_id,kind,owner,*sorted(set(support)),graph.graph_id),graph.incident_id,graph.graph_id,owner,kind,(rule,),tuple(sorted(set(support))),tuple(sorted(metrics_by_entity.get(owner,[]))),()) for (kind,owner,rule),support in groups.items()]
    return tuple(sorted(rows,key=lambda x:(x.candidate_kind,x.subject_node_id,x.candidate_id)))

def nodes_for_entity(graph: IncidentEvidenceGraph, entity_id: str) -> tuple[EvidenceGraphNode,...]:
    owner=f"entity:{entity_id}"; targets={edge.target_node_id for edge in graph.edges if edge.source_node_id==owner}
    return tuple(node for node in graph.nodes if node.node_id in targets)
def evidence_bundle_for_entity(graph: IncidentEvidenceGraph, entity_id: str) -> Mapping[str,tuple[EvidenceGraphNode,...]]:
    rows=nodes_for_entity(graph,entity_id); return {kind:tuple(node for node in rows if node.node_type==kind) for kind in ("EVENT","CHANGE","METRIC_OBSERVATION","TRACE_SPAN")}
