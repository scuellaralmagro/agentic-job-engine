from aje.extraction import cv
from aje.extraction.schema import CandidateProfile, Skill


class _FakeStructured:
    def __init__(self, result):
        self._result = result
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return self._result


class _FakeLLM:
    def __init__(self, result):
        self.structured = _FakeStructured(result)

    def with_structured_output(self, schema):
        return self.structured


def test_extract_cv_returns_structured(monkeypatch):
    canned = CandidateProfile(skills=[Skill(name="Kubernetes")])
    fake = _FakeLLM(canned)
    monkeypatch.setattr(cv, "llm_for", lambda task: fake)

    result = cv.extract_cv("... CV text ...")

    assert result.skills[0].name == "Kubernetes"
    assert fake.structured.last_messages is not None
