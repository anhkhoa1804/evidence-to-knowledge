"""Freeze the Phase 2.14 Qwen-RCA runtime status without touching prior phases."""
from __future__ import annotations

import hashlib, json, platform, sys
from datetime import datetime, timezone
from pathlib import Path

from cdoi.qwen_rca import QWEN_RCA_PROMPT_VERSION, QwenRCAConfig

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_14_rca_qwen"
PHASE13 = ROOT / "experiments/archive/v3_phase2_13"

def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def verify(archive: Path) -> bool:
    entries = json.loads((archive / "HASHES.json").read_text(encoding="utf-8"))["artifacts"]
    return all((archive / relative).is_file() and sha(archive / relative) == digest for relative, digest in entries.items())

def main() -> None:
    if OUT.exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_PHASE214_RCA_ARCHIVE")
    phase13_ok = verify(PHASE13)
    config = QwenRCAConfig.from_environment(); status = config.status()
    write(OUT / "CONFIG.json", {"schema_version": "v3_phase2_14_qwen_rca_config_v1", "configuration": config.public_metadata(), "prompt_version": QWEN_RCA_PROMPT_VERSION, "candidate_source": "H1_THEN_H5_FALLBACK", "budget": {"max_reasoning_rounds": 8, "max_tool_calls": 12, "max_candidate_profiles": 6}, "development_only": True})
    write(OUT / "MODEL_RUNTIME.json", {"schema_version": "v3_phase2_14_qwen_runtime_v1", "status": status, "provider_smoke": "NOT_ATTEMPTED_PROVIDER_UNCONFIGURED" if status != "QWEN_LIVE_READY" else "PENDING_SEPARATE_LIVE_RUN", "function_call_smoke": "NOT_ATTEMPTED_PROVIDER_UNCONFIGURED" if status != "QWEN_LIVE_READY" else "PENDING_SEPARATE_LIVE_RUN", "tool_continuation_smoke": "NOT_ATTEMPTED_PROVIDER_UNCONFIGURED" if status != "QWEN_LIVE_READY" else "PENDING_SEPARATE_LIVE_RUN"})
    write(OUT / "QWEN_RUNTIME_RELIABILITY.json", {"schema_version": "v3_phase2_14_qwen_reliability_v1", "status": status, "model": config.model, "provider": config.provider, "region": config.region, "attempt_count": 0, "successful_completions": 0, "transport_failures": 0, "tool_failures": 0, "schema_failures": 0, "timeouts": 0, "retry_count": 0, "reason": "CREDENTIAL_OR_ENDPOINT_NOT_CONFIGURED; no network request was made."})
    write(OUT / "DEVELOPMENT_DATA_MANIFEST.json", {"schema_version": "v3_phase2_14_rca_development_data_v1", "synthetic_scenarios": ["METRIC_ORIGIN", "DOWNSTREAM_ERROR_SYMPTOM", "UNRELATED_DEPLOYMENT", "TWO_PLAUSIBLE_CANDIDATES", "MISSING_TRACES", "MISSING_CHANGE", "INSUFFICIENT_EVIDENCE", "TOOL_FAILURE"], "pilot_cases": "CONSUMED_DEVELOPMENT_DATA_NOT_RUN_BEFORE_LIVE_SMOKE", "phase212_holdout": "PROHIBITED_CONSUMED_HOLDOUT_NOT_READ"})
    unavailable = {"schema_version": "v3_phase2_14_qwen_development_results_v1", "status": "UNAVAILABLE_QWEN_PROVIDER_UNCONFIGURED", "top1": "NOT_EVALUATED", "top_k": "NOT_EVALUATED", "abstention": "NOT_EVALUATED", "unsupported_claims": "NOT_EVALUATED", "hallucinated_evidence": "NOT_EVALUATED", "tool_calls": 0, "fallback_usage": "NOT_EVALUATED", "latency": "NOT_EVALUATED", "tokens": "NOT_EVALUATED"}
    write(OUT / "TELEMETRY_ONLY_RESULTS.json", unavailable); write(OUT / "CDOI_ASSISTED_RESULTS.json", unavailable)
    write(OUT / "AGENT_FAILURES.json", {"schema_version": "v3_phase2_14_agent_failures_v1", "failures": [{"classification": "QWEN_PROVIDER_UNCONFIGURED", "stage": "PRE_SMOKE", "semantic_result": "NOT_APPLICABLE"}]})
    write(OUT / "STABILITY_RESULTS.json", {"schema_version": "v3_phase2_14_stability_v1", "planned_repeats": 3, "completed_repeats": 0, "status": "NOT_ATTEMPTED_PROVIDER_UNCONFIGURED"})
    write(OUT / "PERFORMANCE.json", {"schema_version": "v3_phase2_14_qwen_performance_v1", "live_model_calls": 0, "cost": "COST_NOT_MEASURED"})
    write(OUT / "RESEARCH_GATE.json", {"schema_version": "v3_phase2_14_qwen_rca_gate_v1", "decision": "QWEN_AUTH_OR_PROVIDER_BLOCKED", "phase13_hashes_verified_before_run": phase13_ok, "runtime_status": status, "agent_adapter": "IMPLEMENTED_TESTED_WITH_MOCK_TRANSPORT", "live_development_evidence": "NOT_AVAILABLE", "independent_rca_validation": "DATA_MISSING", "next_step": "Configure a governed Qwen/DashScope key and endpoint, pass the three smoke stages, then execute the fixed development protocol without holdout use."})
    write(OUT / "EXPERIMENT_MANIFEST.json", {"schema_version": "v3_phase2_14_qwen_manifest_v1", "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "runtime": {"python": sys.version, "platform": platform.platform()}, "phase13_hashes_verified": phase13_ok, "purpose": "DEVELOPMENT_ONLY Qwen RCA bring-up"})
    entries = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob("*.json")) if path.name not in {"HASHES.json", "MANIFEST.json"}}
    write(OUT / "HASHES.json", {"schema_version": "v3_phase2_14_hashes_v1", "artifacts": entries})
    entries = {path.relative_to(OUT).as_posix(): sha(path) for path in sorted(OUT.rglob("*.json")) if path.name != "MANIFEST.json"}
    write(OUT / "MANIFEST.json", {"schema_version": "v3_phase2_14_manifest_v1", "artifacts": entries})

if __name__ == "__main__": main()
