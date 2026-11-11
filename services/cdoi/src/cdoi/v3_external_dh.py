"""Research-only SKOS external-pair extraction and frozen deterministic evaluation."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from rdflib import DCTERMS, Graph, RDF, RDFS, SKOS, URIRef
from .oaei_full_corpus import ConceptProfile, _local_name, normalize
from .v3_phase2_5 import rank_full_corpus
from .v3_phase2_6 import _resolve_annotation_value

DH_EXTERNAL_PROFILE_VERSION = "v3_external_dh_skos_research_v1"

@dataclass(frozen=True)
class DHAnnotationProvenance:
    concept_id: str; predicate: str; raw_annotation_object: str; resolved_value: str; field: str

def _resolved_values(graph: Graph, node: object, predicates: tuple[object, ...]) -> tuple[str, ...]:
    """Read text or label-bearing resource values with stable de-duplication."""
    values: list[str] = []
    for predicate in predicates:
        for raw in graph.objects(node, predicate):
            value, _ = _resolve_annotation_value(graph, raw)
            if value:
                values.append(value)
    return tuple(sorted(set(values), key=lambda value: (normalize(value), value)))


def _label(graph: Graph, node: object) -> str | None:
    for predicate in (SKOS.prefLabel, RDFS.label):
        values = _resolved_values(graph, node, (predicate,))
        if values: return values[0]
    return None

def extract_skos_profiles(path: Path, *, aliases: bool) -> tuple[dict[str, ConceptProfile], tuple[DHAnnotationProvenance, ...]]:
    graph = Graph(); graph.parse(path); nodes = sorted(set(graph.subjects(RDF.type, SKOS.Concept)), key=str)
    labels = {node: _label(graph, node) for node in nodes}; profiles = {}; provenance = []
    for node in nodes:
        label = labels[node]
        if not label: continue
        values: list[str] = []
        if aliases:
            for raw in graph.objects(node, SKOS.altLabel):
                value, resolution = _resolve_annotation_value(graph, raw)
                if value and normalize(value) != normalize(label):
                    values.append(value); provenance.append(DHAnnotationProvenance(str(node), str(SKOS.altLabel), str(raw), value, "aliases"))
        definitions = _resolved_values(graph, node, (SKOS.definition,))
        definition = definitions[0] if definitions else None
        parents = tuple(sorted(value for parent in graph.objects(node, SKOS.broader) if (value := labels.get(parent) or _label(graph, parent))))
        child_nodes = set(graph.subjects(SKOS.broader, node)) | set(graph.objects(node, SKOS.narrower))
        children = tuple(sorted(value for child in child_nodes if (value := labels.get(child) or _label(graph, child))))
        props = tuple(sorted({_local_name(predicate) for predicate in graph.predicates(node, None) if predicate not in {RDF.type, SKOS.prefLabel, SKOS.altLabel, SKOS.definition, SKOS.broader, SKOS.narrower}}))
        profiles[str(node)] = ConceptProfile(str(node), label, tuple(sorted(set(values), key=lambda value: (normalize(value), value))), definition, parents, children, props, ())
    return profiles, tuple(provenance)


def skos_predicate_inventory(path: Path, *, aliases_enabled: bool) -> list[dict[str, object]]:
    """Inventory actual concept predicates without any reference-alignment input."""
    graph = Graph(); graph.parse(path)
    concepts = set(graph.subjects(RDF.type, SKOS.Concept))
    field_by_predicate = {
        SKOS.prefLabel: "label", RDFS.label: "label", SKOS.altLabel: "alias",
        SKOS.definition: "definition", RDFS.comment: "definition", DCTERMS.description: "definition", SKOS.broader: "parent",
        SKOS.narrower: "child",
    }
    counts: Counter[object] = Counter(predicate for concept in concepts for predicate, _ in graph.predicate_objects(concept))
    rows = []
    for predicate, count in sorted(counts.items(), key=lambda item: str(item[0])):
        field = field_by_predicate.get(predicate, "other")
        extracted = predicate in {SKOS.prefLabel, RDFS.label, SKOS.definition, RDFS.comment, SKOS.broader, SKOS.narrower} or (predicate == SKOS.altLabel and aliases_enabled)
        status = "EXTRACTED" if extracted else "DISABLED_P0_ALIAS" if predicate == SKOS.altLabel else "UNSUPPORTED_STANDARD_DEFINITION_PREDICATE" if predicate == DCTERMS.description else "OUT_OF_SCOPE_RELATION_OR_METADATA"
        rows.append({"predicate": str(predicate), "count": count, "profile_field": field, "extracted": extracted, "status": status})
    return rows


def raw_definition_coverage(source_path: Path, target_path: Path, refs: Mapping[str, str]) -> dict[str, int]:
    """Measure standard definition-like raw annotations on the already frozen mapping population."""
    source_graph, target_graph = Graph(), Graph()
    source_graph.parse(source_path); target_graph.parse(target_path)
    predicates = (SKOS.definition, RDFS.comment, DCTERMS.description)
    present = lambda graph, iri: bool(_resolved_values(graph, URIRef(iri), predicates))
    rows = [(present(source_graph, source), present(target_graph, target)) for source, target in refs.items()]
    return {"source_raw_definition_candidates": sum(left for left, _ in rows), "target_raw_definition_candidates": sum(right for _, right in rows), "bilateral_raw_definition_candidates": sum(left and right for left, right in rows)}

def parse_equivalence_reference(path: Path, source_ids: set[str], target_ids: set[str]) -> tuple[dict[str, str], dict[str, int]]:
    graph = Graph(); graph.parse(path); mapping = {}; counts = Counter()
    for cell in set(graph.subjects()):
        entities = [str(value) for _, predicate, value in graph.triples((cell, None, None)) if str(predicate).endswith(("entity1", "entity2"))]
        relation = next((str(value).strip() for _, predicate, value in graph.triples((cell, None, None)) if str(predicate).endswith("relation")), "UNKNOWN")
        counts["total"] += 1; counts[f"relation:{relation}"] += 1
        if len(entities) != 2: counts["invalid"] += 1; continue
        left, right = entities
        if left in source_ids and right in target_ids and relation == "=":
            if left in mapping and mapping[left] != right:
                counts["source_conflict"] += 1
                continue
            counts["duplicate_equivalence"] += int(left in mapping)
            mapping[left] = right; counts["valid_equivalence"] += 1
        else: counts["invalid_or_non_equivalence"] += 1
    counts["unique_source_mappings"] = len(mapping)
    counts["unique_target_mappings"] = len(set(mapping.values()))
    return mapping, dict(counts)

def coverage(source: Mapping[str, ConceptProfile], target: Mapping[str, ConceptProfile], refs: Mapping[str, str]) -> dict[str, Any]:
    rows = [(source[key], target[value]) for key, value in refs.items()]
    both = lambda attr: sum(bool(getattr(a, attr)) and bool(getattr(b, attr)) for a, b in rows)
    return {"mapped_cases": len(rows), "source_labels": sum(bool(a.label) for a, _ in rows), "target_labels": sum(bool(b.label) for _, b in rows), "both_labels": sum(bool(a.label) and bool(b.label) for a, b in rows), "source_aliases": sum(bool(a.aliases) for a, _ in rows), "target_aliases": sum(bool(b.aliases) for _, b in rows), "bilateral_aliases": both("aliases"), "source_definitions": sum(bool(a.definition) for a, _ in rows), "target_definitions": sum(bool(b.definition) for _, b in rows), "bilateral_definitions": both("definition"), "source_parents": sum(bool(a.parents) for a, _ in rows), "target_parents": sum(bool(b.parents) for _, b in rows)}

def paired_rank_changes(p0: list[dict[str, Any]], p1: list[dict[str, Any]]) -> dict[str, int]:
    old, new = ({row["source_id"]: row for row in rows} for rows in (p0, p1)); out = Counter()
    if set(old) != set(new): raise ValueError("P0/P1 populations differ")
    for key in old:
        before, after = old[key]["gold_rank"], new[key]["gold_rank"]
        out["rank_improved" if after < before else "rank_worsened" if after > before else "rank_unchanged"] += 1
        out[("correct" if before == 1 else "wrong") + "_to_" + ("correct" if after == 1 else "wrong")] += 1
    return dict(out)


def hard_negative_audit(source: Mapping[str, ConceptProfile], target: Mapping[str, ConceptProfile], refs: Mapping[str, str]) -> dict[str, object]:
    """Describe full-corpus wrong-target recurrence after gold-blind ranking."""
    wrong_targets: Counter[str] = Counter()
    rows: list[dict[str, object]] = []
    for source_id in sorted(refs):
        ranked = rank_full_corpus(source[source_id], target, "FROZEN_R1_LEXICAL")
        gold_id = refs[source_id]  # Deliberately read only after the candidate ranking is complete.
        gold_rank = next(index for index, (_, target_id, _) in enumerate(ranked, 1) if target_id == gold_id)
        wrong_score, wrong_id, _ = next(item for item in ranked if item[1] != gold_id)
        gold_score = next(score for score, target_id, _ in ranked if target_id == gold_id)
        wrong_targets[wrong_id] += 1
        rows.append({"source_id": source_id, "gold_rank": gold_rank, "gold_score": gold_score, "strongest_wrong_id": wrong_id, "strongest_wrong_label": target[wrong_id].label, "strongest_wrong_score": wrong_score})
    recurring = {target_id: count for target_id, count in sorted(wrong_targets.items()) if count > 1}
    return {"population": len(rows), "wrong_target_counts": dict(sorted(wrong_targets.items())), "recurring_wrong_targets": recurring, "rows": rows}
