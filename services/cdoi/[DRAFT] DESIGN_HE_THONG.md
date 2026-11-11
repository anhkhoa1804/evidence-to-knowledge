## 1. Problem / Why

CDOI tập trung vào bài toán **continual cross-domain semantic integration dưới incomplete và ambiguous evidence**.

Các điểm khó chính:

* **Semantic ambiguity across domains**: cùng concept có thể được biểu diễn khác nhau giữa các domain, trong khi similarity cao chưa chắc đồng nghĩa với semantic equivalence.
* **Retrieval ≠ Selection ≠ Commitment**: tìm được candidate đúng chưa có nghĩa là chọn đúng, và chọn đúng cũng chưa đủ evidence để commit vào ontology/KG.
* **Continual evolution must be safe**: ontology/KG phải tiếp nhận knowledge mới liên tục nhưng vẫn bảo toàn provenance, version history và tránh các semantic commitment sai.
* **Incomplete evidence is unavoidable**: hệ thống cần coi `UNRESOLVED` / abstention là một outcome hợp lệ thay vì buộc phải đưa ra mapping.

CDOI đặt vấn đề trong bối cảnh rộng hơn của enterprise knowledge integration:

`Heterogeneous Sources → Semantic Evidence → Ontology/KG → Applications`

Trong đó **RCA là một downstream use case quan trọng**, không phải định nghĩa của toàn bộ bài toán CDOI. RCA được dùng để kiểm tra khả năng của ontology/KG trong việc kết hợp evidence từ nhiều nguồn, topology và thời gian để hỗ trợ reasoning về nguyên nhân.

---

## 2. Goal & Scope

### Goals

* Xây dựng một **general semantic integration layer** có thể tiếp nhận knowledge từ nhiều domain và tích hợp chúng vào modular ontology/KG.
* Tách rõ pipeline:
  `Candidate Retrieval → Semantic Selection → Commitment / Abstention`.
* Hỗ trợ **continual, provenance-preserving và conservative ontology evolution**.
* Chỉ đưa knowledge đã đủ evidence/approval vào canonical KG; các trường hợp chưa chắc chắn được giữ ở staging hoặc `UNRESOLVED`.
* Xây ontology/KG như một **reusable semantic foundation** cho nhiều downstream applications.

### RCA Positioning

RCA được xem là **một trong các use case cần giải quyết**, không phải điều kiện để CDOI bắt đầu phát triển.

CDOI phát triển từ bài toán tổng quát:

`Cross-domain knowledge integration → reliable ontology/KG → downstream reasoning`

sau đó dùng RCA để kiểm chứng các capability như:

* correlate heterogeneous evidence;
* resolve semantic/context differences;
* represent topology và temporal relationships;
* distinguish symptom from possible cause;
* trace reasoning về source evidence;
* abstain khi evidence không đủ.

Do đó, kiến trúc CDOI không phụ thuộc vào việc phải chờ một RCA dataset cụ thể từ bên ngoài; RCA data là **một nguồn evidence và validation scenario** của kiến trúc tổng quát.

### Current Non-goals

* Chưa cam kết production-grade automatic RCA.
* Không cho LLM/model trực tiếp mutate ontology hoặc canonical KG.
* Chưa claim generalization cho mọi ontology/domain.
* Chưa coi similarity/model output là đủ để automatic semantic commitment.

## 3. Input Data Requirements

> **Input requirements are evidence requirements, not schema requirements.**
> Khách hàng không cần tự thiết kế ontology hay chuẩn hóa dữ liệu theo internal schema của CDOI. Họ chỉ cần cung cấp đủ evidence để hệ thống có thể nhận diện entity, event, relation, semantic meaning và provenance.

### 3.1 Customer Inputs

