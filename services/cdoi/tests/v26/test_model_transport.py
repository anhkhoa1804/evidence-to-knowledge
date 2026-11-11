import json
import os
from pathlib import Path

import pytest

from cdoi.company_gateway import CompanyGatewayTransport
from cdoi.conceptualization import OpenAICompatibleLLM
from cdoi.llm_evaluation import LLMAlignmentResponse
from cdoi.model_config import dotenv_state, load_dotenv_file
from cdoi.model_config import OpenAICompatibleConfig
from cdoi.model_probe import probe_gateway

GATEWAY_IP = os.environ.get("CDOI_TEST_GATEWAY_IP", "127.0.0.1")
GATEWAY_BASE_URL = f"http://{GATEWAY_IP}/prod/ai-gateway/v1"
GATEWAY_HOST = os.environ.get("CDOI_TEST_GATEWAY_HOST", "gateway.example.test")


class Response:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.status_code = status

    def json(self):
        return self.body

    def read(self):
        return json.dumps(self.body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class RecordingSession:
    def __init__(self, response):
        self.trust_env = True
        self.response = response
        self.calls = []

    def request(self, method, url, *, headers, json, timeout):
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json, "timeout": timeout})
        return self.response


def _message(content, **extra):
    return {"choices": [{"message": {"content": content, **extra}}]}


def test_probe_skips_without_credential(monkeypatch):
    monkeypatch.delenv("DMP_MERCURY", raising=False)
    config = OpenAICompatibleConfig("vllm", "vllm/Qwen3.8-27B", "http://unused", "DMP_MERCURY", "gateway.internal")
    report = probe_gateway(config)
    assert report.failure_category == "missing_credential"
    assert report.gateway_reachable is None
    assert report.basic_chat is None


