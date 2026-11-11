import json
from pathlib import Path

from rdflib import Graph, SKOS, URIRef

from cdoi.v3_relation_evaluation import canonical_stw_thesoz_mappings
from cdoi.v3_stw_thesoz import STW_PREFIX, THESOZ_PREFIX


def test_reverse_broad_predicate_is_canonicalized_to_source_narrow(tmp_path: Path):
    source, target = URIRef(STW_PREFIX + "1"), URIRef(THESOZ_PREFIX + "1")
    graph = Graph(); graph.add((source, SKOS.narrowMatch, target)); graph.add((target, SKOS.broadMatch, source))
    path = tmp_path / "mapping.ttl"; graph.serialize(path, format="turtle")
    result = canonical_stw_thesoz_mappings(path, {str(source)}, {str(target)})
    assert result["relation_counts"] == {"narrowMatch": 1}
    assert result["evaluable_rows"][0]["relation"] == "narrowMatch"
    json.dumps(result)


def test_conflicting_source_target_relation_is_not_silently_resolved(tmp_path: Path):
    source, target = URIRef(STW_PREFIX + "1"), URIRef(THESOZ_PREFIX + "1")
    graph = Graph(); graph.add((source, SKOS.exactMatch, target)); graph.add((source, SKOS.relatedMatch, target))
    path = tmp_path / "mapping.ttl"; graph.serialize(path, format="turtle")
    result = canonical_stw_thesoz_mappings(path, {str(source)}, {str(target)})
    assert result["evaluable_rows"] == [] and len(result["conflicted_pairs"]) == 1
