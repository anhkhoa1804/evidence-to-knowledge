"""Source-specific, research-only STW--TheSoz extraction and evaluation helpers.

SKOS mapping predicates are retained as source facts.  They are deliberately
not translated to OWL subclass axioms or production alignment relations.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from rdflib import Graph, Literal, RDF, SKOS

from .oaei_full_corpus import ConceptProfile, normalize
from .v3_phase2_5 import rank_full_corpus

STW_PREFIX = "http://zbw.eu/stw/descriptor/"
THESOZ_PREFIX = "https://data.gesis.org/thesoz/concept_"
RELATION_POLICY = {
    str(SKOS.exactMatch): "EQUIVALENT_CANDIDATE_ONLY",
    str(SKOS.closeMatch): "UNSUPPORTED_RELATION_FAIL_CLOSED",
    str(SKOS.broadMatch): "UNSUPPORTED_RELATION_FAIL_CLOSED",
    str(SKOS.narrowMatch): "UNSUPPORTED_RELATION_FAIL_CLOSED",
    str(SKOS.relatedMatch): "UNSUPPORTED_RELATION_FAIL_CLOSED",
}


def _english_values(graph: Graph, node: object, predicate: object) -> tuple[str, ...]:
    """Return direct English SKOS literals only, with no cross-scheme labels."""
    values = [str(value) for value in graph.objects(node, predicate)
              if isinstance(value, Literal) and value.language == "en" and str(value).strip()]
    return tuple(sorted(set(values), key=lambda value: (normalize(value), value)))


def extract_english_skos_profiles(path: Path, namespace: str, *, aliases: bool = False) -> dict[str, ConceptProfile]:
    """Extract direct, English SKOS labels for one namespace.

    This intentionally does not consume ``skos:*Match`` triples found in an
    ontology.  Those remain reference-only material for the separate mapping
    artifact, preserving the candidate-generation boundary.
    """
    graph = Graph(); graph.parse(path)
    profiles: dict[str, ConceptProfile] = {}
    nodes = sorted((node for node in graph.subjects(RDF.type, SKOS.Concept) if str(node).startswith(namespace)), key=str)
    for node in nodes:
        labels = _english_values(graph, node, SKOS.prefLabel)
        if not labels:
            continue
        alias_values = _english_values(graph, node, SKOS.altLabel) if aliases else ()
        label = labels[0]
        aliases_clean = tuple(value for value in alias_values if normalize(value) != normalize(label))
        parents = tuple(sorted(_english_values(graph, parent, SKOS.prefLabel)[0]
                               for parent in graph.objects(node, SKOS.broader)
                               if _english_values(graph, parent, SKOS.prefLabel)))
        children = tuple(sorted(_english_values(graph, child, SKOS.prefLabel)[0]
                                for child in graph.subjects(SKOS.broader, node)
                                if _english_values(graph, child, SKOS.prefLabel)))
        profiles[str(node)] = ConceptProfile(str(node), label, aliases_clean, None, parents, children, (), ())
    return profiles


def parse_stw_thesoz_mappings(path: Path) -> dict[str, Any]:
    """Read directional SKOS mapping predicates without changing their meaning."""
    graph = Graph(); graph.parse(path)
    rows: list[dict[str, str]] = []
    predicates = tuple(RELATION_POLICY)
    for subject, predicate, target in graph:
        if str(predicate) not in predicates:
            continue
        subject_id, target_id = str(subject), str(target)
        if subject_id.startswith(STW_PREFIX) and target_id.startswith(THESOZ_PREFIX):
            source, target_value = subject_id, target_id
        elif subject_id.startswith(THESOZ_PREFIX) and target_id.startswith(STW_PREFIX):
            source, target_value = target_id, subject_id
        else:
            continue
        rows.append({"source_id": source, "target_id": target_value, "predicate": str(predicate),
                     "relation": str(predicate).rsplit("#", 1)[-1], "policy": RELATION_POLICY[str(predicate)]})
    unique = {(row["source_id"], row["target_id"], row["predicate"]): row for row in rows}
    rows = [unique[key] for key in sorted(unique)]
    return {"rows": rows, "relation_counts": dict(sorted(Counter(row["relation"] for row in rows).items())),
            "mapping_count": len(rows)}


def build_frozen_candidates(source: Mapping[str, ConceptProfile], target: Mapping[str, ConceptProfile], top_k: int) -> dict[str, list[dict[str, object]]]:
    """Rank all source profiles before any reference mapping is passed in."""
    candidates: dict[str, list[dict[str, object]]] = {}
    for source_id in sorted(source):
        ranked = rank_full_corpus(source[source_id], target, "FROZEN_R1_LEXICAL")[:top_k]
        candidates[source_id] = [{"rank": rank, "candidate_id": candidate_id, "retrieval_score": score,
                                  "retrieval_method": "FROZEN_R1_LEXICAL"}
                                 for rank, (score, candidate_id, _) in enumerate(ranked, 1)]
    return candidates


def evaluate_frozen_candidates(candidates: Mapping[str, list[Mapping[str, object]]], mappings: Mapping[str, list[Mapping[str, str]]]) -> dict[str, Any]:
    """Join mapping labels only after candidate artifacts exist; report per relation."""
    by_relation: dict[str, list[dict[str, object]]] = defaultdict(list)
    for source_id, rows in mappings.items():
        ranks = {str(candidate["candidate_id"]): int(candidate["rank"]) for candidate in candidates.get(source_id, [])}
        for row in rows:
            rank = ranks.get(row["target_id"])
            by_relation[row["relation"]].append({"source_id": source_id, "target_id": row["target_id"], "rank": rank,
                                                   "candidate_set_available": source_id in candidates,
                                                   "policy": row["policy"]})
    results = {}
    for relation, rows in sorted(by_relation.items()):
        n = len(rows)
        results[relation] = {"mapping_count": n, "candidate_set_coverage": sum(row["candidate_set_available"] for row in rows) / n if n else None,
                             "retrieval_recall_at_1": sum(row["rank"] == 1 for row in rows) / n if n else None,
                             "retrieval_recall_at_5": sum(row["rank"] is not None and row["rank"] <= 5 for row in rows) / n if n else None,
                             "retrieval_recall_at_20": sum(row["rank"] is not None and row["rank"] <= 20 for row in rows) / n if n else None,
                             "rank_distribution": dict(sorted(Counter("not_in_top20" if row["rank"] is None else str(row["rank"]) for row in rows).items())),
                             "selection_accuracy": None, "unsafe_mapping_count": None,
                             "reason": "No relation-aware selector was run; non-equivalence mappings fail closed. Positive-only mappings cannot establish unsafe-mapping count."}
    return {"relation_results": results, "mapping_rows": sum(len(rows) for rows in by_relation.values())}
