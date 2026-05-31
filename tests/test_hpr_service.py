from services.hpr_service import (
    get_categories,
    get_protocol,
    get_protocol_rows,
    get_metrics_by_domain,
    infer_metric_score,
)


def test_hpr_categories_and_protocol_rows_load():
    assert get_categories() == ["sedentary", "trained", "competitive", "elite"]
    assert get_protocol("trained")["label"] == "Trained"
    assert len(get_protocol_rows("elite")) > len(get_protocol_rows("sedentary"))


def test_hpr_text_is_display_safe_ascii_for_protocol_copy():
    description = get_protocol("sedentary")["description"]
    assert "<=2 sessions/week" in description


def test_hpr_inferred_score_uses_visible_expected_anchor():
    metric = get_metrics_by_domain("strength")[0]
    norms = metric["norms"]["trained"]
    assert infer_metric_score(norms["expected"], norms) == 7.0


def test_hpr_inferred_score_handles_lower_is_better_metrics():
    metric = next(
        item for item in get_metrics_by_domain("movement")
        if item["direction"] == "lower_better"
    )
    norms = metric["norms"]["trained"]
    assert infer_metric_score(norms["elite"], norms) == 10.0
    assert infer_metric_score(norms["min"], norms) == 5.0
