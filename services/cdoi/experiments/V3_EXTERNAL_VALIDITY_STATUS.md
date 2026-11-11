# V3 External Validity Status

Anatomy is retained as a diagnostic/regression corpus, not independent training
and final-test data for a V3 confidence/router model. Any exploratory Anatomy
calibration must be labelled `EXPLORATORY_NON_INDEPENDENT`.

Second-domain status: `DATA_MISSING`. The repository has no bundled OET split
or RCAEval normalized case index, and no other suitable full source/target
ontology pair with mappings was identified. A future adapter must provide a
source ontology, full target corpus, reference mappings and relation types,
license/provenance, and reproducible semantic-profile extraction. V3 does not
fabricate such a corpus or hard-code Anatomy assumptions into its interfaces.
