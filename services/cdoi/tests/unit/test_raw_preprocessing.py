import hashlib
import json
from pathlib import Path

import pytest

import cdoi.cli as cli
from cdoi.raw_preprocessing import (PreprocessingError, bridge_to_existing_core,
                                    load_manifest, process_dataset, write_artifacts)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"


def _result():
    return process_dataset(FIXTURE / "manifest.yaml")


def test_manifest_and_all_fixed_source_adapters_parse_with_expected_counts():
    result = _result()
    assert result.manifest.dataset_id == "demo_rca_001"
    assert (len(result.entities), len(result.relations), len(result.events), len(result.semantic_terms)) == (3, 3, 3, 3)
    assert {item.source_type for item in result.raw_records} == {"service_inventory_csv", "dependency_jsonl", "log_jsonl", "glossary_yaml", "deployment_change_csv", "metric_observation_csv", "trace_span_jsonl"}


def test_invalid_manifest_and_unknown_source_type_fail_closed(tmp_path: Path):
    path = tmp_path / "manifest.yaml"; path.write_text("dataset_id: x\nsources:\n  - id: x\n    type: arbitrary_api\n    path: x\n", encoding="utf-8")
    with pytest.raises(PreprocessingError, match="UNSUPPORTED_SOURCE_TYPE"):
        load_manifest(path)


def test_required_fields_duplicate_ids_and_unresolved_references_are_reported_not_dropped():
    result = _result(); statuses = [issue.status for issue in result.unresolved]
    assert "DUPLICATE_EXTERNAL_ID" in statuses and "INVALID_TIMESTAMP" in statuses
    assert statuses.count("UNKNOWN_ENTITY_REFERENCE") == 2
    unresolved_relation = next(item for item in result.relations if item.target_external_id == "unknown-service")
    assert unresolved_relation.resolution_status == "UNRESOLVED_REFERENCE"


def test_exact_id_correlation_is_conservative_and_never_fuzzy_merges():
    result = _result()
    assert next(item for item in result.events if item.service_external_id == "payment-service").correlation_status == "RESOLVED_EXACT_ID"
    assert next(item for item in result.events if item.service_external_id == "unknown-service").correlation_status == "UNRESOLVED_REFERENCE"
    assert {item.external_id for item in result.entities} == {"payment-service", "order-service", "database-service"}


def test_timestamp_normalization_is_timezone_aware_and_retains_original_value():
    event = next(item for item in _result().events if item.service_external_id == "order-service")
    assert event.original_timestamp.endswith("+07:00") and event.observed_at == "2026-09-18T10:05:00Z"


def test_ids_provenance_and_source_hashes_are_deterministic():
    first, second = _result(), _result()
    assert [item.evidence_id for item in first.raw_records] == [item.evidence_id for item in second.raw_records]
    assert first.source_files == second.source_files
    entity = first.entities[0]
    assert entity.provenance["raw_evidence_id"] == entity.evidence_id and entity.provenance["dataset_id"] == "demo_rca_001"
    assert entity.provenance["declared_dataset_timezone"] == "Asia/Ho_Chi_Minh"


def test_raw_inputs_stay_unchanged_and_generated_artifacts_are_deterministic(tmp_path: Path):
    source = FIXTURE / "inventory" / "services.csv"; before = hashlib.sha256(source.read_bytes()).hexdigest()
    first = write_artifacts(_result(), tmp_path / "one"); second = write_artifacts(_result(), tmp_path / "two")
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()
    assert first["artifacts"] == second["artifacts"]
    assert {path.name for path in (tmp_path / "one").iterdir()} == {"raw_evidence.jsonl", "entities.jsonl", "relations.jsonl", "events.jsonl", "changes.jsonl", "metrics.jsonl", "traces.jsonl", "semantic_terms.jsonl", "unresolved.jsonl", "schema_candidates.jsonl", "semantic_envelope.json", "provenance.json", "manifest.json"}


def test_glossary_only_envelope_reaches_existing_extractor_and_schema_boundary(tmp_path: Path):
    output = tmp_path / "output"; write_artifacts(_result(), output)
    graph, candidates = bridge_to_existing_core(output, "staging")
    assert sorted(entity.id for entity in graph.entities) == ["order_processing", "payment_gateway", "service_timeout"]
    assert {candidate.canonical_label for candidate in candidates if candidate.kind.value == "CLASS"} == {"Order Processing", "Payment Gateway", "Service Timeout"}
    assert "payment-service" not in {entity.id for entity in graph.entities}
    assert all("equivalent" not in relation.relation.casefold() for relation in _result().relations)


def test_artifacts_are_machine_readable_and_no_secret_fixture_fields_are_emitted(tmp_path: Path):
    output = tmp_path / "output"; report = write_artifacts(_result(), output)
    assert report["counts"]["unresolved"] == 21 and report["counts"]["metrics"] == 10 and report["counts"]["traces"] == 14
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8"))["schema_version"] == "cdoi_preprocessing_v1"
    assert "authorization" not in (output / "events.jsonl").read_text(encoding="utf-8").casefold()


def test_cli_supports_manifest_dry_run_without_changing_legacy_preprocess(capsys):
    assert cli.main(["preprocess", str(FIXTURE / "manifest.yaml"), "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["semantic_terms"] == 3
