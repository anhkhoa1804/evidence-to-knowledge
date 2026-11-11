# Maps Before Walking

*Part 4 of 6 — The Edge Cases of Intelligent Knowledge Systems: Retrieval, Reasoning, and Trust in Enterprise AI*

---

## An agent in a dense graph

*Illustrative example (invented).* A maintenance planner asks: "Which spare parts could replace the failed sensor on one production line, given what's in stock?" The company's configuration database is a graph: lines contain machines, machines contain components, components have compatibility rules, inventory has locations. An LLM-driven agent starts at the failed sensor and explores. It follows `hasStatus` to a node called "Broken", which many other components also point to, and now it is wandering a neighbourhood of broken things on other lines. Several steps later it assembles a plausible answer from whatever it passed — a part that is in stock, a part that belongs to that line, and a part that is called a sensor, though not the same one. The answer reads well; the walk was simply unconstrained.

Part 3 ended with claims that carry scope and authority. Those attributes are only useful if something *uses* them while the system is moving through the data. This article is about the step between "we have a structured store" and "an agent reasons correctly over it".

## The assumption: a capable model will find its way

Agentic retrieval over graphs rests on a pleasant idea: give the model the graph and a toolbox (list neighbours, follow a relation, read a node), and let it reason its way along. On public question-answering graphs this works surprisingly well. But public graphs are, structurally, friendly: sparse, open-domain, with entity and relation names that are common in pretraining text, and with few hard rules about what may connect to what. An enterprise graph is the opposite on each count.

## What the research says

### SCAIR: a case study in what breaks

The study this article leans on is SCAIR (Schema-Conditioned Agentic Iterative Reasoning; Chaturvedi et al., ACL 2026 Industry Track). It does two things worth separating: it builds a benchmark, and it proposes a method.

**The benchmark.** The authors derive a question-answering benchmark from a real manufacturing configuration database (production lines, machines, components and their operational states), with questions generated from templates over several reasoning patterns (from one-hop paths through multi-hop and intersection-style patterns). They compare existing KG-RAG methods — two that the authors fine-tuned on this benchmark (RoG, G-Retriever) and two training-free (ToG, PoG).

**The diagnosis.** The authors report two failure modes of generic agents in dense, schema-governed graphs: *search explosion* — the agent expands too many branches — and *semantic drift* — the agent follows links that look related in language but are irrelevant operationally. They single out high-degree attribute nodes, such as a status value like "Broken", as hubs that pull ReAct-style exploration off course. For the plan-and-execute alternative, the authors' own explanation of its weak result is that trained planners internalise the reasoning templates of their training distribution and generalise poorly to other query patterns.

**The method.** SCAIR injects schema-derived priors into planning and restricts traversal to relations and entity types the schema permits, with an iterative loop that checks progress. Under the authors' setup, it reaches accuracy of 35.14, compared with 25.27 for G-Retriever (the strongest baseline by accuracy), 20.80 for RoG, 16.04 for ToG and 16.17 for PoG. A backbone comparison reports that swapping a weaker language model for a stronger one improves answer generation but does not prevent search explosion, which leads the authors to call the failure "architectural, not parametric".

What the evidence does *not* show, and what a careful reader should keep in mind:

- **Absolute accuracy is low.** The best system answers about a third of the questions correctly under the paper's metric. This is a better method on a hard benchmark, not a solved problem.
- **Questions are templated**, not collected from users, so they may not reflect how people actually ask.
- **A key baseline is absent.** The authors themselves list non-agentic schema-constrained traversal and text-to-SPARQL baselines as future work. That means the paper cannot say whether the *agentic* part of SCAIR is needed, or whether schema constraints alone would capture most of the gain. Its ablation removes relation filtering and entity-centric constraints together, so it tests variants of SCAIR, not simpler non-agentic designs; the ablation's values are in a figure I could not extract.
- **Cost rises.** SCAIR uses about 42 model calls per question, against about 14 for ToG and 5.6 for PoG (that comparison covers the training-free methods), and roughly 22,000 input and 6,000 output tokens per query. The authors argue this is functional (the questions need 2–4 hops) and amenable to prompt caching; that is a design argument, not a measured dollar figure.
- **The schema-evolution claim is argued, not measured.** The discussion says training-free methods adapt better to schema change than trained ones; the experiments do not change the schema.
- **Author overlap.** SCAIR shares five authors with BRINK (Part 2) and the data comes from one industrial setting. It is a single group's evidence from a single deployment.

