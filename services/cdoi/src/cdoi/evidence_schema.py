"""Deterministic operational-evidence adapter for existing schema candidates.

It deliberately creates reviewable candidates only.  It neither aligns,
proposes, validates, commits, nor mutates a knowledge graph.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .models import (ClassCandidate, Evidence, ObjectPropertyCandidate,
                     Provenance, SchemaCandidate, SourceReference)
from .raw_preprocessing import (ADAPTER_VERSION, NormalizedEntityEvidence,
                                NormalizedRelationEvidence,
                                NormalizedSemanticTerm, PreprocessingResult)


INDUCTION_VERSION = "cdoi_evidence_schema_v1"
RULE_ENTITY_SERVICE = "ENTITY_SERVICE_ADAPTER_TYPE_V1"
RULE_RELATION_VOCABULARY = "RELATION_BOUNDED_VOCABULARY_V1"
RULE_GLOSSARY = "GLOSSARY_DIRECT_SEMANTIC_TERM_V1"
UNREVIEWED = "CANDIDATE_UNREVIEWED"


def _candidate_id(kind: str, key: str) -> str:
    return "schema-ev-" + hashlib.sha256(f"{INDUCTION_VERSION}\x1f{kind}\x1f{key}".encode("utf-8")).hexdigest()[:24]


def _provenance(domain: str, candidate_id: str) -> Provenance:
    return Provenance(extraction_id="induction-" + candidate_id, input_domain=domain, model="deterministic-evidence-schema-inducer", model_version=INDUCTION_VERSION, timestamp=datetime(1970, 1, 1, tzinfo=timezone.utc), parameters={"adapter_version": ADAPTER_VERSION})


def _evidence(item: Any, text: str) -> Evidence:
    provenance = item.provenance
    return Evidence(reference=SourceReference(source_path=str(provenance["source_file"]), source_system=str(item.source_system), source_span=f"record {provenance['source_record_index']}: {provenance['source_record_id']}", metadata={"raw_evidence_id": str(provenance["raw_evidence_id"]), "normalization_version": str(provenance["normalization_version"])}), text=text)


@dataclass(frozen=True)
class InducedSchemaCandidate:
    """Audit wrapper for a reusable existing schema candidate model."""

    candidate: SchemaCandidate
    induction_rule: str
    supporting_evidence_ids: tuple[str, ...]
    supporting_source_types: tuple[str, ...]
    support_count: int
    partial_support_count: int = 0
    status: str = UNREVIEWED
    validation_status: str = "NOT_APPLICABLE_PRE_PROPOSAL"

    def artifact(self) -> dict[str, Any]:
        return {"schema_version": INDUCTION_VERSION, "candidate_id": self.candidate.candidate_id, "candidate_kind": self.candidate.kind.value, "label": self.candidate.canonical_label, "induction_rule": self.induction_rule, "supporting_evidence_ids": list(self.supporting_evidence_ids), "source_types": list(self.supporting_source_types), "support_count": self.support_count, "partial_support_count": self.partial_support_count, "status": self.status, "validation_status": self.validation_status, "candidate": self.candidate.model_dump(mode="json")}


class EvidenceSchemaInducer:
    """Translate explicit adapter semantics into existing candidate types."""

    def induce(self, result: PreprocessingResult, domain: str | None = None) -> tuple[InducedSchemaCandidate, ...]:
        domain = domain or result.manifest.dataset_id
        items: list[InducedSchemaCandidate] = []
        services = sorted((entity for entity in result.entities if entity.provenance.get("source_type") == "service_inventory_csv"), key=lambda item: item.evidence_id)
        if services:
            candidate_id = _candidate_id("CLASS", "software_service")
            items.append(InducedSchemaCandidate(ClassCandidate(candidate_id=candidate_id, canonical_label="SoftwareService", domain=domain, definition="Candidate generic type supported by explicit service-inventory adapter semantics.", type_hints=["service_inventory_csv"], supporting_abox_ids=[item.external_id for item in services], evidence=[_evidence(item, f"Observed service entity: {item.label}") for item in services], provenance=_provenance(domain, candidate_id)), RULE_ENTITY_SERVICE, tuple(item.evidence_id for item in services), ("service_inventory_csv",), len(services)))
        service_ids = {item.external_id for item in services}
        by_relation: dict[str, list[NormalizedRelationEvidence]] = {}
        for relation in result.relations:
            by_relation.setdefault(relation.relation, []).append(relation)
        for relation_name, rows in sorted(by_relation.items()):
            rows = sorted(rows, key=lambda item: item.evidence_id); candidate_id = _candidate_id("OBJECT_PROPERTY", relation_name)
            resolved_ranges = [item for item in rows if item.target_external_id in service_ids]
            candidate = ObjectPropertyCandidate(candidate_id=candidate_id, canonical_label=relation_name, domain=domain, definition=f"Candidate property supported by the bounded dependency adapter vocabulary: {relation_name}.", relation_signature={relation_name}, supporting_abox_ids=[item.source_external_id for item in rows], evidence=[_evidence(item, f"Observed relation: {item.source_external_id} {relation_name} {item.target_external_id}") for item in rows], provenance=_provenance(domain, candidate_id), domain_hints=["SoftwareService"] if any(item.source_external_id in service_ids for item in rows) else [], range_hints=["SoftwareService"] if resolved_ranges else [])
            items.append(InducedSchemaCandidate(candidate, RULE_RELATION_VOCABULARY, tuple(item.evidence_id for item in rows), tuple(sorted({str(item.provenance["source_type"]) for item in rows})), len(rows), len(rows) - len(resolved_ranges)))
        for term in sorted(result.semantic_terms, key=lambda item: item.evidence_id):
            candidate_id = _candidate_id("CLASS", f"glossary:{term.external_id}")
            candidate = ClassCandidate(candidate_id=candidate_id, canonical_label=term.label, domain=domain, definition=term.definition or "", type_hints=["glossary_term"], supporting_abox_ids=[], evidence=[_evidence(term, f"Explicit glossary term: {term.label}")], provenance=_provenance(domain, candidate_id))
            items.append(InducedSchemaCandidate(candidate, RULE_GLOSSARY, (term.evidence_id,), (str(term.provenance["source_type"]),), 1))
        return tuple(sorted(items, key=lambda item: (item.candidate.kind.value, item.candidate.canonical_label.casefold(), item.candidate.candidate_id)))

    def candidates_for_core(self, result: PreprocessingResult, domain: str | None = None) -> list[SchemaCandidate]:
        """Return the existing schema-contract values at the pre-conceptualization boundary."""
        return [item.candidate for item in self.induce(result, domain)]


def induction_diagnostics(candidates: Iterable[InducedSchemaCandidate], result: PreprocessingResult) -> dict[str, Any]:
    rows = tuple(candidates)
    return {"normalized_entity_evidence": len(result.entities), "normalized_relation_evidence": len(result.relations), "normalized_event_evidence": len(result.events), "normalized_semantic_terms": len(result.semantic_terms), "class_candidates": sum(item.candidate.kind.value == "CLASS" for item in rows), "object_property_candidates": sum(item.candidate.kind.value == "OBJECT_PROPERTY" for item in rows), "data_property_candidates": 0, "event_schema_candidates": 0, "unresolved_evidence": len(result.unresolved), "induction_rule_usage": {rule: sum(item.induction_rule == rule for item in rows) for rule in (RULE_ENTITY_SERVICE, RULE_RELATION_VOCABULARY, RULE_GLOSSARY)}}
