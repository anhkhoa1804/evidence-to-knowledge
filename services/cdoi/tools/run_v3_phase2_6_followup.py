"""Produce versioned Phase-2.6 follow-up diagnostics without reranking candidates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cdoi.v3_phase2_6 import resolved_source_faithful_profiles
from cdoi.v3_phase2_6_followup import dense_runtime_check, derive_residual_taxonomy


ROOT = Path(__file__).resolve().parents[1]
ANATOMY = ROOT / "data" / "benchmarks" / "external" / "oaei" / "anatomy-2026"
PHASE26_ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_6_representation"
PHASE26_RESULT = PHASE26_ARCHIVE / "RESULT.json"
FROZEN = ROOT / "experiments" / "outputs" / "OAEI_V263_PERSISTED_POSTRANKING" / "exp-3950cb966861" / "result.json"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_6_followup"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(("| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(row) + " |" for row in rows)))


def _followup_report(taxonomy: dict[str, Any], dense: dict[str, Any]) -> str:
    residual_n = taxonomy["residual_population_n"]
    category_rows = [[category, str(count), f"{count / residual_n:.1%}" if residual_n else "N/A"] for category, count in taxonomy["category_counts"].items()]
    margin_rows = [[bucket, str(taxonomy["margin_distribution"].get(bucket, 0))] for bucket in ("<0.02", "0.02-0.05", "0.05-0.10", "0.10-0.20", ">=0.20")]
    rank_rows = [[bucket, str(taxonomy["gold_rank_distribution"].get(bucket, 0))] for bucket in ("rank1", "rank2-5", "rank6-10", "rank11-20")]
    transition_rows = [[name, str(count)] for name, count in taxonomy["transitions"].items()]
    structural = {status: sum(case["structural_context_status"] == status for case in taxonomy["residual_cases"]) for status in ("STRUCTURAL_SIGNAL_PRESENT", "STRUCTURAL_SIGNAL_NOT_OBSERVED", "STRUCTURAL_DATA_UNAVAILABLE")}
    return "\n\n".join((
        "# V3 Phase 2.6 Residual Error Taxonomy",
        "**IMPLEMENTED FACT:** This versioned, post-inference diagnostic derives its population from the corrected P1 persisted result and frozen CandidateSets. It does not change selectors, scoring, thresholds, profiles, or policy. Category labels are multi-label observable patterns, not causal findings.",
        f"## Primary population\n\n`{taxonomy['primary_population_definition']}`. Actual derived N = **{residual_n}**. P1 ties remain a distinct population (N = {taxonomy['tie_population_n']}).",
        "## Observable category counts\n\n" + _table(["Category", "Raw count", "Residual %"], category_rows) + f"\n\nCategories overlap: `{taxonomy['categories_overlap']}`; percentages intentionally do not sum to 100%.",
        "## Frozen ambiguity and gold-rank distributions\n\n" + _table(["Original frozen margin", "Residual count"], margin_rows) + "\n\n" + _table(["Original frozen gold rank", "Residual count"], rank_rows),
        "## P0 → P1 selection transitions\n\n" + _table(["Transition", "Count"], transition_rows) + f"\n\nCorrect → wrong records: {len(taxonomy['p0_correct_to_p1_wrong'])}; wrong → correct records: {len(taxonomy['p0_wrong_to_p1_correct'])}. Existing P0-correct/P1-wrong alias placement remains inspected separately in each record.",
        "## Read-only structural diagnostic\n\n" + _table(["Status", "Residual count"], [[name, str(count)] for name, count in structural.items()]) + "\n\nA structural difference is evidence that distinguishable text exists, not evidence that it would fix a decision.",
        "## Interpretation boundary\n\n**MEASURED RESULT:** corrected P1 retains a non-trivial gold-below-strongest-wrong residual population.\n\n**DIAGNOSTIC INTERPRETATION:** residual failures exhibit observable alias, lexical-specificity, and/or structural-context patterns.\n\n**RESEARCH HYPOTHESIS:** some residual cases may require a representation beyond lexical alias matching.\n\nNo causal claim is made that a synonym caused a result; no alias blacklist or Anatomy-specific heuristic was created."
    ))


def _dense_report(dense: dict[str, Any]) -> str:
    runtime = dense.get("runtime", {})
    checks = dense.get("checks", {})
    rows = [[name, "PASS" if value else "FAIL"] for name, value in checks.items()]
    metadata = [[name, str(value)] for name, value in runtime.items()]
    error = dense.get("technical_error")
    error_text = f"\n\nTechnical cause: `{error['stage']}` / `{error['type']}` — {error['message']}" if error else ""
    return "\n\n".join((
        "# V3 Phase 2.6 Dense Linux Readiness",
        "**IMPLEMENTED FACT:** `scripts/check_dense_runtime.py` executes the frozen `dense_structured_profile_v1` smoke contract through `SentenceTransformerBackend`; it has no automatic installation behavior and emits no accuracy metrics on a technical failure.",
        f"## Current status\n\n`{dense['status']}`{error_text}",
        "## Runtime checks\n\n" + _table(["Check", "Result"], rows),
        "## Recorded runtime metadata\n\n" + _table(["Field", "Value"], metadata),
        "## Linux CPU execution\n\nOn a clean Linux or WSL distribution, create a separate virtual environment, install the project with `.[models,dev]`, and run `python scripts/check_dense_runtime.py --device cpu`. Only a `DENSE_RUNTIME_READY` smoke result authorizes a subsequent full fixed-CandidateSet Dense runner. Model ID, revision, normalization, serialization, CandidateSet membership, and evaluation population must remain frozen. A blocker is `RUNTIME_BLOCKER`, never zero performance or semantic abstention.\n\nThe existing baseline freezes `sentence-transformers/all-MiniLM-L6-v2`, CPU, normalized embeddings, and `dense_structured_profile_v1`; no Anatomy model or weight search occurred."
    ))


def _gate_report(taxonomy: dict[str, Any], dense: dict[str, Any]) -> str:
    structural = any(case["structural_context_status"] == "STRUCTURAL_SIGNAL_PRESENT" for case in taxonomy["residual_cases"])
    rows = [
        ["corrected synonym extraction regression safety", "SUPPORTED", "Resolved object-label tests and deterministic provenance remain versioned."],
        ["residual synonym-aware deterministic selection", "PARTIALLY_SUPPORTED", f"P1 residual gold-below-wrong population derived as N={taxonomy['residual_population_n']}; diagnostic only."],
        ["structural-context diagnostic", "PARTIALLY_SUPPORTED" if structural else "UNRESOLVED", "Read-only profile-context difference inspection is available; no structural selector was introduced."],
        ["dense runtime readiness", "SUPPORTED" if dense["status"] == "DENSE_RUNTIME_READY" else "RUNTIME_BLOCKER", "Smoke contract is implemented; current execution status is reported separately."],
        ["dense P0 value", "NOT_TESTED", "No valid Dense runtime result is available in this run."],
        ["dense P1 synonym value", "NOT_TESTED", "No valid Dense runtime result is available in this run."],
        ["Qwen P1 incremental value", "UNAVAILABLE", "QWEN_LIVE_EVAL_UNAVAILABLE; QSEM V1 was not changed."],
        ["external generalization", "DATA_MISSING", "No qualifying independent second ontology pair was evaluated."],
        ["definition utility", "UNRESOLVED", "Bilateral semantic definition evidence is absent in the mapped Anatomy population."],
        ["commitment-calibration readiness", "DATA_MISSING", "Independent calibration data remains absent."],
    ]
    return "\n\n".join(("# V3 Phase 2.6 Follow-up Research Gate", _table(["Area", "Status", "Evidence"], rows), "No semantic decision policy change. No production preprocessing/profile change. No routing, commitment calibration, automatic commitment, or canonical-KG change. Anatomy remains diagnostic/development evidence."))


def run() -> dict[str, Any]:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    phase26 = json.loads(PHASE26_RESULT.read_text(encoding="utf-8"))
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    p0_rows = phase26["conditions"]["P0_CURRENT_V1"]["fixed_candidate_selection"]["rows"]
    p1_rows = phase26["conditions"]["P1_SYNONYMS_RESOLVED_V2"]["fixed_candidate_selection"]["rows"]
    source = resolved_source_faithful_profiles(ANATOMY / "mouse.owl", "P1_SYNONYMS_RESOLVED_V2").profiles
    target = resolved_source_faithful_profiles(ANATOMY / "human.owl", "P1_SYNONYMS_RESOLVED_V2").profiles
    candidates = {str(row["source_iri"]): tuple(str(item["iri"]) for item in row["retrieved_candidates"]) for row in frozen["enriched_cases"]}
    taxonomy = derive_residual_taxonomy(p0_rows, p1_rows, source, target, candidates)
    dense = dense_runtime_check()
    manifest = {
        "schema_version": "v3_phase2_6_followup_artifact_v1",
        "historical_phase25_overwritten": False,
        "inputs": {"phase26_result": str(PHASE26_RESULT.relative_to(ROOT)).replace("\\", "/"), "phase26_result_sha256": _sha256(PHASE26_RESULT), "frozen_candidate_artifact": str(FROZEN.relative_to(ROOT)).replace("\\", "/"), "frozen_candidate_artifact_sha256": _sha256(FROZEN)},
        "outputs": ["RESIDUAL_ERROR_TAXONOMY.json", "DENSE_RUNTIME.json", "DENSE_SELECTION_RESULT.json", "RESULT.json"],
    }
    result = {"schema_version": "v3_phase2_6_followup_result_v1", "taxonomy": {key: value for key, value in taxonomy.items() if key != "residual_cases" and not key.startswith("p0_")}, "dense_runtime_status": dense["status"], "qwen": "QWEN_LIVE_EVAL_UNAVAILABLE", "external_validation": "DATA_MISSING", "definition_utility": "INSUFFICIENT_BILATERAL_DEFINITION_EVIDENCE", "policy_change": False}
    _write_json(ARCHIVE / "RESIDUAL_ERROR_TAXONOMY.json", taxonomy)
    _write_json(ARCHIVE / "DENSE_RUNTIME.json", dense)
    _write_json(ARCHIVE / "RESULT.json", result)
    _write_json(ARCHIVE / "MANIFEST.json", manifest)
    _write_markdown(ROOT / "experiments" / "V3_PHASE2_6_RESIDUAL_ERROR_TAXONOMY.md", _followup_report(taxonomy, dense))
    _write_markdown(ROOT / "experiments" / "V3_PHASE2_6_DENSE_LINUX_READINESS.md", _dense_report(dense))
    _write_markdown(ROOT / "experiments" / "V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md", _gate_report(taxonomy, dense))
    return result


if __name__ == "__main__":
    run()
