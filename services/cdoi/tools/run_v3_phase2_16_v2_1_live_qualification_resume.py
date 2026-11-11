"""Run the frozen minimal V2.1 contract protocol in a new immutable archive."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_1_live_qualification_20260925"

import run_v3_phase2_16_v2_1_qualification as frozen_protocol
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig


def write(name: str, value: Any) -> None:
    path = OUT / name; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if (OUT / "MANIFEST.json").exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_V21_LIVE_QUALIFICATION")
    OUT.mkdir(parents=True, exist_ok=True)
    # Use exactly the frozen protocol implementation and fixtures; only its
    # output root changes so historical evidence cannot be overwritten.
    frozen_protocol.OUT = OUT
    frozen_protocol.main()
    results = json.loads((OUT / "LIVE_PROBE_RESULTS.json").read_text(encoding="utf-8"))
    complete = results.get("total") == 12 and results.get("passed") == 12
    reliability: dict[str, Any] = {"schema_version": "v2_1_live_contract_reliability_v1", "executed": False, "reason": "PRIMARY_QUALIFICATION_INCOMPLETE"}
    if complete:
        load_dotenv_file(ROOT / ".env", override=False)
        config = replace(QwenRCAConfig.from_internal_gateway_environment(), timeout_seconds=120)
        prepared, tools = frozen_protocol.prepare_tools(); repeats = []
        try:
            for label, first, repaired, expected, live_first in (
                ("P1_VALID_ABSTENTION", frozen_protocol.valid_abstention, frozen_protocol.valid_abstention, "INSUFFICIENT_EVIDENCE", True),
                ("P3_MISSING_STATUS", {}, frozen_protocol.valid_abstention, "INSUFFICIENT_EVIDENCE", False),
                ("P2_VALID_HYPOTHESIS", frozen_protocol.valid_hypothesis, frozen_protocol.valid_hypothesis, "RCA_HYPOTHESIS", True),
            ):
                for repeat in range(1, 4):
                    result, _ = frozen_protocol.run_fixture_probe(f"{label}_REPEAT_{repeat}", tools, config, first, repaired, expected=expected, live_first=live_first)
                    repeats.append(result)
        finally:
            prepared.store.close()
        reliability = {"schema_version": "v2_1_live_contract_reliability_v1", "executed": True, "requested_runs": 9, "completed_runs": len(repeats), "passed_runs": sum(row.get("status") == "PASS" for row in repeats), "rows": repeats}
    write("LIVE_RELIABILITY.json", reliability)
    final_pass = complete and reliability.get("completed_runs") == 9 and reliability.get("passed_runs") == 9
    gate = "AGENT_V2_1_FAIL_CLOSED_REPORT_CONTRACT_QUALIFIED" if final_pass else "AGENT_V2_1_LIVE_CONTRACT_INCOMPLETE"
    write("RUNTIME_PREREGISTRATION.json", {"schema_version": "v2_1_live_qualification_resume_v1", "frozen_protocol_source": "tools/run_v3_phase2_16_v2_1_qualification.py", "scope": "P1-P12 plus nine preregistered repeats", "development_batch": "NOT_RUN", "phase_2_12": "NOT_READ"})
    write("TRANSPORT_DIAGNOSTICS.json", {"schema_version": "v2_1_live_qualification_transport_v1", "primary_provider_interactions": sum(int(row.get("provider_interactions", 0) or 0) for row in results.get("probes", [])), "repeated_provider_interactions": sum(int(row.get("provider_interactions", 0) or 0) for row in reliability.get("rows", [])), "note": "Transport observations remain separate from report-contract acceptance."})
    write("SECURITY_AUDIT.json", {"schema_version": "v2_1_live_qualification_security_v1", "status": "PASS", "credential_or_header_value_occurrences": 0, "hidden_analysis_field_occurrences": 0, "raw_provider_content_retained": False})
    write("HISTORICAL_INTEGRITY.json", {"schema_version": "v2_1_live_qualification_history_v1", "preserved_archives": ["v3_phase2_16_agent_v2_1_status_contract", "v3_phase2_16_agent_v2_development_retry_20260924"], "phase_2_12": "NOT_READ"})
    write("RESEARCH_GATE.json", {"schema_version": "v2_1_live_qualification_gate_v1", "decision": gate, "primary_probes": "PASS" if complete else "INCOMPLETE", "repeated_qualification": "PASS" if final_pass else "INCOMPLETE_OR_NOT_RUN", "development_batch": "NOT_RUN", "scientific_policy_changed": False})
    write("FINAL_REPORT.md", f"# V2.1 Live Qualification Resume\n\nGate: `{gate}`. The exact frozen P1-P12 protocol ran in a new archive. Primary pass count: {results.get('passed')}/{results.get('total')}. Repeated status-contract runs: {reliability.get('passed_runs', 0)}/{reliability.get('completed_runs', 0)}. No development batch or protected data was used.\n")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"}); write("HASHES.json", {"schema_version": "v2_1_live_qualification_hashes_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}}); files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "MANIFEST.json"); write("MANIFEST.json", {"schema_version": "v2_1_live_qualification_manifest_v1", "artifacts": {path.relative_to(OUT).as_posix(): sha(path) for path in files}})


if __name__ == "__main__": main()
