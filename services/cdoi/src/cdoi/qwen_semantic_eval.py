"""Bounded compact shared-Top-K semantic evaluation for Qwen.

The prompt builder receives no reference fields.  Reference labels are joined
only after a candidate-valid model response has been recorded.
"""

from __future__ import annotations

import hashlib
import json
import random
from time import perf_counter
from typing import Callable

from .oaei_full_corpus import ConceptProfile
from .qwen_reliability import classify_response


def _profile(profile: ConceptProfile) -> dict:
    """A compact semantic profile, deliberately excluding evaluation labels."""
    return {"id": profile.iri, "label": profile.label, "aliases": list(profile.aliases),
            "parents": list(profile.parents), "children": list(profile.children),
            "properties": list(profile.object_properties + profile.data_properties)}


def compact_semantic_prompt(row: dict, source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], top_k: int) -> str:
    """Construct a candidate-bounded prompt without gold/rank/correctness data."""
    candidate_ids = [item["iri"] for item in row["retrieved_candidates"][:top_k]]
    payload = {"source": _profile(source[row["source_iri"]]), "candidates": [_profile(target[item]) for item in candidate_ids]}
    return "\n".join((
        'Return only JSON: {"candidate_id":"a supplied id or NONE","relation":"EQUIVALENT or NONE"}.',
        "Choose only a supplied candidate when evidence supports Anatomy equivalence; otherwise choose NONE. Do not explain.",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    ))


def _margin(row: dict) -> float:
    scores = row["retrieved_candidates"]
    return float(scores[0]["score"]) - float(scores[1]["score"]) if len(scores) > 1 else 0.0


def _stratum(row: dict, pairwise: dict, threshold: float) -> str:
    margin = _margin(row)
    if row["gold_rank"] == 1 and row["selected_candidate_score"] < threshold:
        return "rank1_threshold_abstention"
    if 2 <= row["gold_rank"] <= 5:
        return "gold_rank_2_5"
    if 6 <= row["gold_rank"] <= 10:
        return "gold_rank_6_10"
    if row["gold_rank"] <= 10 and pairwise["pairwise_gold_rank"] != 1:
        return "pairwise_failure"
    if row["nontrivial"]:
        return "nontrivial_other"
    if margin < .10:
        return "low_margin_other"
    return "easy_control"


V265_PRIORITY = ("rank1_threshold_abstention", "gold_rank_2_5", "gold_rank_6_10", "r2_failure", "margin_lt_0_05", "margin_0_05_0_10", "nontrivial_remaining", "easy_control")


def _v265_stratum(row: dict, threshold: float, top_k: int) -> str:
    """Pre-inference priority assignment; reference-aware categories are explicit."""
    margin = _margin(row)
    r2_target = min(row["retrieved_candidates"][:top_k], key=lambda item: (-item["r2_combined_score"], item["iri"]))["iri"]
    if row["gold_rank"] == 1 and row["selected_candidate_score"] < threshold:
        return "rank1_threshold_abstention"
    if 2 <= row["gold_rank"] <= 5:
        return "gold_rank_2_5"
    if 6 <= row["gold_rank"] <= 10:
        return "gold_rank_6_10"
    if r2_target != row["gold_target_iri"]:
        return "r2_failure"
    if margin < .05:
        return "margin_lt_0_05"
    if margin < .10:
        return "margin_0_05_0_10"
    if row["nontrivial"]:
        return "nontrivial_remaining"
    return "easy_control"


def stratified_sample(rows: list[dict], pairwise_results: list[dict], threshold: float, sample_size: int, seed: int, top_k: int = 10, strategy: str = "V264") -> list[dict]:
    """Deterministic, duplicate-free round-robin selection fixed before inference."""
    by_source = {item["source_id"]: item for item in pairwise_results}
    groups: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda item: item["source_iri"]):
        name = _v265_stratum(row, threshold, top_k) if strategy == "V265" else _stratum(row, by_source[row["source_iri"]], threshold)
        groups.setdefault(name, []).append(row)
    if strategy == "V265":
        rng = random.Random(seed)
        for name in groups:
            rng.shuffle(groups[name])
    selected = []
    order = V265_PRIORITY if strategy == "V265" else sorted(groups)
    while len(selected) < sample_size and any(groups.values()):
        for name in order:
            if groups.get(name) and len(selected) < sample_size:
                selected.append({**groups[name].pop(0), "sample_stratum": name})
    return selected


