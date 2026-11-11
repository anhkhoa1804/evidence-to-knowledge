from pathlib import Path

from rdflib import Graph, Literal, RDF, URIRef

import cdoi.cli as cli
from cdoi.kg_evaluation import APPROVED_VERSION, evaluate_kg_safety


ROOT = Path(__file__).resolve().parents[2]


def test_kg_quality_reports_provenance_and_zero_staging_leakage():
    canonical, staging = Graph(), Graph()
    instance = URIRef("https://example.org/instance/1")
    canonical.add((instance, RDF.type, URIRef("https://example.org/Class")))
    canonical.add((instance, APPROVED_VERSION, Literal("v001")))
    staging.add((URIRef("https://example.org/instance/pending"), RDF.type, URIRef("https://example.org/PendingClass")))
    report = evaluate_kg_safety(canonical, staging)
    assert report["provenance_coverage"] == 1.0
    assert report["canonical_staging_leakage_rate"] == 0.0


def test_cli_experiment_manifest_smoke(tmp_path, monkeypatch, capsys):
    import shutil
    root = tmp_path / "project"
    shutil.copytree(ROOT / "data", root / "data", ignore=shutil.ignore_patterns("external"))
    shutil.copytree(ROOT / "ontologies", root / "ontologies")
    shutil.copytree(ROOT / "experiments", root / "experiments")
    monkeypatch.setattr(cli, "project_root", lambda: root)
    assert cli.main(["experiment", "experiments/configs/b6_full_cdoi.yaml"]) == 0
    assert "false_merge_rate" in capsys.readouterr().out
