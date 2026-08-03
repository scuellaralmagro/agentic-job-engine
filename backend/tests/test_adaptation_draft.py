from aje.adaptation import draft as draft_mod
from aje.adaptation.config import CvConfig
from aje.adaptation.schema import AdaptationResult, TailoredCv


class _RecordingLLM:
    def __init__(self, result):
        self._result = result
        self.calls = 0
        self.messages = None

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.calls += 1
        self.messages = messages
        return self._result.model_copy(deep=True)


def _result(language="en") -> AdaptationResult:
    return AdaptationResult(
        cv=TailoredCv(
            language=language, headline="Backend Engineer", summary="Builds APIs."
        )
    )


def _install(monkeypatch, result):
    llm = _RecordingLLM(result)
    monkeypatch.setattr(draft_mod, "llm_for", lambda task: llm)
    return llm


def test_one_call_is_made_and_the_result_returned(monkeypatch):
    llm = _install(monkeypatch, _result())

    out = draft_mod.draft_cv("CONTEXT", language=None, config=CvConfig())

    assert llm.calls == 1
    assert out.cv.headline == "Backend Engineer"


def test_the_context_is_sent_as_the_human_message(monkeypatch):
    llm = _install(monkeypatch, _result())

    draft_mod.draft_cv("CONTEXT-MARKER", language=None, config=CvConfig())

    role, content = llm.messages[1]
    assert role == "human"
    assert content == "CONTEXT-MARKER"


def test_the_bullet_cap_and_default_language_reach_the_prompt(monkeypatch):
    llm = _install(monkeypatch, _result())

    draft_mod.draft_cv(
        "CONTEXT",
        language=None,
        config=CvConfig(max_bullets_per_experience=3, default_language="es"),
    )

    system = llm.messages[0][1]
    assert "at most 3 bullets" in system
    assert "'es'" in system


def test_an_explicit_language_overrides_whatever_the_model_reports(monkeypatch):
    _install(monkeypatch, _result(language="en"))

    out = draft_mod.draft_cv("CONTEXT", language="es", config=CvConfig())

    assert out.cv.language == "es"


def test_without_an_override_the_models_detection_stands(monkeypatch):
    _install(monkeypatch, _result(language="en"))

    out = draft_mod.draft_cv("CONTEXT", language=None, config=CvConfig())

    assert out.cv.language == "en"
