from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Protocol


class BenchmarkAdapter(Protocol):
    name: str
    def load_split(self, split: str) -> list[dict]: ...
    def dataset_metadata(self) -> dict[str, str]: ...
    def evaluate(self, predictions: dict[str, str], split: str) -> dict[str, float]: ...


class CdoiBenchAdapter:
    """Project-owned, synthetic benchmark for CDOI hypotheses; never a production input."""
    name = "cdoi_bench"

    def __init__(self, root: Path):
        self.root = root

    def load_split(self, split: str) -> list[dict]:
        return json.loads((self.root / f"{split}.json").read_text(encoding="utf-8"))

    def dataset_metadata(self) -> dict[str, str]:
        digest = hashlib.sha256()
        for path in sorted(self.root.glob("*.json")):
            digest.update(path.read_bytes())
        return {"dataset": self.name, "version": "v1-synthetic", "sha256": digest.hexdigest()}

    def evaluate(self, predictions: dict[str, str], split: str) -> dict[str, float]:
        return evaluate_alignment_cases(self.load_split(split), predictions)


def evaluate_alignment_cases(cases: list[dict], predictions: dict[str, str], seed: int = 42) -> dict[str, float | dict[str, int]]:
    """Evaluate relation decisions with explicit selective-prediction diagnostics."""
    total = len(cases)
    exact = sum(predictions.get(case["case_id"]) == case["expected_relation"] for case in cases)
    must_not_merge = [case for case in cases if case.get("must_not_equivalent")]
    false_merges = sum(predictions.get(case["case_id"]) == "EQUIVALENT" for case in must_not_merge)
    matched = [case for case in cases if case["expected_relation"] == "EQUIVALENT"]
    eq_tp = sum(predictions.get(case["case_id"]) == "EQUIVALENT" for case in matched)
    predicted_equiv = sum(value == "EQUIVALENT" for value in predictions.values())
    precision = eq_tp / predicted_equiv if predicted_equiv else 1.0
    recall = eq_tp / len(matched) if matched else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    by_kind = lambda kind: [case for case in cases if case["kind"] == kind]
    score = lambda group: sum(predictions.get(case["case_id"]) == case["expected_relation"] for case in group) / len(group) if group else 1.0
    bridge = by_kind("bridge")
    automatic = [case for case in cases if predictions.get(case["case_id"]) not in {"UNRESOLVED", "REVIEW", None}]
    failures = _failure_taxonomy(cases, predictions)
    result: dict[str, float | dict[str, int]] = {
        "alignment_accuracy": exact / total if total else 1.0,
        "alignment_precision": precision,
        "alignment_recall": recall,
        "alignment_f1": f1,
        "equivalence_precision": precision,
        "false_merge_count": float(false_merges),
        "false_merge_rate": false_merges / len(must_not_merge) if must_not_merge else 0.0,
        "subclass_placement_accuracy": score([case for case in cases if case["expected_relation"] == "SUBCLASS_OF"]),
        "object_property_alignment_accuracy": score(by_kind("object_property")),
        "data_property_alignment_accuracy": score(by_kind("data_property")),
        "property_alignment_f1": _property_f1(cases, predictions),
        "new_concept_precision": score([case for case in cases if case["expected_relation"] == "NEW_CONCEPT"]),
        "unresolved_accuracy": score([case for case in cases if case["expected_relation"] == "UNRESOLVED"]),
        "unresolved_rate": sum(value == "UNRESOLVED" for value in predictions.values()) / total if total else 0.0,
        "bridge_precision": score(bridge),
        "bridge_recall": score(bridge),
        "promotion_precision": score(by_kind("promotion")),
        "auto_decision_coverage": len(automatic) / total if total else 1.0,
        "selective_accuracy": sum(predictions.get(case["case_id"]) == case["expected_relation"] for case in automatic) / len(automatic) if automatic else 1.0,
        "human_review_rate": sum(predictions.get(case["case_id"]) in {"UNRESOLVED", "REVIEW"} for case in cases) / total if total else 0.0,
        "sample_counts": {"total": total, "positive_equivalence": len(matched), "negative_no_merge": len(must_not_merge), **{f"kind_{kind}": len(by_kind(kind)) for kind in sorted({case["kind"] for case in cases})}},
        "failure_taxonomy": failures,
    }
    result.update(bootstrap_intervals(cases, predictions, seed))
    if any(case.get("gold_positive") for case in cases):
        # Reference-positive pairs alone cannot support precision or false-merge claims.
        result.update({"evaluation_protocol": "reference_positive_pair_abstention", "positive_reference_recall": recall, "alignment_precision": None, "alignment_f1": None, "equivalence_precision": None, "false_merge_count": None, "false_merge_rate": None})
    return result


