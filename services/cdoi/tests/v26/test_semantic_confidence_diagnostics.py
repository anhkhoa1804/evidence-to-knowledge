from cdoi.qwen_semantic_eval import repeated_call_diagnostic, stratified_sample
from cdoi.semantic_confidence_diagnostics import agreement_category, confidence_evidence_table, margin_bucket, validation_analysis
from cdoi.oaei_full_corpus import ConceptProfile


class Response:
    status_code = 200
    def __init__(self, text): self.text = text
    def json(self): return {"choices": [{"finish_reason": "stop", "message": {"content": self.text}}], "usage": {}}


def _profile(iri, label): return ConceptProfile(iri, label, (), None, (), (), (), ())


def _row(source, rank=1, score=.9, second=.5):
    return {"source_iri": source, "source_label": source, "gold_target_iri": "g", "gold_rank": rank, "nontrivial": rank != 1, "trivial_lexical": rank == 1, "selected_candidate_iri": "w", "selected_candidate_score": score, "retrieved_candidates": [{"iri": "w", "label": "Wrong", "rank": 1, "score": score, "r2_combined_score": .4, "r2_lexical_score": score, "r2_context_score": 0}, {"iri": "g", "label": "Gold", "rank": 2, "score": second, "r2_combined_score": .8, "r2_lexical_score": second, "r2_context_score": 0}]}


def test_v265_sampling_is_seeded_priority_ordered_and_duplicate_free():
    rows = [_row("s1", 1, .7, .69), _row("s2", 2), _row("s3", 7), _row("s4", 1, .9, .89)]
    pairs = [{"source_id": row["source_iri"], "pairwise_gold_rank": 1, "pairwise_target": "w"} for row in rows]
    first = stratified_sample(rows, pairs, .82, 4, 265, 2, "V265")
    second = stratified_sample(rows, pairs, .82, 4, 265, 2, "V265")
    assert [item["source_iri"] for item in first] == [item["source_iri"] for item in second]
    assert len({item["source_iri"] for item in first}) == 4
    assert first[0]["sample_stratum"] == "rank1_threshold_abstention"


def test_agreement_margin_and_reference_separated_evidence_table():
    assert margin_bucket(.05) == "0_05_0_10"
    assert agreement_category("a", "a", "a", True) == "ALL_AGREE"
    assert agreement_category("a", "b", "NONE", True) == "QWEN_ABSTAINS"
    assert agreement_category("a", "b", None, False) == "QWEN_TECHNICAL_INVALID"
    record = {"source_id": "s", "candidate_valid": True, "qwen_candidate_id": "g", "qwen_relation": "EQUIVALENT", "r1_target": "w", "r2_target": "g", "r1_top1_score": .9, "r1_margin": .2, "gold_target_id": "g", "gold_rank": 2, "nontrivial": True, "sample_stratum": "gold_rank_2_5", "retry_count": 0}
    analysis = validation_analysis([record], .82)
    assert analysis["incremental_value"]["r1"]["baseline_wrong_qwen_correct"] == 1
    table = confidence_evidence_table([_row("s", 2)], {"s": _profile("s", "Source")}, {"g": _profile("g", "Gold"), "w": _profile("w", "Wrong")}, [record])
    assert "gold_candidate" not in table[0]["observable_at_inference"]
    assert table[0]["reference_only"]["gold_candidate"] == "g"


def test_repeated_calls_measure_modal_stability_without_persisting_prompt_content():
    answers = iter([Response('{"candidate_id":"g","relation":"EQUIVALENT"}'), Response('{"candidate_id":"w","relation":"EQUIVALENT"}'), Response('{"candidate_id":"g","relation":"EQUIVALENT"}')])
    row = _row("s", 2)
    result = repeated_call_diagnostic([row], {"s": _profile("s", "Source")}, {"g": _profile("g", "Gold"), "w": _profile("w", "Wrong")}, 2, 3, 1, lambda *args, **kwargs: next(answers), "model", {}, 512)
    assert result["per_case"][0]["same_candidate_selection_rate"] == 2 / 3
    assert result["per_case"][0]["modal_selection_correct"]
    assert all("prompt" not in item for item in result["records"])
