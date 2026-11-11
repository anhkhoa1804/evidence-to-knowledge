import json
import runpy
import socket
from pathlib import Path
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as parquet


ROOT = Path(__file__).resolve().parents[2]
R2A = runpy.run_path(str(ROOT / "tools/run_v3_phase2_10e_r2a.py"))


def test_r2a_preserves_frozen_r2_manifest_and_seven_missing_case_list():
    R2A["verify_r2_manifest"]()
    previous = json.loads((ROOT / "experiments/archive/v3_phase2_10e_r2/CASE_STATUS.json").read_text(encoding="utf-8"))
    assert [row["case_id"] for row in previous["cases"] if row["acquisition_status"] != "CACHED"] == [
        "re2ob_checkoutservice_mem_1", "re2ob_checkoutservice_socket_1", "re2ob_currencyservice_loss_1",
        "re2ob_emailservice_cpu_1", "re2ob_emailservice_delay_1", "re2ob_productcatalogservice_mem_1",
        "re2ob_recommendationservice_disk_1",
    ]


def test_r2a_reuses_valid_cache_without_network(tmp_path: Path):
    prior = R2A["fetch_file"].__globals__["CACHE"]
    try:
        R2A["fetch_file"].__globals__["CACHE"] = tmp_path
        target = tmp_path / "case-a" / "metrics.parquet"; target.parent.mkdir()
        parquet.write_table(pa.table({"time": [1]}), target)
        result = R2A["fetch_file"]("case-a", "metrics.parquet", attempts=1, timeout=1)
        assert result["status"] == "CACHED"
        assert result["method"] == "validated_local_cache"
    finally:
        R2A["fetch_file"].__globals__["CACHE"] = prior


def test_r2a_keeps_partial_file_and_classifies_timeout_explicitly(tmp_path: Path):
    prior = R2A["fetch_file"].__globals__["CACHE"]
    try:
        R2A["fetch_file"].__globals__["CACHE"] = tmp_path
        target = tmp_path / "case-b" / "traces.parquet"; target.parent.mkdir(); target.write_bytes(b"partial")
        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            result = R2A["fetch_file"]("case-b", "traces.parquet", attempts=2, timeout=1, sleeper=lambda _: None)
        assert result["status"] == "DOWNLOAD_FAILED_TIMEOUT"
        assert target.with_suffix(".parquet.part").is_file()
        assert not target.exists()
    finally:
        R2A["fetch_file"].__globals__["CACHE"] = prior


def test_r2a_distinguishes_acquisition_failures_from_candidate_results():
    assert R2A["status_for_exception"](socket.timeout("timed out")) == "DOWNLOAD_FAILED_TIMEOUT"
    assert R2A["status_for_exception"](OSError("connection refused")) == "DOWNLOAD_FAILED_CONNECTION"
