from cdoi.qwen_reliability import classify_response, compact_prompt, reliability_microbenchmark


class Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


def _body(content, finish_reason="stop"):
    return {"choices": [{"finish_reason": finish_reason, "message": {"content": content}}], "usage": {"completion_tokens": 4}}


def _row():
    return {"source_iri": "s:one", "source_label": "Source", "gold_target_iri": "t:gold", "retrieved_candidates": [{"iri": "t:gold", "label": "Gold"}, {"iri": "t:other", "label": "Other"}]}


def test_compact_prompt_excludes_gold_field_and_classifies_response_lifecycle():
    prompt = compact_prompt(_row(), 2)
    assert "gold_target" not in prompt
    valid = classify_response(Response(_body('{"candidate_id":"t:gold","relation":"EQUIVALENT"}')), {"t:gold"}, 512, 1.0)
    truncated = classify_response(Response(_body('{"candidate_id":"t:gold"', "length")), {"t:gold"}, 512, 1.0)
    outside = classify_response(Response(_body('{"candidate_id":"t:bad","relation":"EQUIVALENT"}')), {"t:gold"}, 512, 1.0)
    assert valid["final_status"] == "VALID_SELECTION"
    assert truncated["final_status"] == "TRUNCATED_RESPONSE"
    assert outside["final_status"] == "OUT_OF_CANDIDATE"


def test_microbenchmark_keeps_technical_invalid_distinct_from_model_abstention():
    calls = []
    def requester(method, *, headers, json, timeout):
        calls.append(json)
        return Response(_body('{"candidate_id":"NONE","relation":"NONE"}'))
    result = reliability_microbenchmark([_row()], 2, [512], requester, "model", {"Host": "gateway"})
    assert result["records"][0]["final_status"] == "MODEL_ABSTENTION"
    assert result["by_budget"]["512"]["technical_invalid_rate"] == 0.0
    assert "gold_target" not in calls[0]["messages"][0]["content"]
