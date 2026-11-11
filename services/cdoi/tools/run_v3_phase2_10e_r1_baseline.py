"""Freeze the pre-R1 external-evaluation state."""
from __future__ import annotations
import hashlib, json, platform, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_10e_r1"
EVAL = ROOT / "experiments/archive/v3_phase2_10e_rcaeval"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree(path: Path) -> str:
    rows = [f"{item.relative_to(ROOT).as_posix()}\x1f{sha(item)}" for item in sorted(path.rglob("*")) if item.is_file() and "__pycache__" not in item.parts]
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()

def test_count() -> int:
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=True)
    return sum(int(value) for value in re.findall(r"tests/[^\r\n]+: (\d+)", result.stdout))

def main() -> None:
    phase210 = ROOT / "experiments/archive/v3_phase2_10"
    values = {
        "schema_version": "v3_phase2_10e_r1_baseline_v1",
        "source_tree_sha256": tree(ROOT / "src/cdoi"),
        "test_tree_sha256": tree(ROOT / "tests"),
        "test_count": test_count(),
        "phase210": {
            "incident_evidence_graph_sha256": sha(ROOT / "src/cdoi/incident_evidence_graph.py"),
            "cause_candidates_sha256": sha(phase210 / "CAUSE_CANDIDATES.json"),
            "demo_sha256": sha(phase210 / "DEMO_RESULT.json"),
        },
        "phase210e": {
            "baseline_results_sha256": sha(EVAL / "BASELINE_RESULTS.json"),
            "case_split_sha256": sha(EVAL / "CASE_SPLIT.json"),
            "ground_truth_contract_sha256": sha(EVAL / "GROUND_TRUTH_CONTRACT.json"),
            "evaluation_protocol_sha256": sha(EVAL / "EVALUATION_PROTOCOL.json"),
        },
        "rcaeval": {
            "dataset_revision": "afeacb11bcc94dadfd1c8f483ee4377b2b8b614e",
            "index_sha256": sha(ROOT / "data/benchmarks/external/rcaeval/cases.parquet"),
            "first_case": "re2ob_checkoutservice_cpu_1",
            "first_case_window_spans": 246079,
            "resource_ceiling": 100000,
        },
        "runtime": {"python": sys.version, "platform": platform.platform(), "machine": platform.machine()},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "BASELINE.json").write_text(json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "MANIFEST.json").write_text(json.dumps({"schema_version": "v3_phase2_10e_r1_manifest_v1", "artifacts": {"BASELINE.json": sha(OUT / "BASELINE.json")}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "experiments/V3_PHASE2_10E_R1_BASELINE.md").write_text("# V3 Phase 2.10E-R1 Baseline\n\nFrozen before scalable evidence-store implementation.\n\n" + json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
