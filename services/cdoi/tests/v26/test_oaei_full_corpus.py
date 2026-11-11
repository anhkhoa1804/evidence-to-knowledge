from cdoi.oaei_full_corpus import ConceptProfile, OAEIFullCorpusMatcher


def _profile(iri, label, parents=()):
    return ConceptProfile(iri, label, (), None, parents, (), (), ())


def test_full_corpus_retrieval_does_not_receive_gold_target(tmp_path, monkeypatch):
    source = {"s:heart": _profile("s:heart", "Heart"), "s:liver": _profile("s:liver", "Liver")}
    target = {"t:heart": _profile("t:heart", "Heart"), "t:liver": _profile("t:liver", "Liver"), "t:lung": _profile("t:lung", "Lung")}
    gold = {"s:heart": "t:heart", "s:liver": "t:liver"}
    matcher = OAEIFullCorpusMatcher(tmp_path)
    monkeypatch.setattr(matcher, "load", lambda: (source, target, gold))
    result = matcher.evaluate("R1_FUZZY_LEXICAL", top_k=2, emit_threshold=0.8)
    assert result["protocol"] == "OAEI_FULL_CORPUS_MATCHING"
    assert result["metrics"]["recall_at_1"] == 1.0
    assert result["metrics"]["precision"] == 1.0
    assert result["metrics"]["failure_taxonomy"]["RETRIEVAL_MISS"] == 0
    assert (tmp_path / "normalized_full_corpus_index.json").exists()
