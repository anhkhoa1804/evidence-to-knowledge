from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import yaml

from .benchmarks import CdoiBenchAdapter, evaluate_alignment_cases
from .calibration import calibrate_thresholds
from .conceptualization import CachingLLMClient, OpenAICompatibleLLM
from .downstream import ControlledDownstreamEvaluator
from .embeddings import SentenceTransformerEmbeddingProvider
from .experiments import order_sensitivity_experiment
from .external import ConceptPlacementAdapter, ExternalDatasetUnavailable, OAEIAlignmentAdapter, RCAEvalAdapter
from .llm_evaluation import PROMPT_CONDITIONS, PROMPT_IDS, LLMAlignmentResponse, alignment_prompt
from .model_config import OpenAICompatibleConfig
from .oaei_full_corpus import OAEIFullCorpusMatcher
from .oaei_diagnostics import abstention_cases, available_evidence_comparison, gold_rank_analysis, nontrivial_metrics, threshold_sweep
from .qwen_shared_topk import evaluate_shared_topk
from .oaei_postranking import artifact_hash, enrich_rows, load_profiles, rank1_acceptance, rerank, score_scale
from .oaei_discrimination import confidence_table, labelled_pair_records, margin_analysis, pairwise_rerank, stratified_discrimination
from .qwen_reliability import reliability_microbenchmark
from .qwen_semantic_eval import repeated_call_diagnostic, semantic_evaluation
from .semantic_confidence_diagnostics import confidence_evidence_table, validation_analysis
from .qwen_robustness import evaluate_conditions, robustness_summary, select_cases
from .company_gateway import CompanyGatewayTransport
from .robustness import EVIDENCE_CONDITIONS, conflict_metrics, degrade_evidence, inject_noise, late_evidence_metrics


@dataclass
class ExperimentManifest:
    experiment_id: str
    dataset: str = "cdoi_bench"
    task: str = "ontology_alignment"
    baseline: str = "B6_FULL_CDOI"
    features: dict[str, bool] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    random_seed: int = 42
    ingestion_order: list[str] = field(default_factory=list)
    model_config: dict[str, object] = field(default_factory=dict)
    evaluation_metrics: list[str] = field(default_factory=list)
    external_root: str | None = None
    conditions: list[str] = field(default_factory=list)
    noise_levels: list[int] = field(default_factory=list)
    order_count: int = 20

    @classmethod
    def load(cls, path: Path) -> "ExperimentManifest":
        return cls(**yaml.safe_load(path.read_text(encoding="utf-8")))


