"""Provider-neutral, fail-closed normalization of OpenAI-compatible turns."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


class ProviderOutputError(ValueError):
    """A structural provider-boundary error that is safe to persist."""

    def __init__(self, code: str, path: str = "") -> None:
        super().__init__(code)
        self.code, self.path = code, path


@dataclass(frozen=True)
class CanonicalModelTurn:
    content: str | None
    tool_calls: tuple[Mapping[str, Any], ...]
    finish_reason: str | None
    requested_model: str
    resolved_model: str | None
    normalization_path: str

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "finish_reason": self.finish_reason,
            "message_present": True,
            "message_content_present": self.content is not None,
            "message_content_type": type(self.content).__name__ if self.content is not None else None,
            "message_content_length": len(self.content) if self.content is not None else 0,
            "tool_calls_present": bool(self.tool_calls),
            "tool_call_count": len(self.tool_calls),
            "requested_model": self.requested_model,
            "resolved_model": self.resolved_model,
            "normalization_path": self.normalization_path,
        }


_FENCE = re.compile(r"^```(?:json)?\s*\n(?P<body>\{.*\})\s*\n```$", re.DOTALL)


def _object_text(value: str) -> tuple[str, str]:
    """Accept exactly one object, never substring-reconstruct JSON."""
    text = value.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, Mapping):
            return json.dumps(dict(parsed), sort_keys=True, separators=(",", ":")), "DIRECT_JSON_OBJECT"
        if isinstance(parsed, str):
            decoded = json.loads(parsed)
            if isinstance(decoded, Mapping):
                return json.dumps(dict(decoded), sort_keys=True, separators=(",", ":")), "JSON_STRING_OBJECT"
    except json.JSONDecodeError:
        pass
    if text.count("```") > 2:
        raise ProviderOutputError("QWEN_AMBIGUOUS_OUTPUT", "multiple_fenced_blocks")
    match = _FENCE.fullmatch(text)
    if match:
        try:
            parsed = json.loads(match.group("body"))
        except json.JSONDecodeError as exc:
            raise ProviderOutputError("QWEN_JSON_PARSE_FAILURE", "choices[0].message.content") from exc
        if isinstance(parsed, Mapping):
            return json.dumps(dict(parsed), sort_keys=True, separators=(",", ":")), "JSON_FENCED_OBJECT"
        raise ProviderOutputError("QWEN_CONTENT_NORMALIZATION_FAILURE", "fenced_non_object")
    if "```" in text or ("{" in text and "}" in text):
        raise ProviderOutputError("QWEN_AMBIGUOUS_OUTPUT", "choices[0].message.content")
    return value, "PLAIN_TEXT"


def _content(value: Any) -> tuple[str | None, str]:
    if value is None:
        return None, "EMPTY_CONTENT"
    if isinstance(value, str):
        return _object_text(value)
    # One text block is the only non-string OpenAI-compatible content form
    # supported here. Multiple blocks can be ambiguous and fail closed.
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], Mapping):
        block = value[0]
        if block.get("type") in {"text", "output_text"} and isinstance(block.get("text"), str):
            text, path = _object_text(block["text"])
            return text, "CONTENT_BLOCK_" + path
    raise ProviderOutputError("QWEN_CONTENT_NORMALIZATION_FAILURE", "choices[0].message.content")


def normalize_openai_turn(response: Mapping[str, Any], requested_model: str) -> CanonicalModelTurn:
    try:
        choice = response["choices"][0]
        message = choice["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderOutputError("QWEN_PROVIDER_ENVELOPE_FAILURE", "choices[0].message") from exc
    if not isinstance(choice, Mapping) or not isinstance(message, Mapping):
        raise ProviderOutputError("QWEN_PROVIDER_ENVELOPE_FAILURE", "choices[0].message")
    if choice.get("finish_reason") == "length":
        raise ProviderOutputError("QWEN_OUTPUT_TRUNCATED", "choices[0].finish_reason")
    content, path = _content(message.get("content"))
    calls = message.get("tool_calls") or []
    if not isinstance(calls, list) or not all(isinstance(item, Mapping) for item in calls):
        raise ProviderOutputError("QWEN_TOOL_CALL_PARSE_FAILURE", "choices[0].message.tool_calls")
    if calls and content and content.strip():
        raise ProviderOutputError("QWEN_AMBIGUOUS_OUTPUT", "choices[0].message.content+tool_calls")
    normalized_calls = []
    for index, item in enumerate(calls):
        function = item.get("function")
        if (item.get("type") not in {None, "function"} or not isinstance(function, Mapping)
                or not isinstance(function.get("name"), str)
                or not isinstance(function.get("arguments"), str)):
            raise ProviderOutputError("QWEN_TOOL_CALL_PARSE_FAILURE", f"choices[0].message.tool_calls[{index}]")
        normalized_calls.append({"id": str(item.get("id") or f"local-tool-{index}"), "type": "function",
                                 "function": {"name": function["name"], "arguments": function["arguments"]}})
    resolved = response.get("model") if isinstance(response.get("model"), str) else None
    finish = choice.get("finish_reason") if isinstance(choice.get("finish_reason"), str) else None
    return CanonicalModelTurn(content, tuple(normalized_calls), finish, requested_model, resolved, path)
