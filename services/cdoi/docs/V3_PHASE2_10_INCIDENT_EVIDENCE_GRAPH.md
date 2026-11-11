# V3 Phase 2.10 — Incident Evidence Graph

IncidentEvidenceGraph is an ephemeral, incident-scoped, deterministic fusion of an EvidenceSnapshot. It is not the canonical KG, an approved ontology, static topology, a trace execution graph, or a causal graph.

The graph uses incident, entity, event, change, metric observation, and trace span nodes. Edges are bounded to incident membership, exact entity ownership, static relation, and declared trace parent-child structure. Timestamps remain node attributes; no dense pairwise temporal graph is created.

Static topology means declared component relation. Trace execution graph means request-level declared span hierarchy. Incident evidence graph means typed incident-scoped evidence fusion. Causal graph is not implemented.

CauseCandidate is an unranked, unevaluated hypothesis eligibility record. It contains a subject entity node, explicit generation rule, supporting evidence IDs, context evidence IDs, empty-ready contradictory evidence IDs, graph ID, and incident ID. It has no score, rank, probability, likely/root-cause status, or commitment path.

Phase 2.10 uses only CHANGE_AFFECTS_INCIDENT_ENTITY_V1, ERROR_EVENT_ON_INCIDENT_ENTITY_V1, and ERROR_TRACE_SPAN_ON_INCIDENT_ENTITY_V1. Candidate does not mean cause; association, temporal precedence, trace traversal, and ERROR evidence do not mean causality or root cause. Future evaluation labels must remain outside snapshot, graph, and candidate input artifacts to prevent leakage.
