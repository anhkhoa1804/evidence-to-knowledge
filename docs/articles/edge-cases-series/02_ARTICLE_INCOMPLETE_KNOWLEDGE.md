# The Edge That Isn't There

*Part 2 of 6 — The Edge Cases of Intelligent Knowledge Systems: Retrieval, Reasoning, and Trust in Enterprise AI*

---

## A question with no answer in the store

Part 1 ended with a quiet failure: a missing edge produces no error. Let us follow that failure to its conclusion.

*Illustrative example (invented).* A service graph records that `checkout` calls `payments`, and `payments` depends on `ledger-db`. An engineer asks: "If `ledger-db` goes down, which customer-facing services break?" The graph says: `payments`, and through it `checkout`. The answer is clean, confident, and cited. What the graph does not contain is a nightly reconciliation job, added last quarter by a team that never updated the service catalogue, which also reads from `ledger-db` and feeds the invoicing page. The answer is *incomplete*, and nothing in it says so.

Retrieval systems are built to find what is there. This article is about what they do with what isn't — and about why "I don't have enough information" is a harder capability than it sounds.

## The assumption: the store is a faithful mirror

Almost every retrieval pipeline treats the store as if it were a complete mirror of the domain. Retrieve, rank, answer. When the answer is absent, the pipeline does not notice; it hands the generator the nearest thing it has.

Logic has had a name for this for decades. In the **closed-world assumption** (Reiter, 1978), whatever the database does not state is taken to be false. In an **open-world** reading, whatever it does not state is simply *unknown*. Both are legitimate; they describe different contracts between a database and the world. The failure in most deployed RAG systems is that they adopt neither explicitly. They behave as closed-world when answering ("it isn't listed, so it doesn't exist") and as open-world when explaining ("based on the available information…"), and the user cannot tell which one they are getting.

## "Not there" comes in several kinds

The closed-world shortcut treats every missing assertion as a negative one. They are different things, and it helps to line them up. The first three rows below share one feature: the store says nothing at all.

| Situation | What is true in the world | What the store contains | Right behaviour |
|---|---|---|---|
| **Missing** | The relation holds | No assertion | Ideally retrieve it; at least flag the gap |
| **Unknown** | Undetermined; nobody has established it | No assertion | State that it cannot be established |
| **Truly absent** | The relation does not hold | No assertion | Answer "no" only if the relation is known to be recorded exhaustively |
| **Explicitly negated** | The relation does not hold | A negative assertion with provenance ("A does not call B, verified on a given date") | Answer "no", citing the assertion, while it is still current |
| **Wrongly asserted** | The relation does not hold | A positive assertion that is false | Not an incompleteness problem; it is a validity problem (Part 3) |

From inside the store, the first three rows are indistinguishable: an absent assertion is just an absent assertion. What separates them is *evidence about the evidence*: Was this part of the domain ever surveyed? Is this relation type one we record exhaustively? Who is responsible for keeping it complete? The fourth row is different in kind. An explicit negative assertion is itself a claim, with a source and a date, and it is the only row that counts as *evidence of absence*. The fifth row is not silence at all.

That is why **absence of evidence is not evidence of absence** becomes an engineering requirement rather than a slogan. A system that reads a missing assertion as a negative one has silently moved from the first three rows to the fourth, and will confidently misreport.

## What the research says

### BRINK: measuring what happens when edges go missing

The most direct recent study I found is **BRINK** (Zhou et al., EACL 2026), which asks how knowledge-graph RAG systems behave when part of the graph is removed. The design is careful about one thing that earlier work was not: *which* facts to remove.

The authors take graphs and mine logical rules from them using AMIE3 — for example, a rule that says two people sharing a parent are siblings. They then remove *head* triples (the conclusions of a rule) while keeping the *body* triples (the premises). The removed fact can then, in principle, still be inferred from what remains. This lets the benchmark separate "the answer is truly gone" from "the answer is reachable through reasoning". Questions are then generated for the removed facts over three datasets — one synthetic family graph (2,165 questions), one derived from Freebase (FB15k-237, 5,449), and one from Wikidata (Wikidata5m, 34,651). Six KG-RAG methods are tested (RoG, G-Retriever, GNN-RAG, PoG, StructGPT, ToG).

