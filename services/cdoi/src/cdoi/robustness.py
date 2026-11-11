"""Deterministic V2.5 stress transformations for benchmark inputs.

The transformations operate on copies and retain an ``origin`` record.  They are
experimental perturbations, not a claim about an enterprise noise distribution.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import random
from typing import Iterable


EVIDENCE_CONDITIONS = ("Full", "NoDefinition", "NoRelations", "NoNeighborhood", "NoDomain", "LabelOnly")


def degrade_evidence(cases: Iterable[dict], condition: str) -> list[dict]:
    if condition not in EVIDENCE_CONDITIONS:
        raise ValueError(f"Unknown evidence condition: {condition}")
    output: list[dict] = []
    for original in cases:
        item = deepcopy(original)
        item["case_id"] = f"{original['case_id']}@{condition}"
        item["origin"] = {"case_id": original["case_id"], "transformation": "evidence_degradation", "condition": condition}
        available = {"definition": True, "relations": True, "neighborhood": True, "domain": True, "property": True}
        if condition == "NoDefinition":
            available["definition"] = False
        elif condition == "NoRelations":
            available["relations"] = False
            available["property"] = False
        elif condition == "NoNeighborhood":
            available["neighborhood"] = False
        elif condition == "NoDomain":
            available["domain"] = False
        elif condition == "LabelOnly":
            available = {key: False for key in available}
        item["evidence_available"] = available
        output.append(item)
    return output


def inject_noise(cases: Iterable[dict], level: int, seed: int = 42) -> list[dict]:
    """Apply reproducible label, relation, type, and context perturbations.

    A case-local seed keeps a case stable when benchmark order changes.
    """
    if not 0 <= level <= 100:
        raise ValueError("Noise level must be between 0 and 100.")
    output: list[dict] = []
    for original in cases:
        item = deepcopy(original)
        digest = int(hashlib.sha256(original["case_id"].encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed + digest)
        item["case_id"] = f"{original['case_id']}@noise{level}"
        item["origin"] = {"case_id": original["case_id"], "transformation": "noise", "level": level, "seed": seed}
        applied: list[str] = []
        signals = item.setdefault("signals", {})
        probability = level / 100
        # Each signal represents a distinct evidence channel, making effects inspectable.
        for name, operator in (("lexical", "label"), ("embedding", "label"), ("structural", "relation"), ("domain", "context")):
            if rng.random() < probability:
                signals[name] = round(float(signals.get(name, 0.0)) * (0.35 + 0.35 * rng.random()), 3)
                applied.append(operator)
        if rng.random() < probability:
            item["candidate"] = _noisy_label(str(item.get("candidate", "")), rng)
            applied.append("type_hint")
        item["noise_operators"] = sorted(set(applied))
        output.append(item)
    return output


def _noisy_label(label: str, rng: random.Random) -> str:
    if len(label) < 4:
        return label
    if rng.random() < 0.5:
        return label[:-1]  # deterministic partial label / typo surrogate
    return label.replace("Service", "Svc").replace("Account", "Acct")


def late_evidence_metrics(sequences: list[dict], strategy: str) -> dict[str, float]:
    """Evaluate decision traces while retaining every intermediate decision."""
    final_correct = premature = resolved = regression = reviewed = trace_complete = 0
    total = len(sequences)
    for sequence in sequences:
        steps = sequence["steps"]
        decisions = [step["decisions"][strategy] for step in steps]
        expected = [step["expected"] for step in steps]
        final_correct += decisions[-1] == expected[-1]
        premature += any(decision == "EQUIVALENT" and expected[index] != "EQUIVALENT" for index, decision in enumerate(decisions))
        resolved += decisions[-1] != "UNRESOLVED" and decisions[-1] == expected[-1]
        regression += any(decisions[index] == expected[index] and decisions[index + 1] != expected[index + 1] for index in range(len(decisions) - 1))
        reviewed += sum(decision == "REVIEW" for decision in decisions)
        trace_complete += all("audit" in step for step in steps)
    return {
        "correction_accuracy": final_correct / total if total else 1.0,
        "unsafe_premature_commitment_rate": premature / total if total else 0.0,
        "successful_resolution_rate": resolved / total if total else 1.0,
        "regression_rate": regression / total if total else 0.0,
        "review_rate": reviewed / sum(len(item["steps"]) for item in sequences) if sequences else 0.0,
        "version_trace_completeness": trace_complete / total if total else 1.0,
    }


def conflict_metrics(cases: list[dict]) -> dict[str, float]:
    """Measure provenance-preserving conflict routing and optional authority use."""
    detected = routed = authority_correct = 0
    for case in cases:
        types = {item["type"] for item in case["sources"]}
        conflict = len(types) > 1
        detected += conflict
        routed += conflict and case["without_authority"] == "REVIEW"
        authoritative = next((item for item in case["sources"] if item.get("authoritative")), None)
        authority_correct += bool(authoritative and case.get("with_authority") == authoritative["type"])
    total = len(cases)
    return {"n_total": float(total), "conflict_detection_rate": detected / total if total else 1.0, "review_routing_rate": routed / total if total else 1.0, "authoritative_resolution_accuracy": authority_correct / total if total else 1.0, "provenance_preserved_rate": sum(all("source" in item for item in case["sources"]) for case in cases) / total if total else 1.0}
