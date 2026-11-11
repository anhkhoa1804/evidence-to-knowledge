# The Graph Is a Bet, Not an Upgrade

*Part 1 of 6 — The Edge Cases of Intelligent Knowledge Systems: Retrieval, Reasoning, and Trust in Enterprise AI*

---

## The meeting everyone has had

*Illustrative example (invented).* A platform team has a large collection of internal documents, a working vector search, and a vague sense that answers are shallow. Someone says what someone always says: "Our knowledge is full of relationships. We should use a graph." Nobody objects, because the sentence sounds like common sense. A while later the team owns an extraction pipeline, a graph store, a schema argument, and a retrieval layer that beats the old system on some questions and loses on others, and nobody can say exactly which.

The sentence hid an assumption: that *relationships exist in the data, are recoverable by a machine, and matter for the questions people ask*. Each clause can fail separately. This article is about the three places it fails — and about why "GraphRAG beats RAG on multi-hop questions" is too coarse a summary to decide anything.

## First, stop saying "graph" as if it were one thing

Most arguments about graphs versus vectors are arguments about different objects. At least five are in play.

| Approach | Where does the graph come from? | What does retrieval do with it? |
|---|---|---|
| **Vector RAG** | None | Nearest-neighbour search over text chunks |
| **Hybrid RAG** | None | Embedding plus lexical (e.g. BM25) search, often with reranking |
| **KG-RAG** (RoG, G-Retriever, ToG…) | A graph that already exists | Retrieve paths or subgraphs, reason over them |
| **Microsoft-style GraphRAG** | An LLM builds it from text | Entity-level lookups plus pre-computed community summaries |
| **Graph reasoning agents** | Existing or built | A model walks the graph step by step |

The most useful distinction is between *graph construction* and *graph retrieval*. Construction is a data-engineering problem with an up-front, recurring cost and its own error rate. Retrieval is a query-time problem. A paper that shows graph *retrieval* works over a clean, curated graph (KG-RAG) says little about whether you should *build* a graph from messy documents (GraphRAG). Conflating the two is the most common way the debate goes wrong.

## What the research says

### Where graph structure was designed to help

The paper that introduced Microsoft-style GraphRAG (Edge et al., 2024; preprint) targets a specific failure of vanilla RAG: *global sensemaking* questions such as "what are the main themes in this corpus?" No small set of retrieved chunks can answer them. The authors build an entity graph, detect communities, summarise each community in advance, and answer global questions by combining those summaries. On corpora of around a million tokens they report advantages over naive RAG in the comprehensiveness and diversity of answers. These are comparisons on one kind of question, and the abstract does not claim that graphs win at pinpoint factual lookup.

### Where the comparison gets complicated

Two recent systematic comparisons ask the question more bluntly.

**GraphRAG-Bench** (Xiang et al., 2026; ICLR 2026 poster) builds tasks of increasing difficulty — fact retrieval, complex reasoning, contextual summarisation, creative generation — over a fiction corpus and a medical corpus. The authors report, under their setup, that a reranked vanilla RAG baseline is roughly level with the best graph method on simple fact retrieval, while graph methods pull ahead on complex reasoning and summarisation (figures in the table below, novel corpus). They also report indexing cost: for a single 56,000-token book, token consumption from roughly 89,000 to 655,000 across graph methods.

Some limits affect how far these numbers travel. The benchmark compares against a reranked dense baseline and includes no BM25 or hybrid baseline, so the "vector" side may be understated. It includes no unanswerable questions. The LLM judge is not named and no human validation is described. I also noted a few internal inconsistencies — one appendix table row repeats another corpus's numbers, and the text describes the setup as open-source while the experiments use GPT-4o-mini — so individual figures are best checked against the released code and data before they are reused.

