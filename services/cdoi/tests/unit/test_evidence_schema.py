from dataclasses import replace
import json
from pathlib import Path

from cdoi.evidence_schema import (EvidenceSchemaInducer, RULE_ENTITY_SERVICE,
                                  RULE_GLOSSARY, RULE_RELATION_VOCABULARY,
                                  induction_diagnostics)
from cdoi.raw_preprocessing import process_dataset, write_artifacts


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo" / "manifest.yaml"


def _candidates():
    result = process_dataset(FIXTURE)
    return result, EvidenceSchemaInducer().induce(result)


def test_service_adapter_induces_one_generic_type_not_instance_classes():
    _, candidates = _candidates()
    service = next(item for item in candidates if item.induction_rule == RULE_ENTITY_SERVICE)
    assert service.candidate.canonical_label == "SoftwareService" and service.support_count == 3
    assert "payment-service" not in service.candidate.canonical_label.casefold()
    assert service.status == "CANDIDATE_UNREVIEWED"


def test_bounded_relations_aggregate_support_and_preserve_partial_unknown_target():
    _, candidates = _candidates()
    calls = next(item for item in candidates if item.candidate.canonical_label == "calls")
    assert calls.induction_rule == RULE_RELATION_VOCABULARY and calls.support_count == 2
    assert calls.partial_support_count == 1 and calls.candidate.domain_hints == ["SoftwareService"]
    assert calls.candidate.range_hints == ["SoftwareService"]
    assert len(calls.supporting_evidence_ids) == 2


def test_unresolved_target_alone_has_no_fabricated_range_type():
    result, _ = _candidates()
    only_unknown = replace(result, relations=tuple(item for item in result.relations if item.resolution_status == "UNRESOLVED_REFERENCE"))
    calls = next(item for item in EvidenceSchemaInducer().induce(only_unknown) if item.candidate.canonical_label == "calls")
    assert calls.candidate.range_hints == [] and calls.partial_support_count == 1


def test_glossary_candidates_remain_distinct_from_operational_service_evidence():
    _, candidates = _candidates()
    glossary = [item for item in candidates if item.induction_rule == RULE_GLOSSARY]
    assert {item.candidate.canonical_label for item in glossary} == {"Payment Gateway", "Order Processing", "Service Timeout"}
    assert all(item.candidate.canonical_label != "SoftwareService" for item in glossary)


def test_events_stay_abox_only_and_candidates_have_no_equivalence_or_sameas():
    result, candidates = _candidates()
    serialized = "\n".join(json.dumps(item.artifact(), sort_keys=True) for item in candidates).casefold()
    assert len(result.events) == 3 and "database connection timeout" not in serialized
    assert "sameas" not in serialized and "equivalent" not in serialized


def test_candidate_ids_and_serialization_do_not_depend_on_normalized_input_order():
    result, first = _candidates()
    reordered = replace(result, entities=tuple(reversed(result.entities)), relations=tuple(reversed(result.relations)), semantic_terms=tuple(reversed(result.semantic_terms)))
    second = EvidenceSchemaInducer().induce(reordered)
    assert [item.artifact() for item in first] == [item.artifact() for item in second]


def test_machine_artifact_and_diagnostics_preserve_raw_to_candidate_trace(tmp_path: Path):
    result, candidates = _candidates(); report = write_artifacts(result, tmp_path / "output")
    rows = [json.loads(line) for line in (tmp_path / "output" / "schema_candidates.jsonl").read_text(encoding="utf-8").splitlines()]
    calls = next(row for row in rows if row["label"] == "calls")
    assert calls["supporting_evidence_ids"] and calls["candidate"]["evidence"][0]["reference"]["metadata"]["raw_evidence_id"]
    assert report["schema_induction"] == induction_diagnostics(candidates, result)
    assert report["schema_induction"]["object_property_candidates"] == 2


def test_induction_produces_candidates_only_and_never_writes_ontology_or_kg(tmp_path: Path):
    result, candidates = _candidates(); write_artifacts(result, tmp_path / "output")
    assert candidates and not any(path.suffix == ".ttl" for path in (tmp_path / "output").iterdir())
    assert [item.kind.value for item in EvidenceSchemaInducer().candidates_for_core(result)] == [item.candidate.kind.value for item in candidates]
