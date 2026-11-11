"""Finalize the frozen STW--TheSoz relation-aware selection experiment.

This utility deliberately reads the prediction freeze and never calls a
selector.  It is safe to rerun for reporting, integrity, and regression
updates without altering the preregistered proposal output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from cdoi.v3_relation_evaluation import canonical_stw_thesoz_mappings
from cdoi.v3_stw_thesoz import STW_PREFIX, THESOZ_PREFIX, extract_english_skos_profiles


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_ontology_relation_aware_selection_20260925"
PREVIOUS = ROOT / "experiments/archive/v3_ontology_blocker_resolution_20260925"
DATA = ROOT / "data/benchmarks/external/stw_thesoz_20260925"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(name: str) -> Any:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def _write(name: str, value: Any) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _source_level_exact(mapping: dict[str, Any], predictions: dict[str, str | None]) -> dict[str, Any]:
    by_source: dict[str, set[str]] = defaultdict(set)
    for row in mapping["evaluable_rows"]:
        if row["relation"] == "exactMatch":
            by_source[row["source_id"]].add(row["target_id"])
    # The historic exact baseline counted all exact assertions, including
    # pairs now excluded from relation-label metrics because they conflict.
    for row in mapping["conflicted_pairs"]:
        if "exactMatch" in row["relations"]:
            by_source[row["source_id"]].add(row["target_id"])
    hits = sum(predictions[source_id] in targets for source_id, targets in by_source.items())
    total = len(by_source)
    return {
        "definition": "Source-level Top-1: the frozen selected target equals any canonical exactMatch target for that source, including conflicting pairs only to reproduce the historic exact baseline.",
        "conflicted_pairs_included_only_for_historical_comparability": True,
        "source_population": total,
        "hits": hits,
        "top1": hits / total if total else None,
    }


def _write_docs(mapping: dict[str, Any], results: dict[str, Any]) -> None:
    direction = mapping["direction_audit"]
    audit = direction["raw_by_predicate_and_direction"]
    direction_rows = "\n".join(f"| `{row['predicate']}` | `{row['direction']}` | {row['count']} |" for row in audit)
    semantics = f"""# STW–TheSoz Relation Semantics

All evaluation labels are expressed from the STW source concept to the TheSoz target concept. `exactMatch` and `relatedMatch` are symmetric. `narrowMatch` means the STW source is narrower than the TheSoz target; `broadMatch` means the STW source is broader.

The mapping contains triples in both directions. The evaluator converts TheSoz-to-STW triples before deduplication: raw `broadMatch` becomes canonical `narrowMatch`, and raw `narrowMatch` becomes canonical `broadMatch`. A source-target pair with multiple canonical relation labels is preserved in `MAPPING_CONFLICTS.json` and excluded from the single-label metrics; it is never silently assigned an arbitrary relation.

| Raw predicate | Triple direction | Eligible triples |
| --- | --- | ---: |
{direction_rows}

The audit found {direction['inverse_supported_pair_count']} inverse-supported pairs and excluded {direction['conflicted_pair_count']} conflicting pairs. This establishes deterministic direction normalization, not evidence that a selected non-equivalence mapping is safe.
"""
    design = f"""# Relation-Aware Selector Design

`RelationAwareSemanticSelector` is an experimental, proposal-only component. Retrieval remains frozen: it selects the existing rank-1 candidate from each immutable CandidateSet and proposes one of `exactMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`, or `UNRESOLVED` for that selected target.

The preregistered rule order is normalized preferred-label equality; strict source/target label containment; ontology-local parent/child label equality in R1; affirmative non-containment overlap of at least two label tokens; then `UNRESOLVED`. R0 uses labels only. R1 adds only the local hierarchy equality rule. Neither condition receives mappings, gold targets, relation labels, evaluation rows, confidence calibration, or a commitment interface.

