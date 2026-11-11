from __future__ import annotations

from rdflib import OWL, RDF, RDFS, SKOS, Literal, URIRef

from .models import ChangeAction, OntologyChangeProposal, ValidationReport
from .ontology import OntologyStore
from .versioning import VersionStore


class ReviewGate:
    def decide(self, proposal: OntologyChangeProposal, report: ValidationReport, approved: bool = False) -> bool:
        return report.valid and (not report.requires_human_review or approved)


class ProposalApplier:
    def __init__(self, store: OntologyStore, versions: VersionStore):
        self.store = store
        self.versions = versions

    def apply(self, proposal: OntologyChangeProposal, report: ValidationReport, approved: bool = False):
        if not ReviewGate().decide(proposal, report, approved):
            proposal.status = "rejected" if not report.valid else "review_required"
            return None
        if proposal.action == ChangeAction.NO_CHANGE:
            proposal.status = "accepted"
            return None
        graph = self.store.module(proposal.source_domain).graph
        namespace = self.store.module(proposal.source_domain).namespace
        source = URIRef(namespace + proposal.source_concept.replace(" ", ""))
        if proposal.action == ChangeAction.ADD_CLASS:
            graph.add((source, RDFS.label, Literal(proposal.source_concept)))
            graph.add((source, RDF.type, OWL.Class))
        elif proposal.action == ChangeAction.ADD_SUBCLASS and proposal.target_iri:
            graph.add((source, RDFS.label, Literal(proposal.source_concept)))
            graph.add((source, RDF.type, OWL.Class))
            graph.add((source, RDFS.subClassOf, URIRef(proposal.target_iri)))
        elif proposal.action in {ChangeAction.ADD_OBJECT_PROPERTY, ChangeAction.ADD_DATA_PROPERTY}:
            graph.add((source, RDFS.label, Literal(proposal.source_concept)))
            graph.add((source, RDF.type, OWL.ObjectProperty if proposal.action == ChangeAction.ADD_OBJECT_PROPERTY else OWL.DatatypeProperty))
        elif proposal.action == ChangeAction.ADD_MAPPING and proposal.target_iri:
            graph.add((source, SKOS.exactMatch, URIRef(proposal.target_iri)))
        proposal.status = "accepted"
        return self.versions.commit(proposal, report, approval="human" if approved else "automatic")

    def apply_batch(self, proposals: list[OntologyChangeProposal], reports: list[ValidationReport], run_id: str, approved_ids: set[str] | None = None):
        approved_ids = approved_ids or set()
        accepted = [(proposal, report) for proposal, report in zip(proposals, reports) if ReviewGate().decide(proposal, report, proposal.proposal_id in approved_ids)]
        for proposal, report in accepted:
            proposal.status = "accepted"
            graph = self.store.module(proposal.source_domain).graph
            namespace = self.store.module(proposal.source_domain).namespace
            source = URIRef(namespace + proposal.source_concept.replace(" ", ""))
            if proposal.action == ChangeAction.ADD_CLASS:
                graph.add((source, RDF.type, OWL.Class)); graph.add((source, RDFS.label, Literal(proposal.source_concept)))
            elif proposal.action == ChangeAction.ADD_SUBCLASS and proposal.target_iri:
                graph.add((source, RDF.type, OWL.Class)); graph.add((source, RDFS.label, Literal(proposal.source_concept))); graph.add((source, RDFS.subClassOf, URIRef(proposal.target_iri)))
            elif proposal.action in {ChangeAction.ADD_OBJECT_PROPERTY, ChangeAction.ADD_DATA_PROPERTY}:
                graph.add((source, RDF.type, OWL.ObjectProperty if proposal.action == ChangeAction.ADD_OBJECT_PROPERTY else OWL.DatatypeProperty)); graph.add((source, RDFS.label, Literal(proposal.source_concept)))
            elif proposal.action == ChangeAction.ADD_MAPPING and proposal.target_iri:
                graph.add((source, SKOS.exactMatch, URIRef(proposal.target_iri)))
        material = [(proposal, report) for proposal, report in accepted if proposal.action != ChangeAction.NO_CHANGE]
        if not material:
            return None
        return self.versions.commit_batch([item[0] for item in material], [item[1] for item in material], run_id)
