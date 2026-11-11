# Claims, Not Documents

*Part 3 of 6 — The Edge Cases of Intelligent Knowledge Systems: Retrieval, Reasoning, and Trust in Enterprise AI*

---

## Two runbooks, one incident

Part 2 ended with a store that holds two answers where it should hold one. This article starts from the assumption that makes that case invisible: that relevant passages agree.

*Illustrative example (invented).* During an incident, an on-call engineer asks an assistant how to fail over a message broker. The retrieval layer returns two highly relevant documents. One is an approved runbook, owned by the platform team: "drain the old region first, then promote the standby". The other is a later post-incident review note: "draining first triggered a duplicate-delivery storm; we recommend promoting the standby first, then draining". Same broker, same steps, nearly the same words. Embedding similarity ranks the runbook slightly higher, because it is longer and more complete.

The assistant produces a smooth, well-cited answer. It follows the runbook and never mentions the note.

Nothing in this story involves a retrieval *failure* in the usual sense. The right documents were found. The failure is that the system treated two documents as interchangeable evidence when they are two *claims* with different standing, and it has no way to tell how they relate. A post-incident note is not an amendment: it *recommends*, and does not by itself change an approved procedure. If the recommendation was adopted — the runbook revised, or the note marked as approved guidance — then it supersedes the old step and the assistant gave the wrong answer. If it was not adopted, the runbook is still the authorised procedure, but the note is a credible warning the engineer should see before acting. Either way, silence about the disagreement is the wrong answer.

This article is about the gap between a *relevant document* and a *valid claim*, and about the fact that supersession is something an authority does, not something a date implies.

## The assumption: relevance approximates truth

Retrieval is optimised for relevance: closeness of text to question. Most RAG pipelines then add an implicit second assumption — that relevant passages agree, so more of them is better. That assumption is comfortable in encyclopaedic corpora and false in organisations, where knowledge is produced by different teams at different times with different authority, and is rarely reconciled.

A useful reframing is to stop thinking of the store as a collection of documents and think of it as a collection of **claims**. A claim has:

- a **source** (where it came from),
- a **scope** (which system, region, version or customer it applies to),
- an **authority** (who is entitled to assert it — an owner, a policy, a rumour in a chat export),
- a **time** (more than one, as we shall see).

Relevance tells you the claim is about the topic. It tells you nothing about the other four.

## What the research says

### Conflict is a family, not a single failure

A survey of knowledge conflicts in LLMs (Xu et al., EMNLP 2024) distinguishes **context–memory conflict** (retrieved text contradicts what the model believes), **inter-context conflict** (retrieved passages contradict each other) and **intra-memory conflict** (the model is internally inconsistent). Enterprise settings stress the second most, though the others interact with it: the model's memory can quietly outvote an unfamiliar internal fact.

A benchmark by Cattan et al. (2025; preprint, arXiv:2506.08500) takes the next step: it argues that the *right* behaviour depends on the *type* of conflict. It defines five types — no conflict, complementary information, conflicting opinions, freshness (outdated information), and misinformation — and, for each, what a good answer should do. For instance, with complementary sources it should combine them; with conflicting opinions it should present both; with outdated information it should prefer the newer. The dataset has 458 queries, retrieved from web pages. Counts are lopsided: 161 no-conflict, 115 complementary, 115 conflicting-opinions, 62 outdated and only 5 misinformation.

The authors test an *oracle* condition, in which the prompt also contains a description of the conflict type. Across six model configurations it lifts expected-behaviour scores by about 21 to 28 points, a mean of about 24 (my arithmetic). The two configurations most often quoted, GPT-4o (67.2 to 88.6) and Gemini 2.5 Flash with thinking (68.3 to 89.3), show the smallest gains. Models asked to classify the conflict type themselves reach accuracies of roughly 53–65%. One reading is that much of the gap lies in recognising what kind of conflict it is, not in writing the answer once the conflict is understood. That reading is conditional: the oracle prompt may also tell the model what to do, in which case the lift would partly reflect instruction, not recognition, and the part of the paper I read does not settle which. The authors also find hedging in the no-conflict and freshness categories — answers that equivocate when there was no reason to.