Under the authors' setup, performance drops noticeably in most cases when the graph is made incomplete, as measured both by standard answer overlap and by metrics (Hits@Hard and the Hard Hits Rate) that focus on answers *only* reachable through reasoning. In the paper's own terms, "training-based" methods (its examples are RoG and GNN-RAG) show a smaller drop in the Hard Hits Rate — the share of correct answers that include a hard answer — than "non-trained" ones (its examples are PoG and ToG) when direct evidence is removed. G-Retriever, which is also trained on each dataset, is described as a separate case with similarly low performance on complete and incomplete graphs, and StructGPT is not singled out. An appendix attributes roughly seven in ten failures to retrieval and three in ten to reasoning, averaged across datasets and models.

### The label effect: models may not be reading the graph

One of BRINK's more provocative results concerns *names*. The authors compare three versions of the same graph: with real text labels for entities, with opaque entity identifiers, and with private random identifiers. Text labels significantly boost performance; entity IDs perform about as well as random IDs. The authors interpret this as the language model leaning on its *own* knowledge of the named entities.

This has a consequence rarely discussed. In a public knowledge graph, a system can score well partly because the model already knows the facts, and incompleteness is masked by memory. In an *enterprise* graph, where service names, internal codes and team structures were probably never in any pretraining corpus, no such backstop exists. Public-benchmark robustness to missing edges may therefore *overstate* enterprise robustness. That is an inference from the label experiment, not a result the paper measures on enterprise data.

### What BRINK does not do

BRINK is the right foundation for this article, but it should not be asked to carry weights it was not built for.

- **It does not evaluate abstention.** The study measures whether the system finds the right answer; it does not measure whether the system *declines* when the answer is unrecoverable. Hallucination is discussed only qualitatively (in a table of illustrative cases).
- **Incompleteness is simulated.** Facts are removed by rule-based selection from a graph assumed to be complete, so ground truth is closed-world by construction. A different preprint (Liu et al., arXiv:2511.12208) states, as motivation in its abstract, that existing incomplete-KGQA datasets simulate incompleteness by removing triples at random, and builds its own dataset from real-world knowledge updates instead. I used it only for that point.
- **Horn rules only.** The kinds of facts that can be removed and still be inferable are limited to what Horn rules capture.
- **Not independent of the evidence in Part 4.** BRINK and the SCAIR paper discussed there share five authors, and a related preprint on KG-RAG under incompleteness (arXiv:2504.05163) is by largely the same group. So agreement among them is not independent confirmation.

### Abstention as a research area

The broader literature does treat the ability to decline as a first-class problem. A survey in *Transactions of the ACL* (Wen et al., 2025) frames abstention through the query, the model and the human-values perspective: some queries are unanswerable, some exceed the model's knowledge, and some should not be answered for safety or fairness reasons. The survey is a map of a field, not a measurement of RAG systems on enterprise knowledge, and it is mostly about unaided language models; how its techniques transfer to retrieval over a store is a separate, less-studied question.

Among the retrieval benchmarks reviewed in this series, abstention is rarely what is measured, so the evidence on whether graphs help or hurt a system's ability to decline is thin and mixed. BRINK does not measure it, and GraphRAG-Bench (Part 1) has no unanswerable questions. The partial exceptions score declining only as part of a wider metric: Han et al.'s null-question category, where plain RAG beat the community-based and HippoRAG2 methods but not the two triple-extraction GraphRAG variants, which build their graph by extracting triples from text (table in Part 1), and the "missing" answer class in HoH (Part 3).

## Why the problem is hard

Three reasons "just say you don't know" is not a quick fix.

