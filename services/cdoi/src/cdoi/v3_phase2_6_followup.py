"""Read-only Phase-2.6 follow-up diagnostics and dense-runtime utilities.

This module consumes versioned experiment artifacts after selector inference.  It
does not alter ``_profiles``, frozen CandidateSets, a semantic policy, or any
review/commit path.
"""

from __future__ import annotations

import math
import platform
import re
import sys
import hashlib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from collections import Counter
from dataclasses import asdict
from time import perf_counter
from typing import Any, Mapping, Sequence

from .oaei_full_corpus import _tokens, normalize
from .semantic_decision import (AmbiguityEvidence, CandidateSet, DenseSemanticSelector,
                                EvidenceAssembler, SelectionStatus,
                                SourceProfileReference)
from .v3_phase2_5 import diagnostic_enriched_score
from .v3_phase2_6 import SentenceTransformerBackend, dense_structured_text


FOLLOWUP_SCHEMA_VERSION = "v3_phase2_6_followup_v1"
TAXONOMY_V2_SCHEMA_VERSION = "v3_phase2_6_residual_taxonomy_v2"
FROZEN_MARGIN_BINS = ("<0.02", "0.02-0.05", "0.05-0.10", "0.10-0.20", ">=0.20")
RESIDUAL_CATEGORIES = (
    "ALIAS_COLLISION", "GRANULARITY_CONFUSION", "PARENT_CHILD_CONFUSION",
    "PART_WHOLE_CONFUSION", "GENERIC_SPECIFIC_CONFUSION",
    "LATERALITY_OR_REGION_SPECIFICITY", "COMPOUND_CONCEPT_DECOMPOSITION",
    "LEXICAL_NEAR_DUPLICATE", "MISSING_SOURCE_SYNONYM", "MISSING_TARGET_SYNONYM",
    "STRUCTURAL_CONTEXT_NEEDED", "POSSIBLE_REFERENCE_AMBIGUITY",
    "OTHER_OBSERVED_PATTERN", "INSUFFICIENT_OBSERVABLE_EVIDENCE", "UNCLASSIFIED",
)


def margin_bucket(value: float) -> str:
    if value < .02:
        return "<0.02"
    if value < .05:
        return "0.02-0.05"
    if value < .10:
        return "0.05-0.10"
    if value < .20:
        return "0.10-0.20"
    return ">=0.20"


def rank_bucket(value: int) -> str:
    if value == 1:
        return "rank1"
    if value <= 5:
        return "rank2-5"
    if value <= 10:
        return "rank6-10"
    if value <= 20:
        return "rank11-20"
    return "rank21+"


def _surface(value: str) -> str:
    return normalize(value)


def _terms(profile: Any) -> tuple[tuple[str, str], ...]:
    return (("label", profile.label), *(('alias', value) for value in profile.aliases))


def _shared_surface(left: Any, right: Any) -> list[str]:
    return sorted({_surface(value) for _, value in _terms(left)} & {_surface(value) for _, value in _terms(right)} - {""})


def _structure(profile: Any) -> set[str]:
    values = (
        *getattr(profile, "parents", ()), *getattr(profile, "children", ()),
        *getattr(profile, "object_properties", ()), *getattr(profile, "data_properties", ()),
        *getattr(profile, "properties", ()),
    )
    # rdflib assigns process-local identifiers to unlabelled blank nodes.  They
    # are not source semantic text and must not make a diagnostic artifact vary
    # across parses.  Explicit labels remain available through normal profiles.
    volatile = re.compile(r"^(?:_:)?(?:genid|n)[0-9a-f]{12,}$", re.IGNORECASE)
    return {_surface(value) for value in values if _surface(value) and not volatile.fullmatch(str(value).strip())}


def structural_context_diagnostic(source: Any, gold: Any, wrong: Any) -> tuple[str, list[str]]:
    """Report observable context availability/difference, without predicting a fix."""
    source_context, gold_context, wrong_context = _structure(source), _structure(gold), _structure(wrong)
    if not (source_context or gold_context or wrong_context):
        return "STRUCTURAL_DATA_UNAVAILABLE", ["No parent, child, or property text is available in this profile triplet."]
    if gold_context != wrong_context:
        changed = sorted((gold_context ^ wrong_context))[:6]
        return "STRUCTURAL_SIGNAL_PRESENT", ["Gold and selected-wrong profiles expose different structural text: " + "; ".join(changed)]
    return "STRUCTURAL_SIGNAL_NOT_OBSERVED", ["Available gold and selected-wrong structural text is identical after normalization."]


