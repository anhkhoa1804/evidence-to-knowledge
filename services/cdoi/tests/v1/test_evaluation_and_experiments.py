from pathlib import Path

from cdoi.evaluation import evaluate_gold
from cdoi.experiments import order_sensitivity_experiment
from cdoi.retrieval import HashingEmbeddingProvider


ROOT = Path(__file__).resolve().parents[2]


def test_gold_benchmark_reports_property_bridge_and_false_merge_metrics():
    expected = {
        "same-label-different-semantics": "UNRESOLVED",
        "bank-not-user": "UNRESOLVED",
        "pod-placement": "SUBCLASS_OF",
        "cold-chain-new": "NEW_CONCEPT",
        "party-role-compatible": "SUBCLASS_OF",
        "object-property": "EQUIVALENT",
        "data-property": "NEW_CONCEPT",
        "bridge": "BRIDGE",
        "unsafe-equivalence": "UNRESOLVED",
    }
    metrics = evaluate_gold(expected, ROOT / "data/benchmark/gold.json")
    assert metrics["alignment_accuracy"] == 1.0
    assert metrics["property_alignment_accuracy"] == 1.0
    assert metrics["bridge_mapping_precision"] == 1.0
    assert metrics["false_merge_rate"] == 0.0


def test_order_experiment_reports_four_permutations(tmp_path):
    orders = [
        ["distributed_systems", "commerce", "logistics", "finance", "fintech", "telecom"],
        ["commerce", "logistics", "distributed_systems", "finance", "fintech", "telecom"],
        ["finance", "fintech", "commerce", "logistics", "telecom", "distributed_systems"],
        ["telecom", "distributed_systems", "finance", "commerce", "fintech", "logistics"],
    ]
    reports = order_sensitivity_experiment(ROOT, tmp_path, orders)
    assert len(reports) == 4
    assert all("final_module_triples" in report and "bridge_mappings" in report for report in reports)


def test_deterministic_embedding_baseline_exposes_nonopaque_score():
    provider = HashingEmbeddingProvider()
    assert provider.similarity("runtime pod", "pod runtime") == 1.0
