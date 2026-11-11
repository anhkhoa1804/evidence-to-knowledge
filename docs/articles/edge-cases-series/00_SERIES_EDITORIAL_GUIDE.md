# Series Editorial Guide — The Edge Cases of Intelligent Knowledge Systems

**Subtitle:** Retrieval, Reasoning, and Trust in Enterprise AI

## 1. Positioning

A six-part editorial series on where retrieval-based knowledge systems for organisations *stop working as advertised*. It is a synthesis of published research, not a report of experiments. No article reports new measurements, and none uses any particular company's, product's or repository's architecture as evidence. Every number that appears is a number a cited paper reports, tied to that paper's setup.

The series does not argue that retrieval-augmented generation, graphs or agents are bad. Its stance is narrower: each of these tools carries an assumption, and the assumption fails in predictable places. The articles name the assumption, show where it breaks, and say what the literature does and does not establish.

**Final title:** *The Edge Cases of Intelligent Knowledge Systems*
**Subtitle:** *Retrieval, Reasoning, and Trust in Enterprise AI*

(Titles such as "Beyond RAG" and "The Future of AI" were deliberately avoided: they promise a destination the evidence does not support. The three alternative titles proposed in the first draft were dropped when the title was finalised.)

## 2. Audience

Engineers, architects and technical leads who build or buy retrieval, graph or agent-based knowledge systems for enterprises, and researchers who want a critical map of adjacent literature. Assumed: they know what RAG and a knowledge graph are. Not assumed: familiarity with any specific benchmark. Each article explains what it needs in a sentence or two.

## 3. Themes and the progression

One argument runs through all six articles: **a knowledge system is trustworthy to the extent that it knows the shape and the limits of what it holds.**

| # | Article | Question it asks | Central claim |
|---|---------|------------------|---------------|
| 1 | Graph vs Vector | *What does structure buy, and what does it cost?* | Graphs are a bet on the shape of knowledge and of questions, not a universal upgrade. |
| 2 | Incomplete Knowledge | *What if the answer is not in the store?* | A system must represent what its knowledge cannot establish; absence of evidence is not evidence of absence. |
| 3 | Conflicting Knowledge | *What if the store disagrees with itself?* | Enterprise knowledge is claims with source, scope, authority and time — not just relevant documents. |
| 4 | Schema-Aware Agents | *How should an agent move through structured knowledge?* | Enterprise reasoning needs structure and constraints, applied before semantic similarity. |
| 5 | Agentic Retrieval | *Should the system decide how to search?* | Autonomous retrieval is not inherently better retrieval; it is a cost/benefit decision with stopping rules. |
| 6 | Trustworthy Knowledge Systems | *How do the pieces add up?* | Trust emerges from the interaction of representation, retrieval, reasoning, evidence, constraints and behaviour. |

**Connective tissue.** 1 → 2: if structure is a bet, the bet can fail by omission. 2 → 3: knowledge can be present and still disagree. 3 → 4: resolving disagreement needs structure (scope, type, authority) to reason over. 4 → 5: once an agent can traverse structure, who decides when to stop? 5 → 6: every earlier edge case is a dimension of one trust picture.

Each article ends with a short handoff sentence pointing at the next. Each article connects to the previous one in its opening, by a sentence or a scene, and names the assumption it will stress.

## 4. Terminology (fixed across the series)

