# Series Brief — The Edge Cases of Intelligent Knowledge Systems

*Retrieval, Reasoning, and Trust in Enterprise AI. A six-part literature synthesis. No experiments, no new datasets, no architecture of any particular organisation. Every number below is a number a cited paper reports, in that paper's setup, or is marked as arithmetic on such numbers.*

## Thesis

A knowledge system is trustworthy to the extent that it knows the shape and the limits of what it holds. Each popular tool in the field (graphs, agents, evaluation scores) carries an assumption, and the assumption fails in predictable places that the usual benchmarks do not measure.

## Part 1 — The Graph Is a Bet, Not an Upgrade

- **Assumption stressed:** a graph is a general upgrade over vector search.
- **Central claim:** a graph is a bet that the knowledge has a shape, that the shape can be recovered, and that the questions follow it. "Graph" also names several different designs, and building a graph and retrieving over one are separate costs.
- **Evidence:**
  - GraphRAG-Bench (Xiang et al., ICLR 2026), novel corpus, reranked dense baseline: fact retrieval 60.92 for vector versus 60.14 for the best graph method; complex reasoning 42.93 versus 53.38; summarisation 51.30 versus 64.40. No BM25 or hybrid baseline and no unanswerable questions.
  - Han et al. (preprint), MultiHop-RAG, Llama-3.1-8B: temporal questions 30.70 for vector versus 50.60 for the community-based graph method, but null questions 96.01 versus 80.07. Construction time 135 seconds for plain RAG versus 5,560 and 7,702 seconds for the community-based and triple-extraction variants.
  - In Han et al.'s setup only about 65% of answer entities reach the graph the triple-extraction method builds, which caps what any retriever over it can do.
- **Design implication:** start from the question mix, establish the strongest non-graph baseline first, measure extraction recall before building, route rather than replace, and price maintenance.
- **Handoff:** the bet can fail by omission, through edges that should be there and are not.

## Part 2 — The Edge That Isn't There

- **Assumption stressed:** the store is a faithful mirror of the domain.
- **Central claim:** a missing assertion is not a negative one. Missing, unknown, truly absent, explicitly negated and wrongly asserted are different situations, and a system that merges them will confidently misreport.
- **Evidence:**
  - BRINK (Zhou et al., EACL 2026): mines rules from graphs, removes the conclusion triples while keeping the premises, and tests six KG-RAG methods over three datasets. Performance drops noticeably in most cases; trained methods drop less on hard answers than untrained ones, by the paper's own grouping.
  - BRINK's label experiment: real text labels help, while entity IDs perform about as well as random IDs, so models may lean on memory of named entities. My inference: public-benchmark robustness may overstate robustness on private graphs.
  - BRINK does not measure abstention and its incompleteness is simulated. Abstention evidence across the reviewed benchmarks is thin and mixed.
- **Design implication:** declare completeness per relation and scope with an owner and review date, give answers three states (established, established not to hold, cannot be established), and test refusal explicitly.
- **Handoff:** a store can fail a second way, by holding two answers where it should hold one.

## Part 3 — Claims, Not Documents

- **Assumption stressed:** relevance approximates truth, and relevant passages agree.
- **Central claim:** enterprise knowledge is claims with source, scope, authority and time. "Prefer the newest" breaks when scope, authority or the direction of time differ.
- **Evidence:**
  - HoH (Ouyang et al., ACL 2025), three open models, one relevant plus one distractor, then an outdated version added: score falls from 89.12 to 67.00 (Llama 70B), 85.70 to 48.18 (Llama 8B) and 76.31 to 34.57 (Qwen 7B), about 22, 38 and 42 points (my arithmetic).
  - DRAGged (Cattan et al., preprint): the right behaviour depends on conflict type. Giving the model the conflict type lifts scores by about 21 to 28 points across six configurations (my arithmetic), though the prompt may also carry instruction, so recognition is not isolated.
  - Re³ (Cao et al., ACL 2026): 0.8732 accuracy on finding the latest forecast, against 0.6975 for the strongest baseline. The group built the benchmark, and the authors state the method is designed for "now-focused" queries.
- **Design implication:** keep publication, valid and recorded time apart, record supersession with scope and authority, classify the conflict before answering, show unresolved disagreement, and test with supersession pairs.
- **Handoff:** once claims have structure, how should a system move through it?

## Part 4 — Maps Before Walking

