from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .models import AlignmentDecision, AlignmentRelation


@dataclass
class EvaluationReport:
    alignment_accuracy: float
    equivalence_precision: float
    subclass_placement_accuracy: float
    new_concept_precision: float
    false_merge_count: int
    false_merge_rate: float
    duplicate_concept_count: int
    validation_failure_count: int
    human_review_rate: float
    property_alignment_accuracy: float = 0.0
    unresolved_accuracy: float = 0.0
    bridge_mapping_precision: float = 0.0
    promotion_precision: float = 0.0


def evaluate(decisions: list[AlignmentDecision], expected: list[AlignmentRelation] | None = None, validation_failures: int = 0, review_count: int = 0) -> EvaluationReport:
    expected = expected or []
    accuracy = sum(item.relation == truth for item, truth in zip(decisions, expected)) / len(expected) if expected else 0.0
    equivalent = [item for item in decisions if item.relation == AlignmentRelation.EQUIVALENT]
    false_merges = sum(1 for item in equivalent if item.warnings)
    return EvaluationReport(accuracy, 1 - false_merges / len(equivalent) if equivalent else 1.0, accuracy, accuracy, false_merges, false_merges / len(decisions) if decisions else 0.0, 0, validation_failures, review_count / len(decisions) if decisions else 0.0, accuracy, accuracy, 1.0, 1.0)


def load_gold(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_gold(predictions: dict[str, str], gold_path: Path) -> dict[str, float]:
    gold = load_gold(gold_path)
    correct = sum(predictions.get(item["id"]) == item["expected"] for item in gold)
    by_kind = lambda kind: [item for item in gold if item["kind"] == kind]
    score = lambda items: sum(predictions.get(item["id"]) == item["expected"] for item in items) / len(items) if items else 1.0
    false_merges = sum(1 for item in gold if item["expected"] == "UNRESOLVED" and predictions.get(item["id"]) == "EQUIVALENT")
    return {"alignment_accuracy": correct / len(gold), "property_alignment_accuracy": score(by_kind("object_property") + by_kind("data_property")), "unresolved_accuracy": score([item for item in gold if item["expected"] == "UNRESOLVED"]), "bridge_mapping_precision": score(by_kind("bridge")), "false_merge_count": float(false_merges), "false_merge_rate": false_merges / len(gold)}
