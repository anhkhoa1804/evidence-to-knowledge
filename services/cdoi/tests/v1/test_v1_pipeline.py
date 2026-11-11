import json
import shutil
from pathlib import Path

from rdflib import OWL, RDF, RDFS, URIRef

from cdoi.entity_resolution import DeterministicEntityResolver, EntityResolutionRelation
from cdoi.extraction import StructuredExtractor
from cdoi.models import ChangeAction, EntityCandidate, OntologyChangeProposal, Provenance, RiskLevel
from cdoi.ontology import OntologyStore
from cdoi.pipeline import ContinualIntegrationPipeline
from cdoi.preprocessing import preprocess
from cdoi.schema import DeterministicSchemaInducer
from cdoi.state import RunStateStore
from cdoi.validation import ProposalValidator


ROOT = Path(__file__).resolve().parents[2]


def runtime(tmp_path):
    root = tmp_path / "project"
    for name in ("ontologies", "data"):
        kwargs = {"ignore": shutil.ignore_patterns("external")} if name == "data" else {}
        shutil.copytree(ROOT / name, root / name, **kwargs)
    return root


def test_abox_evidence_is_induced_not_promoted_directly():
    path = ROOT / "data/fixtures/distributed_systems.json"
    graph = StructuredExtractor().extract(path, "distributed_systems", preprocess(path))
    schema = DeterministicSchemaInducer().induce(graph.entities, "distributed_systems", graph.provenance)
    pod = next(candidate for candidate in schema if candidate.canonical_label == "Kubernetes Pod")
    assert pod.supporting_abox_ids == ["pod-1"]
    assert pod.candidate_id != "pod-1"


def test_object_and_data_property_candidates_have_separate_paths():
    path = ROOT / "data/fixtures/commerce.json"
    graph = StructuredExtractor().extract(path, "commerce", preprocess(path))
    schema = DeterministicSchemaInducer().induce(graph.entities, "commerce", graph.provenance)
    by_label = {candidate.canonical_label: candidate.kind.value for candidate in schema}
    assert by_label["fulfilledBy"] == "OBJECT_PROPERTY"
    assert by_label["hasOrderAmount"] == "DATA_PROPERTY"


def test_property_alignment_creates_typed_property_proposals(tmp_path):
    root = runtime(tmp_path)
    result = ContinualIntegrationPipeline(root).ingest(root / "data/fixtures/commerce.json", "commerce")
    property_proposals = {proposal.source_concept: proposal.action.value for proposal in result.proposals if proposal.candidate_kind.value != "CLASS"}
    assert property_proposals["fulfilledBy"] == "ADD_OBJECT_PROPERTY"
    assert property_proposals["hasOrderAmount"] == "ADD_DATA_PROPERTY"


def test_review_pending_proposal_is_staged_and_survives_restart(tmp_path):
    root = runtime(tmp_path)
    pipeline = ContinualIntegrationPipeline(root)
    class PendingBuilder:
        def build(self, profile, decision, namespace):
            return OntologyChangeProposal(source_concept=profile.canonical_label, source_domain=profile.domain, action=ChangeAction.ADD_EQUIVALENCE, target_iri="https://example.org/vt/finance/BankAccount", confidence=0.9, risk_level=RiskLevel.VERY_HIGH, provenance=profile.provenance)
    pipeline.components.builder = PendingBuilder()
    result = pipeline.ingest(root / "data/fixtures/distributed_systems.json", "distributed_systems")
    assert result.staging_count > 0
    assert len(pipeline.components.kg.graph) == 0
    assert len(pipeline.components.kg.staging_graph) > 0
    assert RunStateStore(root / "data/integration_runs").pending()


def test_rejected_proposal_cannot_populate_canonical_kg(tmp_path):
    root = runtime(tmp_path)
    pipeline = ContinualIntegrationPipeline(root)
    class RejectedBuilder:
        def build(self, profile, decision, namespace):
            return OntologyChangeProposal(source_concept=profile.canonical_label, source_domain=profile.domain, action=ChangeAction.ADD_CLASS, proposed_axioms=["https://w3id.org/semanticarts/ns/ontology/gist/Organization rdfs:label \"bad\""], confidence=0.9, risk_level=RiskLevel.VERY_HIGH, provenance=profile.provenance)
    pipeline.components.builder = RejectedBuilder()
    pipeline.ingest(root / "data/fixtures/distributed_systems.json", "distributed_systems")
    assert len(pipeline.components.kg.graph) == 0
    assert len(pipeline.components.kg.staging_graph) > 0


def test_real_shacl_validation_is_exercised():
    store = OntologyStore(ROOT / "ontologies").load_defaults()
    proposal = OntologyChangeProposal(source_concept="Unlabelled", source_domain="finance", action=ChangeAction.ADD_CLASS, proposed_axioms=["https://example.org/vt/finance/Unlabelled a owl:Class"], confidence=0.8, risk_level=RiskLevel.MEDIUM, provenance=Provenance(input_domain="finance"))
    report = ProposalValidator(store).validate(proposal)
    assert not report.valid
    assert not report.shacl_conforms


def test_bridge_is_separate_from_equivalence_and_requires_approval(tmp_path):
    root = runtime(tmp_path)
    pipeline = ContinualIntegrationPipeline(root)
    pipeline.ingest(root / "data/fixtures/commerce.json", "commerce")
    pipeline.ingest(root / "data/fixtures/logistics.json", "logistics")
    bridge = pipeline.discover_mappings()[0]
    assert not pipeline.commit_bridge(bridge, approved=False)
    assert bridge.status == "review_pending"
    assert (root / "data/integration_runs/bridge_proposals" / f"{bridge.proposal_id}.json").exists()
    assert pipeline.commit_bridge(bridge, approved=True)
    graph = pipeline.store.module("bridge_commerce_logistics").graph
    assert (URIRef(bridge.source_iri), URIRef(bridge.predicate_iri), URIRef(bridge.target_iri)) in graph


def test_idempotent_reingestion_and_replay_determinism(tmp_path):
    root = runtime(tmp_path)
    pipeline = ContinualIntegrationPipeline(root)
    first = pipeline.ingest(root / "data/fixtures/finance.json", "finance")
    triples = len(pipeline.store.module("finance").graph)
    second = pipeline.ingest(root / "data/fixtures/finance.json", "finance")
    assert len(pipeline.store.module("finance").graph) == triples
    assert all(proposal.action.value == "NO_CHANGE" for proposal in second.proposals)
    replay_parent = tmp_path / "replay"
    replay_parent.mkdir()
    replay = ContinualIntegrationPipeline(runtime(replay_parent))
    again = replay.ingest(replay.root / "data/fixtures/finance.json", "finance")
    assert [(item.source_concept, item.relation) for item in first.decisions] == [(item.source_concept, item.relation) for item in again.decisions]


def test_entity_resolution_never_asserts_same_as_from_weak_evidence():
    decision = DeterministicEntityResolver().resolve(EntityCandidate(id="customer-123", surface="Customer"), EntityCandidate(id="subscriber-456", surface="Subscriber"))
    assert decision.relation == EntityResolutionRelation.UNRESOLVED
