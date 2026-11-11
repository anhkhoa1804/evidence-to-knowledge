"""Post-retrieval gold-vs-hard-negative and relative-ranking diagnostics.

All feature construction in this module accepts a source and its persisted
candidate list only.  The OAEI reference is attached afterwards solely to
label records and calculate metrics.  Nothing here participates in CDOI's
semantic decision or commitment path.
"""

from __future__ import annotations

import math
from collections import Counter
from statistics import mean, median, pstdev

from .oaei_full_corpus import ConceptProfile, normalize


def _jaccard(left: set[str], right: set[str]) -> float | None:
    if not left or not right:
        return None
    return len(left & right) / len(left | right)


def _tokens(values: tuple[str, ...]) -> set[str]:
    return set(normalize(" ".join(values)).split())


def _definition_similarity(source: ConceptProfile, candidate: ConceptProfile) -> float | None:
    if not source.definition or not candidate.definition:
        return None
    left, right = set(normalize(source.definition).split()), set(normalize(candidate.definition).split())
    return _jaccard(left, right)


def _round(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def candidate_features(row: dict, source: dict[str, ConceptProfile], target: dict[str, ConceptProfile]) -> list[dict]:
    """Score only supplied candidates; deliberately does not read gold fields."""
    profile = source[row["source_iri"]]
    parents, children = _tokens(profile.parents), _tokens(profile.children)
    properties = _tokens(profile.object_properties + profile.data_properties)
    candidates = row["retrieved_candidates"]
    top1_score = float(candidates[0]["score"]) if candidates else 0.0
    top2_score = float(candidates[1]["score"]) if len(candidates) > 1 else None
    scores = [float(item["score"]) for item in candidates]
    records = []
    for candidate in candidates:
        target_profile = target[candidate["iri"]]
        parent = _jaccard(parents, _tokens(target_profile.parents))
        child = _jaccard(children, _tokens(target_profile.children))
        property_score = _jaccard(properties, _tokens(target_profile.object_properties + target_profile.data_properties))
        lexical, context = float(candidate["r2_lexical_score"]), float(candidate["r2_context_score"])
        records.append({
            "source_id": row["source_iri"], "candidate_id": candidate["iri"],
            "candidate_retrieval_rank": int(candidate["rank"]), "candidate_relative_rank": int(candidate["rank"]),
            "lexical_score": lexical, "context_score": context,
            "r2_combined_score": float(candidate["r2_combined_score"]),
            "parent_similarity": _round(parent), "child_similarity": _round(child),
            "property_similarity": _round(property_score),
            "definition_similarity": _round(_definition_similarity(profile, target_profile)),
            "score_difference_from_retrieval_top1": _round(float(candidate["score"]) - top1_score),
            "top1_top2_margin": _round(top1_score - top2_score) if top2_score is not None else None,
            "top1_topk_spread": _round(top1_score - min(scores)) if scores else None,
        })
    return records


def labelled_pair_records(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile]) -> tuple[list[dict], list[dict]]:
    """Attach reference-derived labels only after candidate feature generation."""
    all_records, pairs = [], []
    for row in rows:
        records = candidate_features(row, source, target)
        # This is the first reference read in this function, after scores exist.
        gold_id = row["gold_target_iri"]
        gold = next((item for item in records if item["candidate_id"] == gold_id), None)
        wrong = next((item for item in records if item["candidate_id"] != gold_id), None)
        for item in records:
            all_records.append({**item, "is_gold": item["candidate_id"] == gold_id,
                                "is_hard_negative": bool(wrong and item["candidate_id"] == wrong["candidate_id"]),
                                "nontrivial": bool(row["nontrivial"]), "gold_original_rank": row["gold_rank"],
                                "rank1_abstention": row["gold_rank"] == 1 and row["selected_candidate_score"] < 0.82})
        if gold and wrong:
            deltas = {f"delta_{name}": _round(float(gold[name]) - float(wrong[name]))
                      if gold.get(name) is not None and wrong.get(name) is not None else None
                      for name in ("lexical_score", "context_score", "r2_combined_score", "parent_similarity", "child_similarity", "property_similarity", "definition_similarity")}
            pairs.append({"source_id": row["source_iri"], "gold_candidate_id": gold_id,
                          "hard_negative_candidate_id": wrong["candidate_id"], "gold_original_rank": row["gold_rank"],
                          "nontrivial": bool(row["nontrivial"]),
                          "rank1_abstention": row["gold_rank"] == 1 and row["selected_candidate_score"] < 0.82,
                          **deltas})
    return all_records, pairs


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values); position = (len(values) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return values[low] if low == high else values[low] + (values[high] - values[low]) * (position - low)


def summary(values: list[float | None]) -> dict[str, float | int | None]:
    present = [float(value) for value in values if value is not None]
    return {"n": len(present), "mean": mean(present) if present else None, "median": median(present) if present else None,
            "std": pstdev(present) if len(present) > 1 else 0.0 if present else None,
            **{f"p{int(fraction * 100)}": _quantile(present, fraction) for fraction in (.10, .25, .50, .75, .90)}}


FEATURES = ("lexical_score", "context_score", "r2_combined_score", "parent_similarity", "child_similarity", "property_similarity", "definition_similarity", "candidate_retrieval_rank")


def discrimination(pairs: list[dict], records: list[dict], predicate=lambda _: True) -> dict:
    selected_pairs = [item for item in pairs if predicate(item)]
    source_ids = {item["source_id"] for item in selected_pairs}
    selected_records = [item for item in records if item["source_id"] in source_ids]
    result = {"n_pairs": len(selected_pairs), "gold": {}, "hard_negative": {}, "deltas": {}}
    for feature in FEATURES:
        result["gold"][feature] = summary([item.get(feature) for item in selected_records if item["is_gold"]])
        result["hard_negative"][feature] = summary([item.get(feature) for item in selected_records if item["is_hard_negative"]])
        delta_name = "delta_" + feature
        values = [item.get(delta_name) for item in selected_pairs]
        present = [float(value) for value in values if value is not None]
        result["deltas"][feature] = {"summary": summary(present), "greater_than_zero": sum(value > 0 for value in present) / len(present) if present else None,
                                      "equal_zero": sum(value == 0 for value in present) / len(present) if present else None,
                                      "less_than_zero": sum(value < 0 for value in present) / len(present) if present else None}
    return result


def stratified_discrimination(pairs: list[dict], records: list[dict]) -> dict:
    return {
        "all_gold_in_topk": discrimination(pairs, records),
        "nontrivial": discrimination(pairs, records, lambda item: item["nontrivial"]),
        "gold_rank_1": discrimination(pairs, records, lambda item: item["gold_original_rank"] == 1),
        "gold_rank_2_5": discrimination(pairs, records, lambda item: 2 <= item["gold_original_rank"] <= 5),
        "gold_rank_6_10": discrimination(pairs, records, lambda item: 6 <= item["gold_original_rank"] <= 10),
        "rank1_abstentions": discrimination(pairs, records, lambda item: item["rank1_abstention"]),
    }


MARGIN_BUCKETS = (("lt_0_02", float("-inf"), .02), ("0_02_0_05", .02, .05), ("0_05_0_10", .05, .10), ("0_10_0_20", .10, .20), ("0_20_0_30", .20, .30), ("gte_0_30", .30, float("inf")))


def margin_analysis(rows: list[dict], threshold: float) -> dict:
    buckets = []
    for name, low, high in MARGIN_BUCKETS:
        group = []
        for row in rows:
            scores = [float(item["score"]) for item in row["retrieved_candidates"]]
            margin = scores[0] - scores[1] if len(scores) > 1 else None
            if margin is not None and low <= margin < high:
                group.append((row, margin, scores[0] - scores[min(4, len(scores) - 1)]))
        n = len(group)
        ranks = Counter("1" if item[0]["gold_rank"] == 1 else "2_5" if item[0]["gold_rank"] <= 5 else "6_10" if item[0]["gold_rank"] <= 10 else "11_20" if item[0]["gold_rank"] <= 20 else "gt_20" for item in group)
        emitted = [item for item in group if item[0]["selected_candidate_score"] >= threshold]
        buckets.append({"bucket": name, "n": n, "top1_correctness": sum(item[0]["gold_rank"] == 1 for item in group) / n if n else None,
                        "precision_if_emitted": sum(item[0]["gold_rank"] == 1 for item in emitted) / len(emitted) if emitted else None,
                        "abstention_rate": sum(item[0]["selected_candidate_score"] < threshold for item in group) / n if n else None,
                        "nontrivial_proportion": sum(item[0]["nontrivial"] for item in group) / n if n else None,
                        "gold_rank_distribution": dict(ranks), "margin": summary([item[1] for item in group]), "top1_top5_spread": summary([item[2] for item in group])})
    return {"score_space": "R1_FUZZY_LEXICAL", "buckets": buckets}


COMPONENTS = ("lexical_score", "parent_similarity", "child_similarity", "property_similarity")


def compare_candidates(left: dict, right: dict) -> int:
    """Fixed, label-free component-vote comparator; retrieval rank resolves ties."""
    left_wins = right_wins = 0
    for feature in COMPONENTS:
        a, b = left.get(feature), right.get(feature)
        if a is None or b is None or a == b:
            continue
        if a > b: left_wins += 1
        else: right_wins += 1
    if left_wins != right_wins:
        return -1 if left_wins > right_wins else 1
    if left["candidate_retrieval_rank"] != right["candidate_retrieval_rank"]:
        return -1 if left["candidate_retrieval_rank"] < right["candidate_retrieval_rank"] else 1
    return -1 if left["candidate_id"] < right["candidate_id"] else 1 if left["candidate_id"] > right["candidate_id"] else 0


def pairwise_rerank(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], k: int) -> dict:
    """Candidate-only tournament. Gold is read only after ranking for outcomes."""
    results = []
    for row in rows:
        candidates = candidate_features({**row, "retrieved_candidates": row["retrieved_candidates"][:k]}, source, target)
        # A direct comparator sort is deterministic and evaluates only feature records.
        from functools import cmp_to_key
        ranked = sorted(candidates, key=cmp_to_key(compare_candidates))
        # Evaluation begins here.
        gold_rank = next((index + 1 for index, item in enumerate(ranked) if item["candidate_id"] == row["gold_target_iri"]), None)
        before = row["gold_rank"]
        outcome = "GOLD_NOT_IN_TOPK" if before > k else "CORRECT_PRESERVED" if before == 1 and gold_rank == 1 else "CORRECT_PROMOTED" if gold_rank == 1 else "CORRECT_DEMOTED" if before == 1 else "GOLD_STILL_BELOW_TOP1"
        results.append({"source_id": row["source_iri"], "retrieval_gold_rank": before, "pairwise_gold_rank": gold_rank,
                        "pairwise_target": ranked[0]["candidate_id"], "trivial_lexical": row["trivial_lexical"], "outcome": outcome})
    eligible = [item for item in results if item["retrieval_gold_rank"] <= k]
    n = len(results); nontrivial = [item for item in results if not item["trivial_lexical"]]
    return {"k": k, "n": n, "oracle_at_k": len(eligible) / n if n else None,
            "pairwise_reranked_top1_accuracy": sum(item["pairwise_gold_rank"] == 1 for item in results) / n if n else None,
            "gap_to_oracle": len(eligible) / n - sum(item["pairwise_gold_rank"] == 1 for item in results) / n if n else None,
            "rank_gt1_promoted_to_1": sum(item["retrieval_gold_rank"] > 1 and item["pairwise_gold_rank"] == 1 for item in results),
            "rank1_preserved": sum(item["retrieval_gold_rank"] == 1 and item["pairwise_gold_rank"] == 1 for item in results),
            "rank1_damaged": sum(item["retrieval_gold_rank"] == 1 and item["pairwise_gold_rank"] != 1 for item in results),
            "net_target_selection_gain": sum(item["pairwise_gold_rank"] == 1 for item in results) - sum(item["retrieval_gold_rank"] == 1 for item in results),
            "nontrivial_top1_accuracy": sum(item["pairwise_gold_rank"] == 1 for item in nontrivial) / len(nontrivial) if nontrivial else None,
            "outcome_taxonomy": dict(Counter(item["outcome"] for item in results)), "results": results}


def confidence_table(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], pairwise_results: list[dict]) -> list[dict]:
    """Evaluation artifact for future study; no learned model is fit here."""
    pairwise_by_id = {item["source_id"]: item for item in pairwise_results}
    output = []
    for row in rows:
        features = candidate_features(row, source, target)
        top = features[0]
        pairwise = pairwise_by_id[row["source_iri"]]
        # Labels are deliberately the final operation.
        output.append({"source_id": row["source_iri"], "top1_lexical": top["lexical_score"], "top1_context": top["context_score"], "top1_parent": top["parent_similarity"], "top1_child": top["child_similarity"], "top1_property": top["property_similarity"], "top1_score": row["selected_candidate_score"], "top1_top2_margin": top["top1_top2_margin"], "top1_topk_spread": top["top1_topk_spread"], "pairwise_target": pairwise["pairwise_target"], "r1_top1_correct": row["gold_rank"] == 1, "pairwise_top1_correct": pairwise["pairwise_gold_rank"] == 1, "nontrivial": row["nontrivial"]})
    return output
