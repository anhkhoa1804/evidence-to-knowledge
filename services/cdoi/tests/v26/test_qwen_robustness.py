from cdoi.oaei_full_corpus import ConceptProfile
from cdoi.qwen_robustness import evaluate_conditions, opaque_mapping, permutation_indices, robustness_prompt, robustness_summary


class Response:
    status_code = 200
    def __init__(self, content, status=200): self.status_code, self.content = status, content
    def json(self): return {"choices": [{"finish_reason": "stop", "message": {"content": self.content}}], "usage": {}}


def _profile(iri, label): return ConceptProfile(iri, label, (), None, (), (), (), ())


def _row():
    return {"source_iri": "iri:source", "gold_target_iri": "iri:gold", "gold_rank": 2, "nontrivial": True, "robustness_stratum": "difficult", "retrieved_candidates": [{"iri": "iri:wrong", "score": .8}, {"iri": "iri:gold", "score": .7}]}


def test_permutations_and_opaque_handles_preserve_candidate_set_without_gold_logic():
    assert opaque_mapping(["a", "b"]) == {"a": "C01", "b": "C02"}
    assert permutation_indices(4, "SEEDED_A", 266, "s") == permutation_indices(4, "SEEDED_A", 266, "s")
    source, target, row = {"iri:source": _profile("iri:source", "Source")}, {"iri:gold": _profile("iri:gold", "Gold"), "iri:wrong": _profile("iri:wrong", "Wrong")}, _row()
    prompt, metadata = robustness_prompt(row, source, target, 2, id_mode="OPAQUE_ID")
    assert "iri:gold" not in prompt and "iri:wrong" not in prompt and "iri:source" in prompt
    assert set(metadata["opaque_to_original"].values()) == {"iri:gold", "iri:wrong"}


def test_condition_metrics_map_opaque_answer_back_and_fail_closed():
    source, target, row = {"iri:source": _profile("iri:source", "Source")}, {"iri:gold": _profile("iri:gold", "Gold"), "iri:wrong": _profile("iri:wrong", "Wrong")}, _row()
    condition = {"condition_id": "OPAQUE", "family": "opaque", "order_kind": "ORIGINAL", "order_seed": 266, "id_mode": "OPAQUE_ID", "profile_mode": "Q0_LABEL", "prompt_variant": "P0_FROZEN"}
    result = evaluate_conditions([row], source, target, [condition], 2, 1, lambda *args, **kwargs: Response('{"candidate_id":"C02","relation":"EQUIVALENT"}'), "model", {}, 512)
    record = result["records"][0]
    assert record["selected_candidate_id"] == "iri:gold"
    assert record["candidate_valid"]
    summary = robustness_summary(result["records"])
    assert summary["selection_invariance_rate"] == 1.0
    failed = evaluate_conditions([row], source, target, [condition], 2, 1, lambda *args, **kwargs: Response("", 502), "model", {}, 512)["records"][0]
    assert not failed["candidate_valid"] and failed["selected_candidate_id"] is None
