"""Phase 2.6 representation validation, isolated from production semantics.

Phase 2.5 revealed that OBO annotation objects can be RDF resources whose
``rdfs:label`` is the actual synonym/definition text.  This module versions
that correction rather than changing the historical Phase-2.5 extractor.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping
from types import MappingProxyType

from rdflib import Graph, Literal, RDFS, SKOS

from .oaei_full_corpus import ConceptProfile, _classes, _local_name, _profiles, normalize
from .semantic_decision import DenseScoringBackend, SemanticEvidence
from .v3_phase2_5 import (EXTRACTOR_VERSION, _annotation_key, _clean_annotation,
                          _field_for_predicate)


PROFILE_CONDITION_VERSION = "v2_resolved_annotation_object_label"
PROFILE_CONDITIONS_V2 = (
    "P0_CURRENT_V1",
    "P1_SYNONYMS_RESOLVED_V2",
    "P2_DEFINITIONS_RESOLVED_V2",
    "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2",
    "P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2",
)
DENSE_SERIALIZATION_VERSION = "dense_structured_profile_v1"


@dataclass(frozen=True)
class ResolvedAnnotationProvenance:
    source_ontology: str
    source_concept_id: str
    source_annotation_predicate: str
    raw_annotation_object: str
    raw_annotation_value: str
    normalized_value: str
    normalization_transform: str
    extractor_version: str
    profile_condition: str
    resolution: str
    evidence_origin: str = "SOURCE_PROVIDED"
    profile_field: str = "aliases"


@dataclass(frozen=True)
class SourceEvidence:
    """Preserved raw-source evidence, deliberately distinct from selector use."""

    source_id: str
    profile_condition: str
    available_fields: Mapping[str, tuple[str, ...]]
    provenance: tuple[ResolvedAnnotationProvenance, ...]

    def __post_init__(self) -> None:
        forbidden = {"gold", "reference", "correct", "gold_target", "gold_rank"}
        if any(str(key).casefold() in forbidden or str(key).casefold().startswith("gold_") for key in self.available_fields):
            raise ValueError("SourceEvidence cannot preserve reference-only fields")
        object.__setattr__(self, "available_fields", MappingProxyType({str(key): tuple(value) for key, value in self.available_fields.items()}))

    def selector_fields(self, fields: tuple[str, ...]) -> Mapping[str, tuple[str, ...]]:
        """Expose an explicit subset without deleting preserved source evidence."""
        return {field: self.available_fields.get(field, ()) for field in fields}


@dataclass(frozen=True)
class ResolvedProfileSet:
    condition: str
    profiles: Mapping[str, ConceptProfile]
    provenance: tuple[ResolvedAnnotationProvenance, ...]

    def provenance_rows(self) -> list[dict[str, str]]:
        return [asdict(item) for item in self.provenance]


def _resolve_annotation_value(graph: Graph, value: object) -> tuple[str | None, str]:
    """Resolve literal text or an explicitly labelled RDF annotation object."""
    if isinstance(value, Literal):
        cleaned = _clean_annotation(value)
        return (cleaned or None), "literal"
    labels = sorted({_clean_annotation(item) for predicate in (RDFS.label, SKOS.prefLabel) for item in graph.objects(value, predicate) if _clean_annotation(item)})
    if labels:
        return labels[0], "rdf_resource_rdfs_or_skos_label"
    return None, "unresolved_rdf_resource"


def resolved_source_faithful_profiles(path: Path, condition: str) -> ResolvedProfileSet:
    """Versioned, source-only profile extraction resolving labelled RDF objects."""
    if condition not in PROFILE_CONDITIONS_V2:
        raise ValueError(f"unknown Phase-2.6 profile condition: {condition}")
    graph = Graph(); graph.parse(path)
    current, nodes = _profiles(graph), {str(node): node for node in _classes(graph)}
    aliases_on = condition in {"P1_SYNONYMS_RESOLVED_V2", "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2", "P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2"}
    definitions_on = condition in {"P2_DEFINITIONS_RESOLVED_V2", "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2", "P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2"}
    profiles: dict[str, ConceptProfile] = {}; provenance: list[ResolvedAnnotationProvenance] = []
    for iri, profile in sorted(current.items()):
        aliases: dict[str, tuple[str, object, object, str]] = {}
        definitions: list[tuple[str, object, object, str]] = []
        for predicate, raw_object in sorted(graph.predicate_objects(nodes[iri]), key=lambda item: (str(item[0]), str(item[1]))):
            field = _field_for_predicate(predicate)
            if not field:
                continue
            value, resolution = _resolve_annotation_value(graph, raw_object)
            if not value:
                continue
            if field == "aliases":
                aliases.setdefault(_annotation_key(value), (value, predicate, raw_object, resolution))
            else:
                definitions.append((value, predicate, raw_object, resolution))
        existing_aliases = tuple(profile.aliases)
        existing_keys, label_key = {_annotation_key(item) for item in existing_aliases}, _annotation_key(profile.label)
        if aliases_on:
            added_aliases = [entry for key, entry in aliases.items() if key and key != label_key and key not in existing_keys]
            selected_aliases = tuple(sorted({*existing_aliases, *(entry[0] for entry in added_aliases)}, key=lambda item: (_annotation_key(item), item)))
            for value, predicate, raw_object, resolution in sorted(added_aliases, key=lambda item: (_annotation_key(item[0]), str(item[1]), str(item[2]))):
                provenance.append(ResolvedAnnotationProvenance(path.as_posix(), iri, str(predicate), str(raw_object), value, value, "rdf_object_label_resolution|unicode_nfc|trim|collapse_whitespace|deduplicate_by_normalized_tokens", f"{EXTRACTOR_VERSION}:{PROFILE_CONDITION_VERSION}", condition, resolution, profile_field="aliases"))
        else:
            selected_aliases = existing_aliases
        selected_definition = profile.definition
        if definitions_on and selected_definition is None and definitions:
            value, predicate, raw_object, resolution = min(definitions, key=lambda item: (_annotation_key(item[0]), str(item[1]), str(item[2])))
            selected_definition = value
            provenance.append(ResolvedAnnotationProvenance(path.as_posix(), iri, str(predicate), str(raw_object), value, value, "rdf_object_label_resolution|unicode_nfc|trim|collapse_whitespace|deterministic_first_normalized_value", f"{EXTRACTOR_VERSION}:{PROFILE_CONDITION_VERSION}", condition, resolution, profile_field="definition"))
        profiles[iri] = ConceptProfile(profile.iri, profile.label, selected_aliases, selected_definition, profile.parents, profile.children, profile.object_properties, profile.data_properties)
    return ResolvedProfileSet(condition, profiles, tuple(provenance))


def dense_structured_text(profile: SemanticEvidence) -> str:
    """Pre-specified field-labelled serialization; no learned field weighting."""
    rows = [("label", profile.label), ("aliases", " | ".join(profile.aliases)), ("definition", profile.definition or ""), ("parents", " | ".join(profile.parents)), ("children", " | ".join(profile.children)), ("properties", " | ".join(profile.properties))]
    return "\n".join(f"{field}: {value}" for field, value in rows if value)


class SentenceTransformerBackend:
    """Optional CPU/GPU backend loaded lazily through existing dense contracts."""

    backend_id = "sentence_transformers"
    backend_version = "v3_phase2_6_v1"

    def __init__(self, model_id: str = "sentence-transformers/all-MiniLM-L6-v2", *, revision: str | None = None, device: str = "cpu", normalize_embeddings: bool = True):
        self.model_id, self.revision, self.device = model_id, revision, device
        self.normalize_embeddings = normalize_embeddings
        self._model: Any = None; self._cache: dict[str, Any] = {}

    def _load(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # optional dependency
            self._model = SentenceTransformer(self.model_id, revision=self.revision, device=self.device)
        return self._model

    def metadata(self) -> Mapping[str, Any]:
        model = self._load()
        return {"model_id": self.model_id, "revision": self.revision, "embedding_dimension": model.get_sentence_embedding_dimension(), "normalization": self.normalize_embeddings, "pooling_strategy": "model_default", "runtime": "sentence_transformers", "device": self.device, "serialization_version": DENSE_SERIALIZATION_VERSION}

    def _embed(self, profile: SemanticEvidence) -> Any:
        text = dense_structured_text(profile)
        if text not in self._cache:
            self._cache[text] = self._load().encode(text, convert_to_numpy=True, normalize_embeddings=self.normalize_embeddings, show_progress_bar=False)
        return self._cache[text]

    def score(self, source: SemanticEvidence, candidate: SemanticEvidence) -> float:
        left, right = self._embed(source), self._embed(candidate)
        return float(left @ right) if self.normalize_embeddings else float((left @ right) / (((left @ left) ** .5) * ((right @ right) ** .5)))


def dense_runtime_probe() -> dict[str, Any]:
    """Safe metadata-only probe used by reports; never persists exception secrets."""
    started = perf_counter()
    try:
        import torch
        return {"status": "AVAILABLE", "torch_version": torch.__version__, "device": "cpu", "latency_ms": round((perf_counter() - started) * 1000, 3)}
    except Exception as error:
        return {"status": "RUNTIME_BLOCKER", "error_type": type(error).__name__, "error": str(error)[:300], "latency_ms": round((perf_counter() - started) * 1000, 3)}


def candidate_ids_hash(candidate_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(candidate_ids).encode()).hexdigest()
