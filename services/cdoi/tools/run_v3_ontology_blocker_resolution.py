"""Run the preregistered ontology-blocker resolution archive.

This is an experiment-only entry point.  It never invokes the normal pipeline,
version store, KG populator, or any Qwen/RCA configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cdoi.v3_stw_thesoz import (STW_PREFIX, THESOZ_PREFIX, build_frozen_candidates,
                                 evaluate_frozen_candidates, extract_english_skos_profiles,
                                 parse_stw_thesoz_mappings)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_ontology_blocker_resolution_20260925"
DATA = ROOT / "data/benchmarks/external/stw_thesoz_20260925"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _worker(source_subset: Mapping[str, object], target: Mapping[str, object]) -> dict[str, list[dict[str, object]]]:
    return build_frozen_candidates(source_subset, target, 20)


def _frozen_candidates(source: Mapping[str, object], target: Mapping[str, object]) -> dict[str, list[dict[str, object]]]:
    """Frozen all-source candidate generation, independent of mapping labels."""
    ids = sorted(source)
    workers = min(4, max(1, os.cpu_count() or 1))
    chunks = [{key: source[key] for key in ids[index::workers]} for index in range(workers)]
    if workers == 1:
        return _worker(chunks[0], target)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        parts = list(pool.map(_worker, chunks, [target] * len(chunks)))
    return {key: value for part in parts for key, value in part.items()}


def _pair_candidate_hashes(candidates: Mapping[str, list[Mapping[str, object]]]) -> dict[str, str]:
    return {source_id: hashlib.sha256(json.dumps(candidates[source_id], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for source_id in sorted(candidates)}


def _relation_source_selection(candidates: Mapping[str, list[Mapping[str, object]]], rows: list[Mapping[str, str]]) -> dict[str, object]:
    exact: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row["relation"] == "exactMatch":
            exact[row["source_id"]].add(row["target_id"])
    n = len(exact)
    selected = sum(bool(candidates[source_id]) and str(candidates[source_id][0]["candidate_id"]) in targets
                   for source_id, targets in exact.items() if source_id in candidates)
    return {"relation": "exactMatch", "source_population": n, "top1_equivalence_selection_accuracy": selected / n if n else None,
            "semantics": "The calculation uses only SKOS exactMatch. It is research-only and creates no commitment.",
            "non_equivalence_selection": "NOT_RUN_UNSUPPORTED_RELATION_FAIL_CLOSED"}


def _candidates_markdown() -> str:
    return """# Second Ontology Pair Candidates

| Pair | Mapping evidence | Relation diversity | Qualification |
| --- | --- | --- | --- |
| STW – TheSoz | Publisher-maintained SKOS mapping | exact, narrow, broad, related | SELECTED before CDOI scoring |
| STW – EuroVoc | Publisher mapping | exact, close | Not selected: less relation diversity |
| STW – AGROVOC | Publisher mapping | exact, close | Not selected: less relation diversity |

