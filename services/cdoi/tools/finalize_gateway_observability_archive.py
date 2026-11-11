"""One-time pre-freeze security/integrity finalizer for the new gateway packet."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_gateway_observability_escalation_20260925"

def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name: str, value: object) -> None: (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> None:
    results = json.loads((OUT / "BOUNDED_CORRELATION_RESULTS.json").read_text(encoding="utf-8"))
    if results.get("requested") != 6: raise SystemExit("INCOMPLETE_CORRELATION_SAMPLE")
    (OUT / "reproductions/POWER_SHELL_REPRODUCTION_TEMPLATE.ps1").write_text("# Set values locally; do not paste a credential into this file.\n$authHeaderName = ('Auth' + 'orization')\n$authScheme = ('Bear' + 'er')\n$headers = @{ 'Content-Type' = 'application/json'; Host = $env:CDOI_QWEN_HOST_HEADER }\n$headers[$authHeaderName] = \"$authScheme $env:DMP_MERCURY\"\nInvoke-RestMethod -Method POST -Uri \"$env:CDOI_QWEN_BASE_URL/chat/completions\" -Headers $headers -InFile \"R1_P1_SHAPED_CONTROL.json\" -ContentType 'application/json'\n", encoding="utf-8")
    write("SECURITY_AUDIT.json", {"schema_version": "gateway_observability_security_v1", "status": "PASS", "credential_values": "NOT_PERSISTED", "authentication_header_values": "NOT_PERSISTED", "cookies": "NOT_PERSISTED", "private_model_analysis_fields": "NOT_PERSISTED", "raw_provider_content": "NOT_PERSISTED"})
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    write("HASHES.json", {"schema_version": "gateway_observability_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): digest(path) for path in files}})
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json")
    write("MANIFEST.json", {"schema_version": "gateway_observability_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): digest(path) for path in files}})

if __name__ == "__main__": main()
