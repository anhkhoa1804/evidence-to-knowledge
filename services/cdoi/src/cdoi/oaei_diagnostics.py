"""Pure, post-ranking diagnostics for the frozen OAEI evaluation boundary."""

from __future__ import annotations

from statistics import median
from typing import Iterable


RANK_BUCKETS = (("rank_1", 1, 1), ("rank_2_5", 2, 5), ("rank_6_10", 6, 10), ("rank_11_20", 11, 20))
MARGIN_BUCKETS = (("within_0_02", -0.02, float("inf")), ("within_0_05", -0.05, -0.02), ("within_0_10", -0.10, -0.05), ("below_0_10", float("-inf"), -0.10))


def _safe_divide(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _emission(row: dict, threshold: float, mode: str = "D0_FROZEN") -> tuple[str | None, float]:
    if mode == "D0_FROZEN":
        return (row["selected_candidate_iri"] if row["selected_candidate_score"] >= threshold else None, row["selected_candidate_score"])
    candidates = row["retrieved_candidates"]
    def normalized(candidate: dict) -> float:
        # D1 is intentionally local to this diagnostic.  Existing R2 treats
        # unavailable context as zero; D1 removes only that unavailable weight.
        return candidate["score"] if candidate["context_available"] else candidate["lexical_score"]
    selected = max(candidates, key=lambda candidate: (normalized(candidate), candidate["iri"]))
    score = normalized(selected)
    return (selected["iri"] if score >= threshold else None, score)


def threshold_sweep(rows: Iterable[dict], thresholds: list[float], frozen_threshold: float) -> dict[str, object]:
    """Evaluate fixed candidate rankings at diagnostic thresholds only."""
    rows = list(rows)
    runs = []
    for threshold in thresholds:
        emitted = [_emission(row, threshold)[0] for row in rows]
        correct = sum(value == row["gold_target_iri"] for row, value in zip(rows, emitted))
        emitted_count = sum(value is not None for value in emitted)
        incorrect = emitted_count - correct
        precision = _safe_divide(correct, emitted_count) or 0.0
        recall = _safe_divide(correct, len(rows)) or 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        nontrivial = [(row, value) for row, value in zip(rows, emitted) if row["nontrivial"]]
        nontrivial_correct = sum(value == row["gold_target_iri"] for row, value in nontrivial)
        nontrivial_emitted = sum(value is not None for _, value in nontrivial)
        nontrivial_precision = _safe_divide(nontrivial_correct, nontrivial_emitted)
        nontrivial_recall = _safe_divide(nontrivial_correct, len(nontrivial))
        runs.append({"threshold": threshold, "is_frozen_threshold": threshold == frozen_threshold, "emitted_mappings": emitted_count, "coverage": _safe_divide(emitted_count, len(rows)), "abstentions": len(rows) - emitted_count, "abstention_rate": _safe_divide(len(rows) - emitted_count, len(rows)), "correct_emitted_mappings": correct, "incorrect_emitted_mappings": incorrect, "precision": precision, "recall": recall, "f1": f1, "false_positive_count": incorrect, "false_commitment_rate": _safe_divide(incorrect, emitted_count), "nontrivial_precision": nontrivial_precision, "nontrivial_recall": nontrivial_recall, "nontrivial_f1": 2 * nontrivial_precision * nontrivial_recall / (nontrivial_precision + nontrivial_recall) if nontrivial_precision and nontrivial_recall else 0.0})
    return {"diagnostic_only": True, "frozen_threshold": frozen_threshold, "runs": runs}


def abstention_cases(rows: Iterable[dict], threshold: float) -> tuple[list[dict], dict[str, object]]:
    cases = []
    for row in rows:
        emitted, score = _emission(row, threshold)
        if row["gold_in_top_k"] and emitted is None:
            case = {**row, "frozen_threshold": threshold, "margin_to_threshold": round(score - threshold, 6), "failure": "THRESHOLD_ABSTENTION"}
            cases.append(case)
    rank_buckets = {name: sum(low <= case["gold_rank"] <= high for case in cases) for name, low, high in RANK_BUCKETS}
    margin_buckets = {name: sum(low <= case["margin_to_threshold"] < high for case in cases) for name, low, high in MARGIN_BUCKETS}
    return cases, {"n": len(cases), "gold_rank_buckets": rank_buckets, "threshold_margin_buckets": margin_buckets, "lexical_difficulty": {"same_normalized_label": sum(case["trivial_lexical"] for case in cases), "different_normalized_label": sum(case["nontrivial"] for case in cases)}, "evidence_availability": {str(count): sum(case["available_feature_count"] == count for case in cases) for count in sorted({case["available_feature_count"] for case in cases})}}


def gold_rank_analysis(rows: Iterable[dict], threshold: float) -> dict[str, dict[str, object]]:
    rows = list(rows)
    buckets = [(name, lambda rank, low=low, high=high: low <= rank <= high) for name, low, high in RANK_BUCKETS] + [("rank_gt_20", lambda rank: rank > 20)]
    output = {}
    for name, contains in buckets:
        group = [row for row in rows if contains(row["gold_rank"])]
        emissions = [_emission(row, threshold)[0] for row in group]
        scores = [row["selected_candidate_score"] for row in group]
        margins = [row["top1_vs_gold_score_margin"] for row in group]
        output[name] = {"n": len(group), "selection_accuracy": _safe_divide(sum(value == row["gold_target_iri"] for row, value in zip(group, emissions)), len(group)), "emission_rate": _safe_divide(sum(value is not None for value in emissions), len(group)), "abstention_rate": _safe_divide(sum(value is None for value in emissions), len(group)), "wrong_target_rate": _safe_divide(sum(value is not None and value != row["gold_target_iri"] for row, value in zip(group, emissions)), len(group)), "mean_semantic_score": sum(scores) / len(scores) if scores else None, "median_semantic_score": median(scores) if scores else None, "mean_score_margin": sum(margins) / len(margins) if margins else None, "median_score_margin": median(margins) if margins else None, "trivial_n": sum(row["trivial_lexical"] for row in group), "nontrivial_n": sum(row["nontrivial"] for row in group)}
    return output


def nontrivial_metrics(rows: Iterable[dict], threshold: float) -> dict[str, object]:
    group = [row for row in rows if row["nontrivial"]]
    emissions = [_emission(row, threshold)[0] for row in group]
    correct = sum(value == row["gold_target_iri"] for row, value in zip(group, emissions))
    emitted = sum(value is not None for value in emissions)
    precision = _safe_divide(correct, emitted) or 0.0
    recall = _safe_divide(correct, len(group)) or 0.0
    ranks = [row["gold_rank"] for row in group]
    return {"n": len(group), **{f"recall_at_{k}": _safe_divide(sum(rank <= k for rank in ranks), len(group)) for k in (1, 5, 10, 20)}, "mrr": sum(1 / rank for rank in ranks) / len(group) if group else None, "emitted_precision": precision, "emitted_recall": recall, "emitted_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "abstention_rate": _safe_divide(sum(value is None for value in emissions), len(group)), "wrong_target_rate": _safe_divide(sum(value is not None and value != row["gold_target_iri"] for row, value in zip(group, emissions)), len(group))}


def available_evidence_comparison(rows: Iterable[dict], threshold: float) -> dict[str, object]:
    cases = []
    for row in rows:
        frozen, frozen_score = _emission(row, threshold, "D0_FROZEN")
        normalized, normalized_score = _emission(row, threshold, "D1_AVAILABLE_NORMALIZED")
        cases.append({"source_iri": row["source_iri"], "gold_target_iri": row["gold_target_iri"], "gold_rank": row["gold_rank"], "available_features": row["available_features"], "available_feature_count": row["available_feature_count"], "frozen_score": frozen_score, "normalized_score": normalized_score, "score_delta": round(normalized_score - frozen_score, 6), "frozen_decision": frozen or "UNRESOLVED", "diagnostic_decision": normalized or "UNRESOLVED", "frozen_correct": frozen == row["gold_target_iri"], "diagnostic_correct": normalized == row["gold_target_iri"], "trivial_lexical": row["trivial_lexical"], "selected_candidate_rank": row["selected_candidate_rank"]})
    changed = [case for case in cases if case["frozen_decision"] != case["diagnostic_decision"]]
    return {"diagnostic_only": True, "modes": {"D0": "frozen scorer including zero for unavailable context", "D1": "renormalize away only unavailable context weight within persisted Top-K"}, "cases": cases, "summary": {"n": len(cases), "decision_changed": len(changed), "score_changed": sum(case["score_delta"] != 0 for case in cases), "frozen_correct": sum(case["frozen_correct"] for case in cases), "diagnostic_correct": sum(case["diagnostic_correct"] for case in cases)}}
