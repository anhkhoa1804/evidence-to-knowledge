"""POC V0 package, audit, and fail-closed boundary tests."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from cdoi.rca_agent_v2_4 import RCAAgentV24
from cdoi.rca_poc import run_package

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "data/poc_demo/incident-001"


def package(tmp_path: Path) -> Path:
    target = tmp_path / "package"
    shutil.copytree(DEMO, target)
    return target


class HypothesisModel:
    prompt_version = "poc_test_v24"; system_prompt = "synthetic POC test"

    def generate(self, request):
        candidate = request["candidates"]["items"][0]
        evidence = candidate["supporting_evidence_ids"][0]
        return {"report": {"status": "RCA_HYPOTHESIS", "primary_hypothesis": {
            "candidate_id": candidate["candidate_id"], "statement": "A bounded test hypothesis.",
            "supporting_evidence_ids": [evidence], "limitations": ["NOT_CAUSALLY_PROVEN"],
            "model_self_assessment": "LOW"}, "alternative_hypotheses": [],
            "supporting_evidence_ids": [evidence], "contradictory_evidence_ids": [],
            "reasoning_summary": "A test evidence-backed hypothesis.", "limitations": ["NOT_CALIBRATED"],
            "abstention_reason": None}}

    def repair_output(self, raw, error, request):
        raise ValueError(error)


class AbstainingModel:
    prompt_version = "poc_test_v24"; system_prompt = "synthetic POC test"

    def generate(self, request):
        ids = [row["candidate_id"] for row in request["preloaded_candidate_profiles"]]
        return {"report": {"status": "INSUFFICIENT_EVIDENCE", "primary_hypothesis": None,
            "alternative_hypotheses": [], "supporting_evidence_ids": [], "contradictory_evidence_ids": [],
            "reasoning_summary": "Evidence does not distinguish candidates.", "limitations": ["SPARSE_SIGNAL"],
            "abstention_reason": "SPARSE_SIGNAL", "investigated_candidate_ids": ids,
            "comparison_completed": True, "missing_or_conflicting_evidence": ["MISSING_DISTINGUISHING_SIGNAL"]}}

    def repair_output(self, raw, error, request):
        raise ValueError(error)


class UnknownEvidenceModel(HypothesisModel):
    def generate(self, request):
        result = super().generate(request)
        result["report"]["primary_hypothesis"]["supporting_evidence_ids"] = ["invented-evidence"]
        result["report"]["supporting_evidence_ids"] = ["invented-evidence"]
        return result


def agent(model):
    return RCAAgentV24(model)


def assert_manifest(output: Path) -> None:
    manifest = json.loads((output / "MANIFEST.json").read_text())
    assert manifest["file_count"] == len(manifest["files"])
    for relative, expected in manifest["files"].items():
        assert hashlib.sha256((output / relative).read_bytes()).hexdigest() == expected


def test_poc_hypothesis_has_complete_audit_and_exact_ids(tmp_path):
    output = tmp_path / "out"
    result = run_package(package(tmp_path), output, agent=agent(HypothesisModel()))
    assert result.status == "RCA_HYPOTHESIS"
    assert result.hypotheses and result.evidence_references
    for name in ("INPUT_VALIDATION.json", "NORMALIZATION_SUMMARY.json", "INPUT_PREFLIGHT.json",
                 "EVIDENCE_SNAPSHOT_SUMMARY.json", "INCIDENT_EVIDENCE_GRAPH.json", "CANDIDATES.json",
                 "CANDIDATE_PROFILES.json", "AGENT_TRACE.json", "FINAL_RESULT.json", "RCA_REPORT.md",
                 "RUNTIME.json", "HASHES.json", "MANIFEST.json"):
        assert (output / name).is_file()
    assert "confidence" not in (output / "FINAL_RESULT.json").read_text().casefold()
    assert_manifest(output)


def test_poc_valid_abstention_is_not_a_technical_failure(tmp_path):
    result = run_package(package(tmp_path), tmp_path / "out", agent=agent(AbstainingModel()))
    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.public_error_code is None


def test_poc_unknown_evidence_remains_explicit_technical_failure(tmp_path):
    result = run_package(package(tmp_path), tmp_path / "out", agent=agent(UnknownEvidenceModel()))
    assert result.status == "TECHNICAL_FAILURE"
    assert result.public_error_code == "UNKNOWN_EVIDENCE_REFERENCE"
    assert not result.hypotheses


def test_poc_rejects_label_field_before_processing(tmp_path):
    source = package(tmp_path)
    manifest = json.loads((source / "manifest.json").read_text()); manifest["root_service"] = "not-permitted"
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    result = run_package(source, tmp_path / "out")
    assert result.status == "TECHNICAL_FAILURE"
    assert result.public_error_code == "INPUT_SCHEMA_ERROR"
    validation = json.loads((tmp_path / "out/INPUT_VALIDATION.json").read_text())
    assert validation["ground_truth_fields_read"] == []


def test_poc_rejects_telemetry_outside_declared_window(tmp_path):
    source = package(tmp_path)
    incident = json.loads((source / "incident.json").read_text())
    incident["start_time"], incident["end_time"] = "2030-01-01T00:00:00Z", "2030-01-01T00:01:00Z"
    (source / "incident.json").write_text(json.dumps(incident), encoding="utf-8")
    result = run_package(source, tmp_path / "out")
    assert result.status == "TECHNICAL_FAILURE"
    assert result.public_error_code == "TEMPORAL_ALIGNMENT_ERROR"


def test_poc_exact_identity_failure_is_visible(tmp_path):
    source = package(tmp_path)
    incident = json.loads((source / "incident.json").read_text()); incident["affected_service_ids"] = ["does-not-exist"]
    (source / "incident.json").write_text(json.dumps(incident), encoding="utf-8")
    result = run_package(source, tmp_path / "out")
    assert result.status == "TECHNICAL_FAILURE"
    assert result.public_error_code == "IDENTITY_RESOLUTION_ERROR"


def test_poc_pre_agent_artifacts_are_deterministic_and_read_only(tmp_path):
    first = run_package(package(tmp_path / "first"), tmp_path / "out-first", agent=agent(AbstainingModel()))
    second = run_package(package(tmp_path / "second"), tmp_path / "out-second", agent=agent(AbstainingModel()))
    assert first.status == second.status == "INSUFFICIENT_EVIDENCE"
    for name in ("EVIDENCE_SNAPSHOT_SUMMARY.json", "INCIDENT_EVIDENCE_GRAPH.json", "CANDIDATES.json", "CANDIDATE_PROFILES.json"):
        assert hashlib.sha256((tmp_path / "out-first" / name).read_bytes()).hexdigest() == hashlib.sha256((tmp_path / "out-second" / name).read_bytes()).hexdigest()
    trace = json.loads((tmp_path / "out-first" / "AGENT_TRACE.json").read_text())
    assert trace["tool_calls"] == []
    assert "canonical" not in "\n".join(path.name for path in (tmp_path / "out-first").rglob("*")).casefold()
