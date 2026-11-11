from cdoi.oaei_diagnostics import abstention_cases, available_evidence_comparison, gold_rank_analysis, nontrivial_metrics, threshold_sweep


def _row(*, gold_rank=1, selected="t:gold", score=0.8, lexical=0.8, context_available=False, trivial=False):
    return {
        "source_iri": "s:one", "gold_target_iri": "t:gold", "gold_rank": gold_rank,
        "gold_in_top_k": gold_rank <= 20, "selected_candidate_iri": selected,
        "selected_candidate_score": score, "selected_candidate_rank": 1,
        "selected_lexical_score": lexical, "selected_context_score": 0.0,
        "selected_context_available": context_available, "top1_vs_gold_score_margin": 0.0,
        "available_features": ["lexical"] if not context_available else ["lexical", "context"],
        "available_feature_count": 1 + int(context_available), "trivial_lexical": trivial,
        "nontrivial": not trivial,
        "retrieved_candidates": [{"rank": 1, "iri": selected, "score": score, "lexical_score": lexical, "context_score": 0.0, "context_available": context_available}],
    }


def test_threshold_sweep_isolated_and_reports_coverage_metrics():
    rows = [_row(score=0.8), _row(selected="t:wrong", score=0.9)]
    result = threshold_sweep(rows, [0.75, 0.82], 0.82)
    low, frozen = result["runs"]
    assert result["diagnostic_only"] is True
    assert low["emitted_mappings"] == 2 and low["correct_emitted_mappings"] == 1
    assert frozen["is_frozen_threshold"] is True
    assert rows[0]["selected_candidate_score"] == 0.8


def test_abstentions_and_rank_buckets_are_mutually_classified():
    rows = [_row(gold_rank=1, score=0.8), _row(gold_rank=4, score=0.7), _row(gold_rank=21, score=0.1)]
    cases, summary = abstention_cases(rows, 0.82)
    assert len(cases) == 2
    assert {case["failure"] for case in cases} == {"THRESHOLD_ABSTENTION"}
    assert summary["gold_rank_buckets"] == {"rank_1": 1, "rank_2_5": 1, "rank_6_10": 0, "rank_11_20": 0}
    rank = gold_rank_analysis(rows, 0.82)
    assert rank["rank_1"]["n"] == 1 and rank["rank_gt_20"]["n"] == 1


def test_nontrivial_and_available_evidence_diagnostic_do_not_mutate_frozen_rows():
    rows = [_row(score=0.64, lexical=0.8, context_available=False, trivial=False)]
    nontrivial = nontrivial_metrics(rows, 0.75)
    evidence = available_evidence_comparison(rows, 0.75)
    assert nontrivial["n"] == 1 and nontrivial["emitted_recall"] == 0.0
    assert evidence["summary"]["decision_changed"] == 1
    assert evidence["cases"][0]["frozen_decision"] == "UNRESOLVED"
    assert evidence["cases"][0]["diagnostic_decision"] == "t:gold"
    assert rows[0]["selected_candidate_score"] == 0.64
