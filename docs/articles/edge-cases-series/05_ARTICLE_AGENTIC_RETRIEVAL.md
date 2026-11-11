# When to Stop Searching, and What It Costs

*Part 5 of 6 — The Edge Cases of Intelligent Knowledge Systems: Retrieval, Reasoning, and Trust in Enterprise AI*

---

## The seductive diagram

Part 4 asked how much freedom an agent should have over a graph; this article starts from the assumption beneath that question, that more freedom — more search steps, more tools — simply buys better retrieval.

There is a diagram that now appears in almost every presentation about retrieval. On the left, a single arrow: question → retriever → answer. On the right, a loop: the model searches, reads, reconsiders, searches again, opens a document, searches inside it, and finally answers. The right-hand picture is plainly *smarter*. It looks like what a human researcher does.

The claim attached to the picture is usually that autonomy makes retrieval better. Sometimes it does, by a lot. But the diagram leaves out the clock, the bill, and the question of when the loop should end. This article asks what the research actually says about agentic retrieval — and what it leaves unsaid.

## Why agentic retrieval exists

For some questions, single-shot retrieval is structurally the wrong tool. BRIGHT (Su et al., ICLR 2025) is a benchmark of "reasoning-intensive" queries — questions whose relevant documents do not resemble the question. Its authors report that the best model on the MTEB embedding leaderboard scores 59.0 nDCG@10 on MTEB's retrieval tasks but only 18.0 on BRIGHT. If the system must *work out* what to look for, a single embedding comparison is not enough, and iteration is a reasonable response: decompose, search, read, search again.

Beyond that, there are more mundane reasons: queries that refer to a specific section of a long document, queries that need two different lookups, queries where the first result changes what to ask next. All of these are real. The question is not whether agentic retrieval has uses, but how large its advantage is, what it costs, and who decides when it stops.

## What one headline paper shows

A prominent recent result is *AgenticRAG* (Suresh et al., arXiv:2605.05538, May 2026), an industry-authored preprint. Its system gives a language model four tools — search, find, open and summarise — and lets it iterate up to fifteen times. The headline claim is a 5.9× improvement in retrieval quality. The paper is worth reading closely, because it shows how a headline number is assembled.

| Setup | Measure | Baselines | Agent |
|---|---|---|---|
| BRIGHT, long-document split (eight collections, 861 queries) | Recall@1, averaged over collections | Paper's own single-shot search 8.41; best embedding model 27.8; BM25 11.4 | 49.59 (Claude Sonnet 4.5); 43.49 (GPT-5-mini) |
| Same split | Tokens per query, average | Single-shot search 20.4K | 52.3K |
| FinanceBench (150 questions over 84 long documents) | Answer correctness, % | "Traditional RAG" 24.24; agent with keyword tools 32.71; golden-evidence oracle 94.00 | 92.00 (GPT-5-mini); 91.78 (Claude Sonnet 4.5) |
| Same benchmark | Tokens per query, average | Single-shot search 14.7K | 114.8K |
| Customer-support benchmark | Factuality | Embedding baseline 0.85; BM25 0.83 | 0.96 |

On the BRIGHT split, the multiplier is a ratio of two table values. Dividing 49.59 by the paper's own single-shot baseline of 8.41 gives about 5.9, and 43.49 divided by 8.41 gives about 5.2. Against the best embedding model in the same table (27.8) the Claude agent is about 1.8× better; against BM25 (11.4), roughly 4.4×. On FinanceBench, 92.00 divided by 24.24 is about 3.8×, and 92.00 divided by 32.71 is about 2.8×. (All ratios are my arithmetic on the paper's table values.)

Four points of interpretation follow.

