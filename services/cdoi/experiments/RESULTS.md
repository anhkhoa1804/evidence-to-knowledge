# V2 Controlled Results

These results come from the committed synthetic CDOI-Bench fixture and deterministic rules. They are evidence that the experimental harness distinguishes its own controlled variants; they are not evidence of general semantic-integration performance.

| Run | Held-out accuracy | False merge rate | Equivalence precision | Bridge precision |
| --- | ---: | ---: | ---: | ---: |
| B0 lexical | 0.214 | 0.333 | 0.250 | 0.000 |
| B6 full deterministic CDOI | 0.929 | 0.000 | 1.000 | 1.000 |

The full run missed one held-out unresolved case, yielding unresolved accuracy of 0.75. Its bootstrap accuracy interval on the small fixture was 0.786 to 1.000 across 200 deterministic resamples; this is descriptive only.

The four configured ingestion orders produced decision stability 1.0, bridge stability 1.0, promotion stability 1.0, and false-merge growth 0 on the deterministic fixture. The controlled business-impact fixture yielded full-CDOI impact F1 of 1.0 versus 0.75 for domain-only and bridge-removed variants. This fixture is constructed to test connectivity and explanation-path handling, so external benchmark and real-data evaluation remain necessary.
