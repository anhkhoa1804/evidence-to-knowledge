# CDOI RCA POC V0 Quick Start

Use the included development-only package, or prepare a package that conforms to [the POC specification](CDOI_RCA_POC_V0_SPEC.md).

```powershell
python -m cdoi.rca_poc run data/poc_demo/incident-001 --output experiments/poc_runs/demo-001
```

This command validates and normalizes the package, checks incident-time overlap and exact service identity, builds bounded evidence/candidates/profiles, and writes an audit bundle. Without `--live`, it deliberately demonstrates the explicit `TECHNICAL_FAILURE` path because no provider is configured.

For a no-token readiness check that stops at the agent boundary, use:

```powershell
python -m cdoi.rca_poc run data/poc_demo/incident-001 --output experiments/poc_runs/demo-preflight --preflight-only
```

This creates `PREFLIGHT_ONLY.json` with the pre-live gate and never invokes a provider, a read-only tool, repair, or report-generation turn.

Current V0 `FINAL_RESULT.json` serializes the preflight wrapper as `INSUFFICIENT_EVIDENCE` but includes `PREFLIGHT_ONLY_NOT_A_SEMANTIC_ABSTENTION`; this is **not** an RCA abstention. Filter on `RUNTIME.json.execution_mode == "PREFLIGHT_ONLY"` before computing RCA-status metrics.

To use the separately qualified V2.4-style bounded live route, set the provider URL and the *name* of the environment variable holding its credential, then add `--live`:

```powershell
$env:CDOI_POC_RCA_BASE_URL = "https://configured-provider.example/v1"
$env:CDOI_POC_RCA_API_KEY_ENV = "MY_CONFIGURED_PROVIDER_KEY"
# Populate MY_CONFIGURED_PROVIDER_KEY through your approved secret store in this process.
python -m cdoi.rca_poc run data/poc_demo/incident-001 --output experiments/poc_runs/demo-live --live
```

The POC never stores credential values. It returns only `RCA_HYPOTHESIS`, `INSUFFICIENT_EVIDENCE`, or `TECHNICAL_FAILURE`. A hypothesis is not causal proof, calibrated confidence, approved knowledge, or remediation. The audit bundle’s `FINAL_RESULT.json` is the machine interface and `RCA_REPORT.md` is the concise human report.
