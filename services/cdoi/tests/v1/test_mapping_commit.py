from pathlib import Path
from rdflib import SKOS, URIRef

from cdoi.models import ChangeAction, OntologyChangeProposal, Provenance, RiskLevel
from cdoi.ontology import OntologyStore
from cdoi.merge import ProposalApplier
from cdoi.validation import ProposalValidator
from cdoi.versioning import VersionStore


ROOT = Path(__file__).resolve().parents[2]


def test_approved_mapping_is_materialized_in_domain_graph(tmp_path):
    import shutil
    root = tmp_path / "project"
    shutil.copytree(ROOT / "ontologies", root / "ontologies")
    store = OntologyStore(root / "ontologies").load_defaults()
    versions = VersionStore(root / "data/ontology_versions", store)
    proposal = OntologyChangeProposal(source_concept="Organization", source_domain="distributed_systems", action=ChangeAction.ADD_MAPPING, target_iri="https://w3id.org/semanticarts/ns/ontology/gist/Organization", proposed_axioms=["mapping"], confidence=0.9, risk_level=RiskLevel.HIGH, provenance=Provenance(input_domain="distributed_systems"))
    report = ProposalValidator(store).validate(proposal)
    ProposalApplier(store, versions).apply_batch([proposal], [report], "run-mapping")
    source = URIRef(store.module("distributed_systems").namespace + "Organization")
    assert (source, SKOS.exactMatch, URIRef(proposal.target_iri)) in store.module("distributed_systems").graph
