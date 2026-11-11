"""Post-freeze V2 stability measurement; never alters primary results."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_phase2_16_agent_v2_development_20260924"

from run_v3_phase2_16_v2_development import prepared_for

import sys
sys.path.insert(0, str(ROOT / "src"))
from cdoi.model_config import load_dotenv_file
from cdoi.qwen_rca import QwenRCAConfig
from cdoi.qwen_rca_v2 import QwenRCAAgentV2Model
from cdoi.rca_agent_v2 import RCAAgentV2, V2AgentBudget
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, RCAOrchestrator
from cdoi.rcaeval_evaluation import RCAEvalCase


SELECTED = ("re2ob_checkoutservice_cpu_1", "re2ob_currencyservice_loss_1", "re2ob_productcatalogservice_loss_1", "re2ob_emailservice_socket_1")


def main() -> None:
    output = OUT / "STABILITY_RUNS"
    if output.exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_PHASE216_STABILITY")
    load_dotenv_file(ROOT / ".env", override=False); config = QwenRCAConfig.from_internal_gateway_environment()
    if config.status() != "QWEN_LIVE_READY": raise RuntimeError("QWEN_LIVE_RUNTIME_NOT_READY")
    import pyarrow.parquet as pq
    rows = {str(row["case"]): row for row in pq.read_table(ROOT / "data/benchmarks/external/rcaeval/cases.parquet", columns=["case", "dataset", "system", "inject_time", "time_start", "time_end", "has_logs", "has_traces"]).to_pylist()}
    output.mkdir(parents=True)
    (output / "PREREGISTRATION.json").write_text(json.dumps({"schema_version": "v3_phase2_16_v2_stability_preregistration_v1", "selection": list(SELECTED), "repetitions": 3, "selection_basis": "post-freeze representative technical failures: H1 sizes 1, 9, 10, and H5-expanded topology case", "configuration_freeze": "../V2_CONFIG_FREEZE.json", "no_tuning": True}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    budget = V2AgentBudget(max_tool_calls=8, max_h1_profiles=20, max_evidence_per_tool_call=20, max_output_repairs=1); records=[]
    for case_id in SELECTED:
        row = rows[case_id]; case = RCAEvalCase(case_id, str(row["dataset"]), str(row["system"]), int(row["inject_time"]), int(row["time_start"]) if row["time_start"] is not None else None, int(row["time_end"]) if row["time_end"] is not None else None, bool(row["has_logs"]), bool(row["has_traces"]))
        for repeat in range(1, 4):
            prepared = prepared_for(case, output / "STORES" / f"{case_id}_{repeat}.sqlite")
            try:
                model = QwenRCAAgentV2Model(config, max_output_tokens=512); agent = RCAAgentV2(model, budget=budget)
                report = RCAOrchestrator().run(prepared, output / case_id / f"repeat_{repeat}", InvestigationMode.AGENT, CandidateSourceMode.H1_THEN_H5_FALLBACK, agent, model.public_metadata())
                trace = json.loads((output / case_id / f"repeat_{repeat}" / "AGENT_TRACE.json").read_text(encoding="utf-8"))
                records.append({"case_id": case_id, "repeat": repeat, "status": report.status, "states": trace.get("states"), "tool_calls": report.tool_calls, "transport": model.last_transport_diagnostic, "records": model.records})
            finally: prepared.store.close()
    (output / "RESULTS.json").write_text(json.dumps({"schema_version": "v3_phase2_16_v2_stability_results_v1", "records": records, "summary": {"total_runs": len(records), "technical_failures": sum(row["status"] == "TECHNICAL_FAILURE" for row in records), "zero_tool_calls": sum(row["tool_calls"] == 0 for row in records), "status_agreement": all(row["status"] == "TECHNICAL_FAILURE" for row in records), "interpretation": "Measures reproducibility of the frozen primary output-contract failure; not a quality or tuning run."}}, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__": main()