1. **Retrieval confidence is not evidence of coverage.** A retriever returns *something* for any query. High similarity says the passage resembles the question, not that the passage is complete with respect to it. The reconciliation job in our example would not appear in any ranking, however good, because it never entered the store.
2. **The generator may fill gaps from memory.** The BRINK label results hint at this: when the retrieved context is thin, a fluent language model may complete the picture from what it already believes. The output then looks like grounded reasoning but is partly parametric recall. For internal infrastructure, whose names were probably never in the training data, that recall has little to draw on, so the completion is more likely a guess than knowledge.
3. **Completeness is a property of a relation and a scope, not of the store.** The graph may list *all* production databases exhaustively (because an audit enforces it) and be hopelessly partial about *informal* dependencies. "The graph is incomplete" is almost never the right statement; "this relation, in this region, is not guaranteed complete" almost always is.

## The strongest counterargument

*"Open-world thinking is a luxury. A system that hedges on every question is useless. Operational users want answers; if the CMDB says a host has no listed owner, they treat that as 'no owner' — the closed-world assumption is the contract they signed."*

This is a good objection, and the answer is not to abandon closed-world reasoning. Many enterprise stores *are* closed-world over certain relations by policy: an asset register, a regulated inventory, an access list. In those regions, absence legitimately means "not there", and abstaining would be a failure of usefulness. The point is that the contract is *local* and should be *declared*. A system that knows "ownership is exhaustively tracked, dependencies are not" can answer the first flatly and caveat the second. The failure is the undeclared, global assumption — applying one policy to relations that deserve different ones.

Declarations have a weakness of their own, though: they decay. A completeness flag that nobody owns goes stale as the domain changes, and a stale "exhaustive" is worse than no flag, because it licenses a confident "no". Each declaration therefore needs an owner and a review date. It is cheap only relative to an undetected gap, not free.

## Design implications

Treat these as questions to ask of a design, not a checklist. None has been tested in the work reviewed here.

1. **Annotate completeness per relation and scope.** Record whether a relation type is believed exhaustive, sampled, or opportunistic, who maintains it, and when it was last reviewed. This metadata is cheap compared with an undetected gap, but it needs an owner to stay true. It turns "absent" into an answerable question.
2. **Give the answer three states, not two.** "Established", "established not to hold (an explicit negative assertion, with evidence)", and "cannot be established from available knowledge". Collapse them only at the interface, deliberately.
3. **Make the generator's source visible.** If the answer leans on parametric knowledge rather than retrieved evidence, say so. Showing the evidence chain for each claim lets a reader notice a link that is missing.
4. **Test for abstention explicitly.** Evaluation sets should include questions whose answer is known to be unrecoverable, and measure whether the system declines — separately from accuracy on answerable ones.
5. **Probe with ablated knowledge.** Remove a fact that your own domain experts know is derivable, and observe whether the system finds it, fabricates something, or declines. That test costs far less than an incident.

## Open questions

- How should *evidence of absence* be recorded? A negative assertion ("service A does not call B, verified on date D") is itself a claim with provenance, and it expires.
- Can completeness be estimated, not just asserted — by sampling, by cross-source comparison, by rule-based expectations?
- How do we evaluate abstention without rewarding systems that decline everything? Metrics must trade off coverage against calibrated refusal.
- How much of the apparent robustness of KG-RAG on public graphs comes from the language model's memory — and what does that imply for private graphs?

## Conclusion

A retrieval system that cannot represent what it does not know will, sooner or later, answer a question it should have refused. The remedy is not pessimism; it is bookkeeping — declaring where the store claims completeness, preserving the distinction between an absent assertion and an explicit negative one, and testing refusal as seriously as we test accuracy.

But a store can fail in a second way. Sometimes the problem is not that the answer is missing; it is that the store contains two of them.

---

> **Key takeaways**
> - A missing assertion is not a negative one: missing, unknown, truly absent and explicitly negated are different situations, and a closed-world reading silently merges them.
> - The most direct study reviewed (BRINK) shows KG-RAG degrading when edges are removed but does not measure abstention, and its label experiment suggests public-benchmark robustness may overstate robustness on private graphs.
> - Declare completeness per relation and scope, with an owner and a review date, and test refusal as seriously as accuracy.

