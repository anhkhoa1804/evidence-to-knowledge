# V2.6.2 Diagnostic — Non-trivial Anatomy Mappings

Non-trivial uses the existing V2.6.1 definition exactly: normalized source and
gold target labels differ. The R1 subset has N=568.

| Method | N | R@1 | R@5 | R@10 | R@20 | MRR | Emitted P | Emitted R | F1 | Abstention | Wrong target |
| --- | --: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| R0 exact/normalized lexical | 568 | 0.0000 | 0.0035 | 0.0035 | 0.0053 | 0.0029 | 0.0000 | 0.0000 | 0.0000 | 0.9842 | 0.0158 |
| R1 fuzzy lexical | 568 | 0.4595 | 0.6796 | 0.7518 | 0.8028 | 0.5603 | 0.7049 | 0.1514 | 0.2493 | 0.7852 | 0.0634 |
| R2 lexical + ontology neighbourhood | 568 | 0.4771 | 0.7271 | 0.7835 | 0.8134 | 0.5871 | 0.5556 | 0.0176 | 0.0341 | 0.9683 | 0.0141 |

R2 improves non-trivial retrieval versus R1 (R@10 0.7835 vs 0.7518), but its
frozen contextual emission distribution is substantially more conservative
(emitted recall 0.0176 vs 0.1514). This does not establish a semantic advantage
or disadvantage: it establishes that contextual retrieval and emitter scoring
must be compared on identical candidates before making that claim.

## Diagnostic interpretation

Easy lexical mappings dominate overall figures. The non-trivial subset has much
weaker retrieval and especially weak emitted recall, so V3 evidence should first
target candidate reranking/semantic selection on shared Top-K lists rather than
changing global acceptance policy.
