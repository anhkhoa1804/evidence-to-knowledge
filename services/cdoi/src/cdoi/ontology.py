from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, RDF, RDFS, OWL, URIRef

from .models import OntologyLayer


@dataclass
class OntologyModule:
    name: str
    layer: OntologyLayer
    namespace: str
    graph: Graph
    path: Path


class OntologyStore:
    def __init__(self, root: Path):
        self.root = root
        self.modules: dict[str, OntologyModule] = {}

    def load_defaults(self) -> "OntologyStore":
        definitions = [
            ("foundation", OntologyLayer.FOUNDATION, "https://w3id.org/semanticarts/ns/ontology/gist/", "foundation/gist_subset.ttl"),
            ("core_party_role", OntologyLayer.CORE, "https://example.org/vt/core/party-role/", "core/party_role.ttl"),
            ("core_event", OntologyLayer.CORE, "https://example.org/vt/core/event/", "core/event.ttl"),
            ("core_resource", OntologyLayer.CORE, "https://example.org/vt/core/resource/", "core/resource.ttl"),
            ("core_measurement", OntologyLayer.CORE, "https://example.org/vt/core/measurement/", "core/measurement.ttl"),
            ("core_provenance", OntologyLayer.CORE, "https://example.org/vt/core/provenance/", "core/provenance.ttl"),
            ("core_identity", OntologyLayer.CORE, "https://example.org/vt/core/identity/", "core/identity.ttl"),
            ("distributed_systems", OntologyLayer.DOMAIN, "https://example.org/vt/distributed-systems/", "distributed_systems/distributed_systems.ttl"),
            ("telecom", OntologyLayer.DOMAIN, "https://example.org/vt/telecom/", "telecom/telecom.ttl"),
            ("finance", OntologyLayer.DOMAIN, "https://example.org/vt/finance/", "finance/finance.ttl"),
            ("fintech", OntologyLayer.DOMAIN, "https://example.org/vt/fintech/", "fintech/fintech.ttl"),
            ("logistics", OntologyLayer.DOMAIN, "https://example.org/vt/logistics/", "logistics/logistics.ttl"),
            ("commerce", OntologyLayer.DOMAIN, "https://example.org/vt/commerce/", "commerce/commerce.ttl"),
            ("bridge_commerce_logistics", OntologyLayer.BRIDGE, "https://example.org/vt/bridge/", "bridges/commerce_logistics.ttl"),
        ]
        for name, layer, namespace, relative in definitions:
            path = self.root / relative
            graph = Graph()
            graph.parse(path, format="turtle")
            self.modules[name] = OntologyModule(name, layer, namespace, graph, path)
        return self

    def module(self, name: str) -> OntologyModule:
        return self.modules[name]

    def classes(self, module_names: list[str]) -> list[tuple[OntologyModule, URIRef, str, str]]:
        records = []
        for name in module_names:
            module = self.modules[name]
            for subject in module.graph.subjects(RDF.type, OWL.Class):
                label = next(module.graph.objects(subject, RDFS.label), subject.split("/")[-1])
                definition = next(module.graph.objects(subject, RDFS.comment), "")
                records.append((module, subject, str(label), str(definition)))
        return records

    def properties(self, module_names: list[str], property_type: URIRef | None = None) -> list[tuple[OntologyModule, URIRef, str, str, URIRef]]:
        records = []
        property_types = [property_type] if property_type else [OWL.ObjectProperty, OWL.DatatypeProperty]
        for name in module_names:
            module = self.modules[name]
            for kind in property_types:
                for subject in module.graph.subjects(RDF.type, kind):
                    label = next(module.graph.objects(subject, RDFS.label), subject.split("/")[-1])
                    definition = next(module.graph.objects(subject, RDFS.comment), "")
                    records.append((module, subject, str(label), str(definition), kind))
        return records

    def local_modules(self, domain: str) -> list[str]:
        return ["foundation", *[name for name, module in self.modules.items() if module.layer == OntologyLayer.CORE], domain]

    def serialise_module(self, name: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.module(name).graph.serialize(destination=destination, format="turtle")
