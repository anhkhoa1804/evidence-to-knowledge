# CDOI Current User Input Contract

This is an implementation-grounded contract for the checked-in prototype, not
a target architecture or production promise. Status values used here are:
`IMPLEMENTED`, `IMPLEMENTED_FOR_DIAGNOSTIC_ONLY`,
`PARTIALLY_IMPLEMENTED`, `CONFIGURATION_REQUIRED`, `DATA_REQUIRED`,
`RUNTIME_BLOCKED`, `NOT_IMPLEMENTED`, and `RESEARCH_HYPOTHESIS`.

## A. Executive answer

No. **Raw data plus a prose business/domain description is not sufficient for a
completely new domain in the current executable system.** `cdoi ingest DOMAIN
PATH` uses `StructuredExtractor.extract` (`src/cdoi/extraction.py`), which
reads only UTF-8 JSON concept records. `DOMAIN` must already be a module
hard-coded in `OntologyStore.load_defaults()`.

Raw data plus machine-usable domain knowledge is sufficient only when all of
the following are true:

- The domain is already provisioned as `distributed_systems`, `telecom`,
  `finance`, `fintech`, `logistics`, or `commerce`, with its matching TTL file
  under `ontologies/`.
- The source has been transformed into the explicit JSON `concepts` envelope;
  each concept has a non-empty `label`.
- The provided labels, definitions, type hints, and relation strings contain
  enough evidence for deterministic rules, or `NEW_CONCEPT`, `UNRESOLVED`, and
  staging are acceptable outcomes.
- The checked-in foundation/core/current-domain ontologies are the intended
  target vocabulary.
- Very-high-risk changes are approved through the Python API; the CLI has no
  review/approve command.

It is not sufficient for CSV, JSONL, RDF/OWL/Turtle/XML, database records, API
payloads, logs, generic documents, an unprovisioned domain, entity resolution,
or production RCA. No runtime adapter turns these into `EntityCandidate`
objects. CDOI can derive candidate classes from labels/type hints and candidate
properties from relation-name strings. It must not infer a domain module,
business role/identity meaning, keys, cardinality, trusted authority,
cross-domain equivalence, or `owl:sameAs` from this evidence.

## B. Current entrypoints and implementation map

| Entry boundary | Accepted input / consumer | Required fields, defaults, failure | Output / status |
| --- | --- | --- | --- |
| `cdoi preprocess PATH` | `preprocess()` supports UTF-8 JSON, Markdown, or other text | JSON must parse. JSON leaves become chunks; Markdown uses headings; other text uses paragraphs. No size limit. | `DocumentChunk` preview JSON. **IMPLEMENTED**, preview only. |
| `cdoi ingest DOMAIN PATH` | `ContinualIntegrationPipeline.ingest()` -> `StructuredExtractor.extract()` | Existing domain; JSON object with optional `concepts`; each actual concept needs `label`; `id`, `definition`, `type_hint`, `relations` optional. Unknown domain -> `KeyError`; missing label -> `KeyError`; non-object root -> attribute error. | Run journal, candidates/proposals, optional ontology version, in-memory canonical/staging KG. **IMPLEMENTED** only for this envelope. |
| `cdoi demo` | Fixed fixture JSON and fixed domains | Fixture/module assumptions | Versions, bridge/promotion proposals, Turtle. **IMPLEMENTED_FOR_DIAGNOSTIC_ONLY**. |
| `cdoi experiment MANIFEST` | YAML `ExperimentManifest`, benchmark/external adapters | Dataset-specific reference data | Persisted metrics/predictions. **IMPLEMENTED_FOR_DIAGNOSTIC_ONLY**. |
| `cdoi model probe` | `OpenAICompatibleConfig` environment metadata | Optional model configuration | Secret-free status. **CONFIGURATION_REQUIRED**, not customer data. |

```text
JSON concept envelope + existing domain argument
  -> preprocess(path) [chunks/audit context]
  -> StructuredExtractor.extract -> SemanticCandidateGraph (ABox candidates)
  -> DeterministicSchemaInducer -> typed schema candidates
  -> MockConceptualizer -> ConceptProfile
  -> HybridRetriever (foundation + core + current domain only)
  -> ConservativeAligner -> ProposalBuilder -> ProposalValidator
  -> RunStateStore -> ProposalApplier batch version
  -> approved class type assertions in canonical KG; otherwise staging KG
```

