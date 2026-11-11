"""Bounded, read-only source primitives for CDOI V4-A.

This module deliberately knows no vendor endpoint shapes.  Endpoint selection is
an explicit, post-discovery responsibility; these primitives only enforce the
invariants around configuration, TLS, request bounds, and safe audit metadata.
"""
from __future__ import annotations

import os
import time
import warnings
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping
from urllib.parse import urlparse

import requests


class AcquisitionErrorCode(StrEnum):
    SOURCE_UNCONFIGURED = "SOURCE_UNCONFIGURED"
    SOURCE_CONNECTIVITY_FAILURE = "SOURCE_CONNECTIVITY_FAILURE"
    SOURCE_AUTH_FAILURE = "SOURCE_AUTH_FAILURE"
    PROJECT_NOT_VISIBLE = "PROJECT_NOT_VISIBLE"
    DATA_VIEW_NOT_FOUND = "DATA_VIEW_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    ENDPOINT_NOT_SUPPORTED = "ENDPOINT_NOT_SUPPORTED"
    SOURCE_EMPTY = "SOURCE_EMPTY"
    SOURCE_PARTIAL = "SOURCE_PARTIAL"
    PAGINATION_INCOMPLETE = "PAGINATION_INCOMPLETE"
    TIME_RANGE_UNAVAILABLE = "TIME_RANGE_UNAVAILABLE"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
    SOURCE_TRUNCATED = "SOURCE_TRUNCATED"
    REDACTION_FAILURE = "REDACTION_FAILURE"
    LINEAGE_INCOMPLETE = "LINEAGE_INCOMPLETE"


class AcquisitionError(RuntimeError):
    def __init__(self, code: AcquisitionErrorCode, detail: str) -> None:
        super().__init__(f"{code}:{detail}")
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class SourceConfig:
    source: str
    base_url: str
    username: str
    password: str
    data_view_id: str | None = None
    tls_verify: bool = True

    @classmethod
    def from_environment(cls, source: str, environment: Mapping[str, str] | None = None) -> "SourceConfig":
        env = os.environ if environment is None else environment
        prefix = source.upper()
        required = (f"{prefix}_BASE_URL", f"{prefix}_USERNAME", f"{prefix}_PASSWORD")
        missing = [name for name in required if not str(env.get(name, "")).strip()]
        if missing:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_UNCONFIGURED, f"missing required variables: {', '.join(missing)}")
        base_url = str(env[f"{prefix}_BASE_URL"]).rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_UNCONFIGURED, "base URL must be an absolute HTTPS URL")
        raw_verify = str(env.get(f"{prefix}_TLS_VERIFY", "true")).strip().casefold()
        if raw_verify not in {"true", "false"}:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_UNCONFIGURED, f"{prefix}_TLS_VERIFY must be true or false")
        tls_verify = raw_verify == "true"
        # This is intentionally a configuration boundary, not a general bypass.
        allowed_insecure_hosts = {"coroot": env.get("COROOT_STAGING_HOST", "observability.example.test"),
                                  "kibana": env.get("KIBANA_STAGING_HOST", "logs.example.test")}
        if not tls_verify and allowed_insecure_hosts.get(source.casefold()) != parsed.hostname:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_UNCONFIGURED, "insecure TLS is permitted only for the explicitly authorized staging source hostname")
        return cls(source=source.lower(), base_url=base_url, username=str(env[f"{prefix}_USERNAME"]),
                   password=str(env[f"{prefix}_PASSWORD"]), data_view_id=env.get(f"{prefix}_DATA_VIEW_ID"), tls_verify=tls_verify)

    def safe_audit(self, *, source_type: str = "env") -> Mapping[str, Any]:
        names = [f"{self.source.upper()}_BASE_URL", f"{self.source.upper()}_USERNAME", f"{self.source.upper()}_PASSWORD"]
        if self.data_view_id is not None:
            names.append(f"{self.source.upper()}_DATA_VIEW_ID")
        return {"source": self.source, "tls_verification_enabled": self.tls_verify, "variables": [
            {"variable_name": name, "configured": True, "source_type": source_type, "value_logged": False} for name in names
        ]}


