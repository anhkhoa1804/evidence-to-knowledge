from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationResult:
    equivalence_threshold: float
    unresolved_threshold: float
    dev_false_merge_rate: float
    dev_accuracy: float


def calibrate_thresholds(dev_cases: list[dict], scorer) -> CalibrationResult:
    """Choose thresholds on development data, prioritising zero/low false merges."""
    candidates: list[CalibrationResult] = []
    for equivalent_threshold in (0.55, 0.65, 0.75, 0.85, 0.95):
        for unresolved_threshold in (0.20, 0.35, 0.50):
            predictions = {case["case_id"]: scorer(case, equivalent_threshold, unresolved_threshold) for case in dev_cases}
            must_not_merge = [case for case in dev_cases if case.get("must_not_equivalent")]
            false_merges = sum(predictions[case["case_id"]] == "EQUIVALENT" for case in must_not_merge)
            accuracy = sum(predictions[case["case_id"]] == case["expected_relation"] for case in dev_cases) / len(dev_cases)
            candidates.append(CalibrationResult(equivalent_threshold, unresolved_threshold, false_merges / len(must_not_merge) if must_not_merge else 0.0, accuracy))
    return sorted(candidates, key=lambda item: (item.dev_false_merge_rate, -item.dev_accuracy, item.equivalence_threshold))[0]
