"""Secret-free transport observability for bounded gateway diagnostics only."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Mapping

import requests

from .company_gateway import CompanyGatewayTransport
from .qwen_rca import QwenRCAConfig

SAFE_HEADER_NAMES = frozenset({
    "x-request-id", "x-trace-id", "x-correlation-id", "x-gateway-id",
    "x-upstream-request-id", "server-timing", "x-route-id", "x-worker-id",
})
FORBIDDEN_HEADER_TERMS = ("authorization", "cookie", "set-cookie", "token", "secret", "api-key")


def stable_json_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def safe_response_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
    """Keep only correlation/timing headers, never credentials or cookies."""
    output: dict[str, str] = {}
    for key, value in (headers or {}).items():
        normalized = str(key).strip().lower()
        if any(term in normalized for term in FORBIDDEN_HEADER_TERMS):
            continue
        if normalized in SAFE_HEADER_NAMES:
            output[normalized] = str(value)
    return dict(sorted(output.items()))


def error_phase(exc: BaseException) -> str:
    if isinstance(exc, requests.ConnectTimeout): return "CONNECT_TIMEOUT"
    if isinstance(exc, requests.ReadTimeout): return "READ_TIMEOUT"
    if isinstance(exc, requests.Timeout): return "TOTAL_TIMEOUT"
    if isinstance(exc, requests.ConnectionError): return "CONNECTION_FAILURE"
    return type(exc).__name__.upper()


def endpoint_host(base_url: str | None) -> str:
    if not base_url: return "UNCONFIGURED"
    match = re.match(r"https?://([^/]+)", base_url)
    return match.group(1) if match else "MALFORMED"


def execute_probe(*, probe_id: str, request_body: Mapping[str, Any], config: QwenRCAConfig,
                  repeat_index: int, timeout_seconds: int = 120) -> Mapping[str, Any]:
    """Perform one non-RCA request and retain only lifecycle metadata."""
    request_id = str(uuid.uuid4())
    started_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    started = perf_counter()
    headers = {"Authorization": f"Bearer {config.api_key()}", "Content-Type": "application/json", **config.headers()}
    # Do not send a speculative correlation header: compatibility is unknown.
    transport = CompanyGatewayTransport()
    base = {
        "client_request_id": request_id, "probe_id": probe_id, "repeat_index": repeat_index,
        "local_start_utc": started_utc, "attempt": 1, "endpoint_host": endpoint_host(config.base_url),
        "requested_model": config.model, "request_bytes": len(json.dumps(request_body, sort_keys=True, separators=(",", ":")).encode()),
        "estimated_input_tokens": len(json.dumps(request_body, sort_keys=True, separators=(",", ":")).encode()) // 4,
        "profile_count": len(request_body.get("messages", [{}, {}])[1].get("content", "")) if False else None,
        "tool_count": len(request_body.get("tools") or []),
        "tool_schema_bytes": len(json.dumps(request_body.get("tools") or [], sort_keys=True, separators=(",", ":")).encode()),
        "response_format_mode": "ON" if request_body.get("response_format") else "OFF",
        "connect_result": "NOT_SEPARATELY_OBSERVABLE_WITH_REQUESTS", "http_response_observed": False,
        "safe_response_headers": {}, "provider_request_or_correlation_id": None,
        "client_generated_correlation_header_sent": False,
    }
    try:
        response = transport.request("POST", config.base_url.rstrip("/") + "/chat/completions", headers=headers,
                                     json=dict(request_body), timeout=timeout_seconds)
        safe = safe_response_headers(getattr(response, "headers", None))
        correlation = next((value for key, value in safe.items() if key in {"x-request-id", "x-trace-id", "x-correlation-id", "x-upstream-request-id"}), None)
        return {**base, "http_response_observed": True, "http_status": getattr(response, "status_code", None),
                "safe_response_headers": safe, "provider_request_or_correlation_id": correlation,
                "elapsed_ms": round((perf_counter() - started) * 1000, 3), "timeout_or_error_class": None,
                "local_end_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")}
    except requests.RequestException as exc:
        return {**base, "http_status": None, "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                "timeout_or_error_class": error_phase(exc),
                "local_end_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")}
