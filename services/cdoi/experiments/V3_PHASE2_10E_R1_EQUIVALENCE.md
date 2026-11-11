# V3 Phase 2.10E-R1 Equivalence

On the existing Phase 2.10 preprocessing_demo incident, the exhaustive graph
and the SQLite scalable view produce exact equal CauseCandidate artifacts:
candidate IDs, kinds, subjects, rule IDs, supporting evidence IDs, context
evidence IDs, contradictory evidence IDs, status, schema version, and order.

The small-fixture view uses the exhaustive graph ID solely to make the
identity comparison exact. The high-volume view has its own explicitly
versioned logical-view graph ID because it does not serialize hundreds of
thousands of graph objects. That serialization difference does not change
eligibility, grouping, support, context, or provenance semantics.

Chunk sizes 1, 2, and 100 were checked on the fixture. The SQLite trace index
and candidate result are deterministic and input-order-independent.