def response_shape(payload: Any) -> str:
    if isinstance(payload, Mapping): return "object:" + ",".join(sorted(str(key) for key in payload)[:20])
    if isinstance(payload, list): return "array"
    if payload is None: return "null"
    return type(payload).__name__


class BoundedReadOnlyClient:
    """One-request-at-a-time HTTPS client that never serializes auth material."""
    def __init__(self, config: SourceConfig, *, timeout_seconds: float = 15.0, session: requests.Session | None = None) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.config, self.timeout_seconds = config, timeout_seconds
        self.session = session or requests.Session()
        # Staging addresses resolve to their intended private hostnames. Do not
        # send their session credentials through an ambient proxy configuration.
        if session is None:
            self.session.trust_env = False

    def request_json(self, method: str, endpoint: str, *, endpoint_class: str, params: Mapping[str, str | int] | None = None,
                     json_body: Mapping[str, Any] | None = None, use_basic_auth: bool = True) -> tuple[Mapping[str, Any], Any | None]:
        """Make exactly one bounded request; callers must never serialize its payload blindly."""
        if method not in {"GET", "POST"}:
            raise AcquisitionError(AcquisitionErrorCode.ENDPOINT_NOT_SUPPORTED, "only GET and POST are permitted")
        if not endpoint.startswith("/") or endpoint.startswith("//"):
            raise AcquisitionError(AcquisitionErrorCode.ENDPOINT_NOT_SUPPORTED, "endpoint must be a relative absolute-path")
        started = time.monotonic()
        try:
            with warnings.catch_warnings():
                if not self.config.tls_verify:
                    warnings.simplefilter("ignore", requests.packages.urllib3.exceptions.InsecureRequestWarning)
                response = self.session.request(method, self.config.base_url + endpoint, params=params, json=json_body,
                                                auth=(self.config.username, self.config.password) if use_basic_auth else None,
                                                timeout=self.timeout_seconds, verify=self.config.tls_verify, allow_redirects=False)
        except requests.exceptions.SSLError as exc:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_CONNECTIVITY_FAILURE, "TLS certificate verification failed") from exc
        except requests.exceptions.Timeout as exc:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_CONNECTIVITY_FAILURE, "request timed out") from exc
        except requests.RequestException as exc:
            raise AcquisitionError(AcquisitionErrorCode.SOURCE_CONNECTIVITY_FAILURE, "request could not be completed") from exc
        elapsed_ms = round((time.monotonic() - started) * 1000, 1)
        record: dict[str, Any] = {"endpoint_class": endpoint_class, "method": method, "status": response.status_code,
                                  "elapsed_ms": elapsed_ms, "pagination": "NOT_APPLICABLE", "truncated": False, "errors": []}
        if not self.config.tls_verify:
            record["transport_tls_verified"] = False
            record["transport_exception"] = "STAGING_INSECURE_TLS_EXPLICIT"
            record["warning"] = "TLS certificate verification is disabled for Coroot staging only. Transport authenticity has not been cryptographically verified."
        if response.status_code in (401, 403):
            record["errors"] = [AcquisitionErrorCode.SOURCE_AUTH_FAILURE if response.status_code == 401 else AcquisitionErrorCode.PERMISSION_DENIED]
            return record, None
        if response.status_code == 404:
            record["errors"] = [AcquisitionErrorCode.ENDPOINT_NOT_SUPPORTED]
            return record, None
        try:
            payload = response.json()
            record.update({"response_shape": response_shape(payload), "record_count": len(payload) if isinstance(payload, list) else (len(payload) if isinstance(payload, Mapping) else 1)})
        except ValueError:
            payload = None; record.update({"response_shape": "non_json", "record_count": None})
        return record, payload

    def get(self, endpoint: str, *, endpoint_class: str, params: Mapping[str, str | int] | None = None) -> Mapping[str, Any]:
        return self.request_json("GET", endpoint, endpoint_class=endpoint_class, params=params)[0]

    def post_json(self, endpoint: str, body: Mapping[str, Any], *, endpoint_class: str, use_basic_auth: bool = False) -> Mapping[str, Any]:
        return self.request_json("POST", endpoint, endpoint_class=endpoint_class, json_body=body, use_basic_auth=use_basic_auth)[0]
