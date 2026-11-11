from pathlib import Path

from cdoi.models import AlignmentRelation
from cdoi.pipeline import demo
import cdoi.cli as cli


ROOT = Path(__file__).resolve().parents[2]


def _copy_demo_runtime(runtime: Path) -> None:
    """Copy only application fixtures; optional external research caches stay out of demo tests."""
    import shutil
    shutil.copytree(ROOT / "ontologies", runtime / "ontologies")
    shutil.copytree(ROOT / "data", runtime / "data", ignore=shutil.ignore_patterns("external"))


def test_demo_creates_versions_kg_and_promotion_proposal(tmp_path):
    # The fixture project is read-only; runtime artifacts live in an isolated copy-like root.
    runtime = tmp_path / "project"
    _copy_demo_runtime(runtime)
    results, promotions, kg = demo(runtime)
    assert len(results) == 6
    assert kg.exists()
    assert (runtime / "data/ontology_versions/v000/manifest.json").exists()
    assert promotions and promotions[0].action.value == "PROMOTE_TO_SHARED"
    pod = results[0].decisions[0]
    assert pod.relation == AlignmentRelation.SUBCLASS_OF


def test_ingestion_order_is_measurable(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    for runtime in (first, second):
        _copy_demo_runtime(runtime)
    a_results, a_promotions, _ = demo(first, ["distributed_systems", "finance", "logistics", "fintech", "telecom"])
    b_results, b_promotions, _ = demo(second, ["finance", "fintech", "distributed_systems", "logistics", "telecom"])
    assert len(a_results) == len(b_results)
    assert len(a_promotions) == len(b_promotions)
    assert (first / "data/ontology_versions").exists()


def test_cli_demo_smoke(capsys, tmp_path, monkeypatch):
    runtime = tmp_path / "project"
    _copy_demo_runtime(runtime)
    monkeypatch.setattr(cli, "project_root", lambda: runtime)
    assert cli.main(["demo"]) == 0
    assert "promotion_proposals" in capsys.readouterr().out
