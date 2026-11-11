from pathlib import Path

from rdflib import OWL, RDFS, URIRef

from cdoi.models import ChangeAction, OntologyChangeProposal, Provenance, RiskLevel
from cdoi.ontology import OntologyStore
from cdoi.proposals import classify_risk
from cdoi.validation import ProposalValidator


ROOT = Path(__file__).resolve().parents[2]


def proposal(action, domain="finance", target=None, axioms=None):
    return OntologyChangeProposal(source_concept="User Account", source_domain=domain, action=action, target_iri=target, proposed_axioms=axioms or [], confidence=0.95, risk_level=classify_risk(action, domain, target), provenance=Provenance(input_domain=domain))


def test_bank_account_and_user_account_are_not_automatically_equivalent():
    assert classify_risk(ChangeAction.ADD_EQUIVALENCE, "distributed_systems", "https://example.org/vt/finance/BankAccount") == RiskLevel.VERY_HIGH


def test_foundation_mutation_is_rejected():
    store = OntologyStore(ROOT / "ontologies").load_defaults()
    bad = proposal(ChangeAction.ADD_CLASS, axioms=["https://w3id.org/semanticarts/ns/ontology/gist/Organization rdfs:label \"changed\""])
    report = ProposalValidator(store).validate(bad)
    assert not report.valid
    assert any("immutable" in error for error in report.errors)


def test_taxonomy_cycle_is_rejected():
    store = OntologyStore(ROOT / "ontologies").load_defaults()
    graph = store.module("finance").graph
    namespace = store.module("finance").namespace
    a, b, c = (URIRef(namespace + value) for value in ("A", "B", "C"))
    for node in (a, b, c):
        graph.add((node, __import__("rdflib").RDF.type, OWL.Class))
    graph.add((a, RDFS.subClassOf, b))
    graph.add((b, RDFS.subClassOf, c))
    bad = OntologyChangeProposal(source_concept="C", source_domain="finance", action=ChangeAction.ADD_SUBCLASS, target_iri=str(a), proposed_axioms=[f"{c} rdfs:subClassOf {a}"], confidence=0.9, risk_level=RiskLevel.HIGH, provenance=Provenance(input_domain="finance"))
    assert not ProposalValidator(store).validate(bad).valid


def test_cross_domain_equivalence_requires_human_review():
    store = OntologyStore(ROOT / "ontologies").load_defaults()
    item = proposal(ChangeAction.ADD_EQUIVALENCE, "distributed_systems", "https://example.org/vt/finance/BankAccount")
    report = ProposalValidator(store).validate(item)
    assert report.valid
    assert report.requires_human_review
    assert report.risk_level == RiskLevel.VERY_HIGH
