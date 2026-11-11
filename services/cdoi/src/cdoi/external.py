"""License-aware adapters for data acquired outside this repository."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef


class ExternalDatasetUnavailable(FileNotFoundError):
    pass


def _hash_paths(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


class OAEIAlignmentAdapter:
    """Translate OAEI RDF/OWL artifacts to CDOI-neutral cases at the boundary.

    ``cases.json`` is also accepted for a reviewed, normalized export.  It makes
    unit testing possible without bundling any third-party benchmark material.
    """

    name = "oaei"

    def __init__(self, root: Path):
        self.root = root

    def available(self) -> bool:
        return (self.root / "cases.json").exists() or (self.root / "reference.rdf").exists() and ((self.root / "source.owl").exists() and (self.root / "target.owl").exists() or (self.root / "mouse.owl").exists() and (self.root / "human.owl").exists())

    def load_split(self, split: str = "test") -> list[dict]:
        if not self.available():
            raise ExternalDatasetUnavailable("OAEI data not found in local external/oaei storage. Follow data/benchmarks/external/README.md.")
        normalized = self.root / "cases.json"
        if normalized.exists():
            cases = json.loads(normalized.read_text(encoding="utf-8"))
            return [case for case in cases if case.get("split", "test") == split]
        return self._from_rdf()

    def dataset_metadata(self) -> dict[str, object]:
        files = [path for path in self.root.glob("*") if path.is_file()]
        return {"dataset": self.name, "status": "available" if self.available() else "setup_required", "source": "OAEI Anatomy", "year": "2026" if "anatomy-2026" in str(self.root) else None, "license": "track_terms_required", "local_artifact": "external/oaei", "sha256": _hash_paths(files) if files else None}

    def _from_rdf(self) -> list[dict]:
        source, target, reference = Graph(), Graph(), Graph()
        source_path = self.root / "source.owl" if (self.root / "source.owl").exists() else self.root / "mouse.owl"
        target_path = self.root / "target.owl" if (self.root / "target.owl").exists() else self.root / "human.owl"
        source.parse(source_path)
        target.parse(target_path)
        reference.parse(self.root / "reference.rdf")
        labels = {str(subject): str(label) for graph in (source, target) for subject, _, label in graph.triples((None, RDFS.label, None))}
        kinds = {str(subject): "object_property" if (subject, RDF.type, OWL.ObjectProperty) in source or (subject, RDF.type, OWL.ObjectProperty) in target else "data_property" if (subject, RDF.type, OWL.DatatypeProperty) in source or (subject, RDF.type, OWL.DatatypeProperty) in target else "class" for subject in set(source.subjects()) | set(target.subjects())}
        # Alignment API's entity1/entity2 predicates are stable across common OAEI exports.
        pairs = []
        for cell in reference.subjects():
            entities = [value for _, predicate, value in reference.triples((cell, None, None)) if str(predicate).endswith(("entity1", "entity2"))]
            if len(entities) == 2:
                left, right = map(str, entities)
                pairs.append({"case_id": f"oaei-{len(pairs):05d}", "kind": kinds.get(left, "class"), "candidate": labels.get(left, left.rsplit("/", 1)[-1]), "target": labels.get(right, right.rsplit("/", 1)[-1]), "source_iri": left, "target_iri": right, "expected_relation": "EQUIVALENT", "gold_positive": True, "source": "oaei_anatomy_2026_reference"})
        return pairs


class ConceptPlacementAdapter:
    """Adapter for a normalized OET/LM-placement JSON export."""

    name = "concept_placement"

    def __init__(self, root: Path):
        self.root = root

    def load_split(self, split: str) -> list[dict]:
        path = self.root / f"{split}.json"
        if not path.exists():
            raise ExternalDatasetUnavailable(f"Concept-placement split '{split}' is missing from local external/oet storage. Follow data/benchmarks/external/README.md.")
        return json.loads(path.read_text(encoding="utf-8"))

    def dataset_metadata(self) -> dict[str, object]:
        files = list(self.root.glob("*.json"))
        return {"dataset": self.name, "status": "available" if files else "setup_required", "local_artifact": "external/oet", "sha256": _hash_paths(files) if files else None}

    @staticmethod
    def evaluate(rankings: dict[str, list[str]], cases: list[dict]) -> dict[str, float | None]:
        ranks: list[int] = []
        for case in cases:
            gold = case["parent_id"]
            ranked = rankings.get(case["case_id"], [])
            if gold in ranked:
                ranks.append(ranked.index(gold) + 1)
        total = len(cases)
        return {"retrieval_recall_at_1": sum(rank <= 1 for rank in ranks) / total if total else None, "retrieval_recall_at_5": sum(rank <= 5 for rank in ranks) / total if total else None, "retrieval_recall_at_10": sum(rank <= 10 for rank in ranks) / total if total else None, "top1_parent_accuracy": sum(rank == 1 for rank in ranks) / total if total else None, "top5_parent_accuracy": sum(rank <= 5 for rank in ranks) / total if total else None, "mrr": sum(1 / rank for rank in ranks) / total if total else None, "n_total": float(total)}


class RCAEvalAdapter:
    """Read a small normalized RCAEval case index without importing RCAEval itself."""

    name = "rcaeval"

    def __init__(self, root: Path):
        self.root = root

    def load_cases(self) -> list[dict]:
        path = self.root / "cases.json"
        if not path.exists():
            raise ExternalDatasetUnavailable("RCAEval normalized case index is missing from local external/rcaeval storage. Follow data/benchmarks/external/README.md.")
        return json.loads(path.read_text(encoding="utf-8"))

    def dataset_metadata(self) -> dict[str, object]:
        path = self.root / "cases.json"
        return {"dataset": self.name, "status": "available" if path.exists() else "setup_required", "local_artifact": "external/rcaeval", "sha256": _hash_paths([path]) if path.exists() else None}
