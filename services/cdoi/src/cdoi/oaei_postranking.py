"""V2.6.3 diagnostics over persisted OAEI candidate sets, never gold-driven scoring."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
from statistics import mean, median, pstdev

from .oaei_full_corpus import ConceptProfile, OAEIFullCorpusMatcher


def _quantile(values: list[float], proportion: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * proportion
    low, high = math.floor(position), math.ceil(position)
    return values[low] if low == high else values[low] + (values[high] - values[low]) * (position - low)


def _summary(values: list[float]) -> dict[str, float | None]:
    return {"n": len(values), "mean": mean(values) if values else None, "median": median(values) if values else None, "stddev": pstdev(values) if len(values) > 1 else 0.0 if values else None, **{f"p{int(p * 100)}": _quantile(values, p) for p in (0.10, 0.25, 0.50, 0.75, 0.90)}}


def load_profiles(index_path: Path) -> tuple[dict[str, ConceptProfile], dict[str, ConceptProfile]]:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return ({item["iri"]: ConceptProfile(**{key: tuple(value) if isinstance(value, list) else value for key, value in item.items()}) for item in data["source"]}, {item["iri"]: ConceptProfile(**{key: tuple(value) if isinstance(value, list) else value for key, value in item.items()}) for item in data["target"]})


def enrich_rows(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile]) -> list[dict]:
    """Add R2 scores to the fixed R1 Top-K; reference fields are untouched."""
    matcher = OAEIFullCorpusMatcher(Path("."))
    enriched = []
    for row in rows:
        profile = source[row["source_iri"]]
        candidates = []
        for candidate in row["retrieved_candidates"]:
            lexical = matcher._score(profile, target[candidate["iri"]], "R1_FUZZY_LEXICAL")
            combined = matcher._score(profile, target[candidate["iri"]], "R2_LEXICAL_NEIGHBORHOOD")
            context = (combined - 0.8 * lexical) / 0.2
            candidates.append({**candidate, "r2_lexical_score": round(lexical, 6), "r2_context_score": round(context, 6), "r2_combined_score": round(combined, 6), "context_delta": round(combined - lexical, 6)})
        top1, top2 = candidates[0], candidates[1] if len(candidates) > 1 else None
        source_profile, selected_profile = source[row["source_iri"]], target[top1["iri"]]
        enriched.append({**row, "retrieved_candidates": candidates, "r1_retrieval_score": row["selected_candidate_score"], "r2_lexical_component": top1["r2_lexical_score"], "r2_context_component": top1["r2_context_score"], "r2_combined_score": top1["r2_combined_score"], "r2_context_delta": top1["context_delta"], "top1_top2_r1_margin": round(top1["score"] - top2["score"], 6) if top2 else None, "definition_available": bool(source_profile.definition and selected_profile.definition), "parent_context_available": bool(source_profile.parents and selected_profile.parents), "child_context_available": bool(source_profile.children and selected_profile.children), "property_context_available": bool((source_profile.object_properties or source_profile.data_properties) and (selected_profile.object_properties or selected_profile.data_properties))})
    return enriched


def rank1_acceptance(rows: list[dict], threshold: float) -> dict[str, object]:
    rank1 = [row for row in rows if row["gold_rank"] == 1]
    groups = {"A1_rank1_correctly_emitted": [row for row in rank1 if row["selected_candidate_score"] >= threshold], "A2_rank1_abstained": [row for row in rank1 if row["selected_candidate_score"] < threshold], "A3_rank1_incorrect": []}
    fields = {"lexical_score": "r2_lexical_component", "context_score": "r2_context_component", "combined_score": "r2_combined_score", "threshold_margin": None, "top1_top2_margin": "top1_top2_r1_margin"}
    summary = {}
    for name, group in groups.items():
        distributions = {label: _summary([row[key] if key else row["selected_candidate_score"] - threshold for row in group if (row[key] if key else True) is not None]) for label, key in fields.items()}
        summary[name] = {"n": len(group), "distributions": distributions, "definition_available_rate": mean([row["definition_available"] for row in group]) if group else None, "parent_context_available_rate": mean([row["parent_context_available"] for row in group]) if group else None, "child_context_available_rate": mean([row["child_context_available"] for row in group]) if group else None, "property_context_available_rate": mean([row["property_context_available"] for row in group]) if group else None}
    return {"groups": summary, "cases": {name: group for name, group in groups.items()}}


def score_scale(rows: list[dict], threshold: float) -> dict[str, object]:
    groups = {"gold_candidates_in_top_k": [], "wrong_r1_top_candidates": [], "rank1_emitted_true_positive": [], "rank1_abstained_true_positive": []}
    for row in rows:
        for candidate in row["retrieved_candidates"]:
            if candidate["iri"] == row["gold_target_iri"]:
                groups["gold_candidates_in_top_k"].append(candidate)
        if row["selected_candidate_iri"] != row["gold_target_iri"]:
            groups["wrong_r1_top_candidates"].append(row["retrieved_candidates"][0])
        if row["gold_rank"] == 1:
            groups["rank1_emitted_true_positive" if row["selected_candidate_score"] >= threshold else "rank1_abstained_true_positive"].append(row["retrieved_candidates"][0])
    return {name: {"n": len(group), "r1_lexical": _summary([item["r2_lexical_score"] for item in group]), "r2_context": _summary([item["r2_context_score"] for item in group]), "r2_combined": _summary([item["r2_combined_score"] for item in group]), "context_delta": _summary([item["context_delta"] for item in group])} for name, group in groups.items()}


def rerank(rows: list[dict], threshold: float, k: int) -> dict[str, object]:
    results = []
    for row in rows:
        candidates = row["retrieved_candidates"][:k]
        ranked = sorted(candidates, key=lambda item: (-item["r2_combined_score"], item["iri"]))
        gold_rank = next((index + 1 for index, item in enumerate(ranked) if item["iri"] == row["gold_target_iri"]), None)
        selected = ranked[0]
        accepted = selected["iri"] if selected["r2_combined_score"] >= threshold else None
        results.append({"source_iri": row["source_iri"], "retrieval_gold_rank": row["gold_rank"], "reranked_gold_rank": gold_rank, "reranked_target": selected["iri"], "reranked_score": selected["r2_combined_score"], "accepted_target": accepted, "trivial_lexical": row["trivial_lexical"]})
    eligible = [result for result in results if result["retrieval_gold_rank"] <= k]
    return {"k": k, "n": len(results), "oracle_at_k": len(eligible) / len(results), "reranked_top1_accuracy": sum(item["reranked_gold_rank"] == 1 for item in results) / len(results), "gap_to_oracle": len(eligible) / len(results) - sum(item["reranked_gold_rank"] == 1 for item in results) / len(results), "frozen_threshold_accepted_correct": sum(item["accepted_target"] is not None and item["reranked_gold_rank"] == 1 for item in results) / len(results), "gold_promoted": sum(item["reranked_gold_rank"] is not None and item["reranked_gold_rank"] < item["retrieval_gold_rank"] for item in results), "gold_demoted": sum(item["reranked_gold_rank"] is not None and item["reranked_gold_rank"] > item["retrieval_gold_rank"] for item in results), "gold_unchanged": sum(item["reranked_gold_rank"] == item["retrieval_gold_rank"] for item in results), "rank1_preserved": sum(item["retrieval_gold_rank"] == 1 and item["reranked_gold_rank"] == 1 for item in results), "rank1_damaged": sum(item["retrieval_gold_rank"] == 1 and item["reranked_gold_rank"] != 1 for item in results), "rank_gt1_promoted_to_1": sum(item["retrieval_gold_rank"] > 1 and item["reranked_gold_rank"] == 1 for item in results), "nontrivial_reranked_top1_accuracy": sum(item["reranked_gold_rank"] == 1 and not item["trivial_lexical"] for item in results) / sum(not item["trivial_lexical"] for item in results), "results": results}


def artifact_hash(rows: list[dict]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
