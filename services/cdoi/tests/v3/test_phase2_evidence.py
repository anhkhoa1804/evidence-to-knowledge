from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef

from cdoi.semantic_decision import (AmbiguityEvidence, CandidateSet, DenseSemanticSelector,
                                    SemanticEvidence, SourceProfileReference)
from cdoi.v3_evaluation import risk_coverage, selector_comparison
from cdoi.v3_phase2 import (OntologyPairDataset, audit_ontology_profiles,
                             DenseCandidateRetriever, experimental_enriched_profiles, phase2_parity,
                             tree_manifest)


ROOT = Path(__file__).resolve().parents[2]


def _candidate_set():
    return CandidateSet.from_rows("source", SourceProfileReference("source"), [{"iri": "a", "score": .8}, {"iri": "b", "score": .7}], retriever_id="r1", retriever_version="test")


def test_tree_manifest_is_deterministic_and_path_scoped(tmp_path):
    (tmp_path / "src").mkdir(); (tmp_path / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    first = tree_manifest(tmp_path, ("src/**/*.py",))
    second = tree_manifest(tmp_path, ("src/**/*.py",))
    assert first["aggregate_sha256"] == second["aggregate_sha256"]
    assert first["file_count"] == 1


def test_raw_vs_extracted_profile_audit_distinguishes_absence_from_extraction(tmp_path):
    graph = Graph(); a, b = URIRef("urn:a"), URIRef("urn:b")
    for value in (a, b): graph.add((value, RDF.type, OWL.Class))
    graph.add((a, RDFS.label, __import__("rdflib").Literal("A")))
    graph.add((a, RDFS.subClassOf, b))
    path = tmp_path / "pair.ttl"; graph.serialize(path, format="turtle")
    audit = audit_ontology_profiles(path)
    assert audit["fields"]["aliases"]["categories"]["ABSENT_IN_SOURCE"] == 2
    assert audit["fields"]["parents"]["extraction_recall"] == 1.0
    assert audit["fields"]["label"]["raw_available"] == 1


def test_experimental_enrichment_reads_only_explicit_obo_style_predicates(tmp_path):
    graph = Graph(); node = URIRef("urn:a")
    graph.add((node, RDF.type, OWL.Class)); graph.add((node, RDFS.label, __import__("rdflib").Literal("A")))
    graph.add((node, URIRef("http://example.org/hasRelatedSynonym"), __import__("rdflib").Literal("Alpha")))
    graph.add((node, URIRef("http://example.org/hasDefinition"), __import__("rdflib").Literal("Definition")))
    path = tmp_path / "enriched.ttl"; graph.serialize(path, format="turtle")
    profile = experimental_enriched_profiles(path)["urn:a"]
    assert profile.aliases == ("Alpha",) and profile.definition == "Definition"


class DenseMock:
    backend_id, backend_version, model_id = "mock", "v1", "mock-dense"
    def score(self, source, candidate): return {"a": .2, "b": .9}[candidate.source_id]


class DenseFailure(DenseMock):
    def score(self, source, candidate): raise RuntimeError("backend unavailable")


def test_dense_selector_uses_standard_result_states_without_runtime_assumption():
    values = _candidate_set(); source = SemanticEvidence("source", "Source")
    evidence = AmbiguityEvidence.from_candidate_set(values, source)
    candidates = {"a": SemanticEvidence("a", "A"), "b": SemanticEvidence("b", "B")}
    assert DenseSemanticSelector(DenseMock(), candidates).select(source, values, evidence).candidate_id == "b"
    assert DenseSemanticSelector(DenseFailure(), candidates).select(source, values, evidence).status.value == "TECHNICAL_UNAVAILABLE"
    retrieved = DenseCandidateRetriever(DenseMock()).retrieve(source, candidates, limit=2, index_version="test-index")
    assert [candidate.candidate_id for candidate in retrieved.candidates] == ["b", "a"]


def test_generic_dataset_contract_accepts_non_anatomy_identifiers():
    source, target = SemanticEvidence("urn:source", "Source"), SemanticEvidence("urn:target", "Target")
    # The contract is structural; real adapters provide OAEI ConceptProfile objects.
    dataset = OntologyPairDataset("custom-pair", {source.source_id: source}, {target.source_id: target}, {source.source_id: target.source_id}, {source.source_id: "RELATED_TO"}, {"license": "test"}, "v1")
    assert dataset.relation_types[source.source_id] == "RELATED_TO"


def test_phase2_parity_executes_against_frozen_v263_artifact():
    result = phase2_parity(ROOT / "experiments" / "outputs" / "OAEI_V263_PERSISTED_POSTRANKING" / "exp-3950cb966861" / "result.json")
    assert result["classification"] == "EXACT_PARITY"
    assert result["r1"]["exact_selection"] == result["n"]
    assert result["r2"]["exact_selection"] == result["n"]


def test_risk_coverage_known_cases_including_zero_acceptance_and_ties():
    rows = [{"score": .9, "reference_correct": True}, {"score": .5, "reference_correct": False}, {"score": .5, "reference_correct": True}]
    full, partial, empty = risk_coverage(rows, [.0, .5, 1.0])
    assert full["coverage"] == 1 and round(full["risk"], 3) == .333
    assert partial["committed"] == 3  # threshold ties are included
    assert empty["committed"] == 0 and empty["precision"] is None


def test_agreement_analysis_has_three_selector_and_failure_categories():
    rows = [
        {"source_id": "a", "selector_id": "R1", "status": "SELECTED", "candidate_id": "x", "candidate_set_hash": "h"},
        {"source_id": "a", "selector_id": "R2", "status": "SELECTED", "candidate_id": "x", "candidate_set_hash": "h"},
        {"source_id": "a", "selector_id": "Qwen", "status": "SELECTED", "candidate_id": "y", "candidate_set_hash": "h"},
        {"source_id": "b", "selector_id": "R1", "status": "TECHNICAL_UNAVAILABLE", "candidate_id": None, "candidate_set_hash": "h2"},
    ]
    summary = selector_comparison(rows)
    assert summary["agreement"]["DETERMINISTIC_AGREE_SEMANTIC_DIFFERS"] == 1
    assert summary["agreement"]["TECHNICAL_UNAVAILABLE"] == 1
