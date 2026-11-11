"""Record a separate, read-only Phase 2.14 semantic-track audit."""
from __future__ import annotations

import hashlib, json, platform, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from cdoi.qwen_rca import QwenRCAConfig

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "experiments/archive/v3_phase2_14_semantic"
def write(path: Path, value: object) -> None: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def main() -> None:
    if OUT.exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_PHASE214_SEMANTIC_ARCHIVE")
    dense = subprocess.run([str(ROOT / ".venv_phase26_dense/Scripts/python.exe"), "-c", "import torch"], capture_output=True, text=True)
    error = (dense.stderr or dense.stdout).replace(str(ROOT), "<REPOSITORY>")[:500]
    selected = json.loads((ROOT / "experiments/archive/v3_external_dh/SELECTED_PAIR_MANIFEST.json").read_text(encoding="utf-8"))
    result = json.loads((ROOT / "experiments/archive/v3_external_dh/RESULT.json").read_text(encoding="utf-8"))
    qwen = QwenRCAConfig.from_environment()
    write(OUT / "ENVIRONMENT.json", {"schema_version": "v3_phase2_14_semantic_environment_v1", "python": sys.version, "platform": platform.platform(), "wsl_linux_runtime": "UNAVAILABLE_NO_INSTALLED_DISTRIBUTION"})
    write(OUT / "DATASET_MANIFEST.json", {"schema_version": "v3_phase2_14_semantic_dataset_v1", "second_pair": selected, "prior_external_result_status": result["status"], "boundary": "Existing independent DH evidence is descriptive, small (n=6), and equivalence-only."})
    write(OUT / "DENSE_RUNTIME_RESULTS.json", {"schema_version": "v3_phase2_14_dense_runtime_v1", "status": "DENSE_RUNTIME_STILL_BLOCKED", "environment": "Windows isolated dense venv; clean Linux unavailable", "return_code": dense.returncode, "error": error, "semantic_result": "NOT_MEASURED"})
    write(OUT / "QWEN_SEMANTIC_RESULTS.json", {"schema_version": "v3_phase2_14_qwen_semantic_status_v1", "status": "QWEN_SEMANTIC_EVAL_UNAVAILABLE", "runtime_status": qwen.status(), "boundary": "RCA Qwen configuration and semantic QSEM evaluation remain separate."})
    write(OUT / "SECOND_PAIR_RESULTS.json", {"schema_version": "v3_phase2_14_second_pair_status_v1", "status": "SECOND_ONTOLOGY_PAIR_VALIDATION_SUPPORTED", "selected_pair": selected["candidate_id"], "population": result["population"], "relation_limit": "EQUIVALENCE_ONLY", "definition_utility": "DEFINITION_UTILITY_UNRESOLVED"})
    write(OUT / "RESEARCH_GATE.json", {"schema_version": "v3_phase2_14_semantic_gate_v1", "dense": "DENSE_RUNTIME_STILL_BLOCKED", "qwen_semantic": "QWEN_SEMANTIC_EVAL_UNAVAILABLE", "second_pair": "SECOND_ONTOLOGY_PAIR_VALIDATION_SUPPORTED", "definition_utility": "DEFINITION_UTILITY_UNRESOLVED", "commitment_calibration": "COMMITMENT_CALIBRATION_BLOCKED_DATA", "policy_change": "NONE"})
    write(OUT / "EXPERIMENT_MANIFEST.json", {"schema_version": "v3_phase2_14_semantic_manifest_v1", "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "purpose": "Read-only semantic-track audit; no Anatomy tuning or policy change."})
    entries={path.relative_to(OUT).as_posix():sha(path) for path in sorted(OUT.rglob("*.json")) if path.name not in {"HASHES.json","MANIFEST.json"}}; write(OUT / "HASHES.json", {"schema_version":"v3_phase2_14_semantic_hashes_v1","artifacts":entries})
    entries={path.relative_to(OUT).as_posix():sha(path) for path in sorted(OUT.rglob("*.json")) if path.name!="MANIFEST.json"}; write(OUT / "MANIFEST.json", {"schema_version":"v3_phase2_14_semantic_manifest_v1","artifacts":entries})
if __name__ == "__main__": main()
