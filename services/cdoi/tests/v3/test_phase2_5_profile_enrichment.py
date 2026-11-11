from pathlib import Path

from rdflib import Graph, Literal, OWL, RDF, RDFS, URIRef

from cdoi.oaei_full_corpus import _profiles
from cdoi.v3_phase2_5 import (PROFILE_CONDITIONS, diagnostic_enriched_score,
                              fixed_candidate_selection, profile_coverage,
                              source_faithful_profiles)


def _raw_fixture(tmp_path: Path) -> Path:
    graph = Graph(); node = URIRef("urn:source")
    graph.add((node, RDF.type, OWL.Class)); graph.add((node, RDFS.label, Literal("Canonical Label")))
    graph.add((node, URIRef("urn:hasRelatedSynonym"), Literal(" Alias  Value ")))
    graph.add((node, URIRef("urn:hasRelatedSynonym"), Literal("alias value")))
    graph.add((node, URIRef("urn:hasDefinition"), Literal(" A known definition. ")))
    graph.add((node, URIRef("urn:goldTarget"), Literal("must never enter profile evidence")))
    path = tmp_path / "raw.ttl"; graph.serialize(path, format="turtle")
    return path


def test_source_faithful_profiles_extracts_explicit_fields_with_provenance_and_no_gold(tmp_path):
    path = _raw_fixture(tmp_path)
    current = source_faithful_profiles(path, "P0_CURRENT")
    full = source_faithful_profiles(path, "P4_FULL_SOURCE_FAITHFUL")
    assert PROFILE_CONDITIONS[0] == "P0_CURRENT"
    assert current.profiles["urn:source"].label == full.profiles["urn:source"].label == "Canonical Label"
    assert full.profiles["urn:source"].aliases == ("Alias Value",)
    assert full.profiles["urn:source"].definition == "A known definition."
    assert {item.profile_field for item in full.provenance} == {"aliases", "definition"}
    assert all(item.evidence_origin == "SOURCE_PROVIDED" and "gold" not in item.source_annotation_predicate.casefold() for item in full.provenance)


def test_missing_fields_remain_missing_and_current_profile_is_unchanged(tmp_path):
    graph = Graph(); node = URIRef("urn:bare")
    graph.add((node, RDF.type, OWL.Class)); graph.add((node, RDFS.label, Literal("Bare")))
    path = tmp_path / "bare.ttl"; graph.serialize(path, format="turtle")
    assert source_faithful_profiles(path, "P0_CURRENT").profiles["urn:bare"].aliases == ()
    enriched = source_faithful_profiles(path, "P3_SYNONYMS_DEFINITIONS").profiles["urn:bare"]
    assert enriched.aliases == () and enriched.definition is None
    assert profile_coverage({enriched.iri: enriched})["definition_coverage"] == 0


def test_p0_is_an_exact_default_profile_copy_and_enrichment_does_not_mutate_it(tmp_path):
    path = _raw_fixture(tmp_path)
    graph = Graph(); graph.parse(path)
    default = _profiles(graph)
    p0 = source_faithful_profiles(path, "P0_CURRENT").profiles
    p3 = source_faithful_profiles(path, "P3_SYNONYMS_DEFINITIONS").profiles
    assert p0 == default
    assert default["urn:source"].aliases == () and default["urn:source"].definition is None
    assert p3["urn:source"].aliases and p3["urn:source"].definition


def test_fixed_candidate_selection_keeps_membership_and_scores_only_profiles(tmp_path):
    path = _raw_fixture(tmp_path)
    source = source_faithful_profiles(path, "P3_SYNONYMS_DEFINITIONS").profiles
    targets = {
        "urn:a": source["urn:source"],
        "urn:b": source["urn:source"],
    }
    frozen = [{"source_iri": "urn:source", "gold_target_iri": "urn:a", "gold_rank": 1, "nontrivial": False, "top1_top2_r1_margin": .1, "retrieved_candidates": [{"iri": "urn:b"}, {"iri": "urn:a"}]}]
    result = fixed_candidate_selection(source, targets, frozen)
    assert result["candidate_sets_frozen"] is True
    assert result["rows"][0]["candidate_ids_sha256"]
    assert diagnostic_enriched_score(source["urn:source"], targets["urn:a"])[0] >= 0
