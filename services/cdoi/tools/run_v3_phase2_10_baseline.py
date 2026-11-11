"""Freeze the pre-graph reproducibility baseline for V3 Phase 2.10."""
from __future__ import annotations
import hashlib, json, platform, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_10_baseline"
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def tree(path: Path) -> str:
    return hashlib.sha256("\n".join(f"{p.relative_to(ROOT).as_posix()}\x1f{sha(p)}" for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts).encode()).hexdigest()
def count() -> int:
    run = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True)
    rows = re.findall(r"tests/[^\r\n]+: (\d+)", run.stdout)
    if not rows: raise RuntimeError(run.stdout + run.stderr)
    return sum(map(int, rows))
def main() -> None:
    protected = ["experiments/archive/v3_phase2_7/MANIFEST.json","experiments/archive/v3_phase2_8/MANIFEST.json","experiments/archive/v3_phase2_9/MANIFEST.json","experiments/archive/v3_phase2_9/DEMO_RESULT.json","experiments/V3_PHASE2_9_RESEARCH_GATE.md","experiments/V3_PHASE2_8_RESEARCH_GATE.md","experiments/V3_PHASE2_6_FOLLOWUP_RESEARCH_GATE.md","experiments/archive/v3_external_dh/MANIFEST.json"]
    data = {"baseline_version":"v3_phase2_10_pre_graph_v1","phase":"V3 Phase 2.10 — Incident Evidence Graph & Candidate Cause Representation","source_tree_sha256":tree(ROOT/"src/cdoi"),"test_tree_sha256":tree(ROOT/"tests"),"preprocessing_contract":"cdoi_preprocessing_v1","context_contract":"operational_evidence_context_v1","test_count":count(),"evidence_modalities":["entity","relation","event","change_event","metric","trace_span","semantic_term"],"runtime":{"python":sys.version,"implementation":platform.python_implementation(),"platform":platform.platform(),"machine":platform.machine()},"policy_invariants":["no new adapters","no anomaly detection","no causal inference or RCA ranking","no automatic commitment","canonical KG unchanged","semantic decision policy unchanged"],"protected_artifacts":{p:sha(ROOT/p) for p in protected if (ROOT/p).is_file()}}
    OUT.mkdir(parents=True, exist_ok=True); text=json.dumps(data,indent=2,sort_keys=True)+"\n"
    (OUT/"BASELINE.json").write_text(text,encoding="utf-8")
    (OUT/"MANIFEST.json").write_text(json.dumps({"schema_version":"v3_phase2_10_baseline_manifest_v1","artifacts":{"BASELINE.json":sha(OUT/"BASELINE.json")}},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (ROOT/"experiments/V3_PHASE2_10_BASELINE.md").write_text("# V3 Phase 2.10 Baseline\n\nFrozen before incident-graph implementation.\n\n"+text,encoding="utf-8")
if __name__ == "__main__": main()
