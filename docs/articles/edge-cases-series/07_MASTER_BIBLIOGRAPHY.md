# Master Bibliography

The union of the six article reference lists: 35 sources, each with publication status, how deeply it was read, and which articles cite it. Titles, authors and venues match the article reference lists. Nothing is included from memory alone.

**Status key:** *Peer-reviewed* = published in a refereed venue, as shown on the venue's own page or the ACL Anthology / publisher record. *Preprint* = arXiv or similar, not peer-reviewed as far as verified. *Book chapter / classic* = pre-arXiv publication.

**Read-depth key:** **FULL** = body text, tables and limitations read. **PARTIAL** = main sections and key tables read; the rest summarised or not examined. **ABSTRACT** = abstract, introduction or search-result summary only. **META** = bibliographic metadata and, where noted, the author list only.

**Independence note.** BRINK and SCAIR share five authors (Zhu, H. Zhou, D. Zhou, Staab, Kharlamov); arXiv:2504.05163 comes from an overlapping group. HoH and Re³ share two authors (Ouyang and Cheng). Each pair counts as one line of evidence, not two.

---

## A. Retrieval structure (Part 1)

| Source | Status | Venue / ID | Read depth | Cited in |
|---|---|---|---|---|
| Edge, D., Trinh, H., Cheng, N., Bradley, J., Chao, A., Mody, A., Truitt, S., Metropolitansky, D., Ness, R. O., Larson, J. (2024). *From Local to Global: A Graph RAG Approach to Query-Focused Summarization.* | Preprint | arXiv:2404.16130 (v1 Apr 2024; v2 Feb 2025); no venue stated | ABSTRACT | 1 |
| Xiang, Z., Wu, C., Zhang, Q., Chen, S., Hong, Z., Huang, X., Su, J. (2026). *When to use Graphs in RAG: A Comprehensive Analysis for Graph Retrieval-Augmented Generation* (GraphRAG-Bench). | Peer-reviewed (ICLR 2026, poster) | arXiv:2506.05690 (v3, Feb 2026); code github.com/GraphRAG-Bench/GraphRAG-Benchmark | PARTIAL (setup and results tables read; internal inconsistencies noted in Part 1) | 1, 2, 6 |
| Han, H., Ma, L., Wang, Y., Shomer, H., Lei, Y., Qi, Z., Guo, K., Hua, Z., Long, B., Liu, H., Aggarwal, C. C., Tang, J. (2025). *RAG vs. GraphRAG: A Systematic Evaluation and Key Insights.* | Preprint | arXiv:2502.11371 (v1 Feb 2025; v3 Mar 2026); no venue stated; code github.com/haoyuhan1/RAGvsGraphRAG | PARTIAL (v3 main text and the MultiHop-RAG and Natural Questions tables; construction-time figures and the answer-entity-coverage appendix at summary level; how the null questions are built or scored not inspected) | 1, 2, 6 |

## B. Incompleteness and abstention (Part 2)

| Source | Status | Venue / ID | Read depth | Cited in |
|---|---|---|---|---|
| Reiter, R. (1978). On Closed World Data Bases. In H. Gallaire and J. Minker (eds.), *Logic and Data Bases*, Plenum Press, pp. 55–76. | Book chapter / classic | DOI 10.1007/978-1-4684-3384-5_3 | META (cited for the closed-world definition only) | 2 |
| Zhou, D., Zhu, Y., Wang, X., Zhou, H., He, Y., Chen, J., Staab, S., Kharlamov, E. (2026). What Breaks Knowledge Graph based RAG? Benchmarking and Empirical Insights into Reasoning under Incomplete Knowledge (BRINK). | Peer-reviewed (EACL 2026, long papers, pp. 2522–2538) | DOI 10.18653/v1/2026.eacl-long.114; arXiv:2508.08344 v4 | FULL (including appendices; figure contents not examined) | 2, 4, 6 |
| Zhou, D., Zhu, Y., Wang, X., He, Y., Chen, J., Staab, S., Kharlamov, E. (2025). *Evaluating Knowledge Graph Based Retrieval Augmented Generation Methods under Knowledge Incompleteness.* | Preprint | arXiv:2504.05163 (v2, Aug 2025); arXiv comment says "IRISAI'25", no acceptance statement | META (abstract and author list only) | 2 |
| Liu, J., Shao, P., Qin, W., Liu, F., Yang, Y., Hong, R. (2025). *Debate over Mixed-knowledge: A Robust Multi-Agent Reasoning Framework for Incomplete Knowledge Graph Question Answering.* | Preprint | arXiv:2511.12208; no venue stated | META (abstract and author list only) | 2 |
| Wen, B., Yao, J., Feng, S., Xu, C., Tsvetkov, Y., Howe, B., Wang, L. L. (2025). Know Your Limits: A Survey of Abstention in Large Language Models. | Peer-reviewed (*Transactions of the ACL* 13, 529–556) | DOI 10.1162/tacl_a_00754 | ABSTRACT | 2, 6 |

