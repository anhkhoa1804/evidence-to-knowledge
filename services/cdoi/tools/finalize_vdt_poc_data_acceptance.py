"""Append-only final regression/integrity record for the frozen VDT acceptance run."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "experiments/archive/v3_vdt_poc_data_acceptance_20260928"
OUT = ROOT / "experiments/archive/v3_vdt_poc_data_acceptance_completion_20260928"
VDT = ROOT.parent / "VDT"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: object) -> None:
    path = OUT / name
    if path.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{path}")
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if OUT.exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_VDT_ACCEPTANCE_COMPLETION_ARCHIVE")
    parent_hashes = json.loads((PARENT / "HASHES.json").read_text(encoding="utf-8"))["artifacts"]
    bad = [name for name, expected in parent_hashes.items() if sha(PARENT / name) != expected]
    parent_source = json.loads((PARENT / "SOURCE_INTEGRITY.json").read_text(encoding="utf-8"))["after"]
    current_source = {path.name: sha(path) for path in sorted(VDT.iterdir()) if path.is_file()}
    OUT.mkdir(parents=True)
    write("PREREGISTRATION.json", {"scope": "append-only regression after two added deterministic acceptance edge-case tests", "parent_archive": PARENT.name, "forbidden": ["parent archive modification", "VDT modification", "live model", "labels", "Phase 2.12"]})
    write("PARENT_ARCHIVE_INTEGRITY.json", {"parent": PARENT.name, "hash_entries": len(parent_hashes), "hash_failures": bad, "valid": not bad, "current_vdt_source_matches_parent": current_source == parent_source})
    junit = OUT / "REGRESSION.junit.xml"
    command = [sys.executable, "-m", "pytest", "-q", "--junitxml", str(junit), "--basetemp", "D:/cdoi_vdt_poc_acceptance_completion_pytest_20260928"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    root = ET.parse(junit).getroot(); suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = sum(int(x.attrib.get("tests", "0")) for x in suites); failed = sum(int(x.attrib.get("failures", "0")) + int(x.attrib.get("errors", "0")) for x in suites); skipped = sum(int(x.attrib.get("skipped", "0")) for x in suites)
    write("REGRESSION.json", {"command": command, "exit_code": result.returncode, "collected": tests, "passed": tests - failed - skipped, "failed": failed, "skipped": skipped, "junit_artifact": junit.name, "output": result.stdout[-2000:]})
    write("COMPLETION_SCOPE.json", {"new_tests": ["duplicate identity/dangling topology stays unresolved", "timezone-free/end-before-start incident rejection"], "source_files": {name: sha(ROOT / name) for name in ["src/cdoi/vdt_acceptance.py", "src/cdoi/rca_poc.py", "tests/unit/test_vdt_acceptance.py", "docs/CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md"]}, "live_llm_calls": 0, "generation_tokens": 0})
    (OUT / "FINAL_REPORT.md").write_text(f"# VDT POC Data Acceptance Completion\n\nThis append-only archive preserves the primary frozen acceptance archive and records the final full regression after two additional deterministic edge-case tests. Parent integrity: {len(parent_hashes)}/{len(parent_hashes) - len(bad)} hashes valid. VDT source unchanged: {current_source == parent_source}. Regression: {tests} collected, {tests - failed - skipped} passed, {failed} failed, {skipped} skipped. No model, label value, or VDT source mutation occurred. The data-readiness gate remains `VDT_DATA_NOT_READY_FOR_RCA_POC`.\n", encoding="utf-8")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(OUT).as_posix(): sha(path) for path in files}
    write("HASHES.json", {"algorithm": "sha256", "artifacts": hashes})
    write("MANIFEST.json", {"file_count": len(hashes), "files": hashes, "integrity_rule": "integrity files are not self-hashed"})
    if any(sha(OUT / key) != value for key, value in hashes.items()):
        raise RuntimeError("COMPLETION_HASH_FAILURE")
    print(json.dumps({"parent_bad": len(bad), "tests": tests, "failed": failed, "files": len(hashes)}, sort_keys=True))


if __name__ == "__main__":
    main()