### How other traditions constrain the query

SCAIR is one answer to a problem that other communities have approached with different tools. Five neighbours are worth setting beside it. SAFE I read in full; the others I inspected at abstract or summary level, so this is a comparison of designs, not of numbers.

- **Relaxed matching of a drafted query graph (SAFE; Lee, Park and Han, EMNLP 2025).** Language models do not know the structure of a particular knowledge graph, so the query graphs they draft often fail to match real subgraphs. In SAFE a language model drafts a query graph, and an *Approximate Distance Join* relaxes the matching: a query edge may be satisfied by any pair of graph vertices joined by a path no longer than a threshold, and the best-ranked matching subgraphs are returned. A compact *schema graph* of types and admissible relations serves as a cheap lookup of type-level distances and tightens the entity-type filters. The authors evaluate on WebQSP, CWQ and GrailQA and report accuracy gains and large speed-ups.
- **Generate a structured query, then ground it (ChatKBQA; Luo et al., Findings of ACL 2024).** A fine-tuned model first writes a logical form; entities and relations are then retrieved and substituted to fit the knowledge base. The graph's vocabulary is applied *after* generation, and the authors report strong results on WebQSP and CWQ.
- **Plans that the graph can check (RoG, Luo et al., ICLR 2024; Pangu, Gu, Deng and Su, ACL 2023).** RoG has the model propose relation paths grounded in the graph and then retrieves reasoning paths that follow them. Pangu goes further: a symbolic component enumerates only plans that are valid in the environment, and the language model's job is to *score* them rather than to invent them. Validity is guaranteed by construction; plausibility is the model's contribution.
- **Schema linking in text-to-SQL (DIN-SQL; Pourreza and Rafiei, NeurIPS 2023).** The problem is split into sub-problems, with schema linking as an explicit step, followed by self-correction: the schema is a stage of the pipeline, not a paragraph in the prompt.
- **Ontology-based data access (Poggi et al., 2008).** Long before language models, this tradition layered a conceptual model over data sources through mappings, so that questions are posed against the model rather than against raw storage. It is a reminder that "the schema constrains what can be asked" is an old idea with a formal literature, though one that says nothing about LLM agents.

What do these add? Three observations, which are my reading rather than findings of any one paper.

1. They all treat the schema as a **constraint on action** — what may be generated, followed, matched or scored — not as documentation shown to the model.
2. Several move the model's job from *exploring* to *choosing or repairing*: generate then ground, enumerate then score, draft then match approximately. That is a materially different design from the open-ended walk SCAIR criticises, and it is the comparison SCAIR's own authors say is missing.
3. As far as I could inspect, none was evaluated on dense, operationally constrained enterprise graphs of the kind SCAIR uses, and none confirms SCAIR's specific diagnosis (search explosion, semantic drift around hub nodes). SCAIR's own results are also narrower than they may look: RoG, which its authors fine-tuned on this benchmark, scores 20.80 there, and the authors attribute weak trained planners to the templates of their training data. The paper does not test whether RoG's behaviour on public graphs would carry over, so this says something about one fine-tuned configuration, not about transfer. The independent literature supplies design alternatives, not a replication.

## Four ways to use a schema: a proposed framing

The scheme below is this article's, not SCAIR's. SCAIR does not use these terms, and its experiments do not test them as separate options. The paper establishes that schema-conditioned planning plus schema-aware traversal outperformed the baselines on its benchmark; it does not tell us which ingredient mattered most.

1. **Schema as description.** Put the ontology or table definitions in the prompt. Cheap, but the model is only *advised*; nothing stops it from ignoring the advice.
2. **Schema as planner.** Use types and relations to decide, before touching the data, which paths are possible — "from a component to its machine to its line" — and prune those that cannot work. SCAIR's schema-conditioned planning is closest to this.
3. **Schema as guard.** Enforce, at the tool level, that the agent may only call operations the schema allows (follow relation *R* from an entity of type *T*), and validate results against constraints. This turns a guideline into an invariant. SCAIR's schema-aware traversal is closest to this, and Pangu's enumerate-then-score design is a related example in the neighbouring literature.
4. **Schema as repair.** Let the model draft a query or plan, then use the graph to align it: SAFE relaxes the matching of a drafted query graph using type-level distances and tighter type filters, and ChatKBQA grounds a generated logical form in the knowledge base's own entities and relations. This sits between planner and guard.

