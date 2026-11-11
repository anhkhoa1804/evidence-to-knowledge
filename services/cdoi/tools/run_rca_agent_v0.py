"""Run the Phase 2.13 read-only RCA prototype on a declared incident.

This research CLI does not create ontology/KG writes, remediation actions, or
causal conclusions.  AGENT mode needs an injected model in library use; when
no agent is configured it writes a technical-failure report rather than faking
a live-model result.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cdoi.operational_context import TopologyScope
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, RCAOrchestrator
from cdoi.qwen_rca import QwenRCAAgentModel, QwenRCAConfig
from cdoi.rca_investigation import RCAAgentV0


def main() -> int:
    parser = argparse.ArgumentParser(description="CDOI Phase 2.13 read-only RCA research prototype")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--incident-id", required=True)
    parser.add_argument("--incident-file", type=Path)
    parser.add_argument("--mode", choices=[item.value for item in InvestigationMode], default=InvestigationMode.PROFILE_ONLY.value)
    parser.add_argument("--candidate-source", choices=[item.value for item in CandidateSourceMode], default=CandidateSourceMode.H1_THEN_H5_FALLBACK.value)
    parser.add_argument("--scope", choices=[item.value for item in TopologyScope], default=TopologyScope.ONE_HOP.value)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qwen", action="store_true", help="Use the separately configured Qwen RCA adapter; credentials remain environment-only.")
    args = parser.parse_args()
    orchestrator = RCAOrchestrator()
    prepared = orchestrator.prepare(args.manifest, args.incident_id, args.output / "incident_evidence.sqlite", TopologyScope(args.scope), args.incident_file)
    agent = None; metadata = None
    if args.qwen:
        model = QwenRCAAgentModel(QwenRCAConfig.from_environment())
        agent, metadata = RCAAgentV0(model, max_tool_calls=12, max_candidate_profiles=6), model.public_metadata()
    try:
        report = orchestrator.run(prepared, args.output, InvestigationMode(args.mode), CandidateSourceMode(args.candidate_source), agent, metadata)
    finally:
        prepared.store.close()
    print(json.dumps({"status": report.status, "incident_id": report.incident_id, "output": str(args.output), "research_boundary": "READ_ONLY_NON_CAUSAL_DEVELOPMENT_PROTOTYPE"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
