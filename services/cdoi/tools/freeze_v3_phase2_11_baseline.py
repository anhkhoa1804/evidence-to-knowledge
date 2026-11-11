"""Freeze the immutable R2A state before Phase 2.11 implementation."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_11"
R2A = ROOT / "experiments/archive/v3_phase2_10e_r2a"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path: Path) -> str:
    rows = [f"{item.relative_to(ROOT).as_posix()}\x1f{sha(item)}" for item in sorted(path.rglob("*")) if item.is_file() and "__pycache__" not in item.parts]
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def test_count() -> int:
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only"], cwd=ROOT, text=True, capture_output=True, check=True)
    return int(re.search(r"(\d+) tests collected", result.stdout).group(1))


def main() -> None:
    manifest = json.loads((R2A / "MANIFEST.json").read_text(encoding="utf-8"))
    mismatch = [name for name, digest in manifest["artifacts"].items() if sha(R2A / name) != digest]
    if mismatch:
        raise RuntimeError(f"FROZEN_R2A_MANIFEST_REGRESSION: {mismatch}")
    split = ROOT / "experiments/archive/v3_phase2_10e_rcaeval/CASE_SPLIT.json"
    values = {
        "schema_version": "v3_phase2_11_baseline_v1",
        "source_tree_sha256": tree(ROOT / "src/cdoi"),
        "test_tree_sha256": tree(ROOT / "tests"),
        "test_count": test_count(),
        "phase210_graph_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"),
        "phase210_candidates_sha256": sha(ROOT / "experiments/archive/v3_phase2_10/CAUSE_CANDIDATES.json"),
        "r2a_manifest_sha256": sha(R2A / "MANIFEST.json"),
        "r2a_pilot_results_sha256": sha(R2A / "PILOT_RESULTS.json"),
        "r2a_case_status_sha256": sha(R2A / "CASE_STATUS.json"),
        "pilot_split_sha256": sha(split),
        "holdout_split_sha256": hashlib.sha256(json.dumps(json.loads(split.read_text(encoding="utf-8"))["held_out_re2ob_case_ids"], separators=(",", ":")).encode()).hexdigest(),
        "dataset_revision": "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e",
        "case_index_sha256": sha(ROOT / "data/benchmarks/external/rcaeval/cases.parquet"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "BASELINE.json").write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "MANIFEST.json").write_text(json.dumps({"schema_version": "v3_phase2_11_manifest_v1", "artifacts": {"BASELINE.json": sha(OUT / "BASELINE.json")}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "experiments/V3_PHASE2_11_BASELINE.md").write_text("# V3 Phase 2.11 Baseline\n\n" + json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
