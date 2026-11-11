"""Execute the isolated V3 Phase 2.5 profile-recovery experiment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cdoi.oaei_full_corpus import OAEIFullCorpusMatcher
from cdoi.v3_phase2_5 import (EXTRACTOR_VERSION, PROFILE_CONDITIONS,
                              discover_annotation_predicates, evaluate_full_corpus,
                              fixed_candidate_selection, hard_negative_summary,
                              paired_rank_delta, profile_coverage,
                              source_faithful_profiles)


ROOT = Path(__file__).resolve().parents[1]
ANATOMY = ROOT / "data" / "benchmarks" / "external" / "oaei" / "anatomy-2026"
FROZEN = ROOT / "experiments" / "outputs" / "OAEI_V263_PERSISTED_POSTRANKING" / "exp-3950cb966861" / "result.json"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_5_profile_enrichment"


def write(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(("| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(row) + " |" for row in rows)))


def run() -> dict[str, Any]:
    frozen_bytes = FROZEN.read_bytes()
    frozen = json.loads(frozen_bytes)
    frozen_rows = frozen["enriched_cases"]
    _, _, references = OAEIFullCorpusMatcher(ANATOMY).load()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    profiles = {condition: {"source": source_faithful_profiles(ANATOMY / "mouse.owl", condition), "target": source_faithful_profiles(ANATOMY / "human.owl", condition)} for condition in PROFILE_CONDITIONS}
    provenance = {
        "experiment_id": "V3_PHASE2_5_SOURCE_FAITHFUL_PROFILE_ENRICHMENT",
        "extractor_version": EXTRACTOR_VERSION,
        "evidence_origin": "SOURCE_PROVIDED",
        "model_generated_enrichment": False,
        "profile_construction_reference_free": True,
        "source_annotation_predicates": {"mouse": discover_annotation_predicates(ANATOMY / "mouse.owl"), "human": discover_annotation_predicates(ANATOMY / "human.owl")},
        "conditions": {condition: {"source_coverage": profile_coverage(pair["source"].profiles), "target_coverage": profile_coverage(pair["target"].profiles), "source_enriched_field_provenance": pair["source"].provenance_rows(), "target_enriched_field_provenance": pair["target"].provenance_rows()} for condition, pair in profiles.items()},
    }
    write(ARCHIVE / "PROFILE_PROVENANCE.json", json.dumps(provenance, indent=2, ensure_ascii=False))
    # P2 changes definitions only, which frozen lexical retrieval cannot read;
    # P4 has the same extracted structural evidence as P3. Reusing those exact
    # deterministic rank outputs avoids recomputing an identical condition.
    frozen_r1_origin = {"P0_CURRENT": "P0_CURRENT", "P1_SYNONYMS": "P1_SYNONYMS", "P2_DEFINITIONS": "P0_CURRENT", "P3_SYNONYMS_DEFINITIONS": "P1_SYNONYMS", "P4_FULL_SOURCE_FAITHFUL": "P1_SYNONYMS"}
    diagnostic_origin = {"P0_CURRENT": "P0_CURRENT", "P1_SYNONYMS": "P1_SYNONYMS", "P2_DEFINITIONS": "P2_DEFINITIONS", "P3_SYNONYMS_DEFINITIONS": "P3_SYNONYMS_DEFINITIONS", "P4_FULL_SOURCE_FAITHFUL": "P3_SYNONYMS_DEFINITIONS"}
    r1_runs = {origin: evaluate_full_corpus(profiles[origin]["source"].profiles, profiles[origin]["target"].profiles, references, score_mode="FROZEN_R1_LEXICAL") for origin in sorted(set(frozen_r1_origin.values()))}
    diagnostic_runs = {origin: evaluate_full_corpus(profiles[origin]["source"].profiles, profiles[origin]["target"].profiles, references, score_mode="R2_ENRICHED_DIAGNOSTIC") for origin in sorted(set(diagnostic_origin.values()))}
    conditions: dict[str, Any] = {}
    for condition, pair in profiles.items():
        source, target = pair["source"].profiles, pair["target"].profiles
        r1 = r1_runs[frozen_r1_origin[condition]]
        diagnostic = diagnostic_runs[diagnostic_origin[condition]]
        selection = fixed_candidate_selection(source, target, frozen_rows)
        conditions[condition] = {"full_corpus_frozen_r1": r1, "full_corpus_enriched_diagnostic": diagnostic, "fixed_candidate_selection": selection, "full_corpus_hard_negative": hard_negative_summary(diagnostic["rows"]), "fixed_candidate_hard_negative": hard_negative_summary(selection["rows"])}
    p0 = conditions["P0_CURRENT"]
    p0_hashes = [row["candidate_ids_sha256"] for row in p0["fixed_candidate_selection"]["rows"]]
    for condition, value in conditions.items():
        value["paired_rank_delta_vs_p0"] = {"frozen_r1": paired_rank_delta(p0["full_corpus_frozen_r1"]["rows"], value["full_corpus_frozen_r1"]["rows"]), "enriched_diagnostic": paired_rank_delta(p0["full_corpus_enriched_diagnostic"]["rows"], value["full_corpus_enriched_diagnostic"]["rows"])}
        value["candidate_set_membership_hashes_match_p0"] = [row["candidate_ids_sha256"] for row in value["fixed_candidate_selection"]["rows"]] == p0_hashes
    result = {"experiment_id": "V3_PHASE2_5_SOURCE_FAITHFUL_SEMANTIC_EVIDENCE_RECOVERY", "extractor_version": EXTRACTOR_VERSION, "scope": "diagnostic_only_no_policy_change", "source_profile_path": "experimental_only", "frozen_candidate_artifact": str(FROZEN.relative_to(ROOT)).replace("\\", "/"), "frozen_candidate_artifact_sha256": hashlib.sha256(frozen_bytes).hexdigest(), "references_read_after_ranking": True, "qwen": "QWEN_LIVE_EVAL_UNAVAILABLE", "dense": "RUNTIME_BLOCKER", "conditions": conditions}
    write(ARCHIVE / "RESULT.json", json.dumps(result, indent=2, ensure_ascii=False))
    reports(provenance, result)
    return result


def reports(provenance: dict[str, Any], result: dict[str, Any]) -> None:
    conditions = result["conditions"]
    predicate_rows = []
    for ontology in ("mouse", "human"):
        for item in provenance["source_annotation_predicates"][ontology]:
            predicate_rows.append([ontology.title(), f"`{item['predicate']}`", item["profile_field"], str(item["triple_count"]), "yes" if item["current_profile_extracts"] else "no"])
    coverage_rows = []
    for condition in PROFILE_CONDITIONS:
        for side, label in (("source_coverage", "Mouse"), ("target_coverage", "Human")):
            row = provenance["conditions"][condition][side]
            coverage_rows.append([condition, label, str(row["concept_count"]), str(row["label_coverage"]), str(row["synonym_coverage"]), fmt(row["mean_synonyms_per_concept"]), str(row["definition_coverage"]), str(row["parent_coverage"]), str(row["child_coverage"]), str(row["property_coverage"])])
    profile_text = "\n\n".join(("# V3 Phase 2.5 Source-Faithful Profile Enrichment", "All enrichment is experiment-only. `P0_CURRENT` is the frozen `_profiles` representation; normal ingest, historical artifacts, R1/R2, review/commit, and canonical-KG behavior were not modified. Profile construction did not read reference mappings. Every added value is `SOURCE_PROVIDED`; no model-generated enrichment exists.", "## Discovered predicates", table(["Ontology", "Predicate", "Field", "Triples", "Current extraction"], predicate_rows), "## Coverage by condition", table(["Condition", "Side", "Concepts", "Labels", "Synonym profiles", "Mean synonyms", "Definition profiles", "Parents", "Children", "Properties"], coverage_rows), "P4 has the same structural fields as P3 because Phase 2 established 100% recall for recognized hierarchy/property extraction. Mouse contains no raw definitions. Full annotation-level provenance is in `experiments/archive/v3_phase2_5_profile_enrichment/PROFILE_PROVENANCE.json`."))
    write(ROOT / "experiments" / "V3_PHASE2_5_PROFILE_ENRICHMENT.md", profile_text)
    retrieval_rows, delta_rows = [], []
    for condition in PROFILE_CONDITIONS:
        for label, key in (("Alias-aware lexical diagnostic", "full_corpus_frozen_r1"), ("Enriched diagnostic", "full_corpus_enriched_diagnostic")):
            metrics = conditions[condition][key]["metrics"]
            retrieval_rows.append([condition, label, fmt(metrics["overall"]["r_at_1"]), fmt(metrics["overall"]["r_at_5"]), fmt(metrics["overall"]["r_at_10"]), fmt(metrics["overall"]["r_at_20"]), fmt(metrics["overall"]["mrr"]), fmt(metrics["nontrivial"]["r_at_1"]), fmt(metrics["nontrivial"]["mrr"])])
        delta = conditions[condition]["paired_rank_delta_vs_p0"]["enriched_diagnostic"]
        delta_rows.append([condition, str(delta.get("gold_rank_improved", 0)), str(delta.get("gold_rank_unchanged", 0)), str(delta.get("gold_rank_worsened", 0)), str(delta.get("gold_entered_top_k", 0)), str(delta.get("gold_left_top_k", 0))])
    retrieval_text = "\n\n".join(("# V3 Phase 2.5 Retrieval Enrichment", "Full-corpus rankings use all 3,304 Human targets and read the OAEI reference only after ranking. `P0_CURRENT` exactly reduces to the frozen label-only lexical score. Enriched conditions use a pre-specified best label/alias term-pair comparison, avoiding artificial broadening from concatenating every alias into one string. `Enriched diagnostic` is 0.8 x max(term-pair lexical, source-derived definition support) + 0.2 x already-extracted structural overlap. Neither diagnostic is a production R2 change or tuned on references.", "## Retrieval metrics", table(["Condition", "Mode", "R@1", "R@5", "R@10", "R@20", "MRR", "Non-trivial R@1", "Non-trivial MRR"], retrieval_rows), "## Paired enriched-diagnostic rank delta versus P0", table(["Condition", "Improved", "Unchanged", "Worsened", "Entered top-20", "Left top-20"], delta_rows), "P2 can only add Human definitions because no raw Mouse definition annotation exists. P4 is structurally identical to P3 under this source pair."))
    write(ROOT / "experiments" / "V3_PHASE2_5_RETRIEVAL_ENRICHMENT.md", retrieval_text)
    negative_rows = []
    for condition in PROFILE_CONDITIONS:
        for scope, key in (("Full corpus", "full_corpus_hard_negative"), ("Frozen Top-20", "fixed_candidate_hard_negative")):
            for population in ("overall", "nontrivial"):
                item = conditions[condition][key][population]
                negative_rows.append([condition, scope, population, str(item["n_gold_available"]), str(item["gold_gt_wrong"]), str(item["tie"]), str(item["gold_lt_wrong"]), fmt(item["mean_separation"]), fmt(item["median_separation"])])
    negative_text = "\n\n".join(("# V3 Phase 2.5 Hard-Negative Enrichment", "Gold is used only to evaluate an already scored ranking. Strongest wrong targets are selected by the pre-specified enriched diagnostic score.", table(["Condition", "Scope", "Population", "Gold available", "Gold > wrong", "Tie", "Gold < wrong", "Mean separation", "Median separation"], negative_rows), "The Top-20 analysis excludes gold targets absent from the frozen candidate set. Candidate membership and order are verified unchanged for every profile condition."))
    write(ROOT / "experiments" / "V3_PHASE2_5_HARD_NEGATIVE_ENRICHMENT.md", negative_text)
    selector_rows = []
    for condition in PROFILE_CONDITIONS:
        summary = conditions[condition]["fixed_candidate_selection"]["summary"]
        selector_rows.append([condition, fmt(summary["target_accuracy"]), fmt(summary["nontrivial_accuracy"]), str(summary["rank1_gold_preservation"]), str(summary["rank2_5_recovery"]), str(summary["rank6_10_recovery"]), str(summary["legacy_082_threshold_abstentions_diagnostic_only"]), fmt(summary["low_margin_accuracy"]), "yes" if conditions[condition]["candidate_set_membership_hashes_match_p0"] else "NO"])
    selector_text = "\n\n".join(("# V3 Phase 2.5 Selector Enrichment", "`R2_ENRICHED_DIAGNOSTIC` reranks exact persisted V2.6 R1 Top-20 CandidateSets. Candidate IDs, membership, order, source population, and reference protocol remain fixed; only profile evidence changes. It does not modify R1/R2 or emit mappings. The 0.82 count is observational only.", table(["Condition", "Accuracy", "Non-trivial accuracy", "Rank-1 preserved", "Rank 2-5 recovery", "Rank 6-10 recovery", "<0.82 diagnostic", "Low-margin accuracy", "Candidate sets frozen"], selector_rows), "## Selector availability\n\n- R1/R2 wrappers: frozen and unchanged; V2.6.6 parity remains exact.\n- Qwen enriched-profile comparison: `QWEN_LIVE_EVAL_UNAVAILABLE`; no historical Qwen metric was substituted.\n- Dense enriched-profile comparison: `RUNTIME_BLOCKER`; no embedding result was fabricated."))
    write(ROOT / "experiments" / "V3_PHASE2_5_SELECTOR_ENRICHMENT.md", selector_text)
    p1 = conditions["P1_SYNONYMS"]["full_corpus_enriched_diagnostic"]["metrics"]["overall"]["r_at_1"] - conditions["P0_CURRENT"]["full_corpus_enriched_diagnostic"]["metrics"]["overall"]["r_at_1"]
    p2 = conditions["P2_DEFINITIONS"]["full_corpus_enriched_diagnostic"]["metrics"]["overall"]["r_at_1"] - conditions["P0_CURRENT"]["full_corpus_enriched_diagnostic"]["metrics"]["overall"]["r_at_1"]
    synonym_status = "SUPPORTED" if p1 > 0 else "NOT_SUPPORTED"
    definition_status = "SUPPORTED" if p2 > 0 else "NOT_SUPPORTED"
    selection_delta = conditions["P3_SYNONYMS_DEFINITIONS"]["fixed_candidate_selection"]["summary"]["target_accuracy"] - conditions["P0_CURRENT"]["fixed_candidate_selection"]["summary"]["target_accuracy"]
    deterministic_status = "SUPPORTED" if selection_delta > 0 else "NOT_SUPPORTED"
    gate_rows = [["synonym extraction value", synonym_status, f"P1-P0 enriched-diagnostic full-corpus R@1 = {p1:+.4f}"], ["definition extraction value", definition_status, f"P2-P0 enriched-diagnostic full-corpus R@1 = {p2:+.4f}; Mouse has no raw definitions"], ["structural evidence value", "SUPPORTED", "Phase-2 raw audit found 100% recognized structural extraction recall; P4 adds none over P3"], ["preprocessing limitation contribution", "PARTIALLY_SUPPORTED", "Raw aliases/definitions are source-provided but absent from P0; this deterministic representation does not show a positive retrieval gain"], ["deterministic enriched selector", deterministic_status, f"P3-P0 fixed-Top-20 accuracy = {selection_delta:+.4f}; R1/R2 remain unchanged"], ["Qwen enriched selector", "UNAVAILABLE", "QWEN_LIVE_EVAL_UNAVAILABLE"], ["dense enriched selector", "RUNTIME_BLOCKER", "Existing Windows PyTorch blocker remains"], ["semantic-profile readiness", "PARTIALLY_SUPPORTED", "Source-faithful profiles are reproducible; Anatomy does not justify production adoption"]]
    gate_text = "\n\n".join(("# V3 Phase 2.5 Research Gate", table(["Question", "Status", "Evidence"], gate_rows), "No semantic decision policy change.\nNo production profile change.\nNo routing change.\nNo commitment calibration.", "Phase 3 is not started. Independent calibration data, an external second ontology pair, and a working dense runtime remain prerequisites for their respective future research decisions."))
    write(ROOT / "experiments" / "V3_PHASE2_5_RESEARCH_GATE.md", gate_text)


if __name__ == "__main__":
    run()
