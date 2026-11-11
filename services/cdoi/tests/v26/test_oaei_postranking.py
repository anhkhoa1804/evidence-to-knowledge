from cdoi.oaei_postranking import rank1_acceptance, rerank


def _row(gold_rank=1, selected="t:gold", score=0.9):
    return {"source_iri": "s:one", "gold_rank": gold_rank, "gold_target_iri": "t:gold", "selected_candidate_score": score, "selected_candidate_iri": selected, "trivial_lexical": False, "definition_available": False, "parent_context_available": True, "child_context_available": False, "property_context_available": False, "r2_lexical_component": score, "r2_context_component": 0.2, "r2_combined_score": score, "top1_top2_r1_margin": 0.1, "retrieved_candidates": [{"iri": selected, "r2_combined_score": score}, {"iri": "t:gold" if selected != "t:gold" else "t:other", "r2_combined_score": score - 0.1}]}


def test_rank1_groups_and_reranking_are_deterministic_without_gold_scoring():
    emitted, abstained = _row(score=0.9), _row(score=0.7)
    profile = rank1_acceptance([emitted, abstained], 0.82)
    assert profile["groups"]["A1_rank1_correctly_emitted"]["n"] == 1
    assert profile["groups"]["A2_rank1_abstained"]["n"] == 1
    moved = _row(gold_rank=2, selected="t:wrong", score=0.7)
    moved["retrieved_candidates"] = [{"iri": "t:wrong", "r2_combined_score": 0.6}, {"iri": "t:gold", "r2_combined_score": 0.8}]
    result = rerank([moved], 0.82, 2)
    assert result["rank_gt1_promoted_to_1"] == 1
    assert result["reranked_top1_accuracy"] == 1.0
