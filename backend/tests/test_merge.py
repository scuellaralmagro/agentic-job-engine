from aje.extraction import merge
from aje.extraction.schema import CandidateProfile, ProfileData, Skill


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


def test_merge_stamps_source_id_on_candidate(monkeypatch):
    merged = ProfileData(skills=[Skill(name="Python", source_refs=[1, 7])])
    fake = _FakeLLM(merged)
    monkeypatch.setattr(merge, "llm_for", lambda task: fake)

    existing = ProfileData(skills=[Skill(name="Python", source_refs=[1])])
    candidate = CandidateProfile(skills=[Skill(name="Python")])

    result = merge.merge_into_profile(existing, candidate, source_id=7)

    # candidate items were stamped before the LLM call
    assert candidate.skills[0].source_refs == [7]
    # the message payload carried the new source id
    assert "7" in str(fake.structured.last_messages)
    # returns the model's merged output
    assert result.skills[0].source_refs == [1, 7]


def test_stamping_is_idempotent(monkeypatch):
    fake = _FakeLLM(ProfileData())
    monkeypatch.setattr(merge, "llm_for", lambda task: fake)
    candidate = CandidateProfile(skills=[Skill(name="Go", source_refs=[5])])
    merge.merge_into_profile(ProfileData(), candidate, source_id=5)
    assert candidate.skills[0].source_refs == [5]