- **The multiplier depends on the baseline.** "5.9×" is a fact about a particular single-shot search over a proprietary search stack, which the paper says trades raw quality for speed and scale. The gain over a well-chosen embedding model is real but much smaller.
- **The FinanceBench baseline is undescribed.** The paper does not say how its "traditional RAG" pipeline works, and does not say it is the same system as the single-shot search used elsewhere. That is why the 14.7K-token figure should not be read as the cost of the 24.24 baseline: it belongs to the single-shot search, and the two may differ. The 3.8× deserves the same scrutiny as the 5.9×, and the 2.8× over the keyword-tools agent is the more conservative reading.
- **There are internal discrepancies.** The text says the agent achieves the highest result across all eight splits, yet the paper's own table shows exceptions — on one split (Stack Overflow) a baseline method called ReDI scores 36.3 against the Claude agent's 34.1, and on another BM25 (5.4) beats the GPT-5-mini agent (4.8).
- **No code and no latency or dollar figures.** The paper reports tokens and tool-call counts, which is useful, but not wall-clock time or price. It is a single-source, unreviewed preprint.

On cost, which the paper does report, tokens per query are about 2.6× the single-shot search on the BRIGHT split and about 7.8× on FinanceBench (my arithmetic), with roughly 4.5–4.8 tool calls per query. The quality gain on FinanceBench is large, and so is the token bill.

One ablation is instructive but thin. It was run with GPT-5-mini only, the number of runs is not stated, and the "±" values in the table are not defined. Removing the multi-query tool left Recall@1 comparable (43.49 with it, 44.84 without; the paper itself calls the two comparable), while the average number of tool calls rose from 4.79 to 6.79, which the paper presents as a reduction of about 29% in calls when the tool is present. Read narrowly, a tool can change the length of the trajectory without changing recall in this one configuration. A quality metric alone would not have shown the difference.

## The anatomy of cost

Cost in an agentic loop has several parts that single-shot retrieval does not have.

| Component | Why it grows with autonomy |
|---|---|
| **Tokens** | Every iteration re-reads the accumulated context; most of the bill is input |
| **Latency** | Steps are sequential — each search waits for the previous reasoning |
| **API calls** | Multiple tool calls and multiple model calls per question |
| **Variance** | Different runs take different paths; cost and quality both spread |
| **Debuggability** | A trajectory has to be inspected, not just a ranking |

The efficiency of search agents has become its own research topic. SearchAgent-X (Yang et al., arXiv:2505.12065, preprint) reports 1.3–3.4× higher throughput through scheduling and high-recall approximate retrieval, noting that both too little and too much retrieval effort reduce efficiency. HotelQuEST (Hadad et al., EACL 2026 Industry Track) argues that agentic-search benchmarks measure answer quality and neglect efficiency, and reports that current systems are inefficient and leave substantial room for cost-aware optimisation. Sharifymoghaddam and Lin (Findings of ACL 2026) introduce an *effective token cost* metric and report that a moderate amount of reranking often helps more than extra search-time reasoning, at much lower cost. These are from different task families (deployment engineering, hotel search, a web-browsing benchmark) and none involves enterprise knowledge, so they are best read as evidence that the cost question is real and unsettled.

## The problem of stopping

Agentic retrieval has a decision that single-shot retrieval does not: *when to stop*. Stopping can fail in two opposite directions.

- **Stopping too early:** the first plausible document is accepted and the answer is incomplete. The loop saved money and shipped an error.
- **Stopping too late:** the loop continues to search after the answer is in hand, burning tokens for diminishing returns. A worse case is a hypothesis, not something the studies reviewed here show: the loop finds a contradicting document and talks itself out of a correct answer.

A fixed budget (maximum steps) is a blunt guard. The AgenticRAG paper uses one, at fifteen iterations, and reports an average of under five tool calls, far below the cap. Averages hide the tail, so the paper tells us little about how often the cap is hit or what happens when it is. A better stopping rule needs a notion of *marginal value*: does another step plausibly add evidence? The papers I inspected do not provide such an estimate; stopping is mostly a model judgement plus a cap. The routing work discussed next decides *whether* to retrieve, or how much, before a loop starts; it is not a rule for stopping a loop already under way.

A related stopping case is **the answer isn't there**. A loop that cannot find the evidence may keep searching or return its best guess, and it has more chances than a single shot to assemble a plausible answer from fragments. Part 2 covers abstention; here the point is only that the stopping rule has to include a way to give up.

