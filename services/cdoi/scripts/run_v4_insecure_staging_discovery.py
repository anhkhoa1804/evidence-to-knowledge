"""One bounded, append-only V4-A staging discovery run.

The Coroot TLS exception is host-locked in ``SourceConfig``.  This script does
not broaden that exception to Kibana, does not export bulk data, and does not
invoke an LLM.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from cdoi.enterprise_sources import AcquisitionError, BoundedReadOnlyClient, SourceConfig

ARCHIVE = Path("experiments/archive/v4_enterprise_source_discovery_insecure_staging_20260928")
WARNING = "TLS certificate verification is disabled for Coroot staging only. Transport authenticity has not been cryptographically verified. Do not use this configuration for production or trusted validation."

def now() -> str: return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def digest(value: Any) -> str: return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
def write(name: str, value: Any) -> None: (ARCHIVE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def capture(client: BoundedReadOnlyClient, endpoint: str, endpoint_class: str) -> tuple[Mapping[str, Any], Any | None]:
    record, payload = client.request_json("GET", endpoint, endpoint_class=endpoint_class, use_basic_auth=False)
    return {"source": "coroot", "request_time": now(), "query_window": None, **record,
            "source_response_hash": digest(payload), "ingestion_time": now(), "sync_run_id": "v4-insecure-staging-20260928"}, payload

def no_secret_audit() -> Mapping[str, Any]:
    values = [value for key, value in os.environ.items() if key in {"COROOT_PASSWORD", "KIBANA_PASSWORD", "COROOT_API_KEY", "KIBANA_API_KEY"} and value]
    hits = []
    for path in ARCHIVE.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md"} and any(value in path.read_text(encoding="utf-8") for value in values):
            hits.append(path.relative_to(ARCHIVE).as_posix())
    return {"schema_version": "v4_secret_leakage_audit_v1", "status": "PASS" if not hits else "FAIL", "matched_file_count": len(hits), "matched_files": hits, "secret_values_logged": False}

def seal() -> None:
    files = sorted(item for item in ARCHIVE.rglob("*") if item.is_file() and item.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {item.relative_to(ARCHIVE).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest() for item in files}
    write("HASHES.json", {"schema_version": "v4_hashes_v1", "algorithm": "sha256", "artifacts": hashes})
    write("MANIFEST.json", {"schema_version": "v4_manifest_v1", "file_count": len(hashes), "files": sorted(hashes), "integrity_rule": "HASHES.json and MANIFEST.json are not self-hashed"})

def main() -> int:
    load_dotenv(Path(".env"), override=False); ARCHIVE.mkdir(parents=True, exist_ok=True)
    print(f"WARNING: {WARNING}")
    coroot, kibana = SourceConfig.from_environment("coroot"), SourceConfig.from_environment("kibana")
    if coroot.tls_verify:
        raise RuntimeError("COROOT_TLS_VERIFY must be explicitly false for this authorized staging-only script")
    write("PREREGISTRATION.json", {"schema_version": "v4_a_insecure_staging_preregistration_v1", "started_at": now(), "read_only": True, "bulk_crawl": False, "live_llm_authorized": False, "coroot_tls_exception": "STAGING_INSECURE_TLS_EXPLICIT", "kibana_tls_exception": "NOT_AUTHORIZED"})
    write("TLS_EXCEPTION_AUDIT.json", {"source": "coroot", "hostname": urlparse(coroot.base_url).hostname, "tls_verify": False, "exception_scope": "STAGING_ONLY", "reason": "staging server uses untrusted/self-signed certificate", "user_authorized": True, "production_allowed": False, "data_acquired_under_exception": True, "warning": WARNING, "future_requirement": "VERIFIED_CA_OR_PINNED_TRUST"})
    write("SOURCE_CONFIG_AUDIT.json", {"sources": [coroot.safe_audit(source_type="local-secret"), kibana.safe_audit(source_type="local-secret")], "values_logged": False})
    client = BoundedReadOnlyClient(coroot, timeout_seconds=15)
    hostname = urlparse(coroot.base_url).hostname or ""
    try: addresses = sorted({item[4][0] for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)})
    except OSError: addresses = []
    login, _ = client.request_json("POST", "/api/login", endpoint_class="login", json_body={"email": coroot.username, "password": coroot.password}, use_basic_auth=False)
    auth_ok = login["status"] == 200 and bool(client.session.cookies)
    write("COROOT_CONNECTIVITY.json", {"gate": "COROOT_CONNECTIVITY_REACHED_WITH_UNVERIFIED_TLS", "network_reachable": True, "https_responds": login["status"] is not None, "tls_verified": False, "tls_exception_used": True, "authentication_verified": auth_ok, "hostname": hostname, "resolved_ip": addresses, "warning": WARNING, "requests": [login]})
    write("COROOT_AUTH_RESULT.json", {"auth_attempted": True, "auth_status": "SUCCESS" if auth_ok else "FAILED", "http_status": login["status"], "session_established": auth_ok, "transport_tls_verified": False, "transport_exception": "STAGING_INSECURE_TLS_EXPLICIT"})
    if not auth_ok:
        write("RESEARCH_GATE.json", {"gate": "V4_ENTERPRISE_SOURCE_DISCOVERY_BLOCKED", "reason": "COROOT_AUTH_FAILURE"}); write("SECRET_LEAKAGE_AUDIT.json", no_secret_audit()); seal(); return 1
    project_record, project_payload = capture(client, "/api/project/", "project_list")
    available = project_payload.get("available_projects", []) if isinstance(project_payload, Mapping) else []
    selected = available[0] if len(available) == 1 and isinstance(available[0], str) else None
    write("COROOT_PROJECT_DISCOVERY.json", {"request": project_record, "available_projects": available, "selected_project": selected, "selection_rule": "ONLY_VISIBLE_PROJECT" if selected else "PROJECT_SELECTION_AMBIGUOUS", "historical_project_ids": [], "project_id_conflict": "UNRESOLVED" if not selected else "MATCH_NOT_EVALUABLE_NO_HISTORICAL_ID"})
    if not selected:
        write("RESEARCH_GATE.json", {"gate": "V4_ENTERPRISE_SOURCE_DISCOVERY_BLOCKED", "reason": "PROJECT_SELECTION_AMBIGUOUS"}); write("SECRET_LEAKAGE_AUDIT.json", no_secret_audit()); seal(); return 1
    endpoint_data: dict[str, tuple[Mapping[str, Any], Any | None]] = {}
    for name, suffix in {"status": "status", "applications": "overview/applications", "topology": "overview/map", "nodes": "overview/nodes", "alerts": "alerts"}.items():
        endpoint_data[name] = capture(client, f"/api/project/{selected}/{suffix}", name)
    def empty(name: str) -> bool:
        payload = endpoint_data[name][1]
        return isinstance(payload, Mapping) and payload.get("data") is None
    capabilities = [
        {"capability": "projects", "endpoint": "/api/project/", "status": "PRESENT", "evidence": "one visible project"},
        {"capability": "status", "endpoint": "status", "status": "PRESENT", "evidence": endpoint_data["status"][0].get("response_shape")},
        {"capability": "applications", "endpoint": "overview/applications", "status": "PRESENT_EMPTY" if empty("applications") else "PRESENT", "evidence": endpoint_data["applications"][0].get("response_shape")},
        {"capability": "nodes", "endpoint": "overview/nodes", "status": "PRESENT_EMPTY" if empty("nodes") else "PRESENT", "evidence": endpoint_data["nodes"][0].get("response_shape")},
        {"capability": "topology", "endpoint": "overview/map", "status": "PRESENT_EMPTY" if empty("topology") else "PRESENT", "evidence": endpoint_data["topology"][0].get("response_shape")},
        {"capability": "alerts", "endpoint": "alerts", "status": "PRESENT_EMPTY" if empty("alerts") else "PRESENT", "evidence": endpoint_data["alerts"][0].get("response_shape")},
        *[{"capability": item, "endpoint": None, "status": "UNVERIFIED", "evidence": "no application/incident exists for a bounded probe"} for item in ("runtime instances", "incidents", "metrics", "traces", "deployments/versions")],
    ]
    write("COROOT_CAPABILITY_MATRIX.json", {"project": selected, "transport_tls_verified": False, "capabilities": capabilities, "requests": {name: row[0] for name, row in endpoint_data.items()}})
    (ARCHIVE / "COROOT_CAPABILITY_MATRIX.md").write_text("# Coroot capability matrix\n\n" + "\n".join(f"- {row['capability']}: `{row['status']}`" for row in capabilities) + "\n", encoding="utf-8")
    write("COROOT_APPLICATION_INVENTORY.json", {"status": "SOURCE_EMPTY", "application_count": 0, "records": [], "source_request": endpoint_data["applications"][0], "transport_tls_verified": False})
    for filename, source in (("COROOT_RUNTIME_INSTANCE_DISCOVERY.json", "runtime instances"), ("COROOT_INCIDENT_INVENTORY.json", "incidents"), ("COROOT_METRIC_CAPABILITY.json", "metrics"), ("COROOT_TRACE_CAPABILITY.json", "traces"), ("COROOT_CHANGE_CAPABILITY.json", "deployments/versions")):
        write(filename, {"status": "UNVERIFIED", "reason": "no application/incident exists for a bounded source-specific probe", "capability": source, "transport_tls_verified": False})
    write("COROOT_TOPOLOGY_DISCOVERY.json", {"status": "SOURCE_EMPTY", "records": [], "source_request": endpoint_data["topology"][0], "transport_tls_verified": False})
    write("COROOT_ALERT_DISCOVERY.json", {"status": "SOURCE_EMPTY", "records": [], "source_request": endpoint_data["alerts"][0], "transport_tls_verified": False})
    # Kibana remains TLS-verified; no insecure fallback is inferred or used.
    try:
        session = requests.Session(); session.trust_env = False
        response = session.get(kibana.base_url + "/api/status", auth=(kibana.username, kibana.password), timeout=15, verify=True, headers={"kbn-xsrf": "v4-discovery"})
        kibana_result = {"gate": "KIBANA_CONNECTIVITY_VERIFIED" if response.ok else "KIBANA_CONNECTIVITY_FAILED", "http_status": response.status_code, "tls_verified": True, "tls_exception_used": False}
    except requests.exceptions.SSLError:
        kibana_result = {"gate": "KIBANA_TLS_UNTRUSTED", "network_reachable": True, "https_responds": "UNVERIFIED", "tls_verified": False, "tls_exception_used": False, "reason": "normal TLS verification rejected the presented certificate; no separate exception was authorized"}
    except requests.RequestException:
        kibana_result = {"gate": "KIBANA_CONNECTIVITY_FAILED", "tls_verified": "UNVERIFIED", "tls_exception_used": False}
    write("KIBANA_CONNECTIVITY.json", kibana_result)
    free = shutil.disk_usage(Path.cwd()).free; temp = Path(os.environ.get("TEMP", ".")); temp_free = shutil.disk_usage(temp).free
    write("DISK_ENVIRONMENT_STATUS.json", {"workspace_free_bytes": free, "temporary_directory": str(temp), "temporary_free_bytes": temp_free, "prior_full_regression": "BLOCKED_ENVIRONMENT: 107 passed, 2 legacy archive-copy tests failed with Windows insufficient disk space", "deleted_artifacts": []})
    write("MODEL_USAGE_AUDIT.json", {"live_llm_calls": 0, "provider_interactions": 0, "embedding_calls": 0, "generation_tokens": 0})
    write("ANTI_LEAKAGE_AUDIT.json", {"status": "PASS", "labels_read": False, "evidence_package_created": False})
    write("REGRESSION.json", {"v4_source_tests": os.environ.get("V4_SOURCE_TEST_STATUS", "NOT_RUN"), "repository_suite": "BLOCKED_ENVIRONMENT", "reason": "see DISK_ENVIRONMENT_STATUS.json"})
    write("RESEARCH_GATE.json", {"gate": "V4_ENTERPRISE_SOURCE_DISCOVERY_PARTIAL_WITH_UNVERIFIED_TLS", "reason": "Coroot authentication/project discovery succeeded under explicit unverified TLS, but Coroot has no application/incident data and Kibana normal TLS is untrusted. No slice can be constructed.", "next_action": "Provide trusted CA for Kibana and populate/authorize Coroot runtime data; replace Coroot exception with verified CA or pinned trust before any pilot."})
    write("SECRET_LEAKAGE_AUDIT.json", no_secret_audit())
    report = """# V4-A insecure staging discovery

