from aje.discovery import expand
from aje.discovery.schema import ExpandedQuery


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


def test_expands_and_keeps_original_first(monkeypatch):
    fake = _FakeLLM(
        ExpandedQuery(terms=["Desarrollador Backend", "Ingeniero de Software"])
    )
    monkeypatch.setattr(expand, "llm_for", lambda task: fake)

    terms = expand.expand_query("Backend Engineer")

    assert terms[0] == "Backend Engineer"
    assert "Desarrollador Backend" in terms
    assert fake.structured.last_messages is not None


def test_does_not_duplicate_the_original_term(monkeypatch):
    fake = _FakeLLM(ExpandedQuery(terms=["Backend Engineer", "Desarrollador Backend"]))
    monkeypatch.setattr(expand, "llm_for", lambda task: fake)

    terms = expand.expand_query("Backend Engineer")

    assert terms.count("Backend Engineer") == 1
    assert terms[0] == "Backend Engineer"


def test_blank_terms_are_dropped(monkeypatch):
    fake = _FakeLLM(ExpandedQuery(terms=["  ", "", "Programador Python"]))
    monkeypatch.setattr(expand, "llm_for", lambda task: fake)

    assert expand.expand_query("python") == ["python", "Programador Python"]


def test_llm_failure_falls_back_to_original_term(monkeypatch):
    def _boom(task):
        raise RuntimeError("llm down")

    monkeypatch.setattr(expand, "llm_for", _boom)

    # a flaky model must never cost us the whole run
    assert expand.expand_query("python") == ["python"]


def test_empty_llm_response_falls_back_to_original_term(monkeypatch):
    monkeypatch.setattr(expand, "llm_for", lambda task: _FakeLLM(ExpandedQuery(terms=[])))
    assert expand.expand_query("python") == ["python"]
