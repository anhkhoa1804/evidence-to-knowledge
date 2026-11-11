from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceReference(BaseModel):
    source_path: str
    source_system: str = "fixture"
    source_span: str = ""
    hierarchy: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    reference: SourceReference
    text: str
    confidence: float = 1.0


class Provenance(BaseModel):
    extraction_id: str = Field(default_factory=lambda: f"ext-{uuid4().hex[:12]}")
    input_domain: str
    model: str = "deterministic-structured-extractor"
    model_version: str = "v1"
    timestamp: datetime = Field(default_factory=utc_now)
    human_review_status: str = "not_required"
    run_id: str | None = None
    prompt_version: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class EntityCandidate(BaseModel):
    """An extracted ABox entity observation, never a TBox class by itself."""
    id: str
    surface: str
    type_hint: str | None = None
    definition: str = ""
    relations: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class RelationCandidate(BaseModel):
    subject: str
    predicate: str
    object: str
    evidence: list[Evidence] = Field(default_factory=list)


class EventCandidate(BaseModel):
    id: str
    surface: str
    event_type: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class SemanticCandidateGraph(BaseModel):
    domain: str
    entities: list[EntityCandidate] = Field(default_factory=list)
    relations: list[RelationCandidate] = Field(default_factory=list)
    events: list[EventCandidate] = Field(default_factory=list)
    provenance: Provenance


class SchemaCandidateKind(str, Enum):
    CLASS = "CLASS"
    OBJECT_PROPERTY = "OBJECT_PROPERTY"
    DATA_PROPERTY = "DATA_PROPERTY"


class SchemaCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"schema-{uuid4().hex[:12]}")
    kind: SchemaCandidateKind
    canonical_label: str
    domain: str
    definition: str = ""
    type_hints: list[str] = Field(default_factory=list)
    relation_signature: set[str] = Field(default_factory=set)
    supporting_abox_ids: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    provenance: Provenance


class ClassCandidate(SchemaCandidate):
    kind: SchemaCandidateKind = SchemaCandidateKind.CLASS
    abstraction_candidates: list[str] = Field(default_factory=list)


class ObjectPropertyCandidate(SchemaCandidate):
    kind: SchemaCandidateKind = SchemaCandidateKind.OBJECT_PROPERTY
    domain_hints: list[str] = Field(default_factory=list)
    range_hints: list[str] = Field(default_factory=list)


class DataPropertyCandidate(SchemaCandidate):
    kind: SchemaCandidateKind = SchemaCandidateKind.DATA_PROPERTY
    datatype_hint: str = "string"


class ConceptProfile(BaseModel):
    candidate_id: str
    canonical_label: str
    local_definition: str
    abstraction_candidates: list[str] = Field(default_factory=list)
    semantic_features: set[str] = Field(default_factory=set)
    relation_signature: set[str] = Field(default_factory=set)
    domain: str
    source_candidates: list[str] = Field(default_factory=list)
    provenance: Provenance
    kind: SchemaCandidateKind = SchemaCandidateKind.CLASS


class OntologyLayer(str, Enum):
    FOUNDATION = "L0_FOUNDATION"
    CORE = "ENTERPRISE_CORE"
    SHARED = "ENTERPRISE_CORE"  # V0 compatibility alias; new code uses CORE modules.
    DOMAIN = "DOMAIN"
    BRIDGE = "BRIDGE"
    APPLICATION = "APPLICATION"
    REFERENCE = "REFERENCE"


class OntologyCandidate(BaseModel):
    iri: str
    label: str
    definition: str = ""
    namespace: str
    ontology_layer: OntologyLayer
    domain: str | None = None
    lexical_score: float = 0.0
    embedding_score: float = 0.0
    structural_score: float = 0.0
    relation_signature_score: float = 0.0
    neighborhood_score: float = 0.0
    domain_score: float = 0.0
    final_retrieval_score: float = 0.0
    candidate_kind: SchemaCandidateKind = SchemaCandidateKind.CLASS


