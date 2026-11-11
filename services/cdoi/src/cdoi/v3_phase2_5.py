"""V3 Phase 2.5 source-faithful semantic-evidence recovery experiments.

This module is deliberately an evaluation-only companion to ``v3_phase2``.
It never changes ``_profiles``, normal ingestion, candidate artifacts, or the
review/commit/KG path.  Profile construction uses raw ontology annotations
only; reference mappings are accepted by evaluation functions only after a
ranking has been produced.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

from rdflib import Graph, RDFS, SKOS

from .oaei_full_corpus import (ConceptProfile, _classes, _local_name, _profiles,
                                _tokens, normalize)


EXTRACTOR_VERSION = "v3_phase2_5_source_faithful_v1"
PROFILE_CONDITIONS = (
    "P0_CURRENT",
    "P1_SYNONYMS",
    "P2_DEFINITIONS",
    "P3_SYNONYMS_DEFINITIONS",
    "P4_FULL_SOURCE_FAITHFUL",
)


def _clean_annotation(value: object) -> str:
    """Stable display value: NFC, trim, then collapse whitespace."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(value))).strip()


def _annotation_key(value: str) -> str:
    """Deduplication key; labels remain untouched and aliases are not replaced."""
    return normalize(value)


def _field_for_predicate(predicate: object) -> str | None:
    """Return a field only for semantically explicit annotation predicates."""
    local = _local_name(predicate).casefold()
    if predicate in {SKOS.altLabel, SKOS.prefLabel} or "synonym" in local or "alias" in local:
        return "aliases"
    if predicate in {RDFS.comment, SKOS.definition} or "definition" in local:
        return "definition"
    return None


@dataclass(frozen=True)
class AnnotationProvenance:
    """Raw-source provenance for one experimental enriched value."""

    source_ontology: str
    source_concept_id: str
    source_annotation_predicate: str
    raw_annotation_value: str
    normalized_value: str
    normalization_transform: str
    extractor_version: str
    evidence_origin: str = "SOURCE_PROVIDED"
    profile_field: str = "aliases"


@dataclass(frozen=True)
class ExperimentalProfileSet:
    condition: str
    source_ontology: str
    profiles: Mapping[str, ConceptProfile]
    provenance: tuple[AnnotationProvenance, ...]

    def provenance_rows(self) -> list[dict[str, str]]:
        return [asdict(item) for item in self.provenance]


def discover_annotation_predicates(path: Path) -> list[dict[str, Any]]:
    """Inventory only predicates whose annotation semantics are explicit."""
    graph = Graph()
    graph.parse(path)
    counts: Counter[tuple[str, str]] = Counter()
    for node in _classes(graph):
        for predicate, _ in graph.predicate_objects(node):
            field = _field_for_predicate(predicate)
            if field:
                counts[(str(predicate), field)] += 1
    return [
        {
            "predicate": predicate,
            "profile_field": field,
            "triple_count": count,
            "current_profile_extracts": predicate in {str(SKOS.altLabel), str(SKOS.prefLabel), str(RDFS.comment), str(SKOS.definition)},
        }
        for (predicate, field), count in sorted(counts.items())
    ]


