"""Optional generated 150k-span SQLite indexing stress check; no benchmark score."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cdoi.operational_context import assemble_context, load_incident_windows
from cdoi.raw_preprocessing import NormalizedTraceSpanEvidence, process_dataset
from cdoi.scalable_evidence import IncidentEvidenceStore, ResourceConfiguration

def main() -> None:
    fixture = ROOT / "tests/fixtures/preprocessing_demo"
    result = process_dataset(fixture / "manifest.yaml")
    incident = load_incident_windows(fixture / "incidents/incidents.csv")[0]
    context = assemble_context(result, incident)
    database = ROOT / "data/benchmarks/external/rcaeval/r1_indexes/stress_150k.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists(): database.unlink()
    store = IncidentEvidenceStore(database, context, resource_configuration=ResourceConfiguration(1000, 1000))
    def spans():
        for index in range(150000):
            evidence = f"stress-{index:06d}"
            yield NormalizedTraceSpanEvidence(evidence, "R1_STRESS", f"trace-{index // 3}", f"span-{index}", None, "payment-service", None, "2026-09-18T10:00:00Z", "2026-09-18T10:00:00Z", "2026-09-18T10:00:00Z", None, 1.0, "DERIVED_FROM_DURATION", "ERROR" if index % 1000 == 0 else "OK", None, None, None, "RESOLVED_EXACT_ID", "ROOT", MappingProxyType({}), MappingProxyType({"raw_evidence_id": evidence, "source_file": "generated_stress"}))
    started = time.perf_counter(); inserted = store.add_trace_spans(spans()); elapsed = time.perf_counter() - started
    output = {"schema_version": "v3_phase2_10e_r1_stress_v1", "generated_spans": 150000, "inserted_spans": inserted, "indexed_spans": store.trace_count(), "wall_seconds": elapsed, "sqlite_bytes": database.stat().st_size}
    store.close()
    (ROOT / "experiments/archive/v3_phase2_10e_r1/STRESS_150K.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
