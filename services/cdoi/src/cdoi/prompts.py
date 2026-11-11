"""Versioned minimal structured-output prompts used by optional semantic adapters."""

PROMPTS = {
    "conceptualization_v1": "Return JSON only. Define the schema candidate using its evidence and relation signature. Do not propose OWL axioms.",
    "alignment_v1": "Return JSON only. Select one closed-set semantic relation from the supplied candidate set and evidence. Do not mutate an ontology.",
    "bridge_discovery_v1": "Return JSON only. Propose a bridge only when a cross-domain relationship is evidenced; do not propose equivalence.",
    "promotion_analysis_v1": "Return JSON only. Propose a reusable abstraction without merging or deleting domain concepts.",
    "qwen_alignment_label_v1": "Return only a closed-set semantic decision from labels and supplied targets. Do not mutate an ontology.",
    "qwen_alignment_definition_v1": "Return only a closed-set semantic decision from labels and definitions. Do not mutate an ontology.",
    "qwen_alignment_context_v1": "Return only a closed-set semantic decision using supplied profile, context, and retrieved targets. Do not mutate an ontology.",
    "qwen_bridge_v1": "Return only a bridge proposal decision when evidence supports a cross-domain relation; never infer equivalence from lexical similarity.",
}