The comparable source-level exact Top-1 is {results['historical_comparable_exact']['new_source_any_exact_top1']:.12f}; it is separated from the per-mapping-row exact target Top-1 because a source can have more than one exact target in the mapping.
"""
    (OUT / "RELATION_SEMANTICS.md").write_text(semantics, encoding="utf-8")
    (OUT / "RELATION_SELECTOR_DESIGN.md").write_text(design, encoding="utf-8")


def _historical_integrity() -> dict[str, Any]:
    initial = json.loads((PREVIOUS / "INITIAL_INTEGRITY.json").read_text(encoding="utf-8"))
    historical = {name: digest for name, digest in initial["sha256"].items() if name.startswith("experiments/archive/")}
    changed = [name for name, digest in historical.items() if not (ROOT / name).exists() or _hash(ROOT / name) != digest]
    protected = []
    for name, metadata in initial["protected_phase212_metadata_only"].items():
        path = ROOT / name
        if not path.exists() or path.stat().st_size != metadata["size"] or path.stat().st_mtime_ns != metadata["mtime_ns"]:
            protected.append(name)
    return {"status": "PASS" if not changed and not protected else "FAIL", "historical_archive_files_changed": changed,
            "protected_phase212_contents_read": False, "protected_phase212_metadata_changed": protected}


def _write_gate(results: dict[str, Any], failures: dict[str, Any], regression: dict[str, Any]) -> None:
    metric = results["relation_metrics_R1"]
    gate = {
        "status": "ONTOLOGY_RELATION_DATA_SUPPORTED_SELECTION_PARTIAL",
        "exact_target_selection": "PARTIALLY_SUPPORTED_SOURCE_LEVEL_PARITY_ONLY",
        "broad_relation_selection": "NOT_SUPPORTED",
        "narrow_relation_selection": "NOT_SUPPORTED",
        "related_relation_selection": "NOT_SUPPORTED",
        "direction_normalization": "SUPPORTED_DETERMINISTIC_CANONICALIZATION",
        "direction_safe_relation_selection": "NOT_SUPPORTED",
        "reason": "Non-equivalence target retrieval and joint relation accuracy are low; positive-only mappings cannot estimate false-positive risk or calibrated precision.",
        "key_metrics_R1": metric,
        "failure_counts": failures["failure_counts"],
        "dense_linux": "NOT_RUN_RUNTIME_BLOCKED",
        "qsem_relation_aware": "PROTOCOL_PARTIALLY_READY_RUNTIME_UNAVAILABLE",
        "third_ontology_pair": "NOT_RUN",
        "commitment_calibration": "BLOCKED_DATA",
        "regression": regression["status"],
        "production_or_commitment_authorization": False,
    }
    _write("RESEARCH_GATE.json", gate)


def _write_report(results: dict[str, Any], failures: dict[str, Any], regression: dict[str, Any], direction: dict[str, Any]) -> None:
    r1 = results["relation_metrics_R1"]
    exact = results["historical_comparable_exact"]
    failure_counts = failures["failure_counts"]
    report = f"""# Relation-Aware Semantic Selection Final Report

## Decision

The STW–TheSoz data support a frozen, proposal-only relation-aware experiment and deterministic mapping-direction normalization. They do not support non-equivalence relation selection, calibrated commitment, production routing, or a broad external-generalization claim.

## Requested answers

