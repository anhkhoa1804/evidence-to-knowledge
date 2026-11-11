# V3 Phase 2.10E-R1 Scalability Diagnosis

The prior exhaustive path represented 246,079 selected trace spans as Python
normalized objects, snapshot data, graph nodes, association edges, membership
edges, and sorted graph serialization. An exploratory attempt reached roughly
825 MB working set before a complete candidate result; this is graph/object
overhead rather than a semantic or GPU limitation.

The R1 SQLite store reads 391,997 raw trace rows, validates 391,997, and
indexes all 246,079 fixed-window rows. It does not sample or collapse spans.
The first Windows run completed in 22.24 seconds (11,065 spans/s) and wrote a
154,402,816-byte SQLite index. Peak process memory is NOT_MEASURED in the
portable runner; index size and wall-clock are recorded in SCALABILITY.json.

The logical graph is complete because every selected span is addressable by
evidence ID, service, trace, parent, status, time, and provenance. Only
candidate-relevant indexed query results are materialized.
