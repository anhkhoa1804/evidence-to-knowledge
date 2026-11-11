"""Run frozen Phase-2.6 Dense fixed-CandidateSet selection only after a smoke pass."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping

from cdoi.semantic_decision import (AmbiguityEvidence, CandidateSet, DenseSemanticSelector,
                                    EvidenceAssembler, SelectionStatus,
                                    SourceProfileReference)
from cdoi.v3_phase2_6 import SentenceTransformerBackend
from cdoi.v3_phase2_6_followup import dense_runtime_check


ROOT = Path(__file__).resolve().parents[1]
ANATOMY = ROOT / "data" / "benchmarks" / "external" / "oaei" / "anatomy-2026"
PHASE26 = ROOT / "experiments" / "archive" / "v3_phase2_6_representation" / "RESULT.json"
FROZEN = ROOT / "experiments" / "outputs" / "OAEI_V263_PERSISTED_POSTRANKING" / "exp-3950cb966861" / "result.json"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_6_followup"


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _candidate_set(row: Mapping[str, Any]) -> CandidateSet:
    # Deliberately copy only observable candidate fields.  The reference is read
    # below only after all candidate scores have been computed.
    candidate_rows = [
        {key: value for key, value in candidate.items() if key in {"iri", "rank", "score", "label", "definition", "lexical_score", "context_score", "context_available", "r2_combined_score", "r2_lexical_score", "r2_context_score"}}
        for candidate in row["retrieved_candidates"]
    ]
    source_id = str(row["source_iri"])
    return CandidateSet.from_rows(source_id, SourceProfileReference(source_id, "P0_OR_P1_RESOLVED_V2"), candidate_rows, retriever_id="OAEI_V263_FROZEN_R1", retriever_version="v2_6_6", index_hash=hashlib.sha256("\n".join(str(item["iri"]) for item in row["retrieved_candidates"]).encode()).hexdigest())


def _summarize(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["selection_status"] == "SELECTED"]
    if len(valid) != len(rows):
        return {"technical_status": "TECHNICAL_UNAVAILABLE", "overall_population": len(rows), "technical_unavailable": len(rows) - len(valid), "paired_valid_population": len(valid)}
    nontrivial = [row for row in valid if row["nontrivial"]]
    correct = lambda values: sum(row["selected_id"] == row["gold_id"] for row in values)
    usable = [row for row in nontrivial if row["gold_score"] is not None and row["strongest_wrong_score"] is not None]
    separation = [row["gold_score"] - row["strongest_wrong_score"] for row in usable]
    return {
        "technical_status": "DENSE_AVAILABLE",
        "overall_population": len(rows), "candidate_valid_population": len(valid), "paired_valid_population": len(valid), "technical_unavailable": 0,
        "top1_accuracy": correct(valid) / len(valid) if valid else None,
        "nontrivial_accuracy": correct(nontrivial) / len(nontrivial) if nontrivial else None,
        "rank2_5_recovery": sum(2 <= row["frozen_gold_rank"] <= 5 and row["selected_id"] == row["gold_id"] for row in valid),
        "rank6_10_recovery": sum(6 <= row["frozen_gold_rank"] <= 10 and row["selected_id"] == row["gold_id"] for row in valid),
        "hard_negative_nontrivial": {"n_gold_available": len(usable), "gold_gt_wrong": sum(value > 0 for value in separation), "tie": sum(value == 0 for value in separation), "gold_lt_wrong": sum(value < 0 for value in separation)},
        "latency_ms": {"mean": mean(row["latency_ms"] for row in valid), "median": median(row["latency_ms"] for row in valid), "p95": sorted(row["latency_ms"] for row in valid)[max(0, int(.95 * len(valid)) - 1)]},
    }


def _run_condition(backend: SentenceTransformerBackend, profiles_source: Mapping[str, Any], profiles_target: Mapping[str, Any], frozen_rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    assembler = EvidenceAssembler()
    source_evidence = {identifier: assembler.assemble(profile) for identifier, profile in profiles_source.items()}
    target_evidence = {identifier: assembler.assemble(profile) for identifier, profile in profiles_target.items()}
    selector = DenseSemanticSelector(backend, target_evidence)
    rows: list[dict[str, Any]] = []
    for raw in frozen_rows:
        candidates, source = _candidate_set(raw), source_evidence[str(raw["source_iri"])]
        selection = selector.select(source, candidates, AmbiguityEvidence.from_candidate_set(candidates, source))
        if selection.status == SelectionStatus.TECHNICAL_UNAVAILABLE:
            rows.append({"source_id": str(raw["source_iri"]), "selected_id": None, "selection_status": selection.status.value, "selection_score": None, "latency_ms": selection.latency_ms, "gold_id": None, "gold_in_frozen_candidate_set": None, "gold_score": None, "strongest_wrong_score": None, "frozen_gold_rank": int(raw["gold_rank"]), "frozen_top1_top2_margin": float(raw["top1_top2_r1_margin"]), "nontrivial": bool(raw["nontrivial"]), "candidate_set_hash": candidates.artifact_hash})
            break
        candidate_scores = {candidate.candidate_id: backend.score(source, target_evidence[candidate.candidate_id]) for candidate in candidates.candidates}
        # Reference information enters only after Dense candidate scoring above.
        gold_id = str(raw["gold_target_iri"])
        wrong = [(score, identifier) for identifier, score in candidate_scores.items() if identifier != gold_id]
        wrong_score = min(wrong, key=lambda row: (-row[0], row[1]))[0] if wrong else None
        rows.append({"source_id": str(raw["source_iri"]), "selected_id": selection.candidate_id, "selection_status": selection.status.value, "selection_score": selection.selection_score, "latency_ms": selection.latency_ms, "gold_id": gold_id, "gold_in_frozen_candidate_set": gold_id in candidate_scores, "gold_score": candidate_scores.get(gold_id), "strongest_wrong_score": wrong_score, "frozen_gold_rank": int(raw["gold_rank"]), "frozen_top1_top2_margin": float(raw["top1_top2_r1_margin"]), "nontrivial": bool(raw["nontrivial"]), "candidate_set_hash": candidates.artifact_hash})
    return {"selection_scope": "fixed_frozen_candidate_sets_only", "candidate_membership_regenerated": False, "rows": rows, "summary": _summarize(rows)}


def run() -> dict[str, Any]:
    runtime = dense_runtime_check()
    metadata = {"runtime_check": runtime, "status": runtime["status"], "full_benchmark_executed": False, "no_fabricated_metrics": True}
    if runtime["status"] != "DENSE_RUNTIME_READY":
        _write(ARCHIVE / "DENSE_SELECTION_RESULT.json", metadata)
        return metadata
    phase26 = json.loads(PHASE26.read_text(encoding="utf-8"))
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    from cdoi.v3_phase2_6 import resolved_source_faithful_profiles
    backend = SentenceTransformerBackend(device="cpu", normalize_embeddings=True)
    conditions: dict[str, Any] = {}
    for condition in ("P0_CURRENT_V1", "P1_SYNONYMS_RESOLVED_V2"):
        source = resolved_source_faithful_profiles(ANATOMY / "mouse.owl", condition).profiles
        target = resolved_source_faithful_profiles(ANATOMY / "human.owl", condition).profiles
        conditions[condition] = _run_condition(backend, source, target, frozen["enriched_cases"])
        if conditions[condition]["summary"]["technical_status"] != "DENSE_AVAILABLE":
            metadata.update({"status": "TECHNICAL_UNAVAILABLE", "technical_failure_condition": condition, "conditions": conditions})
            _write(ARCHIVE / "DENSE_SELECTION_RESULT.json", metadata)
            return metadata
    metadata.update({"status": "DENSE_RESULTS_AVAILABLE", "full_benchmark_executed": True, "runtime_metadata": backend.metadata(), "conditions": conditions, "frozen_phase26_result_sha256": hashlib.sha256(PHASE26.read_bytes()).hexdigest(), "frozen_candidate_artifact_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest()})
    _write(ARCHIVE / "DENSE_SELECTION_RESULT.json", metadata)
    return metadata


if __name__ == "__main__":
    run()
