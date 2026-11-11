"""Capture an exact, reproducible regression result for the 2026-09-25 diagnostics.

This is deliberately an evidence runner: it neither changes agent behavior nor
reads protected evaluation material.  It owns only its new immutable archive.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "experiments" / "archive" / "v3_payload_diagnostics_regression_20260925"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summary(text: str) -> dict[str, int | None]:
    match = re.search(r"(\d+) passed", text)
    passed = int(match.group(1)) if match else None
    match = re.search(r"(\d+) failed", text)
    failed = int(match.group(1)) if match else 0
    match = re.search(r"(\d+) skipped", text)
    skipped = int(match.group(1)) if match else 0
    return {"passed": passed, "failed": failed, "skipped": skipped}


def main() -> int:
    if ARCHIVE.exists():
        raise SystemExit(f"Refusing to overwrite immutable archive: {ARCHIVE}")
    ARCHIVE.mkdir(parents=True)
    base_temp = Path(os.environ.get("CDOI_TEST_TMP_ROOT", r"D:\cdoi_payload_diag_regression_pytest_20260925"))
    environment = dict(os.environ)
    environment["TEMP"] = str(base_temp.parent)
    environment["TMP"] = str(base_temp.parent)
    command = [sys.executable, "-m", "pytest", "-q", "--basetemp", str(base_temp)]
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
    output = completed.stdout + completed.stderr
    counts = _summary(output)
    _write_json(
        ARCHIVE / "REGRESSION.json",
        {
            "schema_version": "payload_diagnostics_regression_v1",
            "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "command": command,
            "exit_code": completed.returncode,
            "collected": counts["passed"] + counts["failed"] + counts["skipped"] if counts["passed"] is not None else None,
            **counts,
            "output": output,
            "scope": "post-payload-isolation-and-vdt-temporal-label-diagnosis regression only",
        },
    )
    files = [path for path in sorted(ARCHIVE.iterdir()) if path.is_file()]
    hashes = {path.name: _sha256(path) for path in files}
    _write_json(ARCHIVE / "HASHES.json", {"schema_version": "hashes_v1", "files": hashes})
    manifest_files = [path for path in sorted(ARCHIVE.iterdir()) if path.is_file()]
    _write_json(
        ARCHIVE / "MANIFEST.json",
        {
            "schema_version": "manifest_v1",
            "files": [{"path": path.name, "sha256": _sha256(path)} for path in manifest_files],
        },
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
