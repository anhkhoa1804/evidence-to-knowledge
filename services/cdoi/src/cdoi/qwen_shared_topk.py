"""Bounded, proposal-only Qwen comparison on deterministic shared Top-K sets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from time import perf_counter
from typing import Callable

from .llm_evaluation import LLMAlignmentResponse


@dataclass(frozen=True)
class SharedTopKCase:
    source_iri: str
    source_label: str
    candidate_ids: tuple[str, ...]
    deterministic_target: str | None
    deterministic_relation: str
    gold_target: str
    gold_rank: int
    trivial_lexical: bool
    stratum: str


def _stratum(row: dict, threshold: float) -> str:
    if row["selected_candidate_score"] < threshold and row["gold_in_top_k"]:
        return "deterministic_threshold_abstention"
    if row["selected_candidate_iri"] != row["gold_target_iri"] and row["gold_in_top_k"]:
        return "deterministic_wrong_target"
    if row["nontrivial"]:
        return "nontrivial"
    return "trivial_lexical"


def stratified_cases(rows: list[dict], threshold: float, sample_size: int) -> list[SharedTopKCase]:
    """Deterministically round-robin strata; gold remains evaluation-only."""
    grouped: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda item: item["source_iri"]):
        grouped.setdefault(_stratum(row, threshold), []).append(row)
    selected: list[SharedTopKCase] = []
    while len(selected) < sample_size and any(grouped.values()):
        for name in sorted(grouped):
            if not grouped[name] or len(selected) >= sample_size:
                continue
            row = grouped[name].pop(0)
            deterministic = row["selected_candidate_iri"] if row["selected_candidate_score"] >= threshold else None
            selected.append(SharedTopKCase(row["source_iri"], row["source_label"], tuple(candidate["iri"] for candidate in row["retrieved_candidates"]), deterministic, "EQUIVALENT" if deterministic else "UNRESOLVED", row["gold_target_iri"], row["gold_rank"], row["trivial_lexical"], name))
    return selected


def prompt_for(case: SharedTopKCase, row: dict) -> str:
    """Construct the model input without gold labels or candidate injection."""
    candidates = [{"iri": candidate["iri"], "label": candidate["label"], "definition": candidate["definition"]} for candidate in row["retrieved_candidates"] if candidate["iri"] in case.candidate_ids]
    return "\n".join((
        "Return JSON only with status, semantic_relation, target_id, evidence, and self_reported_confidence.",
        "Choose target_id only from the supplied candidates. Use status UNRESOLVED and target_id null to abstain.",
        f"Source IRI: {case.source_iri}",
        f"Source label: {case.source_label}",
        "Candidates: " + json.dumps(candidates, ensure_ascii=False),
    ))


def evaluate_shared_topk(rows: list[dict], threshold: float, sample_size: int, responder: Callable[[str], str], max_attempts: int = 2) -> dict[str, object]:
    """Evaluate a bounded responder; it cannot retrieve or select outside Top-K."""
    by_source = {row["source_iri"]: row for row in rows}
    results = []
    for case in stratified_cases(rows, threshold, sample_size):
        prompt = prompt_for(case, by_source[case.source_iri])
        started, retries, response, error = perf_counter(), 0, None, None
        for attempt in range(max_attempts):
            try:
                response = LLMAlignmentResponse.model_validate_json(responder(prompt))
                if response.target_id not in set(case.candidate_ids) | {None}:
                    raise ValueError("out_of_candidate_selection")
                break
            except (ValueError, KeyError) as exc:
                error = "out_of_candidate_selection" if str(exc) == "out_of_candidate_selection" else "parse_or_schema_error"
                retries = attempt + 1
                response = None
        target = response.target_id if response else None
        relation = response.relation if response else "UNRESOLVED"
        results.append({"source_iri": case.source_iri, "candidate_set_hash": hashlib.sha256("|".join(case.candidate_ids).encode()).hexdigest(), "candidate_ids": list(case.candidate_ids), "stratum": case.stratum, "deterministic_target": case.deterministic_target, "deterministic_relation": case.deterministic_relation, "qwen_target": target, "qwen_relation": relation, "gold_target_iri": case.gold_target, "gold_rank": case.gold_rank, "trivial_lexical": case.trivial_lexical, "retry_count": retries, "final_status": "valid" if response else error, "latency_ms": round((perf_counter() - started) * 1000, 3), "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()})
    valid = [item for item in results if item["final_status"] == "valid"]
    return {"protocol": "OAEI_SHARED_TOPK_QWEN_COMPARISON", "n": len(results), "max_attempts": max_attempts, "cases": results, "metrics": {"valid_response_rate": len(valid) / len(results) if results else None, "parse_schema_failure_rate": sum(item["final_status"] == "parse_or_schema_error" for item in results) / len(results) if results else None, "out_of_candidate_selection_rate": sum(item["final_status"] == "out_of_candidate_selection" for item in results) / len(results) if results else None, "retry_rate": sum(item["retry_count"] > 0 for item in results) / len(results) if results else None, "abstention_rate": sum(item["qwen_target"] is None for item in results) / len(results) if results else None, "target_selection_accuracy": sum(item["qwen_target"] == item["gold_target_iri"] for item in results) / len(results) if results else None, "deterministic_correct_qwen_wrong": sum(item["deterministic_target"] == item["gold_target_iri"] and item["qwen_target"] != item["gold_target_iri"] for item in results), "deterministic_wrong_qwen_correct": sum(item["deterministic_target"] != item["gold_target_iri"] and item["qwen_target"] == item["gold_target_iri"] for item in results)}}