The patterns can stack, and each has a failure surface. Description fails by ignorance; planning fails when the plan is wrong or the schema is incomplete; guarding fails when the guard is too tight (the true answer needs an edge the schema did not anticipate); repair fails when the draft is too far from any valid query to be fixed. These failure modes are my reasoning.

## What schema awareness does not solve

- **The schema may be wrong or partial.** Enterprise schemas accumulate exceptions; an agent constrained by a stale schema is confidently narrow. This reconnects with Part 2: the constraint is only as complete as the model of the domain.
- **Constraints are more than types.** The interesting enterprise rules are operational: compatibility, availability, ownership, permission. Those are conditions on facts and often on time (Part 3). The SCAIR authors note exactly this and point to constraints with types as future work.
- **Query generation might beat traversal.** If the schema is available, why have an agent walk at all? Generating a structured query (SPARQL, SQL, Cypher) and executing it deterministically sidesteps step-by-step drift. The SCAIR authors flag the missing comparison, and the neighbouring work above (generate-then-ground, enumerate-then-score) suggests the alternatives exist.

## The strongest counterargument

*"Schema-aware agents are an elaborate way to rebuild a query planner. If you have a clean schema, write the query. If you don't have one, the agent can't be schema-aware. The whole approach needs the thing enterprises lack."*

In some environments this objection is simply right: where questions are repetitive and the schema is stable, parameterised queries or generated SPARQL are cheaper, faster and auditable. The case for agents is narrower: questions that are open-ended, span several relation types, or require the system to decide *at run time* which constraints matter. Even there, the argument above suggests the schema should still be doing the heavy lifting — pruning and validating — and the model's role should shrink to the choices a schema cannot make. But I should say plainly that this is an argument, not a result: the design implications below are untested, and the comparison that would decide how much agency is worth — an agent with a schema, against a non-agentic constrained query, on the same questions — has not, in the work I reviewed, been run.

## Design implications

The following are engineering suggestions that follow from the evidence above. They are untested.

1. **Prune by structure before ranking by meaning.** Filter candidate relations and entity types using the schema first, then apply semantic scoring within what survives. The SCAIR authors state this as a principle: structural validity should gate semantic relevance.
2. **Enforce constraints in the tools, not in the prompt.** A tool that refuses an illegal traversal is stronger than an instruction that discourages it. Log refusals — they are a signal that the schema or the question needs attention.
3. **Watch for hubs.** High-degree attribute or status nodes are traps for similarity-driven exploration. Treat them as filters (properties of an entity) rather than as places to walk.
4. **Version the schema and test across a change.** If schema evolution is the reason to prefer inference-time constraints, run the same question set before and after a relation is renamed or split. The literature does not do this; teams should.
5. **Keep a non-agentic baseline.** Before paying for an agent, measure what a constrained, deterministic query achieves on the same questions.
6. **Use opaque names in evaluation.** BRINK's label experiment (Part 2) and SCAIR's argument about leakage both suggest that public benchmarks can be flattered by names the model recognises. Test with renamed or private identifiers to see whether performance survives.

## Open questions

- How much of agent gain comes from schema constraints, how much from iteration, and how much from the larger token budget? The ablation that separates them is not in the literature I could inspect.
- Can schemas carry *operational* constraints (compatibility, availability, authority) in a form an agent can act on, rather than only structural ones?
- What happens when the schema is incomplete — does the guard block the true answer, and can the system tell?
- How do these methods behave when the graph itself is partial or conflicting (Parts 2 and 3)? The benchmarks treat graph content as given.

## Conclusion

An agent walking an enterprise graph without constraints is exploring in the dark. In the one benchmark reviewed here, adding schema constraints helped where a stronger language model alone did not, which suggests the useful step may be a better map applied as a rule — schema first, semantics second. That suggestion rests on a single benchmark from a single group, with no non-agentic baseline, so the field has not yet shown how much autonomy the map leaves worth having.

