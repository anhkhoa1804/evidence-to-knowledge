from __future__ import annotations

import re
import hashlib
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .company_gateway import CompanyGatewayTransport
from .models import ConceptProfile, EntityCandidate, Provenance, SchemaCandidate
from .prompts import PROMPTS

T = TypeVar("T", bound=BaseModel)
PROMPT_VERSION = "conceptualization_v1"
CONCEPTUALIZATION_PROMPT = PROMPTS[PROMPT_VERSION]


class LLMClient(Protocol):
    def structured_generate(self, prompt: str, schema: type[T]) -> T: ...


class OpenAICompatibleLLM:
    """Optional Chat Completions JSON client; never used by the deterministic test path."""

    def __init__(self, base_url: str, api_key: str, model: str, headers: dict[str, str] | None = None, temperature: float = 0.0, max_tokens: int = 256, transport: CompanyGatewayTransport | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.headers = headers or {}
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.last_usage: dict[str, int] = {}
        self.transport = transport or CompanyGatewayTransport()

    def cache_identity(self) -> str:
        # Identity is sufficient for reproducibility but deliberately excludes the token.
        return f"openai-compatible:{self.base_url}:{self.model}:{self.temperature}:{self.max_tokens}:{sorted(self.headers)}"

    def structured_generate(self, prompt: str, schema: type[T]) -> T:
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": self.temperature, "max_tokens": self.max_tokens, "response_format": {"type": "json_object"}}
        response = self.transport.request("POST", f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", **self.headers}, json=payload, timeout=60)
        body = response.json()
        self.last_usage = {key: int(value) for key, value in body.get("usage", {}).items() if isinstance(value, int)}
        return schema.model_validate_json(body["choices"][0]["message"]["content"])


class CachingLLMClient:
    """Content-addressed structured-output cache for repeatable remote-model experiments."""
    def __init__(self, delegate: LLMClient, root: Path):
        self.delegate = delegate
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        self.cache_hits = 0
        self.parse_failures = 0
        self.failed_calls = 0

    def structured_generate(self, prompt: str, schema: type[T]) -> T:
        identity = getattr(self.delegate, "cache_identity", lambda: type(self.delegate).__name__)()
        key = hashlib.sha256(f"{identity}:{schema.__name__}:{prompt}".encode("utf-8")).hexdigest()
        path = self.root / f"{key}.json"
        if path.exists():
            self.cache_hits += 1
            try:
                return schema.model_validate_json(path.read_text(encoding="utf-8"))
            except ValueError:
                self.parse_failures += 1
                raise
        self.calls += 1
        try:
            value = self.delegate.structured_generate(prompt, schema)
        except ValueError:
            self.parse_failures += 1
            self.failed_calls += 1
            raise
        path.write_text(value.model_dump_json(), encoding="utf-8")
        return value

    def metrics(self) -> dict[str, float | int]:
        total = self.calls + self.cache_hits
        return {"llm_calls": self.calls, "successful_calls": self.calls - self.failed_calls, "failed_calls": self.failed_calls, "cache_hits": self.cache_hits, "cache_hit_rate": self.cache_hits / total if total else 1.0, "parse_failures": self.parse_failures}


class MockConceptualizer:
    """Deterministic, inspectable stand-in for an LLM conceptualization stage."""

    def conceptualize(self, entity: EntityCandidate | SchemaCandidate, domain: str, provenance: Provenance) -> ConceptProfile:
        label_value = entity.surface if isinstance(entity, EntityCandidate) else entity.canonical_label
        definition = entity.definition
        relations = entity.relations if isinstance(entity, EntityCandidate) else list(entity.relation_signature)
        identifier = entity.id if isinstance(entity, EntityCandidate) else entity.candidate_id
        kind = getattr(entity, "kind", None)
        words = re.findall(r"[a-z0-9]+", f"{label_value} {definition}".casefold())
        features = set(words) | {relation.casefold() for relation in relations}
        abstractions: list[str] = []
        label = label_value.casefold()
        if "pod" in label:
            abstractions = ["runtime environment", "computing artifact"]
            features.update({"orchestration", "runtime", "container"})
        elif "organization" in label:
            abstractions = ["organization"]
        elif "role" in label:
            abstractions = ["external party role"]
            features.add("role")
        elif "wallet" in label:
            abstractions = ["payment account"]
        return ConceptProfile(candidate_id=identifier, canonical_label=label_value, local_definition=definition, abstraction_candidates=abstractions, semantic_features=features, relation_signature=set(relations), domain=domain, source_candidates=[label_value], provenance=provenance, kind=kind or "CLASS")