| Term | Meaning in this series |
|------|------------------------|
| **Vector RAG / hybrid RAG** | Retrieval over text chunks by embedding similarity (vector) or embedding plus lexical (hybrid). |
| **KG-RAG** | Retrieval and reasoning over a *pre-existing* knowledge graph (RoG, G-Retriever, ToG, …). Graph is given. |
| **GraphRAG (Microsoft-style)** | An LLM *builds* an entity graph and community summaries from text; queries use those. Graph is constructed. |
| **Triple-extraction GraphRAG** | The name used here for the variants that Han et al. call "KG-GraphRAG": the graph is built by extracting triples from text. It is a constructed graph, so it is not KG-RAG. |
| **Graph construction vs graph retrieval** | Two different costs and failure surfaces; never merged. |
| **Absence states (five)** | *Missing*: true in the world but not in the store. *Unknown*: the store cannot establish whether it holds. *Truly absent*: does not hold, and nothing says otherwise. *Explicitly negated*: the store records that it does not hold. *Wrongly asserted*: the store records it, but it is false. Each needs a different response, so they are never collapsed into one "not found". |
| **Claim** | A statement with source, scope, authority and time attached — the unit of Article 3. |
| **Valid time / recorded time / publication time** | When a fact holds in the world / when the system recorded it ("transaction time" in database literature; noted once in Part 3, "recorded time" everywhere else) / when a source was published. |
| **Supersession** | A claim replaces another *within a scope*, by adoption. A later date alone does not imply it. |
| **Schema-aware** | Reasoning that uses types, relations and constraints to restrict what it does, not only to describe the data. |
| **Agentic retrieval** | A model chooses retrieval actions over several steps (search, open, read, refine) and decides when to stop. |
| **Abstention** | The system declines to answer, or states what it cannot establish. |
| **Trust dimension** | One of nine properties in Article 6; never aggregated into a score. Names: 1 retrieval effectiveness; 2 completeness; 3 validity; 4 constraint adherence; 5 evidence grounding; 6 source traceability; 7 uncertainty, calibration and escalation; 8 efficiency (including run-to-run variance); 9 maintainability. Dimension 4 was "Schema consistency" and dimension 7 was "Uncertainty and abstention" in earlier drafts. |
| **Grounding vs traceability** | Grounded: the answer is supported by the retrieved evidence. Traceable: a reader can check which evidence supports which statement. A system can have the first without the second. |

## 5. Evidence discipline

Every substantive claim belongs to one of four kinds. The kinds are an editorial discipline for the author and reviewer; they are **not shown to readers as markers**. In the published prose the distinction is carried by wording:

- **Established results** are attributed to their source and setup ("the authors report, under their setup, that…").
- **Limitations** are stated plainly, in the same place as the result they qualify ("the benchmark has no unanswerable questions", "this is a preprint").
- **The author's interpretation** is signalled by language such as "my reading", "this suggests", "in practice".
- **Engineering recommendations** appear in design sections introduced as suggestions, not tested results.

Hedges appear once, where the inference is first made, not on every later mention. Preprints are named as preprints. Where two papers share authors (BRINK/SCAIR; HoH/Re³), the article says so and does not count them as independent confirmation. Frameworks proposed in the series (the schema-use framing in Part 4, the six components and nine dimensions in Part 6) are labelled as the author's own synthesis.

Invented scenarios are always labelled **"Illustrative example (invented)"**. They contain no quantities that could be mistaken for evidence. Articles name no company, product or repository as a case; third-party names appear only as cited sources or methods.

## 6. Citation conventions

- Inline: (Author et al., Year), with a `[venue]` flag at first mention when it matters (e.g. "preprint").
- Each article ends with a three-line **Key takeaways** box (no claims that are not in the body), then **Reading notes** (reader-facing: what was read at what depth, and what the article could not verify), then **References** (every cited source, full author lists, no "see Part N" stand-ins). The master bibliography (`07_MASTER_BIBLIOGRAPHY.md`) is the union of the six reference lists.
- Only sources actually inspected are cited. Reading depth is recorded in the bibliography. Nothing is cited from memory alone.
- Numbers are quoted only from the source, with the setup that produced them. Ratios are never presented without their denominator (e.g. "5.9× versus the paper's own single-shot baseline").

## 7. Style

- Open with a tension, not a definition. One concrete scene or puzzle, then the assumption beneath it.
- Plain sentences; one idea per paragraph; jargon explained on first use.
- Each article contains at least one serious counterargument, stated in its strongest form before being answered — or left unanswered.
- Admit uncertainty. "The paper does not measure this" is a finding, not an omission.
- Prefer a mechanism to a slogan. Avoid "revolutionary", "game-changing", "paradigm shift".
- Length: 1,500–2,500 words per article. Counting method: the body is everything before the Key takeaways box, including the title, the series line and table cells, and excluding the takeaways, the reading notes and the references. Words are whitespace-separated tokens.
- Structure: opening tension → the assumption → where it breaks → what the research says → deeper analysis → design implications → open questions → conclusion.

## 8. What the series does not do

It does not run experiments, generate datasets, implement retrievers, rank vendors, or present any single organisation's system as a case study. It does not claim a universal best practice. Where the evidence is thin, it says so and stops.
