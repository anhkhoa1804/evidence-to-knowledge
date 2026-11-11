import shutil
from pathlib import Path

from cdoi.experiment_runner import ExperimentManifest, ExperimentRunner


ROOT = Path(__file__).resolve().parents[2]


def runtime(tmp_path):
    root = tmp_path / "project"
    shutil.copytree(ROOT / "data", root / "data", ignore=shutil.ignore_patterns("external"))
    shutil.copytree(ROOT / "ontologies", root / "ontologies")
    (root / "experiments" / "configs").mkdir(parents=True)
    for config in (ROOT / "experiments" / "configs").glob("*.yaml"):
        shutil.copy2(config, root / "experiments" / "configs" / config.name)
    return root


def test_manifest_runner_persists_reproducible_baseline_comparison(tmp_path):
    root = runtime(tmp_path)
    runner = ExperimentRunner(root)
    lexical = runner.run(ExperimentManifest.load(root / "experiments/configs/b0_lexical.yaml"))
    full = runner.run(ExperimentManifest.load(root / "experiments/configs/b6_full_cdoi.yaml"))
    assert lexical["dataset"]["sha256"]
    assert full["metrics"]["false_merge_rate"] <= lexical["metrics"]["false_merge_rate"]
    assert (root / "experiments/outputs/b6_full_cdoi" / full["run_id"] / "result.json").exists()
    assert full["operational"]["deterministic"]


def test_continual_runner_reports_stability_across_four_orders(tmp_path):
    root = runtime(tmp_path)
    orders = [
        ["distributed_systems", "commerce", "logistics", "finance", "fintech", "telecom"],
        ["commerce", "logistics", "finance", "fintech", "telecom", "distributed_systems"],
        ["finance", "fintech", "telecom", "distributed_systems", "commerce", "logistics"],
        ["telecom", "distributed_systems", "commerce", "finance", "logistics", "fintech"],
    ]
    result = ExperimentRunner(root).run_continual(ExperimentManifest.load(root / "experiments/configs/continual_orders.yaml"), orders)
    assert result["summary"]["run_count"] == 4
    assert "decision_stability_mean" in result["summary"]


def test_downstream_controlled_comparison_and_competency_questions(tmp_path):
    root = runtime(tmp_path)
    result = ExperimentRunner(root).run_downstream(ExperimentManifest.load(root / "experiments/configs/downstream.yaml"))
    assert result["variants"]["full_cdoi"]["impact_f1"] >= result["variants"]["domain_aligned"]["impact_f1"]
    assert result["cq_pass_rate"] == 1.0
    assert result["staging_leakage_rate"] == 0.0
