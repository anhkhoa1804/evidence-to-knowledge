import importlib.util
import json
from pathlib import Path

import pytest


def _runner_module():
    path = Path(__file__).resolve().parents[2] / "tools" / "run_v3_phase2_12.py"
    specification = importlib.util.spec_from_file_location("phase212_runner_for_test", path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _candidate(case_id: str) -> dict:
    return {
        "schema_version": "v3_phase2_12_holdout_candidates_v1",
        "case_id": case_id,
        "variants": {name: {} for name in _runner_module().VARIANTS},
    }


def test_phase_a_freeze_requires_all_cases_and_rejects_prior_evaluation(tmp_path, monkeypatch):
    runner = _runner_module()
    monkeypatch.setattr(runner, "OUT", tmp_path / "phase212")
    monkeypatch.setattr(runner, "P211", tmp_path / "phase211")
    runner.P211.mkdir()
    (runner.P211 / "RULES.json").write_text("{}\n", encoding="utf-8")
    runner.OUT.mkdir()
    (runner.OUT / "EXPERIMENT_MANIFEST.json").write_text("{}\n", encoding="utf-8")
    candidates = runner.OUT / "HOLDOUT_CANDIDATES"
    candidates.mkdir()
    (candidates / "one.json").write_text(json.dumps(_candidate("one")), encoding="utf-8")

    with pytest.raises(RuntimeError, match="PHASE_A_CASE_ACCOUNTING_INCOMPLETE"):
        runner.phase_a_freeze(("one", "two"), [{"case_id": "one", "generation_status": "CANDIDATE_ARTIFACT_FROZEN"}], {"configuration": {}})

    (candidates / "two.json").write_text(json.dumps(_candidate("two")), encoding="utf-8")
    evaluation_dir = runner.OUT / "HOLDOUT_EVALUATIONS"
    evaluation_dir.mkdir()
    (evaluation_dir / "one.json").write_text("{}\n", encoding="utf-8")
    statuses = [
        {"case_id": "one", "generation_status": "CANDIDATE_ARTIFACT_FROZEN"},
        {"case_id": "two", "generation_status": "CANDIDATE_ARTIFACT_FROZEN"},
    ]
    with pytest.raises(RuntimeError, match="PHASE_A_FREEZE_REFUSES_PREEXISTING_GROUND_TRUTH_EVALUATIONS"):
        runner.phase_a_freeze(("one", "two"), statuses, {"configuration": {}})

    (evaluation_dir / "one.json").unlink()
    freeze = runner.phase_a_freeze(("one", "two"), statuses, {"configuration": {}})
    assert freeze["candidate_artifact_count"] == 2
    assert freeze["holdout_evaluations_empty"] is True
    assert (runner.OUT / "PHASE_A_FREEZE.json").is_file()
