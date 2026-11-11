from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, RDF, URIRef

from .models import AlignmentDecision, EntityCandidate


class KnowledgeGraphPopulator:
    def __init__(self):
        self.graph = Graph()
        self.staging_graph = Graph()

    def populate(self, entity: EntityCandidate, decision: AlignmentDecision, namespace: str, ontology_version: str | None = None, approved: bool = False) -> None:
        instance = URIRef(namespace + "instance/" + entity.id)
        class_iri = decision.target_concept or namespace + entity.surface.replace(" ", "")
        target = self.graph if approved else self.staging_graph
        target.add((instance, RDF.type, URIRef(class_iri)))
        if approved and ontology_version:
            target.add((instance, URIRef("https://example.org/vt/provenance/approvedInVersion"), Literal(ontology_version)))

    def export_turtle(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(destination=destination, format="turtle")

    def export_staging_turtle(self, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.staging_graph.serialize(destination=destination, format="turtle")