**Reading notes.** *BRINK:* full text read, including appendices; the content of its figures was not examined. AMIE3, FB15k-237 and Wikidata5m are named as BRINK describes them and are not separately cited. *arXiv:2504.05163 and arXiv:2511.12208:* abstract and author list only. *Wen et al.:* abstract level. *Reiter (1978):* cited for the closed-world definition only. *Han et al., HoH and SCAIR:* used here only for the points stated; their reading depth is given in Parts 1, 3 and 4. For Han et al.'s null-question category I did not inspect how the questions were constructed or scored.

## References

- Reiter, R. (1978). On Closed World Data Bases. In H. Gallaire and J. Minker (eds.), *Logic and Data Bases*, Plenum Press, pp. 55–76. DOI: [10.1007/978-1-4684-3384-5_3](https://doi.org/10.1007/978-1-4684-3384-5_3).
- Zhou, D., Zhu, Y., Wang, X., Zhou, H., He, Y., Chen, J., Staab, S., Kharlamov, E. (2026). What Breaks Knowledge Graph based RAG? Benchmarking and Empirical Insights into Reasoning under Incomplete Knowledge (BRINK). *Proceedings of EACL 2026 (long papers)*, pp. 2522–2538. DOI: [10.18653/v1/2026.eacl-long.114](https://doi.org/10.18653/v1/2026.eacl-long.114). arXiv:2508.08344 v4.
- Zhou, D., Zhu, Y., Wang, X., He, Y., Chen, J., Staab, S., Kharlamov, E. (2025). *Evaluating Knowledge Graph Based Retrieval Augmented Generation Methods under Knowledge Incompleteness.* arXiv:2504.05163 (v2, Aug 2025). **Preprint;** the arXiv comment says "IRISAI'25" with no acceptance statement.
- Liu, J., Shao, P., Qin, W., Liu, F., Yang, Y., Hong, R. (2025). *Debate over Mixed-knowledge: A Robust Multi-Agent Reasoning Framework for Incomplete Knowledge Graph Question Answering.* arXiv:2511.12208. **Preprint;** no venue stated.
- Wen, B., Yao, J., Feng, S., Xu, C., Tsvetkov, Y., Howe, B., Wang, L. L. (2025). Know Your Limits: A Survey of Abstention in Large Language Models. *Transactions of the ACL* 13, 529–556. DOI: [10.1162/tacl_a_00754](https://doi.org/10.1162/tacl_a_00754).
- Han, H., Ma, L., Wang, Y., Shomer, H., Lei, Y., Qi, Z., Guo, K., Hua, Z., Long, B., Liu, H., Aggarwal, C. C., Tang, J. (2025). *RAG vs. GraphRAG: A Systematic Evaluation and Key Insights.* arXiv:2502.11371 (v1 Feb 2025; v3 Mar 2026). **Preprint;** no venue stated on the arXiv page.
- Ouyang, J., Pan, T., Cheng, M., Yan, R., Luo, Y., Lin, J., Liu, Q. (2025). HoH: A Dynamic Benchmark for Evaluating the Impact of Outdated Information on Retrieval-Augmented Generation. *Proceedings of ACL 2025 (long)*, pp. 6036–6063. DOI: [10.18653/v1/2025.acl-long.301](https://doi.org/10.18653/v1/2025.acl-long.301).
- Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. (2026). *When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation* (GraphRAG-Bench). ICLR 2026 (poster); arXiv:2506.05690 (v3, Feb 2026).
- Chaturvedi, P., Zhu, Y., Zhou, H., Zhou, D., He, Y., Staab, S., Du, F., Tang, J., Kharlamov, E. (2026). SCAIR: Schema-Conditioned Agentic Iterative Reasoning for Enterprise Knowledge Graphs. *Proceedings of ACL 2026 (Industry Track)*, pp. 1089–1104. DOI: [10.18653/v1/2026.acl-industry.76](https://doi.org/10.18653/v1/2026.acl-industry.76).
