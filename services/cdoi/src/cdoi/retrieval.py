from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Protocol

from .models import ConceptProfile, OntologyCandidate, SchemaCandidateKind
from .ontology import OntologyStore


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def lexical_score(profile: ConceptProfile, label: str, definition: str) -> float:
    source = _tokens(profile.canonical_label)
    target = _tokens(label)
    overlap = len(source & target) / len(source | target) if source | target else 0.0
    sequence = SequenceMatcher(None, profile.canonical_label.casefold(), label.casefold()).ratio()
    definition_overlap = len(_tokens(profile.local_definition) & _tokens(definition)) / max(1, len(_tokens(profile.local_definition) | _tokens(definition)))
    return round(max(overlap, sequence, definition_overlap), 3)


def structural_score(profile: ConceptProfile, label: str, definition: str) -> float:
    target = _tokens(f"{label} {definition}")
    overlap = len(profile.semantic_features & target) / max(1, len(profile.semantic_features | target))
    abstraction = 1.0 if any(_tokens(value) & target for value in profile.abstraction_candidates) else 0.0
    return round(max(overlap, abstraction * 0.8), 3)


class EmbeddingProvider(Protocol):
    def similarity(self, left: str, right: str) -> float: ...


class NullEmbeddingProvider:
    def similarity(self, left: str, right: str) -> float:
        return 0.0


class HashingEmbeddingProvider:
    """Deterministic token baseline for ablations; replace with a local model in production."""
    def similarity(self, left: str, right: str) -> float:
        left_tokens, right_tokens = _tokens(left), _tokens(right)
        return round(len(left_tokens & right_tokens) / len(left_tokens | right_tokens), 3) if left_tokens | right_tokens else 0.0


class HybridRetriever:
    def __init__(self, store: OntologyStore, embedding_provider: EmbeddingProvider | None = None):
        self.store = store
        self.embedding_provider = embedding_provider or NullEmbeddingProvider()

    def retrieve(self, profile: ConceptProfile, limit: int = 5) -> list[OntologyCandidate]:
        module_names = self.store.local_modules(profile.domain)
        candidates: list[OntologyCandidate] = []
        if profile.kind == SchemaCandidateKind.CLASS:
            records = [(module, iri, label, definition, SchemaCandidateKind.CLASS) for module, iri, label, definition in self.store.classes(module_names)]
        else:
            from rdflib import OWL
            expected = OWL.ObjectProperty if profile.kind == SchemaCandidateKind.OBJECT_PROPERTY else OWL.DatatypeProperty
            records = [(module, iri, label, definition, profile.kind) for module, iri, label, definition, _ in self.store.properties(module_names, expected)]
        for module, iri, label, definition, kind in records:
            lexical = lexical_score(profile, label, definition)
            embedding = self.embedding_provider.similarity(f"{profile.canonical_label} {profile.local_definition}", f"{label} {definition}")
            structural = structural_score(profile, label, definition)
            relation = 0.7 if profile.relation_signature and any(token in " ".join(profile.relation_signature).casefold() for token in _tokens(label)) else 0.0
            neighborhood = structural
            domain_score = 1.0 if module.name == profile.domain else 0.75 if module.layer == module.layer.CORE else 0.5
            final = round(0.32 * lexical + 0.13 * embedding + 0.18 * structural + 0.20 * relation + 0.10 * neighborhood + 0.07 * domain_score, 3)
            candidates.append(OntologyCandidate(iri=str(iri), label=label, definition=definition, namespace=module.namespace, ontology_layer=module.layer, domain=module.name if module.layer == module.layer.DOMAIN else None, lexical_score=lexical, embedding_score=embedding, structural_score=structural, relation_signature_score=relation, neighborhood_score=neighborhood, domain_score=domain_score, final_retrieval_score=final, candidate_kind=kind))
        return sorted(candidates, key=lambda item: item.final_retrieval_score, reverse=True)[:limit]
