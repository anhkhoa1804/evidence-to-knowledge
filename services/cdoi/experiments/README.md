# Experimental Framework

Experiment manifests are committed under `experiments/configs`. `ExperimentRunner` persists a separate result directory containing the manifest, dataset metadata/hash, calibration output, predictions, metrics, bootstrap interval, operational counters, and a compact Markdown report.

The deterministic baselines are B0 lexical, B1 embedding signal, B2 lexical plus embedding, B3 structural context, and B6 full conservative CDOI. B4/B5 are optional LLM variants: they require configured adapters and cached structured outputs, and are not required by tests.

`continual_orders.yaml` exercises four isolated ingestion orders. `downstream.yaml` evaluates a deliberately synthetic, controlled impact/RCA/query fixture across raw, extracted, domain-aligned, full-CDOI, and full-without-bridge variants. It is a development experiment, not evidence of real enterprise impact.
