"""Safe, capability-by-capability diagnostics for an OpenAI-compatible model endpoint."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter

import requests

from .company_gateway import CompanyGatewayTransport
from .llm_evaluation import LLMAlignmentResponse
from .model_config import DotenvState, OpenAICompatibleConfig, dotenv_state


@dataclass
class ProbeReport:
    credential_present: bool
    configuration_complete: bool
    gateway_reachable: bool | None
    models_endpoint: str
    basic_chat: bool | None
    json_by_prompt: bool | None
    response_format_json_object: bool | None
    semantic_schema_validation: bool | None
    model_accepted: bool | None
    failure_category: str | None = None
    latency_ms: float | None = None
    diagnostics: list[dict[str, object]] = field(default_factory=list)
    execution_context: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class _TransportResult:
    status: int | None
    body: dict | None
    error: str | None
    diagnostic: dict[str, object]


def probe_gateway(config: OpenAICompatibleConfig, requester=None, environment: DotenvState | None = None, basic_only: bool = False) -> ProbeReport:
    key = config.api_key()
    environment = environment or dotenv_state(config.api_key_env, Path.cwd() / ".env")
    context = {
        **environment.as_dict(),
        "python_executable": sys.executable,
        "working_directory": str(Path.cwd()),
        "config_source": config.config_source,
        "model": config.model,
    }
    if not (config.base_url and config.model and key):
        category = "missing_credential" if not key else "missing_configuration"
        return ProbeReport(bool(key), False, None, "not_attempted", None, None, None, None, None, category, None, [], context)

    # The private IP gateway requires virtual-host routing.
    headers = {"Authorization": f"Bearer {key}", **config.headers()}
    base = config.base_url.rstrip("/")
    started = perf_counter()
    diagnostics: list[dict[str, object]] = []
    requester = requester or CompanyGatewayTransport().request

    if basic_only:
        models = None
        models_endpoint = "not_attempted"
    else:
        models = _request("GET", f"{base}/models", headers, None, requester, timeout=3)
        diagnostics.append(models.diagnostic)
        models_endpoint = "available" if _success(models.status) else "unsupported" if models.status == 404 else _label(models.status, models.error)

    basic = _request("POST", f"{base}/chat/completions", {**headers, "Content-Type": "application/json"}, _chat_payload(config.model, "Reply with exactly OK", 16), requester)
    diagnostics.append(basic.diagnostic)
    reachable = basic.status is not None or (models is not None and models.status is not None)
    elapsed = round((perf_counter() - started) * 1000, 3)
    if not _success(basic.status):
        category = "EXECUTION_CONTEXT_MISMATCH" if basic.status == 403 else _label(basic.status, basic.error)
        context["request_field_names"] = basic.diagnostic["request_field_names"]
        return ProbeReport(True, True, reachable, models_endpoint, False, None, None, None, None, category, elapsed, diagnostics, context)

    if basic_only:
        return ProbeReport(True, True, True, models_endpoint, True, None, None, None, True, None, elapsed, diagnostics, context)

    # Reasoning-capable gateway models can consume a short budget before
    # producing visible content.  This is a diagnostic allowance only; it does
    # not change the configured runtime generation limit.
    diagnostic_tokens = max(config.max_tokens, 512)
    json_prompt = _request("POST", f"{base}/chat/completions", {**headers, "Content-Type": "application/json"}, _chat_payload(config.model, 'Return only JSON: {"status":"ok"}', diagnostic_tokens), requester)
    diagnostics.append(json_prompt.diagnostic)
    json_ok = _success(json_prompt.status) and _is_json(_content(json_prompt.body))
    if not json_ok:
        category = _label(json_prompt.status, json_prompt.error) if not _success(json_prompt.status) else "invalid_response_schema"
        return ProbeReport(True, True, True, models_endpoint, True, False, None, None, True, category, round((perf_counter() - started) * 1000, 3), diagnostics, context)

    response_format = _request("POST", f"{base}/chat/completions", {**headers, "Content-Type": "application/json"}, {**_chat_payload(config.model, 'Return only JSON: {"status":"ok"}', diagnostic_tokens), "response_format": {"type": "json_object"}}, requester)
    diagnostics.append(response_format.diagnostic)
    response_format_ok = _success(response_format.status) and _is_json(_content(response_format.body))

    semantic = _request("POST", f"{base}/chat/completions", {**headers, "Content-Type": "application/json"}, _chat_payload(config.model, _semantic_prompt(), diagnostic_tokens), requester)
    diagnostics.append(semantic.diagnostic)
    semantic_ok = _semantic_content_is_valid(_content(semantic.body)) if _success(semantic.status) else False
    category = None
    if not response_format_ok and not _success(response_format.status):
        category = "response_format_unsupported"
    if not semantic_ok:
        category = category or (_label(semantic.status, semantic.error) if not _success(semantic.status) else "semantic_schema_invalid")
    return ProbeReport(True, True, True, models_endpoint, True, True, response_format_ok, semantic_ok, True, category, round((perf_counter() - started) * 1000, 3), diagnostics, context)


def _chat_payload(model: str, message: str, max_tokens: int) -> dict[str, object]:
    return {"model": model, "messages": [{"role": "user", "content": message}], "temperature": 0, "max_tokens": max_tokens}


def _semantic_prompt() -> str:
    return ('Return only JSON with status MATCHED, semantic_relation EQUIVALENT, target_id probe:target, '
            'evidence ["probe"], and self_reported_confidence 1.0.')


def _request(method: str, url: str, headers: dict[str, str], payload: dict | None, requester, timeout: int = 15) -> _TransportResult:
    diagnostic = {
        "request_path": requests.utils.urlparse(url).path,
        "model": payload.get("model") if payload else None,
        "message_count": len(payload.get("messages", [])) if payload else 0,
        "request_field_names": sorted(payload) if payload else [],
        "effective_host": headers.get("Host"),
        "response_status": None,
        "response_top_level_keys": [],
        "message_field_names": [],
        "content_exists": False,
        "content_type": None,
    }
    try:
        response = requester(method, url, headers=headers, json=payload, timeout=timeout)
        try:
            body = response.json()
        except ValueError:
            body = None
        diagnostic.update(_response_diagnostic(response.status_code, body))
        return _TransportResult(response.status_code, body, None if body is not None else "invalid_json", diagnostic)
    except requests.Timeout:
        return _TransportResult(None, None, "timeout", diagnostic)
    except requests.ConnectionError as error:
        reason = str(error).casefold()
        return _TransportResult(None, None, "connection_refused" if "refused" in reason else "route_unavailable", diagnostic)
    except requests.RequestException:
        return _TransportResult(None, None, "route_unavailable", diagnostic)


def _response_diagnostic(status: int, body: dict) -> dict[str, object]:
    content = _content(body)
    message = _message(body)
    return {
        "response_status": status,
        "response_top_level_keys": sorted(body) if isinstance(body, dict) else [],
        "message_field_names": sorted(message) if isinstance(message, dict) else [],
        "content_exists": content is not None,
        "content_type": type(content).__name__ if content is not None else None,
    }


def _message(body: dict | None) -> dict | None:
    try:
        message = body["choices"][0]["message"]
        return message if isinstance(message, dict) else None
    except (KeyError, IndexError, TypeError):
        return None


def _content(body: dict | None) -> str | None:
    message = _message(body)
    content = message.get("content") if message else None
    return content if isinstance(content, str) else None


def _is_json(content: str | None) -> bool:
    try:
        return isinstance(json.loads(content or ""), dict)
    except json.JSONDecodeError:
        return False


def _semantic_content_is_valid(content: str | None) -> bool:
    try:
        LLMAlignmentResponse.model_validate(json.loads(content or ""))
        return True
    except (ValueError, json.JSONDecodeError):
        return False


def _success(status: int | None) -> bool:
    return status is not None and 200 <= status < 300


def _label(status: int | None, error: str | None) -> str:
    return str(status) if status in {401, 403, 404} else error or "unknown_transport_error"