**Han et al.** (2025; preprint; "RAG vs. GraphRAG: A Systematic Evaluation and Key Insights") compare on text question-answering benchmarks, with Llama-3.1-8B-Instruct as the main generator. On MultiHop-RAG, graph methods lead overall, but by a few points. The pattern by question type is more informative: among the community-based, HippoRAG2 and RAPTOR-style methods, vanilla RAG is as strong or stronger on inference-type and null (unanswerable) questions, while the community-based and HippoRAG2 methods lead on comparison and temporal questions (RAG scores far lower on temporal). On Natural Questions, plain RAG slightly leads. Construction time on MultiHop-RAG is 135 seconds for the plain RAG pipeline versus 5,560 and 7,702 seconds for the community-based and triple-extraction variants (Han et al.'s "KG-GraphRAG", which builds the graph by extracting triples from text). In their setup, only about 65% of answer entities appear in the graph that the triple-extraction method builds, for both HotPotQA and Natural Questions: roughly a third of answer entities never reach the graph. I found no BM25 baseline, and the authors discuss position bias in LLM judging.

| Study and setup | Measure | Vector RAG | Graph method |
|---|---|---|---|
| GraphRAG-Bench, novel corpus (reranked dense baseline) | Fact retrieval, accuracy | 60.92 | 60.14 (HippoRAG2) |
| | Complex reasoning, accuracy | 42.93 | 53.38 (HippoRAG2); 50.93 (Microsoft GraphRAG) |
| | Summarisation, accuracy | 51.30 | 64.40 (HippoRAG2); 64.10 (Microsoft GraphRAG) |
| Han et al., MultiHop-RAG, Llama-3.1-8B | Overall accuracy | 67.02 | 69.01 (Community-GraphRAG, local); 70.27 (HippoRAG2) |
| | Temporal questions | 30.70 | 50.60 (Community-GraphRAG, local); 49.91 (HippoRAG2) |
| | Null questions | 96.01 | 80.07 (Community-GraphRAG, local); 85.71 (HippoRAG2) |
| Han et al., Natural Questions, Llama-3.1-8B | F1 | 64.78 | 63.01 (Community-GraphRAG, local); 61.03 (HippoRAG2) |

Both columns are as reported by the papers; the two studies use different models, corpora and metrics, so numbers should not be compared across rows. In Han et al.'s MultiHop-RAG table the two triple-extraction variants score higher than plain RAG on null questions (above 97) but far lower overall, so the null result is not a clean win for vectors.

### What the two have in common

Neither paper supports "graphs are better" or "graphs are overhyped". Both support a conditional: *graph methods help on certain question types, over certain corpora, at a cost that the headline accuracy does not show.* The conditions are:

1. **The question needs connected evidence** — comparing, aggregating, or chaining facts scattered across documents.
2. **The corpus actually encodes that structure** — a narrative with recurring characters, a regulatory text with defined terms, an incident history with recurring components. A heap of independent FAQ pages has nothing for a graph to connect.
3. **Extraction can recover the structure** — if, as in Han et al.'s setup, about a third of answer entities never reach the graph, retrieval over that graph has a ceiling no reranker can lift.

## The costs nobody puts in the leaderboard

Indexing cost is reported by both papers: token spend and wall-clock time that is orders of magnitude above a vector index. But indexing is the visible cost. Three quieter ones matter more in production.

- **Maintenance.** A vector index can be refreshed by re-embedding changed chunks. A constructed graph must reconcile new entities with old ones (is "payments-svc" the same as "payment service"?), decide what a changed document does to existing edges, and re-run community summaries. The cost of *keeping the graph right* grows with change rate, and neither benchmark above models a changing corpus.
- **Extraction error as a silent filter.** A relation the extractor missed is not retrieved — and no one sees it missing. Part 2 returns to this.
- **Schema drag.** The moment you want reliable multi-hop queries, you need types and relations to be consistent. That is a modelling discipline, which costs people, not tokens. Part 4 returns to the schema.

When comparing options, budget for the *lifecycle*, not the first index: initial build, incremental update, reconciliation, and the human time spent on schema.

## The strongest counterargument

*"This is a transient accounting problem. Extraction is getting cheaper every quarter, and when graph construction costs near zero, the only question left is accuracy — where graphs win on hard questions."*

It is a serious argument, and part of it is right: token prices have fallen, and some of the quoted costs will look dated. But three things resist it. First, cost of *tokens* is not cost of *correctness*: cheaper extraction is still extraction, with a recall ceiling (Han et al.'s 65% figure, which is specific to their extraction setup, is a quality statement, not a price statement). Second, maintenance and reconciliation costs are driven by change rate and ambiguity, not by token price. Third, the counterargument assumes the hard questions are the ones users ask. In many enterprise settings, the commonest questions are lookups — "what is the procedure for X?", "who owns Y?" — where, according to both benchmarks, the vector baseline is competitive. A system tuned for the rare hard question can be needlessly expensive for the common easy one.

The fair conclusion is conditional: if your questions are dominated by global synthesis or connected-evidence reasoning, and your corpus is structurally rich, the graph bet may well pay off. The research does not tell you whether *your* questions and corpus are like that.

## What this means for design

A few practical consequences, framed as decisions rather than rules.

1. **Start from the question mix, not the technology.** Take a sample of real questions and sort them: lookup, comparison, multi-hop chain, global summary, "is this even known?". Each class has different retrieval needs.
2. **Establish the strongest non-graph baseline first.** That means hybrid retrieval with reranking, not bare cosine similarity. In the two comparisons above, the vector baseline is a dense retriever (reranked in GraphRAG-Bench) and neither study includes a BM25 or hybrid baseline, so their graph gains are measured against a dense-only baseline.
3. **Separate the experiment on retrieval from the experiment on construction.** If a pre-built, curated graph exists (a configuration database, an ontology, a product catalogue), KG-RAG is a retrieval choice. If you would have to *extract* the graph, the extraction recall is the first thing to measure.
4. **Route rather than replace.** The question-type pattern in the evidence — vector better at some, graph at others — suggests a router or hybrid, not a winner. Part 5 returns to routing, including what happens when the router sends a question down the wrong path.
5. **Price the maintenance.** Ask: when a meaningful share of documents changes next month, what happens to the graph?

## Open questions

- **Maintenance benchmarks are missing.** We have no widely used evaluation of graph methods under a changing corpus, though change is the normal state of enterprise knowledge.
- **Extraction recall is under-reported.** The comparisons reviewed here mostly report downstream accuracy. Han et al.'s measurement of how many answer entities reach the graph (about 65%, in their setup) is the exception I found.
- **Strong lexical baselines are underused.** The comparison most practitioners want — hybrid retrieval versus graph methods at equal cost — is not in the benchmarks above.
- **Unanswerable questions barely appear.** GraphRAG-Bench has none; Han et al. have a "null" category, where plain RAG scores above the community-based and HippoRAG2 methods but below the two triple-extraction variants. Whether graphs help or hurt a system's ability to say "this isn't known" is mostly unmeasured. That is the subject of the next article.

## Conclusion

A graph is a *bet* — that the knowledge has a shape, that you can recover the shape, and that the questions follow it. When the bet pays, it pays on questions that no chunk-level retriever can answer. When it fails, it fails quietly: the missing edge produces no error, only an answer that might have been better. The right question for a team is not "graph or vector?", but "what shape does our knowledge have, what questions do we ask of it, and what would we lose if the graph were wrong?"

Which brings us to the thing every graph lacks: edges that should be there and aren't.

---

> **Key takeaways**
> - "Graph" names several different designs, and graph construction and graph retrieval have different costs and failure modes.
> - In the comparisons reviewed, graph methods helped on connected-evidence and summary questions, and were roughly level with a reranked vector baseline on simple lookups, at a higher up-front cost.
> - Decide from your own question mix and the strongest non-graph baseline, and budget for the whole lifecycle, not the first index.

**Reading notes.** *Edge et al.:* abstract only; the article uses it only for what the abstract states. *GraphRAG-Bench:* setup and results tables read; the inconsistencies mentioned above come from that reading. *Han et al.:* main text and the MultiHop-RAG and Natural Questions tables read (version 3); the construction-time figures and the appendix on answer-entity coverage were checked only at summary level. The arXiv page names no venue. *Method names:* RoG, G-Retriever and ToG in the opening table are examples of KG-RAG methods and are not separately cited; HippoRAG2 and the other baselines are named as they appear in the two comparisons.

## References

- Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky, D., Ness, R. O., Larson, J. (2024). *From Local to Global: A Graph RAG Approach to Query-Focused Summarization.* arXiv:2404.16130 (v1 Apr 2024; v2 Feb 2025). **Preprint;** no venue stated on the arXiv page.
- Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. (2026). *When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation* (GraphRAG-Bench). ICLR 2026 (poster); arXiv:2506.05690 (v3, Feb 2026). Code: github.com/GraphRAG-Bench/GraphRAG-Benchmark.
- Han, H., Ma, L., Wang, Y., Shomer, H., Lei, Y., Qi, Z., Guo, K., Hua, Z., Long, B., Liu, H., Aggarwal, C. C., Tang, J. (2025). *RAG vs. GraphRAG: A Systematic Evaluation and Key Insights.* arXiv:2502.11371 (v1 Feb 2025; v3 Mar 2026). **Preprint;** no venue stated on the arXiv page. Code: github.com/haoyuhan1/RAGvsGraphRAG.