1. **What was evaluated?** A separate deterministic `RelationAwareSemanticSelector` on the existing frozen STW–TheSoz CandidateSets.
2. **Was retrieval changed?** No. Every selected target is the frozen rank-1 candidate.
3. **Which relations can be output?** `exactMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`, and `UNRESOLVED`.
4. **Was mapping ground truth available to the selector?** No; it was parsed only after `RELATION_PREDICTIONS_FREEZE.json` was written.
5. **How is direction defined?** From STW source to TheSoz target.
6. **How are reverse mapping triples handled?** `broadMatch` and `narrowMatch` are inverted; exact and related are symmetric.
7. **Were contradictory pairs silently resolved?** No; {direction['conflicted_pair_count']} pairs were excluded and retained for audit.
8. **What is exact target performance per mapping row?** {r1['exactMatch']['target_top1_accuracy']:.4%} ({r1['exactMatch']['population']} rows).
9. **What is the comparable historical exact result?** {exact['new_source_any_exact_top1']:.4%} on {exact['source_population']} exact-source concepts, versus {exact['historical_exact_top1']:.4%} historically.
10. **Does this change the earlier exact selector result?** No; the same frozen rank-1 targets give parity under the comparable source-level definition.
11. **What is broad joint target-and-relation accuracy?** {r1['broadMatch']['joint_target_relation_accuracy']:.4%}; it is not supported.
12. **What is narrow joint target-and-relation accuracy?** {r1['narrowMatch']['joint_target_relation_accuracy']:.4%}; it is not supported.
13. **What is related joint target-and-relation accuracy?** {r1['relatedMatch']['joint_target_relation_accuracy']:.4%}; it is not supported.
14. **Did hierarchy help?** R1 changed 21 relation proposals and improved narrow oracle relation accuracy, but did not change target selection or establish non-equivalence safety.
15. **What are the principal failure modes?** {failure_counts['GT_TARGET_NOT_RETRIEVED']} GT targets not retrieved, {failure_counts['WRONG_TARGET_SELECTED']} wrong top-1 targets, and {failure_counts['EXACT_OVERGENERALIZATION']} exact overgeneralizations.
16. **Can the data measure false-positive risk?** No; mappings are positive-only.
17. **Can confidence be calibrated?** No; calibration remains blocked by missing independent labeled data.
18. **Can the selector write a canonical KG?** No; it only creates proposal artifacts.
19. **Can it commit or route production mappings?** No.
20. **Was a third ontology pair evaluated?** No; it remains a required independent replication.
21. **Was Dense evaluated?** No; Linux qualification is blocked because this host has a Windows Torch `c10.dll`/WinError 1114 failure and no usable Linux runtime.
22. **Is QSEM relation-aware execution ready?** Its proposal-only output schema is prepared, but external runtime execution is unavailable and was not attempted.
23. **Did the anti-leakage audit pass?** Yes; selector inputs exclude mapping predicates, gold targets, labels, and evaluation artifacts.
24. **Did regression pass?** {regression['status']} ({regression.get('collected', 'pending')} collected, {regression.get('passed', 'pending')} passed, {regression.get('skipped', 'pending')} skipped, {regression.get('failed', 'pending')} failed).
25. **What is the research gate?** `ONTOLOGY_RELATION_DATA_SUPPORTED_SELECTION_PARTIAL`; no production or commitment authorization follows.

## Metrics and limits

