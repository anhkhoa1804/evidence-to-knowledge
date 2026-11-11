from pathlib import Path

from cdoi.alignment import ConservativeAligner
from cdoi.conceptualization import MockConceptualizer
from cdoi.models import AlignmentRelation, EntityCandidate, OntologyCandidate, OntologyLayer, Provenance
from cdoi.ontology import OntologyStore
from cdoi.retrieval import HybridRetriever


ROOT = Path(__file__).resolve().parents[2]


def test_kubernetes_pod_is_placed_under_runtime_environment():
    provenance = Provenance(input_domain="distributed_systems")
    profile = MockConceptualizer().conceptualize(EntityCandidate(id="pod", surface="Kubernetes Pod", definition="A deployable runtime unit in a container orchestration environment.", relations=["runsOn(Node)", "contains(Container)"]), "distributed_systems", provenance)
    candidates = HybridRetriever(OntologyStore(ROOT / "ontologies").load_defaults()).retrieve(profile)
    decision = ConservativeAligner().align(profile, candidates)
    assert decision.relation == AlignmentRelation.SUBCLASS_OF
    assert decision.target_concept and decision.target_concept.endswith("RuntimeEnvironment")


def test_cross_domain_same_label_is_not_equivalent():
    provenance = Provenance(input_domain="logistics")
    profile = MockConceptualizer().conceptualize(EntityCandidate(id="s", surface="Settlement", definition="A named populated place used as a delivery destination."), "logistics", provenance)
    finance = OntologyCandidate(iri="https://example.org/vt/finance/Settlement", label="Settlement", definition="Completion of financial obligations between counterparties.", namespace="https://example.org/vt/finance/", ontology_layer=OntologyLayer.DOMAIN, domain="finance", lexical_score=1.0, final_retrieval_score=1.0)
    decision = ConservativeAligner().align(profile, [finance])
    assert decision.relation != AlignmentRelation.EQUIVALENT
    assert decision.relation == AlignmentRelation.UNRESOLVED


def test_new_concept_is_explicit():
    provenance = Provenance(input_domain="logistics")
    profile = MockConceptualizer().conceptualize(EntityCandidate(id="cold", surface="Cold Chain Checkpoint", definition="Temperature checkpoint."), "logistics", provenance)
    decision = ConservativeAligner().align(profile, [])
    assert decision.relation == AlignmentRelation.NEW_CONCEPT


def test_exact_local_class_is_reused_not_duplicated():
    provenance = Provenance(input_domain="finance")
    profile = MockConceptualizer().conceptualize(EntityCandidate(id="account", surface="Bank Account", definition="A deposit account maintained by a financial institution."), "finance", provenance)
    decision = ConservativeAligner().align(profile, HybridRetriever(OntologyStore(ROOT / "ontologies").load_defaults()).retrieve(profile))
    assert decision.relation == AlignmentRelation.EQUIVALENT