Bridge discovery and promotion are separate after ingest. They are not generic:
bridge discovery recognizes only an `order`/`commerce order` plus `shipment`
combination, and promotion recognizes `role` labels in at least three domains.

## C. Formal onboarding contract

| Input category | Exact information | Required / condition | Format and consumer | Can infer? / absent behavior | Risk / status |
| --- | --- | --- | --- | --- | --- |
| Domain identity | One fixed name: `distributed_systems`, `telecom`, `finance`, `fintech`, `logistics`, `commerce` | Required for every ingest | CLI arg -> `OntologyStore.module`, retrieval, validation | No. Unknown name raises `KeyError`. | Wrong bounded context/namespace. **IMPLEMENTED**, fixed allow-list. |
| Domain module/namespace | Existing hard-coded TTL module | Required deployment state | `OntologyStore.load_defaults()` | No provisioner; missing files fail load. | Cannot isolate a new domain. **CONFIGURATION_REQUIRED**. |
| Source records | JSON object with `concepts: []` | Required for meaningful ingest | UTF-8 JSON -> `StructuredExtractor` | No. Empty/missing list yields empty run. | No semantic model. **IMPLEMENTED**. |
| Label | `item["label"]` | Required per record | JSON scalar -> all stages | No. Missing key errors; blank value is weakly accepted. | Ambiguous/invalid terms. **IMPLEMENTED**. |
| Stable ID | `item["id"]` | Optional; needed for stable instance identity | JSON scalar -> entity/KG IRI | Positional `<domain>-<index>` default only. | Reordering changes identity. **PARTIALLY_IMPLEMENTED**. |
| Definition | `item.get("definition", "")` | Optional enrichment; needed for ambiguous semantics | JSON string -> profile/retrieval | No. Empty lowers evidence. | Wrong placement. **IMPLEMENTED**. |
| Type hint | `item.get("type_hint")` | Optional enrichment | JSON string -> schema candidate key | No. Missing values collapse same-label observations. | Lost distinction. **IMPLEMENTED**. |
| Relations | `item.get("relations", [])`, convention `predicate(Target)` | Conditional: properties/signature desired | JSON strings -> extractor/inducer/retrieval | Predicate names only. No relation means no property candidate. | Object/data choice is heuristic. **PARTIALLY_IMPLEMENTED**. |
| Provenance | path/span/source system/domain/run/time/extractor | Mostly generated; real source ownership needed for audit | `SourceReference`, `Provenance` | Path/span/run/time yes. Root `source_system` is ignored; default is `fixture`. | False audit source. **PARTIALLY_IMPLEMENTED**. |
| Existing ontology | Fixed foundation/core/domain TTL modules | Required target state, not user payload | `OntologyStore` | No. No target ontology -> load failure. | No semantic context. **CONFIGURATION_REQUIRED**. |
| Customer RDF/OWL/RDFS/SKOS | None at runtime | Only benchmark evaluation has a condition | OAEI adapter reads RDF/OWL | No. `ingest` ignores it. | Benchmark capability mistaken for onboarding. **NOT_IMPLEMENTED**. |
| Approval | Generated proposal IDs as Python `approved_ids` set | Conditional: very-high-risk proposal | `pipeline.ingest(..., approved_ids=...)` | No. CLI has no approval interface; stays pending/staged. | Unsafe commitment. **PARTIALLY_IMPLEMENTED**. |
| Gold/reference mappings | CDOI-Bench/gold JSON, OAEI reference RDF | Never normal runtime input | experiments/external adapters | No. Runtime unaffected. | Data leakage. **IMPLEMENTED_FOR_DIAGNOSTIC_ONLY**. |
| Entity keys | `EntityCandidate.id` only | Conditional: entity resolution requested | resolver, not called by ingest | Exact equal non-empty IDs -> candidate; otherwise unresolved. | False merge. **PARTIALLY_IMPLEMENTED**. |
| Customer constraints | No customer input model | Conditional in desired architecture | Validator owns one in-code label SHACL shape | No. Only baseline checks run. | Business constraint violation. **PARTIALLY_IMPLEMENTED**. |
| Application data | None in runtime | Conditional: real application requested | Synthetic evaluator/external scoring only | No. | Unsupported application claim. **IMPLEMENTED_FOR_DIAGNOSTIC_ONLY**. |

### Exact runtime JSON envelope

```json
{
  "concepts": [
    {
      "id": "order-1007",
      "label": "Commerce Order",
      "type_hint": "business order",
      "definition": "A customer purchase request awaiting fulfillment.",
      "relations": ["fulfilledBy(Shipment)", "hasOrderAmount(Amount)"]
    }
  ]
}
```

