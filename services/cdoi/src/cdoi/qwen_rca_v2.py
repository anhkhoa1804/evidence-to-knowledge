"""V2 Qwen adapter with explicit output budget and safe transport telemetry."""
from __future__ import annotations

import json
from time import perf_counter, sleep
from typing import Any, Callable, Mapping

import requests

from .qwen_rca import QwenRCAAgentModel, QwenRCAConfig, QwenRCAError, _tools
from .provider_output import ProviderOutputError, normalize_openai_turn
from .rca_agent_v2 import RCA_AGENT_V2_PROMPT_VERSION, RCA_AGENT_V2_TOOL_SCHEMA_VERSION

QWEN_RCA_V2_ADAPTER_VERSION = "qwen_rca_openai_compatible_v2"


def rca_v2_system_prompt() -> str:
    return "\n".join((
        "You are investigating evidence-backed hypotheses, not proving causality.",
        "Candidate != Cause. Metric shift != Cause. ERROR span != Cause. Trace path and temporal order are not causal proof.",
        "The complete H1 CandidateEvidenceProfile set is preloaded. Compare every one before INSUFFICIENT_EVIDENCE.",
        "For INSUFFICIENT_EVIDENCE return investigated_candidate_ids, comparison_completed=true, abstention_reason, and missing_or_conflicting_evidence.",
        "Use only supplied read-only tools and cite only supplied evidence IDs. Do not invent evidence.",
        "H5 expansion is optional and only permitted after H1 comparison with a bounded fallback reason.",
        "Return one JSON object. RCA_HYPOTHESIS requires primary_hypothesis.",
    ))


