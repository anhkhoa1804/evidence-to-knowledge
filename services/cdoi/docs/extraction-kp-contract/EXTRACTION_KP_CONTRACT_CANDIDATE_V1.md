# Extraction ↔ KP minimal contract candidate v1

**Status: proposal for owner review; not an approved/public contract.** This document describes a candidate boundary grounded in producer output and current KP evidence models. The producer’s internal `Document` schema 1.4.0 is not renamed or declared to be ExtractionPackage v1.

## Boundary intent

```text
source document → doc-extraction internal Document → serialized candidate package → KP-owned consumer
```

The boundary carries physical observations and extraction/run provenance. KP alone assigns ontology classes, entity identity, relation meaning, business-domain meaning, review state and canonical KG changes.

## Candidate field groups

The candidate would expose only fields needed to identify the producer result, preserve the source and physical extraction, and allow KP to attach evidence:

| Group | Candidate content | Provenance |
|---|---|---|
| Contract envelope | Public contract name, contract version, producer schema/version metadata | Proposal only; version and compatibility are owner decisions |
| Source/run | Producer document ID, input filename, source SHA-256, file type, extraction status, warnings/errors, route/backend/model versions | Producer-native (`P`); timestamp/config/runtime are available but are not identities |
| Physical containers | Page-list index, rendered-page flag, nullable physical page/slide/sheet number, source route/backend, coordinate unit/origin, reading order | Producer-native (`P`); preserve null and format semantics |
| Elements | Producer element ID/type/text, nullable bbox/confidence/source ID/order index/table link, source backend | Producer-native (`P`); element ID is document-local |
| Tables/cells | Table ID/dimensions/page/bbox/backend/confidence; cells’ row/column/spans/text/header/bbox/confidence | Producer-native (`P`); no cell ID exists |
| KP evidence projection | Evidence text and source reference fields supported by KP models | KP model needs (`K`); not yet consumed by a package adapter |
| Cell evidence reference | Deterministic `(table_id,row,col)` reference if KP owner requires stable cell references | Derived (`D`); only after owner approves canonical encoding |

`assets`, rendered-image paths, model runtime internals, and stage intermediate ledgers are not included by default: they are not shown to be required by current KP consumers and can expose local paths or experimental internals. A future owner decision may add explicit fields for a demonstrated consumer need.

## Locator rules candidate

Do not collapse all source positions into a fabricated integer page. Keep the producer page-list `index` distinct from optional physical `page_number`. The candidate must retain `is_rendered_page` and the producer’s coordinate unit/origin when geometry is present. PDF page, PPTX slide, XLSX sheet, and DOCX logical body retain their documented distinctions. The public names/enum vocabulary and whether a typed `locator` object is needed are unresolved owner decisions.

## Table ownership and limits

The candidate preserves the producer’s table-to-element link and cell grid as emitted. It does not create semantic row/column labels, claim that nearby text belongs to a cell, or synthesize a stable `cell_id` without an approved derivation rule. The selected branch’s ownership work has regression coverage, but producer docs note backend-specific merge-span limits; this does not guarantee perfect ownership under all stamps, overlays, scans or table layouts.

## Failure and version policy

The producer currently distinguishes `success`, `success_with_warnings`, and `failed`; no distinct `partial` status is emitted. The candidate should carry this outcome and warnings/errors without mapping failure to an empty successful document. KP must preserve technical failure separately from semantic `UNRESOLVED`.

No compatibility behavior is approved. Major mismatch behavior, newer minor versions, missing optional fields, and unknown fields are listed in `docs/extraction-kp-contract/CONTRACT_OPEN_DECISIONS.md`. Until decided, an adapter must fail closed rather than guess or silently drop physical meaning.

## Deliberately absent

No `canonical_entity_id`, ontology class, `dependsOn`, `sameAs`, business domain, root cause, approved relation, identity resolution, review decision, or canonical KG field belongs in this producer contract. No schema file, validator, adapter, or fixture is claimed by this proposal.