## Routing: not every question deserves a loop

Adaptive-RAG (Jeong et al., NAACL 2024) addresses the cost directly: a small classifier predicts how complex a query is and routes it to no retrieval, single-step retrieval, or multi-step retrieval. The idea is to pay the iterative cost only where the question warrants it. Self-RAG (Asai et al., ICLR 2024) pursues a related idea at the model level, training a model to decide on demand whether to retrieve at all. Both decide *whether* or *how much* to retrieve, not when an iterative loop should stop. Both predate the current generation of tool-using agents and were evaluated on standard question-answering benchmarks, so their routing accuracy on enterprise query mixes is unknown.

A router is also a component with its own error rate, and in my reasoning its two errors are not symmetric. A hard question routed to single-shot retrieval fails quietly: nothing signals that the cheap path was not enough, and the answer looks like any other. An easy question routed to the loop is answered, at a higher cost than it needed. The first error costs trust and the second costs money, which is why logging routing decisions and sampling the cheap path for misroutes matters more than the router's average accuracy. This is an argument from the structure of the problem; I did not find a measurement of either error on enterprise questions.

## The strongest counterargument

*"Cost is a distraction. Tokens get cheaper every few months; latency will drop; the quality gap is large and durable. Optimising for cost now is premature. Build the capable thing and let economics catch up."*

This has force: inference prices have tended to fall, and it would be foolish to design around today's prices. Some mitigations exist and deserve credit. Prompt caching reduces the price of re-reading accumulated context; independent tool calls can be issued in parallel, which shortens latency though not the number of tokens; smaller models can handle simple steps. The SCAIR authors argue caching helps their loop (Part 4). None of these was measured in the AgenticRAG results, so how far they close the gap is open.

It is also true that, in the cases where single-shot retrieval simply cannot find the evidence (BRIGHT-style queries), no amount of cost-saving rescues it. My view of where loops pay off follows from that. They pay off where the first result changes what to ask next, since those steps cannot be parallelised away; where the evidence does not resemble the question; and where a wrong answer costs more than a long one. They pay off less for lookups that a deterministic step would answer, because cost scales with usage and the loop's overhead is paid every time. Latency is not purely an economic quantity either, since an on-call engineer will not wait through a long chain of sequential steps, and variance and debuggability do not shrink with token prices. The real question is not "cheap or capable?" but "where is the loop worth it?".

## Design implications

The following are engineering suggestions that follow from the evidence above, not tested results.

1. **Report the baseline with the ratio.** Any "N× better" claim should state N× over *what*, in what setup, and at what token cost. Insist on a strong single-shot baseline: hybrid retrieval with reranking, not only the weakest one.
2. **Measure quality per unit cost.** Track tokens, tool calls, latency and, where available, dollars alongside accuracy. A configuration that matches accuracy with fewer calls is better.
3. **Make the deterministic path the default.** Use a fixed pipeline for lookup-type questions and reserve the loop for ones that need it; Adaptive-RAG-style routing is one way, a simple rule set another. Log the routing decision so errors can be traced, and sample the cheap path to find misroutes.
4. **Treat stopping as a designed component.** Define budgets in steps, tokens and time; define what the system says when the budget is exhausted ("I could not establish this; here is what I found").
5. **Test the unanswerable tail.** Evaluate on questions where the answer does not exist or cannot be reached, and score whether the loop gives up gracefully.
6. **Keep trajectories.** Store the sequence of searches and reads. It is the audit trail, and it is the basis for finding wasted steps.

## Open questions

- Is there a principled way to estimate the *marginal value* of another retrieval step, so stopping is more than a cap?
- How do agentic gains hold up against strong hybrid-plus-rerank baselines at equal cost? The headline paper compares against weaker ones.
- What are the real dollar and latency costs on enterprise-scale corpora, with caching and parallel calls? The published efficiency work uses other settings.
- How does a loop behave when the store is incomplete or contradictory (Parts 2 and 3)? Most benchmarks assume the answer exists and is unique.

