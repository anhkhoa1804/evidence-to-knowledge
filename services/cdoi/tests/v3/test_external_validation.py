from pathlib import Path

import pytest
from rdflib import Graph, Literal, URIRef

from cdoi.v3_external_validation import (ExternalPairQualification, bilateral_coverage,
                                          choose_qualified_pair, parse_alignment_relations,
                                          unavailable_result)


def _candidate(**changes):
    base = dict(candidate_id="independent_pair", benchmark="test", source_ontology="s", target_ontology="t", source_version="1", target_version="1", full_source_available=True, full_target_available=True, reference_alignment_available=True, stable_ids=True, reference_mapping_count=1, relation_types=("=",), source_labels=True, target_labels=True, source_aliases="AVAILABLE", target_aliases="AVAILABLE", source_definitions="UNKNOWN", target_definitions="UNKNOWN", source_hierarchy=True, target_hierarchy=True, license_status="CLEAR", provenance_status="CLEAR", reproducible_download=True, independent_from_anatomy=True, qualification_status="QUALIFIED")
    base.update(changes); return ExternalPairQualification(**base)


def test_qualification_requires_mandatory_fields_and_no_anatomy_selection():
    with pytest.raises(ValueError): _candidate(full_target_available=False)
    assert choose_qualified_pair([_candidate(candidate_id="oaei_anatomy")]) is None
    assert choose_qualified_pair([_candidate()]).candidate_id == "independent_pair"


def test_bilateral_coverage_and_unavailable_result_do_not_fabricate_metrics():
    coverage = bilateral_coverage([{"s": True, "t": True}, {"s": True, "t": False}, {"s": False, "t": False}], "s", "t")
    assert coverage == {"source_available": 2, "target_available": 1, "both_available": 1, "source_only": 1, "target_only": 0, "neither": 1, "mapped_cases": 3}
    result = unavailable_result("license unresolved")
    assert result["status"] == "EXTERNAL_VALIDATION_DATA_MISSING" and "r_at_1" not in result


def test_relation_parser_preserves_non_equivalence_without_conversion(tmp_path: Path):
    graph = Graph(); cell, e1, e2, relation = URIRef("urn:cell"), URIRef("urn:e1"), URIRef("urn:e2"), URIRef("urn:relation")
    graph.add((cell, URIRef("urn:entity1"), e1)); graph.add((cell, URIRef("urn:entity2"), e2)); graph.add((cell, relation, Literal("<")))
    path = tmp_path / "alignment.rdf"; graph.serialize(path, format="xml")
    parsed = parse_alignment_relations(path)
    assert parsed["relation_types"] == {"<": 1} and parsed["rows"][0]["relation_policy"] == "unknown"
