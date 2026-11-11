from __future__ import annotations

from .models import ChangeAction, ClassCandidate, ConceptProfile, OntologyChangeProposal, RiskLevel, SchemaCandidate


class PromotionEngine:
    def propose(self, candidates: list[SchemaCandidate] | list[ConceptProfile], bridges: list | None = None) -> list[OntologyChangeProposal]:
        # Promotion consumes persisted schema evidence; profiles remain accepted for V0 callers.
        role_profiles = [item for item in candidates if (isinstance(item, ConceptProfile) and "role" in item.semantic_features) or (isinstance(item, ClassCandidate) and "role" in item.canonical_label.casefold())]
        domains = {profile.domain for profile in role_profiles}
        if len(domains) < 3:
            return []
        source = sorted(role_profiles, key=lambda value: value.canonical_label)[0]
        bridge_count = len(bridges or [])
        return [OntologyChangeProposal(source_concept="Party Role", source_domain=source.domain, action=ChangeAction.PROMOTE_TO_SHARED, target_iri="https://example.org/vt/core/party-role/PartyRole", proposed_axioms=["https://example.org/vt/core/party-role/PartyRole a owl:Class"], confidence=0.76, risk_level=RiskLevel.HIGH, evidence=[f"Role-pattern evidence from {len(domains)} domains: {', '.join(sorted(domains))}.", f"Promotion considered {bridge_count} bridge mappings.", "Proposal proposes a reusable abstraction; it does not assert domain concepts equivalent or delete them."], provenance=source.provenance)]
