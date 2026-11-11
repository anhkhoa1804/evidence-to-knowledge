"""Freeze a deterministic, non-Git baseline for V3 Phase 2.7."""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_7_baseline"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(path: Path) -> str:
    rows = []
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file() and "__pycache__" not in candidate.parts):
        rows.append(f"{item.relative_to(ROOT).as_posix()}\x1f{digest(item)}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def test_count() -> int:
    completed = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    match = re.search(r"(\d+) tests collected", completed.stdout)
    per_file = re.findall(r"tests/[^\r\n]+: (\d+)", completed.stdout)
    if not match and not per_file:
        raise RuntimeError(completed.stdout + completed.stderr)
    return int(match.group(1)) if match else sum(int(value) for value in per_file)


def main() -> None:
    fixture = ROOT / "tests" / "fixtures" / "preprocessing_demo"
    protected = [
        "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md",
        "experiments/V3_PHASE2_6_DENSE_REPRESENTATION.md",
        "experiments/archive/v3_external_dh/MANIFEST.json",
        "experiments/archive/preprocessing_mvp_demo/manifest.json",
    ]
    payload = {
        "baseline_version": "v3_phase2_7_pre_context_v1",
        "phase": "V3 Phase 2.7 — Operational Evidence Context & Pre-RCA Validation",
        "source_tree_sha256": tree_digest(ROOT / "src" / "cdoi"),
        "test_tree_sha256": tree_digest(ROOT / "tests"),
        "preprocessing_contract": "cdoi_preprocessing_v1",
        "evidence_schema_sha256": digest(ROOT / "src" / "cdoi" / "evidence_schema.py"),
        "raw_preprocessing_sha256": digest(ROOT / "src" / "cdoi" / "raw_preprocessing.py"),
        "fixture_tree_sha256": tree_digest(fixture),
        "demo_artifact_tree_sha256": tree_digest(ROOT / "experiments" / "archive" / "preprocessing_mvp_demo"),
        "runtime": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform(), "machine": platform.machine()},
        "test_count": test_count(),
        "supported_source_types": ["service_inventory_csv", "dependency_jsonl", "log_jsonl", "glossary_yaml", "deployment_change_csv"],
        "policy_invariants": ["semantic decision policy unchanged", "no selector/routing/threshold/calibration change", "no automatic commitment", "canonical-KG safety gate unchanged", "exact-ID entity resolution only", "no causal inference or RCA"],
        "protected_artifacts": {item: digest(ROOT / item) for item in protected if (ROOT / item).is_file()},
    }
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    baseline = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (ARCHIVE / "BASELINE.json").write_text(baseline, encoding="utf-8")
    manifest = {"schema_version": "v3_phase2_7_baseline_manifest_v1", "artifacts": {"BASELINE.json": digest(ARCHIVE / "BASELINE.json")}}
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = "# V3 Phase 2.7 Baseline\n\nThis immutable baseline was captured before the operational-context contract was introduced. The workspace is not a Git repository; deterministic content hashes are therefore the provenance anchor.\n\n" + baseline
    (ROOT / "experiments" / "V3_PHASE2_7_BASELINE.md").write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
