"""Safe structured-output lifecycle diagnostics for company-gateway Qwen calls."""

from __future__ import annotations

import json
from time import perf_counter
from typing import Callable


def compact_prompt(row: dict, top_k: int) -> str:
    """No gold/reference fields are read or included in this prompt."""
    candidates = [{"id": item["iri"], "label": item["label"]} for item in row["retrieved_candidates"][:top_k]]
    return "\n".join((
        'Return only one JSON object: {"candidate_id":"one supplied id or NONE","relation":"EQUIVALENT or NONE"}.',
        "Do not explain. candidate_id must exactly match a supplied id, or be NONE.",
        f"Source: {row['source_label']}",
        "Candidates: " + json.dumps(candidates, ensure_ascii=False),
    ))


def _extract_json(content: str) -> dict | None:
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(content[start:end + 1])
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def classify_response(response, candidate_ids: set[str], configured_max_tokens: int, latency_ms: float) -> dict[str, object]:
    """Classify technical validity separately from semantic abstention."""
    status = getattr(response, "status_code", None)
    if status is None or not 200 <= status < 300:
        return {"final_status": "TRANSPORT_ERROR", "http_status": status, "latency_ms": latency_ms}
    try:
        body = response.json()
    except ValueError:
        return {"final_status": "UNKNOWN_RESPONSE_FAILURE", "http_status": status, "latency_ms": latency_ms}
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content = message.get("content") if isinstance(message.get("content"), str) else ""
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    record = {"http_status": status, "latency_ms": latency_ms, "finish_reason": choice.get("finish_reason"), "configured_max_tokens": configured_max_tokens, "response_token_usage": {key: usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}, "raw_content_char_length": len(content), "empty_response": not bool(content.strip()), "possible_truncation": choice.get("finish_reason") == "length"}
    if not content.strip():
        return {**record, "final_status": "EMPTY_RESPONSE", "json_extraction_success": False, "json_parse_success": False, "schema_validation_success": False, "candidate_membership_validation_success": False}
    parsed = _extract_json(content)
    if parsed is None:
        return {**record, "final_status": "TRUNCATED_RESPONSE" if record["possible_truncation"] else "JSON_PARSE_ERROR", "json_extraction_success": "{" in content and "}" in content, "json_parse_success": False, "schema_validation_success": False, "candidate_membership_validation_success": False}
    candidate, relation = parsed.get("candidate_id"), parsed.get("relation")
    if not isinstance(candidate, str) or relation not in {"EQUIVALENT", "NONE"} or (candidate == "NONE") != (relation == "NONE"):
        return {**record, "final_status": "SCHEMA_VALIDATION_ERROR", "json_extraction_success": True, "json_parse_success": True, "schema_validation_success": False, "candidate_membership_validation_success": False}
    if candidate != "NONE" and candidate not in candidate_ids:
        return {**record, "final_status": "OUT_OF_CANDIDATE", "json_extraction_success": True, "json_parse_success": True, "schema_validation_success": True, "candidate_membership_validation_success": False}
    return {**record, "final_status": "MODEL_ABSTENTION" if candidate == "NONE" else "VALID_SELECTION", "json_extraction_success": True, "json_parse_success": True, "schema_validation_success": True, "candidate_membership_validation_success": True}


def reliability_microbenchmark(rows: list[dict], top_k: int, budgets: list[int], requester: Callable[..., object], model: str, headers: dict[str, str]) -> dict[str, object]:
    records = []
    for row in rows:
        prompt = compact_prompt(row, top_k)
        candidate_ids = {item["iri"] for item in row["retrieved_candidates"][:top_k]}
        for budget in budgets:
            started = perf_counter()
            try:
                response = requester("POST", headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": budget}, timeout=30)
                lifecycle = classify_response(response, candidate_ids, budget, round((perf_counter() - started) * 1000, 3))
            except Exception as error:  # transport diagnostics must finish a bounded sample.
                lifecycle = {"final_status": "TRANSPORT_ERROR", "http_status": None, "latency_ms": round((perf_counter() - started) * 1000, 3), "error_type": type(error).__name__}
            records.append({"source_iri": row["source_iri"], "candidate_set_size": len(candidate_ids), "prompt_char_length": len(prompt), "prompt_variant": "QREL_COMPACT_V1", **lifecycle})
    by_budget = {}
    for budget in budgets:
        group = [record for record in records if record.get("configured_max_tokens") == budget]
        by_budget[str(budget)] = {"n": len(group), "valid_candidate_response_rate": sum(record["final_status"] == "VALID_SELECTION" for record in group) / len(group) if group else None, "technical_invalid_rate": sum(record["final_status"] not in {"VALID_SELECTION", "MODEL_ABSTENTION"} for record in group) / len(group) if group else None, "mean_latency_ms": sum(record["latency_ms"] for record in group) / len(group) if group else None, "failure_taxonomy": {name: sum(record["final_status"] == name for record in group) for name in ("TRANSPORT_ERROR", "EMPTY_RESPONSE", "TRUNCATED_RESPONSE", "JSON_PARSE_ERROR", "SCHEMA_VALIDATION_ERROR", "OUT_OF_CANDIDATE", "MODEL_ABSTENTION", "VALID_SELECTION", "UNKNOWN_RESPONSE_FAILURE")}}
    return {"protocol": "OAEI_QWEN_STRUCTURED_RELIABILITY_V1", "records": records, "by_budget": by_budget}
