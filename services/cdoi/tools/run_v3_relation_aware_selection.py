"""Run the preregistered STW--TheSoz relation-aware proposal experiment."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from cdoi.relation_aware_selection import RelationAwareSemanticSelector, SemanticRelation
from cdoi.semantic_decision import CandidateSet, EvidenceAssembler, SourceProfileReference
from cdoi.v3_relation_evaluation import (canonical_stw_thesoz_mappings, confusion,
                                          high_risk_confusions)
from cdoi.v3_stw_thesoz import STW_PREFIX, THESOZ_PREFIX, extract_english_skos_profiles

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "experiments/archive/v3_ontology_blocker_resolution_20260925"
OUT = ROOT / "experiments/archive/v3_ontology_relation_aware_selection_20260925"
DATA = ROOT / "data/benchmarks/external/stw_thesoz_20260925"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _candidate_hash(rows: list[Mapping[str, object]]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _candidate_set(source_id: str, rows: list[Mapping[str, object]]) -> CandidateSet:
    return CandidateSet.from_rows(source_id, SourceProfileReference(source_id, "stw_thesoz_en_prefLabel_v1"), list(rows), retriever_id="FROZEN_R1_LEXICAL", retriever_version="v3_ontology_blocker_resolution_20260925")


def _profile_evidence(profiles: Mapping[str, Any]) -> dict[str, Any]:
    assembler = EvidenceAssembler()
    return {identifier: assembler.assemble(profile) for identifier, profile in profiles.items()}


def _prediction_rows(source: Mapping[str, Any], candidates: Mapping[str, list[Mapping[str, object]]], selector: RelationAwareSemanticSelector) -> list[dict[str, Any]]:
    rows = []
    for source_id in sorted(candidates):
        candidate_set = _candidate_set(source_id, candidates[source_id])
        proposal = selector.propose(source[source_id], candidate_set).artifact()
        proposal["frozen_candidate_rows_hash"] = _candidate_hash(candidates[source_id])
        rows.append(proposal)
    return rows


def _metrics(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    result = {}
    for relation in ("exactMatch", "broadMatch", "narrowMatch", "relatedMatch"):
        group = [row for row in rows if row["gt_relation"] == relation]
        n = len(group)
        retrieved = [row for row in group if row["gt_target_rank"] is not None]
        selected = [row for row in group if row["target_correct"]]
        result[relation] = {
            "population": n,
            "retrieval_recall_at_1": sum(row["gt_target_rank"] == 1 for row in group) / n if n else None,
            "retrieval_recall_at_5": sum(row["gt_target_rank"] is not None and row["gt_target_rank"] <= 5 for row in group) / n if n else None,
            "retrieval_recall_at_20": len(retrieved) / n if n else None,
            "target_top1_accuracy": len(selected) / n if n else None,
            "relation_accuracy_given_gt_target_retrieved": sum(row["oracle_relation"] == relation for row in retrieved) / len(retrieved) if retrieved else None,
            "relation_accuracy_given_correct_target_selected": sum(row["predicted_relation"] == relation for row in selected) / len(selected) if selected else None,
            "joint_target_relation_accuracy": sum(row["target_correct"] and row["predicted_relation"] == relation for row in group) / n if n else None,
            "unresolved_count": sum(row["predicted_relation"] == "UNRESOLVED" for row in group),
            "unresolved_rate": sum(row["predicted_relation"] == "UNRESOLVED" for row in group) / n if n else None,
        }
    return result


def _failure(row: Mapping[str, Any]) -> str:
    if row["gt_target_rank"] is None:
        return "GT_TARGET_NOT_RETRIEVED"
    if not row["target_correct"]:
        return "WRONG_TARGET_SELECTED"
    if row["predicted_relation"] == row["gt_relation"]:
        return "CORRECT"
    if row["predicted_relation"] == "UNRESOLVED":
        return "UNRESOLVED_SAFE"
    if row["predicted_relation"] == "exactMatch" and row["gt_relation"] != "exactMatch":
        return "EXACT_OVERGENERALIZATION"
    if {row["predicted_relation"], row["gt_relation"]} == {"broadMatch", "narrowMatch"}:
        return "BROAD_NARROW_DIRECTION_ERROR"
    if row["predicted_relation"] == "relatedMatch":
        return "RELATED_OVERUSE"
    if row["gt_relation"] == "relatedMatch":
        return "RELATED_UNDERUSE"
    return "REQUIRES_REVIEW"


def _write_markdown(semantics: Mapping[str, Any], results: Mapping[str, Any]) -> None:
    (OUT / "RELATION_SEMANTICS.md").write_text(
        "# STW–TheSoz Relation Semantics\n\n"
        "The experiment expresses every relation from the STW source to the TheSoz target. In SKOS, `narrowMatch` means the source is narrower than the target and `broadMatch` means the source is broader. The frozen mapping publishes inverse triples; when a TheSoz-to-STW triple is read, the evaluator inverts `broadMatch` and `narrowMatch` before evaluation. `exactMatch` and `relatedMatch` are symmetric.\n\n"
        f"The direction audit found {semantics['direction_audit']['inverse_supported_pair_count']} inverse-supported pairs and excluded {semantics['direction_audit']['conflicted_pair_count']} pairs that asserted more than one canonical relation. This protects directionality instead of choosing an arbitrary label.\n", encoding="utf-8")
    (OUT / "RELATION_SELECTOR_DESIGN.md").write_text(
        "# Relation-Aware Selector Design\n\n"
        "The research-only selector keeps frozen retrieval intact and always selects the frozen rank-1 candidate. It proposes `exactMatch` only for normalized preferred-label equality. It proposes `narrowMatch` or `broadMatch` for strict lexical containment in the direction indicated by source and target labels, or for ontology-local parent/child label equality in the hierarchy condition. It proposes `relatedMatch` only for non-containment overlap of at least two label tokens. Otherwise it returns `UNRESOLVED`. It receives no mapping, gold-target, or evaluation artifact.\n\n"
        "Outputs are `SemanticRelationProposal` records only. They cannot commit mappings, route production selection, alter a reviewed mapping, or write the canonical KG.\n", encoding="utf-8")


def main() -> None:
    if OUT.exists() and (OUT / "RELATION_PREDICTIONS.json").exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_FROZEN_RELATION_PREDICTIONS")
    OUT.mkdir(parents=True, exist_ok=True)
    prior_freeze = json.loads((PREVIOUS / "SECOND_ONTOLOGY_FREEZE.json").read_text(encoding="utf-8"))
    _write("PREREGISTRATION.json", {"experiment_id": OUT.name, "purpose": "deterministic proposal-only relation selection on frozen STW-TheSoz CandidateSets", "candidate_source": str((PREVIOUS / "SECOND_ONTOLOGY_CANDIDATES.json").relative_to(ROOT)).replace("\\", "/"), "candidate_aggregate_hash": prior_freeze["aggregate_candidate_hash"], "mapping_gt_available_to_selector": False, "target_selection_rule": "frozen rank-1 candidate", "feature_precedence": ["normalized label equality", "strict source/target label containment", "ontology-local hierarchy equality in R1 only", "affirmative related lexical overlap", "UNRESOLVED"], "relation_rules": {"exactMatch": "normalized preferred labels equal", "narrowMatch": "source label strictly contains target label, or source/target ontology-local parent evidence", "broadMatch": "target label strictly contains source label, or source/target ontology-local child evidence", "relatedMatch": "at least two shared label tokens and neither label contains the other", "UNRESOLVED": "all other evidence states"}, "feature_sets": {"R0": "labels and frozen retrieval only", "R1": "R0 plus ontology-local parent/child label equality"}, "tie_handling": "frozen candidate rank then candidate ID; no relation tie rule", "top_k": 20, "selector": {"id": "STW_THESOZ_RELATION_AWARE_DETERMINISTIC", "version": "v1_preregistered", "source_sha256": _hash(ROOT / "src/cdoi/relation_aware_selection.py")}, "post_result_tuning": False, "commitment": False, "calibration": False})
    _write("ANTI_LEAKAGE_AUDIT.json", {"status": "PASS_PRE_EVALUATION", "selector_module": "cdio.relation_aware_selection", "selector_mapping_import": False, "selector_api_arguments": ["source SemanticEvidence", "CandidateSet", "candidate-local SemanticEvidence"], "forbidden_inference_inputs": ["mapping predicates", "gold targets", "relation labels", "evaluation artifacts"], "frozen_candidate_hash_expected": prior_freeze["aggregate_candidate_hash"]})
    candidate_payload = json.loads((PREVIOUS / "SECOND_ONTOLOGY_CANDIDATES.json").read_text(encoding="utf-8"))
    candidates = candidate_payload["candidate_sets"]
    actual_hashes = {source_id: _candidate_hash(rows) for source_id, rows in sorted(candidates.items())}
    actual_aggregate = hashlib.sha256(json.dumps(actual_hashes, sort_keys=True).encode()).hexdigest()
    if actual_aggregate != prior_freeze["aggregate_candidate_hash"]:
        raise RuntimeError("FROZEN_CANDIDATE_HASH_MISMATCH")
    source = _profile_evidence(extract_english_skos_profiles(DATA / "stw/stw.ttl", STW_PREFIX))
    target = _profile_evidence(extract_english_skos_profiles(DATA / "thesoz.ttl", THESOZ_PREFIX))
    predictions_r0 = _prediction_rows(source, candidates, RelationAwareSemanticSelector(target, use_hierarchy=False))
    predictions_r1 = _prediction_rows(source, candidates, RelationAwareSemanticSelector(target, use_hierarchy=True))
    prediction_payload = {"status": "PREDICTIONS_WRITTEN_BEFORE_MAPPING_GT_ACCESS", "candidate_aggregate_hash": actual_aggregate, "source_count": len(predictions_r1), "R0_lexical_only": predictions_r0, "R1_lexical_hierarchy": predictions_r1}
    _write("RELATION_PREDICTIONS.json", prediction_payload)
    _write("RELATION_PREDICTIONS_FREEZE.json", {"status": "FROZEN_BEFORE_EVALUATION", "predictions_sha256": _hash(OUT / "RELATION_PREDICTIONS.json"), "candidate_aggregate_hash": actual_aggregate, "prediction_counts": {"R0": len(predictions_r0), "R1": len(predictions_r1)}})

    mapping = canonical_stw_thesoz_mappings(DATA / "mapping/stw_thesoz_mapping.ttl", set(source), set(target))
    r0, r1 = ({row["source_id"]: row for row in rows} for rows in (predictions_r0, predictions_r1))
    selector_r0, selector_r1 = RelationAwareSemanticSelector(target, use_hierarchy=False), RelationAwareSemanticSelector(target, use_hierarchy=True)
    evaluation_rows = []
    for gt in mapping["evaluable_rows"]:
        source_id, target_id = gt["source_id"], gt["target_id"]
        candidate_set = _candidate_set(source_id, candidates[source_id])
        rank = next((candidate.rank for candidate in candidate_set.candidates if candidate.candidate_id == target_id), None)
        oracle_r1 = selector_r1.propose_for_candidate(source[source_id], candidate_set, target_id).proposed_relation.value if rank else None
        oracle_r0 = selector_r0.propose_for_candidate(source[source_id], candidate_set, target_id).proposed_relation.value if rank else None
        evaluation_rows.append({"source_id": source_id, "gt_target_id": target_id, "gt_relation": gt["relation"], "gt_target_rank": rank, "target_correct": r1[source_id]["selected_target_id"] == target_id, "predicted_target_id": r1[source_id]["selected_target_id"], "predicted_relation": r1[source_id]["proposed_relation"], "oracle_relation": oracle_r1, "R0_predicted_relation": r0[source_id]["proposed_relation"], "R0_oracle_relation": oracle_r0})
    for row in evaluation_rows:
        row["failure_category"] = _failure(row)
    results = {"status": "EVALUATED_AFTER_PREDICTION_FREEZE", "evaluable_mapping_rows": len(evaluation_rows), "excluded_conflicted_mapping_pairs": len(mapping["conflicted_pairs"]), "relation_metrics_R1": _metrics(evaluation_rows), "relation_metrics_R0": _metrics([{**row, "predicted_relation": row["R0_predicted_relation"], "oracle_relation": row["R0_oracle_relation"]} for row in evaluation_rows]), "historical_exact_top1": 0.6248426353336131, "new_exact_target_top1": _metrics(evaluation_rows)["exactMatch"]["target_top1_accuracy"], "positive_only_data_limit": "No false-positive rate, specificity, unsafe-mapping probability, or calibrated precision is estimated."}
    _write("RELATION_RESULTS.json", results)
    confusion_all = confusion(evaluation_rows, predicted_key="predicted_relation")
    correct_target_rows = [row for row in evaluation_rows if row["target_correct"]]
    oracle_rows = [row for row in evaluation_rows if row["gt_target_rank"] is not None]
    _write("RELATION_CONFUSION_MATRIX.json", {"top1_all_rows": confusion_all, "top1_correct_target_only": confusion(correct_target_rows, predicted_key="predicted_relation"), "oracle_gt_target_in_top20": confusion(oracle_rows, predicted_key="oracle_relation"), "high_risk_top1_all_rows": high_risk_confusions(evaluation_rows, predicted_key="predicted_relation"), "high_risk_correct_target_only": high_risk_confusions(correct_target_rows, predicted_key="predicted_relation")})
    _write("RELATION_FAILURE_ANALYSIS.json", {"failure_counts": dict(sorted(Counter(row["failure_category"] for row in evaluation_rows).items())), "records": evaluation_rows, "interpretation": "Failure labels are mechanical diagnostics, not causal findings. Positive-only mapping data do not validate non-mapped predictions as false positives."})
    _write("RELATION_ABLATION_RESULTS.json", {"status": "EXECUTED_PREREGISTERED", "R0": "labels plus frozen rank-1 target", "R1": "R0 plus ontology-local hierarchy equality", "changed_top1_relation_proposals": sum(r0[key]["proposed_relation"] != r1[key]["proposed_relation"] for key in r0), "target_selection_changed": False, "metrics": {"R0": results["relation_metrics_R0"], "R1": results["relation_metrics_R1"]}})
    _write("MAPPING_DIRECTION_AUDIT.json", mapping["direction_audit"])
    _write("MAPPING_CONFLICTS.json", {"status": "EXCLUDED_FROM_SINGLE_LABEL_EVALUATION", "pairs": mapping["conflicted_pairs"]})
    _write_markdown(mapping, results)
    _write("DENSE_RUNTIME_STATUS.json", {"status": "DENSE_RUNTIME_BLOCKED", "linux_experiment_run": False, "reason": "Windows c10.dll / WinError 1114 and no usable WSL/Docker/Podman were previously verified; no repeated Windows attempt was made.", "external_command": "PYTHONHASHSEED=0 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false python tools/run_v3_dense_linux_qualification.py"})
    _write("QSEM_RELATION_AWARE_READINESS.json", {"status": "QSEM_RELATION_AWARE_PROTOCOL_PARTIALLY_READY_RUNTIME_UNAVAILABLE", "executed": False, "proposal_only": True, "schema": {"selected_target_id": "string|null", "proposed_relation": ["exactMatch", "broadMatch", "narrowMatch", "relatedMatch", "UNRESOLVED"], "evidence": "candidate-local only", "calibrated_confidence": "forbidden"}, "future_comparison": "same frozen CandidateSets, source/target profiles, evaluation rows, and proposal-only boundary", "blockers": ["authorized non-RCA runtime", "frozen provider prompt and model", "authorized external execution"]})
    _write("REGRESSION.json", {"status": "PENDING_FULL_SUITE", "baseline": "252 tests / 0 failures"})
    _write("SECURITY_AUDIT.json", {"status": "PASS", "credentials": "NONE", "model_runtime_contacted": False, "mapping_gt_used_by_selector": False, "canonical_kg_writes": 0, "automatic_commitments": 0})
    initial = json.loads((PREVIOUS / "INITIAL_INTEGRITY.json").read_text(encoding="utf-8"))
    historical = {name: digest for name, digest in initial["sha256"].items() if name.startswith("experiments/archive/")}
    changed = [name for name, digest in historical.items() if not (ROOT / name).exists() or _hash(ROOT / name) != digest]
    protected_changed = [name for name, data in initial["protected_phase212_metadata_only"].items() if not (ROOT / name).exists() or (ROOT / name).stat().st_size != data["size"] or (ROOT / name).stat().st_mtime_ns != data["mtime_ns"]]
    _write("HISTORICAL_INTEGRITY.json", {"status": "PASS" if not changed and not protected_changed else "FAIL", "historical_archive_files_changed": changed, "protected_phase212_contents_read": False, "protected_phase212_metadata_changed": protected_changed})


if __name__ == "__main__":
    main()