class QwenRCAAgentV2Model(QwenRCAAgentModel):
    """Separate V2 adapter; V1 request formatting and defaults remain unchanged."""
    prompt_version = RCA_AGENT_V2_PROMPT_VERSION
    system_prompt = rca_v2_system_prompt()

    def __init__(self, config: QwenRCAConfig, requester: Callable[..., Any] | None = None,
                 *, max_output_tokens: int = 512) -> None:
        if max_output_tokens < 1:
            raise ValueError("INVALID_V2_OUTPUT_TOKEN_BUDGET")
        super().__init__(config, requester=requester)
        self.max_output_tokens = max_output_tokens
        self.last_transport_diagnostic: Mapping[str, Any] = {"status": "NOT_CALLED", "attempt_count": 0}
        self.last_contract_diagnostic: Mapping[str, Any] = {"validation_stage_reached": "NOT_CALLED"}
        self.transport_history: list[Mapping[str, Any]] = []

    def public_metadata(self) -> Mapping[str, Any]:
        return {**super().public_metadata(), "adapter_version": QWEN_RCA_V2_ADAPTER_VERSION,
                "prompt_version": self.prompt_version, "temperature": 0,
                "max_output_tokens": self.max_output_tokens}

    def _body(self) -> dict[str, Any]:
        body: dict[str, Any] = {"model": self.config.model, "messages": self._messages, "tools": _tools(),
                                "parallel_tool_calls": False, "temperature": 0,
                                "max_tokens": self.max_output_tokens,
                                "response_format": {"type": "json_object"}}
        if self.config.enable_thinking is not None:
            body["enable_thinking"] = self.config.enable_thinking
        return body

    def generate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if self.config.status() != "QWEN_LIVE_READY":
            raise QwenRCAError("QWEN_PROVIDER_UNCONFIGURED")
        if "prior_tool_results" not in request:
            payload = {"incident": request.get("incident"), "candidates": request.get("candidates"),
                       "preloaded_candidate_profiles": request.get("preloaded_candidate_profiles"),
                       "h1_comparison": request.get("h1_comparison"), "candidate_source": request.get("candidate_source"),
                       "tool_schema_version": RCA_AGENT_V2_TOOL_SCHEMA_VERSION,
                       "report_schema": request.get("report_schema", "RCAReport plus V2 abstention fields")}
            self._messages = [{"role": "system", "content": self.system_prompt},
                              {"role": "user", "content": json.dumps(payload, sort_keys=True)}]
        else:
            for index, result in enumerate(request["prior_tool_results"]):
                call_id = self._last_tool_call_ids[index] if index < len(self._last_tool_call_ids) else f"local-tool-{index}"
                self._messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result, sort_keys=True)})
        response, latency, retries = self._post(self._body())
        message = self._message(response); self._messages.append(message)
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            parsed, ids = [], []
            for call in tool_calls:
                function = call.get("function") if isinstance(call, Mapping) else None
                if not isinstance(function, Mapping) or not isinstance(function.get("name"), str):
                    raise QwenRCAError("QWEN_TOOL_CALL_PARSE_FAILURE")
                try: arguments = json.loads(function.get("arguments", "{}"))
                except (TypeError, json.JSONDecodeError) as exc: raise QwenRCAError("QWEN_TOOL_CALL_PARSE_FAILURE") from exc
                if not isinstance(arguments, Mapping): raise QwenRCAError("QWEN_TOOL_CALL_PARSE_FAILURE")
                parsed.append({"name": function["name"], "arguments": dict(arguments)})
                ids.append(str(call.get("id") or f"local-tool-{len(ids)}"))
            self._last_tool_call_ids = ids
            return {"tool_calls": parsed}
        content = message.get("content")
        if not isinstance(content, str):
            self.last_contract_diagnostic = {**self.last_contract_diagnostic, "validation_stage_reached": "JSON_PARSE", "validation_error_code": "QWEN_CONTENT_NORMALIZATION_FAILURE", "validation_error_path": "choices[0].message.content", "repair_eligible": False}
            raise QwenRCAError("QWEN_CONTENT_NORMALIZATION_FAILURE")
        try: report = json.loads(content)
        except json.JSONDecodeError as exc:
            self.last_contract_diagnostic = {**self.last_contract_diagnostic, "validation_stage_reached": "JSON_PARSE", "validation_error_code": "QWEN_JSON_PARSE_FAILURE", "validation_error_path": "choices[0].message.content", "repair_eligible": False}
            raise QwenRCAError("QWEN_JSON_PARSE_FAILURE") from exc
        if not isinstance(report, Mapping):
            self.last_contract_diagnostic = {**self.last_contract_diagnostic, "validation_stage_reached": "RCA_SCHEMA", "validation_error_code": "QWEN_RCA_SCHEMA_FAILURE", "validation_error_path": "choices[0].message.content", "repair_eligible": False}
            raise QwenRCAError("QWEN_RCA_SCHEMA_FAILURE")
        self.last_contract_diagnostic = {**self.last_contract_diagnostic, "validation_stage_reached": "RCA_SCHEMA_INPUT", "validation_error_code": None, "validation_error_path": None, "repair_eligible": True}
        usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
        self.records.append({"latency_ms": latency, "retry_count": retries, "input_tokens": usage.get("prompt_tokens"),
                             "output_tokens": usage.get("completion_tokens"), "tool_call_count": len(self._last_tool_call_ids),
                             "finish_reason": self._finish_reason(response)})
        return {"report": dict(report)}

    def repair_output(self, raw_output: Mapping[str, Any], error_code: str,
                      request: Mapping[str, Any]) -> Mapping[str, Any]:
        # Raw output is sent only in-memory to the provider for the single bounded
        # repair request; it is deliberately not retained in artifacts or traces.
        prompt = {"task": "Repair this JSON report only. Do not add evidence or change facts.",
                  "validation_error": error_code, "invalid_report": dict(raw_output),
                  "required_schema": request.get("report_schema")}
        result = self.complete([{"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": json.dumps(prompt, sort_keys=True)}],
                               response_format={"type": "json_object"})
        content = result["message"].get("content")
        if not isinstance(content, str): raise QwenRCAError("QWEN_CONTENT_NORMALIZATION_FAILURE")
        try: repaired = json.loads(content)
        except json.JSONDecodeError as exc: raise QwenRCAError("QWEN_JSON_PARSE_FAILURE") from exc
        if not isinstance(repaired, Mapping): raise QwenRCAError("QWEN_RCA_SCHEMA_FAILURE")
        return {"report": dict(repaired)}

    def complete(self, messages: list[Mapping[str, Any]], *, tools: list[Mapping[str, Any]] | None = None,
                 tool_choice: Mapping[str, Any] | str | None = None,
                 response_format: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        if self.config.status() != "QWEN_LIVE_READY": raise QwenRCAError("QWEN_PROVIDER_UNCONFIGURED")
        body: dict[str, Any] = {"model": self.config.model, "messages": [dict(item) for item in messages],
                                "temperature": 0, "max_tokens": self.max_output_tokens}
        if tools is not None: body.update({"tools": tools, "parallel_tool_calls": False})
        if tool_choice is not None: body["tool_choice"] = tool_choice
        if response_format is not None: body["response_format"] = dict(response_format)
        if self.config.enable_thinking is not None: body["enable_thinking"] = self.config.enable_thinking
        response, latency, retries = self._post(body); message = self._message(response)
        usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
        return {"message": message, "latency_ms": latency, "retry_count": retries,
                "usage": {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens")},
                "response_metadata": dict(self.last_response_metadata)}

    @staticmethod
    def _finish_reason(response: Mapping[str, Any]) -> str | None:
        try:
            value = response["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError):
            return None
        return value if isinstance(value, str) else None

    def _message(self, response: Mapping[str, Any]) -> Mapping[str, Any]:
        """Normalize only provider-envelope quirks before RCA semantics run."""
        try:
            turn = normalize_openai_turn(response, self.config.model)
        except ProviderOutputError as exc:
            choice = (response.get("choices") or [{}])[0]
            message = choice.get("message") if isinstance(choice, Mapping) else None
            self.last_contract_diagnostic = {"validation_stage_reached": "PROVIDER_NORMALIZATION", "validation_error_code": exc.code, "validation_error_path": exc.path, "repair_eligible": False,
                                             "finish_reason": choice.get("finish_reason") if isinstance(choice, Mapping) else None,
                                             "message_present": isinstance(message, Mapping),
                                             "message_content_present": message.get("content") is not None if isinstance(message, Mapping) else False,
                                             "message_content_type": type(message.get("content")).__name__ if isinstance(message, Mapping) and message.get("content") is not None else None,
                                             "tool_call_count": len(message.get("tool_calls") or []) if isinstance(message, Mapping) and isinstance(message.get("tool_calls") or [], list) else None,
                                             "requested_model": self.config.model, "resolved_model": response.get("model") if isinstance(response.get("model"), str) else None}
            raise QwenRCAError(exc.code) from exc
        self.last_contract_diagnostic = {**turn.safe_metadata(), "validation_stage_reached": "CONTENT_NORMALIZED", "validation_error_code": None, "validation_error_path": None, "repair_eligible": turn.content is not None and not turn.tool_calls}
        message: dict[str, Any] = {"role": "assistant", "content": turn.content}
        if turn.tool_calls:
            message["tool_calls"] = list(turn.tool_calls)
        return message

    def _post(self, payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], float, int]:
        headers = {"Authorization": f"Bearer {self.config.api_key()}", "Content-Type": "application/json", **self.config.headers()}
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        last_error: QwenRCAError | None = None; observations: list[Mapping[str, Any]] = []
        for attempt in range(self.config.max_retries + 1):
            started = perf_counter()
            try:
                response = self.requester("POST", url, headers=headers, json=dict(payload), timeout=self.config.timeout_seconds)
                elapsed = round((perf_counter() - started) * 1000, 3); status = getattr(response, "status_code", None)
                observations.append({"attempt": attempt + 1, "elapsed_ms": elapsed, "http_status": status if isinstance(status, int) else None})
                if status in {401, 403}: raise QwenRCAError("QWEN_AUTH_FAILURE")
                if status == 404: raise QwenRCAError("QWEN_MODEL_UNAVAILABLE")
                if status == 429: raise QwenRCAError("QWEN_TRANSPORT_FAILURE", "RATE_LIMIT")
                if not isinstance(status, int) or not 200 <= status < 300: raise QwenRCAError("QWEN_TRANSPORT_FAILURE")
                try: body = response.json()
                except ValueError as exc: raise QwenRCAError("QWEN_PROVIDER_ENVELOPE_FAILURE") from exc
                if not isinstance(body, Mapping): raise QwenRCAError("QWEN_PROVIDER_ENVELOPE_FAILURE")
                self.last_response_metadata = self._response_metadata(body)
                self.last_transport_diagnostic = {"status": "SUCCESS", "attempt_count": attempt + 1,
                                                  "retry_count": attempt, "attempts": observations}
                self.transport_history.append(dict(self.last_transport_diagnostic))
                return body, elapsed, attempt
            except requests.Timeout:
                last_error = QwenRCAError("QWEN_TRANSPORT_FAILURE", "TIMEOUT")
            except requests.RequestException as exc:
                last_error = QwenRCAError("QWEN_TRANSPORT_FAILURE", type(exc).__name__)
            except QwenRCAError as exc:
                last_error = exc
            observations.append({"attempt": attempt + 1, "failure_code": last_error.code,
                                 "failure_detail": last_error.detail or None})
            if attempt < self.config.max_retries and last_error.code == "QWEN_TRANSPORT_FAILURE": sleep(0.05 * (attempt + 1))
            else: break
        attempt_count = max((int(item.get("attempt", 0)) for item in observations), default=0)
        self.last_transport_diagnostic = {"status": "FAILURE", "attempt_count": attempt_count,
                                          "retry_count": max(0, attempt_count - 1),
                                          "failure_code": last_error.code if last_error else "QWEN_TRANSPORT_FAILURE",
                                          "failure_detail": last_error.detail if last_error else None,
                                          "attempts": observations}
        self.transport_history.append(dict(self.last_transport_diagnostic))
        raise last_error or QwenRCAError("QWEN_TRANSPORT_FAILURE")
