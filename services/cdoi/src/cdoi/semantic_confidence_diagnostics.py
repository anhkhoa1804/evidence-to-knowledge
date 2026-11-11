"""Pure evaluation summaries for persisted R1/R2/Qwen shared-Top-K runs.

All functions preserve an explicit boundary between observable inputs and
reference-only labels.  They are research reporting utilities, never routing or
commitment logic.
"""

from __future__ import annotations

from collections import Counter
from statistics import median

from .oaei_discrimination import candidate_features
from .oaei_full_corpus import ConceptProfile


MARGIN_BUCKETS = (("lt_0_02", float("-inf"), .02), ("0_02_0_05", .02, .05), ("0_05_0_10", .05, .10), ("0_10_0_20", .10, .20), ("0_20_0_30", .20, .30), ("gte_0_30", .30, float("inf")))


def margin_bucket(value: float | None) -> str | None:
    if value is None:
        return None
    return next((name for name, low, high in MARGIN_BUCKETS if low <= value < high), None)


def agreement_category(r1: str, r2: str, qwen: str | None, valid: bool) -> str:
    if not valid:
        return "QWEN_TECHNICAL_INVALID"
    if qwen == "NONE":
        return "QWEN_ABSTAINS"
    if r1 == r2 == qwen:
        return "ALL_AGREE"
    if r1 == r2:
        return "R1_R2_AGREE_QWEN_DIFFERS"
    if r1 == qwen:
        return "R1_QWEN_AGREE_R2_DIFFERS"
    if r2 == qwen:
        return "R2_QWEN_AGREE_R1_DIFFERS"
    return "ALL_DISAGREE"


def _accuracy(records: list[dict], key: str) -> float | None:
    return sum(item[key] == item["gold_target_id"] for item in records) / len(records) if records else None


def _rank_group(record: dict, threshold: float) -> str:
    rank = record["gold_rank"]
    if rank == 1:
        return "rank1_emitted" if record["r1_top1_score"] >= threshold else "rank1_threshold_abstention"
    if rank <= 5:
        return "gold_rank_2_5"
    if rank <= 10:
        return "gold_rank_6_10"
    return "gold_rank_gt_10"


def _summary(records: list[dict]) -> dict:
    valid = [item for item in records if item["candidate_valid"]]
    return {"n_sampled": len(records), "n_candidate_valid": len(valid), "technical_valid_rate": len(valid) / len(records) if records else None,
            "r1_accuracy_on_valid": _accuracy(valid, "r1_target"), "r2_accuracy_on_valid": _accuracy(valid, "r2_target"), "qwen_accuracy_on_valid": _accuracy(valid, "qwen_candidate_id"),
            "qwen_abstention_rate_on_valid": sum(item["qwen_candidate_id"] == "NONE" for item in valid) / len(valid) if valid else None,
            "nontrivial_proportion": sum(item["nontrivial"] for item in records) / len(records) if records else None,
            "gold_rank_distribution": dict(Counter(_rank_group(item, .82) for item in records))}


