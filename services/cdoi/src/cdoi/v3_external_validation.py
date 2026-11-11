"""Qualification-first external ontology-pair research utilities.

These artifacts stop before evaluation unless a pair satisfies mandatory
independence, corpus, reference, provenance, and licensing requirements.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from rdflib import Graph


QUALIFICATION_SCHEMA_VERSION = "v3_external_pair_qualification_v1"
FORBIDDEN_INDEPENDENT_IDS = frozenset({"oaei_anatomy", "mouse_human_anatomy", "cdoi_bench"})


@dataclass(frozen=True)
class ExternalPairQualification:
    candidate_id: str
    benchmark: str
    source_ontology: str
    target_ontology: str
    source_version: str | None
    target_version: str | None
    full_source_available: bool
    full_target_available: bool
    reference_alignment_available: bool
    stable_ids: bool
    reference_mapping_count: int | None
    relation_types: tuple[str, ...]
    source_labels: bool | None
    target_labels: bool | None
    source_aliases: str
    target_aliases: str
    source_definitions: str
    target_definitions: str
    source_hierarchy: bool | None
    target_hierarchy: bool | None
    license_status: str
    provenance_status: str
    reproducible_download: bool
    independent_from_anatomy: bool
    qualification_status: str
    disqualifying_reasons: tuple[str, ...] = ()
    source_urls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.qualification_status == "QUALIFIED" and (not self.full_source_available or not self.full_target_available or not self.reference_alignment_available or not self.stable_ids or not self.independent_from_anatomy or self.license_status != "CLEAR" or self.provenance_status != "CLEAR"):
            raise ValueError("QUALIFIED requires complete, independent, licensed, provenance-clear inputs")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_alignment_relations(path: Path) -> dict[str, Any]:
    graph = Graph(); graph.parse(path)
    rows = []
    for cell in sorted(set(graph.subjects()), key=str):
        entities = [str(value) for _, predicate, value in graph.triples((cell, None, None)) if str(predicate).endswith(("entity1", "entity2"))]
        relation = next((str(value).strip() for _, predicate, value in graph.triples((cell, None, None)) if str(predicate).endswith("relation")), None)
        if len(entities) == 2:
            rows.append({"source_id": entities[0], "target_id": entities[1], "raw_relation": relation, "relation_policy": "equivalent" if relation == "=" else "unknown"})
    return {"mapping_count": len(rows), "relation_types": dict(Counter(row["raw_relation"] or "UNKNOWN" for row in rows)), "rows": rows}


def bilateral_coverage(rows: Sequence[Mapping[str, Any]], source_field: str, target_field: str) -> dict[str, int]:
    result = Counter()
    for row in rows:
        source, target = bool(row.get(source_field)), bool(row.get(target_field))
        result["source_available"] += source; result["target_available"] += target
        result["both_available"] += source and target; result["source_only"] += source and not target
        result["target_only"] += target and not source; result["neither"] += not source and not target
    result["mapped_cases"] = len(rows)
    return dict(result)


def choose_qualified_pair(candidates: Sequence[ExternalPairQualification]) -> ExternalPairQualification | None:
    """Pre-evaluation choice: never accepts or accesses CDOI score fields."""
    qualified = [candidate for candidate in candidates if candidate.qualification_status == "QUALIFIED" and candidate.candidate_id not in FORBIDDEN_INDEPENDENT_IDS]
    return sorted(qualified, key=lambda candidate: (candidate.license_status != "CLEAR", candidate.provenance_status != "CLEAR", -int(candidate.reproducible_download), candidate.candidate_id))[0] if qualified else None


def unavailable_result(reason: str) -> dict[str, Any]:
    return {"schema_version": QUALIFICATION_SCHEMA_VERSION, "status": "EXTERNAL_VALIDATION_DATA_MISSING", "reason": reason, "no_evaluation_metrics_emitted": True}


def qualification_row(value: ExternalPairQualification) -> dict[str, Any]:
    return asdict(value)
