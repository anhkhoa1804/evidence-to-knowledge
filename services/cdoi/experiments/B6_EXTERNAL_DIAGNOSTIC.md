# B6 External Diagnostic — V2.6.1

The archived V2.6 result is retained unchanged under
`experiments/archive/v2_6_baseline_20260917/`. Its protocol is now named
`OAEI_POSITIVE_PAIR_DIAGNOSTIC`: it supplied a reference pair directly and has
no target-corpus retrieval or negative correspondence set.

| Archived outcome | Count |
| --- | --: |
| Positive reference pairs | 7,580 |
| B6 equivalence decisions | 0 |
| Class-relation errors (`NEW_CONCEPT`) | 7,050 |
| False unresolved | 530 |

The prior artifact records predictions and aggregate taxonomy but does not
persist source/target profile signals; reconstructing 50 signal rows would
require rerunning a different, gold-pair protocol and would not answer the
full-corpus matching question. V2.6.1 therefore preserves this result as a
historical acceptance/abstention diagnostic and uses the new corpus protocol for
retrieval versus selection separation.

For the fair R1 run, 112/1,497 reference classes were retrieval misses at
Top-20, 342 were threshold abstentions despite their gold candidate being in
Top-20, and 28 selected a wrong candidate from an available Top-20. Thus the
largest measured external loss in the frozen lexical chooser is conservative
acceptance/calibration rather than retrieval. This is diagnostic evidence only;
no CDOI score weight or threshold was changed.