- **Assumption stressed:** a capable model will find its own way through a graph.
- **Central claim:** in a dense, schema-governed graph, agents can fail by search explosion and semantic drift. Treat the schema as a constraint on action, not as documentation.
- **Evidence:**
  - SCAIR (Chaturvedi et al., ACL 2026 Industry): templated questions over one manufacturing configuration database. Accuracy 35.14 against 25.27 for the strongest baseline (G-Retriever, fine-tuned by the authors on this benchmark). A stronger language model improved answer generation but did not prevent search explosion ("architectural, not parametric").
  - Cost: about 42 model calls per question against about 14 for ToG and 5.6 for PoG.
  - Neighbouring work (SAFE, ChatKBQA, RoG, Pangu, DIN-SQL, ontology-based data access) uses the schema to shrink the model's job to choosing or repairing. It was not evaluated on SCAIR-style graphs.
- **Design implication:** prune by structure before ranking by meaning, enforce constraints in tools, watch hub nodes, version the schema, and keep a non-agentic baseline. The four schema-use patterns (description, planner, guard, repair) are the author's framing, untested.
- **Evidence limit:** one benchmark, one group, no non-agentic baseline, so how much agency is worth remains open.
- **Handoff:** how much freedom should retrieval be given, and what should it cost?

## Part 5 — When to Stop Searching, and What It Costs

- **Assumption stressed:** more autonomy in retrieval means better retrieval.
- **Central claim:** agentic retrieval is a cost and benefit decision with a stopping rule, not a free upgrade.
- **Evidence:**
  - AgenticRAG (Suresh et al., preprint, no code), BRIGHT long-document split: Recall@1 of 49.59 against 8.41 for the paper's single-shot search is the headline 5.9×. Against the best embedding model in the same table (27.8) it is about 1.8× (my arithmetic).
  - FinanceBench, 150 questions: 92.00 against 24.24 for an undescribed "traditional RAG" baseline and 32.71 for an agent with keyword tools. Tokens per query 14.7K for single-shot search versus 114.8K.
  - A narrow ablation (GPT-5-mini only, run count not stated) changed tool calls from 4.79 to 6.79 with recall comparable. Routing work (Adaptive-RAG, Self-RAG) decides whether or how much to retrieve, not when to stop.
- **Design implication:** report the baseline with every ratio, measure quality per unit cost, make the deterministic path the default, design the stopping rule and the give-up message, log routing, and test the unanswerable tail. My reasoning: a wrongly cheap route fails quietly, a wrongly expensive one costs money.
- **Handoff:** if each part can fail alone, what makes the whole trustworthy?

## Part 6 — Trust Is Not a Component

- **Assumption stressed:** trust is a scalar score that rises as components improve.
- **Central claim:** trust shows up as properties along nine dimensions that interact and sometimes conflict, so improving one can reduce another. No composite score.
- **Evidence:** the evaluations reviewed barely measure dimension 7 (uncertainty, calibration and escalation) and measure cost, lifecycle change and attribution unevenly. ALCE (Gao et al.) shows attribution can be measured. Zheng et al. report that strong LLM judges reach over 80% agreement with human preferences but show position, verbosity and self-enhancement biases.
- **Design implication:** write a trust profile per use, with minimum acceptable behaviour per dimension, and test each dimension with its own probe.

### The framework (the author's own synthesis, not validated)

- **Six components:** Representation, Retrieval, Evidence, Reasoning, Constraints, Behaviour. They form a connected graph, not a stack; the edges are illustrative.
- **Nine dimensions:** 1 Retrieval effectiveness; 2 Completeness; 3 Validity; 4 Constraint adherence; 5 Evidence grounding; 6 Source traceability; 7 Uncertainty, calibration and escalation; 8 Efficiency (including run-to-run variance); 9 Maintainability.
- **Mapping (primary dimensions):** Representation → 2, 9; Retrieval → 1, 8; Evidence → 3, 6; Reasoning → 5; Constraints → 4; Behaviour → 7.
- **Key distinction:** grounded means supported by the evidence; traceable means a reader can check it.
- **Interactions:** better retrieval over an incomplete store makes the wrong answer more convincing; a citation to a superseded document is traceable and invalid; an agent out of budget must choose between guessing and declining.

## Figures and tables that could become slide visuals

1. Part 1: five-approach table (where the graph comes from; what retrieval does with it).
2. Part 1: vector versus graph comparison table by question type, with a note that the two studies are not comparable across rows.
3. Part 2: the five absence states (what is true, what the store contains, right behaviour).
4. Part 2: BRINK's three graph versions (text labels, entity IDs, random IDs) as a simple comparison.
5. Part 3: HoH score before and after the outdated document, three models.
6. Part 3: resolve-when-loading versus resolve-at-query-time table.
7. Part 4: the four schema-use patterns (description, planner, guard, repair) with their failure surfaces.
8. Part 5: AgenticRAG table showing the same agent against three baselines, with the ratios.
9. Part 5: anatomy-of-cost table (tokens, latency, calls, variance, debuggability).
10. Part 6: component diagram (Mermaid source, with SVG export if produced).
11. Part 6: nine-dimension table and component-to-dimension mapping.
12. Part 6: the invented two-use trust profile.
