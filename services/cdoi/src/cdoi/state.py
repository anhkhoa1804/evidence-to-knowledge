from __future__ import annotations

import json
from pathlib import Path

from .models import BridgeProposal, IntegrationRun, ProposalState


class RunStateStore:
    """Filesystem-backed run/proposal journal that survives process restart."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_run(self, run: IntegrationRun) -> None:
        path = self.root / run.run_id
        path.mkdir(parents=True, exist_ok=True)
        (path / "run.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")

    def save_proposal(self, run_id: str, state: ProposalState) -> None:
        path = self.root / run_id / "proposals"
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{state.proposal.proposal_id}.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def load_proposal(self, run_id: str, proposal_id: str) -> ProposalState:
        return ProposalState.model_validate_json((self.root / run_id / "proposals" / f"{proposal_id}.json").read_text(encoding="utf-8"))

    def pending(self) -> list[ProposalState]:
        return [ProposalState.model_validate_json(path.read_text(encoding="utf-8")) for path in self.root.glob("run-*/proposals/*.json") if ProposalState.model_validate_json(path.read_text(encoding="utf-8")).final_mapping_status in {"staged", "review_pending"}]

    def save_bridge(self, proposal: BridgeProposal) -> None:
        path = self.root / "bridge_proposals"
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{proposal.proposal_id}.json").write_text(proposal.model_dump_json(indent=2), encoding="utf-8")
