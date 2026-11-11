# V3 Phase 2.9 Trace Demo

The inc-001 ONE_HOP snapshot includes 3 entities, 2 static relations, 2 events, 2 changes, 7 metrics, 12 trace spans, and 6 trace execution graphs.

The trace provenance example is span-payment: snapshot span to normalized evidence ev-955dd4780931908afc17392b to raw evidence ev-955dd4780931908afc17392b to traces/spans.jsonl record 2 to the manifest.

The overlap-start and overlap-end spans are included. The fully outside span and audit-service span are excluded by the existing time/entity scope; trace scope does not expand from an execution edge.

Temporal ordering plus trace traversal != causality.
