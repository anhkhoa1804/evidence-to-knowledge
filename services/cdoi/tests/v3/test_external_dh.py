"""Regression tests for the research-only external SKOS adapter."""

from pathlib import Path

from rdflib import BNode, DCTERMS, Graph, Literal, RDF, RDFS, SKOS, URIRef

from cdoi.oaei_full_corpus import ConceptProfile
from cdoi.v3_external_dh import (coverage, extract_skos_profiles,
                                  hard_negative_audit, paired_rank_changes, parse_equivalence_reference,
                                  raw_definition_coverage)


def _write_skos(path: Path) -> tuple[URIRef, URIRef]:
    graph = Graph()
    parent, concept = URIRef("urn:parent"), URIRef("urn:concept")
    graph.add((parent, RDF.type, SKOS.Concept)); graph.add((parent, SKOS.prefLabel, Literal("Parent")))
    graph.add((concept, RDF.type, SKOS.Concept)); graph.add((concept, SKOS.prefLabel, Literal("Primary label")))
    alias = BNode(); graph.add((alias, RDFS.label, Literal("Resolved alias")))
    graph.add((concept, SKOS.altLabel, alias)); graph.add((concept, SKOS.definition, Literal("A test definition")))
    graph.add((concept, SKOS.broader, parent)); graph.add((parent, SKOS.narrower, concept))
    graph.serialize(path, format="xml")
    return parent, concept


def test_skos_profiles_use_predicates_and_resolve_resource_annotation_values(tmp_path: Path):
    path = tmp_path / "skos.rdf"; parent, concept = _write_skos(path)
    profiles, provenance = extract_skos_profiles(path, aliases=True)
    item = profiles[str(concept)]
    assert item.label == "Primary label" and item.aliases == ("Resolved alias",)
    assert item.definition == "A test definition" and item.parents == ("Parent",) and item.children == ()
    assert provenance[0].raw_annotation_object.startswith("N") and provenance[0].resolved_value == "Resolved alias"
    assert profiles[str(parent)].children == ("Primary label",)


def test_alias_condition_is_reproducible_and_does_not_replace_label(tmp_path: Path):
    path = tmp_path / "skos.rdf"; _, concept = _write_skos(path)
    p0, p0_provenance = extract_skos_profiles(path, aliases=False)
    p1, p1_provenance = extract_skos_profiles(path, aliases=True)
    assert p0[str(concept)].label == p1[str(concept)].label == "Primary label"
    assert p0[str(concept)].aliases == () and p1[str(concept)].aliases == ("Resolved alias",)
    assert p0_provenance == () and len(p1_provenance) == 1


def test_reference_parser_accepts_equivalence_only_and_rejects_other_relations(tmp_path: Path):
    source, target = URIRef("urn:source"), URIRef("urn:target")
    graph = Graph()
    for index, relation in enumerate(("=", "<")):
        cell = URIRef(f"urn:cell:{index}")
        graph.add((cell, URIRef("urn:entity1"), source)); graph.add((cell, URIRef("urn:entity2"), target))
        graph.add((cell, URIRef("urn:relation"), Literal(relation)))
    path = tmp_path / "reference.rdf"; graph.serialize(path, format="xml")
    refs, audit = parse_equivalence_reference(path, {str(source)}, {str(target)})
    assert refs == {str(source): str(target)}
    assert audit["relation:="] == 1 and audit["relation:<"] == 1 and audit["valid_equivalence"] == 1


def test_coverage_and_paired_rank_changes_require_same_reference_population():
    source = {"s": ConceptProfile("s", "source", ("alias",), "definition", (), (), (), ())}
    target = {"t": ConceptProfile("t", "target", ("alias",), None, (), (), (), ())}
    assert coverage(source, target, {"s": "t"})["bilateral_definitions"] == 0
    changes = paired_rank_changes([{"source_id": "s", "gold_rank": 3}], [{"source_id": "s", "gold_rank": 1}])
    assert changes == {"rank_improved": 1, "wrong_to_correct": 1}


def test_standard_description_predicate_is_audited_without_adding_it_to_p1(tmp_path: Path):
    source, target = URIRef("urn:source"), URIRef("urn:target")
    source_graph, target_graph = Graph(), Graph()
    source_graph.add((source, SKOS.definition, Literal("source definition")))
    target_graph.add((target, DCTERMS.description, Literal("target description")))
    source_path, target_path = tmp_path / "source.rdf", tmp_path / "target.rdf"
    source_graph.serialize(source_path, format="xml"); target_graph.serialize(target_path, format="xml")
    assert raw_definition_coverage(source_path, target_path, {str(source): str(target)}) == {
        "source_raw_definition_candidates": 1, "target_raw_definition_candidates": 1,
        "bilateral_raw_definition_candidates": 1,
    }


def test_hard_negative_audit_ranks_before_using_reference_and_counts_recurrence():
    profile = lambda iri, label: ConceptProfile(iri, label, (), None, (), (), (), ())
    source = {"s1": profile("s1", "common"), "s2": profile("s2", "common")}
    target = {"gold1": profile("gold1", "different one"), "gold2": profile("gold2", "different two"), "wrong": profile("wrong", "common")}
    audit = hard_negative_audit(source, target, {"s1": "gold1", "s2": "gold2"})
    assert audit["recurring_wrong_targets"] == {"wrong": 2}