| Input                                     | Priority                      | Minimum Content                                                                                  | Semantic Role                                                                                  |
| ----------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| **Authoritative Source Data**             | **Required**                  | Ít nhất một nguồn machine-readable chứa entities, events, attributes hoặc relations cần tích hợp | Nguồn evidence gốc cho extraction và semantic integration                                      |
| **Domain Object / Component Inventory**   | **Required**                  | `object_id`, `object_name`, `type_hint` nếu biết, `source_system`, các identifier dùng để join   | Chủ yếu cung cấp **real-world object / ABox evidence**, không phải danh sách ontology concepts |
| **Domain Glossary / Semantic Context**    | **Required**                  | Ý nghĩa, alias và mô tả của các domain terms chính                                               | Cung cấp semantic meaning để xử lý ambiguity và hỗ trợ schema/concept induction                |
| **Source Metadata**                       | **Required**                  | Source system, environment, timezone, collection window, identifier convention                   | Cung cấp provenance, identity và temporal context                                              |
| **Topology / Dependency Data**            | **Conditional / Recommended** | Quan hệ giữa các instances như `service A calls service B`, `pod runs on node`                   | Cung cấp **instance relation evidence**; đặc biệt quan trọng cho RCA                           |
| **Domain Rules / Semantic Relationships** | **Optional**                  | Các quan hệ nghiệp vụ không thể suy ra rõ từ raw data                                            | Bổ sung **semantic relation evidence** ở mức domain/schema                                     |
| **Historical Incidents / Ground Truth**   | **Conditional**               | Incident window, affected components, verified root cause/postmortem                             | Dùng cho evaluation của RCA và downstream reasoning                                            |

### 3.2 Inventory is Entity Evidence, not Concept Definition

Inventory trả lời:

> **“Trong domain hiện có những object thực tế nào?”**

Ví dụ:

| object_id | name            | type_hint | source          |
| --------- | --------------- | --------- | --------------- |
| `svc-01`  | payment-service | service   | service catalog |
| `db-07`   | payment-db      | database  | CMDB            |
| `pod-91`  | payment-7df8    | pod       | Kubernetes      |

Các object này trước hết được xem là **ABox evidence**.

Từ nhiều observations, CDOI mới có thể induction ra schema/concept candidates:

`payment-service-01, payment-service-02, ... → PaymentService / SoftwareService candidate`

Do đó:

`Instance Evidence → Schema Candidate Induction → Class / Property Candidates`

và không áp dụng:

`Instance → Ontology Concept` trực tiếp.

### 3.3 Glossary and Semantic Context

Glossary trả lời:

> **“Các term hoặc loại object này có nghĩa gì trong domain?”**

Ví dụ:

`Node`

* Kubernetes: worker machine
* Telecom: network/network-function concept
* Graph domain: graph vertex

Glossary không cần ánh xạ 1–1 với inventory. Nó mô tả **domain vocabulary**, bao gồm concepts, aliases, definitions và các semantic relationships quan trọng.

### 3.4 Topology Relations vs Semantic Relations

Hai loại relation cần được phân biệt rõ.

**Topology / Instance Relation**

Quan hệ giữa các object cụ thể, thường có thể thay đổi theo thời gian:

`payment-service-01 → uses → postgres-payment-01`

`pod-31 → runsOn → node-7`

`service-A → calls → service-B`

Chúng trả lời:

> **“Những instances nào đang liên kết hoặc phụ thuộc vào nhau?”**

**Semantic / Schema Relation**

Quan hệ ở mức concept/domain meaning:

`SoftwareService → usesDatabase → Database`

`Order → fulfilledBy → Shipment`

`Pod → runsOn → Node`

Chúng trả lời:

> **“Các loại concepts có semantic relationship gì với nhau?”**

Topology observations có thể trở thành evidence để induction ra semantic relations, nhưng hai loại relation này không được coi là cùng một layer.

### 3.5 Input-to-Knowledge Flow

