import json
import os
from pathlib import Path

import pytest
import requests

from cdoi.qwen_rca import INTERNAL_QWEN_PROFILE, QWEN_RCA_PROMPT_VERSION, QwenRCAAgentModel, QwenRCAConfig, QwenRCAError
from cdoi.rca_investigation import CandidateSourceMode, InvestigationMode, RCAAgentV0, RCAOrchestrator

GATEWAY_IP = os.environ.get("CDOI_TEST_GATEWAY_IP", "127.0.0.1")
GATEWAY_BASE_URL = f"http://{GATEWAY_IP}/prod/ai-gateway/v1"
GATEWAY_HOST = os.environ.get("CDOI_TEST_GATEWAY_HOST", "gateway.example.test")

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/preprocessing_demo"


class Response:
    def __init__(self, body, status=200): self.body, self.status_code = body, status
    def json(self): return self.body


class ToolThenReportRequester:
    def __init__(self): self.calls = []; self.candidate = None; self.evidence = None
    def __call__(self, method, url, headers, json, timeout):
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        if len(self.calls) == 1:
            payload = json_module_load(json["messages"][1]["content"])
            self.candidate = payload["candidates"]["items"][0]["candidate_id"]
            self.evidence = payload["candidates"]["items"][0]["supporting_evidence_ids"][0]
            return Response({"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "get_evidence_by_id", "arguments": json_module_dump({"evidence_id": self.evidence})}}]}}]})
        report = {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": self.candidate, "statement": "Evidence-backed investigation hypothesis only.", "supporting_evidence_ids": [self.evidence], "limitations": ["NOT_CAUSALLY_PROVEN"], "model_self_assessment": "LOW"}, "alternative_hypotheses": [], "supporting_evidence_ids": [self.evidence], "contradictory_evidence_ids": [], "reasoning_summary": "Cited evidence was inspected.", "limitations": ["NOT_CALIBRATED"], "abstention_reason": None}
        return Response({"choices": [{"message": {"role": "assistant", "content": json_module_dump(report)}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}})


def json_module_load(value): return json.loads(value)
def json_module_dump(value): return json.dumps(value, sort_keys=True)


def _config(monkeypatch, **changes):
    monkeypatch.setenv("QWEN_API_KEY", "test-key-not-persisted")
    values = {"base_url": "https://example.invalid/compatible-mode/v1", "model": "qwen3.8-max-0902", "api_key_env": "QWEN_API_KEY", "region": "test-region", "enable_thinking": False, "timeout_seconds": 3, "max_retries": 1}
    values.update(changes)
    return QwenRCAConfig(**values)


def _prepared(tmp_path): return RCAOrchestrator().prepare(FIXTURE / "manifest.yaml", "inc-001", tmp_path / "store.sqlite")


def test_unconfigured_status_and_public_metadata_do_not_expose_secret(monkeypatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False); monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    config = QwenRCAConfig(base_url=None)
    assert config.status() == "QWEN_PROVIDER_UNCONFIGURED"
    assert "test-key" not in json_module_dump(config.public_metadata())


def test_qwen_adapter_serial_tool_continuation_and_validated_report(monkeypatch, tmp_path):
    requester = ToolThenReportRequester(); model = QwenRCAAgentModel(_config(monkeypatch), requester=requester)
    prepared = _prepared(tmp_path)
    report = RCAOrchestrator().run(prepared, tmp_path / "run", InvestigationMode.AGENT, CandidateSourceMode.H1_THEN_H5_FALLBACK, RCAAgentV0(model, max_tool_calls=12, max_candidate_profiles=6), model.public_metadata())
    assert report.status == "RCA_HYPOTHESIS"
    assert len(requester.calls) == 2
    assert requester.calls[0]["json"]["enable_thinking"] is False
    assert requester.calls[0]["json"]["parallel_tool_calls"] is False
    assert (tmp_path / "run" / "RUN_MANIFEST.json").read_text(encoding="utf-8").find(QWEN_RCA_PROMPT_VERSION) >= 0
    trace = json.loads((tmp_path / "run" / "AGENT_TRACE.json").read_text(encoding="utf-8"))
    assert trace["tool_calls"][0]["tool_name"] == "get_evidence_by_id"
    assert "test-key" not in (tmp_path / "run" / "RUN_MANIFEST.json").read_text(encoding="utf-8")
    prepared.store.close()


def test_provider_timeout_retries_then_fails_closed(monkeypatch):
    attempts = []
    def timeout(*args, **kwargs): attempts.append(1); raise requests.Timeout()
    model = QwenRCAAgentModel(_config(monkeypatch, max_retries=1), requester=timeout)
    with pytest.raises(QwenRCAError, match="QWEN_TRANSPORT_FAILURE"):
        model.generate({"incident": {}, "candidates": {}, "candidate_source": "H1_SHORTLIST"})
    assert len(attempts) == 2


def test_simple_qwen_smoke_response_is_parsed_as_structured_report(monkeypatch):
    report = {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None, "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [], "reasoning_summary": "No sufficient evidence.", "limitations": ["MISSING_MODALITY"], "abstention_reason": "INSUFFICIENT_EVIDENCE"}
    model = QwenRCAAgentModel(_config(monkeypatch), requester=lambda *args, **kwargs: Response({"choices": [{"message": {"role": "assistant", "content": json_module_dump(report)}}]}))
    assert model.generate({"incident": {"incident_id": "smoke"}, "candidates": {"items": []}, "candidate_source": "H1_SHORTLIST"})["report"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_qwen_tool_arguments_fail_closed(monkeypatch):
    def invalid(*args, **kwargs):
        return Response({"choices": [{"message": {"role": "assistant", "tool_calls": [{"id": "x", "function": {"name": "get_candidates", "arguments": "not json"}}]}}]})
    model = QwenRCAAgentModel(_config(monkeypatch), requester=invalid)
    with pytest.raises(QwenRCAError, match="QWEN_TOOL_CALL_FAILURE"):
        model.generate({"incident": {}, "candidates": {}, "candidate_source": "H1_SHORTLIST"})


def test_internal_gateway_profile_is_explicit_and_secret_free(monkeypatch):
    monkeypatch.setenv("CDOI_QWEN_PROVIDER_PROFILE", INTERNAL_QWEN_PROFILE)
    monkeypatch.setenv("CDOI_QWEN_BASE_URL", GATEWAY_BASE_URL)
    monkeypatch.setenv("CDOI_QWEN_HOST_HEADER", GATEWAY_HOST)
    monkeypatch.setenv("CDOI_QWEN_API_KEY_ENV", "DMP_MERCURY")
    monkeypatch.setenv("DMP_MERCURY", "private-internal-test-token")
    config = QwenRCAConfig.from_internal_gateway_environment()
    metadata = json_module_dump(config.public_metadata())
    assert config.provider_profile == INTERNAL_QWEN_PROFILE
    assert config.host_header == GATEWAY_HOST
    assert config.enable_thinking is None
    assert "private-internal-test-token" not in metadata
    assert GATEWAY_IP not in metadata


def test_internal_gateway_rejects_credential_value_misconfigured_as_env_name(monkeypatch):
    monkeypatch.setenv("CDOI_QWEN_PROVIDER_PROFILE", INTERNAL_QWEN_PROFILE)
    monkeypatch.setenv("CDOI_LLM_API_KEY_ENV", "sk_MisconfiguredCredentialLikeValue")
    config = QwenRCAConfig.from_internal_gateway_environment()
    assert config.api_key_env == "DMP_MERCURY"
    assert "sk_MisconfiguredCredentialLikeValue" not in json_module_dump(config.public_metadata())


def test_internal_gateway_host_reasoning_redaction_and_resolved_model(monkeypatch):
    monkeypatch.setenv("DMP_MERCURY", "private-internal-test-token")
    config = QwenRCAConfig(provider="vllm", provider_profile=INTERNAL_QWEN_PROFILE,
                           model="vllm/Qwen3.8-27B", base_url=GATEWAY_BASE_URL,
                           host_header=GATEWAY_HOST, api_key_env="DMP_MERCURY", enable_thinking=None)
    calls = []
    def requester(*args, **kwargs):
        calls.append(kwargs)
        return Response({"model": "Qwen3.8-27B", "system_fingerprint": "safe-fingerprint", "choices": [{"message": {"role": "assistant", "content": "OK", "reasoning": "hidden", "reasoning_details": ["hidden"]}}]})
    model = QwenRCAAgentModel(config, requester=requester)
    result = model.complete([{"role": "user", "content": "Say OK"}])
    assert calls[0]["headers"]["Host"] == GATEWAY_HOST
    assert calls[0]["json"].get("enable_thinking") is None
    assert result["message"] == {"role": "assistant", "content": "OK"}
    assert result["response_metadata"]["resolved_model"] == "Qwen3.8-27B"
    assert "hidden" not in json_module_dump(result)
    assert "private-internal-test-token" not in json_module_dump(result)
