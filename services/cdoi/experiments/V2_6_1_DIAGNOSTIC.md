# CDOI V2.6.1 Diagnostic External Evaluation

## Baseline

V2.6 reports were archived before V2.6.1 evaluation in
`experiments/archive/v2_6_baseline_20260917/`. The deterministic demo and
existing safety invariants are unchanged. The former Anatomy result remains
`OAEI_POSITIVE_PAIR_DIAGNOSTIC`, not a matcher precision/F1 result.

## Environment and model status

Configuration is loaded once at the CLI configuration boundary with
`load_dotenv(..., override=False)`: process environment values take precedence;
tests need no `.env`; `.env` and `.env.local` are ignored; and public metadata
contains only credential presence, not token content. `openai-compatible` is
configuration metadata; the active adapter is the repository's HTTP
OpenAI-compatible transport.

The company Qwen probe executed successfully with the private-IP transport and
`Host: <llm-gateway-host>`: credential visible, `/models` 200, chat 200, model
accepted, JSON prompt supported, `response_format` supported, and schema-valid
semantic JSON supported. The basic request intentionally contains only model,
messages, temperature, and max_tokens. The response diagnostic never stores
Authorization.

## Fair full-corpus protocol

`OAEI_FULL_CORPUS_MATCHING` extracts labels, aliases, definitions/comments,
parents, children, and lightweight property neighbourhoods for both Anatomy
ontologies. It indexes 2,744 source and 3,304 target classes, retrieves from
the complete target corpus without gold injection, then evaluates gold rank,
fixed chooser emission, abstention, and final predicted correspondences.

## Retrieval and conditional alignment

See [EXTERNAL_RETRIEVAL_RESULTS.md](EXTERNAL_RETRIEVAL_RESULTS.md). For R1,
gold retrieval is R@10=0.9058 and R@20=0.9252. Fixed-emitter selection accuracy
conditioned on gold availability is 0.8529 at Top-1, 0.7719 at Top-5, 0.7485 at
Top-10, and 0.7329 at Top-20. All reference relations are equivalence, so this
is also relation accuracy conditional on a retrieved gold candidate.

## Full alignment and failure taxonomy

R1 emitted 1,051 mappings with precision 0.9657, recall 0.6780, F1 0.7967, and
446 abstentions. Its non-trivial (different normalized labels) recall is
0.1514. The mutually exclusive failure counts are 112 `RETRIEVAL_MISS`, 342
`THRESHOLD_ABSTENTION`, and 28 `GOLD_IN_TOPK_WRONG_TARGET_SELECTED`.

## Calibration and missing-evidence diagnosis

The condition is `C0_ZERO_SHOT_SYNTHETIC_CALIBRATED`: no OAEI labels were used
to choose the 0.82 frozen emitter threshold. The external contextual retrieval
score treats absent context as unavailable signal rather than inventing a zero
similarity; no production score aggregation, threshold, or semantic-core weight
was changed. A threshold sweep or available-feature renormalization must remain
an explicitly separate diagnostic before any policy change.

## Embedding, Qwen, OET, and RCAEval

Embedding retrieval is blocked by Windows PyTorch `c10.dll` initialization
(`RUNTIME_BLOCKER`; Python 3.12.7, 64-bit). No clean CPU/WSL runtime was
provisioned in this repository. A bounded Q0 Qwen reranking check was executed
on one non-trivial source plus its R1 Top-5 candidates (the gold target was not
included in the prompt): the first 512-token response was a `MODEL_PARSE_ERROR`
and the single 1,024-token retry produced valid JSON, chose the retrieved gold
candidate, and selected `EQUIVALENT`. Thus N=1, call count=2, parse/retry rate
0.5, and conditional selection accuracy=1.0 for this diagnostic case only; it
is not a general Qwen score. OET and RCAEval remain `DATA_MISSING`/
license-dependent and do not block this diagnosis.

## Recommended next step

Retrieval is not the dominant observed R1 limitation: only 7.48% of gold pairs
are absent from Top-20, whereas threshold abstention accounts for 22.85% of all
reference cases. Before V3, run a held-out threshold/available-evidence sweep,
then compare frozen deterministic selection and Qwen selection on identical
saved Top-K candidate sets at meaningful N. Obtain a clean CPU or WSL embedding
runtime before claiming any R3–R5 result.