The root-level `source_system` in fixtures is not consumed. The extractor does
not retain raw record values, read field names/foreign keys, or parse relation
arguments beyond splitting at the first `(`. It creates one ABox
`EntityCandidate` per supplied concept record.

## D. Domain context, business semantics, and profiles

The domain argument supplies namespace, target module, provenance domain,
validation module, and retrieval scope. Retrieval searches foundation, every
loaded core module, and the current domain; it does not search other domains as
normal targets. Equal labels from another domain become `UNRESOLVED`, so
`finance:Settlement` does not become `logistics:Settlement` by lexical match.
`config/domains.yaml` is not read by ingest: editing it does not onboard a
domain.

| Business material | Current treatment |
| --- | --- |
| Names | Required `label`, directly consumed. |
| Definitions | Directly consumed from `definition`; token evidence only. |
| Category | Opaque `type_hint`; distinguishes candidate keys but has no general interpretation. |
| Relation semantics | Strings only; relation name becomes a property candidate. Four hard-coded label cues (`pod`, `role`, `organization`, `wallet`) add limited abstractions. |
| Glossary, aliases, synonyms | No runtime fields/parser. A preprocessing transformation may fold text into labels/definitions, but that transformation is outside CDOI. |
| Business rules, process rules, authority, cardinality/domain/range | No intake model and not inferred. |
| LLM semantic extraction | Default is `MockConceptualizer`; `OptionalLLMExtractor` raises `NotImplementedError`; LLM adapters are experimental and not wired into the ingest components. |

Structured enterprise schema is therefore not a supported source format.
Table/API/event names, field names/types, PK/FK, nullability, cardinality and
values are neither extracted nor validated. A preprocessor may express a known
relationship as `predicate(Target)`, but CDOI does not prove the relationship.

The implemented `ConceptProfile` has exactly:

```text
candidate_id, canonical_label, local_definition, abstraction_candidates,
semantic_features, relation_signature, domain, source_candidates, provenance,
kind
```

It has no source IRI, normalized label, aliases, parents, children, property
list, neighbourhood, or independent source-system field. Features are
lowercase alphanumeric label/definition tokens plus relation strings.
Definitions/relations may be missing, reducing retrieval evidence without
causing an error. `HybridRetriever` exposes target lexical, embedding,
structural, relation-signature, neighbourhood, domain and final scores. The
default embedding provider is null (`0.0`); hashing is an ablation baseline;
real embedding providers are experiment-only.

## E. Validation, review, persistence, and KG

`ProposalValidator` checks foundation immutability, new-domain namespace,
taxonomy cycles, duplicate-label warning, and one in-code pySHACL label shape.
It does not import user SHACL, business rules, domain/range, cardinalities, or
forbidden relationships. `ImpactAnalyzer` reports graph counts and currently
always returns zero for `constraints` and `instance_typings`.

| Missing condition | Exact behavior |
| --- | --- |
| Malformed JSON | JSON decoder exception. |
| Non-object JSON | Attribute error at `.get`. |
| No `concepts` | Empty candidate run; no version. |
| Missing label | `KeyError`; record is not skipped. |
| Missing definition/relation/type hint | Empty/default; degraded evidence; continues. |
| Missing ID | Positional default ID. |
| Missing aliases/glossary/keys/constraints | Not represented; no specific warning or inference. |
| Missing provenance | Runtime makes path/span/domain/model/time/run; source system defaults to `fixture`. |
| No retrieval candidate | `NEW_CONCEPT` at 0.8 -> add-class/property proposal. |
| Same label in another domain | `UNRESOLVED`, not equivalence. |
| Invalid proposal | Rejected; class-supported facts go to staging. |
| Very-high risk | `review_pending` unless generated ID is approved through Python; CLI cannot approve. |
| Missing Qwen credential/model | Experiment records skipped/unavailable; default ingest does not call Qwen. |
| Missing embedding runtime | Default ingest never needs it; experiment provider raises a controlled runtime error. |

State files are `data/integration_runs/run-*/run.json`,
`candidate_graph.json`, `schema_candidates.json`, and proposal-state JSON.
They retain path/span, input domain, extractor version, timestamp/run ID and
proposal/version state; they do not guarantee original records, actual source
system, record timestamp, ontology source version, or reviewer rationale.
Version snapshots/deltas are under `data/ontology_versions/vNNN`.