## Conclusion

Agentic retrieval is a real advance for a real class of question. It is not a free upgrade: it exchanges a nearly fixed per-query cost for a variable, path-dependent one that explicit budgets on steps, tokens and time can bound, and it hands the system a decision — when to stop — that single-shot retrieval never had to make. The takeaway: pay for the loop only where the question needs one, and decide in advance how it stops.

That leaves the question the whole series has been circling. If each of these parts can fail on its own, what does it take for the *whole* to be trustworthy?

---

> **Key takeaways**
> - Agentic retrieval has a real use, but "N× better" claims depend on the baseline: the headline 5.9× is against the paper's own single-shot search and is about 1.8× against the best embedding model in the same table.
> - The loop adds costs single-shot retrieval lacks — tokens, latency, variance, debuggability — and a stopping decision that the work reviewed mostly leaves to a model judgement plus a cap.
> - Route simple questions to a deterministic path, put budgets on the loop, and decide what the system says when it runs out.

**Reading notes.** *AgenticRAG:* full text read, including the main tables and most of the appendix; the paper does not describe its "traditional RAG" baseline, which is why that comparison is flagged. *BRIGHT:* the 59.0 versus 18.0 figures are from the proceedings abstract. *Adaptive-RAG, Self-RAG, SearchAgent-X, HotelQuEST, Rerank Before You Reason:* abstract level; the figures given for them are their authors' claims, and HotelQuEST's author order follows the arXiv listing.

## References

- Su, H., Yen, H., Xia, M., Shi, W., Muennighoff, N., Wang, H., Liu, H., Shi, Q., Siegel, Z. S., Tang, M., Sun, R., Yoon, J., Arik, S. O., Chen, D., Yu, T. (2025). BRIGHT: A Realistic and Challenging Benchmark for Reasoning-Intensive Retrieval. *ICLR 2025*; arXiv:2407.12883.
- Suresh, S., Mak, H., Chou, S., Kroon, F., Bhatnagar, S. (2026). *AgenticRAG: Agentic Retrieval for Enterprise Knowledge Bases.* arXiv:2605.05538 (v1, 7 May 2026). **Preprint; no code.**
- Jeong, S., Baek, J., Cho, S., Hwang, S. J., Park, J. C. (2024). Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. *Proceedings of NAACL 2024*. DOI: [10.18653/v1/2024.naacl-long.389](https://doi.org/10.18653/v1/2024.naacl-long.389); arXiv:2403.14403.
- Asai, A., Wu, Z., Wang, Y., Sil, A., Hajishirzi, H. (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. *ICLR 2024*; arXiv:2310.11511.
- Yang, T., Yao, Z., Jin, B., Cui, L., Li, Y., Wang, G., Liu, X. (2025). Demystifying and Enhancing the Efficiency of Large Language Model Based Search Agents (SearchAgent-X). arXiv:2505.12065. **Preprint.**
- Hadad, G., Iskander, S., Kalinsky, O., Tolmach, S., Levy, R., Roitman, H. (2026). HotelQuEST: Balancing Quality and Efficiency in Agentic Search. *EACL 2026 Industry Track* (ACL Anthology 2026.eacl-industry.16); arXiv:2602.23949.
- Sharifymoghaddam, S., Lin, J. (2026). Rerank Before You Reason: Analyzing Reranking Tradeoffs through Effective Token Cost in Deep Search Agents. *Findings of ACL 2026*, pp. 25874–25886; arXiv:2601.14224.
- Chaturvedi, P., Zhu, Y., Zhou, H., Zhou, D., He, Y., Staab, S., Du, F., Tang, J., Kharlamov, E. (2026). SCAIR: Schema-Conditioned Agentic Iterative Reasoning for Enterprise Knowledge Graphs. *Proceedings of ACL 2026 (Industry Track)*, pp. 1089–1104. DOI: [10.18653/v1/2026.acl-industry.76](https://doi.org/10.18653/v1/2026.acl-industry.76).
