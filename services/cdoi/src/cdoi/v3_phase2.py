"""V3 Phase-2 evidence acquisition utilities.

All functions are evaluation/reproducibility helpers.  They never alter
ontology proposals, review policy, or canonical KG state.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Protocol

from rdflib import Graph, RDF, RDFS, SKOS

from .oaei_full_corpus import ConceptProfile, _classes, _local_name, _profiles
from .semantic_decision import (AmbiguityEvidence, CandidateSet, R1DeterministicSelector,
                                R2DeterministicSelector, SelectionResult,
                                SelectionStatus, SemanticEvidence,
                                SourceProfileReference, candidate_set_from_v26_row)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_manifest(root: Path, include: tuple[str, ...]) -> dict[str, Any]:
    """Deterministic, secret-free file manifest for a selected project tree."""
    paths = sorted({path for pattern in include for path in root.glob(pattern) if path.is_file()}, key=lambda path: path.as_posix())
    files = [{"path": path.relative_to(root).as_posix(), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in paths]
    aggregate = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"file_count": len(files), "aggregate_sha256": aggregate, "files": files}


def runtime_fingerprint() -> dict[str, Any]:
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=False).stdout
    return {"python_version": sys.version, "implementation": platform.python_implementation(), "os": platform.platform(), "machine": platform.machine(), "architecture": platform.architecture()[0], "pip_freeze_sha256": hashlib.sha256(freeze.encode()).hexdigest(), "pip_freeze_count": len([line for line in freeze.splitlines() if line])}


@dataclass(frozen=True)
class OntologyPairDataset:
    dataset_id: str
    source_profiles: Mapping[str, ConceptProfile]
    target_profiles: Mapping[str, ConceptProfile]
    reference_mappings: Mapping[str, str]
    relation_types: Mapping[str, str]
    license_provenance: Mapping[str, str]
    profile_extraction_version: str

    def __post_init__(self) -> None:
        if not self.source_profiles or not self.target_profiles or not self.reference_mappings:
            raise ValueError("ontology-pair dataset requires source, target, and reference mappings")
        if not all(source in self.source_profiles and target in self.target_profiles for source, target in self.reference_mappings.items()):
            raise ValueError("reference mappings must point into supplied source and target corpora")


class DatasetAdapter(Protocol):
    def load(self) -> OntologyPairDataset: ...


class DenseCandidateRetriever:
    """D1 full-corpus retrieval adapter using the same candidate contract as R1."""
    retriever_id = "DENSE_CANDIDATE_RETRIEVER"
    retriever_version = "v3_phase2_v1"

    def __init__(self, backend: Any):
        self.backend = backend

    def retrieve(self, source: SemanticEvidence, targets: Mapping[str, SemanticEvidence], limit: int = 20, *, index_version: str | None = None, index_hash: str | None = None) -> CandidateSet:
        scored = sorted(((float(self.backend.score(source, target)), target_id, target) for target_id, target in targets.items()), key=lambda item: (-item[0], item[1]))[:limit]
        rows = [{"rank": rank, "iri": target_id, "score": score, "label": target.label, "dense_score": score} for rank, (score, target_id, target) in enumerate(scored, 1)]
        return CandidateSet.from_rows(source.source_id, SourceProfileReference(source.source_id, source.profile_version), rows, retriever_id=self.retriever_id, retriever_version=self.retriever_version, index_version=index_version, index_hash=index_hash)


def _raw_field_sets(graph: Graph) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    classes = _classes(graph)
    ignored = {RDF.type, RDFS.label, RDFS.comment, RDFS.subClassOf}
    custom = {"aliases": set(), "definition": set()}
    aliases, definitions = set(), set()
    for node in classes:
        for predicate, _ in graph.predicate_objects(node):
            name = _local_name(predicate).casefold()
            if predicate in {SKOS.altLabel, SKOS.prefLabel} or "synonym" in name or "alias" in name:
                aliases.add(str(node))
                if predicate not in {SKOS.altLabel, SKOS.prefLabel}: custom["aliases"].add(str(node))
            if predicate in {RDFS.comment, SKOS.definition} or "definition" in name:
                definitions.add(str(node))
                if predicate not in {RDFS.comment, SKOS.definition}: custom["definition"].add(str(node))
    fields = {
        "label": {str(node) for node in classes if any(graph.objects(node, RDFS.label))},
        "aliases": aliases,
        "definition": definitions,
        "parents": {str(node) for node in classes if any(graph.objects(node, RDFS.subClassOf))},
        "children": {str(node) for node in classes if any(graph.subjects(RDFS.subClassOf, node))},
        "object_properties": {str(node) for node in classes if any(predicate not in ignored for predicate in graph.predicates(node, None))},
        "data_properties": {str(node) for node in classes if any(predicate not in ignored for predicate in graph.predicates(None, node))},
    }
    return fields, custom


def _profile_field_sets(profiles: Mapping[str, ConceptProfile]) -> dict[str, set[str]]:
    return {
        "label": {iri for iri, value in profiles.items() if bool(value.label)},
        "aliases": {iri for iri, value in profiles.items() if bool(value.aliases)},
        "definition": {iri for iri, value in profiles.items() if bool(value.definition)},
        "parents": {iri for iri, value in profiles.items() if bool(value.parents)},
        "children": {iri for iri, value in profiles.items() if bool(value.children)},
        "object_properties": {iri for iri, value in profiles.items() if bool(value.object_properties)},
        "data_properties": {iri for iri, value in profiles.items() if bool(value.data_properties)},
    }


def audit_ontology_profiles(path: Path) -> dict[str, Any]:
    """Compare raw RDF availability with current OAEI profile extraction."""
    graph = Graph(); graph.parse(path)
    raw, custom = _raw_field_sets(graph)
    extracted = _profile_field_sets(_profiles(graph))
    all_nodes = {str(node) for node in _classes(graph)}
    fields = {}
    for field in raw:
        raw_ids, extracted_ids = raw[field], extracted[field]
        categories = Counter()
        for iri in all_nodes:
            if iri in raw_ids and iri in extracted_ids:
                category = "EXTRACTED"
            elif iri in raw_ids and iri in custom.get(field, set()):
                category = "UNSUPPORTED_PREDICATE"
            elif iri in raw_ids:
                category = "NOT_EXTRACTED"
            elif iri in extracted_ids:
                category = "FILTERED_BY_DESIGN"  # local-name label fallback
            else:
                category = "ABSENT_IN_SOURCE"
            categories[category] += 1
        fields[field] = {"raw_available": len(raw_ids), "extracted_available": len(extracted_ids), "extraction_recall": len(raw_ids & extracted_ids) / len(raw_ids) if raw_ids else None, "categories": dict(categories)}
    annotation_predicates = Counter()
    unsupported = Counter()
    known = {str(RDFS.label): "label", str(RDFS.comment): "definition", str(SKOS.prefLabel): "aliases", str(SKOS.altLabel): "aliases", str(SKOS.definition): "definition"}
    for _, predicate, _ in graph:
        name = _local_name(predicate).casefold()
        if str(predicate) in known:
            annotation_predicates[(str(predicate), known[str(predicate)], True)] += 1
        elif "synonym" in name or "alias" in name:
            annotation_predicates[(str(predicate), "aliases", False)] += 1
            unsupported[str(predicate)] += 1
        elif "definition" in name:
            annotation_predicates[(str(predicate), "definition", False)] += 1
            unsupported[str(predicate)] += 1
    return {"path": str(path), "classes": len(all_nodes), "fields": fields, "annotation_predicates": [{"predicate": predicate, "profile_field": field, "currently_extracted": extracted, "triple_count": count} for (predicate, field, extracted), count in sorted(annotation_predicates.items())], "unsupported_annotation_predicates": dict(unsupported)}


def experimental_enriched_profiles(path: Path) -> dict[str, ConceptProfile]:
    """Experimental-only OBO synonym/definition supplement for same-set studies.

    This does not alter the frozen `_profiles` extraction or any runtime ingest
    path.  It uses only raw predicates whose local names explicitly indicate
    synonym/alias/definition semantics.
    """
    graph = Graph(); graph.parse(path)
    current = _profiles(graph)
    nodes = {str(node): node for node in _classes(graph)}
    enriched: dict[str, ConceptProfile] = {}
    for iri, profile in current.items():
        node = nodes[iri]
        aliases = set(profile.aliases)
        definition = profile.definition
        for predicate, value in graph.predicate_objects(node):
            name = _local_name(predicate).casefold()
            if "synonym" in name or "alias" in name:
                aliases.add(str(value))
            if definition is None and "definition" in name:
                definition = str(value)
        enriched[iri] = ConceptProfile(profile.iri, profile.label, tuple(sorted(aliases - {profile.label})), definition, profile.parents, profile.children, profile.object_properties, profile.data_properties)
    return enriched


def enrichment_summary(current: Mapping[str, ConceptProfile], enriched: Mapping[str, ConceptProfile]) -> dict[str, int]:
    return {"profiles": len(current), "aliases_added_to_profiles": sum(not old.aliases and bool(enriched[iri].aliases) for iri, old in current.items()), "definitions_added_to_profiles": sum(not old.definition and bool(enriched[iri].definition) for iri, old in current.items())}


def phase2_parity(result_path: Path) -> dict[str, Any]:
    """Execute V3 deterministic wrappers over frozen V2.6 shared Top-10 rows."""
    result = json.loads(result_path.read_text(encoding="utf-8"))
    rows = result["enriched_cases"]
    historical_r2 = {item["source_iri"]: item for item in result["reranking"]["10"]["results"]}
    r1_matches = r2_matches = score_matches = r1_correct = r2_correct = r1_nontrivial_correct = r2_nontrivial_correct = 0
    differences = []
    for row in rows:
        candidate_set = candidate_set_from_v26_row({**row, "retrieved_candidates": row["retrieved_candidates"][:10]}, method="R1_FUZZY_LEXICAL", index_hash=result.get("candidate_artifact_hash"))
        source = SemanticEvidence(str(row["source_iri"]), str(row["source_label"]))
        ambiguity = AmbiguityEvidence.from_candidate_set(candidate_set, source)
        r1, r2 = R1DeterministicSelector().select(source, candidate_set, ambiguity), R2DeterministicSelector().select(source, candidate_set, ambiguity)
        expected_r1, expected_r2 = row["selected_candidate_iri"], historical_r2[row["source_iri"]]["reranked_target"]
        r1_ok, r2_ok = r1.candidate_id == expected_r1 and r1.status == SelectionStatus.SELECTED, r2.candidate_id == expected_r2 and r2.status == SelectionStatus.SELECTED
        r1_matches += r1_ok; r2_matches += r2_ok
        score_matches += r2.selection_score == historical_r2[row["source_iri"]]["reranked_score"]
        r1_correct += r1.candidate_id == row["gold_target_iri"]; r2_correct += r2.candidate_id == row["gold_target_iri"]
        r1_nontrivial_correct += bool(row["nontrivial"]) and r1.candidate_id == row["gold_target_iri"]; r2_nontrivial_correct += bool(row["nontrivial"]) and r2.candidate_id == row["gold_target_iri"]
        if not (r1_ok and r2_ok): differences.append({"source_id": row["source_iri"], "r1": r1.candidate_id, "expected_r1": expected_r1, "r2": r2.candidate_id, "expected_r2": expected_r2})
    total, nontrivial = len(rows), sum(bool(row["nontrivial"]) for row in rows)
    return {"classification": "EXACT_PARITY" if not differences and score_matches == total else "REGRESSION", "n": total, "r1": {"exact_selection": r1_matches, "top1_accuracy": r1_correct / total, "nontrivial_accuracy": r1_nontrivial_correct / nontrivial}, "r2": {"exact_selection": r2_matches, "exact_score": score_matches, "top1_accuracy": r2_correct / total, "nontrivial_accuracy": r2_nontrivial_correct / nontrivial}, "differences": differences}


def reliability_summary(results: list[SelectionResult]) -> dict[str, Any]:
    latencies = sorted(result.latency_ms for result in results if result.latency_ms is not None)
    return {"n": len(results), "available": sum(result.status != SelectionStatus.TECHNICAL_UNAVAILABLE for result in results), "semantic_abstain": sum(result.status == SelectionStatus.SEMANTIC_ABSTAIN for result in results), "technical_unavailable": sum(result.status == SelectionStatus.TECHNICAL_UNAVAILABLE for result in results), "mean_latency_ms": mean(latencies) if latencies else None, "median_latency_ms": median(latencies) if latencies else None, "p95_latency_ms": latencies[min(len(latencies) - 1, int(.95 * len(latencies)))] if latencies else None, "retry_count": sum(result.attempt_count - 1 for result in results), "cost": "COST_NOT_MEASURED"}