```text
Customer Data
│
├── Inventory
│     ↓ identity / type normalization
│     ↓
│   Entity / ABox Evidence
│
├── Raw Logs / Records / Events
│     ↓ source adapter / parser
│     ↓ extraction
│     ↓
│   Entity + Event + Attribute Evidence
│
├── Topology / Dependencies
│     ↓ parsing + identity/time alignment
│     ↓
│   Instance Relation Evidence
│
├── Domain Glossary / Rules
│     ↓ semantic extraction
│     ↓
│   Definitions + Aliases + Semantic Relation Evidence
│
└── Source Metadata
      ↓ provenance / temporal normalization
      ↓
    Provenance + Identity / Time Context

                ↓
       Evidence Integration
                ↓
 Entity / Event / Relation Evidence
                ↓
 Schema / Concept Candidate Induction
                ↓
        Semantic Profiles
                ↓
       Ontology Integration
                ↓
      Proposal → Validation / Review
                ↓
 Approved Ontology + Canonical KG
```

### 3.6 Processing Principle

Structured sources nên ưu tiên **deterministic adapters/parsers**.

LLM có thể hỗ trợ extraction từ unstructured evidence như definitions, entities hoặc semantic relationships, nhưng output của model chỉ được xem là **evidence/proposal** và không được trực tiếp thay đổi canonical ontology/KG.

## 4. End-to-End Data Flow

CDOI xử lý dữ liệu theo hai responsibility chính:

* **KG Population**: đưa instance facts vào KG dựa trên ontology/mapping đã được approve.
* **Ontology Evolution**: xử lý semantic evidence mới, chưa biết hoặc ambiguous để đề xuất thay đổi ontology.

```text
External Sources
      ↓
Collectors / Adapters
      ↓
Raw Evidence Store
      ↓
Normalization
      ↓
Normalized Records
      ↓
Extraction
      ↓
Entity / Event / Relation / Semantic Evidence
      ↓
Identity, Temporal & Evidence Correlation
      ↓
Integrated Evidence
      │
      ├──────────────────────────────────────────────┐
      │                                              │
      │ Existing semantics known                     │ New / ambiguous semantics
      ↓                                              ↓
Instance Assertions                         Schema / Concept Candidates
      ↓                                              ↓
Validate against                            Semantic Profiles
approved ontology / mappings                        ↓
      ↓                                      Retrieval & Selection
Staging / Validation                                ↓
      ↓                                      Mapping / Change Proposal
Canonical KG                                        ↓
                                             Validation / Review
                                                    ↓
                                             New Ontology Version
                                                    │
                                                    └── updates approved
                                                        schema / mappings

Canonical KG + Temporal Evidence
              ↓
       RCA / Applications
```

### 4.1 Sources → Raw Evidence

**Input:** APIs, databases, logs, events, inventory, topology, business records, glossary and documentation.

**Processing:** source-specific collectors/adapters acquire data while preserving source metadata.

**Output:** raw evidence with provenance and collection context.

---

### 4.2 Raw Evidence → Normalized Records

**Input:** heterogeneous source payloads.

**Processing:** normalize identifiers, timestamps, field formats and source-specific representations without making semantic commitments.

**Output:** normalized records that remain traceable to the original source.

---

### 4.3 Normalized Records → Extracted Evidence

**Input:** normalized structured or unstructured records.

**Processing:** extract entities, events, attributes, relations, aliases and semantic descriptions.

**Output:**

```text
Entity Evidence
Event Evidence
Relation Evidence
Semantic Evidence
```

Extraction produces evidence, not approved ontology knowledge.

---

### 4.4 Identity, Temporal & Evidence Correlation

**Input:** extracted evidence from multiple sources.

**Processing:** correlate evidence using identifiers, source context and temporal validity.

Example:

```text
CMDB:      svc-001
Logs:      payment-service
Kubernetes deployment/payment-service
```

may be correlated as evidence related to the same operational object when sufficient identity evidence exists.

Temporal context is also preserved:

```text
event @ 10:05
topology A → B valid from 09:00–10:10
```

This stage correlates evidence; it does **not** automatically establish ontology equivalence.

---

### 4.5 Branch A — KG Population

If the extracted relation is already supported by approved semantics:

```text
SoftwareService ─usesDatabase→ Database
```

and the observed evidence is:

```text
payment-service-01 ─uses→ postgres-07
```

the system can create an instance assertion candidate.

