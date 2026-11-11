"""Freeze a deterministic, non-Git pre-change baseline for V3 Phase 2.8."""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_8_baseline"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(path: Path) -> str:
    rows = [
        f"{item.relative_to(ROOT).as_posix()}\x1f{digest(item)}"
        for item in sorted(path.rglob("*"))
        if item.is_file() and "__pycache__" not in item.parts
    ]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def test_count() -> int:
    completed = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    total = re.search(r"(\d+) tests collected", completed.stdout)
    per_file = re.findall(r"tests/[^\r\n]+: (\d+)", completed.stdout)
    if not total and not per_file:
        raise RuntimeError(completed.stdout + completed.stderr)
    return int(total.group(1)) if total else sum(int(value) for value in per_file)


def main() -> None:
    protected = [
        "experiments/archive/v3_phase2_7/MANIFEST.json",
        "experiments/archive/v3_phase2_7/DEMO_RESULT.json",
        "experiments/archive/v3_phase2_7/RESEARCH_GATE.json",
        "experiments/V3_PHASE2_7_RESEARCH_GATE.md",
        "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md",
        "experiments/archive/v3_external_dh/MANIFEST.json",
    ]
    baseline = {
        "baseline_version": "v3_phase2_8_pre_metrics_v1",
        "phase": "V3 Phase 2.8 — Metrics Evidence Integration",
        "source_tree_sha256": tree_digest(ROOT / "src" / "cdoi"),
        "test_tree_sha256": tree_digest(ROOT / "tests"),
        "preprocessing_contract": "cdoi_preprocessing_v1",
        "operational_context_contract": "operational_evidence_context_v1",
        "raw_preprocessing_sha256": digest(ROOT / "src" / "cdoi" / "raw_preprocessing.py"),
        "operational_context_sha256": digest(ROOT / "src" / "cdoi" / "operational_context.py"),
        "runtime": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform(), "machine": platform.machine()},
        "test_count": test_count(),
        "supported_evidence_types": ["entity", "relation", "event", "change_event", "semantic_term"],
        "policy_invariants": ["no anomaly detection", "no causal inference or RCA", "exact-ID entity correlation only", "no schema expansion from changes", "no automatic commitment", "canonical-KG safety gate unchanged", "semantic decision policy unchanged"],
        "protected_artifacts": {item: digest(ROOT / item) for item in protected if (ROOT / item).is_file()},
    }
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    text = json.dumps(baseline, indent=2, sort_keys=True) + "\n"
    (ARCHIVE / "BASELINE.json").write_text(text, encoding="utf-8")
    manifest = {"schema_version": "v3_phase2_8_baseline_manifest_v1", "artifacts": {"BASELINE.json": digest(ARCHIVE / "BASELINE.json")}}
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "experiments" / "V3_PHASE2_8_BASELINE.md").write_text("# V3 Phase 2.8 Baseline\n\nFrozen before metric evidence was introduced. This workspace has no Git provenance; deterministic content hashes are the baseline anchor.\n\n" + text, encoding="utf-8")


if __name__ == "__main__":
    main()
