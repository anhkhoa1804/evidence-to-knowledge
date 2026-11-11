from __future__ import annotations

from .models import AlignmentDecision, AlignmentRelation, ConceptProfile, OntologyCandidate, OntologyLayer, SchemaCandidateKind


class ConservativeAligner:
    """Precision-first rules over transparent retrieval signals, replaceable by an LLM adapter."""

    def align(self, profile: ConceptProfile, candidates: list[OntologyCandidate]) -> AlignmentDecision:
        if profile.kind != SchemaCandidateKind.CLASS:
            return PropertyAligner().align(profile, candidates)
        if not candidates:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.NEW_CONCEPT, confidence=0.8, evidence=["No ontology candidates retrieved."], semantic_features_used=sorted(profile.semantic_features), candidate_kind=profile.kind)
        best = candidates[0]
        label = profile.canonical_label.casefold()
        best_label = best.label.casefold()
        cross_domain = best.ontology_layer == OntologyLayer.DOMAIN and best.domain != profile.domain
        runtime_parent = next((candidate for candidate in candidates if candidate.label.casefold() == "runtime environment"), None)
        if "pod" in label and runtime_parent:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.SUBCLASS_OF, target_concept=runtime_parent.iri, confidence=0.91, evidence=["Pod context denotes a deployable runtime unit.", "Runtime Environment is the supported local abstraction."], semantic_features_used=["orchestration", "runtime", "container"])
        if label == best_label:
            if cross_domain:
                return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.UNRESOLVED, confidence=0.35, evidence=["Same label appears in another domain."], semantic_features_used=sorted(profile.semantic_features), warnings=["Cross-domain lexical equality is insufficient for equivalence."], candidate_kind=profile.kind)
            if best.ontology_layer in {OntologyLayer.FOUNDATION, OntologyLayer.SHARED}:
                return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.EQUIVALENT, target_concept=best.iri, confidence=0.96, evidence=["Exact label reuses a reusable foundation/shared concept."], semantic_features_used=sorted(profile.semantic_features))
            if best.ontology_layer == OntologyLayer.DOMAIN and best.domain == profile.domain:
                return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.EQUIVALENT, target_concept=best.iri, confidence=0.99, evidence=["Exact local ontology class already represents the candidate."], semantic_features_used=sorted(profile.semantic_features))
        if best.final_retrieval_score >= 0.72 and not cross_domain:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.SUBCLASS_OF, target_concept=best.iri, confidence=best.final_retrieval_score, evidence=["Local candidate has compatible lexical and structural evidence."], semantic_features_used=sorted(profile.semantic_features))
        if best.lexical_score >= 0.55 and cross_domain:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.RELATED_TO, target_concept=best.iri, confidence=0.45, evidence=["Cross-domain lexical resemblance retained as a non-equivalence relation."], semantic_features_used=sorted(profile.semantic_features), warnings=["No cross-domain equivalence is inferred."])
        return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.NEW_CONCEPT, confidence=0.78, evidence=["No candidate cleared conservative placement thresholds."], semantic_features_used=sorted(profile.semantic_features), candidate_kind=profile.kind)


class PropertyAligner:
    """Property-specific path; property labels never enter the class alignment rules."""

    def align(self, profile: ConceptProfile, candidates: list[OntologyCandidate]) -> AlignmentDecision:
        if not candidates:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.NEW_CONCEPT, confidence=0.8, evidence=["No property candidates retrieved."], candidate_kind=profile.kind)
        best = candidates[0]
        if profile.canonical_label.casefold() == best.label.casefold() and best.domain in {None, profile.domain}:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.EQUIVALENT, target_concept=best.iri, confidence=0.98, evidence=["Exact property label in local/core module."], candidate_kind=profile.kind)
        if best.final_retrieval_score >= 0.72:
            return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.SUBCLASS_OF, target_concept=best.iri, confidence=best.final_retrieval_score, evidence=["Compatible property signature."], candidate_kind=profile.kind)
        return AlignmentDecision(source_concept=profile.canonical_label, relation=AlignmentRelation.NEW_CONCEPT, confidence=0.78, evidence=["No property candidate cleared conservative threshold."], candidate_kind=profile.kind)
