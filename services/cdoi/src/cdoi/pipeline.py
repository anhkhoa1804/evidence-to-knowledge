from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .alignment import ConservativeAligner
from .conceptualization import MockConceptualizer
from .entity_resolution import DeterministicEntityResolver
from .extraction import StructuredExtractor
from .kg import KnowledgeGraphPopulator
from .mapping import CrossDomainMappingDiscovery
from .models import AlignmentDecision, BridgeProposal, ClassCandidate, ConceptProfile, IntegrationRun, OntologyChangeProposal, ProposalState, SchemaCandidate, ValidationReport
from .ontology import OntologyStore
from .preprocessing import preprocess
from .promotion import PromotionEngine
from .proposals import ProposalBuilder
from .retrieval import HybridRetriever
from .schema import DeterministicSchemaInducer
from .state import RunStateStore
from .validation import ProposalValidator
from .versioning import VersionStore
from .merge import ProposalApplier


@dataclass
class PipelineComponents:
    extractor: object
    inducer: object
    conceptualizer: object
    retriever: object
    aligner: object
    builder: object
    validator: object
    applier: object
    kg: KnowledgeGraphPopulator
    resolver: object


@dataclass
class IngestResult:
    domain: str
    run: IntegrationRun
    abox_entities: list = field(default_factory=list)
    schema_candidates: list[SchemaCandidate] = field(default_factory=list)
    profiles: list[ConceptProfile] = field(default_factory=list)
    decisions: list[AlignmentDecision] = field(default_factory=list)
    proposals: list[OntologyChangeProposal] = field(default_factory=list)
    validations: list[ValidationReport] = field(default_factory=list)
    accepted_versions: list[str] = field(default_factory=list)
    staging_count: int = 0
    bridge_proposals: list[BridgeProposal] = field(default_factory=list)