def source_faithful_profiles(path: Path, condition: str) -> ExperimentalProfileSet:
    """Build one isolated profile condition and preserve raw annotation provenance.

    No reference file is accepted or read here.  Only raw annotation values with
    explicit synonym/alias/definition semantics can augment a profile.
    """
    if condition not in PROFILE_CONDITIONS:
        raise ValueError(f"unknown profile condition: {condition}")
    graph = Graph()
    graph.parse(path)
    current = _profiles(graph)
    include_aliases = condition in {"P1_SYNONYMS", "P3_SYNONYMS_DEFINITIONS", "P4_FULL_SOURCE_FAITHFUL"}
    include_definitions = condition in {"P2_DEFINITIONS", "P3_SYNONYMS_DEFINITIONS", "P4_FULL_SOURCE_FAITHFUL"}
    nodes = {str(node): node for node in _classes(graph)}
    ontology = path.as_posix()
    profiles: dict[str, ConceptProfile] = {}
    provenance: list[AnnotationProvenance] = []
    for iri in sorted(current):
        profile, node = current[iri], nodes[iri]
        alias_values: dict[str, tuple[str, object, str]] = {}
        definition_values: list[tuple[str, object, str]] = []
        for predicate, raw in sorted(graph.predicate_objects(node), key=lambda item: (str(item[0]), _annotation_key(_clean_annotation(item[1])), _clean_annotation(item[1]))):
            field = _field_for_predicate(predicate)
            if not field:
                continue
            cleaned = _clean_annotation(raw)
            if not cleaned:
                continue
            if field == "aliases":
                alias_values.setdefault(_annotation_key(cleaned), (cleaned, predicate, str(raw)))
            else:
                definition_values.append((cleaned, predicate, str(raw)))
        aliases = profile.aliases
        definition = profile.definition
        current_alias_keys = {_annotation_key(value) for value in aliases}
        label_key = _annotation_key(profile.label)
        if include_aliases:
            additions = [entry for key, entry in alias_values.items() if key and key != label_key and key not in current_alias_keys]
            aliases = tuple(sorted({*aliases, *(item[0] for item in additions)}, key=lambda value: (_annotation_key(value), value)))
            for cleaned, predicate, raw in sorted(additions, key=lambda item: (_annotation_key(item[0]), item[0], str(item[1]))):
                provenance.append(AnnotationProvenance(ontology, iri, str(predicate), raw, cleaned, "unicode_nfc|trim|collapse_whitespace|deduplicate_by_normalized_tokens", EXTRACTOR_VERSION, profile_field="aliases"))
        if include_definitions and definition is None and definition_values:
            cleaned, predicate, raw = min(definition_values, key=lambda item: (_annotation_key(item[0]), item[0], str(item[1])))
            definition = cleaned
            provenance.append(AnnotationProvenance(ontology, iri, str(predicate), raw, cleaned, "unicode_nfc|trim|collapse_whitespace|deterministic_first_normalized_value", EXTRACTOR_VERSION, profile_field="definition"))
        # P4 carries exactly the already extracted structural fields.  The
        # Phase-2 audit established 100% recall for those recognized fields.
        profiles[iri] = ConceptProfile(profile.iri, profile.label, aliases, definition, profile.parents, profile.children, profile.object_properties, profile.data_properties)
    return ExperimentalProfileSet(condition, ontology, profiles, tuple(provenance))


def profile_coverage(profiles: Mapping[str, ConceptProfile]) -> dict[str, Any]:
    """Coverage is calculated from profiles only; it has no reference input."""
    rows = list(profiles.values())
    n = len(rows)
    synonym = {item.iri for item in rows if item.aliases}
    definitions = {item.iri for item in rows if item.definition}
    return {
        "concept_count": n,
        "label_coverage": sum(bool(item.label) for item in rows),
        "synonym_coverage": len(synonym),
        "mean_synonyms_per_concept": sum(len(item.aliases) for item in rows) / n if n else 0.0,
        "definition_coverage": len(definitions),
        "parent_coverage": sum(bool(item.parents) for item in rows),
        "child_coverage": sum(bool(item.children) for item in rows),
        "property_coverage": sum(bool(item.object_properties or item.data_properties) for item in rows),
        "overlap": {
            "synonym_only": len(synonym - definitions),
            "definition_only": len(definitions - synonym),
            "both": len(synonym & definitions),
            "neither": n - len(synonym | definitions),
        },
    }


def _profile_features(profile: ConceptProfile) -> Mapping[str, Any]:
    terms = tuple(sorted({normalize(value) for value in (profile.label, *profile.aliases) if normalize(value)}))
    return {
        "terms": tuple({"text": term, "tokens": _tokens(term), "chars": set(term.replace(" ", ""))} for term in terms),
        "definition_tokens": _tokens(profile.definition) if profile.definition else set(),
        "context_tokens": profile.context_tokens,
    }


