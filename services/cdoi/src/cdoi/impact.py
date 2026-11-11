from __future__ import annotations

from rdflib import RDFS, URIRef

from .models import OntologyChangeProposal
from .ontology import OntologyStore


class ImpactAnalyzer:
    def __init__(self, store: OntologyStore):
        self.store = store

    def analyze(self, proposal: OntologyChangeProposal) -> dict[str, int]:
        module = self.store.module(proposal.source_domain)
        target = URIRef(proposal.target_iri) if proposal.target_iri else None
        graph = module.graph
        return {
            "subclasses": len(list(graph.subjects(RDFS.subClassOf, target))) if target else 0,
            "superclasses": len(list(graph.objects(target, RDFS.subClassOf))) if target else 0,
            "properties": len(list(graph.predicates(target, None))) if target else 0,
            "mappings": sum(1 for name, item in self.store.modules.items() if item.layer.value == "BRIDGE" and target and (target, None, None) in item.graph),
            "constraints": 0,
            "instance_typings": 0,
        }
