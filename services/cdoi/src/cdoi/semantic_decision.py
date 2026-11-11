"""V3 semantic-decision contracts.

This module is deliberately outside the ontology proposal/commit path.  It
wraps observable retrieval and selector evidence so diagnostics can be replayed
without conflating retrieval, selection, technical availability, calibrated
commitment confidence, or review policy.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from time import perf_counter
from typing import Any, Callable, Mapping, Protocol
from types import MappingProxyType

from .qwen_reliability import classify_response


REFERENCE_ONLY_KEYS = frozenset({
    "gold", "gold_candidate", "gold_target", "gold_target_iri", "gold_rank",
    "correct", "correctness", "reference", "reference_mapping", "nontrivial",
})
SECRET_KEYS = frozenset({"authorization", "api_key", "apikey", "bearer", "token", "password", "secret"})


def _reject_reference(value: Any, path: str = "") -> None:
    """Fail before reference-only fields can become inference evidence."""
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).casefold()
            if key_text in REFERENCE_ONLY_KEYS or key_text.startswith("gold_"):
                raise ValueError(f"reference-only field is forbidden in inference artifact: {path}{key}")
            _reject_reference(nested, f"{path}{key}.")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_reference(nested, f"{path}{index}.")


def _reject_secret_metadata(value: Mapping[str, Any]) -> None:
    for key in value:
        if str(key).casefold() in SECRET_KEYS:
            raise ValueError("selector runtime metadata must not persist credentials")


def _canonical_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceProfileReference:
    source_id: str
    profile_version: str = "unknown"
    profile_hash: str | None = None


@dataclass(frozen=True)
class CandidateEvidence:
    candidate_id: str
    rank: int
    retrieval_score: float
    retrieval_method: str
    observable_evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id or self.rank < 1:
            raise ValueError("candidate_id and positive rank are required")
        _reject_reference(dict(self.observable_evidence))
        object.__setattr__(self, "observable_evidence", MappingProxyType(dict(self.observable_evidence)))


@dataclass(frozen=True)
class CandidateSet:
    """Immutable retrieval artifact.  It intentionally contains no gold data."""
    source_id: str
    source_profile_reference: SourceProfileReference
    candidates: tuple[CandidateEvidence, ...]
    retriever_id: str
    retriever_version: str
    index_version: str | None = None
    index_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.source_id or not self.candidates:
            raise ValueError("CandidateSet requires a source and at least one candidate")
        ranks = tuple(candidate.rank for candidate in self.candidates)
        ids = tuple(candidate.candidate_id for candidate in self.candidates)
        if ranks != tuple(range(1, len(self.candidates) + 1)):
            raise ValueError("CandidateSet ranks must preserve the contiguous retrieval order")
        if len(ids) != len(set(ids)):
            raise ValueError("CandidateSet candidate IDs must be unique")

    @property
    def artifact_hash(self) -> str:
        return _canonical_hash({
            "source_id": self.source_id,
            "source_profile_reference": asdict(self.source_profile_reference),
            "candidates": [{"candidate_id": candidate.candidate_id, "rank": candidate.rank, "retrieval_score": candidate.retrieval_score, "retrieval_method": candidate.retrieval_method, "observable_evidence": dict(candidate.observable_evidence)} for candidate in self.candidates],
            "retriever_id": self.retriever_id,
            "retriever_version": self.retriever_version,
            "index_version": self.index_version,
            "index_hash": self.index_hash,
        })

    def presentation_handles(self, opaque: bool = False) -> Mapping[str, str]:
        return {candidate.candidate_id: f"C{index:02d}" if opaque else candidate.candidate_id for index, candidate in enumerate(self.candidates, 1)}

    @classmethod
    def from_rows(cls, source_id: str, source_profile_reference: SourceProfileReference, rows: list[Mapping[str, Any]], *, retriever_id: str, retriever_version: str, index_version: str | None = None, index_hash: str | None = None) -> "CandidateSet":
        candidates = []
        for index, row in enumerate(rows, 1):
            _reject_reference(dict(row))
            candidate_id = str(row.get("candidate_id", row.get("iri", "")))
            score = float(row.get("retrieval_score", row.get("score", 0.0)))
            evidence = {key: value for key, value in row.items() if key not in {"candidate_id", "iri", "rank", "retrieval_score", "score", "retrieval_method"}}
            candidates.append(CandidateEvidence(candidate_id, int(row.get("rank", index)), score, str(row.get("retrieval_method", retriever_id)), evidence))
        return cls(source_id, source_profile_reference, tuple(candidates), retriever_id, retriever_version, index_version, index_hash)


def candidate_set_from_v26_row(row: Mapping[str, Any], *, method: str, profile_version: str = "oaei_profile_v2_6_6", index_version: str | None = None, index_hash: str | None = None) -> CandidateSet:
    """Migrate only observable V2.6 retrieval fields out of a diagnostic row.

    V2.6 rows also carry evaluation labels.  This adapter selects the source ID
    and supplied retrieved candidates explicitly instead of copying the row, so
    gold rank/correctness cannot cross into the CandidateSet.
    """
    source_id = str(row["source_iri"])
    allowed = {"rank", "iri", "label", "definition", "score", "lexical_score", "context_score", "context_available", "r2_combined_score", "r2_lexical_score", "r2_context_score"}
    candidates = [{key: value for key, value in candidate.items() if key in allowed} for candidate in row["retrieved_candidates"]]
    return CandidateSet.from_rows(source_id, SourceProfileReference(source_id, profile_version), candidates, retriever_id=method, retriever_version="v2_6_6_wrapped", index_version=index_version, index_hash=index_hash)


@dataclass(frozen=True)
class SemanticEvidence:
    """Selector-facing profile fields.  Missing fields stay empty; no invention."""
    source_id: str
    label: str
    aliases: tuple[str, ...] = ()
    definition: str | None = None
    parents: tuple[str, ...] = ()
    children: tuple[str, ...] = ()
    properties: tuple[str, ...] = ()
    profile_version: str = "unknown"

    @property
    def completeness(self) -> Mapping[str, bool]:
        return {"label": bool(self.label), "aliases": bool(self.aliases), "definition": bool(self.definition), "parents": bool(self.parents), "children": bool(self.children), "properties": bool(self.properties)}


class EvidenceAssembler:
    """The only V3 builder for selector evidence; it rejects evaluation labels."""
    version = "v3_evidence_assembler_v1"

    def from_mapping(self, profile: Mapping[str, Any]) -> SemanticEvidence:
        _reject_reference(profile)
        allowed = {"source_id", "iri", "candidate_id", "label", "canonical_label", "aliases", "definition", "local_definition", "parents", "children", "object_properties", "data_properties", "profile_version"}
        unknown = set(profile) - allowed
        if unknown:
            raise ValueError(f"unsupported selector-evidence fields: {sorted(unknown)}")
        return self.assemble(type("Profile", (), dict(profile))())

    def assemble(self, profile: Any) -> SemanticEvidence:
        raw = {
            "source_id": getattr(profile, "iri", getattr(profile, "candidate_id", "")),
            "label": getattr(profile, "label", getattr(profile, "canonical_label", "")),
            "aliases": tuple(getattr(profile, "aliases", ())),
            "definition": getattr(profile, "definition", getattr(profile, "local_definition", None)),
            "parents": tuple(getattr(profile, "parents", ())),
            "children": tuple(getattr(profile, "children", ())),
            "properties": tuple(getattr(profile, "object_properties", ())) + tuple(getattr(profile, "data_properties", ())),
        }
        _reject_reference(raw)
        return SemanticEvidence(**raw)


@dataclass(frozen=True)
class AmbiguityEvidence:
    top1_score: float
    top2_score: float | None
    top1_top2_margin: float | None
    topk_score_spread: float
    candidate_count: int
    profile_completeness: Mapping[str, bool]
    r1_r2_disagreement: bool | None = None
    structural_evidence_available: bool = False

    @classmethod
    def from_candidate_set(cls, candidate_set: CandidateSet, profile: SemanticEvidence, r2_candidate_id: str | None = None) -> "AmbiguityEvidence":
        scores = [candidate.retrieval_score for candidate in candidate_set.candidates]
        top1, top2 = scores[0], scores[1] if len(scores) > 1 else None
        return cls(top1, top2, round(top1 - top2, 6) if top2 is not None else None, round(top1 - scores[-1], 6), len(scores), profile.completeness, (candidate_set.candidates[0].candidate_id != r2_candidate_id) if r2_candidate_id else None, bool(profile.parents or profile.children or profile.properties))


class SelectionStatus(str, Enum):
    SELECTED = "SELECTED"
    SEMANTIC_ABSTAIN = "SEMANTIC_ABSTAIN"
    TECHNICAL_UNAVAILABLE = "TECHNICAL_UNAVAILABLE"


@dataclass(frozen=True)
class SelectionResult:
    status: SelectionStatus
    candidate_id: str | None
    relation: str | None
    selector_id: str
    selector_version: str
    candidate_set_hash: str
    selection_score: float | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    model_config_version: str | None = None
    response_budget: int | None = None
    retry_policy: str | None = None
    runtime_config: Mapping[str, Any] = field(default_factory=dict)
    attempt_count: int = 0
    latency_ms: float | None = None
    technical_status: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _reject_secret_metadata(self.runtime_config)
        if self.status == SelectionStatus.SELECTED and (not self.candidate_id or not self.relation):
            raise ValueError("SELECTED requires candidate_id and relation")
        if self.status == SelectionStatus.SEMANTIC_ABSTAIN and (self.candidate_id is not None or self.relation is not None):
            raise ValueError("SEMANTIC_ABSTAIN cannot carry a target or relation")
        if self.status == SelectionStatus.TECHNICAL_UNAVAILABLE and (self.candidate_id is not None or self.relation is not None):
            raise ValueError("TECHNICAL_UNAVAILABLE cannot masquerade as a semantic result")


class SemanticSelector(Protocol):
    def select(self, source_profile: SemanticEvidence, candidate_set: CandidateSet, evidence: AmbiguityEvidence) -> SelectionResult: ...


class R1DeterministicSelector:
    selector_id = "R1_FUZZY_LEXICAL_SELECTOR"
    selector_version = "v2_6_6_wrapped"

    def select(self, source_profile: SemanticEvidence, candidate_set: CandidateSet, evidence: AmbiguityEvidence) -> SelectionResult:
        candidate = candidate_set.candidates[0]
        return SelectionResult(SelectionStatus.SELECTED, candidate.candidate_id, "EQUIVALENT", self.selector_id, self.selector_version, candidate_set.artifact_hash, selection_score=candidate.retrieval_score, technical_status="DETERMINISTIC_AVAILABLE")


class R2DeterministicSelector:
    selector_id = "R2_LEXICAL_CONTEXT_SELECTOR"
    selector_version = "v2_6_6_wrapped"

    def select(self, source_profile: SemanticEvidence, candidate_set: CandidateSet, evidence: AmbiguityEvidence) -> SelectionResult:
        # Preserve V2.6's exact R2 tie-breaker: descending combined score, IRI/ID.
        candidate = min(candidate_set.candidates, key=lambda item: (-float(item.observable_evidence.get("r2_combined_score", item.retrieval_score)), item.candidate_id))
        return SelectionResult(SelectionStatus.SELECTED, candidate.candidate_id, "EQUIVALENT", self.selector_id, self.selector_version, candidate_set.artifact_hash, selection_score=float(candidate.observable_evidence.get("r2_combined_score", candidate.retrieval_score)), technical_status="DETERMINISTIC_AVAILABLE")


class DenseScoringBackend(Protocol):
    backend_id: str
    backend_version: str
    model_id: str
    def score(self, source: SemanticEvidence, candidate: SemanticEvidence) -> float: ...


class DenseSemanticSelector:
    """Configurable dense shared-Top-K selector; no runtime is assumed available."""
    selector_id = "DENSE_SEMANTIC_SELECTOR"
    selector_version = "v3_phase2_v1"

    def __init__(self, backend: DenseScoringBackend, candidate_evidence: Mapping[str, SemanticEvidence]):
        self.backend, self.candidate_evidence = backend, candidate_evidence

    def select(self, source_profile: SemanticEvidence, candidate_set: CandidateSet, evidence: AmbiguityEvidence) -> SelectionResult:
        started = perf_counter()
        try:
            scored = [(float(self.backend.score(source_profile, self.candidate_evidence[candidate.candidate_id])), candidate.candidate_id) for candidate in candidate_set.candidates]
        except Exception as error:
            return SelectionResult(SelectionStatus.TECHNICAL_UNAVAILABLE, None, None, self.selector_id, self.selector_version, candidate_set.artifact_hash, model_id=getattr(self.backend, "model_id", None), model_config_version=f"{getattr(self.backend, 'backend_id', 'unknown')}:{getattr(self.backend, 'backend_version', 'unknown')}", attempt_count=1, latency_ms=round((perf_counter() - started) * 1000, 3), technical_status=f"DENSE_BACKEND_ERROR:{type(error).__name__}")
        score, candidate_id = min(scored, key=lambda item: (-item[0], item[1]))
        return SelectionResult(SelectionStatus.SELECTED, candidate_id, "EQUIVALENT", self.selector_id, self.selector_version, candidate_set.artifact_hash, selection_score=score, model_id=getattr(self.backend, "model_id", None), model_config_version=f"{getattr(self.backend, 'backend_id', 'unknown')}:{getattr(self.backend, 'backend_version', 'unknown')}", attempt_count=1, latency_ms=round((perf_counter() - started) * 1000, 3), technical_status="DENSE_AVAILABLE")


QSEM_PROTOCOL_V1 = {
    "protocol_id": "QSEM_V1",
    "prompt_version": "QSEM_COMPACT_PROFILE_V1",
    "schema_version": "candidate_id_relation_v1",
    "response_budget": 512,
    "retry_policy": "bounded_retry_v2_6_6",
}


def qsem_v1_prompt(source: SemanticEvidence, candidate_set: CandidateSet, candidate_evidence: Mapping[str, SemanticEvidence], *, opaque_handles: bool = False) -> tuple[str, Mapping[str, str]]:
    """Frozen compact prompt protocol. Candidate order is CandidateSet order."""
    handles = candidate_set.presentation_handles(opaque_handles)
    def profile(value: SemanticEvidence, identifier: str) -> Mapping[str, Any]:
        return {"id": identifier, "label": value.label, "aliases": list(value.aliases), "parents": list(value.parents), "children": list(value.children), "properties": list(value.properties)}
    payload = {"source": profile(source, source.source_id), "candidates": [profile(candidate_evidence[item.candidate_id], handles[item.candidate_id]) for item in candidate_set.candidates]}
    _reject_reference(payload)
    return "\n".join((
        'Return only JSON: {"candidate_id":"a supplied id or NONE","relation":"EQUIVALENT or NONE"}.',
        "Choose only a supplied candidate when evidence supports Anatomy equivalence; otherwise choose NONE. Do not explain.",
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )), handles


class QwenCompactSelector:
    """Experiment-only selector adapter. It is never wired into normal ingest."""
    selector_id = "QWEN_COMPACT_SELECTOR"
    selector_version = "v2_6_6_wrapped"

    def __init__(self, requester: Callable[..., Any], model_id: str, headers: Mapping[str, str] | None = None, response_budget: int = 512, max_attempts: int = 2, opaque_handles: bool = False):
        self.requester, self.model_id, self.headers = requester, model_id, dict(headers or {})
        self.response_budget, self.max_attempts, self.opaque_handles = response_budget, max_attempts, opaque_handles

    def select(self, source_profile: SemanticEvidence, candidate_set: CandidateSet, evidence: AmbiguityEvidence, candidate_evidence: Mapping[str, SemanticEvidence] | None = None) -> SelectionResult:
        profiles = dict(candidate_evidence or {})
        profiles.setdefault(source_profile.source_id, source_profile)
        for candidate in candidate_set.candidates:
            profiles.setdefault(candidate.candidate_id, SemanticEvidence(candidate.candidate_id, str(candidate.observable_evidence.get("label", candidate.candidate_id))))
        prompt, handles = qsem_v1_prompt(source_profile, candidate_set, profiles, opaque_handles=self.opaque_handles)
        presented = set(handles.values()); lifecycle: Mapping[str, Any] = {}; response = None; started = perf_counter()
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.requester("POST", headers=self.headers, json={"model": self.model_id, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": self.response_budget}, timeout=30)
                lifecycle = classify_response(response, presented, self.response_budget, round((perf_counter() - started) * 1000, 3))
            except Exception as error:
                lifecycle = {"final_status": "TRANSPORT_ERROR", "error_type": type(error).__name__, "latency_ms": round((perf_counter() - started) * 1000, 3)}
            if lifecycle["final_status"] in {"VALID_SELECTION", "MODEL_ABSTENTION"}:
                break
        common = dict(selector_id=self.selector_id, selector_version=self.selector_version, candidate_set_hash=candidate_set.artifact_hash, model_id=self.model_id, prompt_version=QSEM_PROTOCOL_V1["prompt_version"], schema_version=QSEM_PROTOCOL_V1["schema_version"], model_config_version="external_requester", response_budget=self.response_budget, retry_policy=QSEM_PROTOCOL_V1["retry_policy"], runtime_config={"temperature": 0, "opaque_handles": self.opaque_handles, "max_attempts": self.max_attempts}, attempt_count=attempt, latency_ms=float(lifecycle.get("latency_ms", 0.0)), technical_status=str(lifecycle.get("final_status")))
        if lifecycle["final_status"] not in {"VALID_SELECTION", "MODEL_ABSTENTION"}:
            return SelectionResult(SelectionStatus.TECHNICAL_UNAVAILABLE, None, None, **common)
        content = response.json()["choices"][0]["message"].get("content", "")
        parsed = json.loads(content[content.find("{"):content.rfind("}") + 1])
        if parsed["candidate_id"] == "NONE":
            return SelectionResult(SelectionStatus.SEMANTIC_ABSTAIN, None, None, **common)
        reverse = {handle: candidate_id for candidate_id, handle in handles.items()}
        return SelectionResult(SelectionStatus.SELECTED, reverse[parsed["candidate_id"]], parsed["relation"], **common)


@dataclass(frozen=True)
class CommitmentEvidence:
    status: str
    method: str
    calibration_id: str | None
    calibration_version: str | None
    score: float | None = None
    evidence_fields: Mapping[str, Any] = field(default_factory=dict)


class CommitmentConfidence(Protocol):
    def assess(self, candidate_set: CandidateSet, ambiguity: AmbiguityEvidence, selection: SelectionResult, semantic_evidence: SemanticEvidence) -> CommitmentEvidence: ...


class UncalibratedCommitmentConfidence:
    """Phase-1 fail-closed protocol: V3 does not estimate commitment probability."""
    method = "UNCALIBRATED_PROTOCOL_ONLY"

    def assess(self, candidate_set: CandidateSet, ambiguity: AmbiguityEvidence, selection: SelectionResult, semantic_evidence: SemanticEvidence) -> CommitmentEvidence:
        return CommitmentEvidence("NOT_CALIBRATED", self.method, None, None, None, {"selection_status": selection.status.value, "candidate_set_hash": candidate_set.artifact_hash})


class DecisionAction(str, Enum):
    PROPOSE_FOR_REVIEW = "PROPOSE_FOR_REVIEW"
    UNRESOLVED = "UNRESOLVED"
    REJECT = "REJECT"


@dataclass(frozen=True)
class DecisionPolicyResult:
    action: DecisionAction
    reason: str


class ConservativeDecisionPolicy:
    """Policy boundary only. It never auto-accepts or mutates ontology/KG state."""
    policy_id = "V3_CONSERVATIVE_REVIEW_ONLY"

    def decide(self, selection: SelectionResult, commitment: CommitmentEvidence) -> DecisionPolicyResult:
        if selection.status == SelectionStatus.TECHNICAL_UNAVAILABLE:
            return DecisionPolicyResult(DecisionAction.UNRESOLVED, "selector_technical_unavailable")
        if selection.status == SelectionStatus.SEMANTIC_ABSTAIN:
            return DecisionPolicyResult(DecisionAction.UNRESOLVED, "selector_semantic_abstention")
        return DecisionPolicyResult(DecisionAction.PROPOSE_FOR_REVIEW, "selected_without_calibrated_commitment; existing validation/review remains authoritative")


class ExperimentalSelectorPolicy:
    """Marker boundary for future experiments. Never call it from normal ingest."""
    policy_id = "EXPERIMENTAL_NO_ROUTING_V1"

    def choose(self, ambiguity: AmbiguityEvidence, available_selectors: tuple[str, ...]) -> str | None:
        return None