That question — how much freedom a retrieval system should be given, and what it should cost — is next.

---

> **Key takeaways**
> - Agents walking dense, schema-governed graphs can fail by search explosion and semantic drift, and in the one benchmark reviewed a stronger language model alone did not prevent it, while schema constraints helped.
> - Neighbouring work uses the schema as a constraint on action (generate then ground, enumerate then score, relaxed matching), which shrinks the model's job to choosing or repairing.
> - The evidence is one benchmark from one group with no non-agentic baseline, so how much agency is worth remains an open question.

**Reading notes.** *SCAIR:* full text read; the ablation's values are in a figure that could not be extracted. *SAFE:* full text read. *BRINK (used for its label experiment, Part 2):* full text read. *ChatKBQA, RoG, Pangu, DIN-SQL, Poggi et al., ReAct:* abstract or metadata level; initials for the Poggi et al. authors were not verified. *G-Retriever, ToG, PoG:* named as they appear in SCAIR's results and are not separately cited.

## References

- Chaturvedi, P., Zhu, Y., Zhou, H., Zhou, D., He, Y., Staab, S., Du, F., Tang, J., Kharlamov, E. (2026). SCAIR: Schema-Conditioned Agentic Iterative Reasoning for Enterprise Knowledge Graphs. *Proceedings of ACL 2026 (Industry Track)*, pp. 1089–1104. DOI: [10.18653/v1/2026.acl-industry.76](https://doi.org/10.18653/v1/2026.acl-industry.76).
- Zhou, D., Zhu, Y., Wang, X., Zhou, H., He, Y., Chen, J., Staab, S., Kharlamov, E. (2026). What Breaks Knowledge Graph based RAG? Benchmarking and Empirical Insights into Reasoning under Incomplete Knowledge (BRINK). *Proceedings of EACL 2026 (long papers)*, pp. 2522–2538. DOI: [10.18653/v1/2026.eacl-long.114](https://doi.org/10.18653/v1/2026.eacl-long.114). arXiv:2508.08344 v4.
- Lee, S., Park, S., Han, W.-S. (2025). SAFE: Schema-Driven Approximate Distance Join for Efficient Knowledge Graph Querying. *Proceedings of EMNLP 2025 (main)*, pp. 17464–17489. [ACL Anthology 2025.emnlp-main.883](https://aclanthology.org/2025.emnlp-main.883).
- Luo, H., E, H., Tang, Z., Peng, S., Guo, Y., Zhang, W., Ma, C., Dong, G., Song, M., Lin, W., Zhu, Y., Luu, A. T. (2024). ChatKBQA: A Generate-then-Retrieve Framework for Knowledge Base Question Answering with Fine-tuned Large Language Models. *Findings of ACL 2024*, pp. 2039–2056. DOI: [10.18653/v1/2024.findings-acl.122](https://doi.org/10.18653/v1/2024.findings-acl.122); arXiv:2310.08975.
- Luo, L., Li, Y.-F., Haffari, G., Pan, S. (2024). Reasoning on Graphs: Faithful and Interpretable Large Language Model Reasoning (RoG). *ICLR 2024*; arXiv:[2310.01061](https://arxiv.org/abs/2310.01061).
- Gu, Y., Deng, X., Su, Y. (2023). Don't Generate, Discriminate: A Proposal for Grounding Language Models to Real-World Environments (Pangu). *Proceedings of ACL 2023 (long)*, pp. 4928–4949. DOI: [10.18653/v1/2023.acl-long.270](https://doi.org/10.18653/v1/2023.acl-long.270).
- Pourreza, M., Rafiei, D. (2023). DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction. *NeurIPS 2023*; arXiv:[2304.11015](https://arxiv.org/abs/2304.11015).
- Poggi, Lembo, Calvanese, De Giacomo, Lenzerini, Rosati (2008). Linking Data to Ontologies. *Journal on Data Semantics X*, LNCS 4900, pp. 133–173. DOI: [10.1007/978-3-540-77688-8_5](https://doi.org/10.1007/978-3-540-77688-8_5).
- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *ICLR 2023*; arXiv:[2210.03629](https://arxiv.org/abs/2210.03629).
