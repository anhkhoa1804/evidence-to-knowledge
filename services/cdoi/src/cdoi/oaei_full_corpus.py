"""Fair full-corpus OAEI Anatomy retrieval diagnostics.

This module deliberately sits at the evaluation boundary.  It does not alter
CDOI semantic policy: it indexes a complete target ontology, retrieves without
gold targets, then measures retrieval separately from a fixed lexical chooser.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, SKOS


def normalize(value: str) -> str:
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _tokens(value: str) -> set[str]:
    return set(normalize(value).split())


def _local_name(iri: object) -> str:
    return re.split(r"[/#]", str(iri))[-1]


@dataclass(frozen=True)
class ConceptProfile:
    iri: str
    label: str
    aliases: tuple[str, ...]
    definition: str | None
    parents: tuple[str, ...]
    children: tuple[str, ...]
    object_properties: tuple[str, ...]
    data_properties: tuple[str, ...]

    @property
    def lexical_text(self) -> str:
        return " ".join((self.label, *self.aliases))

    @property
    def context_tokens(self) -> set[str]:
        return _tokens(" ".join((*self.parents, *self.children, *self.object_properties, *self.data_properties)))


def _classes(graph: Graph) -> set[object]:
    return set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class))


def _profiles(graph: Graph) -> dict[str, ConceptProfile]:
    classes = _classes(graph)
    labels = {node: [str(value) for value in graph.objects(node, RDFS.label)] for node in classes}
    def names(nodes: list[object]) -> tuple[str, ...]:
        return tuple(sorted({(labels.get(node) or [_local_name(node)])[0] for node in nodes}))
    profiles: dict[str, ConceptProfile] = {}
    for node in classes:
        label = (labels.get(node) or [_local_name(node)])[0]
        aliases = tuple(sorted({str(value) for predicate in (SKOS.altLabel, SKOS.prefLabel) for value in graph.objects(node, predicate)} - {label}))
        definition = next((str(value) for predicate in (RDFS.comment, SKOS.definition) for value in graph.objects(node, predicate)), None)
        parents = names(list(graph.objects(node, RDFS.subClassOf)))
        children = names(list(graph.subjects(RDFS.subClassOf, node)))
        object_properties = tuple(sorted({_local_name(predicate) for predicate in graph.predicates(node, None) if predicate not in {RDF.type, RDFS.label, RDFS.comment, RDFS.subClassOf}}))
        data_properties = tuple(sorted({_local_name(predicate) for predicate in graph.predicates(None, node) if predicate not in {RDF.type, RDFS.label, RDFS.comment, RDFS.subClassOf}}))
        profiles[str(node)] = ConceptProfile(str(node), label, aliases, definition, parents, children, object_properties, data_properties)
    return profiles


def _reference_pairs(graph: Graph, source_iris: set[str], target_iris: set[str]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for cell in sorted(set(graph.subjects()), key=str):
        entities = [str(value) for _, predicate, value in sorted(graph.triples((cell, None, None)), key=lambda triple: str(triple[1])) if str(predicate).endswith(("entity1", "entity2"))]
        if len(entities) != 2:
            continue
        left, right = entities
        if left in source_iris and right in target_iris:
            pairs[left] = min(right, pairs.get(left, right))
        elif right in source_iris and left in target_iris:
            pairs[right] = min(left, pairs.get(right, left))
    return pairs


class OAEIFullCorpusMatcher:
    """Index and evaluate Anatomy without exposing gold targets to retrieval."""

    protocol = "OAEI_FULL_CORPUS_MATCHING"

    def __init__(self, root: Path):
        self.root = root

    def load(self) -> tuple[dict[str, ConceptProfile], dict[str, ConceptProfile], dict[str, str]]:
        source_path = self.root / ("source.owl" if (self.root / "source.owl").exists() else "mouse.owl")
        target_path = self.root / ("target.owl" if (self.root / "target.owl").exists() else "human.owl")
        source, target, reference = Graph(), Graph(), Graph()
        source.parse(source_path); target.parse(target_path); reference.parse(self.root / "reference.rdf")
        source_profiles, target_profiles = _profiles(source), _profiles(target)
        pairs = _reference_pairs(reference, set(source_profiles), set(target_profiles))
        return source_profiles, target_profiles, pairs

    def persist_index(self, source: dict[str, ConceptProfile], target: dict[str, ConceptProfile]) -> Path:
        path = self.root / "normalized_full_corpus_index.json"
        path.write_text(json.dumps({"protocol": self.protocol, "source": [asdict(profile) for profile in source.values()], "target": [asdict(profile) for profile in target.values()]}, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def _score(source: ConceptProfile, target: ConceptProfile, method: str) -> float:
        source_text, target_text = normalize(source.lexical_text), normalize(target.lexical_text)
        source_tokens, target_tokens = _tokens(source_text), _tokens(target_text)
        overlap = len(source_tokens & target_tokens) / len(source_tokens | target_tokens) if source_tokens | target_tokens else 0.0
        exact = 1.0 if source_text == target_text else 0.0
        source_characters, target_characters = set(source_text.replace(" ", "")), set(target_text.replace(" ", ""))
        fuzzy = len(source_characters & target_characters) / len(source_characters | target_characters) if source_characters | target_characters else 0.0
        lexical = max(exact, 0.65 * fuzzy + 0.35 * overlap)
        if method == "R0_EXACT_NORMALIZED_LEXICAL":
            return exact
        if method == "R1_FUZZY_LEXICAL":
            return lexical
        context_source, context_target = source.context_tokens, target.context_tokens
        context = len(context_source & context_target) / len(context_source | context_target) if context_source | context_target else 0.0
        # R2 is an evaluation-only contextual retrieval score; unavailable
        # context contributes no signal rather than a synthetic negative signal.
        return 0.8 * lexical + 0.2 * context

    def retrieve(self, source: ConceptProfile, targets: dict[str, ConceptProfile], method: str, limit: int = 20) -> list[str]:
        return [iri for _, iri, _, _, _ in self.ranked_candidates(source, targets, method)[:limit]]

    def ranked_candidates(self, source: ConceptProfile, targets: dict[str, ConceptProfile], method: str) -> list[tuple[float, str, float, float, bool]]:
        """Return a deterministic corpus ranking with evaluation-only components.

        The caller receives no gold information.  The tuple is
        ``(frozen_score, iri, lexical, context, context_available)``.
        """
        source_text = normalize(source.lexical_text)
        source_tokens, source_characters = _tokens(source_text), set(source_text.replace(" ", ""))
        source_context = source.context_tokens
        cache = getattr(self, "_target_lexical_cache", {})
        if not cache:
            cache = {iri: (normalize(target.lexical_text), _tokens(target.lexical_text), set(normalize(target.lexical_text).replace(" ", "")), target.context_tokens) for iri, target in targets.items()}
            self._target_lexical_cache = cache
        ranked: list[tuple[float, str, float, float, bool]] = []
        for iri, (target_text, target_tokens, target_characters, target_context) in cache.items():
            exact = 1.0 if source_text == target_text else 0.0
            token_overlap = len(source_tokens & target_tokens) / len(source_tokens | target_tokens) if source_tokens | target_tokens else 0.0
            character_overlap = len(source_characters & target_characters) / len(source_characters | target_characters) if source_characters | target_characters else 0.0
            lexical = max(exact, 0.65 * character_overlap + 0.35 * token_overlap)
            context_available = bool(source_context and target_context)
            context_overlap = len(source_context & target_context) / len(source_context | target_context) if context_available else 0.0
            if method == "R0_EXACT_NORMALIZED_LEXICAL":
                score = exact
            else:
                if method == "R1_FUZZY_LEXICAL":
                    score = lexical
                else:
                    score = 0.8 * lexical + 0.2 * context_overlap
            ranked.append((score, iri, lexical, context_overlap, context_available))
        return sorted(ranked, key=lambda item: (-item[0], item[1]))

    def diagnostic_rows(self, method: str, top_k: int) -> dict[str, object]:
        """Persistable post-ranking evidence; gold is read only after ranking."""
        source, target, gold = self.load()
        index_path = self.persist_index(source, target)
        rows: list[dict[str, object]] = []
        for source_iri, gold_iri in sorted(gold.items()):
            ranked = self.ranked_candidates(source[source_iri], target, method)
            rank_by_iri = {iri: index + 1 for index, (_, iri, _, _, _) in enumerate(ranked)}
            components_by_iri = {iri: (score, lexical, context, available) for score, iri, lexical, context, available in ranked}
            top = ranked[:top_k]
            selected_score, selected_iri, lexical, context, context_available = top[0]
            gold_score, gold_lexical, gold_context, gold_context_available = components_by_iri[gold_iri]
            candidates = [{"rank": index + 1, "iri": iri, "label": target[iri].label, "definition": target[iri].definition, "score": round(score, 6), "lexical_score": round(candidate_lexical, 6), "context_score": round(candidate_context, 6), "context_available": candidate_context_available} for index, (score, iri, candidate_lexical, candidate_context, candidate_context_available) in enumerate(top)]
            rows.append({"source_iri": source_iri, "source_label": source[source_iri].label, "normalized_source_label": normalize(source[source_iri].label), "gold_target_iri": gold_iri, "gold_target_label": target[gold_iri].label, "normalized_gold_target_label": normalize(target[gold_iri].label), "gold_rank": rank_by_iri[gold_iri], "gold_in_top_k": rank_by_iri[gold_iri] <= top_k, "gold_score": round(gold_score, 6), "gold_lexical_score": round(gold_lexical, 6), "gold_context_score": round(gold_context, 6), "gold_context_available": gold_context_available, "selected_candidate_iri": selected_iri, "selected_candidate_rank": 1, "selected_candidate_score": round(selected_score, 6), "selected_lexical_score": round(lexical, 6), "selected_context_score": round(context, 6), "selected_context_available": context_available, "top1_vs_gold_score_margin": round(selected_score - gold_score, 6), "available_features": ["lexical", *( ["context"] if context_available else [])], "available_feature_count": 1 + int(context_available), "trivial_lexical": normalize(source[source_iri].label) == normalize(target[gold_iri].label), "nontrivial": normalize(source[source_iri].label) != normalize(target[gold_iri].label), "retrieved_candidates": candidates})
        return {"protocol": self.protocol, "method": method, "top_k": top_k, "index_path": str(index_path), "n_source_concepts": len(source), "n_target_concepts": len(target), "n_reference_correspondences": len(rows), "rows": rows}

    def evaluate(self, method: str = "R1_FUZZY_LEXICAL", top_k: int = 20, emit_threshold: float = 0.82) -> dict[str, object]:
        source, target, gold = self.load()
        index_path = self.persist_index(source, target)
        rows: list[dict[str, object]] = []
        predictions: set[tuple[str, str]] = set()
        ranks: list[int] = []
        for source_iri, gold_iri in sorted(gold.items()):
            ranked = self.retrieve(source[source_iri], target, method, max(top_k, len(target)))
            rank = ranked.index(gold_iri) + 1 if gold_iri in ranked else None
            if rank:
                ranks.append(rank)
            top = ranked[:top_k]
            selected = top[0] if top else None
            selected_score = self._score(source[source_iri], target[selected], method) if selected else 0.0
            emitted = selected if selected and selected_score >= emit_threshold else None
            if emitted:
                predictions.add((source_iri, emitted))
            if rank is None or rank > top_k:
                failure = "RETRIEVAL_MISS"
            elif emitted is None:
                failure = "THRESHOLD_ABSTENTION"
            elif emitted != gold_iri:
                failure = "GOLD_IN_TOPK_WRONG_TARGET_SELECTED"
            else:
                failure = None
            rows.append({"source_iri": source_iri, "gold_target_iri": gold_iri, "gold_rank": rank, "gold_in_top_k": rank is not None and rank <= top_k, "selected_target_iri": emitted, "selected_score": round(selected_score, 6), "failure": failure, "trivial_lexical": normalize(source[source_iri].label) == normalize(target[gold_iri].label)})
        gold_pairs = set(gold.items())
        true_positive = len(predictions & gold_pairs)
        precision = true_positive / len(predictions) if predictions else 1.0
        recall = true_positive / len(gold_pairs) if gold_pairs else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        def recall_at(k: int) -> float:
            return sum(row["gold_rank"] is not None and row["gold_rank"] <= k for row in rows) / len(rows) if rows else 0.0
        available = [row for row in rows if row["gold_in_top_k"]]
        conditional = sum(row["selected_target_iri"] == row["gold_target_iri"] for row in available) / len(available) if available else None
        def conditional_at(k: int) -> float | None:
            group = [row for row in rows if row["gold_rank"] is not None and row["gold_rank"] <= k]
            return sum(row["selected_target_iri"] == row["gold_target_iri"] for row in group) / len(group) if group else None
        nontrivial = [row for row in rows if not row["trivial_lexical"]]
        failures = ("RETRIEVAL_MISS", "TOPK_WRONG_RANK", "GOLD_IN_TOPK_BUT_REJECTED", "GOLD_IN_TOPK_WRONG_TARGET_SELECTED", "WRONG_RELATION", "MISSING_EVIDENCE", "THRESHOLD_ABSTENTION", "MODEL_PARSE_ERROR")
        return {"protocol": self.protocol, "method": method, "index_path": str(index_path), "metrics": {"n_source_concepts": len(source), "n_target_concepts": len(target), "n_reference_correspondences": len(rows), "recall_at_1": recall_at(1), "recall_at_5": recall_at(5), "recall_at_10": recall_at(10), "recall_at_20": recall_at(20), "mrr": sum(1 / rank for rank in ranks) / len(rows) if rows else 0.0, "median_gold_rank": sorted(ranks)[len(ranks) // 2] if ranks else None, "gold_missing_from_top_k_rate": 1 - recall_at(top_k), "alignment_accuracy_given_gold_in_top_1": conditional_at(1), "alignment_accuracy_given_gold_in_top_5": conditional_at(5), "alignment_accuracy_given_gold_in_top_10": conditional_at(10), "alignment_accuracy_given_gold_in_top_k": conditional, "relation_accuracy_given_gold_available": conditional, "emitted_mappings": len(predictions), "abstentions": sum(row["selected_target_iri"] is None for row in rows), "precision": precision, "recall": recall, "f1": f1, "nontrivial_mapping_recall": sum(row["selected_target_iri"] == row["gold_target_iri"] for row in nontrivial) / len(nontrivial) if nontrivial else None, "failure_taxonomy": {name: sum(row["failure"] == name for row in rows) for name in failures}}, "rows": rows}
