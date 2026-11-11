from __future__ import annotations

import json
from pathlib import Path

from .models import OntologyChangeProposal, ValidationReport, VersionRecord
from .ontology import OntologyStore


class VersionStore:
    def __init__(self, root: Path, ontology_store: OntologyStore):
        self.root = root
        self.ontology_store = ontology_store
        self.root.mkdir(parents=True, exist_ok=True)

    def initialise(self) -> VersionRecord:
        path = self.root / "v000"
        path.mkdir(parents=True, exist_ok=True)
        for name in self.ontology_store.modules:
            self.ontology_store.serialise_module(name, path / "ontologies" / f"{name}.ttl")
        report = ValidationReport(valid=True, risk_level="LOW")
        record = VersionRecord(version="v000", parent_version=None, proposal_ids=[], added_axioms=[], source_domains=[], validation=report, approval="baseline")
        (path / "manifest.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def latest(self) -> str | None:
        versions = sorted(path.name for path in self.root.glob("v[0-9][0-9][0-9]"))
        return versions[-1] if versions else None

    def commit(self, proposal: OntologyChangeProposal, report: ValidationReport, approval: str = "automatic") -> VersionRecord:
        parent = self.latest() or self.initialise().version
        version = f"v{int(parent[1:]) + 1:03d}"
        path = self.root / version
        path.mkdir(parents=True, exist_ok=False)
        for name in self.ontology_store.modules:
            self.ontology_store.serialise_module(name, path / "ontologies" / f"{name}.ttl")
        record = VersionRecord(version=version, parent_version=parent, proposal_ids=[proposal.proposal_id], added_axioms=proposal.proposed_axioms, source_domains=[proposal.source_domain], validation=report, approval=approval)
        (path / "manifest.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
        (path / "delta.json").write_text(json.dumps({"proposal": proposal.model_dump(mode="json"), "validation": report.model_dump(mode="json")}, indent=2), encoding="utf-8")
        return record

    def commit_batch(self, proposals: list[OntologyChangeProposal], reports: list[ValidationReport], run_id: str) -> VersionRecord:
        parent = self.latest() or self.initialise().version
        version = f"v{int(parent[1:]) + 1:03d}"
        path = self.root / version
        path.mkdir(parents=True, exist_ok=False)
        for name in self.ontology_store.modules:
            self.ontology_store.serialise_module(name, path / "ontologies" / f"{name}.ttl")
        added = [axiom for proposal in proposals for axiom in proposal.proposed_axioms]
        record = VersionRecord(version=version, parent_version=parent, proposal_ids=[proposal.proposal_id for proposal in proposals], added_axioms=added, source_domains=sorted({proposal.source_domain for proposal in proposals}), validation=reports[0], approval="batch", run_id=run_id)
        (path / "manifest.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
        (path / "delta.json").write_text(json.dumps({"run_id": run_id, "proposals": [proposal.model_dump(mode="json") for proposal in proposals], "validations": [report.model_dump(mode="json") for report in reports]}, indent=2), encoding="utf-8")
        return record
