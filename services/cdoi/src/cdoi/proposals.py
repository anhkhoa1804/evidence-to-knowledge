from __future__ import annotations

from .models import AlignmentDecision, AlignmentRelation, ChangeAction, ConceptProfile, OntologyChangeProposal, RiskLevel, SchemaCandidateKind


def classify_risk(action: ChangeAction, source_domain: str, target_iri: str | None = None) -> RiskLevel:
    if action == ChangeAction.ADD_EQUIVALENCE:
        return RiskLevel.VERY_HIGH
    if target_iri and "semanticarts" in target_iri and action not in {ChangeAction.ADD_MAPPING, ChangeAction.NO_CHANGE}:
        return RiskLevel.VERY_HIGH
    if action in {ChangeAction.ADD_SUBCLASS, ChangeAction.ADD_MAPPING, ChangeAction.PROMOTE_TO_SHARED, ChangeAction.ADD_BRIDGE_MAPPING}:
        return RiskLevel.HIGH
    if action in {ChangeAction.ADD_CLASS, ChangeAction.ADD_OBJECT_PROPERTY, ChangeAction.ADD_DATA_PROPERTY, ChangeAction.KEEP_DOMAIN_LOCAL}:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class ProposalBuilder:
    def build(self, profile: ConceptProfile, decision: AlignmentDecision, namespace: str) -> OntologyChangeProposal:
        source_iri = namespace + profile.canonical_label.replace(" ", "")
        action_by_relation = {
            AlignmentRelation.NEW_CONCEPT: ChangeAction.ADD_CLASS,
            AlignmentRelation.SUBCLASS_OF: ChangeAction.ADD_SUBCLASS,
            AlignmentRelation.SUPERCLASS_OF: ChangeAction.ADD_MAPPING,
            AlignmentRelation.EQUIVALENT: ChangeAction.ADD_MAPPING,
            AlignmentRelation.RELATED_TO: ChangeAction.KEEP_DOMAIN_LOCAL,
            AlignmentRelation.UNRESOLVED: ChangeAction.UNRESOLVED,
        }
        action = action_by_relation[decision.relation]
        if decision.relation == AlignmentRelation.NEW_CONCEPT and profile.kind == SchemaCandidateKind.OBJECT_PROPERTY:
            action = ChangeAction.ADD_OBJECT_PROPERTY
        if decision.relation == AlignmentRelation.NEW_CONCEPT and profile.kind == SchemaCandidateKind.DATA_PROPERTY:
            action = ChangeAction.ADD_DATA_PROPERTY
        if decision.relation == AlignmentRelation.EQUIVALENT and decision.target_concept and decision.target_concept.startswith(namespace):
            action = ChangeAction.NO_CHANGE
        axioms: list[str] = []
        if action == ChangeAction.ADD_CLASS:
            axioms = [f"{source_iri} a owl:Class", f'{source_iri} rdfs:label "{profile.canonical_label}"']
        elif action == ChangeAction.ADD_SUBCLASS and decision.target_concept:
            axioms = [f"{source_iri} rdfs:subClassOf {decision.target_concept}", f'{source_iri} rdfs:label "{profile.canonical_label}"']
        elif action == ChangeAction.ADD_MAPPING and decision.target_concept:
            axioms = [f"{source_iri} skos:exactMatch {decision.target_concept}"]
        elif action in {ChangeAction.ADD_OBJECT_PROPERTY, ChangeAction.ADD_DATA_PROPERTY}:
            property_type = "owl:ObjectProperty" if action == ChangeAction.ADD_OBJECT_PROPERTY else "owl:DatatypeProperty"
            axioms = [f"{source_iri} a {property_type}", f'{source_iri} rdfs:label "{profile.canonical_label}"']
        return OntologyChangeProposal(source_concept=profile.canonical_label, source_domain=profile.domain, action=action, target_iri=decision.target_concept, proposed_axioms=axioms, confidence=decision.confidence, risk_level=classify_risk(action, profile.domain, decision.target_concept), evidence=decision.evidence + decision.warnings, provenance=profile.provenance, candidate_id=profile.candidate_id, candidate_kind=profile.kind)