def validation_analysis(records: list[dict], threshold: float) -> dict:
    """Same-case margin, rank, agreement and incremental-value summaries."""
    enriched = [{**item, "margin_bucket": margin_bucket(item["r1_margin"]), "gold_rank_group": _rank_group(item, threshold), "agreement": agreement_category(item["r1_target"], item["r2_target"], item["qwen_candidate_id"], item["candidate_valid"])} for item in records]
    by_margin = {name: _summary([item for item in enriched if item["margin_bucket"] == name]) for name, _, _ in MARGIN_BUCKETS}
    rank_names = ("rank1_emitted", "rank1_threshold_abstention", "gold_rank_2_5", "gold_rank_6_10", "gold_rank_gt_10")
    by_rank = {name: _summary([item for item in enriched if item["gold_rank_group"] == name]) for name in rank_names}
    nontrivial = _summary([item for item in enriched if item["nontrivial"]])
    valid = [item for item in enriched if item["candidate_valid"]]
    increments = {}
    for name, baseline in (("r1", "r1_target"), ("r2", "r2_target")):
        increments[name] = {"baseline_wrong_qwen_correct": sum(item[baseline] != item["gold_target_id"] and item["qwen_candidate_id"] == item["gold_target_id"] for item in valid),
                            "baseline_correct_qwen_wrong": sum(item[baseline] == item["gold_target_id"] and item["qwen_candidate_id"] != item["gold_target_id"] for item in valid),
                            "baseline_abstain_qwen_correct": sum(item["r1_top1_score"] < threshold and item["qwen_candidate_id"] == item["gold_target_id"] for item in valid) if name == "r1" else None,
                            "baseline_correct_qwen_abstain": sum(item[baseline] == item["gold_target_id"] and item["qwen_candidate_id"] == "NONE" for item in valid),
                            "net_incremental_correct": sum(item[baseline] != item["gold_target_id"] and item["qwen_candidate_id"] == item["gold_target_id"] for item in valid) - sum(item[baseline] == item["gold_target_id"] and item["qwen_candidate_id"] != item["gold_target_id"] for item in valid)}
    categories = ("ALL_AGREE", "R1_R2_AGREE_QWEN_DIFFERS", "R1_QWEN_AGREE_R2_DIFFERS", "R2_QWEN_AGREE_R1_DIFFERS", "ALL_DISAGREE", "QWEN_ABSTAINS", "QWEN_TECHNICAL_INVALID")
    agreements = {name: {**_summary([item for item in enriched if item["agreement"] == name]), "mean_margin": sum(item["r1_margin"] for item in enriched if item["agreement"] == name) / sum(item["agreement"] == name for item in enriched) if any(item["agreement"] == name for item in enriched) else None, "median_margin": median([item["r1_margin"] for item in enriched if item["agreement"] == name]) if any(item["agreement"] == name for item in enriched) else None} for name in categories}
    return {"all_sampled": _summary(enriched), "margin_stratified": by_margin, "gold_rank_stratified": by_rank, "nontrivial": nontrivial, "incremental_value": increments, "agreement": agreements, "records": enriched}


def confidence_evidence_table(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], qwen_records: list[dict]) -> list[dict]:
    """Create a leakage-separated future-methodology table after inference."""
    qwen_by_source = {item["source_id"]: item for item in qwen_records}
    result = []
    for row in rows:
        qwen = qwen_by_source.get(row["source_iri"])
        if not qwen:
            continue
        # Candidate features only receive source and supplied candidates.
        top = candidate_features(row, source, target)[0]
        r2 = min(row["retrieved_candidates"][:len(qwen.get("candidate_ids", row["retrieved_candidates"]))], key=lambda item: (-item["r2_combined_score"], item["iri"]))
        observable = {"source_id": row["source_iri"], "r1_top1_candidate": row["selected_candidate_iri"], "r1_top1_score": row["selected_candidate_score"], "r1_top2_score": row["retrieved_candidates"][1]["score"] if len(row["retrieved_candidates"]) > 1 else None, "r1_margin": top["top1_top2_margin"], "r1_topk_spread": top["top1_topk_spread"], "r2_candidate": r2["iri"], "r2_score": r2["r2_combined_score"], "lexical_feature": top["lexical_score"], "context_feature": top["context_score"], "parent_feature": top["parent_similarity"], "child_feature": top["child_similarity"], "property_feature": top["property_similarity"], "r1_r2_agreement": row["selected_candidate_iri"] == r2["iri"], "qwen_valid": qwen["candidate_valid"], "qwen_candidate": qwen["qwen_candidate_id"], "qwen_relation": qwen["qwen_relation"], "qwen_abstain": qwen["qwen_candidate_id"] == "NONE", "qwen_attempt_count": qwen["retry_count"] + 1, "r1_qwen_agreement": row["selected_candidate_iri"] == qwen["qwen_candidate_id"], "r2_qwen_agreement": r2["iri"] == qwen["qwen_candidate_id"], "sample_stratum": qwen["sample_stratum"], "margin_bucket": margin_bucket(top["top1_top2_margin"])}
        # Evaluation-only reference columns are attached after observable table creation.
        reference = {"gold_candidate": row["gold_target_iri"], "gold_rank": row["gold_rank"], "nontrivial": row["nontrivial"], "r1_correct": row["selected_candidate_iri"] == row["gold_target_iri"], "r2_correct": r2["iri"] == row["gold_target_iri"], "qwen_correct": qwen["qwen_candidate_id"] == row["gold_target_iri"]}
        result.append({"observable_at_inference": observable, "reference_only": reference})
    return result
