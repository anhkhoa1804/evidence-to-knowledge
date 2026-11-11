"""Evaluation-only STW--TheSoz canonical relation handling and metrics."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from rdflib import Graph, SKOS

from .relation_aware_selection import SemanticRelation
from .v3_stw_thesoz import STW_PREFIX, THESOZ_PREFIX

_INVERSE = {"broadMatch": "narrowMatch", "narrowMatch": "broadMatch", "exactMatch": "exactMatch", "relatedMatch": "relatedMatch"}
_RELATIONS = frozenset(_INVERSE)


def canonical_stw_thesoz_mappings(path: Path, source_ids: set[str], target_ids: set[str]) -> dict[str, Any]:
    """Canonicalize predicate direction from STW source to TheSoz target.

    Reverse triples are inverted before de-duplication.  Pairs that assert
    multiple canonical relations are retained in the audit and excluded from
    single-label relation metrics rather than arbitrarily resolved.
    """
    graph = Graph(); graph.parse(path)
    raw: list[dict[str, str]] = []
    predicates = {str(getattr(SKOS, name)): name for name in _RELATIONS}
    for subject, predicate, obj in graph:
        raw_relation = predicates.get(str(predicate))
        if not raw_relation:
            continue
        left, right = str(subject), str(obj)
        if left.startswith(STW_PREFIX) and right.startswith(THESOZ_PREFIX):
            source, target, direction, relation = left, right, "STW_TO_THESOZ", raw_relation
        elif left.startswith(THESOZ_PREFIX) and right.startswith(STW_PREFIX):
            source, target, direction, relation = right, left, "THESOZ_TO_STW", _INVERSE[raw_relation]
        else:
            continue
        if source in source_ids and target in target_ids:
            raw.append({"source_id": source, "target_id": target, "raw_predicate": raw_relation,
                        "canonical_relation": relation, "triple_direction": direction})
    evidence_by_pair: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        evidence_by_pair[row["source_id"], row["target_id"]].append(row)
    evaluable, conflicts = [], []
    for pair, rows in sorted(evidence_by_pair.items()):
        relations = sorted({row["canonical_relation"] for row in rows})
        record = {"source_id": pair[0], "target_id": pair[1], "relations": relations, "evidence": sorted(rows, key=lambda row: (row["canonical_relation"], row["triple_direction"], row["raw_predicate"]))}
        if len(relations) == 1:
            evaluable.append({"source_id": pair[0], "target_id": pair[1], "relation": relations[0], "evidence_count": len(rows)})
        else:
            conflicts.append(record)
    inverse_pairs = sum(len(rows) >= 2 and len({row["canonical_relation"] for row in rows}) == 1 for rows in evidence_by_pair.values())
    direction_counts = Counter((row["raw_predicate"], row["triple_direction"]) for row in raw)
    return {"raw_eligible_triples": len(raw), "evaluable_rows": evaluable, "conflicted_pairs": conflicts,
            "relation_counts": dict(sorted(Counter(row["relation"] for row in evaluable).items())),
            "direction_audit": {"raw_by_predicate_and_direction": [{"predicate": predicate, "direction": direction, "count": count} for (predicate, direction), count in sorted(direction_counts.items())],
                                "inverse_supported_pair_count": inverse_pairs, "conflicted_pair_count": len(conflicts)}}


def confusion(rows: Iterable[Mapping[str, str]], *, predicted_key: str) -> dict[str, dict[str, int]]:
    labels = [item.value for item in SemanticRelation]
    matrix = {truth: {prediction: 0 for prediction in labels} for truth in _RELATIONS}
    for row in rows:
        matrix[str(row["gt_relation"])][str(row[predicted_key])] += 1
    return matrix


def high_risk_confusions(rows: Iterable[Mapping[str, str]], *, predicted_key: str) -> dict[str, int]:
    rows = list(rows)
    count = lambda truth, prediction: sum(row["gt_relation"] == truth and row[predicted_key] == prediction for row in rows)
    return {"broad_to_exact": count("broadMatch", "exactMatch"), "narrow_to_exact": count("narrowMatch", "exactMatch"),
            "related_to_exact": count("relatedMatch", "exactMatch"), "broad_to_narrow": count("broadMatch", "narrowMatch"),
            "narrow_to_broad": count("narrowMatch", "broadMatch"), "exact_to_broad": count("exactMatch", "broadMatch"),
            "exact_to_narrow": count("exactMatch", "narrowMatch"), "non_equivalence_to_related": sum(row["gt_relation"] != "relatedMatch" and row[predicted_key] == "relatedMatch" for row in rows)}
