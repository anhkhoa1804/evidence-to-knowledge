# Research Notes

The working hypothesis remains: persistent modular cross-domain ontology integration can be made safer by combining context-aware alignment, symbolic validation, conservative merge policy, explicit bridge mappings, and reviewable promotion. This is a research hypothesis, not a novelty claim.

## V1 research framing

V1 differs from V0 in three material ways. First, it distinguishes observed ABox entities from induced TBox classes and properties. Second, it treats a cross-domain bridge, a reusable-core promotion, and semantic equivalence as different proposal types. Third, it makes canonical KG population depend on an approved schema version, retaining non-approved observations in staging.

The compact gold benchmark and multi-order experiment enable falsifiable measurements of alignment accuracy, property alignment, bridge precision, promotion precision, false-merge rate, duplicate count, review rate, and order sensitivity. They are fixtures, not evidence of external enterprise performance.

## Related systems

AutoSchemaKG motivates contextual conceptualization and schema induction; CDOI adds ABox/TBox separation, persistent run state, and governed integration. OntoAligner motivates transparent retrieval and evaluation separation; CDOI keeps retrieval scores visible and does not reuse its runtime stack. DeepOnto motivates optional reasoning adapters; V1 uses a portable RDFLib taxonomy reasoner plus pySHACL, avoiding mandatory Java infrastructure.

OntoEKG provides a construction baseline; CDOI's added question is safe stateful integration over successive bounded contexts. LLMs4OL and LM ontology concept placement motivate future benchmark expansion. The EDC Extract-Define-Canonicalize framing motivates retrieval followed by canonicalization, but no unofficial EDC code is used.

Semantic Arts gist remains the immutable external foundation adapter. FIBO and GS1/EPCIS remain optional references rather than automatic truth sources or default runtime imports. All upstream checkouts remain read-only under `research/upstream`; licensing and commit details are retained in `research/UPSTREAM_NOTES.md`.

## Limitations and questions

The mock conceptualizer, hashing embedding baseline, synthetic bridge detector, and lightweight reasoner are deterministic scaffolding, not semantic-performance claims. Future work should calibrate retrieval and review thresholds against external gold corpora, compare local embeddings and structured LLM models, add DL reasoner adapters, evaluate human reviewer agreement, and study whether bridge evidence improves promotion precision without increasing false merges.

## V2 Experimental Validation

V2 makes the hypothesis testable rather than asserting it: CDOI-Bench includes hard negatives, development/test separation, property and bridge cases, promotion cases, and continual-order runs. Calibration is performed only on the development split, with false-merge rate prioritized over equivalence recall. Reports include bootstrap intervals for deterministic benchmark accuracy but should not be interpreted as statistical significance on a small synthetic benchmark.

The downstream fixture isolates what bridge connectivity contributes by comparing domain-aligned and full-without-bridge variants against full CDOI. Neutral or negative external benchmark results would be reported as such. External OET/OAEI/LLMs4OL/RCA datasets are not bundled and require license-aware setup; V2 therefore enables, but does not yet claim, external comparative validation.

## V2.5 External and Failure-Driven Evaluation

V2.5 treats controlled CDOI-Bench results as proof of mechanism only. Its external adapters, evidence-degradation/noise transformations, late-evidence traces, structural order comparisons, selective-prediction metrics, and failure taxonomy are intended to expose where the current hypothesis fails. Missing external data or model access is recorded as an unavailable experiment rather than converted into a synthetic claim. Any V3 priorities must be derived from observed failure counts, not from fixture scores alone.

## V2.6 External Execution

V2.6 executes OAEI Anatomy through a pair-level reference-positive protocol and records the result separately from controlled CDOI-Bench. This is insufficient for standard OAEI precision or retrieval analysis because the adapter receives no target-corpus retrieval task and no negatives. The observed gap is therefore a failure signal that motivates a fair candidate-retrieval evaluation protocol, not a claim about general ontology matching quality. Qwen and sentence-transformer integrations remain optional: remote credentials and compatible local ML runtimes are prerequisites for their empirical results, while their adapters and safety boundaries are covered offline.
