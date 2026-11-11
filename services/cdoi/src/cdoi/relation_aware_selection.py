"""Research-only deterministic relation proposals over an immutable CandidateSet.

The selector deliberately has no mapping-reader dependency.  Cross-ontology
mapping rows belong only to the evaluator, after predictions are frozen.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .oaei_full_corpus import normalize
from .semantic_decision import CandidateSet, SemanticEvidence


class SemanticRelation(str, Enum):
    EXACT_MATCH = "exactMatch"
    BROAD_MATCH = "broadMatch"
    NARROW_MATCH = "narrowMatch"
    RELATED_MATCH = "relatedMatch"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class SemanticRelationProposal:
    """An experiment-only proposal; it has no commitment, routing, or KG effect."""
    source_id: str
    selected_target_id: str | None
    proposed_relation: SemanticRelation
    candidate_set_hash: str
    selector_id: str
    selector_version: str
    decision_reason: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id or not self.candidate_set_hash:
            raise ValueError("source identity and candidate-set hash are required")
        if self.proposed_relation != SemanticRelation.UNRESOLVED and not self.selected_target_id:
            raise ValueError("resolved relation proposal requires a selected target")
        forbidden = {"gold", "reference", "mapping", "ground_truth", "correct"}
        if any(any(word in str(key).casefold() for word in forbidden) for key in self.evidence):
            raise ValueError("proposal evidence cannot contain evaluation fields")
        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))

    def artifact(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "selected_target_id": self.selected_target_id,
                "proposed_relation": self.proposed_relation.value, "candidate_set_hash": self.candidate_set_hash,
                "selector_id": self.selector_id, "selector_version": self.selector_version,
                "decision_reason": self.decision_reason, "evidence": dict(self.evidence)}


def _tokens(value: str) -> frozenset[str]:
    return frozenset(normalize(value).split())


def _equal(left: str, right: str) -> bool:
    return bool(normalize(left)) and normalize(left) == normalize(right)


def _contains(more_specific: frozenset[str], more_general: frozenset[str]) -> bool:
    return bool(more_general) and more_general < more_specific


class RelationAwareSemanticSelector:
    """Frozen conservative rules with optional ontology-local hierarchy evidence.

    Relation direction is always expressed from the source concept to the
    selected target: ``narrowMatch`` means the source is narrower; ``broadMatch``
    means the source is broader.  ``relatedMatch`` is affirmative-only and is
    never the fallback branch.
    """
    selector_id = "STW_THESOZ_RELATION_AWARE_DETERMINISTIC"
    selector_version = "v1_preregistered"

    def __init__(self, candidate_evidence: Mapping[str, SemanticEvidence], *, use_hierarchy: bool = True):
        self._candidate_evidence = MappingProxyType(dict(candidate_evidence))
        self.use_hierarchy = use_hierarchy

    def propose(self, source: SemanticEvidence, candidate_set: CandidateSet) -> SemanticRelationProposal:
        """Propose from source, target-local profiles, and frozen candidates only."""
        return self.propose_for_candidate(source, candidate_set, candidate_set.candidates[0].candidate_id)

    def propose_for_candidate(self, source: SemanticEvidence, candidate_set: CandidateSet, candidate_id: str) -> SemanticRelationProposal:
        """Classify one member of a frozen set; the caller supplies no GT to this API."""
        candidate = next((item for item in candidate_set.candidates if item.candidate_id == candidate_id), None)
        if candidate is None:
            raise ValueError("relation classification requires a frozen CandidateSet member")
        target = self._candidate_evidence[candidate.candidate_id]
        source_tokens, target_tokens = _tokens(source.label), _tokens(target.label)
        evidence: dict[str, Any] = {
            "target_rank": candidate.rank,
            "retrieval_score": candidate.retrieval_score,
            "normalized_label_equal": _equal(source.label, target.label),
            "source_label_tokens": len(source_tokens),
            "target_label_tokens": len(target_tokens),
            "shared_label_tokens": len(source_tokens & target_tokens),
            "hierarchy_enabled": self.use_hierarchy,
        }
        relation, reason = SemanticRelation.UNRESOLVED, "insufficient_affirmative_relation_evidence"
        if evidence["normalized_label_equal"]:
            relation, reason = SemanticRelation.EXACT_MATCH, "normalized_preferred_label_equality"
        elif _contains(source_tokens, target_tokens):
            relation, reason = SemanticRelation.NARROW_MATCH, "source_label_strictly_contains_target_label"
        elif _contains(target_tokens, source_tokens):
            relation, reason = SemanticRelation.BROAD_MATCH, "target_label_strictly_contains_source_label"
        elif self.use_hierarchy:
            relation, reason = self._hierarchy_relation(source, target)
        if relation == SemanticRelation.UNRESOLVED and self._affirmative_related(source_tokens, target_tokens):
            relation, reason = SemanticRelation.RELATED_MATCH, "non_containment_multi_token_lexical_overlap"
        evidence["source_parent_count"] = len(source.parents)
        evidence["source_child_count"] = len(source.children)
        evidence["target_parent_count"] = len(target.parents)
        evidence["target_child_count"] = len(target.children)
        return SemanticRelationProposal(source.source_id, candidate.candidate_id, relation, candidate_set.artifact_hash,
                                        self.selector_id, self.selector_version + ("_R1" if self.use_hierarchy else "_R0"), reason, evidence)

    @staticmethod
    def _affirmative_related(source: frozenset[str], target: frozenset[str]) -> bool:
        # Two shared tokens avoids using a single generic word as a catch-all.
        return len(source & target) >= 2 and not _contains(source, target) and not _contains(target, source)

    @staticmethod
    def _hierarchy_relation(source: SemanticEvidence, target: SemanticEvidence) -> tuple[SemanticRelation, str]:
        target_is_source_parent = any(_equal(parent, target.label) for parent in source.parents)
        target_parent_is_source = any(_equal(source.label, parent) for parent in target.parents)
        if target_is_source_parent or target_parent_is_source:
            return SemanticRelation.NARROW_MATCH, "ontology_local_parent_label_equality"
        target_is_source_child = any(_equal(child, target.label) for child in source.children)
        target_child_is_source = any(_equal(source.label, child) for child in target.children)
        if target_is_source_child or target_child_is_source:
            return SemanticRelation.BROAD_MATCH, "ontology_local_child_label_equality"
        return SemanticRelation.UNRESOLVED, "no_ontology_local_directional_evidence"
