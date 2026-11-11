from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .pipeline import ContinualIntegrationPipeline, demo
from .preprocessing import preprocess
from .experiment_runner import ExperimentManifest, ExperimentRunner
from .model_config import OpenAICompatibleConfig, dotenv_state, load_dotenv_file
from .model_probe import probe_gateway
from .raw_preprocessing import PreprocessingError, process_dataset, write_artifacts
from .evidence_schema import EvidenceSchemaInducer, induction_diagnostics


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _result_payload(result):
    return {"domain": result.domain, "run_id": result.run.run_id, "new_concepts": sum(1 for proposal in result.proposals if proposal.action.value == "ADD_CLASS"), "reused_or_placed": sum(1 for proposal in result.proposals if proposal.action.value in {"ADD_SUBCLASS", "ADD_MAPPING", "NO_CHANGE"}), "rejected_or_review": sum(1 for proposal in result.proposals if proposal.status not in {"accepted", "proposed"}), "staging_facts": result.staging_count, "versions": result.accepted_versions, "bridge_proposals": [proposal.model_dump(mode="json") for proposal in result.bridge_proposals], "alignments": [{"source": decision.source_concept, "relation": decision.relation.value, "target": decision.target_concept, "confidence": decision.confidence, "kind": decision.candidate_kind.value} for decision in result.decisions]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cdoi", description="Cross-domain continual ontology integration prototype")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo_parser = subparsers.add_parser("demo")
    demo_parser.add_argument("--order", nargs="+", help="Domain ingestion order")
    preprocess_parser = subparsers.add_parser("preprocess")
    preprocess_parser.add_argument("path", type=Path)
    preprocess_parser.add_argument("--output", type=Path, help="Write versioned raw-evidence artifacts for a dataset manifest.")
    preprocess_parser.add_argument("--dry-run", action="store_true", help="Validate and count a dataset manifest without writing artifacts.")
    ingest_parser = subparsers.add_parser("ingest")
    ingest_parser.add_argument("domain")
    ingest_parser.add_argument("path", type=Path)
    experiment_parser = subparsers.add_parser("experiment", help="Run a serializable V2 experiment manifest.")
    experiment_parser.add_argument("manifest", type=Path)
    model_parser = subparsers.add_parser("model", help="Inspect optional remote model connectivity.")
    model_parser.add_argument("action", choices=["probe"])
    for name in ("extract", "align", "validate", "review", "commit", "promote", "evaluate"):
        subparsers.add_parser(name, help=f"Use '{name}' through the deterministic demo in V1.")
    args = parser.parse_args(argv)
    root = project_root()
    dotenv_before = None
    if args.command in {"experiment", "model"}:
        api_key_env = os.environ.get("CDOI_LLM_API_KEY_ENV", "DMP_MERCURY")
        dotenv_before = dotenv_state(api_key_env, root / ".env")
        load_dotenv_file(root / ".env", override=False)
    if args.command == "preprocess":
        if args.output or args.dry_run:
            try:
                result = process_dataset(args.path)
                induced = EvidenceSchemaInducer().induce(result)
                payload = {"schema_version": "cdoi_preprocessing_v1", "dataset_id": result.manifest.dataset_id, "counts": {"raw_records": len(result.raw_records), "entities": len(result.entities), "relations": len(result.relations), "events": len(result.events), "changes": len(result.changes), "metrics": len(result.metrics), "traces": len(result.traces), "semantic_terms": len(result.semantic_terms), "unresolved": len(result.unresolved)}, "schema_induction": induction_diagnostics(induced, result), "dry_run": args.dry_run}
                if not args.dry_run:
                    if not args.output:
                        raise PreprocessingError("INVALID_MANIFEST: --output is required unless --dry-run is used")
                    payload["artifact_manifest"] = write_artifacts(result, args.output)
                print(json.dumps(payload, indent=2))
                return 0
            except PreprocessingError as exc:
                print(json.dumps({"status": str(exc)}))
                return 2
        print(json.dumps([{"text": chunk.text, "source_span": chunk.reference.source_span, "hierarchy": chunk.reference.hierarchy} for chunk in preprocess(args.path)], indent=2))
        return 0
    if args.command == "ingest":
        result = ContinualIntegrationPipeline(root).ingest(args.path, args.domain)
        print(json.dumps(_result_payload(result), indent=2))
        return 0
    if args.command == "demo":
        results, promotions, kg_path = demo(root, args.order)
        report = {"ontology_versions": [version.name for version in sorted((root / "data" / "ontology_versions").glob("v[0-9][0-9][0-9]"))], "stages": [_result_payload(result) for result in results], "promotion_proposals": [proposal.model_dump(mode="json") for proposal in promotions], "knowledge_graph": str(kg_path)}
        print(json.dumps(report, indent=2))
        return 0
    if args.command == "experiment":
        manifest = ExperimentManifest.load(args.manifest)
        runner = ExperimentRunner(root)
        if manifest.task == "continual_evolution":
            domains = manifest.ingestion_order or ["distributed_systems", "commerce", "logistics", "finance", "fintech", "telecom"]
            orders = runner.sampled_orders(domains, manifest.order_count, manifest.random_seed)
            result = runner.run_continual(manifest, orders)
        elif manifest.task == "downstream":
            result = runner.run_downstream(manifest)
        else:
            result = runner.run(manifest)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "model":
        config = OpenAICompatibleConfig.from_environment("process_environment_with_dotenv_fallback_override_false")
        print(json.dumps({"configuration": config.public_metadata(), "probe": probe_gateway(config, environment=dotenv_before, basic_only=True).as_dict()}, indent=2))
        return 0
    print(json.dumps({"command": args.command, "status": "interface_present", "message": "Run 'cdoi demo' for the V1 end-to-end workflow."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
