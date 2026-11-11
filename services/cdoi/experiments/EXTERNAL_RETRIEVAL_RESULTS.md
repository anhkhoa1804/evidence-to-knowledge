# External Retrieval Results — V2.6.1

Protocol: `OAEI_FULL_CORPUS_MATCHING`. Each of 1,497 reference-backed mouse
source classes was ranked against all 3,304 human target classes. Gold targets
were read only after ranking. The normalized source/target index is persisted at
`data/benchmarks/external/oaei/anatomy-2026/normalized_full_corpus_index.json`.

| Method | N | R@1 | R@5 | R@10 | R@20 | MRR | Median Rank |
| --- | --: | --: | --: | --: | --: | --: | --: |
| R0 exact/normalized lexical | 1,497 | 0.6206 | 0.6219 | 0.6219 | 0.6226 | 0.6217 | 1 |
| R1 fuzzy lexical | 1,497 | 0.7949 | 0.8784 | 0.9058 | 0.9252 | 0.8332 | 1 |
| R2 lexical + ontology neighbourhood | 1,497 | 0.8016 | 0.8965 | 0.9178 | 0.9292 | 0.8433 | 1 |
| R3 real embedding | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| R4 lexical + embedding | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| R5 hybrid + contextual | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

R3–R5 are unavailable because the local 64-bit Python 3.12 environment raises
`OSError: WinError 1114` while loading PyTorch `c10.dll`; this is recorded as a
`RUNTIME_BLOCKER`, not a zero result. No model weights or runtime packages were
changed for this diagnostic.

The result establishes that candidate retrieval is substantially stronger than
the former reference-positive pair experiment could measure. It does not make a
claim about semantic relation selection or real dense retrieval.