class AlignmentRelation(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    SUBCLASS_OF = "SUBCLASS_OF"
    SUPERCLASS_OF = "SUPERCLASS_OF"
    RELATED_TO = "RELATED_TO"
    NEW_CONCEPT = "NEW_CONCEPT"
    UNRESOLVED = "UNRESOLVED"


class PropertyAlignmentRelation(str, Enum):
    EQUIVALENT_PROPERTY = "EQUIVALENT_PROPERTY"
    SUBPROPERTY_OF = "SUBPROPERTY_OF"
    RELATED_PROPERTY = "RELATED_PROPERTY"
    NEW_PROPERTY = "NEW_PROPERTY"
    UNRESOLVED_PROPERTY = "UNRESOLVED_PROPERTY"


class AlignmentDecision(BaseModel):
    source_concept: str
    relation: AlignmentRelation
    target_concept: str | None = None
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    semantic_features_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    candidate_kind: SchemaCandidateKind = SchemaCandidateKind.CLASS


class ChangeAction(str, Enum):
    ADD_CLASS = "ADD_CLASS"
    ADD_SUBCLASS = "ADD_SUBCLASS"
    ADD_OBJECT_PROPERTY = "ADD_OBJECT_PROPERTY"
    ADD_DATA_PROPERTY = "ADD_DATA_PROPERTY"
    ADD_ALIAS = "ADD_ALIAS"
    ADD_MAPPING = "ADD_MAPPING"
    ADD_EQUIVALENCE = "ADD_EQUIVALENCE"
    KEEP_DOMAIN_LOCAL = "KEEP_DOMAIN_LOCAL"
    PROMOTE_TO_SHARED = "PROMOTE_TO_SHARED"
    NO_CHANGE = "NO_CHANGE"
    UNRESOLVED = "UNRESOLVED"
    ADD_BRIDGE_MAPPING = "ADD_BRIDGE_MAPPING"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class OntologyChangeProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"prop-{uuid4().hex[:12]}")
    source_concept: str
    source_domain: str
    action: ChangeAction
    target_iri: str | None = None
    proposed_axioms: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    risk_level: RiskLevel
    evidence: list[str] = Field(default_factory=list)
    provenance: Provenance
    status: str = "proposed"
    run_id: str | None = None
    candidate_id: str | None = None
    candidate_kind: SchemaCandidateKind = SchemaCandidateKind.CLASS
    impact: dict[str, Any] = Field(default_factory=dict)


class BridgeProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: f"bridge-{uuid4().hex[:12]}")
    source_iri: str
    predicate_iri: str
    target_iri: str
    source_domain: str
    target_domain: str
    bridge_module: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    provenance: Provenance
    status: str = "proposed"


class IntegrationRun(BaseModel):
    run_id: str = Field(default_factory=lambda: f"run-{uuid4().hex[:12]}")
    source_path: str
    domain: str
    ontology_version: str | None = None
    status: str = "started"
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    proposal_ids: list[str] = Field(default_factory=list)


class ProposalState(BaseModel):
    proposal: OntologyChangeProposal
    validation: "ValidationReport | None" = None
    review_decision: str = "pending"
    final_mapping_status: str = "staged"
    ontology_version: str | None = None


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    logical_checks: dict[str, bool] = Field(default_factory=dict)
    policy_checks: dict[str, bool] = Field(default_factory=dict)
    risk_level: RiskLevel
    requires_human_review: bool = False
    shacl_conforms: bool = True
    reasoner: str = "rdflib-taxonomy"
    impact: dict[str, Any] = Field(default_factory=dict)


class VersionRecord(BaseModel):
    version: str
    parent_version: str | None
    proposal_ids: list[str]
    added_axioms: list[str]
    removed_axioms: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
    source_domains: list[str]
    validation: ValidationReport
    approval: str
    run_id: str | None = None
