from __future__ import annotations

from rdflib import Graph, RDF, RDFS, OWL, Literal, Namespace, URIRef
from pyshacl import validate as shacl_validate

from .models import ChangeAction, OntologyChangeProposal, RiskLevel, ValidationReport
from .ontology import OntologyStore
from .reasoning import Reasoner, TaxonomyReasoner
from .impact import ImpactAnalyzer


class ProposalValidator:
    def __init__(self, store: OntologyStore, reasoner: Reasoner | None = None, impact_analyzer: ImpactAnalyzer | None = None):
        self.store = store
        self.reasoner = reasoner or TaxonomyReasoner()
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer(store)

    def _would_cycle(self, subject: str, parent: str, domain: str) -> bool:
        graph = self.store.module(domain).graph
        frontier = [URIRef(parent)]
        seen: set[URIRef] = set()
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            if str(node) == subject:
                return True
            frontier.extend(graph.objects(node, RDFS.subClassOf))
        return False

    def validate(self, proposal: OntologyChangeProposal) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        foundation_iri = self.store.module("foundation").namespace
        source_namespace = self.store.module(proposal.source_domain).namespace if proposal.source_domain in self.store.modules else ""
        modifies_foundation = any(axiom.startswith(foundation_iri) for axiom in proposal.proposed_axioms)
        if modifies_foundation:
            errors.append("Foundation ontology is immutable; a proposed axiom has a foundation subject.")
        if proposal.action == ChangeAction.ADD_EQUIVALENCE and proposal.source_domain != "shared":
            warnings.append("Cross-module equivalence is very high risk and requires human approval.")
        if proposal.action == ChangeAction.ADD_SUBCLASS and proposal.target_iri:
            subject = source_namespace + proposal.source_concept.replace(" ", "")
            if self.reasoner.has_taxonomy_cycle(self.store.module(proposal.source_domain).graph, URIRef(subject), URIRef(proposal.target_iri)):
                errors.append("Proposed subclass relation creates a taxonomy cycle.")
        if proposal.action in {ChangeAction.ADD_CLASS, ChangeAction.ADD_SUBCLASS} and source_namespace and not all(axiom.startswith(source_namespace) for axiom in proposal.proposed_axioms):
            errors.append("Namespace policy requires new domain axioms to have a domain-local subject.")
        duplicate_label = False
        if proposal.action == ChangeAction.ADD_CLASS:
            graph = self.store.module(proposal.source_domain).graph
            duplicate_label = any(str(label).casefold() == proposal.source_concept.casefold() for label in graph.objects(None, RDFS.label))
            if duplicate_label:
                warnings.append("A class with this label already exists in the target module.")
        shacl_conforms = self._shacl_conforms(proposal)
        if not shacl_conforms:
            errors.append("SHACL label constraint failed for proposed schema resource.")
        requires_review = proposal.risk_level == RiskLevel.VERY_HIGH
        impact = self.impact_analyzer.analyze(proposal)
        proposal.impact = impact
        return ValidationReport(valid=not errors, errors=errors, warnings=warnings, logical_checks={"taxonomy_cycle": not any("cycle" in error for error in errors), "reasoner_available": True, "shacl_basic": shacl_conforms}, policy_checks={"foundation_immutable": not modifies_foundation, "namespace_policy": not any("Namespace" in error for error in errors), "cross_domain_equivalence_guard": proposal.action != ChangeAction.ADD_EQUIVALENCE or requires_review}, risk_level=proposal.risk_level, requires_human_review=requires_review, shacl_conforms=shacl_conforms, reasoner=self.reasoner.name, impact=impact)

    def _shacl_conforms(self, proposal: OntologyChangeProposal) -> bool:
        if proposal.action not in {ChangeAction.ADD_CLASS, ChangeAction.ADD_SUBCLASS, ChangeAction.ADD_OBJECT_PROPERTY, ChangeAction.ADD_DATA_PROPERTY}:
            return True
        data = Graph()
        shapes = Graph()
        sh = Namespace("http://www.w3.org/ns/shacl#")
        source = URIRef(self.store.module(proposal.source_domain).namespace + proposal.source_concept.replace(" ", ""))
        kind = OWL.Class if proposal.action in {ChangeAction.ADD_CLASS, ChangeAction.ADD_SUBCLASS} else OWL.ObjectProperty if proposal.action == ChangeAction.ADD_OBJECT_PROPERTY else OWL.DatatypeProperty
        data.add((source, RDF.type, kind))
        if any("rdfs:label" in axiom for axiom in proposal.proposed_axioms):
            data.add((source, RDFS.label, Literal(proposal.source_concept)))
        shape = URIRef("https://example.org/shapes/SchemaLabelShape")
        shapes.add((shape, RDF.type, sh.NodeShape))
        shapes.add((shape, sh.targetClass, kind))
        prop = URIRef("https://example.org/shapes/SchemaLabelProperty")
        shapes.add((shape, sh.property, prop))
        shapes.add((prop, sh.path, RDFS.label))
        shapes.add((prop, sh.minCount, Literal(1)))
        conforms, _, _ = shacl_validate(data_graph=data, shacl_graph=shapes, inference="none", abort_on_first=False)
        return bool(conforms)
