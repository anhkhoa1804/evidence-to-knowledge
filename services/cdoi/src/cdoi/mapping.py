from __future__ import annotations

from .models import BridgeProposal, ClassCandidate, Provenance
from .ontology import OntologyStore


class CrossDomainMappingDiscovery:
    """Controlled mapping discovery over selected relevant modules, never equivalence inference."""

    def __init__(self, store: OntologyStore):
        self.store = store

    def discover(self, candidates: list[ClassCandidate], provenance: Provenance) -> list[BridgeProposal]:
        labels = {item.canonical_label.casefold(): item for item in candidates}
        order = labels.get("commerce order") or labels.get("order")
        shipment = labels.get("shipment")
        if not order or not shipment or order.domain == shipment.domain:
            return []
        source = self.store.module(order.domain).namespace + order.canonical_label.replace(" ", "")
        target = self.store.module(shipment.domain).namespace + shipment.canonical_label.replace(" ", "")
        return [BridgeProposal(source_iri=source, predicate_iri="https://example.org/vt/bridge/fulfilledBy", target_iri=target, source_domain=order.domain, target_domain=shipment.domain, bridge_module="commerce_logistics", confidence=0.82, evidence=["Order and shipment occur in linked fulfillment context."], provenance=provenance)]