def _property_f1(cases: list[dict], predictions: dict[str, str]) -> float:
    properties = [case for case in cases if case["kind"] in {"object_property", "data_property"}]
    if not properties:
        return 1.0
    correct = sum(predictions.get(case["case_id"]) == case["expected_relation"] for case in properties)
    return correct / len(properties)


def _failure_taxonomy(cases: list[dict], predictions: dict[str, str]) -> dict[str, int]:
    categories = {key: 0 for key in ("retrieval_miss", "concept_profile_error", "class_relation_error", "property_relation_error", "unsafe_equivalence", "false_unresolved", "new_concept_error", "bridge_error", "promotion_error", "entity_resolution_error", "late_evidence_failure", "order_instability", "provenance_failure", "downstream_path_error")}
    for case in cases:
        predicted, expected = predictions.get(case["case_id"]), case["expected_relation"]
        if predicted == expected:
            continue
        if case.get("gold_in_top_k") is False:
            categories["retrieval_miss"] += 1
        elif predicted == "EQUIVALENT" and case.get("must_not_equivalent"):
            categories["unsafe_equivalence"] += 1
        elif predicted == "UNRESOLVED":
            categories["false_unresolved"] += 1
        elif case["kind"] in {"object_property", "data_property"}:
            categories["property_relation_error"] += 1
        elif case["kind"] == "bridge":
            categories["bridge_error"] += 1
        elif case["kind"] == "promotion":
            categories["promotion_error"] += 1
        elif expected == "NEW_CONCEPT":
            categories["new_concept_error"] += 1
        else:
            categories["class_relation_error"] += 1
    return categories


def bootstrap_intervals(cases: list[dict], predictions: dict[str, str], seed: int = 42, samples: int = 200) -> dict[str, float]:
    """Deterministic percentile bootstrap for descriptive uncertainty intervals."""
    if not cases:
        return {"accuracy_bootstrap_low": 1.0, "accuracy_bootstrap_high": 1.0, "false_merge_bootstrap_low": 0.0, "false_merge_bootstrap_high": 0.0, "bootstrap_samples": float(samples)}
    rng = random.Random(seed)
    accuracies: list[float] = []
    false_merge_rates: list[float] = []
    for _ in range(samples):
        sample = [rng.choice(cases) for _ in cases]
        accuracies.append(sum(predictions.get(case["case_id"]) == case["expected_relation"] for case in sample) / len(sample))
        negatives = [case for case in sample if case.get("must_not_equivalent")]
        false_merge_rates.append(sum(predictions.get(case["case_id"]) == "EQUIVALENT" for case in negatives) / len(negatives) if negatives else 0.0)
    accuracies.sort(); false_merge_rates.sort()
    low, high = max(0, int(samples * 0.025) - 1), min(samples - 1, int(samples * 0.975))
    return {"accuracy_bootstrap_low": accuracies[low], "accuracy_bootstrap_high": accuracies[high], "false_merge_bootstrap_low": false_merge_rates[low], "false_merge_bootstrap_high": false_merge_rates[high], "bootstrap_samples": float(samples)}


class ExternalBenchmarkSetupAdapter:
    """Placeholder metadata adapter for licensed/downloaded OET, OAEI, and LLMs4OL corpora."""
    def __init__(self, name: str, setup_document: Path):
        self.name = name
        self.setup_document = setup_document

    def load_split(self, split: str) -> list[dict]:
        raise FileNotFoundError(f"{self.name} data is external. Follow {self.setup_document} before loading '{split}'.")

    def dataset_metadata(self) -> dict[str, str]:
        return {"dataset": self.name, "status": "external_setup_required"}

    def evaluate(self, predictions: dict[str, str], split: str) -> dict[str, float]:
        self.load_split(split)
        return {}