def classify_observable_patterns(source: Any, gold: Any, wrong: Any) -> tuple[list[str], list[str], str]:
    """Conservative multi-label taxonomy based only on profile-observable text."""
    categories: list[str] = []
    evidence: list[str] = []
    source_label, gold_label, wrong_label = _surface(source.label), _surface(gold.label), _surface(wrong.label)
    source_aliases = {_surface(value) for value in source.aliases} - {""}
    gold_aliases = {_surface(value) for value in gold.aliases} - {""}
    wrong_aliases = {_surface(value) for value in wrong.aliases} - {""}
    alias_overlap = sorted((({source_label} | source_aliases) & wrong_aliases) - {""})
    if alias_overlap:
        categories.append("ALIAS_COLLISION")
        evidence.append("Source label/alias exactly matches selected-wrong alias: " + "; ".join(alias_overlap))
    if not source_aliases:
        categories.append("MISSING_SOURCE_SYNONYM")
        evidence.append("No resolved P1 source aliases are present; raw-source absence is not inferred.")
    if not wrong_aliases and not gold_aliases:
        categories.append("MISSING_TARGET_SYNONYM")
        evidence.append("Neither gold nor selected-wrong candidate has a resolved P1 alias; raw-source absence is not inferred.")
    gold_tokens, wrong_tokens = _tokens(gold.label), _tokens(wrong.label)
    if gold_tokens and wrong_tokens and (gold_tokens < wrong_tokens or wrong_tokens < gold_tokens):
        categories.append("GENERIC_SPECIFIC_CONFUSION")
        evidence.append("One target label token set is a proper subset of the other.")
    specificity = {"left", "right", "anterior", "posterior", "superior", "inferior", "upper", "lower", "medial", "lateral", "region", "lobe", "wall", "fundus"}
    if (gold_tokens | wrong_tokens) & specificity and (gold_tokens & specificity) != (wrong_tokens & specificity):
        categories.append("LATERALITY_OR_REGION_SPECIFICITY")
        evidence.append("Gold and selected-wrong labels differ on a surface laterality/region/specificity term.")
    if (" of " in gold.label.casefold() or " of " in wrong.label.casefold()) and gold_tokens != wrong_tokens:
        categories.append("COMPOUND_CONCEPT_DECOMPOSITION")
        evidence.append("At least one target label has a compositional 'of' phrase and the target token sets differ.")
    token_union = gold_tokens | wrong_tokens
    token_similarity = len(gold_tokens & wrong_tokens) / len(token_union) if token_union else 0.0
    if token_similarity >= .5 and gold_label != wrong_label:
        categories.append("LEXICAL_NEAR_DUPLICATE")
        evidence.append(f"Gold/selected-wrong label token Jaccard is {token_similarity:.3f}.")
    structural_status, structural_notes = structural_context_diagnostic(source, gold, wrong)
    if structural_status == "STRUCTURAL_SIGNAL_PRESENT":
        categories.append("STRUCTURAL_CONTEXT_NEEDED")
    evidence.extend(structural_notes)
    if not categories:
        categories.append("UNCLASSIFIED")
        evidence.append("No conservative observable taxonomy pattern was established.")
    return sorted(set(categories)), evidence, structural_status


def _strongest_wrong(source: Any, target: Mapping[str, Any], candidate_ids: Sequence[str], gold_id: str) -> tuple[str | None, float | None, Mapping[str, float] | None]:
    scored = [(diagnostic_enriched_score(source, target[candidate_id])[0], candidate_id, diagnostic_enriched_score(source, target[candidate_id])[1]) for candidate_id in candidate_ids if candidate_id != gold_id]
    if not scored:
        return None, None, None
    score, candidate_id, components = min(scored, key=lambda row: (-row[0], row[1]))
    return candidate_id, score, components


