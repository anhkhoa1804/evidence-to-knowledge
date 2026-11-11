# CDOI V3 final snapshot — 2026-09-28

This is the current handoff for Cross-Domain Continual Ontology Integration. It supersedes dated “current context” documents, but does not rewrite frozen history. V3 closes as `V3_FINAL_STATE_VERIFIED_WITH_RESIDUALS`; V4 entry is `V4_ENTRY_AUTHORIZED_WITH_CONSTRAINTS` for **enterprise evidence acquisition only**, not V4 implementation or production RCA.

## Purpose, architecture and authorities

CDOI integrates semantic ontology proposals while separately investigating operational incidents through bounded evidence. Ontology retrieval → CandidateSet → selection → commitment evidence → review/version gate remain separate. Operational raw sources → normalization/lineage → EvidenceSnapshot → IncidentEvidenceGraph → H1/H5 candidates → CandidateEvidenceProfiles → read-only RCA agent/report remain separate from the canonical KG. The POC V0 CLI packages a single incident through this operational path. Current executable source/tests outrank hash-verified frozen measured artifacts; the matrix and contracts index them; older handoffs are dated history. See the closure archive's authority and claim registry.

## Current measured and implemented state

| Branch | Verified state | Boundary |
| --- | --- | --- |
| Ontology | Relation-aware STW–TheSoz proposal experiment is frozen and hash-verified; exact mapping evidence is scoped | Broad/narrow/related auto-selection unsupported; Dense unqualified; confidence uncalibrated; no production routing/commitment |
| RCA V2.4 | 12 consumed opaque-ID RCAEval development cases: 4 hypotheses, 6 valid abstentions, 2 technical failures; Top-1 and hypothesis-only Top-3 4/12; 6/6 synthetic live repair probes | Not independent validation, causal proof, calibrated confidence or production reliability |
| POC V0 | Current CLI help, demo deterministic preflight and no-provider run executed; preflight writes audit and invokes no provider; no-provider run fails explicitly | Preflight public status is `INSUFFICIENT_EVIDENCE` but marked `PREFLIGHT_ONLY_NOT_A_SEMANTIC_ABSTENTION`; exclude from RCA abstention metrics |
| VDT | Current source hashes equal frozen delivery; 100 incidents, 36 valid/exact IDs, 0 aligned logs/metrics/traces/changes, 36 usable topology contexts, 0 eligible packages | No governed root labels; not an RCA-evaluable enterprise dataset |
| Enterprise sources | Coroot and Kibana intended responsibilities are documented | No endpoint/access config, connectivity, project/data-view discovery, acquisition or acceptance verified here |

The current full suite passed **319/319**, zero failed/skipped; the post-cleanup JUnit and exact command are in `FINAL_REGRESSION.json`. The 319 figure is current, while 305 and 312 remain correct only for their historical milestones. The listed hashes recomputed cleanly for ontology (20), V2.4 (118), POC (89), VDT primary (21), VDT completion (6), V2.3 blocker resolution (350) and Phase 2.11 (34). Phase 2.13's 26 listed hashes verify but five extras are not in its hash manifest. Protected Phase 2.12 case material was not opened; only root manifest file hashes were recorded.

## Data, security and safety boundaries

The executable POC contract requires exact incident/service IDs, explicit timezone-qualified windows, supported constrained source schemas, overlap checks, source hashes and label-field rejection. The acquisition specification and VDT request demand separate evidence and governed-label deliveries. Coroot is intended for runtime inventory/health/topology/traces and Kibana for application logs; neither supplies root-cause truth merely by being a telemetry source. Missing identity/time/source provenance remains unresolved, not inferred.

Current mutable `docs/src/tools` text scan found no candidate literal credentials under its heuristic; ignored local `.env` contents were not opened. This is a scoped hygiene result, not a full historical secret audit. Credentials must remain in secure read-only source/provider configuration and never enter prompts, snapshots, reports, audit bundles or committed files. No live model, embedding, bulk source crawl or generation-token use occurred in this closure. Local deterministic VDT/POC metadata records zero provider interactions; external billing was not queried.

The following remain frozen: retrieval ≠ selection ≠ commitment; entity resolution ≠ ontology alignment; technical failure ≠ semantic abstention; candidate ≠ cause; trace path and temporal precedence ≠ causality; IncidentEvidenceGraph ≠ Canonical KG; LLM proposal ≠ approved mutation; unknown IDs fail closed; GT stays outside inference; exact identity is preferred with no silent fuzzy merge. Review/version gating protects canonical writes. No automatic remediation or KG write path is authorized by the RCA POC.

## What remains unknown or blocked

The dominant next-workstream blocker is an accepted enterprise incident package with aligned evidence, exact time-valid identity and source provenance. VDT needs overlapping logs and separate governed labels; metrics/traces/changes would enrich it but are not all mandatory for first preflight. Staging access must be supplied and verified before read-only acquisition. V2.4 still has two technical failures in 12 development cases, independent RCA validation is absent, and claim-level causal support is not established. Dense, non-equivalence selection and commitment calibration remain separate ontology research gaps. None of these may be silently treated as solved by V4 entry.

## Repository and transition

The tree is **dirty, uncommitted and accounted with some entries requiring owner review**; closure did not reset or delete user work. The 2026-09-25 master context is historical, not current authority. V4 may start only with bounded, authorized Coroot/Kibana metadata discovery and secret isolation, then an exact lineage-preserving one-incident vertical slice and deterministic POC preflight. [V4 entry plan](../V4_ENTRY_PLAN.md) is documentation, not implementation. V4 must not reinterpret V3 negative results, open protected Phase 2.12 cases, assume provider/enterprise connectivity, count preflight as abstention, or claim production readiness.