def test_dotenv_loader_keeps_existing_process_values(monkeypatch, tmp_path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("DMP_MERCURY=dotenv-token\nCDOI_LLM_MODEL=dotenv-model\n", encoding="utf-8")
    monkeypatch.setenv("DMP_MERCURY", "process-token")
    before = dotenv_state("DMP_MERCURY", dotenv)
    load_dotenv_file(dotenv, override=False)
    assert before.process_present and before.dotenv_present and before.values_equal is False
    assert os.environ["DMP_MERCURY"] == "process-token"


def test_env_files_are_ignored_and_public_metadata_never_contains_token(monkeypatch):
    monkeypatch.setenv("DMP_MERCURY", "private-test-token")
    ignored = (Path(__file__).resolve().parents[2] / ".gitignore").read_text(encoding="utf-8")
    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    config = OpenAICompatibleConfig("openai-compatible", "vllm/Qwen3.8-27B", "http://gateway", "DMP_MERCURY", GATEWAY_HOST)
    assert ".env" in ignored and ".env.local" in ignored
    assert "DMP_MERCURY=" in example and "private-test-token" not in example
    assert "private-test-token" not in json.dumps(config.public_metadata())


def test_probe_stages_basic_json_response_format_and_schema(monkeypatch):
    monkeypatch.setenv("DMP_MERCURY", "test-token")
    requests = []

    def requester(method, url, headers, json, timeout):
        requests.append({"method": method, "url": url, "headers": headers, "json": json})
        if url.endswith("/models"):
            return Response({"data": [{"id": "vllm/Qwen3.8-27B"}]})
        payload = json
        content = payload["messages"][0]["content"]
        if content == "Reply with exactly OK":
            return Response(_message("OK", reasoning_content="ignored"))
        if "self_reported_confidence" in content:
            return Response(_message('{"status":"MATCHED","semantic_relation":"EQUIVALENT","target_id":"probe:target","evidence":["probe"],"self_reported_confidence":1.0}', reasoning_content="ignored"))
        return Response(_message('{"status":"ok"}'))

    config = OpenAICompatibleConfig("vllm", "vllm/Qwen3.8-27B", "http://gateway", "DMP_MERCURY", "llm-gw.internal")
    report = probe_gateway(config, requester)
    assert report.gateway_reachable and report.model_accepted
    assert report.basic_chat and report.json_by_prompt and report.response_format_json_object and report.semantic_schema_validation
    assert requests[1]["headers"]["Host"] == "llm-gw.internal"
    basic = requests[1]["json"]
    assert basic == {"model": "vllm/Qwen3.8-27B", "messages": [{"role": "user", "content": "Reply with exactly OK"}], "temperature": 0, "max_tokens": 16}
    assert report.diagnostics[1]["request_field_names"] == ["max_tokens", "messages", "model", "temperature"]
    assert report.diagnostics[-1]["message_field_names"] == ["content", "reasoning_content"]


def test_probe_stops_on_basic_403_as_execution_context_mismatch(monkeypatch):
    monkeypatch.setenv("DMP_MERCURY", "test-token")
    requests = []

    def requester(method, url, headers, json, timeout):
        requests.append({"method": method, "url": url, "headers": headers, "json": json})
        return Response({"error": {"message": "not exposed"}}, status=200 if url.endswith("/models") else 403)

    config = OpenAICompatibleConfig("vllm", "vllm/Qwen3.8-27B", "http://gateway", "DMP_MERCURY", "llm-gw.internal")
    report = probe_gateway(config, requester)
    assert report.failure_category == "EXECUTION_CONTEXT_MISMATCH"
    assert report.basic_chat is False
    assert report.json_by_prompt is None
    assert len(requests) == 2
    assert report.execution_context["request_field_names"] == ["max_tokens", "messages", "model", "temperature"]


def test_company_gateway_transport_ignores_proxy_environment_and_preserves_request(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://proxy.invalid:8800")
    session = RecordingSession(Response(_message("OK")))
    transport = CompanyGatewayTransport(session)
    response = transport.request(
        "POST",
        f"{GATEWAY_BASE_URL}/chat/completions",
        headers={"Host": GATEWAY_HOST, "Authorization": "Bearer test-token"},
        json={"model": "vllm/Qwen3.8-27B"},
        timeout=15,
    )
    assert response.status_code == 200
    assert session.trust_env is False
    assert session.calls[0]["headers"]["Host"] == GATEWAY_HOST


def test_openai_compatible_client_uses_private_transport_without_logging_bearer():
    session = RecordingSession(Response({"choices": [{"message": {"content": '{"status":"MATCHED","semantic_relation":"EQUIVALENT","target_id":"x"}'}}], "usage": {"prompt_tokens": 4, "completion_tokens": 2}}))
    client = OpenAICompatibleLLM("http://gateway", "secret-token", "vllm/Qwen3.8-27B", {"Host": GATEWAY_HOST}, transport=CompanyGatewayTransport(session))
    response = client.structured_generate("prompt", LLMAlignmentResponse)
    assert response.relation == "EQUIVALENT"
    assert session.trust_env is False
    assert session.calls[0]["headers"]["Host"] == GATEWAY_HOST
    assert session.calls[0]["headers"]["Authorization"] == "Bearer secret-token"
    assert "secret-token" not in client.cache_identity()
    assert client.last_usage == {"prompt_tokens": 4, "completion_tokens": 2}


def test_basic_probe_uses_virtual_host_has_secret_free_diagnostics_and_minimal_payload(monkeypatch):
    monkeypatch.setenv("DMP_MERCURY", "test-token")
    requests = []

    def requester(method, url, headers, json, timeout):
        requests.append({"method": method, "url": url, "headers": headers, "json": json})
        return Response({"data": []} if url.endswith("/models") else _message("OK"))

    config = OpenAICompatibleConfig("vllm", "vllm/Qwen3.8-27B", GATEWAY_BASE_URL, "DMP_MERCURY", GATEWAY_HOST)
    report = probe_gateway(config, requester, basic_only=True)
    basic = requests[0]
    assert report.basic_chat is True
    assert len(requests) == 1
    assert basic["headers"]["Host"] == GATEWAY_HOST
    assert basic["headers"]["Authorization"] == "Bearer test-token"
    assert set(basic["json"]) == {"model", "messages", "temperature", "max_tokens"}
    assert "test-token" not in json.dumps(report.as_dict())
    assert report.diagnostics[0]["effective_host"] == GATEWAY_HOST


def test_closed_set_llm_schema_rejects_unknown_relation():
    with pytest.raises(ValueError):
        LLMAlignmentResponse.model_validate({"status": "MATCHED", "semantic_relation": "MERGE_EVERYTHING"})