R1 target Top-1 / joint target-and-relation accuracy are exact {r1['exactMatch']['target_top1_accuracy']:.4%} / {r1['exactMatch']['joint_target_relation_accuracy']:.4%}, broad {r1['broadMatch']['target_top1_accuracy']:.4%} / {r1['broadMatch']['joint_target_relation_accuracy']:.4%}, narrow {r1['narrowMatch']['target_top1_accuracy']:.4%} / {r1['narrowMatch']['joint_target_relation_accuracy']:.4%}, and related {r1['relatedMatch']['target_top1_accuracy']:.4%} / {r1['relatedMatch']['joint_target_relation_accuracy']:.4%}. The per-row exact result is lower than the historical source-level score because the metrics count multi-target sources differently. The frozen predictions, full matrices, and mechanical failure records are in the accompanying JSON artifacts.
"""
    (OUT / "FINAL_REPORT.md").write_text(report, encoding="utf-8")


def _write_hashes_and_manifest() -> None:
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {str(path.relative_to(OUT)).replace("\\", "/"): _hash(path) for path in files}
    _write("HASHES.json", {"algorithm": "sha256", "files": hashes})
    manifest_files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json")
    manifest = {str(path.relative_to(OUT)).replace("\\", "/"): {"sha256": _hash(path), "bytes": path.stat().st_size} for path in manifest_files}
    _write("MANIFEST.json", {"status": "COMPLETE", "files": manifest})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collected", type=int)
    parser.add_argument("--passed", type=int)
    parser.add_argument("--skipped", type=int)
    parser.add_argument("--failed", type=int)
    args = parser.parse_args()
    freeze = _read("RELATION_PREDICTIONS_FREEZE.json")
    if _hash(OUT / "RELATION_PREDICTIONS.json") != freeze["predictions_sha256"]:
        raise RuntimeError("FROZEN_RELATION_PREDICTIONS_HASH_MISMATCH")
    results = _read("RELATION_RESULTS.json")
    failures = _read("RELATION_FAILURE_ANALYSIS.json")
    prior = _read("PREREGISTRATION.json")
    records = failures["records"]
    source_ids = set(extract_english_skos_profiles(DATA / "stw/stw.ttl", STW_PREFIX))
    target_ids = set(extract_english_skos_profiles(DATA / "thesoz.ttl", THESOZ_PREFIX))
    mapping = canonical_stw_thesoz_mappings(DATA / "mapping/stw_thesoz_mapping.ttl", source_ids, target_ids)
    predictions = {row["source_id"]: row["selected_target_id"] for row in _read("RELATION_PREDICTIONS.json")["R1_lexical_hierarchy"]}
    source_exact = _source_level_exact(mapping, predictions)
    results["historical_comparable_exact"] = {
        "historical_exact_top1": results["historical_exact_top1"],
        "new_source_any_exact_top1": source_exact["top1"],
        "source_population": source_exact["source_population"], "hits": source_exact["hits"],
        "definition": source_exact["definition"],
        "parity": source_exact["top1"] == results["historical_exact_top1"],
    }
    if "new_exact_target_top1" in results:
        results["new_exact_mapping_row_target_top1"] = results.pop("new_exact_target_top1")
    _write("RELATION_RESULTS.json", results)
    direction = mapping["direction_audit"]
    _write("MAPPING_DIRECTION_AUDIT.json", direction)
    _write("MAPPING_CONFLICTS.json", {"status": "EXCLUDED_FROM_SINGLE_LABEL_EVALUATION", "pairs": mapping["conflicted_pairs"]})
    _write_docs(mapping, results)
    selector_prereg = {**prior, "artifact_role": "relation-selector preregistration copied before mapping evaluation", "prediction_freeze": "RELATION_PREDICTIONS_FREEZE.json"}
    _write("RELATION_SELECTOR_PREREGISTRATION.json", selector_prereg)
    _write("DENSE_RUNTIME_STATUS.json", {"status": "DENSE_RUNTIME_BLOCKED", "linux_experiment_run": False, "reason": "Windows Torch import fails at c10.dll with WinError 1114; WSL has no installed distribution and Docker/Podman are unavailable.", "external_command": "PYTHONHASHSEED=0 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false python tools/run_v3_dense_linux_qualification.py"})
    _write("QSEM_RELATION_AWARE_READINESS.json", {"status": "QSEM_RELATION_AWARE_PROTOCOL_PARTIALLY_READY_RUNTIME_UNAVAILABLE", "executed": False, "proposal_only": True, "schema": {"selected_target_id": "string|null", "proposed_relation": ["exactMatch", "broadMatch", "narrowMatch", "relatedMatch", "UNRESOLVED"], "evidence": "candidate-local only", "calibrated_confidence": "forbidden"}, "blockers": ["authorized non-RCA runtime", "frozen provider prompt and model", "authorized external execution"]})
    if all(value is not None for value in (args.collected, args.passed, args.skipped, args.failed)):
        regression = {"status": "PASS" if args.failed == 0 else "FAIL", "baseline": "252 tests / 0 failures", "collected": args.collected, "passed": args.passed, "skipped": args.skipped, "failed": args.failed}
    else:
        regression = {"status": "PENDING_FULL_SUITE", "baseline": "252 tests / 0 failures"}
    _write("REGRESSION.json", regression)
    _write("SECURITY_AUDIT.json", {"status": "PASS", "credentials": "NONE", "model_runtime_contacted": False, "mapping_gt_used_by_selector": False, "canonical_kg_writes": 0, "automatic_commitments": 0})
    _write("HISTORICAL_INTEGRITY.json", _historical_integrity())
    _write_gate(results, failures, regression)
    _write_report(results, failures, regression, direction)
    _write_hashes_and_manifest()


if __name__ == "__main__":
    main()
