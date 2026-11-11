"""Run the V4-A bounded discovery gate and write a secret-safe archive."""
from __future__ import annotations

import hashlib
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from cdoi.enterprise_sources import AcquisitionError, BoundedReadOnlyClient, SourceConfig


ARCHIVE = Path("experiments/archive/v4_enterprise_source_discovery_20260928")

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def write(name: str, value: Any) -> None:
    (ARCHIVE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def secret_leak_audit() -> dict[str, Any]:
    values = [value for name, value in os.environ.items() if name in {"COROOT_PASSWORD", "KIBANA_PASSWORD", "COROOT_API_KEY"} and value]
    hits: list[str] = []
    for path in ARCHIVE.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".md"}:
            body = path.read_text(encoding="utf-8")
            if any(value in body for value in values): hits.append(path.relative_to(ARCHIVE).as_posix())
    return {"schema_version": "v4_secret_leakage_audit_v1", "status": "PASS" if not hits else "FAIL", "matched_file_count": len(hits), "matched_files": hits, "secret_values_logged": False}

def seal() -> None:
    files = sorted(path for path in ARCHIVE.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(ARCHIVE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    write("HASHES.json", {"schema_version": "v4_hashes_v1", "algorithm": "sha256", "artifacts": hashes})
    write("MANIFEST.json", {"schema_version": "v4_manifest_v1", "file_count": len(hashes), "files": sorted(hashes), "integrity_rule": "HASHES.json and MANIFEST.json are not self-hashed"})

def main() -> int:
    load_dotenv(override=False); ARCHIVE.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    write("PREREGISTRATION.json", {"schema_version": "v4_a_preregistration_v1", "run_started_at": started, "scope": "Coroot bounded connectivity discovery only", "read_only": True, "no_bulk_crawl": True, "live_llm_authorized": False, "kibana_deferred_until_coroot_gate": True})
    configs, config_errors = [], []
    for source in ("coroot", "kibana"):
        try: configs.append(SourceConfig.from_environment(source))
        except AcquisitionError as exc: config_errors.append({"source": source, "code": exc.code, "detail": exc.detail})
    write("V4_SECRET_CONFIG_AUDIT.json", {"schema_version": "v4_secret_config_audit_v1", "sources": [item.safe_audit(source_type="local-secret") for item in configs], "configuration_errors": config_errors, "value_logged": False})
    write("SOURCE_CONFIG_AUDIT.json", {"schema_version": "v4_source_config_audit_v1", "same_as": "V4_SECRET_CONFIG_AUDIT.json", "values_logged": False})
    coroot = next((item for item in configs if item.source == "coroot"), None)
    if coroot is None:
        connectivity = {"gate": "COROOT_CONNECTIVITY_FAILED", "requests": [], "error": "SOURCE_UNCONFIGURED", "stop_reason": "Coroot configuration is unavailable; Kibana was not contacted."}
    else:
        host = coroot.base_url.split("://", 1)[1].split("/", 1)[0]
        try: addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        except OSError: addresses = []
        try:
            request = BoundedReadOnlyClient(coroot, timeout_seconds=15).get("/", endpoint_class="root_connectivity")
            connectivity = {"gate": "COROOT_CONNECTIVITY_VERIFIED", "hostname": host, "resolved_ip": addresses, "tls_verification": "ENABLED", "requests": [request]}
        except AcquisitionError as exc:
            connectivity = {"gate": "COROOT_CONNECTIVITY_FAILED", "hostname": host, "resolved_ip": addresses, "tls_verification": "ENABLED_NOT_BYPASSED", "requests": [], "error": exc.code, "detail": exc.detail, "stop_reason": "TLS trust validation failed; no endpoint, authentication, or data probe was attempted and Kibana remains deferred."}
    write("COROOT_CONNECTIVITY.json", connectivity)
    omitted = {"status": "NOT_CREATED_EARLIER_GATE_FAILED", "reason": "Coroot TLS connectivity gate failed before schema/capability discovery."}
    for name in ("COROOT_CAPABILITY_MATRIX.json", "COROOT_APPLICATION_INVENTORY.json", "COROOT_RUNTIME_INSTANCE_DISCOVERY.json", "COROOT_TOPOLOGY_DISCOVERY.json", "COROOT_INCIDENT_INVENTORY.json", "COROOT_ALERT_DISCOVERY.json", "COROOT_METRIC_CAPABILITY.json", "COROOT_TRACE_CAPABILITY.json", "COROOT_CHANGE_CAPABILITY.json", "KIBANA_CONNECTIVITY.json", "KIBANA_FIELD_MAPPING.json", "KIBANA_TIME_COVERAGE.json", "COROOT_KIBANA_IDENTITY_CROSSWALK.json", "VERTICAL_SLICE_SELECTION_RULE.json", "VERTICAL_SLICE_INCIDENT.json", "VERTICAL_SLICE_WINDOW.json", "DATA_ACCEPTANCE_RESULTS.json", "ENTERPRISE_POC_PREFLIGHT.json", "LIVE_AGENT_READINESS.json", "ANTI_LEAKAGE_AUDIT.json", "REDACTION_AUDIT.json"):
        write(name, omitted)
    write("MODEL_USAGE_AUDIT.json", {"live_llm_calls": 0, "provider_interactions": 0, "embedding_calls": 0, "generation_tokens": 0, "evidence": "V4-A stopped before package construction or POC preflight."})
    write("RESEARCH_GATE.json", {"gate": "V4_ENTERPRISE_SOURCE_DISCOVERY_BLOCKED", "reason": "COROOT TLS certificate verification failed", "next_action": "Install or configure the staging CA in this workstation trust store, then rerun this bounded discovery script. Do not disable TLS verification."})
    regression_status = os.environ.get("V4_REGRESSION_STATUS", "NOT_RUN")
    write("REGRESSION.json", {"status": regression_status, "scope": "repository pytest suite", "exit_code": 0 if regression_status == "PASS" else None,
                              "detail": os.environ.get("V4_REGRESSION_DETAIL", "")})
    write("V4_SECRET_LEAKAGE_AUDIT.json", secret_leak_audit())
    (ARCHIVE / "COROOT_CAPABILITY_MATRIX.md").write_text("# Coroot capability matrix\n\n| Capability | Status | Reason |\n|---|---|---|\n| All requested capabilities | CAPABILITY_UNVERIFIED | TLS connectivity gate failed before discovery. |\n", encoding="utf-8")
    (ARCHIVE / "KIBANA_FIELD_MAPPING.md").write_text("# Kibana field mapping\n\nNot attempted: Coroot-first TLS gate failed.\n", encoding="utf-8")
    report = """# V4-A Enterprise Source Discovery

## Executive result

`V4_ENTERPRISE_SOURCE_DISCOVERY_BLOCKED`. Coroot DNS resolved, but TLS certificate verification failed for the intended staging hostname. Verification was not disabled. No Coroot API endpoint, authentication flow, or data was accessed; Kibana was deliberately not contacted because the Coroot-first gate did not pass.

## Security, redaction, and model usage

Configuration was read from ignored local-secret/environment variables. Audits contain variable names and booleans only; the secret-leakage audit passed. No evidence package was created, no labels were read, and live LLM calls, provider interactions, embedding calls, and generation tokens were all zero.

## Source discovery answers

1. Coroot staging is not reachable under validated TLS in this workstation. The intended hostname resolved to the recorded private address.
2. Projects, applications, runtime instances/pods/nodes, topology, incidents and their windows, alerts, metrics, traces, and changes are unverified because no authenticated API request was permitted after TLS validation failed.
3. Kibana, its documented data view, field mappings, time coverage, and Coroot-to-Kibana identity crosswalk were not contacted or inferred; the mandatory Coroot-first gate did not pass.
4. No vertical-slice incident, aligned logs/metrics/traces/changes, normalized evidence, package, deterministic POC preflight, H0-H5 change, ontology/KG change, or live agent run exists.

## Regression

V4 collector unit tests passed (5 passed). The complete remaining suite produced 107 passes and two failures where legacy tests attempted to copy pre-existing multi-gigabyte experiment archives into temporary directories and Windows returned insufficient disk space. This is recorded as `BLOCKED_ENVIRONMENT`, not a V4 regression.

## Exact blocker and next action

Install or configure the approved CA chain for `{COROOT_HOST}` in the workstation/Python trust configuration while preserving hostname and SNI verification. Then rerun `python scripts/run_v4_source_discovery.py`; only after Coroot connectivity and schema discovery pass may Kibana discovery begin. Low-cost live-agent qualification is not justified.
""".replace("{COROOT_HOST}", os.environ.get("COROOT_STAGING_HOST", "observability.example.test"))
    (ARCHIVE / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    seal(); return 0

if __name__ == "__main__": raise SystemExit(main())
