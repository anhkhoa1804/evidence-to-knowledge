from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .models import EntityCandidate, Evidence, Provenance, RelationCandidate, SemanticCandidateGraph
from .preprocessing import DocumentChunk


class Extractor(Protocol):
    def extract(self, path: Path, domain: str, chunks: list[DocumentChunk]) -> SemanticCandidateGraph: ...


class StructuredExtractor:
    """Deterministic parser for explicit JSON concept records; never emits OWL axioms."""

    def extract(self, path: Path, domain: str, chunks: list[DocumentChunk]) -> SemanticCandidateGraph:
        source = json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else {}
        provenance = Provenance(input_domain=domain)
        entities: list[EntityCandidate] = []
        relations: list[RelationCandidate] = []
        seen: set[tuple[str, str]] = set()
        for index, item in enumerate(source.get("concepts", []), 1):
            label = str(item["label"]).strip()
            key = (label.casefold(), str(item.get("definition", "")).casefold())
            if key in seen:
                continue
            seen.add(key)
            entity_id = item.get("id", f"{domain}-{index}")
            evidence = Evidence(reference=chunks[0].reference if chunks else None or __import__("cdoi.models", fromlist=["SourceReference"]).SourceReference(source_path=str(path)), text=item.get("definition", label))
            entities.append(EntityCandidate(id=entity_id, surface=label, type_hint=item.get("type_hint"), definition=item.get("definition", ""), relations=item.get("relations", []), evidence=[evidence]))
            for relation in item.get("relations", []):
                predicate, _, object_ = relation.partition("(")
                relations.append(RelationCandidate(subject=entity_id, predicate=predicate, object=object_.rstrip(")") or "unknown", evidence=[evidence]))
        return SemanticCandidateGraph(domain=domain, entities=entities, relations=relations, provenance=provenance)


class OptionalLLMExtractor:
    """Extension point for future unstructured extraction; intentionally disabled in V1."""

    def extract(self, path: Path, domain: str, chunks: list[DocumentChunk]) -> SemanticCandidateGraph:
        raise NotImplementedError("Configure an LLM extractor adapter; deterministic structured extraction is the V1 default.")
