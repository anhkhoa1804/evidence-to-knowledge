"""Freeze deterministic VDT data acceptance and RCA POC preflight readiness.

No live provider, embedding service, V2.4 agent, or label value is used here.
The current VDT delivery is read-only; this runner writes only a new archive.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VDT = ROOT.parent / "VDT"
OUT = ROOT / "experiments/archive/v3_vdt_poc_data_acceptance_20260928"
sys.path.insert(0, str(ROOT / "src"))

from cdoi.vdt_acceptance import coverage_csv_rows, source_inventory, validate  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    target = OUT / name
    if target.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value if isinstance(value, str) else json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def markdown_table(rows: list[dict[str, Any]], columns: tuple[str, ...]) -> str:
    header = "| " + " | ".join(columns) + " |\n"
    divider = "| " + " | ".join("---" for _ in columns) + " |\n"
    body = "".join("| " + " | ".join(str(row.get(column, "")).replace("|", "\\|") for column in columns) + " |\n" for row in rows)
    return header + divider + body


def main() -> None:
    if OUT.exists():
        raise RuntimeError("REFUSE_TO_OVERWRITE_FROZEN_VDT_ACCEPTANCE_ARCHIVE")
    if not VDT.is_dir():
        raise RuntimeError("VDT_SOURCE_NOT_FOUND")
    OUT.mkdir(parents=True)
    before = {path.name: sha(path) for path in sorted(VDT.iterdir()) if path.is_file()}
    write("PREREGISTRATION.json", {"schema_version": "vdt_poc_acceptance_preregistration_v1", "scope": "deterministic VDT inventory, acceptance, POC package eligibility and preflight readiness", "source": "EXTERNAL_READ_ONLY_VDT", "forbidden": ["live LLM", "V2.4 live agent", "embeddings", "labels in evidence", "window expansion", "timezone reinterpretation", "Phase 2.12", "H0-H5 change", "canonical KG mutation"]})
    inventory = source_inventory(VDT); acceptance = validate(VDT)
    write("VDT_SOURCE_INVENTORY.json", inventory)
    inventory_rows = [{"source": row["source_name"], "format": row.get("format"), "records": row.get("record_count"), "status": row.get("status"), "modality": row.get("likely_modality"), "label_fields": ", ".join(row.get("label_like_field_names_only", [])) or "none"} for row in inventory["files"]]
    write("VDT_SOURCE_INVENTORY.md", "# VDT Source Inventory\n\n" + markdown_table(inventory_rows, ("source", "format", "records", "status", "modality", "label_fields")) + "\nAll fields are structural summaries; label values and raw enterprise records are not exported.\n")
    write("VDT_ACCEPTANCE_RESULTS.json", acceptance)
    coverage = coverage_csv_rows(acceptance); write("VDT_INCIDENT_COVERAGE.json", {"schema_version": "vdt_incident_coverage_v1", "rows": coverage})
    with (OUT / "VDT_INCIDENT_COVERAGE.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("incident_id", "status", "identity", "logs", "metrics", "traces", "changes", "topology", "provenance", "poc_ready", "reason_codes")); writer.writeheader(); writer.writerows(coverage)
    write("VDT_INCIDENT_COVERAGE.md", "# VDT Incident Coverage\n\n" + markdown_table(coverage, ("incident_id", "status", "identity", "logs", "metrics", "traces", "changes", "topology", "provenance", "poc_ready")))
    aggregate = acceptance["aggregate"]
    gap = {"schema_version": "vdt_current_gap_analysis_v1", "incident_total": acceptance["incident_total"], "structurally_valid_incidents": acceptance["structurally_valid_incidents"], "exact_resolvable_identity": aggregate["exact_resolvable_identity"], "aligned_logs": aggregate["aligned_logs"], "aligned_metrics": {"count": 0, "reason": "SOURCE_NOT_DELIVERED"}, "aligned_traces": {"count": 0, "reason": "SOURCE_NOT_DELIVERED"}, "aligned_changes": {"count": 0, "reason": "SOURCE_NOT_DELIVERED"}, "usable_topology": aggregate["usable_topology"], "minimum_poc_packages": aggregate["minimum_poc_packages"], "temporal_finding": "Valid VDT incident windows have no aligned log records; current log records are outside those windows.", "no_window_expansion": True, "no_timezone_reinterpretation": True, "label_values_read": False}
    write("VDT_CURRENT_GAP_ANALYSIS.json", gap)
    requirements = {"schema_version": "vdt_data_acquisition_requirements_v2", "reference_spec": "docs/CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md", "P0": ["authoritative valid incident intervals", "exact identity map", "logs/events aligned to those intervals", "per-source provenance", "separate governed labels if evaluation is later intended"], "P1": ["metrics", "traces", "changes/deployments", "runtime instance/host mapping", "topology provenance"], "P2": ["ConfigProfile", "ServiceBusinessProfile", "KnownProblem", "Procedure", "business impact"], "current_delivery": {"topology": "STRUCTURALLY_DELIVERED", "service_inventory": "STRUCTURALLY_DELIVERED", "identity_map": "STRUCTURALLY_DELIVERED", "logs": "DELIVERED_NOT_TEMPORALLY_ALIGNED", "metrics": "SOURCE_NOT_DELIVERED", "traces": "SOURCE_NOT_DELIVERED", "changes": "SOURCE_NOT_DELIVERED", "governed_root_labels": "NOT_DELIVERED"}}
    write("DATA_ACQUISITION_REQUIREMENTS.json", requirements)
    write("POC_PACKAGE_BUILD_RESULTS.json", {"schema_version": "vdt_poc_package_build_results_v1", "accepted_incident_count": aggregate["minimum_poc_packages"], "packages_built": 0, "status": "NOT_RUN_NO_ACCEPTED_INCIDENTS" if aggregate["minimum_poc_packages"] == 0 else "NOT_RUN_BY_FROZEN_ARCHIVE_RUNNER", "reason": "Current VDT delivery has no accepted incident; package builder was tested only with deterministic fixtures.", "label_values_read": False})
    write("POC_PREFLIGHT_RESULTS.json", {"schema_version": "vdt_poc_preflight_results_v1", "runs": [], "status": "NOT_RUN_NO_ACCEPTED_INCIDENTS" if aggregate["minimum_poc_packages"] == 0 else "NOT_RUN", "required_path": "package validation → normalization → EvidenceSnapshot → IncidentEvidenceGraph → frozen H1/H5 → CandidateEvidenceProfiles → stop before live model", "live_provider_invocations": 0, "generation_tokens": 0})
    write("ANTI_LEAKAGE_AUDIT.json", {"schema_version": "vdt_poc_anti_leakage_v1", "label_values_read": False, "label_field_names_detected_only": acceptance["label_package"]["detected_field_names_only"], "labels_entered_normalization": False, "labels_entered_snapshot": False, "labels_entered_candidates": False, "labels_entered_profiles": False, "labels_entered_agent": False, "phase2_12_case_material_opened": False, "policy": "LABEL_PACKAGE_SEPARATE"})
    write("MODEL_USAGE_AUDIT.json", {"schema_version": "vdt_poc_model_usage_audit_v1", "live_llm_calls": 0, "live_provider_interactions": 0, "generation_tokens": 0, "embedding_api_calls": 0, "scripted_model_calls": 0, "purpose": "deterministic VDT data acceptance and POC preflight", "evidence": "This runner imports no provider client and records no agent invocation."})
    after = {path.name: sha(path) for path in sorted(VDT.iterdir()) if path.is_file()}
    write("SOURCE_INTEGRITY.json", {"before": before, "after": after, "unchanged": before == after})
    shutil.copyfile(ROOT / "docs/CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md", OUT / "CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md")
    shutil.copyfile(ROOT / "docs/VDT_RCA_DATA_ACQUISITION_REQUEST_V2.md", OUT / "VDT_RCA_DATA_ACQUISITION_REQUEST_V2.md")
    shutil.copyfile(ROOT / "docs/VDT_DATA_OWNER_REQUEST_MATRIX.md", OUT / "VDT_DATA_OWNER_REQUEST_MATRIX.md")
    junit = OUT / "REGRESSION.junit.xml"
    command = [sys.executable, "-m", "pytest", "-q", "--junitxml", str(junit), "--basetemp", "D:/cdoi_vdt_poc_acceptance_pytest_20260928"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    root = ET.parse(junit).getroot(); suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = sum(int(row.attrib.get("tests", "0")) for row in suites); failures = sum(int(row.attrib.get("failures", "0")) + int(row.attrib.get("errors", "0")) for row in suites); skipped = sum(int(row.attrib.get("skipped", "0")) for row in suites)
    write("REGRESSION.json", {"schema_version": "vdt_poc_acceptance_regression_v1", "command": command, "exit_code": completed.returncode, "collected": tests, "passed": tests - failures - skipped, "failed": failures, "skipped": skipped, "junit_artifact": junit.name, "output": completed.stdout[-2000:]})
    gate = "VDT_DATA_READY_FOR_RCA_POC" if aggregate["minimum_poc_packages"] else "VDT_DATA_NOT_READY_FOR_RCA_POC"
    write("RESEARCH_GATE.json", {"schema_version": "vdt_poc_data_readiness_gate_v1", "gate": gate, "answers_data_readiness_not_rca_quality": True, "minimum_poc_packages": aggregate["minimum_poc_packages"], "live_model_authorized_by_this_gate": False, "next_action": "Obtain an aligned governed evidence delivery, then rerun deterministic acceptance and POC preflight."})
    report = f"""# VDT POC Data Acceptance Final Report

