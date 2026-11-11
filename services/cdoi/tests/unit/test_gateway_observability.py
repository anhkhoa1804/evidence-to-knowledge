from requests import ConnectTimeout, ReadTimeout

from cdoi.gateway_observability import error_phase, safe_response_headers, stable_json_hash


def test_safe_headers_only_retains_documented_correlation_metadata():
    result = safe_response_headers({"X-Request-Id": "r1", "Server-Timing": "app;dur=1", "Authorization": "no", "Set-Cookie": "no", "X-Other": "drop"})
    assert result == {"server-timing": "app;dur=1", "x-request-id": "r1"}


def test_timeout_phase_and_request_hash_are_deterministic():
    assert error_phase(ConnectTimeout()) == "CONNECT_TIMEOUT"
    assert error_phase(ReadTimeout()) == "READ_TIMEOUT"
    assert stable_json_hash({"b": 2, "a": 1}) == stable_json_hash({"a": 1, "b": 2})
