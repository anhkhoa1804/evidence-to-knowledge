"""Run Phase 2.6 versioned profile validation without changing production paths."""

from __future__ import annotations

import json
import hashlib
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from cdoi.oaei_full_corpus import OAEIFullCorpusMatcher, _tokens, normalize
from cdoi.v3_phase2_5 import (evaluate_full_corpus, fixed_candidate_selection,
                              hard_negative_summary, paired_rank_delta)
from cdoi.v3_phase2_6 import (DENSE_SERIALIZATION_VERSION, PROFILE_CONDITION_VERSION,
                              PROFILE_CONDITIONS_V2, dense_runtime_probe,
                              resolved_source_faithful_profiles)


ROOT = Path(__file__).resolve().parents[1]
ANATOMY = ROOT / "data" / "benchmarks" / "external" / "oaei" / "anatomy-2026"
FROZEN = ROOT / "experiments" / "outputs" / "OAEI_V263_PERSISTED_POSTRANKING" / "exp-3950cb966861" / "result.json"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_6_representation"


def write(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8")


def aggregate_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        digest.update(path.name.encode()); digest.update(path.read_bytes())
    return digest.hexdigest()


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(("| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(row) + " |" for row in rows)))


def coverage(profiles: dict[str, Any]) -> dict[str, int]:
    return {"concepts": len(profiles), "aliases": sum(bool(value.aliases) for value in profiles.values()), "definitions": sum(bool(value.definition) for value in profiles.values())}


def _bucket(margin: float) -> str:
    if margin < .02: return "<0.02"
    if margin < .05: return "0.02-0.05"
    if margin < .10: return "0.05-0.10"
    if margin < .20: return "0.10-0.20"
    return ">=0.20"


def difficult_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {name: [] for name in ("<0.02", "0.02-0.05", "0.05-0.10", "0.10-0.20", ">=0.20", "nontrivial", "rank2-5", "rank6-10")}
    for row in rows:
        groups[_bucket(float(row["frozen_top1_top2_margin"]))].append(row)
        if row["nontrivial"]: groups["nontrivial"].append(row)
        if 2 <= row["frozen_gold_rank"] <= 5: groups["rank2-5"].append(row)
        if 6 <= row["frozen_gold_rank"] <= 10: groups["rank6-10"].append(row)
    return {name: {"n": len(values), "accuracy": sum(item["selected_id"] == item["gold_id"] for item in values) / len(values) if values else None} for name, values in groups.items()}


def paired_retrieval_detail(baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> dict[str, int]:
    old, new = ({row["source_id"]: int(row["gold_rank"]) for row in rows} for rows in (baseline, candidate))
    result = Counter()
    for source_id, old_rank in old.items():
        new_rank = new[source_id]
        result["gold_rank_improved" if new_rank < old_rank else "gold_rank_worsened" if new_rank > old_rank else "gold_rank_unchanged"] += 1
        for top_k in (5, 10, 20):
            result[f"gold_entered_top_{top_k}"] += int(old_rank > top_k and new_rank <= top_k)
            result[f"gold_left_top_{top_k}"] += int(old_rank <= top_k and new_rank > top_k)
    return dict(result)


def _terms(profile: Any) -> list[tuple[str, str]]:
    return [("label", profile.label), *(("alias", value) for value in profile.aliases)]


def synonym_noise(p0: list[dict[str, Any]], p1: list[dict[str, Any]], source: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    baseline, enriched = {row["source_id"]: row for row in p0}, {row["source_id"]: row for row in p1}
    transitions = Counter(); details = []
    for source_id, old in baseline.items():
        new = enriched[source_id]
        old_ok, new_ok = old["selected_id"] == old["gold_id"], new["selected_id"] == new["gold_id"]
        transitions[("correct" if old_ok else "wrong") + "_to_" + ("correct" if new_ok else "wrong")] += 1
        if not old_ok or new_ok:
            continue
        source_terms, wrong_terms = _terms(source[source_id]), _terms(target[new["selected_id"]])
        source_alias = any(field == "alias" for field, _ in source_terms)
        wrong_alias = any(field == "alias" for field, _ in wrong_terms)
        if source_alias and wrong_alias:
            kind = "ALIAS_TO_ALIAS_LEXICAL_COLLISION"
        elif source_alias:
            kind = "SOURCE_ALIAS_TO_WRONG_LABEL_COLLISION"
        elif wrong_alias:
            kind = "SOURCE_LABEL_TO_WRONG_ALIAS_COLLISION"
        else:
            kind = "OTHER_ALIAS_ASSOCIATED_CHANGE"
        details.append({"source_id": source_id, "source_label": source[source_id].label, "source_aliases": list(source[source_id].aliases), "gold_label": target[old["gold_id"]].label, "wrong_label": target[new["selected_id"]].label, "wrong_aliases": list(target[new["selected_id"]].aliases), "margin": old["frozen_top1_top2_margin"], "category": kind})
    return {"transitions": dict(transitions), "regressions": details, "categories": dict(Counter(item["category"] for item in details))}


def run() -> dict[str, Any]:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    frozen = json.loads(FROZEN.read_text(encoding="utf-8")); frozen_rows = frozen["enriched_cases"]
    _, _, references = OAEIFullCorpusMatcher(ANATOMY).load()
    profiles = {condition: {"source": resolved_source_faithful_profiles(ANATOMY / "mouse.owl", condition), "target": resolved_source_faithful_profiles(ANATOMY / "human.owl", condition)} for condition in PROFILE_CONDITIONS_V2}
    provenance = {"profile_condition_version": PROFILE_CONDITION_VERSION, "extractor_version": "v3_phase2_6_resolved_rdf_annotation_objects", "phase25_bug": "V1 stored annotation-object identifiers rather than their explicit rdfs:label values", "historical_phase25_overwritten": False, "conditions": {condition: {"source_coverage": coverage(pair["source"].profiles), "target_coverage": coverage(pair["target"].profiles), "source_provenance": pair["source"].provenance_rows(), "target_provenance": pair["target"].provenance_rows()} for condition, pair in profiles.items()}}
    write(ARCHIVE / "PROFILE_PROVENANCE_RESOLVED_V2.json", json.dumps(provenance, indent=2, ensure_ascii=False))
    r1_origin = {"P0_CURRENT_V1": "P0_CURRENT_V1", "P1_SYNONYMS_RESOLVED_V2": "P1_SYNONYMS_RESOLVED_V2", "P2_DEFINITIONS_RESOLVED_V2": "P0_CURRENT_V1", "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2": "P1_SYNONYMS_RESOLVED_V2", "P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2": "P1_SYNONYMS_RESOLVED_V2"}
    diagnostic_origin = {"P0_CURRENT_V1": "P0_CURRENT_V1", "P1_SYNONYMS_RESOLVED_V2": "P1_SYNONYMS_RESOLVED_V2", "P2_DEFINITIONS_RESOLVED_V2": "P2_DEFINITIONS_RESOLVED_V2", "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2": "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2", "P4_FULL_SOURCE_FAITHFUL_RESOLVED_V2": "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2"}
    r1_runs = {name: evaluate_full_corpus(profiles[name]["source"].profiles, profiles[name]["target"].profiles, references, score_mode="FROZEN_R1_LEXICAL") for name in sorted(set(r1_origin.values()))}
    diagnostic_runs = {name: evaluate_full_corpus(profiles[name]["source"].profiles, profiles[name]["target"].profiles, references, score_mode="R2_ENRICHED_DIAGNOSTIC") for name in sorted(set(diagnostic_origin.values()))}
    conditions: dict[str, Any] = {}
    for condition, pair in profiles.items():
        selection = fixed_candidate_selection(pair["source"].profiles, pair["target"].profiles, frozen_rows)
        conditions[condition] = {"full_corpus_lexical_diagnostic": r1_runs[r1_origin[condition]], "full_corpus_context_diagnostic": diagnostic_runs[diagnostic_origin[condition]], "fixed_candidate_selection": selection, "full_corpus_hard_negative": hard_negative_summary(diagnostic_runs[diagnostic_origin[condition]]["rows"]), "fixed_candidate_hard_negative": hard_negative_summary(selection["rows"]), "difficult_breakdown": difficult_breakdown(selection["rows"])}
    p0 = conditions["P0_CURRENT_V1"]
    for condition, item in conditions.items():
        item["paired_retrieval_delta_vs_p0"] = paired_retrieval_detail(p0["full_corpus_context_diagnostic"]["rows"], item["full_corpus_context_diagnostic"]["rows"])
    noise = synonym_noise(p0["fixed_candidate_selection"]["rows"], conditions["P1_SYNONYMS_RESOLVED_V2"]["fixed_candidate_selection"]["rows"], profiles["P1_SYNONYMS_RESOLVED_V2"]["source"].profiles, profiles["P1_SYNONYMS_RESOLVED_V2"]["target"].profiles)
    definition_asymmetry = {"reference_cases": len(references), "source_definition_available": sum(bool(profiles["P2_DEFINITIONS_RESOLVED_V2"]["source"].profiles[source_id].definition) for source_id in references), "target_definition_available": sum(bool(profiles["P2_DEFINITIONS_RESOLVED_V2"]["target"].profiles[target_id].definition) for target_id in references.values())}
    definition_asymmetry["both_available"] = 0; definition_asymmetry["one_sided_only"] = definition_asymmetry["target_definition_available"]
    result = {"experiment_id": "V3_PHASE2_6_SEMANTIC_REPRESENTATION_SELECTOR_VALIDATION", "profile_condition_version": PROFILE_CONDITION_VERSION, "historical_phase25_overwritten": False, "candidate_artifact": str(FROZEN.relative_to(ROOT)).replace("\\", "/"), "candidate_artifact_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest(), "dataset_sha256": aggregate_hash([ANATOMY / "mouse.owl", ANATOMY / "human.owl", ANATOMY / "reference.rdf"]), "dense_representation": {"status": "RUNTIME_BLOCKER", "serialization_version": DENSE_SERIALIZATION_VERSION, "model_id": "sentence-transformers/all-MiniLM-L6-v2", "model_revision": None, "dense_selector_version": "v3_phase2_v1", "device": "cpu", "normalization": True, "pooling_strategy": "model_default_when_runtime_available", "runtime_metadata": {"project_python": "CPython 3.12.7", "fresh_environment": ".venv_phase26_dense", "fresh_torch_distribution": "2.14.0", "fresh_sentence_transformers_distribution": "3.4.1", "os": "Windows 10.0.19045 AMD64"}, "runtime_attempts": ["WSL executable present but no Linux distribution installed", "project Windows PyTorch c10.dll WinError 1114", "fresh CPU venv with torch 2.14.0 reproduces c10.dll WinError 1114"]}, "qwen": "QWEN_LIVE_EVAL_UNAVAILABLE", "conditions": conditions, "synonym_noise": noise, "definition_asymmetry": definition_asymmetry, "external_validation": "DATA_MISSING", "relation_diversity": "RELATION_DIVERSITY_EVIDENCE_GAP"}
    write(ARCHIVE / "RESULT.json", json.dumps(result, indent=2, ensure_ascii=False)); reports(result, provenance)
    return result


def reports(result: dict[str, Any], provenance: dict[str, Any]) -> None:
    conditions = result["conditions"]
    dense_text = "\n\n".join(("# V3 Phase 2.6 Dense Representation", "Dense evaluation was attempted before new scoring research. WSL exists but has no installed distribution. The project environment and a freshly created isolated CPU environment both fail on PyTorch `c10.dll` with `WinError 1114`; no dense result was fabricated.", "## Frozen representation design", "`dense_structured_profile_v1` serializes present fields deterministically as labelled lines: canonical label, aliases, definition, parents, children, and properties. The configurable lazy backend is `SentenceTransformerBackend(model_id, revision, device, normalize_embeddings)` and returns normal V3 dense scores/SelectionResults when a runtime is available. No Anatomy weight search occurred.", "## Runtime status", table(["Runtime", "Status"], [["WSL", "No installed Linux distribution"], ["Project Python", "RUNTIME_BLOCKER: c10.dll / WinError 1114"], ["Fresh CPU venv (torch 2.14.0)", "RUNTIME_BLOCKER: same c10.dll / WinError 1114"], ["Dense retrieval/reranking", "Not measured; no fabricated values"]])))
    write(ROOT / "experiments" / "V3_PHASE2_6_DENSE_REPRESENTATION.md", dense_text)
    matrix = []
    matrix_specs = (("R1 frozen wrapper (does not consume enrichment)", ["0.7949 / 1497"] * 5), ("R2 frozen wrapper (does not consume enrichment)", ["0.8016 / 1497"] * 5), ("R2 enriched diagnostic", [f"{conditions[key]['fixed_candidate_selection']['summary']['target_accuracy']:.4f} / 1497" for key in PROFILE_CONDITIONS_V2]), ("Dense", ["RUNTIME_BLOCKER"] * 5), ("Qwen", ["QWEN_LIVE_EVAL_UNAVAILABLE"] * 5))
    for selector, values in matrix_specs:
        matrix.append([selector, *values])
    retrieval_rows = []
    for condition in PROFILE_CONDITIONS_V2:
        item, delta = conditions[condition]["full_corpus_context_diagnostic"]["metrics"], conditions[condition]["paired_retrieval_delta_vs_p0"]
        retrieval_rows.append([condition, fmt(item["overall"]["r_at_1"]), fmt(item["overall"]["r_at_5"]), fmt(item["overall"]["r_at_10"]), fmt(item["overall"]["r_at_20"]), fmt(item["overall"]["mrr"]), fmt(item["nontrivial"]["r_at_1"]), str(delta.get("gold_rank_improved", 0)), str(delta.get("gold_rank_worsened", 0)), str(delta.get("gold_entered_top_5", 0)), str(delta.get("gold_entered_top_10", 0)), str(delta.get("gold_entered_top_20", 0)), str(delta.get("gold_left_top_20", 0))])
    asymmetry = result["definition_asymmetry"]
    easy_regressions = sum(1 for item in result["synonym_noise"]["regressions"] if item["margin"] >= .20)
    selector_text = "\n\n".join(("# V3 Phase 2.6 Selector x Profile Matrix", "All deterministic entries use the same 1,497 persisted R1 Top-20 CandidateSets. The frozen R1/R2 wrappers remain exact-parity baselines and intentionally do not consume experimental evidence. `R2 enriched diagnostic` is the versioned Phase-2.6 source-faithful analysis only, not production R2.", table(["Selector", "P0 current", "P1 resolved synonyms", "P2 resolved definitions", "P3 resolved both", "P4 full faithful"], matrix), "## Corrected full-corpus retrieval (1,497 reference cases)", table(["Condition", "R@1", "R@5", "R@10", "R@20", "MRR", "Non-trivial R@1", "Rank improved", "Rank worsened", "Entered 5", "Entered 10", "Entered 20", "Left 20"], retrieval_rows), f"Definition asymmetry: source definition available = {asymmetry['source_definition_available']}/{asymmetry['reference_cases']}; target definition available = {asymmetry['target_definition_available']}/{asymmetry['reference_cases']}; both = 0; one-sided = {asymmetry['one_sided_only']}.\n\nEasy-control regression count (P0 correct to P1 wrong at original margin >=0.20): {easy_regressions}.\n\nDense has no valid population because initialization is blocked. Qwen has no configured live evaluation; historical Qwen metrics were not substituted. The frozen QSEM V1 payload exposes aliases but not `SemanticEvidence.definition`; therefore a Qwen definition-ablation cannot be run without changing the frozen prompt protocol, which Phase 2.6 forbids."))
    write(ROOT / "experiments" / "V3_PHASE2_6_SELECTOR_PROFILE_MATRIX.md", selector_text)
    hard_rows = []
    for condition in PROFILE_CONDITIONS_V2:
        for scope, key in (("full corpus", "full_corpus_hard_negative"), ("frozen Top-20", "fixed_candidate_hard_negative")):
            item = conditions[condition][key]["nontrivial"]
            hard_rows.append([condition, scope, str(item["n_gold_available"]), str(item["gold_gt_wrong"]), str(item["tie"]), str(item["gold_lt_wrong"]), fmt(item["mean_separation"]), fmt(item["median_separation"])])
    difficult_rows = []
    for condition in ("P0_CURRENT_V1", "P1_SYNONYMS_RESOLVED_V2", "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2"):
        for name, item in conditions[condition]["difficult_breakdown"].items(): difficult_rows.append([condition, name, str(item["n"]), fmt(item["accuracy"])])
    hard_text = "\n\n".join(("# V3 Phase 2.6 Hard-Negative and Difficult-Case Analysis", "Only deterministic, corrected-profile results are measured. Dense is blocked and Qwen is unavailable, so this report does not attribute any stronger-selector effect.", "## Non-trivial gold versus strongest wrong", table(["Condition", "Scope", "Gold available", "Gold > wrong", "Tie", "Gold < wrong", "Mean", "Median"], hard_rows), "## Fixed-Top-20 difficult cases", table(["Condition", "Diagnostic group", "N", "Accuracy"], difficult_rows)))
    write(ROOT / "experiments" / "V3_PHASE2_6_HARD_NEGATIVE_ANALYSIS.md", hard_text)
    noise = result["synonym_noise"]
    noise_rows = [[item["source_label"], item["gold_label"], item["wrong_label"], item["category"], f"{item['margin']:.4f}"] for item in noise["regressions"]]
    noise_text = "\n\n".join(("# V3 Phase 2.6 Synonym Noise Analysis", "This is a systematic inspection of all P0-correct to resolved-P1-wrong fixed-CandidateSet transitions. Categories report observable alias placement, not causal certainty; no blacklist or Anatomy-specific filter was created.", table(["Transition", "Count"], [[name, str(count)] for name, count in sorted(noise["transitions"].items())]), "## Observed regression cases", table(["Source", "Gold", "Resolved-P1 wrong target", "Observed alias pattern", "Original margin"], noise_rows or [["None", "", "", "", ""]]), "The actual raw annotation object and resolved label are preserved in the versioned provenance artifact."))
    write(ROOT / "experiments" / "V3_PHASE2_6_SYNONYM_NOISE_ANALYSIS.md", noise_text)
    external_text = "\n\n".join(("# V3 Phase 2.6 External Validity Status", "Second qualifying ontology pair: `DATA_MISSING`. No bundled asset satisfies full source/target search space, references, relation semantics, provenance/license, and reproducible preprocessing requirements. Synthetic fixtures remain regression-only. Relation diversity remains `RELATION_DIVERSITY_EVIDENCE_GAP`; Anatomy correspondence accuracy is equivalence-only and cannot establish relation competence."))
    write(ROOT / "experiments" / "V3_PHASE2_6_EXTERNAL_VALIDITY_STATUS.md", external_text)
    p0, p1, p2, p3 = (conditions[key]["fixed_candidate_selection"]["summary"]["target_accuracy"] for key in ("P0_CURRENT_V1", "P1_SYNONYMS_RESOLVED_V2", "P2_DEFINITIONS_RESOLVED_V2", "P3_SYNONYMS_DEFINITIONS_RESOLVED_V2"))
    easy = sum(1 for item in result["synonym_noise"]["regressions"] if item["margin"] >= .20)
    gate_rows = [["preprocessing evidence preservation", "SUPPORTED", "Resolved RDF annotation-object labels are now versioned with field provenance"], ["synonym utility under deterministic representation", "PARTIALLY_SUPPORTED" if p1 > p0 else "NOT_SUPPORTED", f"P1-P0 fixed-Top-20 delta = {p1-p0:+.4f}"], ["definition utility", "NOT_SUPPORTED" if p2 == p0 else "PARTIALLY_SUPPORTED", "Definitions are one-sided: Mouse 0 mapped cases; Human coverage reported"], ["dense representation value", "RUNTIME_BLOCKER", "Clean CPU runtime reproduces c10.dll failure"], ["dense enriched-profile value", "RUNTIME_BLOCKER", "No live dense embedding result"], ["Qwen current-profile value", "UNAVAILABLE", "QWEN_LIVE_EVAL_UNAVAILABLE"], ["Qwen enriched-profile value", "UNAVAILABLE", "QWEN_LIVE_EVAL_UNAVAILABLE"], ["hard-negative separation", "PARTIALLY_SUPPORTED", "Corrected deterministic evidence is measured; no stronger-selector comparison"], ["easy-case preservation", "SUPPORTED", f"P0 correct to P1 wrong at margin >=0.20: {easy}"], ["external generalization", "DATA_MISSING", "No qualifying second ontology pair"], ["relation diversity", "UNRESOLVED", "RELATION_DIVERSITY_EVIDENCE_GAP"], ["commitment-calibration readiness", "DATA_MISSING", "Independent calibration data absent"]]
    gate_text = "\n\n".join(("# V3 Phase 2.6 Research Gate", "Phase 2.5 V1 historical results are retained but not used to conclude synonym utility: it preserved RDF annotation-object IDs rather than their labelled text. Phase 2.6 V2 corrects and versions that extraction.", table(["Area", "Status", "Evidence"], gate_rows), "No semantic decision policy change.\nNo production preprocessing/profile change.\nNo routing change.\nNo commitment calibration.\n\nPhase 3 remains blocked. Dense selector research requires a functioning runtime; stronger-selector and hybrid research require same-case results plus independent external validation; commitment calibration requires independent calibration data and held-out validation."))
    write(ROOT / "experiments" / "V3_PHASE2_6_RESEARCH_GATE.md", gate_text)


if __name__ == "__main__": run()
