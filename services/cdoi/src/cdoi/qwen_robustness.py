"""Representation-perturbation diagnostics for frozen shared-Top-K Qwen runs.

This module is intentionally experiment-only.  It varies presentation order,
handles, profile fields, or neutral instruction wording while preserving the
candidate set.  References are consulted only after model outputs are recorded.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from statistics import mean, median
from time import perf_counter
from typing import Callable

from .oaei_full_corpus import ConceptProfile
from .qwen_reliability import classify_response


PROFILE_MODES = {
    "Q0_LABEL": ("label",), "Q1_LABEL_ALIASES": ("label", "aliases"),
    "Q2_PARENT": ("label", "aliases", "parents"),
    "Q3_PARENT_CHILD": ("label", "aliases", "parents", "children"),
    "Q4_FULL": ("label", "aliases", "parents", "children", "properties"),
}
PROMPT_VARIANTS = {
    "P0_FROZEN": ('Return only JSON: {"candidate_id":"a supplied id or NONE","relation":"EQUIVALENT or NONE"}.', "Choose only a supplied candidate when evidence supports Anatomy equivalence; otherwise choose NONE. Do not explain."),
    "P1_PARAPHRASE": ('Respond only with {"candidate_id":"a supplied id or NONE","relation":"EQUIVALENT or NONE"}.', "Select a listed equivalent Anatomy candidate only when supported; otherwise return NONE. No explanation."),
    "P2_INSTRUCTION_ORDER": ("Use NONE unless one listed candidate is equivalent to the source. Do not explain.", 'Output JSON only: {"candidate_id":"a supplied id or NONE","relation":"EQUIVALENT or NONE"}.'),
}


def _fields(profile: ConceptProfile, fields: tuple[str, ...], identifier: str) -> dict:
    result = {"id": identifier}
    if "label" in fields: result["label"] = profile.label
    if "aliases" in fields and profile.aliases: result["aliases"] = list(profile.aliases)
    if "parents" in fields and profile.parents: result["parents"] = list(profile.parents)
    if "children" in fields and profile.children: result["children"] = list(profile.children)
    properties = profile.object_properties + profile.data_properties
    if "properties" in fields and properties: result["properties"] = list(properties)
    return result


def opaque_mapping(candidate_ids: list[str]) -> dict[str, str]:
    """Deterministic reversible handles assigned from original candidate order."""
    return {candidate_id: f"C{index:02d}" for index, candidate_id in enumerate(candidate_ids, 1)}


def permutation_indices(size: int, kind: str, seed: int, source_id: str) -> list[int]:
    indices = list(range(size))
    if kind == "ORIGINAL": return indices
    if kind == "REVERSE": return list(reversed(indices))
    digest = hashlib.sha256(f"{seed}:{source_id}:{kind}".encode()).digest()
    random.Random(int.from_bytes(digest[:8], "big")).shuffle(indices)
    return indices


def robustness_prompt(row: dict, source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], top_k: int, *, order_kind: str = "ORIGINAL", order_seed: int = 266, id_mode: str = "ORIGINAL_ID", profile_mode: str = "Q4_FULL", prompt_variant: str = "P0_FROZEN") -> tuple[str, dict]:
    """Build a neutral prompt; no reference field is read by this function."""
    fields = PROFILE_MODES[profile_mode]
    candidates = row["retrieved_candidates"][:top_k]
    ids = [item["iri"] for item in candidates]; mapping = opaque_mapping(ids)
    indices = permutation_indices(len(candidates), order_kind, order_seed, row["source_iri"])
    display = []
    for index in indices:
        item = candidates[index]; original = item["iri"]
        display_id = mapping[original] if id_mode == "OPAQUE_ID" else original
        display.append(_fields(target[original], fields, display_id))
    # Opaque-ID control changes candidate handles only; preserve the source
    # profile identifier so it does not introduce a second presentation change.
    source_id = source[row["source_iri"]].iri
    payload = {"source": _fields(source[row["source_iri"]], fields, source_id), "candidates": display}
    lines = (*PROMPT_VARIANTS[prompt_variant], json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    profile_counts = {name: sum(bool(getattr(source[row["source_iri"]], name if name != "properties" else "object_properties")) for _ in [0]) + sum(bool(getattr(target[item["iri"]], name if name != "properties" else "object_properties")) for item in candidates) for name in ("aliases", "parents", "children", "properties")}
    return "\n".join(lines), {"original_candidate_ids": ids, "display_candidate_ids": [item["id"] for item in display], "opaque_to_original": {value: key for key, value in mapping.items()} if id_mode == "OPAQUE_ID" else {}, "permutation_indices": indices, "profile_field_counts": profile_counts}


def select_cases(validation_records: list[dict], rows_by_source: dict[str, dict], sample_size: int, seed: int) -> list[dict]:
    """Pre-inference selection from frozen V2.6.5 validity/strata, never correctness."""
    groups: dict[str, list[str]] = {}
    for record in validation_records:
        if record["candidate_valid"]:
            groups.setdefault(record["sample_stratum"], []).append(record["source_id"])
    rng = random.Random(seed)
    for values in groups.values(): rng.shuffle(values)
    selected = []
    while len(selected) < sample_size and any(groups.values()):
        for name in sorted(groups):
            if groups[name] and len(selected) < sample_size:
                selected.append({**rows_by_source[groups[name].pop(0)], "robustness_stratum": name})
    return selected


def evaluate_conditions(rows: list[dict], source: dict[str, ConceptProfile], target: dict[str, ConceptProfile], conditions: list[dict], top_k: int, max_attempts: int, requester: Callable[..., object], model: str, headers: dict[str, str], response_budget: int) -> dict:
    records = []
    for row in rows:
        for condition in conditions:
            presentation = {key: condition[key] for key in ("order_kind", "order_seed", "id_mode", "profile_mode", "prompt_variant") if key in condition}
            prompt, metadata = robustness_prompt(row, source, target, top_k, **presentation)
            budget = int(condition.get("response_budget", response_budget)); display_ids = set(metadata["display_candidate_ids"]); attempts, lifecycle, response = 0, None, None; started = perf_counter()
            for attempts in range(1, max_attempts + 1):
                try:
                    response = requester("POST", headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": budget}, timeout=30)
                    lifecycle = classify_response(response, display_ids, budget, round((perf_counter() - started) * 1000, 3))
                except Exception as error:
                    lifecycle = {"final_status": "TRANSPORT_ERROR", "http_status": None, "latency_ms": round((perf_counter() - started) * 1000, 3), "error_type": type(error).__name__}
                if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"} or attempts == max_attempts: break
            display_target = relation = None
            if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}:
                content = response.json()["choices"][0]["message"].get("content", "")
                parsed = json.loads(content[content.find("{"):content.rfind("}") + 1]); display_target, relation = parsed["candidate_id"], parsed["relation"]
            original_target = metadata["opaque_to_original"].get(display_target, display_target) if display_target not in {None, "NONE"} else display_target
            position = metadata["display_candidate_ids"].index(display_target) + 1 if display_target in metadata["display_candidate_ids"] else None
            # Evaluation labels are joined only after the condition response.
            records.append({"source_id": row["source_iri"], "robustness_stratum": row.get("robustness_stratum", "prior_technical_invalid"), "condition_id": condition["condition_id"], "condition": condition, "candidate_set_hash": hashlib.sha256("|".join(sorted(metadata["original_candidate_ids"])).encode()).hexdigest(), "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(), "prompt_char_length": len(prompt), "candidate_count": len(metadata["original_candidate_ids"]), "profile_field_counts": metadata["profile_field_counts"], "permutation_indices": metadata["permutation_indices"], "retry_count": attempts - 1, "display_selected_id": display_target, "selected_candidate_id": original_target, "selected_display_position": position, "qwen_relation": relation, "candidate_valid": lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}, "gold_target_id": row["gold_target_iri"], "gold_rank": row["gold_rank"], "nontrivial": row["nontrivial"], "r1_margin": float(row["retrieved_candidates"][0]["score"]) - float(row["retrieved_candidates"][1]["score"]), **lifecycle})
    return {"records": records, "conditions": conditions}


def robustness_summary(records: list[dict]) -> dict:
    by_condition = {}
    for condition in sorted({item["condition_id"] for item in records}):
        group = [item for item in records if item["condition_id"] == condition]; valid = [item for item in group if item["candidate_valid"]]
        by_condition[condition] = {"n": len(group), "valid": len(valid), "technical_valid_rate": len(valid) / len(group) if group else None, "accuracy_on_valid": sum(item["selected_candidate_id"] == item["gold_target_id"] for item in valid) / len(valid) if valid else None, "nontrivial_accuracy": sum(item["selected_candidate_id"] == item["gold_target_id"] and item["nontrivial"] for item in valid) / sum(item["nontrivial"] for item in valid) if any(item["nontrivial"] for item in valid) else None, "abstention_rate": sum(item["selected_candidate_id"] == "NONE" for item in valid) / len(valid) if valid else None, "mean_latency_ms": mean(item["latency_ms"] for item in group) if group else None, "failure_taxonomy": dict(Counter(item["final_status"] for item in group))}
    per_case = []
    for source_id in sorted({item["source_id"] for item in records}):
        group = [item for item in records if item["source_id"] == source_id]; valid = [item for item in group if item["candidate_valid"]]; selected = [item["selected_candidate_id"] for item in valid]
        modal = max(sorted(set(selected)), key=selected.count) if selected else None
        per_case.append({"source_id": source_id, "conditions": len(group), "valid_outputs": len(valid), "unique_selected_candidates": len(set(selected)), "selection_invariant": len(set(selected)) <= 1 and bool(selected), "relation_invariant": len({item["qwen_relation"] for item in valid}) <= 1 and bool(valid), "modal_target": modal, "modal_target_correct": modal == group[0]["gold_target_id"] if modal else None, "representation_status": "REPRESENTATION_SENSITIVE" if len(set(selected)) > 1 else "INVARIANT_OR_UNAVAILABLE"})
    order_records = [item for item in records if item["condition"].get("family") == "order" and item["candidate_valid"] and item["selected_display_position"] is not None]
    return {"by_condition": by_condition, "per_case": per_case, "selection_invariance_rate": sum(item["selection_invariant"] for item in per_case) / len(per_case) if per_case else None, "relation_invariance_rate": sum(item["relation_invariant"] for item in per_case) / len(per_case) if per_case else None, "modal_accuracy": sum(item["modal_target_correct"] for item in per_case if item["modal_target_correct"] is not None) / sum(item["modal_target_correct"] is not None for item in per_case) if per_case else None, "representation_sensitive_cases": sum(item["representation_status"] == "REPRESENTATION_SENSITIVE" for item in per_case), "position_selection_frequency": dict(Counter(item["selected_display_position"] for item in order_records))}