Flow:

```text
Integrated Evidence
      ↓
Instance Assertion
      ↓
Validate against Approved Ontology / Mapping
      ↓
Staging / Validation
      ↓
Canonical KG
```

No ontology change is required for every new instance fact.

---

### 4.6 Branch B — Ontology Evolution

When evidence introduces a new or ambiguous semantic concept/relation:

```text
PaymentOrder ─settledThrough→ ClearingNetwork
```

the evidence enters the ontology-evolution path:

```text
Integrated Evidence
      ↓
Schema / Concept Candidate
      ↓
Semantic Profile
      ↓
Candidate Retrieval & Semantic Selection
      ↓
Mapping / Ontology Change Proposal
      ↓
Validation / Review
      ↓
Approved Ontology Version
```

Semantic selection may produce a proposal, abstain when evidence is insufficient, or record technical failure separately.

Approved changes update the semantic model used by future KG population.

---

### 4.7 Canonical KG → Applications

Canonical KG contains only assertions supported by approved ontology/mappings and validated evidence.

Downstream applications such as RCA consume:

```text
Canonical KG
+ current / historical topology
+ events
+ telemetry
+ change history
```

to support reasoning.

RCA consumes ontology/KG and evidence but does not directly modify the ontology.

---

### Core Lifecycle Principle

```text
Raw Evidence
!= Extracted Evidence
!= Instance Assertion
!= Schema Candidate
!= Approved Ontology Knowledge
!= Canonical KG Assertion
```

CDOI therefore keeps **evidence processing, ontology evolution and KG population as separate responsibilities**.

## 5. Data Model & Storage Design

CDOI tách dữ liệu theo **lifecycle, semantic state và access pattern**, thay vì lưu toàn bộ dữ liệu trong một graph duy nhất.

| Logical Store              | Stored Data                                                                             | Role                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Raw Evidence Store**     | Raw files, API responses, logs, source payloads                                         | Giữ evidence gốc để audit và reprocess                                         |
| **Normalized Store**       | Normalized records, identifier fields, timestamps                                       | Intermediate processing layer; có thể persist hoặc retention ngắn tùy workload |
| **Evidence Store**         | Entity, event, relation, attribute evidence; correlation/link evidence                  | Lưu extracted và correlated evidence cùng provenance                           |
| **Ontology Store**         | Ontology modules, mappings, ontology versions                                           | Quản lý approved semantic model                                                |
| **Proposal / Audit Store** | Ontology/mapping proposals, validation results, model outputs, review decisions         | Lưu các **decision objects** và ontology evolution history                     |
| **Staging KG**             | Candidate / unapproved **instance assertions**                                          | Cách ly assertions chưa đủ điều kiện commit                                    |
| **Canonical KG**           | Approved instance assertions + references to provenance, mappings and ontology versions | Knowledge chính thức cho applications                                          |

### 5.1 Core Separation

Hai loại candidate không được trộn với nhau:

```text
Ontology / Mapping Proposal
        → Proposal / Audit Store

Instance Assertion Candidate
        → Staging KG
```

Ví dụ:

```text
PaymentService subclassOf SoftwareService
```

→ ontology/schema proposal.

```text
payment-service-01 usesDatabase postgres-07
```

→ instance assertion candidate.

Do đó:

```text
Raw Evidence
≠ Extracted / Correlated Evidence
≠ Schema Proposal
≠ Instance Assertion Candidate
≠ Approved Ontology Knowledge
≠ Canonical KG Assertion
```

### 5.2 IDs, Provenance & Versioning

Các record quan trọng nên có tối thiểu:

```text
raw_record_id
normalized_record_id
evidence_id
proposal_id / assertion_id
source_id
processing_version
ontology_version
mapping_version
observed_at / valid_time
decision_status
```

Điều này cho phép phân biệt reprocessing:

```text
raw-123
→ extractor-v1 → evidence-456

raw-123
→ extractor-v2 → evidence-891
```

Audit chain mong muốn:

```text
Canonical Assertion
    ↓
Assertion Decision / Approval
    ↓
Semantic Mapping + Ontology Version
    ↓
Evidence IDs
    ↓
Normalized Record IDs
    ↓
Raw Source IDs
```

### 5.3 Storage Responsibility

* **Ontology Store** giữ schema và semantic model.
* **Proposal / Audit Store** giữ proposal, validation và review lifecycle.
* **Staging KG** chỉ giữ instance assertions chưa approved.
* **Canonical KG** chỉ chứa approved assertions có khả năng trace về evidence và semantic version.
* Evidence không được tự động trở thành canonical knowledge.

### 5.4 Physical Storage Pattern

Ở mức design hiện tại, có thể định hướng storage theo workload:

| Logical Layer          | Suitable Storage Pattern                                              |
| ---------------------- | --------------------------------------------------------------------- |
| Raw Evidence           | Object / document storage                                             |
| Normalized Records     | Relational hoặc structured document storage                           |
| Evidence               | Relational / document storage, hỗ trợ query theo entity, time, source |
| Ontology               | Versioned RDF/OWL artifacts                                           |
| Proposal / Audit       | Transactional relational / document store                             |
| Staging / Canonical KG | Graph / RDF store                                                     |

Đây là **storage pattern**, chưa phải vendor selection. Công nghệ cụ thể có thể được chọn sau dựa trên volume, query pattern, retention và deployment constraints.

## 6. Processing & Extraction Design

Processing layer có nhiệm vụ chuyển raw/normalized data thành **structured evidence**. Layer này **không thực hiện cross-source identity correlation, semantic alignment hay ontology commitment**. 

### 6.1 Processing by Source Type

| Source Type                                              | Processing                                             | Output                                      |
| -------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------- |
| **Structured** — API, CSV, DB, inventory                 | Deterministic adapter / parser                         | Entity, event, attribute, relation evidence |
| **Telemetry** — logs, metrics, traces                    | Source-specific parser + field/timestamp normalization | Event / observation / interaction evidence  |
| **Topology / Dependency**                                | Parse + identifier/timestamp normalization             | Instance relation evidence                  |
| **Semi / Unstructured** — documents, glossary, free text | Parser + optional LLM-assisted extraction              | Definition, alias, entity/relation evidence |

Nguyên tắc:

```text
Structured source
→ deterministic processing first

Unstructured source
→ parser + optional model-assisted extraction
```

### 6.2 Extraction Output Contract

Extractor sinh ra **evidence**, không phải ontology/schema candidate:

```text
EntityEvidence
EventEvidence
RelationEvidence
AttributeEvidence
DefinitionEvidence
AliasEvidence
```

Mỗi evidence nên giữ tối thiểu:

```text
evidence_id
source_record_id
source_span / source_location
content
timestamp / validity if available
extraction_method       # parser / rule / llm / manual
processing_version
provenance
extraction_status
```

`Candidate` được dành cho các stage semantic/schema phía sau.

### 6.3 LLM Boundary

LLM chỉ hỗ trợ **extract information expressed or supported by the source**, ví dụ entity, definition, alias hoặc relation evidence.

```text
Unstructured Source
        ↓
LLM / Model Extraction
        ↓
Structured Evidence Proposal
        ↓
Output Schema + Grounding Validation
        ↓
Evidence Store
```

Ví dụ LLM có thể extract:

```text
subject: payment-service
relation_text: stores data in
object: PostgreSQL
source_span: ...
```

nhưng việc map relation này thành ontology property như `usesDatabase` thuộc **Semantic Integration**, không thuộc Extraction.

Không cho phép:

```text
LLM → Approved Ontology
LLM → Canonical KG
```

### 6.4 Validation & Failure Handling

```text
Parse / Extract
      ↓
Output Schema Validation
      ↓
Provenance / Grounding Check
      ↓
Evidence Store
      ↓
Identity, Temporal & Evidence Correlation   # Step 4
```

Failure được giữ riêng:

```text
parse failure
→ quarantine / retry

invalid model output
→ validation failure

identity cannot be correlated
→ retain evidence with unresolved identity

missing / unreliable time
→ retain evidence with temporal uncertainty
```

### 6.5 Responsibility Boundary

```text
Extraction ≠ Identity Correlation
Extraction ≠ Semantic Alignment
LLM Extraction ≠ Ontology Decision
```

Nguyên tắc của layer này là: **preserve evidence first; semantic interpretation and commitment happen later.**

## 7. Semantic Integration & Ontology Evolution

Semantic Integration nhận correlated evidence / semantic profiles và xử lý theo flow:

`Semantic Evidence → Candidate Retrieval → Semantic Selection → Mapping / Change Proposal → Validation / Policy → Ontology Version Commit`

CDOI tách rõ **retrieval, selection và commitment**. Retrieval tìm candidate; selection xác định semantic interpretation phù hợp; còn commitment quyết định interpretation đó có đủ điều kiện để trở thành approved ontology knowledge hay không. Similarity hoặc model score không được xem trực tiếp là commitment confidence. 

Nếu selector không đủ evidence, nó trả `SEMANTIC_ABSTAIN` và case được giữ ở trạng thái `UNRESOLVED`. Model/infrastructure failure được ghi riêng là `TECHNICAL_UNAVAILABLE`, không được coi là semantic abstention.

Deterministic, dense hoặc LLM-based methods có thể hỗ trợ retrieval/selection tùy implementation, nhưng **không có quyền trực tiếp commit ontology changes**.

Ontology được evolve theo dạng incremental, versioned:

`O0 + Δ1 → O1 + Δ2 → O2`

---

## 8. Identity, Relation & Temporal Handling

| Concern       | Design Principle                                                                                                                          |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Identity**  | Correlate objects bằng stable IDs, source mappings và contextual evidence; semantic similarity không đủ để tự động tạo entity equivalence |
| **Relations** | Tách **instance/topology relation** khỏi **semantic/schema relation**; topology là instance evidence và có thể thay đổi theo thời gian    |
| **Temporal**  | Relations, topology và configuration phải gắn `observed_at / valid_time`; historical state không mặc định là current state                |

Ví dụ, `svc-01` trong CMDB, `payment-service` trong logs và Kubernetes deployment chỉ được xem là cùng operational object khi có đủ identity evidence; label similarity tự nó không đủ để tạo equivalence.

Tương tự:

`payment-service-01 calls fraud-service-01`

là **instance/topology evidence**, khác với:

`SoftwareService calls SoftwareService`

là **schema-level relation**.

Identity và temporal correlation phải được xử lý trước khi evidence từ nhiều nguồn được coi là cùng hỗ trợ cho một semantic decision. 

---

## 9. KG / Ontology Governance

CDOI quản lý riêng hai lifecycle.

**Ontology Evolution**

`Schema Candidate → Mapping / Change Proposal → Validation / Impact Analysis → Review when required → Ontology Version Commit`

**KG Population**

`Instance Evidence → Candidate Assertion → Validate against Approved Schema / Mapping → Staging → Commit Approved Assertion`

`Ontology Store` giữ approved schema/mappings theo version; `Proposal / Audit Store` giữ ontology/mapping proposals và decision history; `Staging KG` giữ candidate instance assertions; `Canonical KG` chỉ chứa approved assertions có thể trace về evidence, mapping và ontology version. 

Ontology changes và instance assertions chỉ được commit khi thỏa validation/policy tương ứng. **Human review chỉ bắt buộc đối với các case mà governance policy yêu cầu**, không phải mọi assertion.

Nguyên tắc chính:

**For semantic commitment, precision is prioritized over recall.** Khi evidence chưa đủ, hệ thống ưu tiên giữ `UNRESOLVED` thay vì thực hiện semantic commitment không an toàn.

## 10. RCA Consumption Design

RCA là **downstream consumer** của CDOI, sử dụng:

`Canonical KG + Operational / Temporal Evidence → RCA Reasoning`