Only class-supported type triples are populated. Approved triples go to the
in-memory canonical graph with `approvedInVersion`; all non-approved class
facts go to staging. Relations, property values, events, and evidence are not
populated. `export_kg()` writes canonical and staging Turtle. An approved
version is not a rich enterprise KG.

## F. Entity identity, mappings, evaluation, and infrastructure

TBox alignment can proceed without ABox identity. The resolver is not called by
`ingest`. If called, identical non-empty source IDs produce only
`SAME_ENTITY_CANDIDATE`; every other case is `UNRESOLVED`; it never asserts
`owl:sameAs`. Real entity resolution needs authoritative cross-system identity
keys/mappings through a missing adapter. Labels, semantic similarity and
ontology mappings are insufficient.

There is no user-facing mapping import. Runtime proposals are candidates;
`approved_ids` is an in-process approval control. Bridges require separate
`commit_bridge(..., approved=True)` and are neither equivalence nor identity.
`data/benchmark/gold.json`, CDOI-Bench and OAEI `reference.rdf` are evaluation
references only. They must not enter normal ingestion or runtime prompting.

Default ingest/demo is credential-free, offline and does not require a GPU,
model or embedding. Optional experiment/model configuration uses
`CDOI_LLM_PROVIDER`, `CDOI_LLM_MODEL`, `CDOI_LLM_BASE_URL`,
`CDOI_LLM_API_KEY_ENV` (default `DMP_MERCURY`), `CDOI_LLM_HOST_HEADER`,
`CDOI_LLM_TEMPERATURE`, and `CDOI_LLM_MAX_TOKENS`. These are deployment
configuration, never customer semantic input. Public metadata is secret-free;
credentials must not be stored in input, journals, manifests or reports.

## G. Evidence sufficiency and readiness lifecycle

| Level | Inputs | Operations | Unsafe/unavailable |
| --- | --- | --- | --- |
| 0 — insufficient | Raw/prose, unsupported source, or unknown domain | Preprocess preview only | Ingestion/alignment/domain creation |
| 1 — ingestible | Existing domain + valid JSON labels | ABox/schema candidates and run artifacts | Meaningful semantics not guaranteed |
| 2 — alignable | Level 1 + definitions/type hints/relation strings + target ontologies | Retrieval, conservative decisions, proposals | Cross-domain equivalence/business constraints |
| 3 — safely integratable | Level 2 + valid proposals and required approval | Versioned changes and approved class type triples | Entity merge, relation/value KG population |
| 4 — application-ready | Not a general runtime state | Synthetic downstream fixture can be evaluated | Production RCA/search/impact/query application |

```text
ingested = candidate graph/schema candidates persisted
semantically aligned = decision/proposal exists (may be NEW or UNRESOLVED)
approved = validation/review gate passed and version committed
KG-ready = approved class type Turtle exported
application-ready = NOT ESTABLISHED by the ingest pipeline
```

## H. Four domain scenarios

### A. Customer / Order / Shipment / Payment database

For an already provisioned `commerce`/`logistics` context, preprocessing must
convert database/schema facts to records such as `Commerce Order`, `Customer
Role`, `Shipment`, with `fulfilledBy(Shipment)`. CDOI derives candidate classes
and relation-name properties. It cannot read database rows, CSV headers, table
PK/FKs, nullability, amount values, or prove relationship semantics. It cannot
know whether `Customer` means Person, Party, PartyRole, AccountHolder or
Subscriber; the owner must encode a precise label/definition and still review
the proposal. Output is versioned schema/type assertions, not an order/payment
fact graph.

### B. Observability / RCA

Raw services, pods, hosts, events, metrics, traces and logs are not ingested.
For existing `distributed_systems`, a preprocessor may provide `Kubernetes Pod`
with definition and `runsOn(Node)`; the hard-coded `pod` rule can propose the
specific `Runtime Environment` placement. Event/metric/trace values become no
facts by default. Dependency direction, incident causality, trace semantics,
ownership and metric meaning must be supplied/approved. A real RCA application
also requires events/dependencies/observations and an algorithm outside CDOI;
`ControlledDownstreamEvaluator` is synthetic only.

### C. RDF/ontology-rich domain

Customer OWL/RDF/RDFS/SKOS/Turtle cannot be passed to `ingest`. Fixed checked-in
TTL is its only ordinary target input. OAEI RDF/OWL parsing is benchmark-only.
The owner must use an out-of-contract conversion to JSON and separate code/
deployment work to add a hard-coded module. No public command imports their
ontology or creates its domain module.

