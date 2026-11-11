from __future__ import annotations

import re
from collections import defaultdict
from typing import Protocol

from .models import ClassCandidate, DataPropertyCandidate, EntityCandidate, ObjectPropertyCandidate, Provenance, SchemaCandidate


class SchemaCandidateInducer(Protocol):
    def induce(self, entities: list[EntityCandidate], domain: str, provenance: Provenance) -> list[SchemaCandidate]: ...


class DeterministicSchemaInducer:
    """Promotes repeated/type-hinted ABox observations into traceable schema candidates."""

    _data_markers = {"ms", "count", "amount", "timestamp", "status", "code", "value"}

    def induce(self, entities: list[EntityCandidate], domain: str, provenance: Provenance) -> list[SchemaCandidate]:
        classes: list[SchemaCandidate] = []
        seen: set[tuple[str, str]] = set()
        for entity in entities:
            key = (entity.surface.casefold(), (entity.type_hint or "").casefold())
            if key not in seen:
                seen.add(key)
                abstractions = ["runtime environment"] if "pod" in entity.surface.casefold() else ["party role"] if "role" in entity.surface.casefold() else []
                classes.append(ClassCandidate(canonical_label=entity.surface, domain=domain, definition=entity.definition, type_hints=[entity.type_hint] if entity.type_hint else [], relation_signature=set(entity.relations), supporting_abox_ids=[entity.id], evidence=entity.evidence, provenance=provenance, abstraction_candidates=abstractions))
        properties: dict[tuple[str, str], SchemaCandidate] = {}
        for entity in entities:
            for relation in entity.relations:
                predicate, _, target = relation.partition("(")
                name = predicate.strip()
                if not name:
                    continue
                normalized_name = name.casefold()
                key = (normalized_name, "data" if any(marker in normalized_name for marker in self._data_markers) else "object")
                if key not in properties:
                    common = dict(canonical_label=name, domain=domain, definition=f"Observed relation {name}.", relation_signature={relation}, supporting_abox_ids=[entity.id], evidence=entity.evidence, provenance=provenance)
                    if key[1] == "data":
                        properties[key] = DataPropertyCandidate(**common, datatype_hint="string")
                    else:
                        properties[key] = ObjectPropertyCandidate(**common, domain_hints=[entity.surface], range_hints=[target.rstrip(")")])
                else:
                    candidate = properties[key]
                    candidate.supporting_abox_ids.append(entity.id)
                    candidate.relation_signature.add(relation)
        return classes + list(properties.values())