Caveats: it is a preprint; the evaluation uses an LLM judge (validated at 0.89 agreement on 100 examples); queries are web-based and restricted to safe topics; and the "misinformation" category has just five items, so no conclusion should rest on it. It does not measure whether a system *abstains*.

### Outdated information is damaging and often invisible

HoH (Ouyang et al., ACL 2025) builds a benchmark from Wikipedia revisions — 96,124 question–answer pairs over 219,463 documents — to test what happens when outdated and current documents coexist. Each answer is scored +1 if perfect, 0 if the model says the information is missing, and −1 if harmful (it relies on outdated information). The benchmark's score is the percentage of perfect answers minus the percentage of harmful ones; the authors validated their judge manually. The abstract reports a drop of at least 20% for mainstream models. In the tables this is absolute points on that score, and the generation experiments cover only three open models (Llama 3.1 70B and 8B, and Qwen 2.5 7B).

Take one relevant document plus one distractor, then add an outdated version of the relevant document. In the score-ordered setting the score falls from 89.12 to 67.00 for Llama 70B, from 85.70 to 48.18 for Llama 8B and from 76.31 to 34.57 for Qwen 7B: drops of roughly 22, 38 and 42 points (my arithmetic from the paper's two tables). The lowest single cell I found, −2.77, is one model and one setting (Qwen 2.5 7B, five distractors, documents ordered by date), where harmful answers outnumber perfect ones. Without retrieval the models mostly answer "missing" rather than giving a harmful answer, so in this benchmark the harm comes from retrieving the outdated document.

A different line of work (evolveQA; Nakshatri et al., arXiv:2510.19172, a preprint under submission) tests models' own knowledge on documentation that changed over time, not RAG, and reports lower accuracy than on non-changing controls. It motivates the problem; it does not show how a retrieval layer would fare.

### Time-aware retrieval helps — within a limited remit

Re³ (Cao et al., ACL 2026) proposes a retriever that combines relevance with recency and filters conflicting versions, with an LLM arbitrating among candidates. On its own benchmark of recurring-update data (NOAA forecasts, among others), where the task is to find the *latest* forecast among many, it reports 0.8732 accuracy, against 0.4238 for an existing temporal retriever (TempRetrieval), 0.4977 for a semantic-only dense retriever (BGE-M3) and 0.6975 for the strongest baseline, a retriever fine-tuned with LoRA. It also reports that filtering out stale context cut input tokens by about 58% and added under a second of total latency in its setup.

Three things temper this. The benchmark was built by the group that proposes the method. HoH and Re³ share authors, so they are not independent confirmation of each other. And the authors themselves state the limitation that matters here: the method is designed for "now-focused" queries, and applying it to *historical* ("what was the forecast last week?") or aggregation questions would require relaxing the recency bias. A recency filter answers the question "what is the latest?"; it does not answer "what was true then?" or "which applies here?".

## Why "prefer the newest" is not enough

Recency is the most popular fix, and for a certain class of question it is correct. In my reasoning it fails in at least four ways that routinely occur inside organisations. These four are my argument, not findings of the studies above.

1. **Scope.** The newer runbook applies to region B; the older to region A. Neither supersedes the other; each is valid within its scope.
2. **Authority.** A recent chat message, or a post-incident note that recommends a change, disagrees with an older approved policy. Newer is not more authoritative: a recommendation supersedes an approved procedure only once someone with the authority to do so has adopted it.
3. **Direction of time.** A policy published today takes effect next quarter. For a question about now, the older one still holds.
4. **Retroactive correction.** A document written last week may *correct* what was true last year. The publication date and the validity period are different things.

This is where three times need to be kept apart. **Publication time** is when a source was written. **Valid time** is when the fact held in the world. **Recorded time** is when the system learned it. Temporal-database research has distinguished valid time from *transaction time* (the database term for what this series calls recorded time) since the 1980s (Snodgrass and Ahn, 1985). Modern memory systems for agents have revived the idea; Zep, for example, models facts on a temporal knowledge graph that tracks both when an event happened and when the system learned of it (Rasmussen et al., 2025, preprint). The practical significance: a bitemporal view lets you answer "what did we believe on Tuesday?" as well as "what was true on Tuesday?" — which is what post-incident review requires.

Reasoning about *which claim to believe* is an older problem too. Doyle's truth-maintenance system (1979) kept the justifications behind each belief so that when an assumption was retracted, dependent beliefs could be retracted with it. An enterprise assistant has the same obligation in miniature: when a policy is superseded, every conclusion that cited it should be re-examined.

## When to resolve: as knowledge is loaded, or as it is asked?

A design decision with no universal answer: do you reconcile conflicts when you *load* knowledge into the store, or when you *answer* a question?

| | Resolve when loading | Resolve at query time |
|---|---|---|
| **Strength** | Cheap at query time; consistent answers; can mark supersession once | Keeps all claims; can resolve differently per question, scope and time |
| **Weakness** | Information lost if resolution was wrong; hard to reverse; needs authority rules up front | More latency and tokens; the model may be the arbiter; inconsistent answers across queries |
| **Fits when** | Authority is clear (versioned policies, owned configuration) | Scope or time matters to the question; claims contested |

My suggestion is that a design may need both: resolve what is clearly resolvable (a document marked as superseded, a versioned artefact) and carry the rest forward as explicit, *labelled* conflict. In the work I reviewed, no single strategy dominates; the main message of the Cattan et al. benchmark is precisely that behaviour should depend on conflict type. Multi-agent debate over conflicting evidence has been proposed (Wang et al., COLM 2025, MADAM-RAG), but in what I read the cost of such arbitration, and its behaviour on enterprise-style authority conflicts, is not established.

## The strongest counterargument

*"This is over-engineering. Most organisations can solve most of it with a freshness boost and a 'last reviewed' date. Claim-level modelling needs extraction and metadata that nobody maintains — the cure is worse than the disease."*

It is a fair challenge, and it is often right in practice: a simple recency prior is cheap, and for versioned content such as release notes or forecasts it works (Re³'s results point that way). The remaining disagreement is about where the rest falls. The cases that hurt most — the incident runbook, the policy exception, the region-specific procedure — are exactly those where recency alone misleads, and where a confident wrong answer costs the most. A pragmatic path is not full claim modelling everywhere, but *selective*: apply it to the content classes where a wrong answer has consequences, and use cheap proxies (ownership, status, effective dates) elsewhere.

## Design implications

The following are engineering suggestions that follow from the argument above, not tested results.

1. **Treat time as three fields, not one.** Capture publication time, validity (start, end, or open) and recorded time when they are available, even partially.
2. **Record supersession as an explicit relation** between claims, with its scope and the authority that made it. Keep "recommended" and "adopted" distinct. Do not rely on similarity to discover that two documents are versions of the same thing.
3. **Consider making the system classify the conflict before answering.** The benchmark results are consistent with recognising the type being a large part of the difficulty, though the oracle confound above leaves that open; an explicit classification step is cheap to try and to measure.
4. **Show the disagreement.** When two scopes or authorities disagree and cannot be resolved, say so, with sources, instead of choosing silently.
5. **Test with supersession pairs.** Evaluation sets should include documents that differ only in validity or scope, and score whether the system picks the right one *and* explains why.

## Open questions

- How should *authority* be represented? The literature I reviewed treats time richly and authority barely at all.
- What is the cost of query-time arbitration at scale, and when does a cheaper rule suffice?
- Do results on Wikipedia revisions and weather forecasts transfer to internal procedural knowledge, where versions are informal and edits are unrecorded?
- How should a system treat claims that are *contested* rather than outdated — where both are current and the organisation has simply not decided?

## Conclusion

A relevant document is evidence that a topic is addressed; a claim is evidence that something is true, for someone, somewhere, for a while. Systems that retrieve documents and hope the generator sorts out the claims will keep producing fluent answers that follow a superseded step, or ignore a warning that nobody has yet adopted. The fix is not one algorithm; it is a modelling stance: keep source, scope, authority and time attached to what the system knows.

Once claims have structure, the next question is how a system should move through that structure — and who gets to decide where it walks.

---

> **Key takeaways**
> - Relevant is not the same as valid: a claim has a source, scope, authority and time, and "prefer the newest" breaks when scope, authority or the direction of time differ.
> - In the work reviewed, outdated documents lowered RAG scores in HoH's setup, the right behaviour depended on conflict type in the DRAGged benchmark, and recency-aware retrieval was shown only for "latest value" questions.
> - Keep publication, valid and recorded time apart, record supersession with its scope and authority, and show unresolved disagreement instead of choosing silently.

**Reading notes.** *HoH:* full text read, including the results tables. *DRAGged (Cattan et al.):* main results and setup read (v2); the oracle prompt's exact wording was not examined beyond its description of the conflict type. *Re³:* main text and results tables read. *Xu et al., evolveQA, Zep, Snodgrass and Ahn, Wang et al. (MADAM-RAG):* abstract or metadata level; MADAM-RAG's venue is taken from the arXiv record, and I could not locate a proceedings page. *Doyle (1979):* cited for the idea only.

## References

- Xu, R., Qi, Z., Guo, Z., Wang, C., Wang, H., Zhang, Y., Xu, W. (2024). Knowledge Conflicts for LLMs: A Survey. *Proceedings of EMNLP 2024*, pp. 8541–8565. DOI: [10.18653/v1/2024.emnlp-main.486](https://doi.org/10.18653/v1/2024.emnlp-main.486).
- Cattan, A., Jacovi, A., Ram, O., Herzig, J., Aharoni, R., Goldshtein, S., Ofek, E., Szpektor, I., Caciularu, A. (2025). *DRAGged into Conflicts: Detecting and Addressing Conflicting Sources in Search-Augmented LLMs.* arXiv:2506.08500 (v2, Jun 2025). **Preprint;** no venue stated on the arXiv page. Code/data: github.com/google-research-datasets/rag_conflicts.
- Ouyang, J., Pan, T., Cheng, M., Yan, R., Luo, Y., Lin, J., Liu, Q. (2025). HoH: A Dynamic Benchmark for Evaluating the Impact of Outdated Information on Retrieval-Augmented Generation. *Proceedings of ACL 2025 (long)*, pp. 6036–6063. DOI: [10.18653/v1/2025.acl-long.301](https://doi.org/10.18653/v1/2025.acl-long.301).
- Nakshatri, N. S., Roy, S., Arivazhagan, M. G., Zhou, H., Bannihatti Kumar, V., Gangadharaiah, R. (2025). *When Facts Change: Probing LLMs on Evolving Knowledge with evolveQA.* arXiv:2510.19172 (v2, Nov 2025). **Preprint, "under submission".**
- Cao, J., Ouyang, J., Cheng, M., Zhou, Z., Liu, C., Li, Y., Liu, Z., Wang, S. (2026). Re3: Relevance & Recency Retrieval for Mitigating Temporal Hallucination. *Proceedings of ACL 2026 (long)*, pp. 25735–25760. DOI: [10.18653/v1/2026.acl-long.1180](https://doi.org/10.18653/v1/2026.acl-long.1180).
- Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J., Chalef, D. (2025). *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* arXiv:2501.13956 (v1, Jan 2025). **Preprint; vendor authors.**
- Wang, H., Prasad, A., Stengel-Eskin, E., Bansal, M. (2025). Retrieval-Augmented Generation with Conflicting Evidence (MADAM-RAG). *Conference on Language Modeling (COLM) 2025*; arXiv:[2504.13079](https://arxiv.org/abs/2504.13079) (v2, Aug 2025).
- Snodgrass, R., Ahn, I. (1985). A Taxonomy of Time in Databases. *Proceedings of ACM SIGMOD 1985*, pp. 236–246.
- Doyle, J. (1979). A Truth Maintenance System. *Artificial Intelligence* 12, 231–272.
