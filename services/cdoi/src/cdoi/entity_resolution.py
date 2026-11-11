from __future__ import annotations

from enum import Enum
from pydantic import BaseModel

from .models import EntityCandidate


class EntityResolutionRelation(str, Enum):
    SAME_ENTITY_CANDIDATE = "SAME_ENTITY_CANDIDATE"
    UNRESOLVED = "UNRESOLVED"


class EntityResolutionDecision(BaseModel):
    left_id: str
    right_id: str
    relation: EntityResolutionRelation
    confidence: float
    evidence: list[str] = []


class DeterministicEntityResolver:
    """Boundary only: strong source identifiers yield a candidate, never owl:sameAs."""

    def resolve(self, left: EntityCandidate, right: EntityCandidate) -> EntityResolutionDecision:
        same_source_id = left.id == right.id and left.id != ""
        return EntityResolutionDecision(left_id=left.id, right_id=right.id, relation=EntityResolutionRelation.SAME_ENTITY_CANDIDATE if same_source_id else EntityResolutionRelation.UNRESOLVED, confidence=0.95 if same_source_id else 0.0, evidence=["Identical source identifier."] if same_source_id else ["Insufficient strong identity evidence; no owl:sameAs asserted."])
