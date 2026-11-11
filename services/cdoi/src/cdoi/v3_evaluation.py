"""V3 evaluation-only comparison and calibration scaffolding."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

from .semantic_decision import SelectionResult, SelectionStatus


@dataclass(frozen=True)
class CalibrationProtocol:
    calibration_dataset: str
    calibration_split: str
    feature_definition: str
    method: str
    calibration_version: str
    target_risk_metric: str
    independence_status: str = "NOT_FIT"


def risk_coverage(records: Iterable[Mapping[str, object]], thresholds: Iterable[float]) -> list[dict[str, float | int | None]]:
    """Evaluation only: records must already contain score and reference correctness."""
    rows = list(records)
    result = []
    for threshold in thresholds:
        committed = [row for row in rows if row.get("score") is not None and float(row["score"]) >= threshold]
        correct = sum(bool(row.get("reference_correct")) for row in committed)
        coverage = len(committed) / len(rows) if rows else 0.0
        precision = correct / len(committed) if committed else None
        risk = 1 - precision if precision is not None else None
        result.append({"threshold": float(threshold), "n": len(rows), "committed": len(committed), "coverage": coverage, "precision": precision, "risk": risk, "accepted_error_rate": (len(committed) - correct) / len(committed) if committed else None, "abstention": 1 - coverage})
    return result


def selector_comparison(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Compare selector outputs on identical candidate-set hashes after inference."""
    rows = list(rows); by_source: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        by_source.setdefault(str(row["source_id"]), []).append(row)
    selector_names = sorted({str(row["selector_id"]) for row in rows})
    metrics = {}
    for selector in selector_names:
        group = [row for row in rows if row["selector_id"] == selector]
        selected = [row for row in group if row["status"] == SelectionStatus.SELECTED.value]
        technical = [row for row in group if row["status"] == SelectionStatus.TECHNICAL_UNAVAILABLE.value]
        abstain = [row for row in group if row["status"] == SelectionStatus.SEMANTIC_ABSTAIN.value]
        metrics[selector] = {"n": len(group), "selected": len(selected), "semantic_abstention": len(abstain), "technical_unavailable": len(technical), "same_case_accuracy": sum(row.get("reference_correct") is True for row in group) / len(group) if group else None, "mean_latency_ms": sum(float(row.get("latency_ms") or 0) for row in group) / len(group) if group else None}
    agreements = Counter()
    for group in by_source.values():
        hashes = {row.get("candidate_set_hash") for row in group if row.get("candidate_set_hash") is not None}
        statuses = {str(row["selector_id"]): str(row["status"]) for row in group}
        targets = {str(row["selector_id"]): row.get("candidate_id") for row in group if row["status"] == SelectionStatus.SELECTED.value}
        if len(hashes) > 1:
            category = "INVALID_CANDIDATE_SET_COMPARISON"
        elif any(status == SelectionStatus.TECHNICAL_UNAVAILABLE.value for status in statuses.values()):
            category = "TECHNICAL_UNAVAILABLE"
        elif any(status == SelectionStatus.SEMANTIC_ABSTAIN.value for status in statuses.values()):
            category = "SEMANTIC_ABSTAIN"
        elif len(targets) == len(group) and len(set(targets.values())) == 1:
            category = "ALL_AGREE"
        elif {"R1", "R2"} <= set(targets) and targets["R1"] == targets["R2"]:
            category = "DETERMINISTIC_AGREE_SEMANTIC_DIFFERS"
        elif {"Dense", "Qwen"} <= set(targets) and targets["Dense"] == targets["Qwen"]:
            category = "DENSE_QWEN_AGREE"
        else:
            category = "ALL_DISAGREE"
        agreements[category] += 1
    return {"selectors": metrics, "agreement": dict(agreements), "reference_only_note": "reference_correct is evaluation-only and must be joined after selector inference"}
