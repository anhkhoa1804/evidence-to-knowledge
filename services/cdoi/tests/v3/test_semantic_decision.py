import json

import pytest

from cdoi.semantic_decision import (
    AmbiguityEvidence,
    CandidateSet,
    candidate_set_from_v26_row,
    ConservativeDecisionPolicy,
    EvidenceAssembler,
    QwenCompactSelector,
    R1DeterministicSelector,
    R2DeterministicSelector,
    SelectionResult,
    SelectionStatus,
    SemanticEvidence,
    SourceProfileReference,
    UncalibratedCommitmentConfidence,
    qsem_v1_prompt,
)
from cdoi.v3_evaluation import CalibrationProtocol, risk_coverage, selector_comparison
from cdoi.kg import KnowledgeGraphPopulator
from cdoi.models import AlignmentDecision, AlignmentRelation, EntityCandidate


def candidate_set():
    return CandidateSet.from_rows("s", SourceProfileReference("s", "oaei_profile_v1"), [
        {"rank": 1, "iri": "t:one", "score": .82, "label": "One", "r2_combined_score": .60},
        {"rank": 2, "iri": "t:two", "score": .75, "label": "Two", "r2_combined_score": .81},
    ], retriever_id="R1_FUZZY_LEXICAL", retriever_version="v2_6_6", index_version="anatomy-2026", index_hash="index")


def profile():
    return SemanticEvidence("s", "Source", aliases=("Origin",), parents=("Parent",), profile_version="oaei_profile_v1")


def candidates():
    return {"t:one": SemanticEvidence("t:one", "One"), "t:two": SemanticEvidence("t:two", "Two", parents=("Parent",))}


def test_candidate_set_is_immutable_ranked_and_hashable_without_reference_fields():
    first, second = candidate_set(), candidate_set()
    assert first.artifact_hash == second.artifact_hash
    assert [item.candidate_id for item in first.candidates] == ["t:one", "t:two"]
    assert first.presentation_handles(True) == {"t:one": "C01", "t:two": "C02"}
    with pytest.raises(TypeError):
        first.candidates[0].observable_evidence["new"] = "mutation"
    with pytest.raises(ValueError, match="reference-only"):
        CandidateSet.from_rows("s", SourceProfileReference("s"), [{"iri": "t", "score": .1, "gold_rank": 1}], retriever_id="R1", retriever_version="v")
    with pytest.raises(ValueError, match="reference-only"):
        EvidenceAssembler().from_mapping({"source_id": "s", "label": "Source", "gold_target_iri": "t"})


def test_v26_adapter_copies_only_observable_candidate_fields():
    migrated = candidate_set_from_v26_row({"source_iri": "s", "gold_target_iri": "forbidden", "gold_rank": 2, "retrieved_candidates": [{"rank": 1, "iri": "t", "score": .8, "label": "Target"}]}, method="R1_FUZZY_LEXICAL")
    assert migrated.candidates[0].candidate_id == "t"
    assert "gold" not in migrated.candidates[0].observable_evidence


def test_ambiguity_is_observable_evidence_not_a_policy_rule():
    evidence = AmbiguityEvidence.from_candidate_set(candidate_set(), profile(), "t:two")
    assert evidence.top1_top2_margin == .07
    assert evidence.topk_score_spread == .07
    assert evidence.r1_r2_disagreement is True
    assert evidence.structural_evidence_available is True


def test_selection_result_states_reject_invalid_combinations():
    with pytest.raises(ValueError):
        SelectionResult(SelectionStatus.SELECTED, None, None, "x", "v", "hash")
    with pytest.raises(ValueError):
        SelectionResult(SelectionStatus.SEMANTIC_ABSTAIN, "t", "EQUIVALENT", "x", "v", "hash")
    with pytest.raises(ValueError):
        SelectionResult(SelectionStatus.TECHNICAL_UNAVAILABLE, "t", "EQUIVALENT", "x", "v", "hash")


