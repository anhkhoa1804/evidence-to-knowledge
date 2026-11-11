import pytest

from cdoi.relation_aware_selection import (RelationAwareSemanticSelector, SemanticRelation,
                                            SemanticRelationProposal)
from cdoi.semantic_decision import CandidateSet, SemanticEvidence, SourceProfileReference


def _set(target_id: str = "t") -> CandidateSet:
    return CandidateSet.from_rows("s", SourceProfileReference("s"), [{"candidate_id": target_id, "retrieval_score": .9}], retriever_id="frozen", retriever_version="v1")


def _propose(source: SemanticEvidence, target: SemanticEvidence, *, hierarchy: bool = True):
    return RelationAwareSemanticSelector({target.source_id: target}, use_hierarchy=hierarchy).propose(source, _set(target.source_id))


def test_relation_enum_and_strict_exact_behavior():
    proposal = _propose(SemanticEvidence("s", "Public debt"), SemanticEvidence("t", "public debt"))
    assert proposal.proposed_relation == SemanticRelation.EXACT_MATCH
    assert proposal.selected_target_id == "t"
    assert proposal.artifact()["evidence"]["normalized_label_equal"] is True


def test_broad_and_narrow_direction_is_preserved():
    narrow = _propose(SemanticEvidence("s", "government budget policy"), SemanticEvidence("t", "budget policy"))
    broad = _propose(SemanticEvidence("s", "budget policy"), SemanticEvidence("t", "government budget policy"))
    assert narrow.proposed_relation == SemanticRelation.NARROW_MATCH
    assert broad.proposed_relation == SemanticRelation.BROAD_MATCH


def test_related_requires_affirmative_overlap_and_is_not_a_fallback():
    related = _propose(SemanticEvidence("s", "international trade policy"), SemanticEvidence("t", "trade policy reform"))
    unresolved = _propose(SemanticEvidence("s", "taxation"), SemanticEvidence("t", "migration"))
    assert related.proposed_relation == SemanticRelation.RELATED_MATCH
    assert unresolved.proposed_relation == SemanticRelation.UNRESOLVED


def test_hierarchy_ablation_and_candidate_immutability():
    source = SemanticEvidence("s", "micro policy", parents=("economic policy",))
    target = SemanticEvidence("t", "economic policy")
    assert _propose(source, target).proposed_relation == SemanticRelation.NARROW_MATCH
    assert _propose(source, target, hierarchy=False).proposed_relation == SemanticRelation.UNRESOLVED
    candidate_set = _set(); before = candidate_set.artifact_hash
    _propose(SemanticEvidence("s", "a"), SemanticEvidence("t", "b"))
    assert candidate_set.artifact_hash == before


def test_mapping_gt_is_not_an_api_input_and_proposals_remain_proposal_only():
    assert "mapping" not in RelationAwareSemanticSelector.propose.__annotations__
    with pytest.raises(ValueError):
        SemanticRelationProposal("s", "t", SemanticRelation.EXACT_MATCH, "hash", "selector", "v1", "reason", {"gold_target": "t"})


def test_oracle_candidate_must_already_be_in_the_frozen_set():
    selector = RelationAwareSemanticSelector({"t": SemanticEvidence("t", "target")})
    with pytest.raises(ValueError):
        selector.propose_for_candidate(SemanticEvidence("s", "source"), _set("t"), "outside")
