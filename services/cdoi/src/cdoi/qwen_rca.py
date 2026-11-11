"""Qwen OpenAI-compatible adapter for the read-only RCA Agent V0.

This module is deliberately separate from the proposal-only semantic-selector
Qwen path.  It performs no semantic selection, KG write, or remediation.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from time import perf_counter, sleep
from typing import Any, Callable, Mapping

import requests

from .company_gateway import CompanyGatewayTransport

QWEN_RCA_PROMPT_VERSION = "rca_agent_qwen_v1"
QWEN_RCA_ADAPTER_VERSION = "qwen_rca_openai_compatible_v1"
INTERNAL_QWEN_PROFILE = "DMP_INTERNAL_QWEN"


class QwenRCAError(ValueError):
    """Fail-closed provider/runtime error safe to persist without secrets."""
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code)
        self.code, self.detail = code, detail


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None: return default
    if value.strip().casefold() in {"1", "true", "yes"}: return True
    if value.strip().casefold() in {"0", "false", "no"}: return False
    raise ValueError("INVALID_QWEN_ENABLE_THINKING")


def _credential_env_name(value: str | None, default: str) -> str:
    """Accept an environment-variable *name*, never a credential value."""
    candidate = (value or default).strip()
    return candidate if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate) else default


@dataclass(frozen=True)
class QwenRCAConfig:
    provider: str = "qwen-openai-compatible"
    model: str = "qwen3.8-max-0902"
    base_url: str | None = None
    region: str = "UNSPECIFIED"
    api_key_env: str = "QWEN_API_KEY"
    # ``None`` means omit the provider extension and retain gateway default.
    enable_thinking: bool | None = False
    timeout_seconds: int = 30
    max_retries: int = 1
    provider_profile: str = "GENERIC_QWEN"
    host_header: str | None = None

    @classmethod
    def from_environment(cls) -> "QwenRCAConfig":
        key_env = "QWEN_API_KEY" if os.environ.get("QWEN_API_KEY") else "DASHSCOPE_API_KEY"
        return cls(
            provider=os.environ.get("QWEN_PROVIDER", "qwen-openai-compatible"),
            model=os.environ.get("QWEN_MODEL", "qwen3.8-max-0902"),
            base_url=os.environ.get("QWEN_BASE_URL") or os.environ.get("DASHSCOPE_BASE_URL"),
            region=os.environ.get("QWEN_REGION", "UNSPECIFIED"),
            api_key_env=key_env,
            enable_thinking=_bool(os.environ.get("QWEN_ENABLE_THINKING"), False),
            timeout_seconds=int(os.environ.get("QWEN_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.environ.get("QWEN_MAX_RETRIES", "1")),
        )

    @classmethod
    def from_internal_gateway_environment(cls) -> "QwenRCAConfig":
        """Explicit, isolated profile for the private DMP OpenAI gateway.

        It intentionally does not change the generic Qwen/DashScope defaults.
        The legacy CDOI_LLM names are read only as a compatibility bridge for
        repository-local configuration, never as an implicit generic profile.
        """
        profile = os.environ.get("CDOI_QWEN_PROVIDER_PROFILE", INTERNAL_QWEN_PROFILE)
        if profile != INTERNAL_QWEN_PROFILE:
            raise ValueError("INVALID_INTERNAL_QWEN_PROVIDER_PROFILE")
        configured_key_env = _credential_env_name(os.environ.get("CDOI_QWEN_API_KEY_ENV") or os.environ.get("CDOI_LLM_API_KEY_ENV"), "DMP_MERCURY")
        # A string which merely resembles an identifier can still be a token
        # (for example an ``sk_...`` value). A profile may only expose a name
        # that resolves to an actual process variable; otherwise use the
        # governed default name and report the credential as unavailable.
        key_env = configured_key_env if configured_key_env in os.environ else "DMP_MERCURY"
        return cls(
            provider="vllm",
            provider_profile=profile,
            model=os.environ.get("CDOI_QWEN_MODEL") or os.environ.get("CDOI_LLM_MODEL") or "vllm/Qwen3.8-27B",
            base_url=os.environ.get("CDOI_QWEN_BASE_URL") or os.environ.get("CDOI_LLM_BASE_URL"),
            host_header=os.environ.get("CDOI_QWEN_HOST_HEADER") or os.environ.get("CDOI_LLM_HOST_HEADER"),
            api_key_env=key_env,
            region="INTERNAL",
            enable_thinking=None,
            timeout_seconds=int(os.environ.get("CDOI_QWEN_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.environ.get("CDOI_QWEN_MAX_RETRIES", "1")),
        )

    def api_key(self) -> str | None: return os.environ.get(self.api_key_env)

    def status(self) -> str:
        if not self.api_key() or not self.base_url: return "QWEN_PROVIDER_UNCONFIGURED"
        if self.timeout_seconds < 1 or self.max_retries < 0: return "QWEN_PROVIDER_UNCONFIGURED"
        return "QWEN_LIVE_READY"

    def public_metadata(self) -> Mapping[str, Any]:
        return {"provider": self.provider, "provider_profile": self.provider_profile, "api_style": "OPENAI_COMPATIBLE", "requested_model": self.model, "region": self.region, "base_url_class": "INTERNAL_IP_CONFIGURED" if self.provider_profile == INTERNAL_QWEN_PROFILE and self.base_url else "CONFIGURED" if self.base_url else "UNCONFIGURED", "api_key_env": self.api_key_env, "credential_configured": bool(self.api_key()), "host_header_configured": bool(self.host_header), "thinking_mode": "GATEWAY_DEFAULT" if self.enable_thinking is None else self.enable_thinking, "timeout_seconds": self.timeout_seconds, "max_retries": self.max_retries, "adapter_version": QWEN_RCA_ADAPTER_VERSION}

    def headers(self) -> dict[str, str]:
        return {"Host": self.host_header} if self.host_header else {}


def rca_system_prompt() -> str:
    return "\n".join((
        "You are investigating hypotheses, not proving causality.",
        "Candidate != Cause. Metric shift != Cause. ERROR span != Cause.",
        "Trace path != causal path. Temporal precedence != causality. Missing evidence != contradiction.",
        "Do not invent telemetry, topology, deployments, or benchmark answers.",
        "Use only the supplied read-only tools and cite retrieved evidence IDs.",
        "Abstain with INSUFFICIENT_EVIDENCE when evidence cannot distinguish candidates.",
        "Return exactly one JSON object matching the supplied RCA report schema when no tool is needed.",
    ))


def _tools() -> list[Mapping[str, Any]]:
    names = ("get_incident_summary", "get_candidates", "get_expanded_candidates", "get_candidate_profile", "get_metric_evidence", "get_trace_evidence", "get_event_evidence", "get_change_evidence", "get_topology_context", "get_evidence_by_id")
    return [{"type": "function", "function": {"name": name, "description": "Read-only CDOI incident-evidence query. It cannot mutate any data.", "parameters": {"type": "object", "additionalProperties": True}}} for name in names]


class QwenRCAAgentModel:
    """Stateful serial-function-call adapter implementing ``RCAAgentModel``."""
    def __init__(self, config: QwenRCAConfig, requester: Callable[..., Any] | None = None) -> None:
        self.config = config
        self.requester = requester or (CompanyGatewayTransport().request if config.provider_profile == INTERNAL_QWEN_PROFILE else requests.request)
        self._messages: list[Mapping[str, Any]] = []
        self._last_tool_call_ids: list[str] = []
        self.records: list[Mapping[str, Any]] = []
        self.last_response_metadata: Mapping[str, Any] = {}

    prompt_version = QWEN_RCA_PROMPT_VERSION
    system_prompt = rca_system_prompt()

    def public_metadata(self) -> Mapping[str, Any]:
        return self.config.public_metadata()

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.config.status() != "QWEN_LIVE_READY": raise QwenRCAError("QWEN_PROVIDER_UNCONFIGURED")
        if "prior_tool_results" not in request:
            self._messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": json.dumps({"incident": request.get("incident"), "candidates": request.get("candidates"), "candidate_source": request.get("candidate_source"), "tool_schema_version": request.get("tool_schema_version"), "report_schema": "RCAReport statuses RCA_HYPOTHESIS, INSUFFICIENT_EVIDENCE, TECHNICAL_FAILURE"}, sort_keys=True)}]
        else:
            for index, result in enumerate(request["prior_tool_results"]):
                call_id = self._last_tool_call_ids[index] if index < len(self._last_tool_call_ids) else f"local-tool-{index}"
                self._messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, sort_keys=True)})
        body = {"model": self.config.model, "messages": self._messages, "tools": _tools(), "parallel_tool_calls": False, "temperature": 0, "response_format": {"type": "json_object"}}
        if self.config.enable_thinking is not None: body["enable_thinking"] = self.config.enable_thinking
        response, latency, retries = self._post(body)
        message = self._message(response)
        self._messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            parsed, ids = [], []
            for call in tool_calls:
                function = call.get("function") if isinstance(call, Mapping) else None
                if not isinstance(function, Mapping) or not isinstance(function.get("name"), str): raise QwenRCAError("QWEN_TOOL_CALL_FAILURE")
                try: arguments = json.loads(function.get("arguments", "{}"))
                except (TypeError, json.JSONDecodeError) as exc: raise QwenRCAError("QWEN_TOOL_CALL_FAILURE") from exc
                if not isinstance(arguments, Mapping): raise QwenRCAError("QWEN_TOOL_CALL_FAILURE")
                parsed.append({"name": function["name"], "arguments": dict(arguments)})
                ids.append(str(call.get("id") or f"local-tool-{len(ids)}"))
            self._last_tool_call_ids = ids
            return {"tool_calls": parsed}
        content = message.get("content")
        if not isinstance(content, str): raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE")
        try: report = json.loads(content)
        except json.JSONDecodeError as exc: raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE") from exc
        if not isinstance(report, Mapping): raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE")
        usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
        self.records.append({"latency_ms": latency, "retry_count": retries, "input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"), "tool_call_count": len(self._last_tool_call_ids)})
        return {"report": dict(report)}

    def complete(self, messages: list[Mapping[str, Any]], *, tools: list[Mapping[str, Any]] | None = None,
                 tool_choice: Mapping[str, Any] | str | None = None,
                 response_format: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        """Low-level sanitized completion used only by bounded runtime probes.

        The returned assistant message intentionally contains only OpenAI
        continuation fields.  Provider reasoning fields are discarded before
        any caller can serialize the result.
        """
        if self.config.status() != "QWEN_LIVE_READY":
            raise QwenRCAError("QWEN_PROVIDER_UNCONFIGURED")
        body: dict[str, Any] = {"model": self.config.model, "messages": [dict(item) for item in messages], "temperature": 0}
        if tools is not None:
            body.update({"tools": tools, "parallel_tool_calls": False})
        if tool_choice is not None: body["tool_choice"] = tool_choice
        if response_format is not None: body["response_format"] = dict(response_format)
        if self.config.enable_thinking is not None: body["enable_thinking"] = self.config.enable_thinking
        response, latency, retries = self._post(body)
        message = self._message(response)
        usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
        return {"message": message, "latency_ms": latency, "retry_count": retries,
                "usage": {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens")},
                "response_metadata": dict(self.last_response_metadata)}

    def _post(self, payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], float, int]:
        headers = {"Authorization": f"Bearer {self.config.api_key()}", "Content-Type": "application/json", **self.config.headers()}
        url = self.config.base_url.rstrip("/") + "/chat/completions"  # config is the only endpoint source
        last_error: QwenRCAError | None = None
        for attempt in range(self.config.max_retries + 1):
            started = perf_counter()
            try:
                response = self.requester("POST", url, headers=headers, json=dict(payload), timeout=self.config.timeout_seconds)
                latency = round((perf_counter() - started) * 1000, 3)
                status = getattr(response, "status_code", None)
                if status == 401 or status == 403: raise QwenRCAError("QWEN_AUTH_FAILURE")
                if status == 404: raise QwenRCAError("QWEN_MODEL_UNAVAILABLE")
                if status == 429: raise QwenRCAError("QWEN_TRANSPORT_FAILURE", "RATE_LIMIT")
                if not isinstance(status, int) or not 200 <= status < 300: raise QwenRCAError("QWEN_TRANSPORT_FAILURE")
                try: body = response.json()
                except ValueError as exc: raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE") from exc
                if not isinstance(body, Mapping): raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE")
                self.last_response_metadata = self._response_metadata(body)
                return body, latency, attempt
            except requests.Timeout as exc: last_error = QwenRCAError("QWEN_TRANSPORT_FAILURE", "TIMEOUT")
            except requests.RequestException as exc: last_error = QwenRCAError("QWEN_TRANSPORT_FAILURE", type(exc).__name__)
            except QwenRCAError as exc: last_error = exc
            if attempt < self.config.max_retries and last_error.code == "QWEN_TRANSPORT_FAILURE": sleep(0.05 * (attempt + 1))
            else: break
        raise last_error or QwenRCAError("QWEN_TRANSPORT_FAILURE")

    @staticmethod
    def _message(response: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc: raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE") from exc
        if not isinstance(message, Mapping): raise QwenRCAError("QWEN_OUTPUT_VALIDATION_FAILURE")
        # Never retain or serialize hidden chain-of-thought-style fields.
        safe: dict[str, Any] = {"role": str(message.get("role", "assistant"))}
        if isinstance(message.get("content"), str) or message.get("content") is None:
            safe["content"] = message.get("content")
        if isinstance(message.get("tool_calls"), list):
            safe["tool_calls"] = [dict(item) for item in message["tool_calls"] if isinstance(item, Mapping)]
        return safe

    def _response_metadata(self, response: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"requested_model": self.config.model, "resolved_model": response.get("model") if isinstance(response.get("model"), str) else None,
                "provider": self.config.provider, "system_fingerprint": response.get("system_fingerprint") if isinstance(response.get("system_fingerprint"), str) else None}