def _fuzzy_from_features(source: Mapping[str, Any], target: Mapping[str, Any]) -> float:
    """Best label/alias term pair; P0 exactly reduces to historical label scoring."""
    scores = []
    for source_term in source["terms"]:
        for target_term in target["terms"]:
            source_tokens, target_tokens = source_term["tokens"], target_term["tokens"]
            overlap = len(source_tokens & target_tokens) / len(source_tokens | target_tokens) if source_tokens | target_tokens else 0.0
            exact = 1.0 if source_term["text"] == target_term["text"] else 0.0
            source_chars, target_chars = source_term["chars"], target_term["chars"]
            fuzzy = len(source_chars & target_chars) / len(source_chars | target_chars) if source_chars | target_chars else 0.0
            scores.append(max(exact, 0.65 * fuzzy + 0.35 * overlap))
    return max(scores, default=0.0)


def _fuzzy_lexical(source: ConceptProfile, target: ConceptProfile) -> float:
    return _fuzzy_from_features(_profile_features(source), _profile_features(target))


def _jaccard_text(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens) if left_tokens | right_tokens else 0.0


def _context_overlap(source: ConceptProfile, target: ConceptProfile) -> float:
    left, right = source.context_tokens, target.context_tokens
    return len(left & right) / len(left | right) if left and right else 0.0


def diagnostic_enriched_score(source: ConceptProfile, target: ConceptProfile) -> tuple[float, Mapping[str, float]]:
    """Pre-specified diagnostic score, not a production R2 replacement.

    It keeps the historical 0.8 lexical / 0.2 structural composition.  An
    available definition can support lexical evidence through a symmetric
    cross-field token comparison; it never uses a reference alignment.
    """
    lexical = _fuzzy_lexical(source, target)
    definition_support = max(
        _jaccard_text(source.lexical_text, target.definition) if target.definition else 0.0,
        _jaccard_text(source.definition, target.lexical_text) if source.definition else 0.0,
        _jaccard_text(source.definition, target.definition) if source.definition and target.definition else 0.0,
    )
    context = _context_overlap(source, target)
    return 0.8 * max(lexical, definition_support) + 0.2 * context, {
        "lexical": lexical,
        "definition_support": definition_support,
        "context": context,
    }


def _diagnostic_from_features(source: Mapping[str, Any], target: Mapping[str, Any]) -> tuple[float, Mapping[str, float]]:
    lexical = _fuzzy_from_features(source, target)
    source_term_tokens = set().union(*(term["tokens"] for term in source["terms"]))
    target_term_tokens = set().union(*(term["tokens"] for term in target["terms"]))
    definition_support = max(
        len(source_term_tokens & target["definition_tokens"]) / len(source_term_tokens | target["definition_tokens"]) if target["definition_tokens"] else 0.0,
        len(source["definition_tokens"] & target_term_tokens) / len(source["definition_tokens"] | target_term_tokens) if source["definition_tokens"] else 0.0,
        len(source["definition_tokens"] & target["definition_tokens"]) / len(source["definition_tokens"] | target["definition_tokens"]) if source["definition_tokens"] and target["definition_tokens"] else 0.0,
    )
    left, right = source["context_tokens"], target["context_tokens"]
    context = len(left & right) / len(left | right) if left and right else 0.0
    return 0.8 * max(lexical, definition_support) + 0.2 * context, {"lexical": lexical, "definition_support": definition_support, "context": context}


