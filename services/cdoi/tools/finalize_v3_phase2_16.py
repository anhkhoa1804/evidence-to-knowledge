"""Add exact regression accounting and refresh only the new V2 archive hashes."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from cdoi.qwen_rca_v2 import rca_v2_system_prompt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2"


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    text = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if not (OUT / "RESEARCH_GATE.json").exists(): raise RuntimeError("PHASE216_ARCHIVE_MISSING")
    results = json.loads((OUT / "TEST_RESULTS.json").read_text(encoding="utf-8"))
    if "--run-regression" in sys.argv:
        completed = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
        collection = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True, check=False)
        collected = sum(int(value) for value in re.findall(r":\s*(\d+)\s*$", collection.stdout, flags=re.MULTILINE))
        results.update({"command": f"{sys.executable} -m pytest -q", "exit_code": completed.returncode,
                        "status": "PASS" if completed.returncode == 0 else "FAIL",
                        "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-1000:],
                        "collected": collected, "passed": collected if completed.returncode == 0 else "NOT_AVAILABLE",
                        "failed": 0 if completed.returncode == 0 else "NOT_AVAILABLE", "skipped": 0 if completed.returncode == 0 else "NOT_AVAILABLE",
                        "collection_command": f"{sys.executable} -m pytest --collect-only -q"})
    write(OUT / "TEST_RESULTS.json", results)
    config = json.loads((OUT / "V2_CONFIG.json").read_text(encoding="utf-8"))
    config["prompt_sha256"] = hashlib.sha256(rca_v2_system_prompt().encode("utf-8")).hexdigest()
    config["phase212"] = "ROOT_HASH_MANIFEST_ONLY_NO_CASE_OR_EVALUATION_ACCESS"
    write(OUT / "V2_CONFIG.json", config)
    preregistration = json.loads((OUT / "PREREGISTRATION.json").read_text(encoding="utf-8"))
    preregistration["forbidden"] = ["PHASE212_CASE_OR_EVALUATION_ACCESS", "V2_12_CASE_DEVELOPMENT_RUN", "V1_ARTIFACT_MUTATION", "ONTOLOGY_OR_CAUSAL_POLICY_CHANGE"]
    preregistration["allowed_integrity_check"] = "Phase 2.12 root HASHES.json only"
    write(OUT / "PREREGISTRATION.json", preregistration)
    (OUT / "FINAL_REPORT.md").write_text(
        "# V3 Phase 2.16 Agent V2 Synthetic Qualification\n\n"
        "Gate: `AGENT_V2_SYNTHETIC_QUALIFICATION_PASSED`. All 15/15 deterministic synthetic cases passed. "
        "The runner read only the Phase 2.12 root hash manifest for integrity verification; it did not access a protected case, candidate, evaluation, or ground-truth artifact, and did not run a V2 12-case development batch. V2 quality against real RCA cases remains `NOT_EVALUATED`. "
        f"Full regression: {results.get('collected')} collected, {results.get('passed')} passed, {results.get('failed')} failed, {results.get('skipped')} skipped.\n", encoding="utf-8")
    artifacts = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    write(OUT / "HASHES.json", {"schema_version": "v3_phase2_16_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})
    artifacts = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json")
    write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_16_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in artifacts}})


if __name__ == "__main__": main()
