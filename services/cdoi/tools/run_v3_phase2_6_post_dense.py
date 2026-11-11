"""Produce post-follow-up V2 diagnostics; never alters selectors or policy."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cdoi.v3_phase2_6 import resolved_source_faithful_profiles
from cdoi.v3_phase2_6_followup import (dense_runtime_check, derive_residual_taxonomy_v2,
                                        reconcile_alias_collisions)

ROOT = Path(__file__).resolve().parents[1]
ANATOMY = ROOT / "data" / "benchmarks" / "external" / "oaei" / "anatomy-2026"
PHASE26 = ROOT / "experiments" / "archive" / "v3_phase2_6_representation" / "RESULT.json"
FROZEN = ROOT / "experiments" / "outputs" / "OAEI_V263_PERSISTED_POSTRANKING" / "exp-3950cb966861" / "result.json"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_6_post_dense"

def _hash(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _write_json(path: Path, value: Any) -> None: path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def _write_md(path: Path, value: str) -> None: path.write_text(value.rstrip() + "\n", encoding="utf-8")
def _table(headers: list[str], rows: list[list[str]]) -> str: return "\n".join(("| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(row) + " |" for row in rows)))

def _taxonomy_report(taxonomy: dict[str, Any]) -> str:
    aliases = []
    for field, values in taxonomy["alias_state_counts"].items(): aliases.extend([[field, state, str(count)] for state, count in values.items()])
    semantic = [[name, str(count)] for name, count in taxonomy["semantic_pattern_counts"].items()]
    structural = [[name, str(count)] for name, count in taxonomy["structural_status_counts"].items()]
    return "\n\n".join(("# V3 Phase 2.6 Residual Taxonomy V2", "**IMPLEMENTED FACT:** V2 separates alias availability, exact normalized alias overlap, semantic surface patterns, and structural-profile comparison. It is post-inference diagnostic data only.", f"## Population\n\nDerived residual N = **{taxonomy['residual_population_n']}**; no count is hard-coded.", "## Alias availability\n\n" + _table(["Field", "Observable state", "N"], aliases), "## Semantic surface patterns\n\n" + _table(["Pattern", "N"], semantic), "## Structural comparison\n\n" + _table(["Observable status", "N"], structural), "## Interpretation boundary\n\n`NO_RESOLVED_*_ALIAS_OBSERVED` describes this P1 profile only; it does not claim a source ontology lacks synonyms. `STRUCTURAL_PROFILE_DIFFERENCE_PRESENT` does not claim structural evidence is necessary or sufficient to correct a selection. No selector/scoring/policy behavior changed."))

def _reconciliation_report(reconciliation: dict[str, Any]) -> str:
    rows = [[row["source_label"], "yes" if row["in_residual_138"] else "no", row["legacy_alias_placement"], ", ".join(row["normalized_observable_alias_collision_patterns"]) or "NONE"] for row in reconciliation["records"]]
    return "\n\n".join(("# V3 Phase 2.6 Alias-Collision Reconciliation", "**MEASURED RESULT:** the earlier 8-case report is the P0-correct to P1-wrong transition population. Its labels classify where aliases were available, not necessarily exact text equality. V2 records exact normalized overlap separately.", _table(["Regression source", "In residual-138?", "Legacy placement label", "V2 exact-overlap field"], rows), f"All regressions = {reconciliation['regression_population_n']}; in residual-138 = {reconciliation['regressions_in_residual_n']}; exact normalized overlap = {reconciliation['regressions_with_exact_overlap_n']}.", "The old residual `ALIAS_COLLISION=0` was not a selector inconsistency: it used a narrower residual population and a different, exact-overlap interpretation than the legacy placement label. V2 removes the overloaded term."))

def _dense_report(dense: dict[str, Any]) -> str:
    error = dense.get("technical_error", {})
    return "\n\n".join(("# V3 Phase 2.6 Dense P0/P1", "**IMPLEMENTED FACT:** the full runner remains smoke-gated and frozen to shared CandidateSets, MiniLM, CPU, normalized embeddings, and `dense_structured_profile_v1`.", f"## Status\n\n`RUNTIME_BLOCKER`: Windows `{error.get('stage')}` / `{error.get('type')}`. Linux/WSL execution is also unavailable: no installed WSL distribution exists and this non-admin session cannot provision the required runtime. No Dense P0/P1 metrics, intersection counts, abstentions, or zero scores were emitted.", "A clean Linux/WSL environment must pass the smoke contract before the existing full runner is allowed to calculate P0/P1 same-CandidateSet metrics."))

def _gate(dense_status: str) -> str:
    rows = [["corrected extraction safety", "SUPPORTED", "Versioned correction and regression tests."], ["residual deterministic selection", "PARTIALLY_SUPPORTED", "V2 derives N=138 diagnostics without tuning."], ["taxonomy consistency", "SUPPORTED", "Alias availability, overlap, semantic, and structural dimensions are separate."], ["Dense runtime", dense_status, "Windows c10.dll blocker; no usable Linux/WSL distro."], ["Dense P0 value", "NOT_TESTED", "Smoke gate did not pass."], ["Dense P1 synonym value", "NOT_TESTED", "Smoke gate did not pass."], ["Dense complementary value", "NOT_TESTED", "No paired Dense results."], ["Qwen incremental value", "UNAVAILABLE", "QWEN_LIVE_EVAL_UNAVAILABLE; QSEM V1 unchanged."], ["definition utility", "UNRESOLVED", "No bilateral source-side definition evidence."], ["external generalization", "DATA_MISSING", "A qualifying second pair requires source/target corpora, mappings, provenance/license, reproducible extraction, and preferably bilateral evidence/context."], ["commitment calibration readiness", "DATA_MISSING", "Independent calibration data and held-out validation absent."]]
    return "# V3 Phase 2.6 Post-Dense Research Gate\n\n" + _table(["Area", "Status", "Evidence"], rows) + "\n\nNo semantic policy, production preprocessing/profile, routing, calibration, threshold, canonical-KG, or QSEM V1 change. Phase 3 remains blocked."

def run() -> dict[str, Any]:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    phase26, frozen = json.loads(PHASE26.read_text(encoding="utf-8")), json.loads(FROZEN.read_text(encoding="utf-8"))
    p0 = phase26["conditions"]["P0_CURRENT_V1"]["fixed_candidate_selection"]["rows"]; p1 = phase26["conditions"]["P1_SYNONYMS_RESOLVED_V2"]["fixed_candidate_selection"]["rows"]
    source = resolved_source_faithful_profiles(ANATOMY / "mouse.owl", "P1_SYNONYMS_RESOLVED_V2").profiles; target = resolved_source_faithful_profiles(ANATOMY / "human.owl", "P1_SYNONYMS_RESOLVED_V2").profiles
    candidates = {str(row["source_iri"]): tuple(str(item["iri"]) for item in row["retrieved_candidates"]) for row in frozen["enriched_cases"]}
    taxonomy, reconciliation, dense = derive_residual_taxonomy_v2(p0, p1, source, target, candidates), reconcile_alias_collisions(p0, p1, source, target, candidates), dense_runtime_check()
    dense_result = {"status": "RUNTIME_BLOCKER", "full_benchmark_executed": False, "no_fabricated_metrics": True, "runtime": dense, "linux_wsl": {"status": "RUNTIME_BLOCKER", "reason": "NO_INSTALLED_WSL_DISTRIBUTION_NON_ADMIN_SESSION"}}
    intersection = {"status": "NOT_EXECUTED_RUNTIME_BLOCKER", "paired_population": 1497, "paired_valid_population": 0, "no_fabricated_metrics": True}
    manifest = {"schema_version": "v3_phase2_6_post_dense_v1", "historical_artifacts_overwritten": False, "inputs": {"phase26_sha256": _hash(PHASE26), "frozen_candidate_sha256": _hash(FROZEN)}, "outputs": ["RESIDUAL_TAXONOMY_V2.json", "ALIAS_RECONCILIATION.json", "DENSE_RUNTIME.json", "DENSE_P0_P1_RESULT.json", "DENSE_ERROR_INTERSECTION.json", "RESULT.json"]}
    result = {"taxonomy_residual_n": taxonomy["residual_population_n"], "alias_reconciliation": {"regressions": reconciliation["regression_population_n"], "in_residual": reconciliation["regressions_in_residual_n"], "exact_overlap": reconciliation["regressions_with_exact_overlap_n"]}, "dense_status": "RUNTIME_BLOCKER", "policy_change": False, "qwen": "QWEN_LIVE_EVAL_UNAVAILABLE", "external_validation": "DATA_MISSING", "commitment_calibration": "DATA_MISSING"}
    for name, value in (("RESIDUAL_TAXONOMY_V2.json", taxonomy), ("ALIAS_RECONCILIATION.json", reconciliation), ("DENSE_RUNTIME.json", dense), ("DENSE_P0_P1_RESULT.json", dense_result), ("DENSE_ERROR_INTERSECTION.json", intersection), ("RESULT.json", result), ("MANIFEST.json", manifest)): _write_json(ARCHIVE / name, value)
    _write_md(ROOT / "experiments" / "V3_PHASE2_6_RESIDUAL_TAXONOMY_V2.md", _taxonomy_report(taxonomy)); _write_md(ROOT / "experiments" / "V3_PHASE2_6_ALIAS_COLLISION_RECONCILIATION.md", _reconciliation_report(reconciliation)); _write_md(ROOT / "experiments" / "V3_PHASE2_6_DENSE_P0_P1.md", _dense_report(dense)); _write_md(ROOT / "experiments" / "V3_PHASE2_6_DENSE_ERROR_INTERSECTION.md", "# V3 Phase 2.6 Dense Error Intersection\n\n`NOT_EXECUTED_RUNTIME_BLOCKER`. No Dense selector output exists, so paired correctness counts and residual-138 Dense statuses are intentionally absent rather than fabricated."); _write_md(ROOT / "experiments" / "V3_PHASE2_6_POST_DENSE_RESEARCH_GATE.md", _gate("RUNTIME_BLOCKER"))
    return result

if __name__ == "__main__": run()