def _case_record(p0: Mapping[str, Any], p1: Mapping[str, Any], source: Mapping[str, Any], target: Mapping[str, Any], candidate_ids: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    source_id, gold_id = str(p1["source_id"]), str(p1["gold_id"])
    source_profile, gold_profile = source[source_id], target[gold_id]
    wrong_id, wrong_score, wrong_components = _strongest_wrong(source_profile, target, candidate_ids.get(source_id, (str(p1["selected_id"]),)), gold_id)
    if wrong_id is None:
        wrong_id, wrong_score = str(p1["selected_id"]), None
        wrong_components = None
    wrong_profile = target[wrong_id]
    categories, evidence, structural_status = classify_observable_patterns(source_profile, gold_profile, wrong_profile)
    gold_score, gold_components = diagnostic_enriched_score(source_profile, gold_profile)
    return {
        "source_id": source_id,
        "source_label": source_profile.label,
        "gold_target_id": gold_id,
        "gold_target_label": gold_profile.label,
        "selected_wrong_target_id": wrong_id,
        "selected_wrong_target_label": wrong_profile.label,
        "original_gold_rank": int(p1["frozen_gold_rank"]),
        "original_margin": float(p1["frozen_top1_top2_margin"]),
        "p0_result": "correct" if p0["selected_id"] == p0["gold_id"] else "wrong",
        "p1_result": "correct" if p1["selected_id"] == p1["gold_id"] else "wrong",
        "source_aliases": list(source_profile.aliases),
        "gold_aliases": list(gold_profile.aliases),
        "wrong_aliases": list(wrong_profile.aliases),
        "observable_categories": categories,
        "observed_evidence": evidence,
        "structural_context_status": structural_status,
        "scores": {
            "gold_score": gold_score,
            "strongest_wrong_score": wrong_score,
            "delta_gold_minus_wrong": gold_score - wrong_score if wrong_score is not None else None,
            "gold_components": dict(gold_components),
            "strongest_wrong_components": dict(wrong_components or {}),
        },
        "diagnostic_notes": "Observable diagnostic only; no causal synonym claim or selector change.",
        "causal_claim": None,
    }


def derive_residual_taxonomy(p0_rows: Sequence[Mapping[str, Any]], p1_rows: Sequence[Mapping[str, Any]], source: Mapping[str, Any], target: Mapping[str, Any], candidate_ids: Mapping[str, Sequence[str]] | None = None) -> dict[str, Any]:
    """Derive all Phase-2.6 follow-up populations from persisted rows, never a constant."""
    p0_by_id, p1_by_id = ({str(row["source_id"]): row for row in rows} for rows in (p0_rows, p1_rows))
    if set(p0_by_id) != set(p1_by_id):
        raise ValueError("paired P0/P1 taxonomy requires identical source populations")
    candidate_ids = candidate_ids or {source_id: (str(row["selected_id"]), str(row["gold_id"])) for source_id, row in p1_by_id.items()}
    residual_rows = [row for row in p1_rows if row["nontrivial"] and row["gold_in_frozen_candidate_set"] and float(row["separation"]) < 0]
    ties = [row for row in p1_rows if row["nontrivial"] and row["gold_in_frozen_candidate_set"] and float(row["separation"]) == 0]
    transitions = Counter()
    regression_rows: list[dict[str, Any]] = []
    improvement_rows: list[dict[str, Any]] = []
    for source_id in sorted(p0_by_id):
        p0, p1 = p0_by_id[source_id], p1_by_id[source_id]
        p0_state = "correct" if p0["selected_id"] == p0["gold_id"] else "wrong"
        p1_state = "correct" if p1["selected_id"] == p1["gold_id"] else "wrong"
        transitions[f"{p0_state}_to_{p1_state}"] += 1
        if p0_state == "correct" and p1_state == "wrong":
            regression_rows.append(_case_record(p0, p1, source, target, candidate_ids))
        if p0_state == "wrong" and p1_state == "correct":
            improvement_rows.append(_case_record(p0, p1, source, target, candidate_ids))
    residual = [_case_record(p0_by_id[str(row["source_id"])], row, source, target, candidate_ids) for row in residual_rows]
    counts = Counter(category for row in residual for category in row["observable_categories"])
    return {
        "schema_version": FOLLOWUP_SCHEMA_VERSION,
        "primary_population_definition": "P1 resolved-synonyms V2; frozen Top-20; non-trivial; gold available; gold score < strongest wrong score",
        "residual_population_n": len(residual),
        "residual_cases": residual,
        "tie_population_n": len(ties),
        "tie_source_ids": [str(row["source_id"]) for row in ties],
        "category_counts": {category: counts[category] for category in RESIDUAL_CATEGORIES},
        "categories_overlap": any(len(row["observable_categories"]) > 1 for row in residual),
        "margin_distribution": dict(Counter(margin_bucket(float(row["original_margin"])) for row in residual)),
        "gold_rank_distribution": dict(Counter(rank_bucket(int(row["original_gold_rank"])) for row in residual)),
        "transitions": dict(sorted(transitions.items())),
        "p0_correct_to_p1_wrong": regression_rows,
        "p0_wrong_to_p1_correct": improvement_rows,
        "p1_rank2_5_source_ids": [str(row["source_id"]) for row in p1_rows if 2 <= int(row["frozen_gold_rank"]) <= 5],
        "p1_rank6_10_source_ids": [str(row["source_id"]) for row in p1_rows if 6 <= int(row["frozen_gold_rank"]) <= 10],
        "p1_low_margin_source_ids": [str(row["source_id"]) for row in p1_rows if float(row["frozen_top1_top2_margin"]) < .05],
        "paired_valid": {"p0_rows": len(p0_rows), "p1_rows": len(p1_rows), "paired_rows": len(p0_by_id)},
    }


def _stable_profile_values(profile: Any, field: str) -> list[str]:
    volatile = re.compile(r"^(?:_:)?(?:genid|n)[0-9a-f]{12,}$", re.IGNORECASE)
    return sorted({str(value) for value in getattr(profile, field, ()) if str(value).strip() and not volatile.fullmatch(str(value).strip())}, key=lambda value: (_surface(value), value))


def alias_collision_patterns(source: Any, wrong: Any) -> list[str]:
    """Exact normalized surface overlaps, distinct from alias availability."""
    source_label, wrong_label = _surface(source.label), _surface(wrong.label)
    source_aliases = {_surface(value) for value in source.aliases} - {""}
    wrong_aliases = {_surface(value) for value in wrong.aliases} - {""}
    patterns: list[str] = []
    if source_label and source_label in wrong_aliases:
        patterns.append("SOURCE_LABEL_EQUALS_WRONG_ALIAS")
    if wrong_label and wrong_label in source_aliases:
        patterns.append("SOURCE_ALIAS_EQUALS_WRONG_LABEL")
    if source_aliases & wrong_aliases:
        patterns.append("SOURCE_ALIAS_EQUALS_WRONG_ALIAS")
    return patterns


def _alias_state(profile: Any, role: str) -> str:
    return f"RESOLVED_{role}_ALIAS_PRESENT" if profile.aliases else f"NO_RESOLVED_{role}_ALIAS_OBSERVED"


def _semantic_patterns(source: Any, gold: Any, wrong: Any) -> list[str]:
    legacy, _, _ = classify_observable_patterns(source, gold, wrong)
    allowed = {"GENERIC_SPECIFIC_CONFUSION", "LATERALITY_OR_REGION_SPECIFICITY", "LEXICAL_NEAR_DUPLICATE", "COMPOUND_CONCEPT_DECOMPOSITION"}
    values = sorted(set(legacy) & allowed)
    return values or ["UNCLASSIFIED_SEMANTIC_PATTERN"]


def _v2_case_record(p0: Mapping[str, Any], p1: Mapping[str, Any], source: Mapping[str, Any], target: Mapping[str, Any], candidate_ids: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    source_id, gold_id = str(p1["source_id"]), str(p1["gold_id"])
    source_profile, gold_profile = source[source_id], target[gold_id]
    wrong_id, _, _ = _strongest_wrong(source_profile, target, candidate_ids[source_id], gold_id)
    if wrong_id is None:
        raise ValueError("residual diagnostic requires a non-gold frozen candidate")
    wrong_profile = target[wrong_id]
    structural, notes = structural_context_diagnostic(source_profile, gold_profile, wrong_profile)
    structural = {"STRUCTURAL_SIGNAL_PRESENT": "STRUCTURAL_PROFILE_DIFFERENCE_PRESENT", "STRUCTURAL_SIGNAL_NOT_OBSERVED": "STRUCTURAL_PROFILE_DIFFERENCE_NOT_OBSERVED"}.get(structural, structural)
    return {
        "source_id": source_id, "source_label": source_profile.label,
        "gold_target_id": gold_id, "gold_target_label": gold_profile.label,
        "wrong_target_id": wrong_id, "wrong_target_label": wrong_profile.label,
        "gold_rank": int(p1["frozen_gold_rank"]), "original_margin": float(p1["frozen_top1_top2_margin"]),
        "p0_correct": p0["selected_id"] == p0["gold_id"], "p1_correct": p1["selected_id"] == p1["gold_id"],
        "source_alias_state": _alias_state(source_profile, "SOURCE"),
        "gold_alias_state": _alias_state(gold_profile, "GOLD_TARGET"),
        "wrong_alias_state": _alias_state(wrong_profile, "WRONG_TARGET"),
        "alias_collision_patterns": alias_collision_patterns(source_profile, wrong_profile),
        "semantic_patterns": _semantic_patterns(source_profile, gold_profile, wrong_profile),
        "structural_status": structural,
        "gold_parent_labels": _stable_profile_values(gold_profile, "parents"), "wrong_parent_labels": _stable_profile_values(wrong_profile, "parents"),
        "gold_child_labels": _stable_profile_values(gold_profile, "children"), "wrong_child_labels": _stable_profile_values(wrong_profile, "children"),
        "gold_properties": sorted(set(_stable_profile_values(gold_profile, "object_properties") + _stable_profile_values(gold_profile, "data_properties"))),
        "wrong_properties": sorted(set(_stable_profile_values(wrong_profile, "object_properties") + _stable_profile_values(wrong_profile, "data_properties"))),
        "diagnostic_notes": notes + ["Observable evidence only; availability does not establish source absence and structural difference does not establish necessity."],
    }


def reconcile_alias_collisions(p0_rows: Sequence[Mapping[str, Any]], p1_rows: Sequence[Mapping[str, Any]], source: Mapping[str, Any], target: Mapping[str, Any], candidate_ids: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """Reconcile legacy alias-placement labels with exact-overlap V2 evidence."""
    p0, p1 = ({str(row["source_id"]): row for row in rows} for rows in (p0_rows, p1_rows))
    residual_ids = {identifier for identifier, row in p1.items() if row["nontrivial"] and row["gold_in_frozen_candidate_set"] and float(row["separation"]) < 0}
    records = []
    for identifier in sorted(p0):
        if p0[identifier]["selected_id"] == p0[identifier]["gold_id"] and p1[identifier]["selected_id"] != p1[identifier]["gold_id"]:
            source_profile, wrong = source[identifier], target[str(p1[identifier]["selected_id"])]
            old = "ALIAS_TO_ALIAS_LEXICAL_COLLISION" if source_profile.aliases and wrong.aliases else "SOURCE_ALIAS_TO_WRONG_LABEL_COLLISION" if source_profile.aliases else "SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION" if wrong.aliases else "OTHER_ALIAS_ASSOCIATED_CHANGE"
            records.append({"source_id": identifier, "source_label": source_profile.label, "gold_target_label": target[str(p1[identifier]["gold_id"])].label, "wrong_target_label": wrong.label, "in_residual_138": identifier in residual_ids, "legacy_alias_placement": old, "normalized_observable_alias_collision_patterns": alias_collision_patterns(source_profile, wrong)})
    return {"schema_version": TAXONOMY_V2_SCHEMA_VERSION, "regression_population_n": len(records), "residual_population_n": len(residual_ids), "records": records, "regressions_in_residual_n": sum(row["in_residual_138"] for row in records), "regressions_with_exact_overlap_n": sum(bool(row["normalized_observable_alias_collision_patterns"]) for row in records)}


def derive_residual_taxonomy_v2(p0_rows: Sequence[Mapping[str, Any],], p1_rows: Sequence[Mapping[str, Any]], source: Mapping[str, Any], target: Mapping[str, Any], candidate_ids: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    p0 = {str(row["source_id"]): row for row in p0_rows}
    residual_rows = [row for row in p1_rows if row["nontrivial"] and row["gold_in_frozen_candidate_set"] and float(row["separation"]) < 0]
    rows = [_v2_case_record(p0[str(row["source_id"])], row, source, target, candidate_ids) for row in residual_rows]
    return {"schema_version": TAXONOMY_V2_SCHEMA_VERSION, "primary_population_definition": "P1 resolved-synonyms V2; frozen Top-20; non-trivial; gold available; gold score < strongest wrong score", "residual_population_n": len(rows), "records": rows, "alias_state_counts": {field: dict(Counter(row[field] for row in rows)) for field in ("source_alias_state", "gold_alias_state", "wrong_alias_state")}, "alias_collision_pattern_counts": dict(Counter(value for row in rows for value in row["alias_collision_patterns"])), "semantic_pattern_counts": dict(Counter(value for row in rows for value in row["semantic_patterns"])), "structural_status_counts": dict(Counter(row["structural_status"] for row in rows)), "margin_distribution": dict(Counter(margin_bucket(row["original_margin"]) for row in rows)), "gold_rank_distribution": dict(Counter(rank_bucket(row["gold_rank"]) for row in rows))}


def paired_error_intersection(deterministic_rows: Sequence[Mapping[str, Any]], dense_rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    deterministic = {str(row["source_id"]): row for row in deterministic_rows}; dense = {str(row["source_id"]): row for row in dense_rows}
    if set(deterministic) != set(dense):
        raise ValueError("paired error intersection requires identical source populations")
    result = Counter()
    for identifier in deterministic:
        d_row, n_row = deterministic[identifier], dense[identifier]
        if d_row.get("selection_status", "SELECTED") != "SELECTED" or n_row.get("selection_status", "SELECTED") != "SELECTED":
            result["technical_unavailable"] += 1; continue
        d_ok, n_ok = d_row["selected_id"] == d_row["gold_id"], n_row["selected_id"] == n_row["gold_id"]
        result[("both_correct" if d_ok and n_ok else "deterministic_only_correct" if d_ok else "dense_only_correct" if n_ok else "both_wrong")] += 1
    result["paired_population"] = len(deterministic)
    result["paired_valid_population"] = len(deterministic) - result["technical_unavailable"]
    return dict(result)


def paired_correctness_transitions(p0_rows: Sequence[Mapping[str, Any]], p1_rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Generic paired transition accounting for future Dense P0/P1 results."""
    p0, p1 = ({str(row["source_id"]): row for row in rows} for rows in (p0_rows, p1_rows))
    if set(p0) != set(p1):
        raise ValueError("paired transitions require identical source populations")
    result = Counter()
    for identifier in p0:
        if p0[identifier].get("selection_status", "SELECTED") != "SELECTED" or p1[identifier].get("selection_status", "SELECTED") != "SELECTED":
            result["technical_unavailable"] += 1; continue
        before = "correct" if p0[identifier]["selected_id"] == p0[identifier]["gold_id"] else "wrong"
        after = "correct" if p1[identifier]["selected_id"] == p1[identifier]["gold_id"] else "wrong"
        result[f"{before}_to_{after}"] += 1
    result["paired_population"] = len(p0); result["paired_valid_population"] = len(p0) - result["technical_unavailable"]
    return dict(result)


def residual_dense_outcomes(residual_records: Sequence[Mapping[str, Any]], dense_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Account for every deterministic residual without inferring a Dense result."""
    dense = {str(row["source_id"]): row for row in dense_rows}
    records = []
    for residual in residual_records:
        identifier, row = str(residual["source_id"]), dense.get(str(residual["source_id"]))
        if row is None or row.get("selection_status", "SELECTED") != "SELECTED": outcome = "DENSE_TECHNICAL_UNAVAILABLE"
        elif row.get("gold_score") is not None and row.get("strongest_wrong_score") is not None and float(row["gold_score"]) == float(row["strongest_wrong_score"]): outcome = "TIE_OR_AMBIGUOUS"
        elif row.get("selected_id") == row.get("gold_id"): outcome = "FIXED_BY_DENSE"
        else: outcome = "STILL_WRONG"
        records.append({"source_id": identifier, "dense_outcome": outcome})
    return {"population_n": len(records), "outcome_counts": dict(Counter(row["dense_outcome"] for row in records)), "records": records}


def dense_runtime_check(model_id: str = "sentence-transformers/all-MiniLM-L6-v2", *, revision: str | None = None, device: str = "cpu", normalize_embeddings: bool = True) -> dict[str, Any]:
    """Execute a bounded Dense smoke check; errors are technical, never metrics."""
    packages: dict[str, str] = {}
    for package in ("torch", "sentence-transformers", "transformers", "numpy"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "NOT_INSTALLED"
    backend_sources = (Path(__file__).with_name("v3_phase2_6.py"), Path(__file__))
    source_hash = hashlib.sha256(b"".join(path.read_bytes() for path in backend_sources)).hexdigest()
    result: dict[str, Any] = {"schema_version": FOLLOWUP_SCHEMA_VERSION, "status": "RUNTIME_BLOCKER", "checks": {"PYTHON_OK": True}, "runtime": {"platform": platform.platform(), "python": sys.version.split()[0], "device": device, "model_id": model_id, "model_revision": revision, "normalize_embeddings": normalize_embeddings, "relevant_package_versions": packages, "relevant_package_versions_sha256": hashlib.sha256("\n".join(f"{name}=={value}" for name, value in sorted(packages.items())).encode()).hexdigest(), "dense_backend_sources_sha256": source_hash}}
    try:
        import torch
        result["checks"]["TORCH_IMPORT_OK"] = True
        result["runtime"]["torch_version"] = torch.__version__
    except Exception as error:
        result["checks"]["TORCH_IMPORT_OK"] = False; result["technical_error"] = {"stage": "torch_import", "type": type(error).__name__, "message": str(error)[:300]}
        return result
    try:
        import sentence_transformers
        result["checks"]["SENTENCE_TRANSFORMERS_IMPORT_OK"] = True
        result["runtime"]["sentence_transformers_version"] = sentence_transformers.__version__
    except Exception as error:
        result["checks"]["SENTENCE_TRANSFORMERS_IMPORT_OK"] = False; result["technical_error"] = {"stage": "sentence_transformers_import", "type": type(error).__name__, "message": str(error)[:300]}
        return result
    try:
        backend = SentenceTransformerBackend(model_id, revision=revision, device=device, normalize_embeddings=normalize_embeddings)
        result["checks"]["MODEL_BACKEND_INIT_OK"] = True
        metadata = dict(backend.metadata())
        result["checks"]["MODEL_LOAD_OK"] = True; result["runtime"].update(metadata)
        from .semantic_decision import SemanticEvidence
        left, right = SemanticEvidence("smoke-source", "alpha concept", aliases=("alpha",)), SemanticEvidence("smoke-target", "beta concept", aliases=("beta",))
        vectors = [backend._embed(value) for value in (left, right)]
        finite = all(bool(getattr(vector, "shape", ())) and all(math.isfinite(float(item)) for item in vector) for vector in vectors)
        normalized = all(abs(float(vector @ vector) - 1.0) < 1e-4 for vector in vectors) if normalize_embeddings else None
        result["checks"]["EMBEDDING_SMOKE_TEST_OK"] = finite and (normalized is not False)
        result["smoke"] = {"embedding_shape": list(vectors[0].shape), "finite": finite, "normalized": normalized, "pair_score": backend.score(left, right)}
        candidates = CandidateSet.from_rows("smoke-source", SourceProfileReference("smoke-source"), [{"iri": "smoke-target-a", "score": .9}, {"iri": "smoke-target-b", "score": .8}], retriever_id="frozen-smoke", retriever_version="v1")
        profiles = {"smoke-target-a": left, "smoke-target-b": right}
        selection = DenseSemanticSelector(backend, profiles).select(left, candidates, AmbiguityEvidence.from_candidate_set(candidates, left))
        result["checks"]["SELECTION_SMOKE_TEST_OK"] = selection.status == SelectionStatus.SELECTED
        result["status"] = "DENSE_RUNTIME_READY" if all(result["checks"].values()) else "RUNTIME_BLOCKER"
    except Exception as error:
        result["technical_error"] = {"stage": "backend_load_or_smoke", "type": type(error).__name__, "message": str(error)[:300]}
    return result
