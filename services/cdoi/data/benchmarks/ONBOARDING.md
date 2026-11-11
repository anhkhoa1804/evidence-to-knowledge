# Enterprise Onboarding Contract

Production integration needs more than raw records and a model endpoint. Provide available source schemas and API/database metadata, glossary/data dictionary, identifier and entity-matching rules, business rules, authoritative-source declarations, vocabulary assets, constraints, security/access policies, and semantic-governance policy.

Suggested package: `data/raw`, `schemas`, `glossary`, `identity`, `constraints`, `references`, and `governance.yaml`. Missing inputs are permissible, but the integration should retain uncertainty and increase review rather than infer authority. Benchmarks remain development artifacts and are never production dependencies.