### D. Text/document-heavy domain

`cdoi preprocess document.md` creates chunks, but `StructuredExtractor` reads
non-JSON as `{}` and extracts no entities. `OptionalLLMExtractor` is disabled
and raises `NotImplementedError`. Generic documents, automated glossary
extraction and ontology learning are absent; the safe result is no integration,
not invented semantics.

## I. Team contracts and onboarding checklist

### Current-input matrix (preprocessing implementation checklist)

| Input | Who provides it? | Mandatory? | Can preprocessing derive it? | Can LLM propose it? | Can system safely infer it? | Used by which stage? | What happens if missing? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Loaded domain ID | Deployment owner/caller | Yes | No | No runtime LLM path | No | Module lookup, namespace, retrieval, validation | `KeyError` for unknown domain |
| Domain TTL module | Deployment/repository maintainer | Yes | No supported provisioner | No | No | Ontology loading/retrieval/commit | Pipeline cannot load |
| `concepts` JSON envelope | Source owner/preprocessor | Yes for useful ingest | Yes, from unsupported raw sources outside CDOI | Not in current pipeline | No | Extractor | Empty run if absent |
| Label | Source owner/preprocessor | Yes per record | Only by an external mapping | No runtime LLM path | No | Extraction through proposal | `KeyError` if absent |
| Stable ID | Source owner/preprocessor | Conditional: continuity/identity | Yes only if source has one | No runtime LLM path | Only unstable index default | ABox support/KG IRI/resolver | Positional default |
| Definition/type hint | Domain expert/preprocessor | Conditional: ambiguous/precise alignment | Can copy supplied metadata; cannot reliably invent semantics | Experiment-only LLM may propose, not commit | No | Profile/retrieval/schema induction | Degraded evidence/candidate collapse |
| Relation string | Domain expert/preprocessor | Conditional: properties/signature | Can transform an authoritative source relation | No runtime LLM path | Relation name only | Extractor/schema/profile | No property candidate/context |
| Source provenance | Preprocessor/runtime | Generated minimum; real ownership conditional | Path/span yes | No | Path/span/run only | Evidence/state audit | Defaults can misstate source system |
| Existing mapping/approval | Reviewer/application owner | Conditional: high-risk commit | No | No | No | Review gate/bridge commit | Pending/staging |
| Entity identity evidence | Authoritative source owner | Conditional: entity resolution | May carry strong source IDs | No | Exact equal source ID only -> candidate | Separate resolver | `UNRESOLVED`; no `owl:sameAs` |
| Customer constraints | Domain governance owner | Conditional: required business validation | No supported format | No | No | Not consumed | Only baseline validator runs |
| Gold/reference labels | Evaluation team | No at runtime | No | No | No | Experiments only | No effect on ingest |
| LLM/embedding config | Platform operator | No for default ingest | No | N/A | No | Optional experiments/model probe | Skipped/unavailable experiment |

### Domain-independent mandatory inputs

Every successful current runtime ingestion requires exactly: an existing loaded
domain identifier, its already deployed ontology module/namespace, a readable
UTF-8 JSON object, and at least one `concepts` record with a `label` if a
non-empty result is expected. The run-time-generated provenance fields and
default component stack are also necessary system state, but are not supplied
by a customer. An existing customer ontology, gold mappings, glossary, aliases,
identity rules, or application dataset is not an API requirement; each is
either unsupported or conditional as stated above.

**Does the user need to provide an ontology?** No, not when they use one of the
already provisioned domains: the repository supplies the foundation/core/domain
TTL target state. But a completely new domain cannot be used until an ontology
module and namespace have been provisioned in code/repository state. The user
cannot provide an OWL/RDF file to satisfy that requirement through the current
CLI.

**Preprocessing:** create UTF-8 JSON; enforce non-empty labels; preserve stable
IDs where meaningful; supply truthful definitions/type hints/relation strings;
and flag information not representable without loss. Do not use gold mappings,
force equivalence, invent FK/cardinality semantics, make approval decisions, or
write ontology commits. The current CLI cannot carry a genuine source-system
identifier (it defaults to `fixture`).

**Evaluation:** consume CDOI-Bench/OAEI/OET/RCAEval and gold references only in
experiments. Qwen diagnostic prompts exclude references until response capture.
Evaluation does not mutate the core and is not runtime intake.