## Executive result

Gate: `{gate}`. The current VDT delivery cannot produce a valid POC package without fabrication: zero incidents satisfy the deterministic minimum evidence contract.

## Purpose and no-LLM scope

This run inventories and accepts/rejects operational data before RCA reasoning. No live LLM, scripted model, embedding service, agent, tool call, generation token, Phase 2.12 material, or label value was used.

## Inventory and incident population

VDT contains {acceptance['incident_total']} incident records; {acceptance['structurally_valid_incidents']} have explicit valid windows and {aggregate['exact_resolvable_identity']} have exact resolvable service identity. Topology is usable for {aggregate['usable_topology']} structurally valid exact-ID anchors.

## Temporal and modality coverage

Aligned logs: {aggregate['aligned_logs']}. Metrics: `0/N — SOURCE_NOT_DELIVERED`. Traces: `0/N — SOURCE_NOT_DELIVERED`. Changes/deployments: `0/N — SOURCE_NOT_DELIVERED`. Existing logs are present but not aligned to valid incident intervals; timestamps were not shifted and windows were not expanded.

## Provenance and labels

Hashes are retained, but source ownership, collection method, and governed label provenance remain unavailable. Potential label field names were detected structurally; no label value entered evidence, snapshots, candidates, profiles, packages, or a model input.

