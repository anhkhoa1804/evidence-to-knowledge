# V2.6.5 Diagnostic — Identical-Prompt Qwen Consistency and Reliability

Twenty difficult cases from the frozen validation order were called three times
each with identical prompt, candidates, temperature, schema, and budget. The
60-call consistency portion produced 56 candidate-valid outputs (0.9333): 46
valid selections, 10 semantic abstentions, and 4 empty technical responses.

Among valid outputs, mean per-case same-candidate and same-relation rates were
both 1.0000; there were no cases with more than one selected candidate. Modal
selection accuracy was 0.7500. This shows stable selections when a valid answer
is returned, but does not erase the technical-invalid fallback requirement.

The separate repeat of the three V2.6.4 final-empty source cases produced one
valid selection and two further empty responses. This small recheck indicates
that empty outputs are partly transient but may also be case/prompt-sensitive.

For the N=150 validation: 164 calls served 150 cases; final failures were seven
empty responses (HTTP 200, zero content, `finish_reason=length`) and one HTTP
502 transport error. There were no JSON, schema, out-of-candidate, or
truncation-with-content failures. Mean case latency was 3,953.4 ms, median
2,358.0 ms, and p95 15,869.7 ms. No authorization or token was persisted.
