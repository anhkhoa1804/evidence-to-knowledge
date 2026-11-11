# V3 Phase 2.10E — RCAEval Qualification

## Status

SUPPORTED for research reuse. RCAEval is maintained by phamquiluan/RCAEval;
the upstream repository and datasets state an MIT license. This qualification
used repository revision bb48c5aa9a24f1d5fcc716bdd479ea2d63145c90 and
Hugging Face dataset revision afeacb11bcc94dadfd1c8f483ee4377b2b8b614e.

Authoritative sources:

- https://github.com/phamquiluan/RCAEval
- https://huggingface.co/datasets/phamquiluan/RCAEval
- https://doi.org/10.5281/zenodo.14590730

The downloaded cases.parquet index SHA-256 is
c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb.
The complete cache inventory and hashes are in
archive/v3_phase2_10e_rcaeval/DATASET_HASHES.json.

## Index inspection

The frozen index contains 735 cases across the published suites. RE2-OB has
90 Online Boutique cases: six fault labels (cpu, mem, disk, delay, loss,
socket), three repetitions, five root-cause services, and declared metrics,
logs, and traces for every index row. Its index encoding supplies case ID,
suite/system, root-cause service, fault, injection timestamp, metric
dimensions/timesteps, and modality sizes.

root_cause_service and fault are evaluation labels. They are split from
operational case metadata before any adaptation. Static topology is
STATIC_TOPOLOGY_UNAVAILABLE; independently observable change events and
semantic glossary terms are unavailable. No topology, change, or glossary
was fabricated.

RE2-TT, RE3-OB, and RE3-TT remain reserved. RootCauseBench is recorded only
as a later complementary change/commit-granularity benchmark.
