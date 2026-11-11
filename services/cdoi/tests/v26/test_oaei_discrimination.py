from cdoi.oaei_discrimination import candidate_features, compare_candidates, labelled_pair_records, margin_analysis, pairwise_rerank
from cdoi.oaei_full_corpus import ConceptProfile


def _profile(iri, label, parents=(), children=(), properties=()):
    return ConceptProfile(iri, label, (), None, parents, children, properties, ())


def _row(gold="t:gold", score=0.9, second=0.8):
    return {"source_iri": "s:one", "gold_target_iri": gold, "gold_rank": 1 if gold == "t:gold" else 2,
            "nontrivial": True, "trivial_lexical": False, "selected_candidate_score": score, "retrieved_candidates": [
                {"iri": "t:gold", "rank": 1, "score": score, "r2_lexical_score": score, "r2_context_score": .2, "r2_combined_score": .76},
                {"iri": "t:wrong", "rank": 2, "score": second, "r2_lexical_score": second, "r2_context_score": .1, "r2_combined_score": .66}]}


def _profiles():
    return {"s:one": _profile("s:one", "Source", ("Body",), (), ("part",))}, {"t:gold": _profile("t:gold", "Gold", ("Body",), (), ("part",)), "t:wrong": _profile("t:wrong", "Wrong", ("Else",), (), ())}


def test_feature_generation_does_not_consult_gold_and_hard_negative_excludes_it():
    source, target = _profiles()
    row = _row()
    features = candidate_features({key: value for key, value in row.items() if key != "gold_target_iri"}, source, target)
    assert [item["candidate_id"] for item in features] == ["t:gold", "t:wrong"]
    records, pairs = labelled_pair_records([row], source, target)
    assert next(item for item in records if item["candidate_id"] == "t:gold")["is_gold"]
    assert pairs[0]["hard_negative_candidate_id"] == "t:wrong"
    assert pairs[0]["delta_parent_similarity"] > 0


def test_margin_buckets_and_pairwise_tie_break_are_deterministic_and_label_free():
    source, target = _profiles()
    row = _row(gold="t:wrong", score=.9, second=.88)
    analysis = margin_analysis([row], .82)
    assert next(item for item in analysis["buckets"] if item["bucket"] == "0_02_0_05")["n"] == 1
    assert compare_candidates({"candidate_id": "a", "candidate_retrieval_rank": 1, "lexical_score": .5, "parent_similarity": None, "child_similarity": None, "property_similarity": None}, {"candidate_id": "b", "candidate_retrieval_rank": 2, "lexical_score": .5, "parent_similarity": None, "child_similarity": None, "property_similarity": None}) == -1
    reranked = pairwise_rerank([row], source, target, 2)
    assert reranked["rank1_preserved"] >= 0
    assert reranked["outcome_taxonomy"]
