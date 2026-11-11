"""Optional real embedding providers used only by V2.5 experiments."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Protocol
from urllib.request import Request, urlopen


class VectorModel(Protocol):
    def encode(self, values: list[str], normalize_embeddings: bool = True): ...


class SentenceTransformerEmbeddingProvider:
    """Lazy local sentence-transformer adapter with content-addressed vector cache."""

    def __init__(self, model_id: str, cache_root: Path, model: VectorModel | None = None, normalize: bool = True):
        self.model_id = model_id
        self.cache_root = cache_root
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.normalize = normalize
        self.calls = 0
        self.cache_hits = 0
        self.dimension: int | None = None

    def _model(self) -> VectorModel:
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_id)
            except ImportError as error:
                raise RuntimeError("embedding_dependency_missing") from error
            except (OSError, RuntimeError, ValueError) as error:
                # Do not leak local paths, driver details, or gateway credentials into a result.
                raise RuntimeError(f"embedding_runtime_unavailable:{type(error).__name__}") from error
        return self.model

    def vector(self, text: str) -> list[float]:
        key = hashlib.sha256(f"{self.model_id}:{self.normalize}:{text}".encode("utf-8")).hexdigest()
        path = self.cache_root / f"{key}.json"
        if path.exists():
            self.cache_hits += 1
            vector = json.loads(path.read_text(encoding="utf-8"))
            self.dimension = len(vector)
            return vector
        self.calls += 1
        value = self._model().encode([text], normalize_embeddings=self.normalize)[0]
        vector = [float(item) for item in value]
        self.dimension = len(vector)
        path.write_text(json.dumps(vector), encoding="utf-8")
        return vector

    def similarity(self, left: str, right: str) -> float:
        a, b = self.vector(left), self.vector(right)
        denominator = math.sqrt(sum(value * value for value in a)) * math.sqrt(sum(value * value for value in b))
        return round(sum(x * y for x, y in zip(a, b)) / denominator, 6) if denominator else 0.0

    def metadata(self) -> dict[str, object]:
        total = self.calls + self.cache_hits
        model = self.model
        return {"provider": "sentence_transformers", "model_id": self.model_id, "model_revision": getattr(model, "revision", None), "embedding_dimension": self.dimension, "normalization": self.normalize, "pooling": "provider_default", "embedding_calls": self.calls, "cache_hits": self.cache_hits, "cache_hit_rate": self.cache_hits / total if total else 1.0}


class OpenAICompatibleEmbeddingProvider:
    """Optional remote embeddings adapter; credentials stay in caller configuration."""

    def __init__(self, base_url: str, api_key: str, model_id: str):
        self.base_url, self.api_key, self.model_id = base_url.rstrip("/"), api_key, model_id
        self.calls = 0

    def vector(self, text: str) -> list[float]:
        payload = json.dumps({"model": self.model_id, "input": text}).encode("utf-8")
        request = Request(f"{self.base_url}/embeddings", data=payload, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=60) as response:  # nosec B310: explicit experimental endpoint
            body = json.loads(response.read().decode("utf-8"))
        self.calls += 1
        return [float(value) for value in body["data"][0]["embedding"]]

    def similarity(self, left: str, right: str) -> float:
        a, b = self.vector(left), self.vector(right)
        denominator = math.sqrt(sum(value * value for value in a)) * math.sqrt(sum(value * value for value in b))
        return round(sum(x * y for x, y in zip(a, b)) / denominator, 6) if denominator else 0.0