class ContinualIntegrationPipeline:
    """Orchestrates injected components; semantic decisions belong to the collaborators."""

    def __init__(self, project_root: Path, components: PipelineComponents | None = None, debug_per_proposal_commits: bool = False):
        self.root = project_root
        self.store = OntologyStore(project_root / "ontologies").load_defaults()
        self.versions = VersionStore(project_root / "data" / "ontology_versions", self.store)
        self.versions.initialise()
        self.state = RunStateStore(project_root / "data" / "integration_runs")
        self.debug_per_proposal_commits = debug_per_proposal_commits
        self.components = components or self._default_components()
        self.profiles: list[ConceptProfile] = []
        self.schema_candidates: list[SchemaCandidate] = []
        self.bridge_proposals: list[BridgeProposal] = []

    def _default_components(self) -> PipelineComponents:
        validator = ProposalValidator(self.store)
        return PipelineComponents(StructuredExtractor(), DeterministicSchemaInducer(), MockConceptualizer(), HybridRetriever(self.store), ConservativeAligner(), ProposalBuilder(), validator, ProposalApplier(self.store, self.versions), KnowledgeGraphPopulator(), DeterministicEntityResolver())

    def ingest(self, path: Path, domain: str, approved_ids: set[str] | None = None) -> IngestResult:
        run = IntegrationRun(source_path=str(path), domain=domain, ontology_version=self.versions.latest())
        self.state.save_run(run)
        chunks = preprocess(path)
        graph = self.components.extractor.extract(path, domain, chunks)
        graph.provenance.run_id = run.run_id
        schema_candidates = self.components.inducer.induce(graph.entities, domain, graph.provenance)
        run_dir = self.root / "data" / "integration_runs" / run.run_id
        (run_dir / "candidate_graph.json").write_text(graph.model_dump_json(indent=2), encoding="utf-8")
        (run_dir / "schema_candidates.json").write_text(json.dumps([candidate.model_dump(mode="json") for candidate in schema_candidates], indent=2), encoding="utf-8")
        result = IngestResult(domain=domain, run=run, abox_entities=graph.entities, schema_candidates=schema_candidates)
        namespace = self.store.module(domain).namespace
        for candidate in schema_candidates:
            profile = self.components.conceptualizer.conceptualize(candidate, domain, graph.provenance)
            candidates = self.components.retriever.retrieve(profile)
            decision = self.components.aligner.align(profile, candidates)
            proposal = self.components.builder.build(profile, decision, namespace)
            proposal.run_id = run.run_id
            validation = self.components.validator.validate(proposal)
            state = ProposalState(proposal=proposal, validation=validation, review_decision="pending" if validation.requires_human_review else "automatic", final_mapping_status="review_pending" if validation.requires_human_review else "staged")
            self.state.save_proposal(run.run_id, state)
            result.profiles.append(profile); result.decisions.append(decision); result.proposals.append(proposal); result.validations.append(validation)
        version = self.components.applier.apply_batch(result.proposals, result.validations, run.run_id, approved_ids)
        committable = {"ADD_CLASS", "ADD_SUBCLASS", "ADD_OBJECT_PROPERTY", "ADD_DATA_PROPERTY", "ADD_MAPPING", "NO_CHANGE"}
        accepted_ids = {proposal.proposal_id for proposal in result.proposals if proposal.status == "accepted" and proposal.action.value in committable}
        for proposal, validation in zip(result.proposals, result.validations):
            persisted = self.state.load_proposal(run.run_id, proposal.proposal_id)
            if proposal.proposal_id in accepted_ids:
                persisted.final_mapping_status = "approved"; persisted.ontology_version = version.version if version else self.versions.latest(); persisted.review_decision = "approved"
            elif validation.requires_human_review:
                persisted.final_mapping_status = "review_pending"
            elif not validation.valid:
                persisted.final_mapping_status = "rejected"; persisted.review_decision = "rejected"
            self.state.save_proposal(run.run_id, persisted)
        for candidate, decision, proposal in zip(schema_candidates, result.decisions, result.proposals):
            if not isinstance(candidate, ClassCandidate):
                continue
            approved = proposal.proposal_id in accepted_ids
            for entity_id in candidate.supporting_abox_ids:
                entity = next(item for item in graph.entities if item.id == entity_id)
                self.components.kg.populate(entity, decision, namespace, version.version if approved and version else self.versions.latest(), approved=approved)
                if not approved:
                    result.staging_count += 1
        run.proposal_ids = [proposal.proposal_id for proposal in result.proposals]
        run.ontology_version = version.version if version else self.versions.latest()
        run.status = "committed" if version else "review_or_staging"
        run.completed_at = datetime.now(timezone.utc)
        self.state.save_run(run)
        if version:
            result.accepted_versions.append(version.version)
        self.profiles.extend(result.profiles)
        self.schema_candidates.extend(schema_candidates)
        return result

    def discover_mappings(self) -> list[BridgeProposal]:
        class_candidates = [candidate for candidate in self.schema_candidates if isinstance(candidate, ClassCandidate)]
        bridges = CrossDomainMappingDiscovery(self.store).discover(class_candidates, class_candidates[0].provenance) if class_candidates else []
        for bridge in bridges:
            self.state.save_bridge(bridge)
        self.bridge_proposals.extend(bridges)
        return bridges

    def commit_bridge(self, proposal: BridgeProposal, approved: bool = False) -> bool:
        """A bridge is independently owned and never implies identity or core promotion."""
        if not approved:
            proposal.status = "review_pending"
            self.state.save_bridge(proposal)
            return False
        from rdflib import URIRef
        module = self.store.module(f"bridge_{proposal.bridge_module}")
        module.graph.add((URIRef(proposal.source_iri), URIRef(proposal.predicate_iri), URIRef(proposal.target_iri)))
        proposal.status = "approved"
        self.state.save_bridge(proposal)
        return True

    def promote(self) -> list[OntologyChangeProposal]:
        return PromotionEngine().propose(self.schema_candidates, self.bridge_proposals)

    def export_kg(self) -> Path:
        destination = self.root / "data" / "outputs" / "knowledge_graph.ttl"
        self.components.kg.export_turtle(destination)
        self.components.kg.export_staging_turtle(self.root / "data" / "outputs" / "staging_knowledge_graph.ttl")
        return destination


def demo(project_root: Path, order: list[str] | None = None) -> tuple[list[IngestResult], list[OntologyChangeProposal], Path]:
    pipeline = ContinualIntegrationPipeline(project_root)
    order = order or ["distributed_systems", "commerce", "logistics", "finance", "fintech", "telecom"]
    results = [pipeline.ingest(project_root / "data" / "fixtures" / f"{domain}.json", domain) for domain in order]
    bridges = pipeline.discover_mappings()
    if results:
        results[-1].bridge_proposals = bridges
    proposals = pipeline.promote()
    return results, proposals, pipeline.export_kg()