def rank_full_corpus(source: ConceptProfile, targets: Mapping[str, ConceptProfile], score_mode: str) -> list[tuple[float, str, Mapping[str, float]]]:
    """Rank without any reference mapping.  Evaluation is intentionally separate."""
    if score_mode not in {"FROZEN_R1_LEXICAL", "R2_ENRICHED_DIAGNOSTIC"}:
        raise ValueError(f"unknown score mode: {score_mode}")
    source_features = _profile_features(source)
    cache_key = id(targets)
    target_features = _TARGET_FEATURE_CACHE.get(cache_key)
    if target_features is None:
        target_features = {target_id: _profile_features(target) for target_id, target in targets.items()}
        _TARGET_FEATURE_CACHE[cache_key] = target_features
    rows = []
    for target_id, target in target_features.items():
        if score_mode == "FROZEN_R1_LEXICAL":
            score, components = _fuzzy_from_features(source_features, target), {}
        else:
            score, components = _diagnostic_from_features(source_features, target)
        rows.append((score, target_id, components))
    return sorted(rows, key=lambda row: (-row[0], row[1]))


_TARGET_FEATURE_CACHE: dict[int, Mapping[str, Mapping[str, Any]]] = {}


def _aggregate_ranks(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ranks = [int(row["gold_rank"]) for row in rows]
    n = len(rows)
    return {
        "n": n,
        "r_at_1": sum(rank <= 1 for rank in ranks) / n if n else None,
        "r_at_5": sum(rank <= 5 for rank in ranks) / n if n else None,
        "r_at_10": sum(rank <= 10 for rank in ranks) / n if n else None,
        "r_at_20": sum(rank <= 20 for rank in ranks) / n if n else None,
        "mrr": sum(1 / rank for rank in ranks) / n if n else None,
    }


def evaluate_full_corpus(source: Mapping[str, ConceptProfile], target: Mapping[str, ConceptProfile], references: Mapping[str, str], *, score_mode: str) -> dict[str, Any]:
    """Evaluate rankings after ``rank_full_corpus`` has independently ranked them."""
    rows: list[dict[str, Any]] = []
    for source_id in sorted(references):
        ranked = rank_full_corpus(source[source_id], target, score_mode)
        gold_id = references[source_id]  # This line is deliberately after ranking.
        rank_by_id = {target_id: index for index, (_, target_id, _) in enumerate(ranked, 1)}
        score_by_id = {target_id: (score, components) for score, target_id, components in ranked}
        gold_rank = rank_by_id[gold_id]
        gold_score = score_by_id[gold_id][0]
        wrong_score = next(score for score, target_id, _ in ranked if target_id != gold_id)
        rows.append({
            "source_id": source_id,
            "gold_rank": gold_rank,
            "gold_score": gold_score,
            "strongest_wrong_score": wrong_score,
            "separation": gold_score - wrong_score,
            "relation": "EQUIVALENT",
            "nontrivial": normalize(source[source_id].label) != normalize(target[gold_id].label),
        })
    nontrivial = [row for row in rows if row["nontrivial"]]
    return {
        "score_mode": score_mode,
        "metrics": {"overall": _aggregate_ranks(rows), "nontrivial": _aggregate_ranks(nontrivial)},
        "rows": rows,
    }


def paired_rank_delta(baseline_rows: Sequence[Mapping[str, Any]], enriched_rows: Sequence[Mapping[str, Any]], top_k: int = 20) -> dict[str, int]:
    """Paired rank changes after both conditions have independently ranked."""
    baseline = {str(row["source_id"]): row for row in baseline_rows}
    enriched = {str(row["source_id"]): row for row in enriched_rows}
    if set(baseline) != set(enriched):
        raise ValueError("paired rank comparison requires the same source population")
    result = Counter()
    for source_id in baseline:
        old, new = int(baseline[source_id]["gold_rank"]), int(enriched[source_id]["gold_rank"])
        result["gold_rank_improved" if new < old else "gold_rank_worsened" if new > old else "gold_rank_unchanged"] += 1
        result["gold_entered_top_k"] += int(old > top_k and new <= top_k)
        result["gold_left_top_k"] += int(old <= top_k and new > top_k)
    return dict(result)


def _selection_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    nontrivial = [row for row in rows if row["nontrivial"]]
    correct = lambda values: sum(row["selected_id"] == row["gold_id"] for row in values)
    return {
        "n": n,
        "target_accuracy": correct(rows) / n if n else None,
        "nontrivial_accuracy": correct(nontrivial) / len(nontrivial) if nontrivial else None,
        "rank1_gold_preservation": sum(row["frozen_gold_rank"] == 1 and row["selected_id"] == row["gold_id"] for row in rows),
        "rank2_5_recovery": sum(2 <= row["frozen_gold_rank"] <= 5 and row["selected_id"] == row["gold_id"] for row in rows),
        "rank6_10_recovery": sum(6 <= row["frozen_gold_rank"] <= 10 and row["selected_id"] == row["gold_id"] for row in rows),
        "legacy_082_threshold_abstentions_diagnostic_only": sum(row["selected_score"] < 0.82 for row in rows),
        "low_margin_cases": sum(row["frozen_top1_top2_margin"] < 0.05 for row in rows),
        "low_margin_accuracy": correct([row for row in rows if row["frozen_top1_top2_margin"] < 0.05]) / sum(row["frozen_top1_top2_margin"] < 0.05 for row in rows) if any(row["frozen_top1_top2_margin"] < 0.05 for row in rows) else None,
    }


def fixed_candidate_selection(profiles_source: Mapping[str, ConceptProfile], profiles_target: Mapping[str, ConceptProfile], frozen_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Rerank exactly frozen candidate IDs; membership/order is never regenerated."""
    rows: list[dict[str, Any]] = []
    for item in frozen_rows:
        candidates = item["retrieved_candidates"]
        candidate_ids = [str(candidate["iri"]) for candidate in candidates]
        scored = []
        for candidate_id in candidate_ids:
            score, components = diagnostic_enriched_score(profiles_source[str(item["source_iri"])], profiles_target[candidate_id])
            scored.append((score, candidate_id, components))
        selected_score, selected_id, components = min(scored, key=lambda value: (-value[0], value[1]))
        gold_id = str(item["gold_target_iri"])  # Read only after all candidate scores exist.
        gold_scored = next((row for row in scored if row[1] == gold_id), None)
        wrong_scored = [row for row in scored if row[1] != gold_id]
        strongest_wrong = min(wrong_scored, key=lambda value: (-value[0], value[1])) if wrong_scored else None
        rows.append({
            "source_id": str(item["source_iri"]),
            "selected_id": selected_id,
            "selected_score": selected_score,
            "gold_id": gold_id,
            "gold_in_frozen_candidate_set": gold_scored is not None,
            "gold_score": gold_scored[0] if gold_scored else None,
            "strongest_wrong_score": strongest_wrong[0] if gold_scored and strongest_wrong else None,
            "separation": gold_scored[0] - strongest_wrong[0] if gold_scored and strongest_wrong else None,
            "frozen_gold_rank": int(item["gold_rank"]),
            "frozen_top1_top2_margin": float(item["top1_top2_r1_margin"]),
            "nontrivial": bool(item["nontrivial"]),
            "candidate_ids_sha256": hashlib.sha256("\n".join(candidate_ids).encode()).hexdigest(),
            "components": components,
        })
    return {"selector": "R2_ENRICHED_DIAGNOSTIC", "selector_version": "v3_phase2_5_v1", "candidate_sets_frozen": True, "summary": _selection_summary(rows), "rows": rows}


def hard_negative_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate gold vs strongest wrong candidate only where gold is available."""
    usable = [row for row in rows if row.get("gold_score") is not None and row.get("strongest_wrong_score") is not None]
    def summarize(values: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        separation = [float(row["separation"]) for row in values]
        return {
            "n_gold_available": len(values),
            "gold_gt_wrong": sum(value > 0 for value in separation),
            "tie": sum(value == 0 for value in separation),
            "gold_lt_wrong": sum(value < 0 for value in separation),
            "mean_separation": mean(separation) if separation else None,
            "median_separation": median(separation) if separation else None,
        }
    return {"overall": summarize(usable), "nontrivial": summarize([row for row in usable if row["nontrivial"]])}