def semantic_evaluation(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], pairwise_results: list[dict], threshold: float, top_k: int, sample_size: int, seed: int, max_attempts: int, requester: Callable[..., object], model: str, headers: dict[str, str], response_budget: int, sampling_strategy: str = "V264") -> dict:
    sample = stratified_sample(rows, pairwise_results, threshold, sample_size, seed, top_k, sampling_strategy)
    pairwise_by_source = {item["source_id"]: item for item in pairwise_results}
    records = []
    for row in sample:
        prompt = compact_semantic_prompt(row, source, target, top_k)
        candidate_ids = {item["iri"] for item in row["retrieved_candidates"][:top_k]}
        attempts, lifecycle = 0, None
        started = perf_counter()
        for attempts in range(1, max_attempts + 1):
            try:
                response = requester("POST", headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": response_budget}, timeout=30)
                lifecycle = classify_response(response, candidate_ids, response_budget, round((perf_counter() - started) * 1000, 3))
            except Exception as error:
                lifecycle = {"final_status": "TRANSPORT_ERROR", "http_status": None, "latency_ms": round((perf_counter() - started) * 1000, 3), "error_type": type(error).__name__}
            if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"} or attempts == max_attempts:
                break
        parsed_target = None
        # classify_response intentionally stores no content; safely reparse only
        # from structured result fields supplied by this evaluator below.
        # We obtain it from the last response body without persisting raw content.
        if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}:
            content = response.json()["choices"][0]["message"].get("content", "")
            parsed = json.loads(content[content.find("{"):content.rfind("}") + 1])
            parsed_target, relation = parsed["candidate_id"], parsed["relation"]
        else:
            relation = None
        pairwise = pairwise_by_source[row["source_iri"]]
        # The reference is used only now, after response validity/selection.
        candidate_valid = lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}
        records.append({"source_id": row["source_iri"], "sample_stratum": row["sample_stratum"],
                        "candidate_ids": sorted(candidate_ids), "candidate_set_hash": hashlib.sha256("|".join(sorted(candidate_ids)).encode()).hexdigest(),
                        "prompt_variant": "QSEM_COMPACT_PROFILE_V1", "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
                        "prompt_char_length": len(prompt), "retry_count": attempts - 1,
                        "qwen_candidate_id": parsed_target, "qwen_relation": relation,
                        "candidate_valid": candidate_valid, "r1_target": row["selected_candidate_iri"], "r1_top1_score": row["selected_candidate_score"],
                        "r1_top2_score": row["retrieved_candidates"][1]["score"] if len(row["retrieved_candidates"]) > 1 else None,
                        "r1_margin": _margin(row), "r1_topk_spread": float(row["retrieved_candidates"][0]["score"]) - float(row["retrieved_candidates"][top_k - 1]["score"]),
                        "r2_target": min(row["retrieved_candidates"][:top_k], key=lambda item: (-item["r2_combined_score"], item["iri"]))["iri"],
                        "pairwise_target": pairwise["pairwise_target"],
                        "gold_target_id": row["gold_target_iri"], "gold_rank": row["gold_rank"], "nontrivial": row["nontrivial"],
                        **lifecycle})
    valid = [item for item in records if item["candidate_valid"]]
    def target_accuracy(items, key):
        return sum(item[key] == item["gold_target_id"] for item in items) / len(items) if items else None
    def subset(name): return [item for item in valid if item["sample_stratum"] == name]
    disagreement = {name: 0 for name in ("deterministic_correct_qwen_correct", "deterministic_correct_qwen_wrong", "deterministic_wrong_qwen_correct", "deterministic_wrong_qwen_wrong", "deterministic_abstain_qwen_correct", "deterministic_abstain_qwen_wrong")}
    for item in valid:
        deterministic_correct, qwen_correct = item["pairwise_target"] == item["gold_target_id"], item["qwen_candidate_id"] == item["gold_target_id"]
        abstain = next(row for row in sample if row["source_iri"] == item["source_id"])["selected_candidate_score"] < threshold
        if abstain: key = "deterministic_abstain_qwen_correct" if qwen_correct else "deterministic_abstain_qwen_wrong"
        elif deterministic_correct: key = "deterministic_correct_qwen_correct" if qwen_correct else "deterministic_correct_qwen_wrong"
        else: key = "deterministic_wrong_qwen_correct" if qwen_correct else "deterministic_wrong_qwen_wrong"
        disagreement[key] += 1
    return {"protocol": "OAEI_QWEN_COMPACT_SHARED_TOPK_SEMANTIC_V1", "sample_size": len(sample), "seed": seed, "sampling_strategy": sampling_strategy, "sampling_priority": list(V265_PRIORITY) if sampling_strategy == "V265" else None, "sampled_source_ids": [row["source_iri"] for row in sample], "top_k": top_k, "max_attempts": max_attempts, "response_budget": response_budget,
            "sample_strata": {name: sum(item["sample_stratum"] == name for item in sample) for name in sorted({item["sample_stratum"] for item in sample})}, "records": records,
            "metrics": {"technical_valid_rate": len(valid) / len(records) if records else None, "candidate_valid_rate": len(valid) / len(records) if records else None,
                        "retry_rate": sum(item["retry_count"] > 0 for item in records) / len(records) if records else None,
                        "mean_latency_ms": sum(item["latency_ms"] for item in records) / len(records) if records else None,
                        "target_selection_accuracy": target_accuracy(valid, "qwen_candidate_id"), "relation_accuracy": sum(item["qwen_relation"] == "EQUIVALENT" for item in valid) / len(valid) if valid else None,
                        "combined_mapping_accuracy": sum(item["qwen_candidate_id"] == item["gold_target_id"] and item["qwen_relation"] == "EQUIVALENT" for item in valid) / len(valid) if valid else None,
                        "abstention_rate": sum(item["qwen_candidate_id"] == "NONE" for item in valid) / len(valid) if valid else None,
                        "r1_same_sample_accuracy": target_accuracy(valid, "r1_target"), "r2_same_sample_accuracy": target_accuracy(valid, "r2_target"), "pairwise_same_sample_accuracy": target_accuracy(valid, "pairwise_target"),
                        "nontrivial_accuracy": target_accuracy([item for item in valid if item["nontrivial"]], "qwen_candidate_id"),
                        "rank1_abstention_recovery": target_accuracy(subset("rank1_threshold_abstention"), "qwen_candidate_id"), "rank2_5_recovery": target_accuracy(subset("gold_rank_2_5"), "qwen_candidate_id"), "rank6_10_recovery": target_accuracy(subset("gold_rank_6_10"), "qwen_candidate_id"), "easy_control_accuracy": target_accuracy(subset("easy_control"), "qwen_candidate_id"), "disagreement": disagreement,
                        "failure_taxonomy": {status: sum(item["final_status"] == status for item in records) for status in ("TRANSPORT_ERROR", "EMPTY_RESPONSE", "TRUNCATED_RESPONSE", "JSON_PARSE_ERROR", "SCHEMA_VALIDATION_ERROR", "OUT_OF_CANDIDATE", "MODEL_ABSTENTION", "VALID_SELECTION", "UNKNOWN_RESPONSE_FAILURE")}}}


