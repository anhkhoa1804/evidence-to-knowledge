from __future__ import annotations

import shutil
from uuid import uuid4
from pathlib import Path

from rdflib import OWL, RDF, RDFS

from .pipeline import ContinualIntegrationPipeline


def order_sensitivity_experiment(project_root: Path, work_root: Path, orders: list[list[str]]) -> list[dict]:
    """Runs isolated permutations and reports structural rather than just count differences."""
    reports = []
    for index, order in enumerate(orders):
        # A fresh runtime makes repeated manifests rerunnable without modifying prior evidence.
        runtime = work_root / f"order_{index:02d}-{uuid4().hex[:8]}"
        shutil.copytree(project_root / "ontologies", runtime / "ontologies")
        shutil.copytree(project_root / "data" / "fixtures", runtime / "data" / "fixtures")
        pipeline = ContinualIntegrationPipeline(runtime)
        results = [pipeline.ingest(runtime / "data" / "fixtures" / f"{domain}.json", domain) for domain in order]
        bridges = pipeline.discover_mappings()
        promotions = pipeline.promote()
        mappings = sorted(f"{decision.source_concept}:{decision.relation.value}:{decision.target_concept}" for result in results for decision in result.decisions)
        structure = _semantic_structure(pipeline)
        reports.append({"order": order, "mappings": mappings, "duplicate_concepts": sum(1 for result in results for validation in result.validations for warning in validation.warnings if "label" in warning), "promotions": len(promotions), "bridge_mappings": len(bridges), "false_merges": sum(1 for result in results for decision in result.decisions if decision.relation.value == "EQUIVALENT" and decision.warnings), "versions": len(list((runtime / "data" / "ontology_versions").glob("v[0-9][0-9][0-9]"))), "final_module_triples": {name: len(module.graph) for name, module in pipeline.store.modules.items() if module.layer.value in {"DOMAIN", "BRIDGE", "ENTERPRISE_CORE"}}, "semantic_structure": structure})
    return reports


def _semantic_structure(pipeline: ContinualIntegrationPipeline) -> dict[str, list[str]]:
    """Canonicalize semantic graph elements independently of Turtle serialization."""
    classes: set[str] = set()
    properties: set[str] = set()
    subclass_edges: set[str] = set()
    bridge_edges: set[str] = set()
    for module in pipeline.store.modules.values():
        graph = module.graph
        classes.update(str(subject) for subject in graph.subjects(RDF.type, OWL.Class))
        properties.update(str(subject) for kind in (OWL.ObjectProperty, OWL.DatatypeProperty) for subject in graph.subjects(RDF.type, kind))
        subclass_edges.update(f"{subject}>{parent}" for subject, _, parent in graph.triples((None, RDFS.subClassOf, None)))
        if module.layer.value == "BRIDGE":
            bridge_edges.update(f"{subject}>{predicate}>{target}" for subject, predicate, target in graph if predicate != RDF.type)
    return {"classes": sorted(classes), "properties": sorted(properties), "subclass_edges": sorted(subclass_edges), "bridge_edges": sorted(bridge_edges), "promotion_edges": sorted(proposal.target_iri or "" for proposal in pipeline.promote())}
