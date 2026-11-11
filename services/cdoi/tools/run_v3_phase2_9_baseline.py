"""Freeze a deterministic, non-Git pre-change baseline for V3 Phase 2.9."""
from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "experiments" / "archive" / "v3_phase2_9_baseline"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(path: Path) -> str:
    rows = [f"{item.relative_to(ROOT).as_posix()}\x1f{digest(item)}" for item in sorted(path.rglob("*")) if item.is_file() and "__pycache__" not in item.parts]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def test_count() -> int:
    completed = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
    total = re.search(r"(\d+) tests collected", completed.stdout)
    rows = re.findall(r"tests/[^\r\n]+: (\d+)", completed.stdout)
    if not total and not rows:
        raise RuntimeError(completed.stdout + completed.stderr)
    return int(total.group(1)) if total else sum(int(value) for value in rows)


def main() -> None:
    protected = [
        "experiments/archive/v3_phase2_7/MANIFEST.json",
        "experiments/archive/v3_phase2_8/MANIFEST.json",
        "experiments/archive/v3_phase2_8/DEMO_RESULT.json",
        "experiments/archive/v3_phase2_8/RESEARCH_GATE.json",
        "experiments/V3_PHASE2_7_RESEARCH_GATE.md",
        "experiments/V3_PHASE2_8_RESEARCH_GATE.md",
        "experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md",
        "experiments/archive/v3_external_dh/MANIFEST.json",
    ]
    baseline = {
        "baseline_version": "v3_phase2_9_pre_traces_v1",
        "phase": "V3 Phase 2.9 — Distributed Trace Evidence Integration",
        "source_tree_sha256": tree_digest(ROOT / "src" / "cdoi"),
        "test_tree_sha256": tree_digest(ROOT / "tests"),
        "preprocessing_contract": "cdoi_preprocessing_v1",
        "operational_context_contract": "operational_evidence_context_v1",
        "runtime": {"python": sys.version, "implementation": platform.python_implementation(), "platform": platform.platform(), "machine": platform.machine()},
        "test_count": test_count(),
        "evidence_modalities": ["entity", "relation", "event", "change_event", "metric", "semantic_term"],
        "policy_invariants": ["execution path is not causal path", "no anomaly detection", "no RCA or causal scoring", "exact-ID entity correlation only", "no schema expansion from traces", "no automatic commitment", "canonical-KG safety gate unchanged", "semantic decision policy unchanged"],
        "protected_artifacts": {item: digest(ROOT / item) for item in protected if (ROOT / item).is_file()},
    }
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    text = json.dumps(baseline, indent=2, sort_keys=True) + "\n"
    (ARCHIVE / "BASELINE.json").write_text(text, encoding="utf-8")
    (ARCHIVE / "MANIFEST.json").write_text(json.dumps({"schema_version": "v3_phase2_9_baseline_manifest_v1", "artifacts": {"BASELINE.json": digest(ARCHIVE / "BASELINE.json")}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "experiments" / "V3_PHASE2_9_BASELINE.md").write_text("# V3 Phase 2.9 Baseline\n\nFrozen before distributed trace evidence was introduced. This workspace has no Git provenance; deterministic content hashes are the baseline anchor.\n\n" + text, encoding="utf-8")


if __name__ == "__main__":
    main()
