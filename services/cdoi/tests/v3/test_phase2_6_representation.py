from pathlib import Path

import pytest
from rdflib import Graph, Literal, OWL, RDF, RDFS, URIRef

from cdoi.semantic_decision import (AmbiguityEvidence, CandidateSet, DenseSemanticSelector,
                                    SemanticEvidence, SourceProfileReference, qsem_v1_prompt)
from cdoi.v3_phase2_6 import (DENSE_SERIALIZATION_VERSION, PROFILE_CONDITIONS_V2,
                              SentenceTransformerBackend, SourceEvidence, candidate_ids_hash,
                              dense_structured_text, resolved_source_faithful_profiles)


def _resource_annotation_fixture(tmp_path: Path) -> Path:
    graph = Graph(); concept, alias, definition = URIRef("urn:concept"), URIRef("urn:alias"), URIRef("urn:def")
    graph.add((concept, RDF.type, OWL.Class)); graph.add((concept, RDFS.label, Literal("Canonical")))
    graph.add((concept, URIRef("urn:hasRelatedSynonym"), alias)); graph.add((alias, RDFS.label, Literal("Alias text")))
    graph.add((concept, URIRef("urn:hasDefinition"), definition)); graph.add((definition, RDFS.label, Literal("Definition text")))
    path = tmp_path / "resource_annotations.ttl"; graph.serialize(path, format="turtle")
    return path


def test_phase26_resolves_labelled_rdf_annotation_objects_and_versions_provenance(tmp_path):
    profiles = resolved_source_faithful_profiles(_resource_annotation_fixture(tmp_path), "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2")
    profile = profiles.profiles["urn:concept"]
    assert PROFILE_CONDITIONS_V2[0] == "P0_CURRENT_V1"
    assert profile.label == "Canonical" and profile.aliases == ("Alias text",) and profile.definition == "Definition text"
    assert all(item.raw_annotation_object.startswith("urn:") and item.profile_condition.endswith("V2") for item in profiles.provenance)


def test_source_evidence_preserves_more_than_a_selector_consumes():
    source = SourceEvidence("s", "P1", {"aliases": ("Alias",), "definition": ("Definition",)}, ())
    assert source.selector_fields(("aliases",)) == {"aliases": ("Alias",)}
    assert source.available_fields["definition"] == ("Definition",)
    with pytest.raises(ValueError, match="reference-only"):
        SourceEvidence("s", "P1", {"gold_target": ("forbidden",)}, ())


def test_dense_serialization_is_deterministic_structured_and_backend_is_lazy():
    profile = SemanticEvidence("s", "Label", aliases=("Alias",), definition="Definition", parents=("Parent",))
    text = dense_structured_text(profile)
    backend = SentenceTransformerBackend("test/model", device="cpu")
    assert DENSE_SERIALIZATION_VERSION == "dense_structured_profile_v1"
    assert text == dense_structured_text(profile)
    assert "label: Label" in text and "aliases: Alias" in text and "definition: Definition" in text
    assert backend._model is None


class _TieBackend:
    backend_id, backend_version, model_id = "mock", "v1", "mock-dense"
    def score(self, source, candidate): return .5


class _UnavailableBackend(_TieBackend):
    def score(self, source, candidate): raise RuntimeError("initialization failed")


def test_dense_contract_uses_candidate_id_ties_and_failure_state_without_changing_set():
    candidates = CandidateSet.from_rows("s", SourceProfileReference("s"), [{"iri": "b", "score": .8}, {"iri": "a", "score": .7}], retriever_id="r", retriever_version="v")
    before = candidate_ids_hash([item.candidate_id for item in candidates.candidates])
    source = SemanticEvidence("s", "Source")
    evidence = AmbiguityEvidence.from_candidate_set(candidates, source)
    profiles = {"a": SemanticEvidence("a", "A"), "b": SemanticEvidence("b", "B")}
    tied = DenseSemanticSelector(_TieBackend(), profiles).select(source, candidates, evidence)
    failed = DenseSemanticSelector(_UnavailableBackend(), profiles).select(source, candidates, evidence)
    assert tied.candidate_id == "a" and tied.status.value == "SELECTED" and tied.candidate_set_hash == candidates.artifact_hash
    assert failed.status.value == "TECHNICAL_UNAVAILABLE" and failed.candidate_id is None
    assert before == candidate_ids_hash([item.candidate_id for item in candidates.candidates])


def test_resolved_profile_conditions_are_deterministic_and_p0_preserves_default(tmp_path):
    path = _resource_annotation_fixture(tmp_path)
    first = resolved_source_faithful_profiles(path, "P1_SYNONYMS_RESOLVED_V2")
    second = resolved_source_faithful_profiles(path, "P1_SYNONYMS_RESOLVED_V2")
    p0 = resolved_source_faithful_profiles(path, "P0_CURRENT_V1")
    assert first == second and p0.profiles["urn:concept"].aliases == () and p0.profiles["urn:concept"].definition is None


def test_qwen_frozen_protocol_keeps_candidate_set_and_order_when_only_profile_evidence_changes():
    candidates = CandidateSet.from_rows("s", SourceProfileReference("s"), [{"iri": "a", "score": .8}, {"iri": "b", "score": .7}], retriever_id="r", retriever_version="v")
    current_source = SemanticEvidence("s", "Source")
    enriched_source = SemanticEvidence("s", "Source", aliases=("Source Alias",), definition="Definition not emitted by frozen QSEM")
    current_targets = {"a": SemanticEvidence("a", "A"), "b": SemanticEvidence("b", "B")}
    enriched_targets = {"a": SemanticEvidence("a", "A", aliases=("Alpha",)), "b": SemanticEvidence("b", "B")}
    current_prompt, current_handles = qsem_v1_prompt(current_source, candidates, current_targets, opaque_handles=True)
    enriched_prompt, enriched_handles = qsem_v1_prompt(enriched_source, candidates, enriched_targets, opaque_handles=True)
    assert current_handles == enriched_handles == {"a": "C01", "b": "C02"}
    assert current_prompt.splitlines()[:2] == enriched_prompt.splitlines()[:2]
    assert "gold" not in current_prompt.casefold() and "gold" not in enriched_prompt.casefold()
    assert current_prompt != enriched_prompt
