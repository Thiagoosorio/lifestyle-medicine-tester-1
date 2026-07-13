import ast
from pathlib import Path

import services.cpet_report_html as cpet_report_html
from services.cpet_report_html import generate_cpet_client_report


def test_high_risk_html_uses_service_headline_and_hides_training_prescriptions():
    html = generate_cpet_client_report(
        {
            "peak_vo2_ml_kg_min": 9,
            "peak_rer": 1.12,
            "vt1_hr_bpm": 90,
            "vt2_hr_bpm": 110,
            "peak_hr_bpm": 130,
        }
    )

    assert "Medical-pattern review comes before training progression." in html
    assert "Clinical review and clearance" in html
    assert html.index("Clinical review and clearance") < html.index("Your thresholds")
    assert "Your training zones at a glance" not in html
    assert "Your individualized zones" not in html
    assert "Your training plan" not in html


def test_html_generator_passes_client_context_to_service(monkeypatch):
    seen = {}

    def fake_summary(metrics, client_context="general", previous_metrics=None, modality=None):
        seen["client_context"] = client_context
        return {
            "fitness_classification": None,
            "training_zones": {"has_zones": False},
            "metabolic_profile": None,
            "limiter_profile": {},
            "result_headline": {
                "Level": "Routine",
                "Headline": "Context-aware headline",
                "Meaning": "Context-aware meaning.",
                "Next step": "Context-aware next step.",
            },
            "clinical_review_flags": [],
            "prescriptions_suppressed": False,
            "action_plan": [],
            "retest_targets": [],
        }

    monkeypatch.setattr(cpet_report_html, "build_cpet_coach_summary", fake_summary)

    html = cpet_report_html.generate_cpet_client_report({}, client_context="endurance")

    assert seen["client_context"] == "endurance"
    assert "Context-aware headline" in html


def test_every_cpet_html_download_call_supplies_client_context():
    page_path = Path(__file__).parents[1] / "pages" / "cpet_report.py"
    tree = ast.parse(page_path.read_text(encoding="utf-8"))

    report_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"generate_cpet_client_report", "_render_client_report_download"}
    ]

    assert report_calls
    for call in report_calls:
        assert any(keyword.arg == "client_context" for keyword in call.keywords)