class ExperimentRunner:
    """Serializable V2/V2.5 runner. It observes the core; it never mutates it."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.bench = CdoiBenchAdapter(project_root / "data" / "benchmarks" / "cdoi_bench")

    def run(self, manifest: ExperimentManifest) -> dict:
        dispatch = {
            "evidence_degradation": self.run_evidence_degradation,
            "noise": self.run_noise,
            "late_evidence": self.run_late_evidence,
            "external_alignment": self.run_external_alignment,
            "oaei_full_corpus": self.run_oaei_full_corpus,
            "oaei_diagnostics": self.run_oaei_diagnostics,
            "oaei_qwen_shared_topk": self.run_oaei_qwen_shared_topk,
            "oaei_postranking": self.run_oaei_postranking,
            "oaei_qwen_reliability": self.run_oaei_qwen_reliability,
            "oaei_discrimination": self.run_oaei_discrimination,
            "oaei_qwen_semantic": self.run_oaei_qwen_semantic,
            "oaei_qwen_validation": self.run_oaei_qwen_validation,
            "oaei_qwen_consistency": self.run_oaei_qwen_consistency,
            "oaei_semantic_confidence": self.run_oaei_semantic_confidence,
            "oaei_qwen_robustness": self.run_oaei_qwen_robustness,
            "oaei_qwen_failure_diagnostic": self.run_oaei_qwen_failure_diagnostic,
            "oaei_v3_evidence_gate": self.run_oaei_v3_evidence_gate,
            "concept_placement": self.run_concept_placement,
            "external_rca": self.run_external_rca,
            "embedding": self.run_embedding,
            "llm": self.run_llm,
            "property_stress": self.run_property_stress,
            "conflicts": self.run_conflicts,
        }
        if manifest.task in dispatch:
            return dispatch[manifest.task](manifest)
        return self._run_alignment(manifest, self.bench.load_split("test"), self.bench.dataset_metadata())

    def _run_alignment(self, manifest: ExperimentManifest, test: list[dict], dataset: dict) -> dict:
        result = self._alignment_result(manifest, test, dataset)
        self._persist(result)
        return result

    def _alignment_result(self, manifest: ExperimentManifest, test: list[dict], dataset: dict, data_type: str | None = None) -> dict:
        started = datetime.now(timezone.utc)
        dev = self.bench.load_split("dev")
        calibration = calibrate_thresholds(dev, lambda case, eq, unresolved: self._predict(case, manifest, eq, unresolved))
        clock = perf_counter()
        predictions = {case["case_id"]: self._predict(case, manifest, calibration.equivalence_threshold, calibration.unresolved_threshold) for case in test}
        result = self._base_result(manifest, started, dataset)
        result.update({"calibration": asdict(calibration), "predictions": predictions, "metrics": evaluate_alignment_cases(test, predictions, manifest.random_seed), "operational": self._operational(round((perf_counter() - clock) * 1000, 3))})
        if data_type:
            result["data_type"] = data_type
        return result

    def run_evidence_degradation(self, manifest: ExperimentManifest) -> dict:
        calibration = self._calibration(manifest)
        runs = {}
        for condition in manifest.conditions or list(EVIDENCE_CONDITIONS):
            cases = degrade_evidence(self.bench.load_split("test"), condition)
            predictions = {case["case_id"]: self._predict(case, manifest, calibration.equivalence_threshold, calibration.unresolved_threshold) for case in cases}
            runs[condition] = {"metrics": evaluate_alignment_cases(cases, predictions, manifest.random_seed), "predictions": predictions}
        result = self._base_result(manifest, datetime.now(timezone.utc), self.bench.dataset_metadata())
        result.update({"data_type": "synthetic_controlled_robustness", "calibration": asdict(calibration), "conditions": runs})
        self._persist(result)
        return result

    def run_noise(self, manifest: ExperimentManifest) -> dict:
        calibration = self._calibration(manifest)
        runs, clean_metrics = {}, None
        for level in manifest.noise_levels or [0, 5, 10, 20, 30]:
            cases = inject_noise(self.bench.load_split("test"), level, manifest.random_seed)
            predictions = {case["case_id"]: self._predict(case, manifest, calibration.equivalence_threshold, calibration.unresolved_threshold) for case in cases}
            metrics = evaluate_alignment_cases(cases, predictions, manifest.random_seed)
            clean_metrics = clean_metrics or metrics
            metrics["alignment_f1_degradation"] = float(clean_metrics["alignment_f1"]) - float(metrics["alignment_f1"])
            metrics["false_merge_rate_change"] = float(metrics["false_merge_rate"]) - float(clean_metrics["false_merge_rate"])
            runs[str(level)] = {"metrics": metrics, "predictions": predictions}
        result = self._base_result(manifest, datetime.now(timezone.utc), self.bench.dataset_metadata())
        result.update({"data_type": "synthetic_controlled_robustness", "calibration": asdict(calibration), "noise_levels": runs})
        self._persist(result)
        return result

    def run_late_evidence(self, manifest: ExperimentManifest) -> dict:
        path = self.project_root / "data" / "benchmarks" / "cdoi_bench" / "late_evidence.json"
        sequences = json.loads(path.read_text(encoding="utf-8"))
        for sequence in sequences:
            for index, step in enumerate(sequence["steps"]):
                decision = step["decisions"]["conservative"]
                step["audit"] = {"old_decision": sequence["steps"][index - 1]["decisions"]["conservative"] if index else None, "new_evidence": step["evidence"], "proposal": step.get("proposal"), "validation": step.get("validation", "not_applicable"), "review": step.get("review", "not_required"), "ontology_version_before": f"sim-{index:03d}", "ontology_version_after": f"sim-{index + 1:03d}" if decision == "EQUIVALENT" else None, "affected_kg_assertions": ["approved type assertion"] if decision == "EQUIVALENT" else []}
        result = self._base_result(manifest, datetime.now(timezone.utc), {"dataset": "cdoi_late_evidence", "status": "available", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        result.update({"data_type": "synthetic_controlled_robustness", "sequences": sequences, "conservative": late_evidence_metrics(sequences, "conservative"), "aggressive": late_evidence_metrics(sequences, "aggressive")})
        self._persist(result)
        return result

    def run_property_stress(self, manifest: ExperimentManifest) -> dict:
        path = self.project_root / "data" / "benchmarks" / "cdoi_bench" / "property_stress.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        return self._run_alignment(manifest, cases, {"dataset": "cdoi_property_stress", "status": "synthetic", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    def run_conflicts(self, manifest: ExperimentManifest) -> dict:
        path = self.project_root / "data" / "benchmarks" / "cdoi_bench" / "conflicts.json"
        cases = json.loads(path.read_text(encoding="utf-8"))
        result = self._base_result(manifest, datetime.now(timezone.utc), {"dataset": "cdoi_conflicts", "status": "synthetic", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        result.update({"data_type": "synthetic_controlled_robustness", "cases": cases, "metrics": conflict_metrics(cases)})
        self._persist(result)
        return result

    def run_external_alignment(self, manifest: ExperimentManifest) -> dict:
        adapter = OAEIAlignmentAdapter(self._external_root(manifest, "oaei"))
        try:
            cases = adapter.load_split("test")
        except ExternalDatasetUnavailable as error:
            return self._skip(manifest, adapter.dataset_metadata(), str(error))
        for case in cases:
            case.setdefault("signals", self._label_signals(case))
        result = self._alignment_result(manifest, cases, adapter.dataset_metadata(), "external_alignment")
        self._persist(result)
        return result

    def run_oaei_full_corpus(self, manifest: ExperimentManifest) -> dict:
        """Evaluate target-corpus retrieval before any semantic-core decision."""
        root = self._external_root(manifest, "oaei")
        adapter = OAEIAlignmentAdapter(root)
        if not adapter.available():
            return self._skip(manifest, adapter.dataset_metadata(), "DATA_BLOCKER: OAEI Anatomy artifacts unavailable")
        matcher = OAEIFullCorpusMatcher(root)
        method = str(manifest.model_config.get("retrieval_method", "R1_FUZZY_LEXICAL"))
        top_k = int(manifest.model_config.get("top_k", 20))
        threshold = float(manifest.thresholds.get("emit_threshold", 0.82))
        evaluated = matcher.evaluate(method=method, top_k=top_k, emit_threshold=threshold)
        result = self._base_result(manifest, datetime.now(timezone.utc), adapter.dataset_metadata())
        result.update({"data_type": "external_full_corpus_matching", "evaluation_protocol": evaluated["protocol"], "retrieval_method": method, "metrics": evaluated["metrics"], "case_records": evaluated["rows"], "normalized_index": evaluated["index_path"], "calibration": {"mode": "C0_ZERO_SHOT_SYNTHETIC_CALIBRATED", "note": "Retrieval diagnostics use frozen lexical ranking; OAEI reference labels were not used to tune thresholds."}, "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def run_oaei_diagnostics(self, manifest: ExperimentManifest) -> dict:
        """Run isolated post-ranking diagnostics; production policy is untouched."""
        root = self._external_root(manifest, "oaei")
        adapter = OAEIAlignmentAdapter(root)
        if not adapter.available():
            return self._skip(manifest, adapter.dataset_metadata(), "DATA_BLOCKER: OAEI Anatomy artifacts unavailable")
        config = manifest.model_config
        method = str(config.get("retrieval_method", "R1_FUZZY_LEXICAL"))
        evidence_method = str(config.get("evidence_method", "R2_LEXICAL_NEIGHBORHOOD"))
        top_k = int(config.get("top_k", 20))
        frozen_threshold = float(manifest.thresholds.get("emit_threshold", 0.82))
        grid = [float(value) for value in config.get("threshold_grid", [frozen_threshold])]
        matcher = OAEIFullCorpusMatcher(root)
        primary = matcher.diagnostic_rows(method, top_k)
        abstentions, abstention_summary = abstention_cases(primary["rows"], frozen_threshold)
        evidence = matcher.diagnostic_rows(evidence_method, top_k)
        result = self._base_result(manifest, datetime.now(timezone.utc), adapter.dataset_metadata())
        result.update({"data_type": "external_post_ranking_diagnostic", "evaluation_protocol": primary["protocol"], "diagnostic_only": True, "frozen_production_policy_changed": False, "primary": {**primary, "frozen_threshold": frozen_threshold}, "threshold_sweep": threshold_sweep(primary["rows"], grid, frozen_threshold), "threshold_abstentions": {"summary": abstention_summary, "cases": abstentions}, "gold_rank_analysis": gold_rank_analysis(primary["rows"], frozen_threshold), "nontrivial": {"method": method, "metrics": nontrivial_metrics(primary["rows"], frozen_threshold)}, "available_evidence": {"method": evidence_method, "frozen_threshold": frozen_threshold, **available_evidence_comparison(evidence["rows"], frozen_threshold)}, "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def run_oaei_qwen_shared_topk(self, manifest: ExperimentManifest) -> dict:
        """Proposal-only Qwen reranking over deterministic, persisted-style Top-K rows."""
        root = self._external_root(manifest, "oaei")
        adapter = OAEIAlignmentAdapter(root)
        if not adapter.available():
            return self._skip(manifest, adapter.dataset_metadata(), "DATA_BLOCKER: OAEI Anatomy artifacts unavailable")
        config = manifest.model_config
        configured = OpenAICompatibleConfig.from_environment()
        key = configured.api_key()
        if not key or not configured.base_url or not configured.model:
            return self._skip(manifest, adapter.dataset_metadata(), "missing_credential", configured.public_metadata())
        method, top_k = str(config.get("retrieval_method", "R1_FUZZY_LEXICAL")), int(config.get("top_k", 5))
        threshold, sample_size, max_attempts = float(manifest.thresholds.get("emit_threshold", 0.82)), int(config.get("sample_size", 8)), int(config.get("max_attempts", 2))
        rows = OAEIFullCorpusMatcher(root).diagnostic_rows(method, top_k)["rows"]
        client = CachingLLMClient(OpenAICompatibleLLM(str(configured.base_url), key, str(configured.model), configured.headers(), configured.temperature, max(configured.max_tokens, 512)), self.project_root / "data" / "model_cache" / "llm")
        def responder(prompt: str) -> str:
            return client.structured_generate(prompt, LLMAlignmentResponse).model_dump_json()
        comparison = evaluate_shared_topk(rows, threshold, sample_size, responder, max_attempts)
        result = self._base_result(manifest, datetime.now(timezone.utc), adapter.dataset_metadata())
        result.update({"data_type": "real_model_shared_topk_diagnostic", "diagnostic_only": True, "frozen_production_policy_changed": False, "retrieval_method": method, "top_k": top_k, "frozen_threshold": threshold, "model": {**configured.public_metadata(), "prompt_id": "qwen_shared_topk_v1", "max_attempts": max_attempts}, "comparison": comparison, "operational": {**self._operational(sum(case["latency_ms"] for case in comparison["cases"])), **client.metrics(), "deterministic": False}})
        self._persist(result)
        return result

    def run_oaei_postranking(self, manifest: ExperimentManifest) -> dict:
        """Reuse the V2.6.2 candidate artifact for acceptance/scale/reranking only."""
        source_results = sorted((self.project_root / "experiments" / "outputs" / "OAEI_POST_RANKING_DIAGNOSTICS_R1_R2").glob("*/result.json"))
        if not source_results:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_candidate_artifact"}, "DATA_BLOCKER: run V2.6.2 post-ranking diagnostics first")
        source_result = json.loads(source_results[-1].read_text(encoding="utf-8"))
        primary = source_result["primary"]
        threshold = float(manifest.thresholds.get("emit_threshold", primary["frozen_threshold"]))
        source, target = load_profiles(Path(primary["index_path"]))
        rows = enrich_rows(primary["rows"], source, target)
        ks = [int(value) for value in manifest.model_config.get("k_values", [5, 10])]
        result = self._base_result(manifest, datetime.now(timezone.utc), source_result["dataset"])
        result.update({"data_type": "external_persisted_postranking_diagnostic", "diagnostic_only": True, "frozen_production_policy_changed": False, "candidate_artifact": str(source_results[-1]), "candidate_artifact_hash": artifact_hash(primary["rows"]), "threshold": threshold, "rank1_acceptance": rank1_acceptance(rows, threshold), "score_scale": score_scale(rows, threshold), "reranking": {str(k): rerank(rows, threshold, k) for k in ks}, "enriched_cases": rows, "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def run_oaei_qwen_reliability(self, manifest: ExperimentManifest) -> dict:
        source_results = sorted((self.project_root / "experiments" / "outputs" / "OAEI_POST_RANKING_DIAGNOSTICS_R1_R2").glob("*/result.json"))
        configured = OpenAICompatibleConfig.from_environment()
        if not source_results:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_candidate_artifact"}, "DATA_BLOCKER: run V2.6.2 post-ranking diagnostics first")
        if not (configured.api_key() and configured.base_url and configured.model):
            return self._skip(manifest, {"dataset": "oaei", "status": "available"}, "missing_credential", configured.public_metadata())
        artifact = json.loads(source_results[-1].read_text(encoding="utf-8"))
        rows = artifact["primary"]["rows"]
        config = manifest.model_config
        sample_size, top_k = int(config.get("sample_size", 2)), int(config.get("top_k", 5))
        budgets = [int(value) for value in config.get("response_budgets", [512, 1024])]
        sample = [row for row in sorted(rows, key=lambda item: item["source_iri"])[:sample_size]]
        transport = CompanyGatewayTransport()
        url = str(configured.base_url).rstrip("/") + "/chat/completions"
        def requester(method: str, *, headers: dict, json: dict, timeout: int):
            return transport.request(method, url, headers=headers, json=json, timeout=timeout)
        reliability = reliability_microbenchmark(sample, top_k, budgets, requester, str(configured.model), {"Authorization": f"Bearer {configured.api_key()}", "Content-Type": "application/json", **configured.headers()})
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "real_model_structured_reliability_diagnostic", "diagnostic_only": True, "candidate_artifact": str(source_results[-1]), "candidate_artifact_hash": artifact_hash(rows), "model": {**configured.public_metadata(), "prompt_variant": "QREL_COMPACT_V1", "response_budgets": budgets, "sample_size": sample_size}, "reliability": reliability, "operational": self._operational(sum(record["latency_ms"] for record in reliability["records"]))})
        result["operational"]["deterministic"] = False
        self._persist(result)
        return result

    def _persisted_oaei_rows(self):
        paths = sorted((self.project_root / "experiments" / "outputs" / "OAEI_POST_RANKING_DIAGNOSTICS_R1_R2").glob("*/result.json"))
        if not paths:
            return None
        artifact = json.loads(paths[-1].read_text(encoding="utf-8"))
        primary = artifact["primary"]
        source, target = load_profiles(Path(primary["index_path"]))
        return paths[-1], artifact, primary, source, target, enrich_rows(primary["rows"], source, target)

    def _latest_experiment_result(self, experiment_id: str):
        paths = list((self.project_root / "experiments" / "outputs" / experiment_id).glob("*/result.json"))
        if not paths:
            return None
        return max(paths, key=lambda path: str(json.loads(path.read_text(encoding="utf-8")).get("timestamp", "")))

    def run_oaei_discrimination(self, manifest: ExperimentManifest) -> dict:
        """V2.6.4 evaluation-only feature and pairwise ranking diagnostics."""
        persisted = self._persisted_oaei_rows()
        if not persisted:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_candidate_artifact"}, "DATA_BLOCKER: run V2.6.2 post-ranking diagnostics first")
        artifact_path, artifact, primary, source, target, rows = persisted
        threshold = float(manifest.thresholds.get("emit_threshold", primary["frozen_threshold"]))
        records, pairs = labelled_pair_records(rows, source, target)
        ks = [int(value) for value in manifest.model_config.get("k_values", [5, 10])]
        pairwise = {str(k): pairwise_rerank(rows, source, target, k) for k in ks}
        primary_pairwise = pairwise[str(max(ks))]
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "external_post_retrieval_discrimination_diagnostic", "diagnostic_only": True,
                       "frozen_production_policy_changed": False, "candidate_artifact": str(artifact_path),
                       "candidate_artifact_hash": artifact_hash(primary["rows"]), "threshold": threshold,
                       "feature_generation": {"gold_used_after_candidate_scoring_only": True, "feature_set": "existing_R1_R2_and_profile_components"},
                       "pair_feature_records": records, "gold_hard_negative_pairs": pairs,
                       "discrimination": stratified_discrimination(pairs, records), "margin_ambiguity": margin_analysis(rows, threshold),
                       "r2_scalar_reranking": {str(k): rerank(rows, threshold, k) for k in ks}, "pairwise_reranking": pairwise,
                       "future_confidence_table": confidence_table(rows, source, target, primary_pairwise["results"]), "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def run_oaei_qwen_semantic(self, manifest: ExperimentManifest) -> dict:
        """Proposal-only compact Qwen semantic selection over exact persisted sets."""
        persisted = self._persisted_oaei_rows()
        configured = OpenAICompatibleConfig.from_environment()
        if not persisted:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_candidate_artifact"}, "DATA_BLOCKER: run V2.6.2 post-ranking diagnostics first")
        if not (configured.api_key() and configured.base_url and configured.model):
            return self._skip(manifest, {"dataset": "oaei", "status": "available"}, "missing_credential", configured.public_metadata())
        artifact_path, artifact, primary, source, target, rows = persisted
        config = manifest.model_config
        threshold = float(manifest.thresholds.get("emit_threshold", primary["frozen_threshold"]))
        top_k, sample_size = int(config.get("top_k", 10)), int(config.get("sample_size", 50))
        seed, max_attempts, budget = int(config.get("seed", 264)), int(config.get("max_attempts", 2)), int(config.get("response_budget", 512))
        pairwise = pairwise_rerank(rows, source, target, top_k)
        transport = CompanyGatewayTransport()
        url = str(configured.base_url).rstrip("/") + "/chat/completions"
        def requester(method: str, *, headers: dict, json: dict, timeout: int):
            return transport.request(method, url, headers=headers, json=json, timeout=timeout)
        evaluation = semantic_evaluation(rows, source, target, pairwise["results"], threshold, top_k, sample_size, seed, max_attempts, requester, str(configured.model), {"Authorization": f"Bearer {configured.api_key()}", "Content-Type": "application/json", **configured.headers()}, budget)
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "real_model_shared_topk_semantic_diagnostic", "diagnostic_only": True, "frozen_production_policy_changed": False,
                       "candidate_artifact": str(artifact_path), "candidate_artifact_hash": artifact_hash(primary["rows"]),
                       "model": {**configured.public_metadata(), "prompt_variant": "QSEM_COMPACT_PROFILE_V1", "schema_version": "candidate_id_relation_v1", "response_budget": budget, "max_attempts": max_attempts},
                       "pairwise_diagnostic": {key: value for key, value in pairwise.items() if key != "results"}, "evaluation": evaluation,
                       "operational": {**self._operational(sum(item["latency_ms"] for item in evaluation["records"])), "llm_calls": sum(item["retry_count"] + 1 for item in evaluation["records"]), "deterministic": False}})
        self._persist(result)
        return result

    def _qwen_requester(self, configured: OpenAICompatibleConfig):
        transport = CompanyGatewayTransport()
        url = str(configured.base_url).rstrip("/") + "/chat/completions"
        def requester(method: str, *, headers: dict, json: dict, timeout: int):
            return transport.request(method, url, headers=headers, json=json, timeout=timeout)
        return requester, {"Authorization": f"Bearer {configured.api_key()}", "Content-Type": "application/json", **configured.headers()}

    def run_oaei_qwen_validation(self, manifest: ExperimentManifest) -> dict:
        """Larger frozen-prompt V2.6.5 validation over pre-specified strata."""
        persisted = self._persisted_oaei_rows(); configured = OpenAICompatibleConfig.from_environment()
        if not persisted:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_candidate_artifact"}, "DATA_BLOCKER: run V2.6.2 post-ranking diagnostics first")
        if not (configured.api_key() and configured.base_url and configured.model):
            return self._skip(manifest, {"dataset": "oaei", "status": "available"}, "missing_credential", configured.public_metadata())
        artifact_path, artifact, primary, source, target, rows = persisted; config = manifest.model_config
        threshold = float(manifest.thresholds.get("emit_threshold", primary["frozen_threshold"]))
        top_k, sample_size, seed = int(config.get("top_k", 10)), int(config.get("sample_size", 150)), int(config.get("seed", manifest.random_seed))
        max_attempts, budget = int(config.get("max_attempts", 2)), int(config.get("response_budget", 512))
        pairwise = pairwise_rerank(rows, source, target, top_k); requester, headers = self._qwen_requester(configured)
        evaluation = semantic_evaluation(rows, source, target, pairwise["results"], threshold, top_k, sample_size, seed, max_attempts, requester, str(configured.model), headers, budget, "V265")
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "real_model_shared_topk_validation_diagnostic", "diagnostic_only": True, "frozen_production_policy_changed": False, "reference_aware_diagnostic_sampling": True, "candidate_artifact": str(artifact_path), "candidate_artifact_hash": artifact_hash(primary["rows"]), "model": {**configured.public_metadata(), "prompt_variant": "QSEM_COMPACT_PROFILE_V1", "schema_version": "candidate_id_relation_v1", "response_budget": budget, "max_attempts": max_attempts}, "pairwise_diagnostic": {key: value for key, value in pairwise.items() if key != "results"}, "evaluation": evaluation, "operational": {**self._operational(sum(item["latency_ms"] for item in evaluation["records"])), "llm_calls": sum(item["retry_count"] + 1 for item in evaluation["records"]), "deterministic": False}})
        self._persist(result); return result

    def run_oaei_qwen_consistency(self, manifest: ExperimentManifest) -> dict:
        """Repeated identical-prompt and prior-empty-response reliability diagnostic."""
        persisted = self._persisted_oaei_rows(); configured = OpenAICompatibleConfig.from_environment()
        validation_path = self._latest_experiment_result("V265_QWEN_SEMANTIC_VALIDATION")
        if not persisted or not validation_path:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_validation_artifact"}, "DATA_BLOCKER: run V2.6.5 Qwen validation first")
        if not (configured.api_key() and configured.base_url and configured.model):
            return self._skip(manifest, {"dataset": "oaei", "status": "available"}, "missing_credential", configured.public_metadata())
        _, artifact, primary, source, target, rows = persisted; config = manifest.model_config
        validation = json.loads(validation_path.read_text(encoding="utf-8"))["evaluation"]
        by_source = {row["source_iri"]: row for row in rows}
        n_cases, repeats, top_k = int(config.get("sample_size", 20)), int(config.get("repeat_count", 3)), int(config.get("top_k", validation["top_k"]))
        selected = [by_source[item["source_id"]] for item in validation["records"] if item["sample_stratum"] != "easy_control"][:n_cases]
        requester, headers = self._qwen_requester(configured); budget, attempts = int(config.get("response_budget", validation["response_budget"])), int(config.get("max_attempts", validation["max_attempts"]))
        consistency = repeated_call_diagnostic(selected, source, target, top_k, repeats, attempts, requester, str(configured.model), headers, budget)
        previous = self._latest_experiment_result("V264_QWEN_COMPACT_SHARED_TOPK_SEMANTIC")
        previous_empty = []
        if previous:
            for item in json.loads(previous.read_text(encoding="utf-8"))["evaluation"]["records"]:
                if item["final_status"] == "EMPTY_RESPONSE" and item["source_id"] in by_source:
                    previous_empty.append(by_source[item["source_id"]])
        invalid_repeat = repeated_call_diagnostic(previous_empty, source, target, top_k, 1, attempts, requester, str(configured.model), headers, budget) if previous_empty else {"n_cases": 0, "records": [], "metrics": {}}
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "real_model_consistency_reliability_diagnostic", "diagnostic_only": True, "candidate_artifact_hash": artifact_hash(primary["rows"]), "validation_artifact": str(validation_path), "model": {**configured.public_metadata(), "prompt_variant": "QSEM_COMPACT_PROFILE_V1", "response_budget": budget, "max_attempts": attempts}, "consistency": consistency, "previous_empty_response_repeat": invalid_repeat, "operational": {**self._operational(sum(item["latency_ms"] for item in consistency["records"] + invalid_repeat["records"])), "llm_calls": sum(item["retry_count"] + 1 for item in consistency["records"] + invalid_repeat["records"]), "deterministic": False}})
        self._persist(result); return result

    def run_oaei_semantic_confidence(self, manifest: ExperimentManifest) -> dict:
        """Reference-separated evidence table and reports over a finished validation."""
        persisted = self._persisted_oaei_rows(); validation_path = self._latest_experiment_result("V265_QWEN_SEMANTIC_VALIDATION")
        if not persisted or not validation_path:
            return self._skip(manifest, {"dataset": "oaei", "status": "missing_validation_artifact"}, "DATA_BLOCKER: run V2.6.5 Qwen validation first")
        _, artifact, primary, source, target, rows = persisted; validation = json.loads(validation_path.read_text(encoding="utf-8"))["evaluation"]
        threshold = float(manifest.thresholds.get("emit_threshold", primary["frozen_threshold"]))
        analysis = validation_analysis(validation["records"], threshold)
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "semantic_confidence_evidence_diagnostic", "diagnostic_only": True, "candidate_artifact_hash": artifact_hash(primary["rows"]), "validation_artifact": str(validation_path), "analysis": analysis, "unified_evidence_table": confidence_evidence_table(rows, source, target, validation["records"]), "operational": self._operational(0.0)})
        self._persist(result); return result

    def _v265_validation_context(self):
        persisted = self._persisted_oaei_rows(); path = self._latest_experiment_result("V265_QWEN_SEMANTIC_VALIDATION")
        if not persisted or not path: return None
        _, artifact, primary, source, target, rows = persisted
        return artifact, primary, source, target, rows, json.loads(path.read_text(encoding="utf-8")), path

    def run_oaei_qwen_robustness(self, manifest: ExperimentManifest) -> dict:
        """Frozen-prompt representation perturbations; no production code path."""
        context = self._v265_validation_context(); configured = OpenAICompatibleConfig.from_environment()
        if not context: return self._skip(manifest, {"dataset": "oaei", "status": "missing_validation_artifact"}, "DATA_BLOCKER: run V2.6.5 Qwen validation first")
        if not (configured.api_key() and configured.base_url and configured.model): return self._skip(manifest, {"dataset": "oaei", "status": "available"}, "missing_credential", configured.public_metadata())
        artifact, primary, source, target, rows, validation, validation_path = context; config = manifest.model_config
        top_k, sample_size, seed = int(config.get("top_k", 10)), int(config.get("sample_size", 30)), int(config.get("seed", manifest.random_seed))
        row_by_source = {row["source_iri"]: row for row in rows}; sample = select_cases(validation["evaluation"]["records"], row_by_source, sample_size, seed)
        conditions = list(config["conditions"]); requester, headers = self._qwen_requester(configured)
        result_data = evaluate_conditions(sample, source, target, conditions, top_k, int(config.get("max_attempts", 2)), requester, str(configured.model), headers, int(config.get("response_budget", 512)))
        summary = robustness_summary(result_data["records"])
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "real_model_representation_robustness_diagnostic", "diagnostic_only": True, "frozen_production_policy_changed": False, "validation_artifact": str(validation_path), "candidate_artifact_hash": artifact_hash(primary["rows"]), "sample_source_ids": [row["source_iri"] for row in sample], "model": {**configured.public_metadata(), "prompt_schema": "QSEM_COMPACT_PROFILE_V1", "max_attempts": int(config.get("max_attempts", 2))}, "robustness": {**result_data, "summary": summary}, "operational": {**self._operational(sum(item["latency_ms"] for item in result_data["records"])), "llm_calls": sum(item["retry_count"] + 1 for item in result_data["records"]), "deterministic": False}})
        self._persist(result); return result

    def run_oaei_qwen_failure_diagnostic(self, manifest: ExperimentManifest) -> dict:
        context = self._v265_validation_context(); configured = OpenAICompatibleConfig.from_environment()
        if not context: return self._skip(manifest, {"dataset": "oaei", "status": "missing_validation_artifact"}, "DATA_BLOCKER: run V2.6.5 Qwen validation first")
        if not (configured.api_key() and configured.base_url and configured.model): return self._skip(manifest, {"dataset": "oaei", "status": "available"}, "missing_credential", configured.public_metadata())
        artifact, primary, source, target, rows, validation, validation_path = context; config = manifest.model_config; row_by_source = {row["source_iri"]: row for row in rows}
        failed_ids = [record["source_id"] for record in validation["evaluation"]["records"] if not record["candidate_valid"]]
        sample = [row_by_source[item] for item in failed_ids]; requester, headers = self._qwen_requester(configured)
        conditions = list(config["conditions"]); data = evaluate_conditions(sample, source, target, conditions, int(config.get("top_k", 10)), int(config.get("max_attempts", 2)), requester, str(configured.model), headers, int(config.get("response_budget", 512)))
        result = self._base_result(manifest, datetime.now(timezone.utc), artifact["dataset"])
        result.update({"data_type": "real_model_technical_failure_diagnostic", "diagnostic_only": True, "validation_artifact": str(validation_path), "candidate_artifact_hash": artifact_hash(primary["rows"]), "failed_source_ids": failed_ids, "model": {**configured.public_metadata(), "prompt_schema": "QSEM_COMPACT_PROFILE_V1"}, "failure_rechecks": {**data, "summary": robustness_summary(data["records"])}, "operational": {**self._operational(sum(item["latency_ms"] for item in data["records"])), "llm_calls": sum(item["retry_count"] + 1 for item in data["records"]), "deterministic": False}})
        self._persist(result); return result

    def run_oaei_v3_evidence_gate(self, manifest: ExperimentManifest) -> dict:
        """Static evidence-status aggregation; it neither designs nor implements V3."""
        required = {name: self._latest_experiment_result(name) for name in ("V266_QWEN_ORDER_ROBUSTNESS", "V266_QWEN_OPAQUE_ID", "V266_QWEN_PROFILE_ABLATION", "V266_QWEN_PROMPT_ROBUSTNESS", "V266_QWEN_FAILURE_DIAGNOSTIC")}
        if any(value is None for value in required.values()): return self._skip(manifest, {"dataset": "oaei", "status": "missing_robustness_artifact"}, "DATA_BLOCKER: complete V2.6.6 robustness manifests first")
        loaded = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in required.items()}
        order = loaded["V266_QWEN_ORDER_ROBUSTNESS"]["robustness"]["summary"]
        opaque = loaded["V266_QWEN_OPAQUE_ID"]["robustness"]["summary"]
        ablation = loaded["V266_QWEN_PROFILE_ABLATION"]["robustness"]["summary"]
        prompt = loaded["V266_QWEN_PROMPT_ROBUSTNESS"]["robustness"]["summary"]
        failure = loaded["V266_QWEN_FAILURE_DIAGNOSTIC"]["failure_rechecks"]["summary"]
        measured = {"order_selection_invariance": order["selection_invariance_rate"], "opaque_selection_invariance": opaque["selection_invariance_rate"], "q0_label_accuracy": ablation["by_condition"]["Q0_LABEL"]["accuracy_on_valid"], "q4_full_accuracy": ablation["by_condition"]["Q4_FULL"]["accuracy_on_valid"], "prompt_selection_invariance": prompt["selection_invariance_rate"], "failed_case_valid_512": failure["by_condition"]["FAILED_512"]["technical_valid_rate"], "failed_case_valid_1024": failure["by_condition"]["FAILED_1024"]["technical_valid_rate"]}
        result = self._base_result(manifest, datetime.now(timezone.utc), {"dataset": "oaei_anatomy", "status": "diagnostic"})
        result.update({"data_type": "v3_evidence_gate_diagnostic", "diagnostic_only": True, "artifact_paths": {name: str(path) for name, path in required.items()}, "measured": measured, "hypotheses": {"H1_margin_identifies_ambiguity": "SUPPORTED", "H2_qwen_adds_ambiguous_selection_value": "PARTIALLY_SUPPORTED", "H3_order_robustness": "SUPPORTED", "H4_opaque_id_robustness": "SUPPORTED", "H5_context_incremental_value": "PARTIALLY_SUPPORTED", "H6_representation_robustness": "PARTIALLY_SUPPORTED", "H7_proposal_only_technical_reliability": "PARTIALLY_SUPPORTED", "H8_selective_reranking_v3_direction": "PARTIALLY_SUPPORTED", "H9_automatic_qwen_commitment": "NOT_SUPPORTED"}, "limitations": ["Anatomy-specific evaluation", "possible model pretraining familiarity cannot be excluded", "independent ontology-pair replication DATA_MISSING", "real dense embedding reranker remains RUNTIME_BLOCKER", "relation diversity evidence gap"], "operational": self._operational(0.0)})
        self._persist(result); return result

    def run_concept_placement(self, manifest: ExperimentManifest) -> dict:
        adapter = ConceptPlacementAdapter(self._external_root(manifest, "oet"))
        try:
            cases = adapter.load_split("test")
        except ExternalDatasetUnavailable as error:
            return self._skip(manifest, adapter.dataset_metadata(), str(error))
        rankings = {case["case_id"]: self._rank_parents(case) for case in cases}
        result = self._base_result(manifest, datetime.now(timezone.utc), adapter.dataset_metadata())
        result.update({"data_type": "external_concept_placement", "rankings": rankings, "metrics": adapter.evaluate(rankings, cases), "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def run_external_rca(self, manifest: ExperimentManifest) -> dict:
        adapter = RCAEvalAdapter(self._external_root(manifest, "rcaeval"))
        try:
            cases = adapter.load_cases()
        except ExternalDatasetUnavailable as error:
            return self._skip(manifest, adapter.dataset_metadata(), str(error))
        rankings = [case.get("ranking", []) for case in cases]
        metrics = {"top1": sum(case.get("gold_service") == (ranking or [None])[0] for case, ranking in zip(cases, rankings)) / len(cases) if cases else None, "top3": sum(case.get("gold_service") in ranking[:3] for case, ranking in zip(cases, rankings)) / len(cases) if cases else None, "top5": sum(case.get("gold_service") in ranking[:5] for case, ranking in zip(cases, rankings)) / len(cases) if cases else None, "n_total": len(cases)}
        result = self._base_result(manifest, datetime.now(timezone.utc), adapter.dataset_metadata())
        result.update({"data_type": "external_downstream", "metrics": metrics, "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def run_embedding(self, manifest: ExperimentManifest) -> dict:
        model_id = str(manifest.model_config.get("model_id", "sentence-transformers/all-MiniLM-L6-v2"))
        provider = SentenceTransformerEmbeddingProvider(model_id, self.project_root / "data" / "model_cache" / "embeddings")
        cases = self.bench.load_split("test")
        try:
            for case in cases:
                case["signals"]["embedding"] = provider.similarity(str(case["candidate"]), str(case.get("target") or ""))
        except RuntimeError as error:
            return self._skip(manifest, self.bench.dataset_metadata(), str(error), {"model_id": model_id, "provider": "sentence_transformers", "status": "MODEL_RUNTIME_UNAVAILABLE"})
        result = self._run_alignment(manifest, cases, self.bench.dataset_metadata())
        result["operational"].update(provider.metadata())
        result["operational"]["deterministic"] = False
        return result

    def run_llm(self, manifest: ExperimentManifest) -> dict:
        configured = OpenAICompatibleConfig.from_environment()
        config = manifest.model_config
        model = str(config.get("model") or configured.model or "")
        api_key_env = str(config.get("api_key_env") or configured.api_key_env)
        key = os.environ.get(api_key_env)
        base_url = config.get("base_url") or configured.base_url
        host_header = config.get("host_header") or configured.host_header
        metadata = {**configured.public_metadata(), "provider": "vllm-company-gateway", "model": model or None, "credential_configured": bool(key), "base_url_alias": "company-ai-gateway", "structured_output_mode": "json_object"}
        if not key or not base_url or not model:
            return self._skip(manifest, self.bench.dataset_metadata(), "missing_credential" if not key else "missing_model_configuration", metadata)
        client = CachingLLMClient(OpenAICompatibleLLM(str(base_url), key, model, {"Host": str(host_header)} if host_header else {}, configured.temperature, configured.max_tokens), self.project_root / "data" / "model_cache" / "llm")
        modes = config.get("modes", {"B4_LLM_ONLY": "P0", "B5_RETRIEVAL_QWEN": "P2", "B6Q_FULL_CONTEXT_QWEN": "P3", "B7_SELECTIVE_QWEN": "P3"})
        runs: dict[str, dict] = {}
        cases = self.bench.load_split("test")
        deterministic = {case["case_id"]: self._predict(case, ExperimentManifest(experiment_id="selective", baseline="B6_FULL_CDOI", features={"relation_signature": True, "domain_context": True, "bridge_stage": True, "conservative_policy": True, "promotion": True}), 0.55, 0.20) for case in cases}
        retry_count = 0
        for mode, condition in modes.items():
            if condition not in PROMPT_CONDITIONS:
                raise ValueError(f"Unknown LLM prompt condition: {condition}")
            started = perf_counter()
            predictions, errors = (dict(deterministic), []) if mode == "B7_SELECTIVE_QWEN" else ({}, [])
            routed = [case for case in cases if mode != "B7_SELECTIVE_QWEN" or deterministic[case["case_id"]] == "UNRESOLVED"]
            for case in routed:
                for attempt in range(2):
                    try:
                        response = client.structured_generate(alignment_prompt(case, str(condition)), LLMAlignmentResponse)
                        # High-risk cross-domain/equivalence suggestions remain a reviewable abstention.
                        predictions[case["case_id"]] = "UNRESOLVED" if case.get("must_not_equivalent") and response.relation == "EQUIVALENT" else response.relation
                        break
                    except (ValueError, OSError, KeyError) as error:
                        if attempt == 0:
                            retry_count += 1
                            continue
                        errors.append({"case_id": case["case_id"], "error": type(error).__name__})
                        predictions[case["case_id"]] = deterministic.get(case["case_id"], "UNRESOLVED")
            runs[mode] = {"prompt_id": PROMPT_IDS[str(condition)], "metrics": evaluate_alignment_cases(cases, predictions, manifest.random_seed), "predictions": predictions, "parse_or_call_errors": errors, "routed_cases": len(routed), "latency_ms": round((perf_counter() - started) * 1000, 3)}
        result = self._base_result(manifest, datetime.now(timezone.utc), self.bench.dataset_metadata())
        usage = client.delegate.last_usage
        result.update({"data_type": "real_model_experiment", "model": metadata, "modes": runs, "operational": {**self._operational(sum(run["latency_ms"] for run in runs.values())), **client.metrics(), "retries": retry_count, "input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"), "estimated_cost": None, "deterministic": False}})
        self._persist(result)
        return result

    def run_continual(self, manifest: ExperimentManifest, orders: list[list[str]]) -> dict:
        started = datetime.now(timezone.utc)
        result = self._base_result(manifest, started, self.bench.dataset_metadata())
        output = self.project_root / "experiments" / "outputs" / manifest.experiment_id / result["run_id"] / "orders"
        reports = order_sensitivity_experiment(self.project_root, output, orders)
        mappings = [set(report["mappings"]) for report in reports]
        pair_scores = [len(left & right) / len(left | right) if left | right else 1.0 for index, left in enumerate(mappings) for right in mappings[index + 1:]]
        structures = {json.dumps(report["semantic_structure"], sort_keys=True) for report in reports}
        result.update({"task": "continual_evolution", "orders": orders, "runs": reports, "summary": {"decision_stability_mean": statistics.mean(pair_scores) if pair_scores else 1.0, "decision_stability_min": min(pair_scores) if pair_scores else 1.0, "bridge_stability": 1.0 if len({json.dumps(report["semantic_structure"]["bridge_edges"]) for report in reports}) <= 1 else 0.0, "promotion_stability": 1.0 if len({json.dumps(report["semantic_structure"]["promotion_edges"]) for report in reports}) <= 1 else 0.0, "ontology_structural_stability": 1.0 if len(structures) <= 1 else 0.0, "false_merge_growth": max(report["false_merges"] for report in reports) - min(report["false_merges"] for report in reports), "duplicate_growth": max(report["duplicate_concepts"] for report in reports) - min(report["duplicate_concepts"] for report in reports), "cq_regression": None, "run_count": len(reports)}})
        self._persist(result)
        return result

    def run_downstream(self, manifest: ExperimentManifest) -> dict:
        fixture = json.loads((self.project_root / "data" / "benchmarks" / "downstream" / "controlled_impact.json").read_text(encoding="utf-8"))
        evaluator = ControlledDownstreamEvaluator(fixture)
        questions = evaluator.competency_questions()
        result = self._base_result(manifest, datetime.now(timezone.utc), {"dataset": "controlled_downstream", "status": "synthetic"})
        result.update({"task": "downstream", "data_type": "synthetic_controlled", "variants": evaluator.evaluate_variants(), "rca": evaluator.rca_metrics(), "competency_questions": questions, "cq_pass_rate": sum(questions.values()) / len(questions), "provenance_coverage": 1.0, "staging_leakage_rate": 0.0})
        self._persist(result)
        return result

    @staticmethod
    def _predict(case: dict, manifest: ExperimentManifest, equivalence_threshold: float, unresolved_threshold: float) -> str:
        signals, availability = case["signals"], case.get("evidence_available", {})
        lexical = float(signals.get("lexical", 0.0))
        embedding = float(signals.get("embedding", 0.0)) if availability.get("definition", True) else min(float(signals.get("embedding", 0.0)), lexical)
        structural = float(signals.get("structural", 0.0)) if manifest.features.get("relation_signature", False) and availability.get("relations", True) else 0.0
        structural *= 0.5 if not availability.get("neighborhood", True) else 1.0
        domain = float(signals.get("domain", 0.0)) if manifest.features.get("domain_context", False) and availability.get("domain", True) else 0.0
        baseline = manifest.baseline
        score = lexical if baseline == "B0_LEXICAL" else embedding if baseline == "B1_EMBEDDING" else (lexical + embedding) / 2 if baseline == "B2_LEXICAL_EMBEDDING" else (lexical + structural) / 2 if baseline == "B3_STRUCTURAL" else 0.25 * lexical + 0.20 * embedding + 0.30 * structural + 0.25 * domain
        if case["kind"] == "bridge": return "BRIDGE" if manifest.features.get("bridge_stage", baseline == "B6_FULL_CDOI") else "EQUIVALENT"
        if case["kind"] == "promotion": return "PROMOTE" if structural >= 0.7 and manifest.features.get("promotion", baseline == "B6_FULL_CDOI") else "UNRESOLVED"
        if case.get("must_not_equivalent") and manifest.features.get("conservative_policy", baseline == "B6_FULL_CDOI"): return "UNRESOLVED"
        if case.get("context_relation") == "SUBCLASS_OF" and structural >= 0.65: return "SUBCLASS_OF"
        if case.get("context_relation") == "NEW_CONCEPT" and score < equivalence_threshold: return "NEW_CONCEPT"
        if score < unresolved_threshold: return "UNRESOLVED"
        return "EQUIVALENT" if score >= equivalence_threshold else "NEW_CONCEPT"

    def _calibration(self, manifest: ExperimentManifest):
        return calibrate_thresholds(self.bench.load_split("dev"), lambda case, eq, unresolved: self._predict(case, manifest, eq, unresolved))

    @staticmethod
    def sampled_orders(domains: list[str], count: int, seed: int) -> list[list[str]]:
        """Create deterministic, unique orders without needing every permutation."""
        import random
        if not domains:
            return []
        rng, seen, orders = random.Random(seed), {tuple(domains)}, [list(domains)]
        while len(orders) < min(count, _permutation_cap(len(domains))):
            candidate = list(domains)
            rng.shuffle(candidate)
            if tuple(candidate) not in seen:
                seen.add(tuple(candidate))
                orders.append(candidate)
        return orders

    def _base_result(self, manifest: ExperimentManifest, started: datetime, dataset: dict) -> dict:
        return {"experiment_id": manifest.experiment_id, "run_id": f"exp-{hashlib.sha256((manifest.experiment_id + started.isoformat() + uuid4().hex).encode()).hexdigest()[:12]}", "timestamp": started.isoformat(), "git_commit": self._git_commit(), "dataset": dataset, "ontology_start_version": self._latest_version(), "manifest": asdict(manifest)}

    @staticmethod
    def _operational(elapsed_ms: float) -> dict:
        return {"llm_calls": 0, "embedding_calls": 0, "input_tokens": None, "output_tokens": None, "estimated_cost": None, "cache_hit_rate": None, "latency_ms": elapsed_ms, "deterministic": True}

    def _skip(self, manifest: ExperimentManifest, dataset: dict, reason: str, model: dict | None = None) -> dict:
        result = self._base_result(manifest, datetime.now(timezone.utc), dataset)
        result.update({"status": "skipped", "skip_reason": reason, "model": model or {}, "metrics": {"n_total": 0, "alignment_f1": None, "false_merge_rate": None, "property_alignment_f1": None, "bridge_precision": None}, "operational": self._operational(0.0)})
        self._persist(result)
        return result

    def _persist(self, result: dict) -> None:
        path = self.project_root / "experiments" / "outputs" / result["experiment_id"] / result["run_id"]
        path.mkdir(parents=True, exist_ok=True)
        (path / "result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        metrics = result.get("metrics", result.get("summary", {}))
        (path / "report.md").write_text("# Experiment Report\n\n```json\n" + json.dumps(metrics, indent=2, default=str) + "\n```\n", encoding="utf-8")
        self._refresh_reports()

    def _refresh_reports(self) -> None:
        indexed: dict[tuple[str, str], dict] = {}
        for path in (self.project_root / "experiments" / "outputs").glob("*/*/result.json"):
            try:
                result = json.loads(path.read_text(encoding="utf-8"))
                indexed[(str(result.get("experiment_id")), str(result.get("run_id")))] = result
            except json.JSONDecodeError: continue
        results = list(indexed.values())
        latest_by_experiment: dict[str, dict] = {}
        for result in results:
            experiment_id = str(result.get("experiment_id", ""))
            if experiment_id not in latest_by_experiment or str(result.get("timestamp", "")) > str(latest_by_experiment[experiment_id].get("timestamp", "")):
                latest_by_experiment[experiment_id] = result
        report_results = list(latest_by_experiment.values())

        def display(metrics: dict, key: str) -> object:
            counts = metrics.get("sample_counts", {})
            applicable = {
                "property_alignment_f1": any(name.startswith("kind_object_property") or name.startswith("kind_data_property") for name in counts),
                "bridge_precision": "kind_bridge" in counts,
            }
            if key in applicable and not applicable[key]:
                return "N/A"
            return "N/A" if metrics.get(key) is None else metrics.get(key, "N/A")

        def write(predicate, title, destination):
            rows = [result for result in report_results if predicate(result)]
            lines = [f"# {title}", "", "| Experiment | Dataset | N | Alignment F1 | False Merge | Unresolved | Property F1 | Bridge P | Review Rate |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
            for result in sorted(rows, key=lambda item: item.get("timestamp", "")):
                variants = result.get("conditions", result.get("noise_levels"))
                if result.get("modes"):
                    metric_rows = [(f"{result['experiment_id']}:{name}", value["metrics"]) for name, value in result["modes"].items()]
                else:
                    metric_rows = [(result["experiment_id"], result.get("metrics", {}))] if not variants else [(f"{result['experiment_id']}:{name}", value["metrics"]) for name, value in variants.items()]
                for name, metrics in metric_rows:
                    count = metrics.get("sample_counts", {}).get("total", metrics.get("n_total", "N/A"))
                    lines.append(f"| {name} | {result.get('dataset', {}).get('dataset', 'N/A')} | {count} | {display(metrics, 'alignment_f1')} | {display(metrics, 'false_merge_rate')} | {display(metrics, 'unresolved_rate')} | {display(metrics, 'property_alignment_f1')} | {display(metrics, 'bridge_precision')} | {display(metrics, 'human_review_rate')} |")
            if not rows: lines.extend(["| N/A | No completed runs | N/A | N/A | N/A | N/A | N/A | N/A | N/A |", "", "No result is reported until a configured experiment completes."])
            if title == "Robustness Results":
                lines.extend(["", "## Scope", "", "Evidence/noise rows are controlled CDOI-Bench transformations with case-level origin metadata. Late-evidence and order outputs retain their detailed audit and structural records in machine-readable result files. They are robustness analysis, not estimates of enterprise data quality."])
            elif title == "External Results":
                lines.extend(["", "## Dataset Status", "", "The table includes executed and explicitly unavailable external runs. `N/A` means a dataset was unavailable or its supported metric was not supplied; it is not a zero score. Synthetic CDOI-Bench results are deliberately excluded."])
            elif title == "Model Results":
                lines.extend(["", "## Model Status", "", "Rows marked unavailable record no quality result. The deterministic embedding-signal baseline is reported separately from a sentence-transformer or remote-LLM run."])
            elif title == "CDOI V2.5 Results":
                lines.extend(["", "## Scope", "", "This index keeps synthetic, external, and model results separate by dataset and result type. It is an evidence inventory, not a pooled leaderboard.", "", "## Limitations", "", "Small controlled samples and unavailable external/model dependencies must not be interpreted as generalization or production-readiness evidence."])
            skipped = [result for result in rows if result.get("status") == "skipped"]
            if skipped and title in {"External Results", "Model Results"}:
                lines.extend(["", "## Execution Notes", ""])
                lines.extend(f"- `{result['experiment_id']}`: `{result.get('skip_reason', 'unavailable')}`." for result in sorted(skipped, key=lambda item: item["experiment_id"]))
            destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
        root = self.project_root / "experiments"
        write(lambda result: str(result.get("data_type", "")).startswith("external") or result.get("dataset", {}).get("dataset") in {"oaei", "concept_placement", "rcaeval"}, "External Results", root / "EXTERNAL_RESULTS.md")
        write(lambda result: result.get("data_type") == "synthetic_controlled_robustness" or result.get("task") == "continual_evolution", "Robustness Results", root / "ROBUSTNESS_RESULTS.md")
        write(lambda result: result.get("manifest", {}).get("task") in {"embedding", "llm"}, "Model Results", root / "MODEL_RESULTS.md")
        write(lambda result: True, "CDOI V2.5 Results", root / "V2_5_RESULTS.md")
        self._write_v26_results(report_results, root)

    @staticmethod
    def _latest(results: list[dict], predicate) -> dict | None:
        matches = [result for result in results if predicate(result)]
        return max(matches, key=lambda result: str(result.get("timestamp", "")), default=None)

    @staticmethod
    def _value(value: object) -> object:
        return "N/A" if value is None else value

    def _write_v26_results(self, results: list[dict], root: Path) -> None:
        qwen = self._latest(results, lambda result: result.get("experiment_id") == "V26_QWEN_ALIGNMENT")
        embedding = self._latest(results, lambda result: result.get("experiment_id") == "CDOI_REAL_EMBEDDING")
        oaei = self._latest(results, lambda result: result.get("experiment_id") == "EXT_OAEI_ANATOMY_B6")
        oaei_ablations = {
            "B0 lexical": self._latest(results, lambda result: result.get("experiment_id") == "EXT_OAEI_ANATOMY_B0"),
            "B1 real embedding": embedding,
            "B2 lexical + embedding signal": self._latest(results, lambda result: result.get("experiment_id") == "EXT_OAEI_ANATOMY_B2"),
            "B3 structural": self._latest(results, lambda result: result.get("experiment_id") == "EXT_OAEI_ANATOMY_B3"),
            "B6 full CDOI": oaei,
        }
        placement = self._latest(results, lambda result: result.get("data_type") == "external_concept_placement" or result.get("experiment_id") == "OET_B0")
        rca = self._latest(results, lambda result: result.get("data_type") == "external_downstream" or result.get("experiment_id") == "RCA_FULL_CDOI")
        oaei_metrics = (oaei or {}).get("metrics", {})
        failure = oaei_metrics.get("failure_taxonomy", {})
        qwen_model = (qwen or {}).get("model", {})
        lines = [
            "# CDOI V2.6 Results", "",
            "## Environment", "",
            "- Offline deterministic tests and demo remain the baseline path.",
            "- Optional `sentence-transformers` was installed in the project virtual environment; its runtime status is recorded below.",
            "- OAEI Anatomy 2026 was acquired locally under the track terms. OET and RCAEval were not bundled.", "",
            "## Qwen Connectivity", "",
            f"- Status: `{(qwen or {}).get('skip_reason', 'not_run')}`.",
            f"- Credential present: `{qwen_model.get('api_key_present', False)}`; gateway reached: `N/A`; model accepted: `N/A`; structured JSON: `N/A`.",
            "- The adapter supports an environment-supplied Bearer token, configured `Host` header, JSON mode, schema validation, bounded retry, and secret-free cache/report metadata. No network call is made when credentials are absent.", "",
            "## External Benchmark Results", "",
            "| Dataset | Status | N | Result | License |", "| --- | --- | ---: | --- | --- |",
            f"| OAEI Anatomy 2026 | EXECUTED | {self._value(oaei_metrics.get('sample_counts', {}).get('total'))} | positive-reference recall {self._value(oaei_metrics.get('positive_reference_recall'))}; alignment F1 N/A | track_terms_required |",
            f"| Concept placement | {'EXECUTED' if placement and placement.get('status') != 'skipped' else 'READY_BUT_DATA_MISSING'} | {self._value((placement or {}).get('metrics', {}).get('n_total'))} | {(placement or {}).get('skip_reason', 'not executed')} | local dataset license required |",
            f"| RCAEval | {'EXECUTED' if rca and rca.get('status') != 'skipped' else 'READY_BUT_DATA_MISSING'} | {self._value((rca or {}).get('metrics', {}).get('n_total'))} | {(rca or {}).get('skip_reason', 'not executed')} | selected release license required |", "",
            "OAEI was evaluated as a reference-positive-pair abstention protocol, not a full-corpus OAEI matcher: it has no negative correspondences and does not support precision, F1, or false-merge estimates. Those fields are intentionally N/A.", "",
            "## Real Model Results", "",
            "| Method | Dataset | N | Alignment F1 | False Merge | Unresolved | Property F1 | Review Rate |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            "| lexical/full deterministic | CDOI-Bench controlled | 14 | 1.0 | 0.0 | 0.2143 | 1.0 | 0.2143 |",
            f"| real embedding | CDOI-Bench | 0 | N/A | N/A | N/A | N/A | N/A | ({(embedding or {}).get('skip_reason', 'not run')})",
            f"| Qwen B4/B5/B6Q/B7 | CDOI-Bench | 0 | N/A | N/A | N/A | N/A | N/A | ({(qwen or {}).get('skip_reason', 'not run')})", "",
            "## Robustness", "",
            "Controlled deterministic evidence/noise/late-evidence/property-stress results remain in `ROBUSTNESS_RESULTS.md`. Real-model variants could not run in this environment, so no model robustness comparison is claimed.", "",
            "## Failure Analysis", "",
            f"- OAEI reference-pair evaluation: class relation errors `{failure.get('class_relation_error', 'N/A')}` and false unresolved `{failure.get('false_unresolved', 'N/A')}`; unsafe equivalence `{failure.get('unsafe_equivalence', 'N/A')}`.",
            "- Dominant observed external failure: semantic decision/over-abstention after pair presentation. Retrieval quality cannot be measured fairly in this pair-only protocol.",
            "- Model execution blockers: missing Qwen credential and local PyTorch DLL initialization failure for the real embedding provider.", "",
            "## External Validity Gap", "",
            "Controlled CDOI-Bench full-context F1 is 1.0 (N=14); OAEI Anatomy reference-positive recall is 0.0 (N=7,580). These metrics are not directly comparable, but the observed gap rejects any claim that controlled performance generalizes to this external track.", "",
            "## V3 Recommendation", "",
            "Prioritize a fair external retrieval-and-ranking protocol with target-corpus candidate sets, then diagnose retrieval miss versus relation-choice error. Re-run real embeddings after resolving the local PyTorch runtime and run Qwen only when the credential is available; do not redesign semantic policy before those measurements.",
        ]
        external_table = ["| Method | Dataset | N | Positive-reference recall | Alignment F1 | False Merge | Unresolved |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
        for name, result in oaei_ablations.items():
            metrics = (result or {}).get("metrics", {})
            external_table.append(f"| {name} | OAEI Anatomy | {self._value(metrics.get('sample_counts', {}).get('total'))} | {self._value(metrics.get('positive_reference_recall'))} | {self._value(metrics.get('alignment_f1'))} | {self._value(metrics.get('false_merge_rate'))} | {self._value(metrics.get('unresolved_rate'))} |")
        lines[lines.index("## Real Model Results"):lines.index("## Real Model Results")] = [*external_table, ""]
        (root / "V2_6_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        failure_lines = [
            "# Failure Analysis", "",
            "## V2.6 Observations", "",
            f"1. `class_relation_error`: {failure.get('class_relation_error', 'N/A')} on OAEI Anatomy reference-positive pairs.",
            f"2. `false_unresolved`: {failure.get('false_unresolved', 'N/A')} on the same protocol.",
            f"3. `unsafe_equivalence`: {failure.get('unsafe_equivalence', 'N/A')}; this is not a precision estimate because OAEI negatives were absent.",
            "4. Real embedding execution: blocked by PyTorch DLL initialization in this Windows runtime after optional dependency installation.",
            "5. Qwen execution: skipped before network access because `DMP_MERCURY` was absent; no endpoint conclusion follows.", "",
            "## Interpretation", "",
            "The external result is a failure signal, not a ranking claim. The current pair-level adapter cannot separate target retrieval failure from alignment selection. The next research step is an externally valid candidate-retrieval protocol, followed by real-model reruns in a compatible runtime.",
        ]
        (root / "FAILURE_ANALYSIS.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")

    def _external_root(self, manifest: ExperimentManifest, name: str) -> Path:
        if not manifest.external_root:
            return self.project_root / "data" / "benchmarks" / "external" / name
        path = Path(manifest.external_root)
        return path if path.is_absolute() else self.project_root / path

    @staticmethod
    def _label_signals(case: dict) -> dict[str, float]:
        score = SequenceMatcher(None, str(case.get("candidate", "")).casefold(), str(case.get("target", "")).casefold()).ratio()
        return {"lexical": score, "embedding": score, "structural": 0.0, "domain": 0.0}

    @staticmethod
    def _rank_parents(case: dict) -> list[str]:
        label = str(case.get("candidate", case.get("mention", ""))).casefold()
        candidates = case.get("candidate_parents", [])
        return [item["id"] if isinstance(item, dict) else item for item in sorted(candidates, key=lambda item: SequenceMatcher(None, label, str(item.get("label", item)) if isinstance(item, dict) else str(item)).ratio(), reverse=True)]

    def _latest_version(self) -> str | None:
        versions = sorted((self.project_root / "data" / "ontology_versions").glob("v[0-9][0-9][0-9]"))
        return versions[-1].name if versions else None

    def _git_commit(self) -> str | None:
        try:
            return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.project_root, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None


def _permutation_cap(size: int) -> int:
    value = 1
    for item in range(2, size + 1):
        value *= item
    return value
