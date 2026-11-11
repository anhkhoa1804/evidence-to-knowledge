# CDOI-Bench Annotation Guide

Annotate semantic truth separately from the safe workflow decision. Use `EQUIVALENT` only when identity criteria and intended extension match. Use `SUBCLASS_OF` when every source instance is a target instance. Use `RELATED_TO` or `BRIDGE` for a meaningful cross-domain connection that is neither identity nor reusable-core promotion. Use `NEW_CONCEPT` when current evidence supports a distinct schema addition. Use `UNRESOLVED` when available evidence cannot safely justify a stronger action.

`must_not_equivalent` is a hard safety label. Examples include finance `BankAccount` versus IT `UserAccount`, and finance versus logistics `Settlement`. A hidden possible relationship does not override an `UNRESOLVED` workflow decision when evidence is insufficient. Entity identity labels are annotated separately from ontology alignment and must not imply `owl:sameAs` without authoritative matching evidence.