## C. Conflict, time and validity (Part 3)

| Source | Status | Venue / ID | Read depth | Cited in |
|---|---|---|---|---|
| Xu, R., Qi, Z., Guo, Z., Wang, C., Wang, H., Zhang, Y., Xu, W. (2024). Knowledge Conflicts for LLMs: A Survey. | Peer-reviewed (EMNLP 2024, pp. 8541–8565) | DOI 10.18653/v1/2024.emnlp-main.486 | ABSTRACT | 3 |
| Cattan, A., Jacovi, A., Ram, O., Herzig, J., Aharoni, R., Goldshtein, S., Ofek, E., Szpektor, I., Caciularu, A. (2025). *DRAGged into Conflicts: Detecting and Addressing Conflicting Sources in Search-Augmented LLMs.* | Preprint | arXiv:2506.08500 (v2, Jun 2025); no venue stated; code/data github.com/google-research-datasets/rag_conflicts | PARTIAL (main results and setup, v2; exact oracle prompt wording not examined) | 3, 6 |
| Ouyang, J., Pan, T., Cheng, M., Yan, R., Luo, Y., Lin, J., Liu, Q. (2025). HoH: A Dynamic Benchmark for Evaluating the Impact of Outdated Information on Retrieval-Augmented Generation. | Peer-reviewed (ACL 2025, long, pp. 6036–6063) | DOI 10.18653/v1/2025.acl-long.301 | FULL (including results tables) | 2, 3, 6 |
| Nakshatri, N. S., Roy, S., Arivazhagan, M. G., Zhou, H., Bannihatti Kumar, V., Gangadharaiah, R. (2025). *When Facts Change: Probing LLMs on Evolving Knowledge with evolveQA.* | Preprint ("under submission") | arXiv:2510.19172 (v2, Nov 2025) | ABSTRACT | 3 |
| Cao, J., Ouyang, J., Cheng, M., Zhou, Z., Liu, C., Li, Y., Liu, Z., Wang, S. (2026). Re3: Relevance & Recency Retrieval for Mitigating Temporal Hallucination. | Peer-reviewed (ACL 2026, long, pp. 25735–25760) | DOI 10.18653/v1/2026.acl-long.1180 | PARTIAL (main text and results tables) | 3, 6 |
| Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J., Chalef, D. (2025). *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* | Preprint (vendor authors) | arXiv:2501.13956 (v1, Jan 2025) | ABSTRACT | 3 |
| Wang, H., Prasad, A., Stengel-Eskin, E., Bansal, M. (2025). Retrieval-Augmented Generation with Conflicting Evidence (MADAM-RAG). | Peer-reviewed (COLM 2025, per the arXiv v2 record; proceedings page not located) | arXiv:2504.13079 (v2, Aug 2025) | ABSTRACT | 3 |
| Snodgrass, R., Ahn, I. (1985). A Taxonomy of Time in Databases. | Peer-reviewed (ACM SIGMOD 1985, pp. 236–246) | — | META | 3 |
| Doyle, J. (1979). A Truth Maintenance System. | Peer-reviewed (*Artificial Intelligence* 12, 231–272) | — | META (cited for the idea only) | 3 |

## D. Schema-aware agents (Part 4)