Operational evidence có thể gồm current/historical topology, events, logs, metrics, traces và change history. Canonical KG cung cấp semantic context và approved relationships; operational evidence phản ánh trạng thái hệ thống tại thời điểm incident.

RCA có thể trả về:

`RCA_RESULT | RANKED_HYPOTHESES | INSUFFICIENT_EVIDENCE | TECHNICAL_FAILURE`

`INSUFFICIENT_EVIDENCE` thuộc RCA layer và không nên đồng nhất với semantic `UNRESOLVED`.

RCA hypotheses/results có thể được lưu như **application output hoặc audit artifact**, nhưng **không tự động trở thành canonical ontology/KG knowledge**.

---

## 11. Failure Handling & Observability

Failure được phân loại theo stage để tránh quy mọi lỗi về model hoặc ontology.

| Failure                                                         | Handling / Classification                    |
| --------------------------------------------------------------- | -------------------------------------------- |
| Source unavailable                                              | Retry / collection failure                   |
| Parse / extraction failure                                      | Quarantine record                            |
| Model output malformed / schema-invalid                         | `MODEL_OUTPUT_INVALID` / validation failure  |
| Backend / model infrastructure unavailable                      | `TECHNICAL_UNAVAILABLE`                      |
| Identity không correlate được                                   | Retain evidence with unresolved identity     |
| Time/topology không đủ tin cậy                                  | Retain evidence with temporal uncertainty    |
| Semantic evidence không đủ                                      | `SEMANTIC_ABSTAIN` → system giữ `UNRESOLVED` |
| Ontology proposal không đạt policy                              | Reject / pending                             |
| Instance assertion chưa đủ điều kiện                            | Giữ trong Staging KG                         |
| Evidence/KG hợp lệ nhưng RCA hypothesis sai                     | `REASONING_GAP`                              |
| Prediction hợp lý nhưng ground truth thiếu/sai/khác granularity | `EVALUATION_GAP`                             |

Observability chain nên trace được:

`Source → Processing Version → Evidence → Correlation → Semantic Decision → Proposal / Assertion → Validation / Commit → RCA Hypothesis / Result`

Mục tiêu là xác định failure thuộc **collection, extraction, identity, temporal, semantic, technical, reasoning hay evaluation layer**.

---

## 12. Validation & Current Implementation Status

### 12.1 Validation Focus

Validation được thực hiện theo từng layer; các nội dung dưới đây là **validation focus**, chưa phải quantitative pass threshold.

| Layer                       | Validation Focus                                                     |
| --------------------------- | -------------------------------------------------------------------- |
| **Collection / Processing** | Completeness, parsing, provenance                                    |
| **Extraction**              | Entity/event/relation correctness, grounding                         |
| **Identity / Temporal**     | Cross-source correlation, temporal validity                          |
| **Semantic Integration**    | Retrieval, selection, abstention, unsafe commitment                  |
| **Ontology / KG**           | Schema validity, staging/canonical safety, provenance                |
| **RCA**                     | Hypothesis quality, evidence support, insufficient-evidence handling |

Threshold và success metrics cụ thể nên được xác định trong evaluation plan riêng.

### 12.2 Current Implementation Status

| Capability                                           | Status                  |
| ---------------------------------------------------- | ----------------------- |
| Modular ontology/KG architecture                     | **IMPLEMENTED**         |
| Versioning, provenance, staging/canonical separation | **IMPLEMENTED**         |
| Retrieval / semantic-selection contracts             | **IMPLEMENTED**         |
| Generic raw enterprise ingestion                     | **NOT IMPLEMENTED**     |
| Real cross-source identity / temporal correlation    | **LIMITED / PROTOTYPE** |
| Dense real-model evaluation                          | **BLOCKED**             |
| Independent second-domain validation                 | **DATA MISSING**        |
| Commitment-confidence calibration                    | **NOT READY**           |
| Production RCA                                       | **NOT IMPLEMENTED**     |

Current evidence supports the **semantic integration architecture and safety boundaries**, nhưng chưa đủ để claim general enterprise validity hoặc production-grade RCA.
