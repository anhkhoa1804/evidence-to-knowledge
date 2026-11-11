from cdoi.oaei_full_corpus import ConceptProfile
from cdoi.qwen_semantic_eval import compact_semantic_prompt, semantic_evaluation


class Response:
    status_code = 200
    def __init__(self, content, finish_reason="stop"):
        self.body = {"choices": [{"finish_reason": finish_reason, "message": {"content": content}}], "usage": {"completion_tokens": 4}}
    def json(self): return self.body


def _profile(iri, label): return ConceptProfile(iri, label, (), None, (), (), (), ())


def _row():
    return {"source_iri": "s", "source_label": "Source", "gold_target_iri": "g", "gold_rank": 2, "nontrivial": True, "selected_candidate_score": .7,
            "selected_candidate_iri": "w", "retrieved_candidates": [{"iri": "w", "rank": 1, "label": "Wrong", "score": .7, "r2_combined_score": .5}, {"iri": "g", "rank": 2, "label": "Gold", "score": .6, "r2_combined_score": .8}]}


def test_compact_semantic_prompt_and_bounded_retry_keep_gold_out_of_prompt():
    source, target, row = {"s": _profile("s", "Source")}, {"g": _profile("g", "Gold"), "w": _profile("w", "Wrong")}, _row()
    prompt = compact_semantic_prompt(row, source, target, 2)
    assert "gold_target" not in prompt and "gold_rank" not in prompt
    answers = iter([Response('{"candidate_id":"outside","relation":"EQUIVALENT"}'), Response('{"candidate_id":"g","relation":"EQUIVALENT"}')])
    result = semantic_evaluation([row], source, target, [{"source_id": "s", "pairwise_gold_rank": 2, "pairwise_target": "w"}], .82, 2, 1, 264, 2, lambda *args, **kwargs: next(answers), "model", {"Host": "gateway"}, 512)
    record = result["records"][0]
    assert record["final_status"] == "VALID_SELECTION"
    assert record["retry_count"] == 1
    assert result["metrics"]["target_selection_accuracy"] == 1.0
    assert result["metrics"]["r2_same_sample_accuracy"] == 1.0


def test_valid_none_is_semantic_abstention_not_technical_invalid():
    source, target, row = {"s": _profile("s", "Source")}, {"g": _profile("g", "Gold"), "w": _profile("w", "Wrong")}, _row()
    result = semantic_evaluation([row], source, target, [{"source_id": "s", "pairwise_gold_rank": 2, "pairwise_target": "w"}], .82, 2, 1, 264, 1, lambda *args, **kwargs: Response('{"candidate_id":"NONE","relation":"NONE"}'), "model", {}, 512)
    assert result["records"][0]["final_status"] == "MODEL_ABSTENTION"
    assert result["metrics"]["technical_valid_rate"] == 1.0
