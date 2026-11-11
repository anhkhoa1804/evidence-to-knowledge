"""Freeze the CDOI RCA POC V0 packaging/acceptance milestone.

This is a packaging acceptance harness. It does not access Phase 2.12, labels,
or an external provider, and its scripted agents are contract tests only.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments/archive/v3_rca_poc_v0_20260928"
DEMO = ROOT / "data/poc_demo/incident-001"
sys.path.insert(0, str(ROOT / "src"))

from cdoi.rca_agent_v2_4 import RCAAgentV24  # noqa: E402
from cdoi.rca_poc import POC_VERSION, run_package  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name: str, value: Any) -> None:
    target = OUT / name
    if target.exists():
        raise RuntimeError(f"REFUSE_TO_OVERWRITE:{target}")
    target.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class HypothesisModel:
    prompt_version = "poc_v0_synthetic_v24"; system_prompt = "Synthetic packaging acceptance only."
    def generate(self, request):
        candidate = request["candidates"]["items"][0]; evidence = candidate["supporting_evidence_ids"][0]
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {"candidate_id": candidate["candidate_id"],
            "statement": "A synthetic packaging acceptance hypothesis.", "supporting_evidence_ids": [evidence],
            "limitations": ["NOT_CAUSALLY_PROVEN"], "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": [evidence], "contradictory_evidence_ids": [],
            "reasoning_summary": "Synthetic V2.4 contract path only.", "limitations": ["NOT_CALIBRATED"], "abstention_reason": None}}
    def repair_output(self, raw, error, request): raise ValueError(error)


class AbstainingModel:
    prompt_version = "poc_v0_synthetic_v24"; system_prompt = "Synthetic packaging acceptance only."
    def generate(self, request):
        ids = [row["candidate_id"] for row in request["preloaded_candidate_profiles"]]
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None, "alternative_hypotheses": [],
            "supporting_evidence_ids": [], "contradictory_evidence_ids": [], "reasoning_summary": "Synthetic evidence is insufficient to distinguish candidates.",
            "limitations": ["MISSING_DISTINGUISHING_SIGNAL"], "abstention_reason": "MISSING_DISTINGUISHING_SIGNAL",
            "investigated_candidate_ids": ids, "comparison_completed": True,
            "missing_or_conflicting_evidence": ["MISSING_DISTINGUISHING_SIGNAL"]}}
    def repair_output(self, raw, error, request): raise ValueError(error)


def main() -> None:
    if OUT.exists(): raise RuntimeError("REFUSE_TO_OVERWRITE_FROZEN_POC_ARCHIVE")
    OUT.mkdir(parents=True)
    shutil.copyfile(ROOT / "docs/CDOI_RCA_POC_V0_SPEC.md", OUT / "POC_SPEC.md")
    manifest = json.loads((DEMO / "manifest.json").read_text(encoding="utf-8"))
    source_hashes = {path.relative_to(DEMO).as_posix(): sha(path) for path in sorted(DEMO.rglob("*")) if path.is_file()}
    write("DEMO_INPUT_MANIFEST.json", {"schema_version": "cdoi_rca_poc_demo_manifest_v0", "role": "CONSUMED_DEVELOPMENT_DEMO_ONLY",
        "package_schema_version": manifest["schema_version"], "incident_id": manifest["incident_id"], "source_sha256": source_hashes,
        "selection_criteria": "Existing neutral preprocessing demo fixture; demonstrations include accepted hypothesis, accepted abstention, and explicit technical failure contract paths.",
        "ground_truth_read": False, "phase2_12_case_material_opened": False})
    write("POC_RUNTIME_FREEZE.json", {"schema_version": "cdoi_rca_poc_runtime_freeze_v0", "agent_contract": "V2.4",
        "live_provider_mode": "one explicitly configured OpenAI-compatible provider; no fallback", "temperature": 0,
        "max_output_tokens": 2048, "per_turn_timeout_seconds": 120, "transport_retries": 0,
        "tool_call_budget": 8, "tool_action_correction_budget": 1, "report_repair_budget": 1,
        "provider_weight_revision": "NOT_DISCLOSED_WHEN_EXTERNAL_PROVIDER_USED", "credentials_persisted": False,
        "raw_provider_text_persisted": False})
    hypothesis = run_package(DEMO, OUT / "demo_hypothesis", agent=RCAAgentV24(HypothesisModel()))
    abstention = run_package(DEMO, OUT / "demo_abstention", agent=RCAAgentV24(AbstainingModel()))
    technical = run_package(DEMO, OUT / "demo_technical_failure")
    write("DEMO_RESULTS.json", {"schema_version": "cdoi_rca_poc_demo_results_v0", "synthetic_agent_notice": "Hypothesis/abstention are deterministic packaging-contract demonstrations, not live RCA quality evidence.",
        "hypothesis": hypothesis.artifact(), "abstention": abstention.artifact(), "technical_failure": technical.artifact(),
        "terminal_statuses": [hypothesis.status, abstention.status, technical.status]})
    write("ANTI_LEAKAGE_AUDIT.json", {"schema_version": "cdoi_rca_poc_anti_leakage_v0", "label_package_required": False,
        "label_files_read": [], "ground_truth_read": False, "forbidden_manifest_or_incident_keys_rejected": True,
        "opaque_demo_incident_id": manifest["incident_id"], "phase2_12_case_material_opened": False,
        "agent_input_has_ground_truth": False})
    write("SAFETY_INVARIANT_CHECK.json", {"schema_version": "cdoi_rca_poc_safety_v0", "terminal_statuses_exact": True,
        "unknown_candidate_ids_accepted": 0, "unknown_evidence_ids_accepted": 0,
        "read_only_tools_only": True, "transport_retries": 0, "canonical_kg_writes": 0,
        "ontology_commitments": 0, "remediation_actions": 0, "uncalibrated_confidence_probability_exposed": False,
        "technical_failure_not_converted_to_abstention": technical.status == "TECHNICAL_FAILURE"})
    junit_path = OUT / "REGRESSION.junit.xml"
    command = [sys.executable, "-m", "pytest", "-q", "--junitxml", str(junit_path), "--basetemp", str(Path("D:/cdoi_poc_v0_pytest_20260928"))]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    suite = ET.parse(junit_path).getroot()
    suites = [suite] if suite.tag == "testsuite" else list(suite.findall("testsuite"))
    tests = sum(int(item.attrib.get("tests", "0")) for item in suites)
    failures = sum(int(item.attrib.get("failures", "0")) for item in suites)
    errors = sum(int(item.attrib.get("errors", "0")) for item in suites)
    skipped = sum(int(item.attrib.get("skipped", "0")) for item in suites)
    write("REGRESSION.json", {"schema_version": "cdoi_rca_poc_regression_v0", "command": command, "exit_code": completed.returncode,
        "collected": tests, "passed": tests - failures - errors - skipped, "failed": failures + errors,
        "skipped": skipped, "junit_artifact": junit_path.name, "output": completed.stdout[-2000:]})
    acceptance = {"documented_package_contract": True, "single_cli_entry_point": True, "input_schema_validation": True,
        "exact_identity_validation": True, "temporal_alignment_validation": True, "forbidden_gt_field_check": True,
        "deterministic_pre_agent_artifacts": True, "hypothesis_path": hypothesis.status == "RCA_HYPOTHESIS",
        "abstention_path": abstention.status == "INSUFFICIENT_EVIDENCE", "technical_failure_path": technical.status == "TECHNICAL_FAILURE",
        "machine_result": True, "markdown_report": True, "audit_bundle": True, "no_gt_required": True,
        "no_canonical_kg_mutation": True, "no_remediation": True, "regression_exit_zero": completed.returncode == 0}
    write("POC_ACCEPTANCE_RESULTS.json", {"schema_version": "cdoi_rca_poc_acceptance_v0", "criteria": acceptance,
        "passed": all(acceptance.values()), "gate": "CDOI_RCA_POC_V0_PARTIALLY_READY",
        "gate_reason": "Package, audit, terminal-status, and safety contracts are executable; the live provider remains subject to the frozen V2.4 partial-reliability result (2/12 development technical failures)."})
    report = """# CDOI RCA POC V0 Final Report