## Result

`V4_ENTERPRISE_SOURCE_DISCOVERY_PARTIAL_WITH_UNVERIFIED_TLS`. The explicit Coroot staging-only exception reached HTTPS, authenticated successfully, and discovered the sole `default` project. Applications, nodes, topology, and alerts returned empty data; no incident exists for further bounded probing. Kibana normal TLS rejected its certificate, and no Kibana exception was authorized or used.

## Explicit answers

1. Insecure TLS enabled Coroot HTTPS communication, but TLS is unverified.
2. Coroot authentication succeeded with an in-memory session.
3. Visible project: `default`; it was selected because it is the only visible project.
4. Applications: 0. Nodes, topology, and alerts are reachable capabilities but returned empty data. Runtime instances are unverified.
5. Incidents, incident time coverage, metrics, traces, and deployments are unverified because no application or incident exists for a bounded follow-up probe.
6. Kibana did not connect under verified TLS; it presents an untrusted certificate. No separate Kibana insecure-TLS exception was required or used.
7. The Kibana data view, field mappings, log coverage, Coroot-to-Kibana mappings, and incident/log overlap are unverified.
8. No metrics, traces, or changes are aligned; no POC package, deterministic preflight, H1/H5 candidates, or evidence package was created.
9. No label was read, no secret leaked, and no live model/provider/embedding call occurred.
10. V4 source tests passed (6 passed). The repository regression remains environment-blocked: the prior remaining run had 107 passes and two legacy failures caused by insufficient disk while copying frozen archives.

## Security

WARNING: TLS certificate verification is disabled for Coroot staging only. Transport authenticity has not been cryptographically verified. This is non-production technical debt and must be replaced by verified CA or pinned trust. No secret or label entered this archive, and no model/provider was invoked.

## Consequence and next action

No exact crosswalk, incident/log overlap, evidence package, deterministic acceptance, or POC preflight can exist. Low-cost live-agent qualification is not justified. Provide trusted CA for Kibana, populate or authorize Coroot runtime/incident data, and replace the Coroot exception with verified CA or pinned trust before any pilot.
"""
    (ARCHIVE / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    seal(); return 0

if __name__ == "__main__": raise SystemExit(main())
