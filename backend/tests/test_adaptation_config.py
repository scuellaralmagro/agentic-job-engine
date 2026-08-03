from aje.adaptation.config import CvConfig, load_cv_config
from aje.adaptation.schema import AdaptationResult, TailoredCv


def test_loads_template_and_page_settings(tmp_path):
    path = tmp_path / "cv.yaml"
    path.write_text(
        "template: cv_default\n"
        "default_language: es\n"
        "page: { format: A4, margin_mm: 15 }\n"
        "max_bullets_per_experience: 5\n",
        encoding="utf-8",
    )

    cfg = load_cv_config(path)

    assert cfg.template == "cv_default"
    assert cfg.default_language == "es"
    assert cfg.page.format == "A4"
    assert cfg.page.margin_mm == 15
    assert cfg.max_bullets_per_experience == 5


def test_an_empty_file_yields_working_defaults(tmp_path):
    path = tmp_path / "cv.yaml"
    path.write_text("", encoding="utf-8")

    cfg = load_cv_config(path)

    assert cfg.template == "cv_default"
    assert cfg.page.format == "A4"


def test_the_shipped_config_file_loads():
    from pathlib import Path

    cfg = load_cv_config(Path("config/cv.yaml"))

    assert cfg.template


def test_adaptation_result_round_trips_through_json():
    result = AdaptationResult.model_validate(
        {
            "cv": {
                "language": "en",
                "headline": "Backend Engineer",
                "summary": "Builds APIs.",
                "experiences": [
                    {
                        "source_key": "experience:acme|backend engineer",
                        "bullets": [
                            {
                                "source_key": "experience:acme|backend engineer#bullet:0",
                                "text": "Cut p99 latency 40%",
                            }
                        ],
                    }
                ],
                "skill_keys": ["skill:python"],
            },
            "suggestions": [
                {
                    "kind": "rewrite",
                    "source_key": "experience:acme|backend engineer#bullet:0",
                    "before": "Worked on the API",
                    "after": "Cut p99 latency 40%",
                    "reason": "The offer leads with performance work",
                }
            ],
        }
    )

    assert isinstance(result.cv, TailoredCv)
    assert result.cv.experiences[0].bullets[0].text == "Cut p99 latency 40%"
    assert result.cv.achievement_keys == []
    assert result.suggestions[0].kind == "rewrite"
