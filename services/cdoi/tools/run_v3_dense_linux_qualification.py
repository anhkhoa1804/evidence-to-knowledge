"""Verify the frozen Dense Linux qualification preconditions without tuning.

Run from a clean Linux checkout after installing the exact packages recorded in
the ontology archive.  It performs the existing Dense smoke contract and
validates every frozen input hash before any future P0/P1 scorer is permitted.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from cdoi.v3_phase2_6_followup import dense_runtime_check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_ontology_blocker_resolution_20260925"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    config = json.loads((OUT / "DENSE_EXPERIMENT_CONFIG.json").read_text(encoding="utf-8"))
    result = {"experiment_id": config["experiment_id"], "platform": platform.platform(), "python": sys.version.split()[0],
              "environment": {name: os.environ.get(name) for name in ("PYTHONHASHSEED", "OMP_NUM_THREADS", "TOKENIZERS_PARALLELISM")}}
    if platform.system() != "Linux":
        result.update({"status": "DENSE_RUNTIME_BLOCKED", "reason": "CLEAN_LINUX_REQUIRED"})
    else:
        inputs = {relative: {"expected": digest, "actual": _hash(ROOT / relative)} for relative, digest in config["frozen_input_sha256"].items()}
        result["frozen_input_hashes"] = inputs
        if any(item["expected"] != item["actual"] for item in inputs.values()):
            result.update({"status": "DENSE_RUNTIME_BLOCKED", "reason": "FROZEN_INPUT_HASH_MISMATCH"})
        else:
            smoke = dense_runtime_check(config["model"], revision=config["model_revision"], device="cpu", normalize_embeddings=True)
            result["smoke"] = smoke
            result.update({"status": "DENSE_RUNTIME_READY_FOR_PREREGISTERED_P0_P1" if smoke["status"] == "DENSE_RUNTIME_READY" else "DENSE_RUNTIME_BLOCKED"})
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "DENSE_RUNTIME_READY_FOR_PREREGISTERED_P0_P1" else 2


if __name__ == "__main__":
    raise SystemExit(main())
