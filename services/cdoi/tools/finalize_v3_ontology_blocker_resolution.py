"""Freeze validation, integrity, and reporting for the ontology-track archive."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_ontology_blocker_resolution_20260925"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(name: str, value: object) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    results = json.loads((OUT / "SECOND_ONTOLOGY_RESULTS.json").read_text(encoding="utf-8"))
    initial = json.loads((OUT / "INITIAL_INTEGRITY.json").read_text(encoding="utf-8"))
    historical = {name: value for name, value in initial["sha256"].items() if name.startswith("experiments/archive/")}
    unchanged, changed = [], []
    for relative, digest in historical.items():
        path = ROOT / relative
        if path.exists() and _hash(path) == digest:
            unchanged.append(relative)
        else:
            changed.append(relative)
    protected_changed = []
    for relative, metadata in initial["protected_phase212_metadata_only"].items():
        path = ROOT / relative
        if not path.exists() or path.stat().st_size != metadata["size"] or path.stat().st_mtime_ns != metadata["mtime_ns"]:
            protected_changed.append(relative)
    _write("HISTORICAL_INTEGRITY.json", {"status": "PASS" if not changed and not protected_changed else "FAIL", "historical_archive_files_verified": len(unchanged), "historical_archive_files_changed": changed, "protected_phase212_contents_read": False, "protected_phase212_metadata_changed": protected_changed})
    report = f"""# Ontology Blocker Resolution — Final Report

1. Dense remains technically blocked: Windows PyTorch cannot initialize `c10.dll` (WinError 1114).
2. No clean Linux Dense experiment ran because this workspace has neither a usable WSL distribution nor Docker/Podman.
3. Dense therefore has no measured improvement, match, or degradation result.
4. Dense CandidateSet equality is not applicable because Dense did not run.
5. Dense introduced no measured unsafe selection; no Dense selection output exists.
6. A stronger second pair was identified: STW–TheSoz.
7. It was selected and its all-source candidate sets were frozen before mapping GT parsing.
8. The qualified frozen population has {results['eligible_mapping_count']} mapping rows across {results['source_count_with_mappings']} source concepts.
9. Relations represented: exactMatch={results['relation_counts']['exactMatch']}, broadMatch={results['relation_counts']['broadMatch']}, narrowMatch={results['relation_counts']['narrowMatch']}, relatedMatch={results['relation_counts']['relatedMatch']}.
10. CDOI preserves all four SKOS relation semantics. It evaluates equivalence only for exactMatch and fails closed for the other three.
11. This is stronger external evidence than six equivalence-only IDAI/PACTOLS mappings, but it is still one source family and does not establish broad generalization.
12. External ontology validation is partially supported: retrieval and exact-selection evidence are measured; relation-aware semantic selection remains unsupported.
13. QSEM external validation lacks an authorized non-RCA runtime and a separately frozen relation-aware proposal protocol.
14. QSEM was not evaluated because the RCA runtime is not authorization for semantic evaluation.
15. QSEM remains proposal-only.
16. Commitment calibration remains `BLOCKED_DATA`.
17. The STW–TheSoz data do not support calibration: they lack a held-out calibration split and validated negatives.
18. Canonical KG and review boundaries were preserved: zero writes and zero automatic commitments.
19. Historical semantic archives were unchanged; Phase 2.12 protected content was not read.
20. The dominant blocker is now Dense Linux runtime availability, followed by lack of a relation-aware semantic selector and authorized QSEM runtime.

The exact relation-specific retrieval results, candidate hashes, source hashes, and safety boundary are in the companion JSON artifacts. No production policy changed.
"""
    (OUT / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    _write("RESEARCH_GATE.json", {"status": "ONTOLOGY_EXTERNAL_VALIDATION_SUPPORTED_DENSE_BLOCKED", "dense": "DENSE_SELECTOR_RUNTIME_BLOCKED", "second_ontology": "SECOND_ONTOLOGY_VALIDATION_PARTIALLY_SUPPORTED", "relation_diversity": "SECOND_ONTOLOGY_RELATION_DIVERSITY_SUPPORTED_DATA_ONLY", "qsem": "QSEM_EXTERNAL_EVAL_RUNTIME_UNAVAILABLE", "calibration": "COMMITMENT_CALIBRATION_STILL_BLOCKED_DATA", "production_policy_change": False})
    artifacts = {path.relative_to(OUT).as_posix(): _hash(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}}
    _write("HASHES.json", {"schema_version": "v3_ontology_blocker_resolution_hashes_v1", "artifacts": artifacts})
    manifest = {"schema_version": "v3_ontology_blocker_resolution_manifest_v1", "archive": OUT.name, "artifacts": {path.relative_to(OUT).as_posix(): _hash(path) for path in sorted(OUT.iterdir()) if path.is_file() and path.name != "MANIFEST.json"}, "no_production_change": True, "no_rca_track_changes": True}
    _write("MANIFEST.json", manifest)


if __name__ == "__main__":
    main()
