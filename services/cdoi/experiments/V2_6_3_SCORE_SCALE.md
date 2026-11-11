# V2.6.3 Diagnostic — R2 Score Scale

## Implementation map

In `oaei_full_corpus.py`, R1 is lexical similarity. R2 is the fixed evaluation
formula `0.8 * lexical + 0.2 * context`. These are similarity/retrieval scores,
not calibrated probabilities. The frozen emitter compares the R1 top-candidate
score with 0.82. The V2.6.3 reranker evaluates R2 separately over that fixed
candidate set; it does not change the emitter.

## Measured distributions

| Population | N | Mean lexical | Mean context | Mean R2 combined | Mean context delta |
| --- | --: | ---: | ---: | ---: | ---: |
| Gold candidate in R1 Top-20 | 1,385 | 0.8961 | 0.2243 | 0.7618 | -0.1344 |
| Rank-1 emitted true positive | 1,015 | 0.9887 | 0.2263 | 0.8362 | -0.1525 |
| Rank-1 abstained true positive | 175 | 0.6989 | 0.1988 | 0.5989 | -0.1000 |
| Wrong R1 top candidate | 307 | 0.6909 | 0.1413 | 0.5810 | -0.1099 |

`context_delta` is R2 combined minus lexical. It is negative in these groups
because the fixed 0.8/0.2 aggregation replaces part of a generally higher
lexical score with lower context similarity. That is a scale effect of the
formula, not evidence that contextual information is absent or harmful.

## Diagnostic interpretation

R2 improves fixed-corpus candidate ordering, but direct comparison of its
combined score to the R1-oriented 0.82 emitter threshold is not meaningful.
The code currently supplies a score for retrieval relevance and the frozen
experiment uses a top-candidate score for commitment. V3 should test a distinct
semantic-confidence model only after this evidence is reviewed; none is added
here.