| Source | Status | Venue / ID | Read depth | Cited in |
|---|---|---|---|---|
| Chaturvedi, P., Zhu, Y., Zhou, H., Zhou, D., He, Y., Staab, S., Du, F., Tang, J., Kharlamov, E. (2026). SCAIR: Schema-Conditioned Agentic Iterative Reasoning for Enterprise Knowledge Graphs. | Peer-reviewed (ACL 2026, Industry Track, pp. 1089–1104) | DOI 10.18653/v1/2026.acl-industry.76 | FULL (the ablation's values are in a figure that could not be extracted) | 2, 4, 5, 6 |
| Lee, S., Park, S., Han, W.-S. (2025). SAFE: Schema-Driven Approximate Distance Join for Efficient Knowledge Graph Querying. | Peer-reviewed (EMNLP 2025, main, pp. 17464–17489) | ACL Anthology 2025.emnlp-main.883 | FULL | 4 |
| Luo, H., E, H., Tang, Z., Peng, S., Guo, Y., Zhang, W., Ma, C., Dong, G., Song, M., Lin, W., Zhu, Y., Luu, A. T. (2024). ChatKBQA: A Generate-then-Retrieve Framework for Knowledge Base Question Answering with Fine-tuned Large Language Models. | Peer-reviewed (Findings of ACL 2024, pp. 2039–2056) | DOI 10.18653/v1/2024.findings-acl.122; arXiv:2310.08975 | ABSTRACT | 4 |
| Luo, L., Li, Y.-F., Haffari, G., Pan, S. (2024). Reasoning on Graphs: Faithful and Interpretable Large Language Model Reasoning (RoG). | Peer-reviewed (ICLR 2024) | arXiv:2310.01061 | ABSTRACT | 4 |
| Gu, Y., Deng, X., Su, Y. (2023). Don't Generate, Discriminate: A Proposal for Grounding Language Models to Real-World Environments (Pangu). | Peer-reviewed (ACL 2023, long, pp. 4928–4949) | DOI 10.18653/v1/2023.acl-long.270 | ABSTRACT | 4 |
| Pourreza, M., Rafiei, D. (2023). DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction. | Peer-reviewed (NeurIPS 2023) | arXiv:2304.11015 | ABSTRACT | 4 |
| Poggi, Lembo, Calvanese, De Giacomo, Lenzerini, Rosati (2008). Linking Data to Ontologies. | Peer-reviewed (*Journal on Data Semantics X*, LNCS 4900, pp. 133–173) | DOI 10.1007/978-3-540-77688-8_5 | META (author initials not verified) | 4 |
| Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. | Peer-reviewed (ICLR 2023) | arXiv:2210.03629 | ABSTRACT | 4 |

## E. Agentic retrieval (Part 5)

| Source | Status | Venue / ID | Read depth | Cited in |
|---|---|---|---|---|
| Su, H., Yen, H., Xia, M., Shi, W., Muennighoff, N., Wang, H., Liu, H., Shi, Q., Siegel, Z. S., Tang, M., Sun, R., Yoon, J., Arik, S. O., Chen, D., Yu, T. (2025). BRIGHT: A Realistic and Challenging Benchmark for Reasoning-Intensive Retrieval. | Peer-reviewed (ICLR 2025) | arXiv:2407.12883 | ABSTRACT (the figures cited are from the proceedings abstract) | 5 |
| Suresh, S., Mak, H., Chou, S., Kroon, F., Bhatnagar, S. (2026). *AgenticRAG: Agentic Retrieval for Enterprise Knowledge Bases.* | Preprint (no code) | arXiv:2605.05538 (v1, 7 May 2026) | FULL (body, main tables and most of the appendix; the paper does not describe its "traditional RAG" baseline) | 5, 6 |
| Jeong, S., Baek, J., Cho, S., Hwang, S. J., Park, J. C. (2024). Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question Complexity. | Peer-reviewed (NAACL 2024) | DOI 10.18653/v1/2024.naacl-long.389; arXiv:2403.14403 | ABSTRACT | 5 |
| Asai, A., Wu, Z., Wang, Y., Sil, A., Hajishirzi, H. (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. | Peer-reviewed (ICLR 2024; status taken from an earlier check, not re-verified) | arXiv:2310.11511 | ABSTRACT | 5 |
| Yang, T., Yao, Z., Jin, B., Cui, L., Li, Y., Wang, G., Liu, X. (2025). Demystifying and Enhancing the Efficiency of Large Language Model Based Search Agents (SearchAgent-X). | Preprint | arXiv:2505.12065 | ABSTRACT | 5 |
| Hadad, G., Iskander, S., Kalinsky, O., Tolmach, S., Levy, R., Roitman, H. (2026). HotelQuEST: Balancing Quality and Efficiency in Agentic Search. | Peer-reviewed (EACL 2026, Industry Track) | ACL Anthology 2026.eacl-industry.16; arXiv:2602.23949 | ABSTRACT (author order follows the arXiv listing; not checked against the Anthology) | 5 |
| Sharifymoghaddam, S., Lin, J. (2026). Rerank Before You Reason: Analyzing Reranking Tradeoffs through Effective Token Cost in Deep Search Agents. | Peer-reviewed (Findings of ACL 2026, pp. 25874–25886) | arXiv:2601.14224 | ABSTRACT | 5 |

## F. Trustworthiness and evaluation (Part 6)

| Source | Status | Venue / ID | Read depth | Cited in |
|---|---|---|---|---|
| Gao, T., Yen, H., Yu, J., Chen, D. (2023). Enabling Large Language Models to Generate Text with Citations (ALCE). | Peer-reviewed (EMNLP 2023, pp. 6465–6488) | arXiv:2305.14627 | ABSTRACT | 6 |
| Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., Stoica, I. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. | Peer-reviewed (NeurIPS 2023; venue not re-verified) | arXiv:2306.05685 | ABSTRACT (the 80% agreement figure is the paper's own claim) | 6 |
| Zhou, Y., Zhang, W., Shao, J., Liu, Y., Li, X., Jin, J., Qian, H., Liu, Z., Li, C., Zhang, J. C., Dou, Z., Yu, P. S., Mao, J. (2024). *Trustworthiness in Retrieval-Augmented Generation Systems: A Survey.* | Preprint | arXiv:2409.10102 (v1 Sep 2024; v2 May 2026); no venue stated; author list varies by version | META | 6 |

---

## Collected but not cited

| Source | Reason |
|---|---|
| Xiong et al., *Experience-following in agent memory* (ACL 2026 long, pp. 623–645; DOI 10.18653/v1/2026.acl-long.27; arXiv:2505.16067) | Tasks are not enterprise knowledge; kept out to preserve focus. |
| arXiv:2509.14608 (position paper on participant-aware access control) | Preprint, not read in depth; permission-aware retrieval is outside the six arguments. |
| GoG (arXiv:2404.14741) | Mentioned in BRINK's appendix; not needed. |

## Known gaps in verification

Resolved during editing and no longer open: the Han et al. figures and their variant labels, the BRINK method grouping and failure ratio, the HoH and DRAGged results, the Re³ metric label, and the AgenticRAG ablation scope.

Still open:

- **Abstract or metadata level only:** Edge et al., Wen et al., Xu et al., evolveQA, Zep, MADAM-RAG, Snodgrass and Ahn, Doyle, ChatKBQA, RoG, Pangu, DIN-SQL, Poggi et al., ReAct, BRIGHT, Adaptive-RAG, Self-RAG, SearchAgent-X, HotelQuEST, Rerank Before You Reason, ALCE, the LLM-as-judge paper, the trustworthiness survey, arXiv:2504.05163 and arXiv:2511.12208. Claims drawn from them are limited to what those texts support.
- **Han et al.:** construction-time figures checked at summary level only; how the null questions are built or scored was not inspected.
- **GraphRAG-Bench:** figures were not re-read after the first pass.
- **DRAGged:** the exact oracle prompt wording was not examined; no venue was found.
- **SCAIR:** the train/test split and the ablation values (in a figure) were not extracted.
- **Venues taken without a second check:** MADAM-RAG (COLM 2025, from the arXiv record), Self-RAG (ICLR 2024), the LLM-as-judge paper (NeurIPS 2023), the trustworthiness survey (no venue; author list varies by version).
- **Author details:** Poggi et al. are given by surname only; the HotelQuEST author order follows arXiv; the evolveQA author "Bannihatti Kumar, V." follows the arXiv listing.
- **AgenticRAG:** two reported split discrepancies (Stack Overflow/ReDI and BM25) from an earlier read were not re-checked.
- No forward-citation check ("does later work challenge it?") was performed systematically for any source.