def repeated_call_diagnostic(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], top_k: int, repeat_count: int, max_attempts: int, requester: Callable[..., object], model: str, headers: dict[str, str], response_budget: int) -> dict:
    """Repeat frozen prompts; response content is parsed transiently, never saved."""
    records = []
    for row in rows:
        prompt = compact_semantic_prompt(row, source, target, top_k)
        candidate_ids = {item["iri"] for item in row["retrieved_candidates"][:top_k]}
        for repeat_index in range(repeat_count):
            attempts, lifecycle, response = 0, None, None
            started = perf_counter()
            for attempts in range(1, max_attempts + 1):
                try:
                    response = requester("POST", headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": response_budget}, timeout=30)
                    lifecycle = classify_response(response, candidate_ids, response_budget, round((perf_counter() - started) * 1000, 3))
                except Exception as error:
                    lifecycle = {"final_status": "TRANSPORT_ERROR", "http_status": None, "latency_ms": round((perf_counter() - started) * 1000, 3), "error_type": type(error).__name__}
                if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"} or attempts == max_attempts:
                    break
            candidate, relation = None, None
            if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}:
                content = response.json()["choices"][0]["message"].get("content", "")
                parsed = json.loads(content[content.find("{"):content.rfind("}") + 1])
                candidate, relation = parsed["candidate_id"], parsed["relation"]
            # Reference labels are attached only after the repeated inference.
            records.append({"source_id": row["source_iri"], "repeat_index": repeat_index, "candidate_set_hash": hashlib.sha256("|".join(sorted(candidate_ids)).encode()).hexdigest(), "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(), "retry_count": attempts - 1, "qwen_candidate_id": candidate, "qwen_relation": relation, "candidate_valid": lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}, "gold_target_id": row["gold_target_iri"], **lifecycle})
    per_case = []
    for source_id in sorted({item["source_id"] for item in records}):
        group = [item for item in records if item["source_id"] == source_id]
        valid = [item for item in group if item["candidate_valid"]]
        selections = [item["qwen_candidate_id"] for item in valid]
        relations = [item["qwen_relation"] for item in valid]
        modal = max(sorted(set(selections)), key=selections.count) if selections else None
        per_case.append({"source_id": source_id, "calls": len(group), "candidate_valid_calls": len(valid), "unique_selected_candidates": len(set(selections)), "same_candidate_selection_rate": max((selections.count(value) for value in set(selections)), default=0) / len(selections) if selections else None, "same_relation_rate": max((relations.count(value) for value in set(relations)), default=0) / len(relations) if relations else None, "modal_candidate": modal, "modal_selection_correct": modal == group[0]["gold_target_id"] if modal else None, "technical_invalid_calls": len(group) - len(valid)})
    valid_records = [item for item in records if item["candidate_valid"]]
    return {"protocol": "OAEI_QWEN_IDENTICAL_PROMPT_CONSISTENCY_V1", "n_cases": len(per_case), "repeat_count": repeat_count, "records": records, "per_case": per_case,
            "metrics": {"candidate_valid_rate": len(valid_records) / len(records) if records else None, "same_candidate_selection_rate": sum(item["same_candidate_selection_rate"] for item in per_case if item["same_candidate_selection_rate"] is not None) / sum(item["same_candidate_selection_rate"] is not None for item in per_case) if per_case else None, "same_relation_rate": sum(item["same_relation_rate"] for item in per_case if item["same_relation_rate"] is not None) / sum(item["same_relation_rate"] is not None for item in per_case) if per_case else None, "modal_selection_accuracy": sum(item["modal_selection_correct"] for item in per_case if item["modal_selection_correct"] is not None) / sum(item["modal_selection_correct"] is not None for item in per_case) if per_case else None, "unstable_cases": sum(item["unique_selected_candidates"] > 1 for item in per_case), "failure_taxonomy": {status: sum(item["final_status"] == status for item in records) for status in ("TRANSPORT_ERROR", "EMPTY_RESPONSE", "TRUNCATED_RESPONSE", "JSON_PARSE_ERROR", "SCHEMA_VALIDATION_ERROR", "OUT_OF_CANDIDATE", "MODEL_ABSTENTION", "VALID_SELECTION", "UNKNOWN_RESPONSE_FAILURE")}}}