def test_r1_r2_wrappers_preserve_v26_selection_semantics():
    source, values, ambiguity = profile(), candidate_set(), AmbiguityEvidence.from_candidate_set(candidate_set(), profile())
    assert R1DeterministicSelector().select(source, values, ambiguity).candidate_id == "t:one"
    assert R2DeterministicSelector().select(source, values, ambiguity).candidate_id == "t:two"


def test_frozen_qsem_prompt_preserves_order_handles_and_excludes_reference():
    prompt, handles = qsem_v1_prompt(profile(), candidate_set(), candidates(), opaque_handles=True)
    payload = json.loads(prompt.split("\n")[-1])
    assert "gold" not in prompt.casefold() and "reference" not in prompt.casefold()
    assert [item["id"] for item in payload["candidates"]] == ["C01", "C02"]
    assert handles["t:two"] == "C02"
    assert payload["source"]["parents"] == ["Parent"]


class Response:
    status_code = 200
    def __init__(self, content): self.content = content
    def json(self): return {"choices": [{"message": {"content": self.content}, "finish_reason": "stop"}]}


def test_qwen_adapter_distinguishes_selection_abstention_and_technical_unavailable():
    source, values, ambiguity = profile(), candidate_set(), AmbiguityEvidence.from_candidate_set(candidate_set(), profile())
    selected = QwenCompactSelector(lambda *args, **kwargs: Response('{"candidate_id":"t:two","relation":"EQUIVALENT"}'), "model").select(source, values, ambiguity, candidates())
    abstained = QwenCompactSelector(lambda *args, **kwargs: Response('{"candidate_id":"NONE","relation":"NONE"}'), "model").select(source, values, ambiguity, candidates())
    unavailable = QwenCompactSelector(lambda *args, **kwargs: Response(""), "model", max_attempts=1).select(source, values, ambiguity, candidates())
    assert (selected.status, selected.candidate_id) == (SelectionStatus.SELECTED, "t:two")
    assert abstained.status == SelectionStatus.SEMANTIC_ABSTAIN
    assert unavailable.status == SelectionStatus.TECHNICAL_UNAVAILABLE


def test_policy_is_review_only_and_technical_failure_never_auto_accepts():
    source, values, ambiguity = profile(), candidate_set(), AmbiguityEvidence.from_candidate_set(candidate_set(), profile())
    result = R1DeterministicSelector().select(source, values, ambiguity)
    commitment = UncalibratedCommitmentConfidence().assess(values, ambiguity, result, source)
    assert ConservativeDecisionPolicy().decide(result, commitment).action.value == "PROPOSE_FOR_REVIEW"
    failed = SelectionResult(SelectionStatus.TECHNICAL_UNAVAILABLE, None, None, "q", "v", values.artifact_hash)
    assert ConservativeDecisionPolicy().decide(failed, commitment).action.value == "UNRESOLVED"


def test_selector_output_has_no_path_to_canonical_kg_without_existing_approval():
    kg = KnowledgeGraphPopulator()
    kg.populate(EntityCandidate(id="pending", surface="Source"), AlignmentDecision(source_concept="Source", relation=AlignmentRelation.EQUIVALENT, target_concept="urn:target", confidence=.9), "urn:domain/", approved=False)
    assert len(kg.graph) == 0
    assert len(kg.staging_graph) == 1


def test_calibration_and_comparison_are_evaluation_only_scaffolds():
    protocol = CalibrationProtocol("Anatomy", "exploratory", "margin", "none", "v1", "accepted_error_rate", "EXPLORATORY_NON_INDEPENDENT")
    assert protocol.independence_status == "EXPLORATORY_NON_INDEPENDENT"
    curve = risk_coverage([{"score": .9, "reference_correct": True}, {"score": .5, "reference_correct": False}], [.8])
    assert curve[0]["coverage"] == .5 and curve[0]["risk"] == 0
    comparison = selector_comparison([{"source_id": "s", "selector_id": "r1", "status": "SELECTED", "candidate_id": "t", "reference_correct": True}, {"source_id": "s", "selector_id": "r2", "status": "SELECTED", "candidate_id": "t", "reference_correct": True}])
    assert comparison["agreement"]["ALL_AGREE"] == 1