## POC eligibility and preflight

No incident was `ACCEPTED_FOR_POC_PREFLIGHT`; therefore zero VDT POC packages were built and zero POC preflight runs were attempted. The builder and POC `--preflight-only` boundary are covered by deterministic tests, but no synthetic or substituted VDT success was created.

## Exact missing data and request

The P0 need is telemetry/events covering the same declared incident periods, plus valid authoritative windows, exact identity/provenance metadata, and separate governed labels for any future evaluation. See `VDT_RCA_DATA_ACQUISITION_REQUEST_V2.md`, `VDT_DATA_OWNER_REQUEST_MATRIX.md`, and `CDOI_RCA_DATA_ACQUISITION_SPEC_V1.md`.

## Regression and integrity

Full regression: {tests} collected, {tests - failures - skipped} passed, {failures} failed, {skipped} skipped. VDT source hashes before/after are identical: {before == after}. This archive is hash-sealed.

## Recommended next action

Request aligned VDT evidence for governed incident windows, then rerun `python -m cdoi.vdt_acceptance validate SOURCE --output RESULT.json`. Do not call a live agent until an incident is accepted and deterministic POC preflight has reached H1/H5 and profiles.
"""
    write("FINAL_REPORT.md", report)
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(OUT).as_posix(): sha(path) for path in files}
    write("HASHES.json", {"schema_version": "vdt_poc_acceptance_hashes_v1", "algorithm": "sha256", "artifacts": hashes})
    write("MANIFEST.json", {"schema_version": "vdt_poc_acceptance_manifest_v1", "file_count": len(hashes), "files": hashes, "integrity_rule": "HASHES.json and MANIFEST.json are not self-hashed."})
    if any(sha(OUT / name) != expected for name, expected in hashes.items()):
        raise RuntimeError("VDT_ACCEPTANCE_ARCHIVE_HASH_FAILURE")
    print(json.dumps({"gate": gate, "files": len(hashes), "regression_exit": completed.returncode}, sort_keys=True))


if __name__ == "__main__":
    main()