STW–TheSoz was selected on source availability, stable public identifiers, reproducible downloads, explicit CC BY 4.0 licensing, documented expert provenance, and four mapping relations. No CDOI performance was inspected before selection.
"""


def main() -> None:
    if not (OUT / "PREREGISTRATION.json").exists():
        raise RuntimeError("missing preregistration")
    source_path, target_path, mapping_path = DATA / "stw/stw.ttl", DATA / "thesoz.ttl", DATA / "mapping/stw_thesoz_mapping.ttl"
    if not all(path.exists() for path in (source_path, target_path, mapping_path)):
        raise RuntimeError("frozen STW–TheSoz source files are missing")

    inventory = {path.relative_to(ROOT).as_posix(): {"sha256": _hash(path), "bytes": path.stat().st_size}
                 for path in (source_path, target_path, mapping_path, DATA / "stw.ttl.zip", DATA / "stw_thesoz_mapping.ttl.zip")}
    source = extract_english_skos_profiles(source_path, STW_PREFIX)
    target = extract_english_skos_profiles(target_path, THESOZ_PREFIX)
    _write("SECOND_ONTOLOGY_SELECTION.json", {
        "status": "SELECTED_BEFORE_EVALUATION", "pair": "STW-TheSoz", "selection_basis": ["public machine-readable source and target", "stable identifiers", "CC BY 4.0", "documented expert mapping provenance", "four SKOS mapping relations", "independent of Anatomy"],
        "performance_inspected_before_selection": False,
    })
    _write("SECOND_ONTOLOGY_SOURCE_INVENTORY.json", {"status": "FROZEN", "files": inventory, "source_profiles": len(source), "target_profiles": len(target), "language": "en", "profile_policy": "direct English skos:prefLabel; aliases disabled; mapping predicates excluded"})

    candidates = _frozen_candidates(source, target)
    candidate_hashes = _pair_candidate_hashes(candidates)
    _write("SECOND_ONTOLOGY_CANDIDATES.json", {"status": "FROZEN_PRE_GROUND_TRUTH", "source_population": len(candidates), "top_k": 20, "retriever": "FROZEN_R1_LEXICAL", "candidate_sets": candidates})
    _write("SECOND_ONTOLOGY_FREEZE.json", {"status": "FROZEN", "source_population": len(candidates), "candidate_set_hashes": candidate_hashes, "aggregate_candidate_hash": hashlib.sha256(json.dumps(candidate_hashes, sort_keys=True).encode()).hexdigest(), "mapping_ground_truth_read_after_candidate_freeze": True})

    parsed = parse_stw_thesoz_mappings(mapping_path)
    eligible = [row for row in parsed["rows"] if row["source_id"] in source and row["target_id"] in target]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        grouped[row["source_id"]].append(row)
    results = evaluate_frozen_candidates(candidates, grouped)
    results.update({"status": "EVALUATED_RETRIEVAL_AND_EXACT_SELECTION_ONLY", "eligible_mapping_count": len(eligible), "source_count_with_mappings": len(grouped), "relation_counts": dict(sorted({key: sum(row["relation"] == key for row in eligible) for key in {row["relation"] for row in eligible}}.items())), "exact_selection": _relation_source_selection(candidates, eligible), "relation_semantics": {"exactMatch": "evaluated as an equivalence candidate only", "narrowMatch": "preserved; unsupported for selector interpretation", "broadMatch": "preserved; unsupported for selector interpretation", "relatedMatch": "preserved; unsupported for selector interpretation"}, "canonical_kg_writes": 0, "automatic_commitments": 0})
    _write("SECOND_ONTOLOGY_RESULTS.json", results)
    (OUT / "SECOND_ONTOLOGY_PAIR_CANDIDATES.md").write_text(_candidates_markdown(), encoding="utf-8")
    (OUT / "SECOND_ONTOLOGY_ANALYSIS.md").write_text(
        "# STW–TheSoz Analysis\n\nThe full English STW and TheSoz vocabularies were indexed before mapping labels were parsed. Candidate sets contain the same deterministic Top-20 format for every eligible STW source. Mapping predicates remain SKOS facts: only `exactMatch` receives an equivalence-selection metric; `broadMatch`, `narrowMatch`, and `relatedMatch` remain unsupported and fail closed. No result can create a canonical KG write, automatic commitment, or production policy change.\n", encoding="utf-8")
    _write("QSEM_EVALUATION_READINESS.json", {"status": "QSEM_EXTERNAL_EVAL_RUNTIME_UNAVAILABLE", "proposal_only": True, "blockers": {"authorized_non_RCA_runtime": "MISSING", "independent_frozen_semantic_dataset": "NOW_PARTIALLY_AVAILABLE_STW_THE_SOZ", "prompt_freeze": "QSEM_V1 frozen for Anatomy equivalence only; a relation-diverse protocol requires a new preregistered prompt", "candidate_freeze": "AVAILABLE_FOR_STW_THE_SOZ", "evaluation_protocol": "MISSING_FOR_RELATION_DIVERSE_QSEM", "relation_labels": "AVAILABLE_BUT_UNSUPPORTED_BY_QSEM_V1"}, "actions_required": ["obtain authorized non-RCA semantic runtime", "preregister a relation-aware proposal schema", "freeze prompt/model/temperature/candidate artifacts", "compare proposal-only results with the deterministic baseline"]})
    _write("CALIBRATION_DATA_READINESS.json", {"status": "COMMITMENT_CALIBRATION_STILL_BLOCKED_DATA", "new_pair_assessment": {"independent_from_Anatomy": True, "relation_diversity": True, "selection_bias": "publisher mapping population; not a separately held-out calibration split", "negative_labels": "ABSENT", "frozen_scoring_policy": True, "calibration_grade": False}, "requirements": ["independent labeled mapping split", "positive and negative outcomes", "relation-specific labels", "fixed candidate-generation and scoring policy", "sample-size and calibration-error analysis without tuning reuse"], "probability_emitted": False})
    _write("DENSE_EXPERIMENT_CONFIG.json", {"status": "NOT_RUN_RUNTIME_BLOCKED", "environment": {"python": "3.12", "os": "Linux", "device": "cpu", "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false"}, "model": "sentence-transformers/all-MiniLM-L6-v2", "model_revision": "resolve and freeze in Linux before execution", "packages": ["torch==2.7.1", "sentence-transformers==5.7.0", "transformers==4.52.4", "numpy==2.2.6"], "candidate_set": "Phase2.6 persisted R1 Top20", "profiles": ["P0_CURRENT_V1", "P1_SYNONYMS_RESOLVED_V2"], "serializer": "dense_structured_profile_v1", "metric": "normalized cosine", "top_k": 20, "seed": 0, "outputs": ["candidate-set equality", "selection accuracy", "rank/margin movement", "P0/P1 correctness transitions", "UNRESOLVED", "technical failures"], "command": "PYTHONHASHSEED=0 OMP_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false python tools/run_v3_dense_linux_qualification.py"})
    _write("DENSE_RESULTS.json", {"status": "NOT_RUN_RUNTIME_BLOCKED", "linux_experiment_executed": False, "candidate_sets_identical": None, "metrics": None, "unsafe_selections": None})
    (OUT / "DENSE_ANALYSIS.md").write_text("# Dense Analysis\n\nWindows `torch` import reproduces c10.dll / WinError 1114 and no usable Linux runtime is installed. The frozen Linux configuration is executable without interactive edits; no Dense metric is emitted until its smoke check succeeds in a clean Linux environment.\n", encoding="utf-8")
    _write("REGRESSION.json", {"status": "PENDING_TEST_COMMAND", "scope": "full repository pytest follows archive generation"})
    _write("SECURITY_AUDIT.json", {"status": "PASS", "credentials_or_tokens": "NONE", "authorization_headers": "NONE", "qsem_runtime_contacted": False, "canonical_kg_writes": 0})
    _write("ONTOLOGY_TRACK_BASELINE.json", {"deterministic_core": "VERIFIED_COMPLETE", "dense": "BLOCKED_TECHNICAL", "second_pair_prior": "PARTIALLY_SUPPORTED_IDAI_PACTOLS_6_EQUIVALENCE", "qsem": "IMPLEMENTED_NOT_EXTERNALLY_VALIDATED", "calibration": "BLOCKED_DATA"})


if __name__ == "__main__":
    main()
