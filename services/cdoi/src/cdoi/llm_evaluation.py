"""Structured, proposal-only LLM experiment boundary."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class LLMAlignmentResponse(BaseModel):
    status: Literal["MATCHED", "NEW", "UNRESOLVED", "REVIEW"]
    relation: Literal["EQUIVALENT", "SUBCLASS_OF", "SUPERCLASS_OF", "RELATED_TO", "NEW_CONCEPT", "UNRESOLVED", "BRIDGE", "PROMOTE"] = Field(validation_alias=AliasChoices("relation", "semantic_relation"))
    target_id: str | None = None
    evidence: list[str] = Field(default_factory=list)
    self_reported_confidence: float = 0.0


PROMPT_CONDITIONS = ("P0", "P1", "P2", "P3")
PROMPT_IDS = {"P0": "qwen_alignment_label_v1", "P1": "qwen_alignment_definition_v1", "P2": "qwen_alignment_retrieval_v1", "P3": "qwen_alignment_context_v1", "BRIDGE": "qwen_bridge_v1"}


def alignment_prompt(case: dict, condition: str) -> str:
    if condition not in PROMPT_CONDITIONS:
        raise ValueError(f"Unknown prompt condition: {condition}")
    lines = ["Return JSON only with status (MATCHED, NEW, UNRESOLVED, REVIEW), semantic_relation (EQUIVALENT, SUBCLASS_OF, SUPERCLASS_OF, RELATED_TO, NEW_CONCEPT, UNRESOLVED, BRIDGE, PROMOTE), target_id, evidence, and self_reported_confidence. Do not provide hidden reasoning or ontology changes.", f"Source label: {case.get('candidate', '')}"]
    if condition in {"P1", "P2", "P3"}:
        lines.append(f"Definition: {case.get('definition', '')}")
    if condition in {"P2", "P3"}:
        lines.append(f"Candidate target: {case.get('target', '')}")
    if condition == "P3":
        lines.extend([f"Domain context: {case.get('source_domain', '')}", f"Relation signature: {case.get('relation_signature', '')}", f"Ontology neighborhood: {case.get('neighborhood', '')}"])
    return "\n".join(lines)
