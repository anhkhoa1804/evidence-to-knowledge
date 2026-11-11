import json
import hashlib
from pathlib import Path

from rdflib import BNode, Graph, Literal, OWL, RDF, RDFS, URIRef

from cdoi.oaei_full_corpus import ConceptProfile
from cdoi.v3_phase2_6 import resolved_source_faithful_profiles
from cdoi.v3_phase2_6_followup import (classify_observable_patterns, dense_runtime_check,
                                        derive_residual_taxonomy, derive_residual_taxonomy_v2,
                                        margin_bucket, paired_correctness_transitions,
                                        paired_error_intersection, rank_bucket,
                                        reconcile_alias_collisions)
from cdoi.v3_phase2_6_followup import residual_dense_outcomes


def _profile(iri, label, aliases=(), parents=()):
    return ConceptProfile(iri, label, tuple(aliases), None, tuple(parents), (), (), ())


def _row(source_id, selected_id, gold_id, *, separation, rank=2, margin=.03, nontrivial=True):
    return {"source_id": source_id, "selected_id": selected_id, "selected_score": .7, "gold_id": gold_id,
            "gold_in_frozen_candidate_set": True, "gold_score": .5, "strongest_wrong_score": .7,
            "separation": separation, "frozen_gold_rank": rank, "frozen_top1_top2_margin": margin,
            "nontrivial": nontrivial, "components": {"lexical": .7, "context": 0.0}}


def test_phase26_literal_annotations_are_preserved_and_blank_nodes_do_not_leak_ids(tmp_path):
    graph = Graph(); concept, blank = URIRef("urn:concept"), BNode()
    graph.add((concept, RDF.type, OWL.Class)); graph.add((concept, RDFS.label, Literal("Canonical")))
    graph.add((concept, URIRef("urn:hasExactSynonym"), Literal("Direct literal synonym")))
    graph.add((concept, URIRef("urn:hasExactSynonym"), blank)); graph.add((blank, RDFS.label, Literal("Resolved blank-node synonym")))
    path = tmp_path / "annotation.ttl"; graph.serialize(path, format="turtle")
    result = resolved_source_faithful_profiles(path, "P1_SYNONYMS_RESOLVED_V2")
    profile = result.profiles["urn:concept"]
    assert profile.aliases == ("Direct literal synonym", "Resolved blank-node synonym")
    assert all("genid" not in value.casefold() and "_:" not in value for value in profile.aliases)
    raw = {item.raw_annotation_value: item for item in result.provenance}
    assert raw["Direct literal synonym"].resolution == "literal"
    assert raw["Resolved blank-node synonym"].raw_annotation_object != "Resolved blank-node synonym"


def test_taxonomy_derives_population_and_preserves_multilabel_unclassified_cases():
    source = {"s": _profile("s", "Left lung", ("lung left",), ("Thorax",)), "u": _profile("u", "Unique")}
    target = {"g": _profile("g", "Left lung lobe", (), ("Thorax",)), "w": _profile("w", "Lung", ("left lung",), ("Respiratory",)), "ug": _profile("ug", "Gold"), "uw": _profile("uw", "Wrong")}
    p0 = [_row("s", "g", "g", separation=.2), _row("u", "uw", "ug", separation=-.1, rank=11, margin=.21)]
    p1 = [_row("s", "w", "g", separation=-.2), _row("u", "uw", "ug", separation=-.1, rank=11, margin=.21)]
    output = derive_residual_taxonomy(p0, p1, source, target, {"s": ("g", "w"), "u": ("ug", "uw")})
    assert output["residual_population_n"] == 2
    first = next(item for item in output["residual_cases"] if item["source_id"] == "s")
    assert {"ALIAS_COLLISION", "GENERIC_SPECIFIC_CONFUSION", "LATERALITY_OR_REGION_SPECIFICITY"} <= set(first["observable_categories"])
    assert first["causal_claim"] is None and first["structural_context_status"] == "STRUCTURAL_SIGNAL_PRESENT"
    assert output["transitions"]["correct_to_wrong"] == 1
    assert output["gold_rank_distribution"]["rank11-20"] == 1
    assert output["categories_overlap"] is True
    assert output["paired_valid"] == {"p0_rows": 2, "p1_rows": 2, "paired_rows": 2}
    assert margin_bucket(.02) == "0.02-0.05" and rank_bucket(6) == "rank6-10"
    encoded = json.loads(json.dumps(output))
    assert encoded["residual_population_n"] == 2


def test_unclassified_pattern_is_explicitly_allowed():
    source = _profile("s", "Source", ("Source alternative",))
    gold = _profile("g", "Alpha", ("Gold alternative",))
    wrong = _profile("w", "Beta", ("Wrong alternative",))
    categories, evidence, status = classify_observable_patterns(source, gold, wrong)
    assert categories == ["UNCLASSIFIED"]
    assert status == "STRUCTURAL_DATA_UNAVAILABLE" and evidence


def test_structural_diagnostic_discards_process_local_blank_node_identifiers():
    source = _profile("s", "Source", parents=("n1234567890abcdef",))
    gold = _profile("g", "Gold", parents=("nabcdef0123456789",))
    wrong = _profile("w", "Wrong", parents=("n0011223344556677",))
    _, evidence, status = classify_observable_patterns(source, gold, wrong)
    assert status == "STRUCTURAL_DATA_UNAVAILABLE"
    assert not any("n1234567890abcdef" in value for value in evidence)


