import hashlib
import shutil
from pathlib import Path

from cdoi.raw_preprocessing import changes_for_entity, process_dataset, write_artifacts


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "preprocessing_demo"


def _result(): return process_dataset(FIXTURE / "manifest.yaml")


def test_change_csv_preserves_declared_transition_and_exact_target_correlation():
    changes = {item.change_id: item for item in _result().changes}
    deploy = changes["chg-001"]
    assert (deploy.change_type, deploy.version_before, deploy.version_after, deploy.correlation_status) == ("DEPLOYMENT", "1.4.2", "1.5.0", "RESOLVED_EXACT_ID")
    assert changes["chg-002"].config_before == "false" and changes["chg-002"].config_after == "true"
    assert changes["chg-004"].correlation_status == "UNRESOLVED_CHANGE_TARGET"


def test_change_time_and_rollback_are_explicit_noncausal_evidence():
    changes = {item.change_id: item for item in _result().changes}
    assert changes["chg-003"].rollback_of == "chg-001" and changes["chg-003"].rollback_status == "RESOLVED_CHANGE_REFERENCE"
    assert changes["chg-001"].observed_at == "2026-09-18T09:55:00Z"
    interval = changes_for_entity(tuple(changes.values()), "payment-service", "2026-09-18T09:55:00Z", "2026-09-18T10:20:00Z")
    assert [item.change_id for item in interval] == ["chg-001", "chg-003"]
    assert not hasattr(interval[0], "causal_score")


def test_invalid_changes_are_preserved_as_issues_and_do_not_create_schema_candidates(tmp_path: Path):
    result = _result(); statuses = {item.status for item in result.unresolved}
    report = write_artifacts(result, tmp_path / "out")
    assert {"INVALID_TIMESTAMP", "UNKNOWN_DECLARED_CHANGE_TYPE", "UNRESOLVED_CHANGE_TARGET"}.issubset(statuses)
    assert report["change_diagnostics"] == {"raw_change_records": 6, "valid_changes": 4, "invalid_changes": 2, "resolved_change_targets": 3, "unresolved_change_targets": 1, "change_types": {"CONFIG_CHANGE": 1, "DEPLOYMENT": 1, "RESTART": 1, "ROLLBACK": 1}, "rollback_references": 1, "invalid_rollback_references": 0}
    assert "OperationalChangeEvent" not in (tmp_path / "out" / "schema_candidates.jsonl").read_text(encoding="utf-8")


def test_change_ids_files_and_serialization_are_deterministic_and_input_read_only(tmp_path: Path):
    source = FIXTURE / "changes" / "deployments.csv"; before = hashlib.sha256(source.read_bytes()).hexdigest()
    first, second = _result(), _result()
    assert [item.evidence_id for item in first.changes] == [item.evidence_id for item in second.changes]
    one, two = write_artifacts(first, tmp_path / "one"), write_artifacts(second, tmp_path / "two")
    assert before == hashlib.sha256(source.read_bytes()).hexdigest() and one["artifacts"]["changes.jsonl"] == two["artifacts"]["changes.jsonl"]


def test_manifest_without_change_source_remains_valid_and_does_not_require_changes_artifact(tmp_path: Path):
    dataset = tmp_path / "dataset"; shutil.copytree(FIXTURE, dataset)
    manifest = (dataset / "manifest.yaml").read_text(encoding="utf-8")
    manifest = manifest.replace("  - id: deployment_changes\n    type: deployment_change_csv\n    path: changes/deployments.csv\n", "")
    (dataset / "manifest.yaml").write_text(manifest, encoding="utf-8")
    result = process_dataset(dataset / "manifest.yaml"); write_artifacts(result, tmp_path / "output")
    assert result.changes == () and not (tmp_path / "output" / "changes.jsonl").exists()
