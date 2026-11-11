# Object provenance contract design

## Decision

Keep the existing `provenance.transformation_chain` and add an optional,
versioned `provenance_steps` graph in `DocumentExtractionContract 1.1.0`.
`transformation_chain` currently records schema lineage such as
`doc-extraction-document/1.4.0`; it has no operation identity, backend, parent
edges, or binding to emitted evidence. Reusing those strings as object refs
would change their meaning and still fail to encode the measured need.

The minimum operation model is:

```json
{
  "provenance_steps": [{
    "step_id": "prov-779c343cb6ae73ee",
    "operation": "extract_element",
    "backend": {"name": "pymupdf-native", "version": null},
    "parent_refs": []
  }],
  "elements": [{"element_id": "p0-e0", "provenance_refs": ["prov-779c343cb6ae73ee"]}]
}
```

`step_id`, operation role, backend identity, optional exact backend version,
and parent refs are the only step fields. Package source identity and run ID
scope the graph. Step refs on an element/table identify its outputs; parent
refs identify known contributing operations. Multiple refs are allowed per
object. No timestamp or full configuration snapshot is required for identity.

For table cells, omitted/null refs inherit the table's refs. An explicit empty
array means attribution is unavailable; a nonempty array overrides inherited
refs. The current producer has no cell-specific backend graph, so its cells
inherit table provenance without nine repeated pointers.

The KP validator requires unique step IDs, resolvable object and parent refs,
an acyclic graph, and no unreferenced steps. Unknown backend names are accepted
as identities; version is optional. Unknown/missing attribution stays missing
and never falls back to the run backend.

## Compatibility

KP 1.0.0 is strict and rejects unknown fields. The new reader accepts exact
`1.0.0` and `1.1.0`; other values fail closed. Legacy 1.0 packages remain
valid and serialize with their exact old wire fields. A 1.0 reader cannot
ignore a 1.1 payload, so producers must negotiate the contract version. This
is backward compatibility for old packages, not forward compatibility with
an old reader.

KP `DocumentIR.run_provenance` retains run-level backend and schema lineage
separately from `provenance_steps`. Elements, tables, and cells retain refs.
Ask/Why evidence metadata reports `run_backend` separately, resolves a single
distinct `source_backend` only when truthful, and always carries the object
provenance list. Multi-backend objects leave the scalar source backend null.
The separate EvidenceRef v1 contract is unchanged; Ask/Why evidence metadata
retains the complete refs, and EvidenceRef receives a scalar backend only when
it is unambiguous.

The producer projection uses accepted canonical per-element/table
`source_backend` fields only. Operation labels are deterministic producer
projection roles (`extract_element`, `detect_table`); they do not claim the
private acquisition/reconciliation stages. Backend version is populated only
when a producer model-version key exactly matches that backend name. The
private `ObservationLedger`, rejected candidates, and arbitration details are
not serialized.

The implementation and generated real fixtures are in the Extraction and KP
integration worktrees. Detailed mapping, tests, and remaining limits are in
[`docs/provenance/OBJECT_PROVENANCE_MAPPING.md`](OBJECT_PROVENANCE_MAPPING.md) and
[`docs/provenance/OBJECT_PROVENANCE_TEST_RESULTS.md`](OBJECT_PROVENANCE_TEST_RESULTS.md).