def test_dense_runtime_failure_has_no_fake_metrics(monkeypatch):
    import builtins
    original = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "torch":
            raise OSError("test torch failure")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    result = dense_runtime_check("test/model")
    assert result["status"] == "RUNTIME_BLOCKER"
    assert result["checks"]["TORCH_IMPORT_OK"] is False
    assert "metrics" not in result and "semantic_abstention" not in result


def test_followup_diagnostic_does_not_mutate_historical_phase25_artifact():
    root = Path(__file__).resolve().parents[2]
    historical = root / "experiments" / "archive" / "v3_phase2_5_profile_enrichment" / "RESULT.json"
    before = hashlib.sha256(historical.read_bytes()).hexdigest()
    source = {"s": _profile("s", "Source", ("Source alias",))}
    target = {"g": _profile("g", "Gold", ("Gold alias",)), "w": _profile("w", "Wrong", ("Wrong alias",))}
    p0 = [_row("s", "g", "g", separation=.1)]
    p1 = [_row("s", "w", "g", separation=-.1)]
    derive_residual_taxonomy(p0, p1, source, target, {"s": ("g", "w")})
    assert hashlib.sha256(historical.read_bytes()).hexdigest() == before


def test_taxonomy_v2_uses_orthogonal_observable_alias_and_structural_dimensions():
    source = {"s": _profile("s", "Source", ())}
    target = {"g": _profile("g", "Gold", ("Gold alias",), ("Parent A",)), "w": _profile("w", "Wrong", ("Source",), ("Parent B",))}
    p0, p1 = [_row("s", "g", "g", separation=.2)], [_row("s", "w", "g", separation=-.2)]
    taxonomy = derive_residual_taxonomy_v2(p0, p1, source, target, {"s": ("g", "w")})
    record = taxonomy["records"][0]
    assert record["source_alias_state"] == "NO_RESOLVED_SOURCE_ALIAS_OBSERVED"
    assert record["alias_collision_patterns"] == ["SOURCE_LABEL_EQUALS_WRONG_ALIAS"]
    assert record["structural_status"] == "STRUCTURAL_PROFILE_DIFFERENCE_PRESENT"
    assert "STRUCTURAL_CONTEXT_NEEDED" not in json.dumps(record)
    assert "MISSING_SOURCE_SYNONYM" not in json.dumps(record)


def test_alias_reconciliation_keeps_regression_population_separate_from_residual_population():
    source = {"s": _profile("s", "Muscle")}
    target = {"g": _profile("g", "Muscle"), "w": _profile("w", "Tissue", ("muscle",))}
    p0 = [_row("s", "g", "g", separation=.2, nontrivial=False)]
    p1 = [_row("s", "w", "g", separation=-.2, nontrivial=False)]
    output = reconcile_alias_collisions(p0, p1, source, target, {"s": ("g", "w")})
    assert output["regression_population_n"] == 1 and output["regressions_in_residual_n"] == 0
    assert output["records"][0]["normalized_observable_alias_collision_patterns"] == ["SOURCE_LABEL_EQUALS_WRONG_ALIAS"]


def test_paired_error_intersection_has_explicit_valid_denominator_and_technical_state():
    deterministic = [{"source_id": "a", "selected_id": "g", "gold_id": "g"}, {"source_id": "b", "selected_id": "x", "gold_id": "g"}, {"source_id": "c", "selected_id": "g", "gold_id": "g"}]
    dense = [{"source_id": "a", "selected_id": "g", "gold_id": "g"}, {"source_id": "b", "selected_id": "g", "gold_id": "g"}, {"source_id": "c", "selected_id": None, "gold_id": "g", "selection_status": "TECHNICAL_UNAVAILABLE"}]
    output = paired_error_intersection(deterministic, dense)
    assert output["both_correct"] == 1 and output["dense_only_correct"] == 1
    assert output["technical_unavailable"] == 1 and output["paired_valid_population"] == 2


def test_dense_p0_p1_transitions_and_residual_statuses_are_complete():
    p0 = [{"source_id": "a", "selected_id": "g", "gold_id": "g"}, {"source_id": "b", "selected_id": "x", "gold_id": "g"}]
    p1 = [{"source_id": "a", "selected_id": "x", "gold_id": "g"}, {"source_id": "b", "selected_id": "g", "gold_id": "g"}]
    assert paired_correctness_transitions(p0, p1)["correct_to_wrong"] == 1
    assert paired_correctness_transitions(p0, p1)["wrong_to_correct"] == 1
    residual = [{"source_id": "a"}, {"source_id": "b"}, {"source_id": "c"}]
    dense = [{"source_id": "a", "selected_id": "g", "gold_id": "g"}, {"source_id": "b", "selected_id": "x", "gold_id": "g", "gold_score": .5, "strongest_wrong_score": .5}]
    outcomes = residual_dense_outcomes(residual, dense)
    assert outcomes["population_n"] == 3
    assert outcomes["outcome_counts"] == {"FIXED_BY_DENSE": 1, "TIE_OR_AMBIGUOUS": 1, "DENSE_TECHNICAL_UNAVAILABLE": 1}
