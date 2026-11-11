# V4 — Enterprise Evidence Integration & Pilot Readiness

Entry is **authorized with constraints** by the V3 final closure gate, not a claim that V4 has begun or that any enterprise source has been accessed. V3 remains a verified research/POC system with known residuals, not a production RCA system.

The first objective is to obtain a governed, temporally aligned real-incident evidence slice from the intended staging sources without weakening the V3 contracts. The intended responsibilities are [Coroot runtime/health/topology/tracing and Kibana application logs](CDOI_ENTERPRISE_SOURCE_BOUNDARY.md); neither endpoint, project, data view, nor credential has been verified in this closure environment.

1. **Discovery gate:** obtain authorized, scoped, read-only connection metadata and perform bounded project/data-view/field/time-coverage probes. Record provider, endpoint class, query limits, pagination and rate limits without persisting credentials or bulk records.
2. **Collector contract:** implement separately versioned, windowed, read-only, source-hashed adapters with redacted provenance and explicit partial/error states. Do not infer missing values or make silent fuzzy identity joins.
3. **Identity gate:** establish authoritative time-valid Coroot service ↔ workload ↔ instance/pod ↔ host ↔ Kibana identity mappings. Unresolved references remain unresolved.
4. **Vertical slice:** one governed incident with explicit UTC window, aligned Kibana logs, Coroot health/metrics and topology, traces/changes only if available, source hashes and no label package in inference input. Run deterministic acceptance and POC preflight first.
5. **Enterprise POC gate:** consider a bounded live agent only after accepted evidence, a separate runtime qualification and a zero-secrets prompt/tool audit. V2.4 development reliability is partial; no provider is assumed mandatory.
6. **Evaluation gate:** keep reviewed root-target labels physically separate, freeze predictions before label access, and classify pilot results separately from independent validation. Causal proof, remediation and production authorization remain out of scope.

Before a live pilot, version the POC preflight result contract so `PREFLIGHT_ONLY` cannot be miscounted as semantic abstention. Preserve retrieval ≠ selection ≠ commitment, technical failure ≠ abstention, candidate ≠ cause, trace/time ≠ causality, evidence graph ≠ canonical KG, unknown-ID fail-closed behavior, and no unapproved KG writes. Dense/QSEM, ontology calibration, causal modeling and full production HA are independent later research/product tracks, not prerequisites for read-only enterprise acquisition.
