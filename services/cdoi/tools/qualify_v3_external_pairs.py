"""Persist qualification-first external-validation evidence without scoring CDOI."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from cdoi.v3_external_validation import (ExternalPairQualification, choose_qualified_pair,
                                          parse_alignment_relations, qualification_row,
                                          sha256, unavailable_result)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "research" / "upstream" / "ontoaligner" / "assets" / "cmt-conference"
ARCHIVE = ROOT / "experiments" / "archive" / "v3_external_validation"

def write_json(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def write_md(path, value): path.write_text(value.rstrip() + "\n", encoding="utf-8")
def table(headers, rows): return "\n".join(("| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |", *("| " + " | ".join(row) + " |" for row in rows)))

def run():
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    relations = parse_alignment_relations(ASSETS / "reference.xml")
    candidates = [
        ExternalPairQualification("oaei_conference_cmt_conference", "OAEI Conference / OntoFarm", "CMT", "Conference", "legacy local OAEI asset", "legacy local OAEI asset", True, True, True, True, relations["mapping_count"], tuple(relations["relation_types"]), False, False, "UNKNOWN", "UNKNOWN", "AVAILABLE", "ABSENT", True, True, "UNRESOLVED_MANUAL_LICENSE_REVIEW", "PARTIAL_OFFICIAL_PROVENANCE", True, True, "REQUIRES_MANUAL_REVIEW", ("SOURCE_AND_TARGET_RDFS_LABELS_ABSENT", "DATASET_LICENSE_NOT_ESTABLISHED_BY_LOCAL_OR_OFFICIAL_RECORD"), ("https://oaei.ontologymatching.org/2025/conference/index.html", "https://github.com/sciknoworg/OntoAligner")),
        ExternalPairQualification("ontoaligner_bioml_catalog", "OntoAligner Bio-ML catalog", "NCIT/DOID or OMIM/ORDO", "paired ontology", None, None, False, False, False, True, None, (), None, None, "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", None, None, "UNKNOWN", "UPSTREAM_ADAPTER_ONLY", False, True, "DATA_MISSING", ("NO_LOCAL_FULL_ONTOLOGY_PAIR_AND_REFERENCE_ALIGNMENT",), ("https://github.com/sciknoworg/OntoAligner",)),
        ExternalPairQualification("local_oet_rcaeval_adapters", "CDOI external adapter placeholders", "OET/RCAEval source", "target", None, None, False, False, False, False, None, (), None, None, "UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN", None, None, "UNKNOWN", "LOCAL_PATHS_EMPTY", False, True, "DATA_MISSING", ("NORMALIZED_EXTERNAL_CASE_FILES_NOT_PRESENT",), ()),
    ]
    selected = choose_qualified_pair(candidates)
    files = {name: sha256(ASSETS / name) for name in ("source.xml", "target.xml", "reference.xml")}
    candidate_data = {"schema_version": "v3_external_candidates_v1", "selection_precedes_evaluation": True, "candidates": [qualification_row(item) for item in candidates], "cmt_local_file_hashes": files, "cmt_reference_relations": relations["relation_types"]}
    qualification = {"schema_version": "v3_external_qualification_v1", "qualified_candidate_ids": [], "selected_pair": None, "status": "EXTERNAL_VALIDATION_DATA_MISSING", "selection_rule": "license/provenance, reproducible access, full source/target, trusted reference, stable IDs; never CDOI score", "reasons": [reason for candidate in candidates for reason in candidate.disqualifying_reasons]}
    manifest = {"schema_version": "v3_external_validation_manifest_v1", "selection_timestamp": "2026-09-18", "selection_precedes_evaluation": True, "selected_pair": None, "qualification_criteria": qualification["selection_rule"], "known_limitations": qualification["reasons"], "protected_anatomy_artifacts": "not read for selection or evaluation"}
    write_json(ARCHIVE / "CANDIDATES.json", candidate_data); write_json(ARCHIVE / "QUALIFICATION.json", qualification); write_json(ARCHIVE / "MANIFEST.json", manifest)
    rows = [[item.candidate_id, item.benchmark, item.qualification_status, "; ".join(item.disqualifying_reasons) or "none"] for item in candidates]
    write_md(ROOT / "experiments" / "V3_EXTERNAL_PAIR_CANDIDATES.md", "# V3 External Pair Candidates\n\n" + table(["Candidate", "Benchmark", "Status", "Blockers"], rows))
    write_md(ROOT / "experiments" / "V3_EXTERNAL_PAIR_QUALIFICATION.md", "# V3 External Pair Qualification\n\n**IMPLEMENTED FACT:** selection criteria were applied before CDOI evaluation. No candidate is qualified.\n\n" + table(["Candidate", "Full source", "Full target", "Reference", "Labels", "License", "Status"], [[item.candidate_id, str(item.full_source_available), str(item.full_target_available), str(item.reference_alignment_available), f"source={item.source_labels}; target={item.target_labels}", item.license_status, item.qualification_status] for item in candidates]) + "\n\n`EXTERNAL_VALIDATION_DATA_MISSING`: no evaluation was run.")
    write_md(ROOT / "experiments" / "V3_EXTERNAL_EVIDENCE_COVERAGE.md", "# V3 External Evidence Coverage\n\nNo pair qualified, so no selected-pair mapped-population coverage or P0/P1 result exists. CMT–Conference local inspection: source classes=32, target classes=81, `rdfs:label`=0 on both; source comments=3, target comments=0; reference mappings=15, all relation `=`. These facts do not overcome the license/provenance and label blockers.")
    write_md(ROOT / "experiments" / "V3_EXTERNAL_VALIDATION_RESULT.md", "# V3 External Validation Result\n\n`EXTERNAL_VALIDATION_DATA_MISSING`. No pair was selected or evaluated; no accuracy, retrieval, fixed-set, hard-negative, or synonym metric was emitted.")
    gate = [["external pair availability", "PARTIALLY_SUPPORTED", "CMT–Conference artifacts found locally."], ["external pair qualification", "DATA_MISSING", "No candidate meets mandatory license/provenance and usable-label criteria."], ["external provenance/license", "UNRESOLVED", "Official OAEI provenance located; reusable data license not established."], ["external reference alignment", "PARTIALLY_SUPPORTED", "CMT reference has 15 equality mappings but pair remains unqualified."], ["bilateral alias evidence", "NOT_TESTED", "No selected pair."], ["bilateral definition evidence", "UNRESOLVED", "No selected pair."], ["external P0/P1/fixed selection", "NOT_TESTED", "Qualification first; no scoring."], ["external relation diversity", "UNRESOLVED", "CMT local reference is equivalence-only."], ["Dense runtime", "RUNTIME_BLOCKER", "Unchanged."], ["Qwen current-profile value", "UNAVAILABLE", "Unchanged."], ["cross-dataset replication", "DATA_MISSING", "No qualified external evaluation."], ["commitment-calibration readiness", "DATA_MISSING", "Unchanged."], ["Phase 3 readiness", "NOT_SUPPORTED", "Independent qualified evaluation and calibration data absent."]]
    write_md(ROOT / "experiments" / "V3_EXTERNAL_VALIDATION_RESEARCH_GATE.md", "# V3 External Validation Research Gate\n\n" + table(["Area", "Status", "Evidence"], gate) + "\n\nNo semantic-policy, production-profile, routing, threshold, calibration, canonical-KG, automatic-commitment, or QSEM V1 change.")
    return qualification
if __name__ == "__main__": run()
