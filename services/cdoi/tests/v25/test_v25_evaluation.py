import json
import shutil
from pathlib import Path

from cdoi.benchmarks import evaluate_alignment_cases
from cdoi.conceptualization import CachingLLMClient
from cdoi.embeddings import SentenceTransformerEmbeddingProvider
from cdoi.experiment_runner import ExperimentManifest, ExperimentRunner
from cdoi.external import ConceptPlacementAdapter, OAEIAlignmentAdapter
from cdoi.llm_evaluation import LLMAlignmentResponse, alignment_prompt
from cdoi.robustness import degrade_evidence, inject_noise


ROOT = Path(__file__).resolve().parents[2]


def runtime(tmp_path):
    root = tmp_path / "project"
    shutil.copytree(ROOT / "data", root / "data", ignore=shutil.ignore_patterns("external"))
    shutil.copytree(ROOT / "ontologies", root / "ontologies")
    shutil.copytree(ROOT / "experiments", root / "experiments")
    return root


def test_noise_and_evidence_transforms_are_deterministic_and_traceable():
    cases = json.loads((ROOT / "data/benchmarks/cdoi_bench/test.json").read_text(encoding="utf-8"))
    degraded = degrade_evidence(cases, "LabelOnly")
    assert degraded[0]["origin"]["case_id"] == cases[0]["case_id"]
    assert not any(degraded[0]["evidence_available"].values())
    assert inject_noise(cases, 20, 7) == inject_noise(cases, 20, 7)


def test_selective_metrics_include_counts_failure_taxonomy_and_intervals():
    cases = [{"case_id": "safe", "kind": "class", "expected_relation": "UNRESOLVED", "must_not_equivalent": True}, {"case_id": "match", "kind": "object_property", "expected_relation": "EQUIVALENT"}]
    metrics = evaluate_alignment_cases(cases, {"safe": "EQUIVALENT", "match": "EQUIVALENT"})
    assert metrics["false_merge_rate"] == 1.0
    assert metrics["sample_counts"]["total"] == 2
    assert metrics["failure_taxonomy"]["unsafe_equivalence"] == 1
    assert "accuracy_bootstrap_low" in metrics


def test_external_adapters_accept_normalized_offline_exports(tmp_path):
    oaei = tmp_path / "oaei"
    oaei.mkdir()
    (oaei / "cases.json").write_text(json.dumps([{ "case_id": "x", "split": "test", "kind": "object_property", "candidate": "hostedOn", "target": "runsOn", "expected_relation": "EQUIVALENT" }]), encoding="utf-8")
    assert OAEIAlignmentAdapter(oaei).load_split("test")[0]["kind"] == "object_property"
    placement = tmp_path / "placement"
    placement.mkdir()
    (placement / "test.json").write_text(json.dumps([{ "case_id": "p", "candidate": "Pod", "parent_id": "runtime", "candidate_parents": [{"id": "runtime", "label": "Runtime Environment"}, {"id": "party", "label": "Party"}] }]), encoding="utf-8")
    cases = ConceptPlacementAdapter(placement).load_split("test")
    metrics = ConceptPlacementAdapter.evaluate({"p": ["runtime", "party"]}, cases)
    assert metrics["top1_parent_accuracy"] == 1.0


def test_late_evidence_and_continual_runs_persist_without_colliding(tmp_path):
    root = runtime(tmp_path)
    runner = ExperimentRunner(root)
    late = runner.run(ExperimentManifest(experiment_id="late", task="late_evidence"))
    assert late["conservative"]["unsafe_premature_commitment_rate"] == 0.0
    manifest = ExperimentManifest(experiment_id="orders", task="continual_evolution")
    order = [["distributed_systems", "commerce", "logistics", "finance", "fintech", "telecom"]]
    first, second = runner.run_continual(manifest, order), runner.run_continual(manifest, order)
    assert first["run_id"] != second["run_id"]
    assert first["summary"]["ontology_structural_stability"] == 1.0


def test_real_embedding_adapter_is_mockable_and_cached(tmp_path):
    class FakeModel:
        def encode(self, values, normalize_embeddings=True):
            return [[1.0, 0.0] if value == "left" else [0.0, 1.0] for value in values]
    provider = SentenceTransformerEmbeddingProvider("fake", tmp_path, model=FakeModel())
    assert provider.similarity("left", "left") == 1.0
    assert provider.similarity("left", "left") == 1.0
    assert provider.metadata()["cache_hits"] >= 2


def test_llm_cache_replays_structured_response(tmp_path):
    class FakeClient:
        def __init__(self): self.calls = 0
        def structured_generate(self, prompt, schema):
            self.calls += 1
            return schema(status="MATCHED", relation="EQUIVALENT", target_id="x")
    fake = FakeClient()
    cached = CachingLLMClient(fake, tmp_path)
    prompt = alignment_prompt({"candidate": "Pod", "target": "Runtime Environment"}, "P3")
    cached.structured_generate(prompt, LLMAlignmentResponse)
    cached.structured_generate(prompt, LLMAlignmentResponse)
    assert fake.calls == 1
    assert cached.metrics()["cache_hits"] == 1
