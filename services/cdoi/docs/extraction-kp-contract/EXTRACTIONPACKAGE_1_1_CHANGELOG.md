# ExtractionPackage 1.1.0 change log

`DocumentExtractionContract` 1.1.0 adds accepted object-to-operation
provenance refs while retaining the 1.0 package fields and meanings.

- Added `provenance_steps[]` with unique `step_id`, operation role, backend
  name/optional exact version, and parent refs.
- Added optional `provenance_refs[]` to elements and tables. Cell refs are
  optional: null/omitted inherits table refs; `[]` explicitly means unknown.
- KP validates dangling object/parent refs, unique IDs, cycles, and orphan
  steps. Unknown backend identities and null versions are allowed.
- KP 1.1 reader continues to ingest exact 1.0.0 payloads. A 1.0 reader stays
  strict and must reject 1.1 payloads; legacy producer serialization omits all
  1.1 fields.
- `transformation_chain` continues to mean schema/transformation lineage; it
  is not reinterpreted as the operation graph.
- KP `DocumentIR`, semantic evidence, and Why metadata preserve the refs.
  EvidenceRef v1 remains unchanged and gets a scalar object backend only when
  it is unambiguous. `run_backend` is distinct from object-level `source_backend`.

The producer currently projects only backends already present on accepted
canonical elements/tables. It does not expose the private ObservationLedger.
The measured PDF suite confirms native text and table evidence resolve to
different backend steps. Multi-ref behavior is contract-tested synthetically,
not claimed as a naturally measured producer output.
