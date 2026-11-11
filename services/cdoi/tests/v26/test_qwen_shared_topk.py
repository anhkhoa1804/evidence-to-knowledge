import json

from cdoi.qwen_shared_topk import evaluate_shared_topk, prompt_for, stratified_cases


def _row(source="s:one", target="t:gold", score=0.8):
    return {"source_iri": source, "source_label": "Source", "gold_target_iri": target, "gold_rank": 1, "gold_in_top_k": True, "selected_candidate_iri": target, "selected_candidate_score": score, "nontrivial": True, "trivial_lexical": False, "retrieved_candidates": [{"iri": target, "label": "Target", "definition": None}, {"iri": "t:other", "label": "Other", "definition": None}]}


def test_shared_topk_prompt_excludes_gold_and_rejects_out_of_candidate_selection():
    row = _row()
    case = stratified_cases([row], 0.82, 1)[0]
    prompt = prompt_for(case, row)
    assert "gold_target" not in prompt and "t:gold" in prompt  # Candidate membership is allowed.
    result = evaluate_shared_topk([row], 0.82, 1, lambda _: json.dumps({"status": "MATCHED", "semantic_relation": "EQUIVALENT", "target_id": "t:not-offered"}))
    assert result["metrics"]["out_of_candidate_selection_rate"] == 1.0
    assert result["cases"][0]["retry_count"] == 2


def test_shared_topk_uses_same_candidates_for_deterministic_and_qwen():
    row = _row(score=0.9)
    response = json.dumps({"status": "MATCHED", "semantic_relation": "EQUIVALENT", "target_id": "t:gold", "evidence": [], "self_reported_confidence": 0.9})
    result = evaluate_shared_topk([row], 0.82, 1, lambda _: response)
    assert result["metrics"]["valid_response_rate"] == 1.0
    assert result["cases"][0]["candidate_ids"] == ["t:gold", "t:other"]
    assert result["cases"][0]["qwen_target"] == result["cases"][0]["deterministic_target"]
