from pathlib import Path

from rdflib import Graph, Literal, RDF, SKOS, URIRef

from cdoi.v3_stw_thesoz import (STW_PREFIX, THESOZ_PREFIX, evaluate_frozen_candidates,
                                 extract_english_skos_profiles, parse_stw_thesoz_mappings)


def test_extraction_is_language_scoped_and_does_not_consume_match_labels(tmp_path: Path):
    stw = URIRef(STW_PREFIX + "1"); other = URIRef("urn:other")
    graph = Graph(); graph.add((stw, RDF.type, SKOS.Concept)); graph.add((stw, SKOS.prefLabel, Literal("English", lang="en")))
    graph.add((stw, SKOS.prefLabel, Literal("Deutsch", lang="de"))); graph.add((stw, SKOS.exactMatch, other))
    path = tmp_path / "source.ttl"; graph.serialize(path, format="turtle")
    profiles = extract_english_skos_profiles(path, STW_PREFIX)
    assert profiles[str(stw)].label == "English" and profiles[str(stw)].aliases == ()


def test_mapping_parser_preserves_skos_relation_and_non_equivalence_fails_closed(tmp_path: Path):
    source, target = URIRef(STW_PREFIX + "1"), URIRef(THESOZ_PREFIX + "1")
    graph = Graph(); graph.add((target, SKOS.narrowMatch, source)); graph.add((source, SKOS.exactMatch, target))
    path = tmp_path / "mapping.ttl"; graph.serialize(path, format="turtle")
    parsed = parse_stw_thesoz_mappings(path)
    assert parsed["relation_counts"] == {"exactMatch": 1, "narrowMatch": 1}
    assert {row["policy"] for row in parsed["rows"] if row["relation"] == "narrowMatch"} == {"UNSUPPORTED_RELATION_FAIL_CLOSED"}


def test_relation_evaluation_does_not_claim_selection_accuracy():
    candidates = {"s": [{"rank": 1, "candidate_id": "t"}]}
    mappings = {"s": [{"target_id": "t", "relation": "exactMatch", "policy": "EQUIVALENT_CANDIDATE_ONLY"}]}
    result = evaluate_frozen_candidates(candidates, mappings)["relation_results"]["exactMatch"]
    assert result["retrieval_recall_at_1"] == 1 and result["selection_accuracy"] is None and result["unsafe_mapping_count"] is None
