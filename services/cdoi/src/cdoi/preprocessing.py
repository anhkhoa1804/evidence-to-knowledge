from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import SourceReference


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    reference: SourceReference


def normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _walk_json(value: Any, path: list[str], source: Path, system: str) -> list[DocumentChunk]:
    if isinstance(value, dict):
        chunks: list[DocumentChunk] = []
        for key, nested in value.items():
            chunks.extend(_walk_json(nested, path + [str(key)], source, system))
        return chunks
    if isinstance(value, list):
        return [item for index, nested in enumerate(value) for item in _walk_json(nested, path + [str(index)], source, system)]
    text = normalize_text(str(value))
    if not text:
        return []
    return [DocumentChunk(text, SourceReference(source_path=str(source), source_system=system, source_span="$." + ".".join(path), hierarchy=path))]


def preprocess_json(path: Path, source_system: str = "fixture") -> list[DocumentChunk]:
    return _walk_json(json.loads(path.read_text(encoding="utf-8")), [], path, source_system)


def preprocess_markdown(path: Path, source_system: str = "fixture") -> list[DocumentChunk]:
    heading: list[str] = []
    chunks: list[DocumentChunk] = []
    paragraphs: list[str] = []
    for index, line in enumerate(normalize_text(path.read_text(encoding="utf-8")).split("\n"), 1):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            if paragraphs:
                chunks.append(DocumentChunk("\n".join(paragraphs), SourceReference(source_path=str(path), source_system=source_system, source_span=f"lines through {index - 1}", hierarchy=heading.copy())))
                paragraphs = []
            level, title = len(match.group(1)), match.group(2).strip()
            heading = heading[: level - 1] + [title]
        elif line.strip():
            paragraphs.append(line)
        elif paragraphs:
            chunks.append(DocumentChunk("\n".join(paragraphs), SourceReference(source_path=str(path), source_system=source_system, source_span=f"line {index}", hierarchy=heading.copy())))
            paragraphs = []
    if paragraphs:
        chunks.append(DocumentChunk("\n".join(paragraphs), SourceReference(source_path=str(path), source_system=source_system, source_span="final paragraph", hierarchy=heading.copy())))
    return chunks


def preprocess_text(path: Path, source_system: str = "fixture") -> list[DocumentChunk]:
    return [DocumentChunk(paragraph, SourceReference(source_path=str(path), source_system=source_system, source_span=f"paragraph {index + 1}")) for index, paragraph in enumerate(re.split(r"\n\s*\n", normalize_text(path.read_text(encoding="utf-8")))) if paragraph]


def preprocess(path: Path, source_system: str = "fixture") -> list[DocumentChunk]:
    suffix = path.suffix.casefold()
    if suffix == ".json":
        return preprocess_json(path, source_system)
    if suffix in {".md", ".markdown"}:
        return preprocess_markdown(path, source_system)
    return preprocess_text(path, source_system)