**Applications:** may consume exported canonical Turtle as approved,
class-type-only data and retain version annotation. Staging is audit/workflow
data, not approved truth. There is no application API or enforced access
control preventing misuse of staging/proposal/Qwen JSON; treating those as
non-canonical is an operating invariant.

Checklist for a domain owner:

1. Is the bounded context one of the six loaded domains? If no, stop: module
   provisioning must be implemented first.
2. Can you provide a JSON `concepts` object with a non-empty label for each
   concept, and a stable ID where continuity matters?
3. What exact definition, type/category and `predicate(Target)` relationships
   can you assert for each concept?
4. Which labels are ambiguous (Customer, Settlement, Account), and what
   definition distinguishes the intended extension?
5. What source path/span must remain auditable? Record actual source-system
   ownership separately because normal ingest does not carry it.
6. Do you require PK/FK/cardinality/business-rule validation? It is not
   supported by this runtime.
7. Do you require entity resolution? Supply authoritative identity evidence to
   a separate implementation; do not expect `owl:sameAs`.
8. Who approves very-high-risk ontology/bridge changes through the Python
   API?
9. Is the expected output only approved type assertions, or a real RCA/search/
   impact application? The latter is outside this runtime.
10. Keep gold mappings with evaluation and credentials with infrastructure.

## J. CURRENTLY NOT SUPPORTED OR NOT PROVEN

- **NOT_IMPLEMENTED:** new-domain/module/namespace onboarding. `config/domains.yaml` is inactive at runtime.
- **NOT_IMPLEMENTED:** runtime CSV, JSONL, RDF/OWL/RDFS/SKOS/Turtle, XML, database, API, log, event-stream, or arbitrary-document adapters.
- **PARTIALLY_IMPLEMENTED:** Markdown/plain-text preprocessing exists but is not followed by runtime extraction.
- **NOT_IMPLEMENTED:** general ontology learning; glossary/alias/synonym/business-rule extraction; schema/FK/cardinality/type inference; customer SHACL intake.
- **NOT_IMPLEMENTED:** runtime import of a customer ontology or trusted mapping file; OAEI RDF/OWL is diagnostic only.
- **PARTIALLY_IMPLEMENTED:** deterministic local alignment/proposal generation. Qwen and real embeddings are experiment paths, not default ingestion. Missing Qwen credentials and the recorded Windows embedding runtime issue make production model routing **RUNTIME_BLOCKED / NOT PROVEN** here.
- **NOT_IMPLEMENTED:** enterprise entity resolution and generic cross-domain relationship discovery. The one implemented cross-domain rule is Order-to-Shipment fulfillment.
- **IMPLEMENTED_FOR_DIAGNOSTIC_ONLY:** CDOI-Bench, OAEI, controlled downstream RCA/impact, and semantic-confidence/Qwen diagnostics.
- **RESEARCH_HYPOTHESIS:** that current lexical/definition/relation-token evidence generalizes to enterprise semantics; existing external artifacts explicitly report an external-validity gap.

## K. Documentation normalization (not a new architecture)

| Layer | Current structure | Limitation |
| --- | --- | --- |
| A. Source Evidence | JSON `concepts`, `Evidence`, `SourceReference`, `SemanticCandidateGraph` | Only explicit concept records extract at runtime. |
| B. Domain Context | CLI domain, `Provenance.input_domain`, `OntologyModule` | Cannot provision a new domain. |
| C. Semantic Context | label/definition/type hint/relation, `ConceptProfile`, target TTL labels/comments | No alias/glossary/ontology-import contract. |
| D. Constraints/Governance | validator, proposal state, review gate, version records | No customer policy/constraint intake or review UI. |
| E. Application Intent | No ingest field; synthetic downstream fixture | No application runtime contract. |
| F. Evaluation Reference | CDOI-Bench/gold/OAEI/OET/RCAEval | Must remain separate from runtime. |
| G. Infrastructure | `OpenAICompatibleConfig`, optional embeddings | Deployment, not domain data. |

Evidence traced in `src/cdoi/cli.py`, `pipeline.py`, `preprocessing.py`,
`extraction.py`, `schema.py`, `models.py`, `conceptualization.py`,
`retrieval.py`, `alignment.py`, `proposals.py`, `validation.py`, `merge.py`,
`state.py`, `versioning.py`, `kg.py`, `entity_resolution.py`, `mapping.py`,
`promotion.py`, `ontology.py`, `external.py`, `experiment_runner.py`, and
`downstream.py`, plus their tests. Documentation claims are marked implemented
only where the executed call path confirms them.