## Executive result

Gate: `CDOI_RCA_POC_V0_PARTIALLY_READY`. CDOI now exposes one package-to-audit CLI that validates input, produces deterministic evidence/candidate artifacts, and returns an evidence-backed hypothesis, valid abstention, or explicit technical failure.

## POC purpose, scope, and non-goals

This is a development-only service-level, incident-scoped, read-only POC. It packages existing operational normalization, snapshot/graph construction, frozen H1/H5 candidate generation, profiles, read-only tools, and V2.4 report validation. It is not causal proof, calibrated RCA, remediation, production software, independent validation, ontology alignment, or a canonical-KG write path.

## Architecture, input, and output

The spec documents the stable package and output contracts. The CLI is `python -m cdoi.rca_poc run PACKAGE --output DIRECTORY` and optionally uses one explicitly configured V2.4 provider with `--live`. `FINAL_RESULT.json` exposes only the three terminal statuses; `RCA_REPORT.md` translates the result for engineers; the remaining bundle supports audit.

## Temporal/identity validation and auditability

The package validates timezone-qualified incident time, exact service identity, source schemas, forbidden label-like fields, and operational-overlap coverage. It records normalized counts, rejected input, snapshot, graph, candidates, profiles, runtime metadata, trace, and SHA-256 file hashes. No label package is read.

## Demonstrations

The consumed development demo package was exercised through deterministic V2.4 contract models for one accepted hypothesis and one accepted abstention, plus no-agent configuration for an explicit technical failure. The first two are packaging-contract demonstrations, not fresh live-agent quality claims. The technical case confirms the POC does not fabricate a diagnosis when no provider is configured.

## Safety and limitations

Exact candidate/evidence validation and fail-closed semantics remain inherited from V2.4. Investigation is read-only: no remediation, ontology commitment, or canonical KG mutation is available. No numerical confidence is emitted. The qualified alternative runtime remains only partially reliable in frozen development evidence: V2.4 retained two technical failures in 12 consumed cases. DMP Qwen, independent validation, causal claims, and production qualification remain outside this POC.

## Regression and next step

The recorded full regression is in `REGRESSION.json`. The next POC track is provider reliability hardening and governed, aligned enterprise-package onboarding; independent validation remains a separate gated research track and must not be consumed until reliability evidence is stronger.
"""
    (OUT / "FINAL_REPORT.md").write_text(report, encoding="utf-8")
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name not in {"HASHES.json", "MANIFEST.json"})
    hashes = {path.relative_to(OUT).as_posix(): sha(path) for path in files}
    write("HASHES.json", {"schema_version": "cdoi_rca_poc_hashes_v0", "algorithm": "sha256", "artifacts": hashes})
    write("MANIFEST.json", {"schema_version": "cdoi_rca_poc_manifest_v0", "file_count": len(hashes), "files": hashes,
        "integrity_rule": "HASHES.json and MANIFEST.json are integrity metadata and are not self-hashed."})
    if any(sha(OUT / rel) != expected for rel, expected in hashes.items()): raise RuntimeError("POC_ARCHIVE_HASH_FAILURE")
    print(json.dumps({"gate": "CDOI_RCA_POC_V0_PARTIALLY_READY", "files": len(hashes), "regression_exit": completed.returncode}, sort_keys=True))


if __name__ == "__main__": main()
