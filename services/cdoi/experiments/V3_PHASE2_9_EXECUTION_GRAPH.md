# V3 Phase 2.9 Execution Graph

The graph artifact is experiments/archive/v3_phase2_9/EXECUTION_GRAPH.json. It holds declared span hierarchy only.

The incident snapshot has six selected trace graphs and twelve selected spans. Trace-001 retains three in-scope parent-child edges and one observed branch. Its status remains PARTIAL_UNRESOLVED_SERVICE because the source trace also contains an unresolved-service span that the incident scope excludes. Trace-002 is PARTIAL_MISSING_PARENT. Trace-004 is PARTIAL_PARENT_CYCLE and has no traversable edges.

Static topology != execution path != causal path.
