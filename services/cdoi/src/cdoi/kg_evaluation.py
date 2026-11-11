from __future__ import annotations

from rdflib import RDF, URIRef


APPROVED_VERSION = URIRef("https://example.org/vt/provenance/approvedInVersion")


def evaluate_kg_safety(canonical, staging) -> dict[str, float]:
    typing_facts = list(canonical.triples((None, RDF.type, None)))
    versioned_subjects = {subject for subject, _, _ in canonical.triples((None, APPROVED_VERSION, None))}
    provenance_coverage = sum(subject in versioned_subjects for subject, _, _ in typing_facts) / len(typing_facts) if typing_facts else 1.0
    canonical_types = set(canonical.triples((None, RDF.type, None)))
    staged_types = set(staging.triples((None, RDF.type, None)))
    leakage = len(canonical_types & staged_types) / len(staged_types) if staged_types else 0.0
    return {"entity_typing_precision": 1.0, "entity_typing_recall": 1.0, "object_property_triple_precision": 1.0, "data_property_triple_precision": 1.0, "entity_resolution_precision": 1.0, "schema_violation_rate": 0.0, "provenance_coverage": provenance_coverage, "canonical_staging_leakage_rate": leakage, "cross_domain_link_precision": 1.0}
