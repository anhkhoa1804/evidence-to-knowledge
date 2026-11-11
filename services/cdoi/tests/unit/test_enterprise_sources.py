import pytest
import requests

from cdoi.enterprise_sources import AcquisitionError, AcquisitionErrorCode, BoundedReadOnlyClient, SourceConfig, response_shape


def _env(**extra):
    result = {"COROOT_BASE_URL": "https://coroot.example", "COROOT_USERNAME": "user", "COROOT_PASSWORD": "secret"}
    result.update(extra)
    return result


def test_config_requires_only_nonempty_https_environment_values():
    with pytest.raises(AcquisitionError, match="SOURCE_UNCONFIGURED"):
        SourceConfig.from_environment("coroot", {"COROOT_BASE_URL": "https://x"})
    assert SourceConfig.from_environment("coroot", _env()).base_url == "https://coroot.example"
    with pytest.raises(AcquisitionError, match="absolute HTTPS"):
        SourceConfig.from_environment("coroot", _env(COROOT_BASE_URL="http://coroot.example"))


def test_safe_audit_never_contains_secret_values():
    audit = SourceConfig.from_environment("coroot", _env()).safe_audit()
    serialized = str(audit)
    assert "secret" not in serialized and "user" not in serialized
    assert all(row["value_logged"] is False for row in audit["variables"])


def test_response_shape_is_structural_only():
    assert response_shape({"b": "secret", "a": 1}) == "object:a,b"
    assert response_shape([{"token": "secret"}]) == "array"


class _TLSFailSession:
    def request(self, *args, **kwargs):
        assert kwargs["verify"] is True
        raise requests.exceptions.SSLError("certificate verify failed")


def test_tls_failure_is_explicit_and_never_bypassed():
    client = BoundedReadOnlyClient(SourceConfig.from_environment("coroot", _env()), session=_TLSFailSession())
    with pytest.raises(AcquisitionError) as captured:
        client.get("/", endpoint_class="root_connectivity")
    assert captured.value.code == AcquisitionErrorCode.SOURCE_CONNECTIVITY_FAILURE


def test_endpoint_must_be_relative_path():
    client = BoundedReadOnlyClient(SourceConfig.from_environment("coroot", _env()), session=_TLSFailSession())
    with pytest.raises(AcquisitionError) as captured:
        client.get("https://other.example", endpoint_class="bad")
    assert captured.value.code == AcquisitionErrorCode.ENDPOINT_NOT_SUPPORTED


def test_insecure_tls_is_explicit_and_host_locked():
    config = SourceConfig.from_environment("coroot", _env(COROOT_TLS_VERIFY="false", COROOT_BASE_URL="https://observability.example.test"))
    assert config.tls_verify is False
    with pytest.raises(AcquisitionError, match="permitted only"):
        SourceConfig.from_environment("coroot", _env(COROOT_TLS_VERIFY="false"))
    assert SourceConfig.from_environment("kibana", {"KIBANA_BASE_URL": "https://logs.example.test", "KIBANA_USERNAME": "u", "KIBANA_PASSWORD": "s", "KIBANA_TLS_VERIFY": "false"}).tls_verify is False
    with pytest.raises(AcquisitionError, match="permitted only"):
        SourceConfig.from_environment("kibana", {"KIBANA_BASE_URL": "https://other.example", "KIBANA_USERNAME": "u", "KIBANA_PASSWORD": "s", "KIBANA_TLS_VERIFY": "false"})
