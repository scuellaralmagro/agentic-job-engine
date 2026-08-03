import pytest

from aje.extraction.profile_service import save_profile
from aje.extraction.schema import Experience, ProfileData
from aje.models import Offer
from aje.scoring import embed as embed_mod
from aje.scoring.config import PrefilterSettings
from scripts.calibrate_threshold import collect_similarities, percentiles
from tests.fakes import FakeEmbeddings


@pytest.fixture
def fake_embeddings(monkeypatch):
    monkeypatch.setattr(embed_mod, "embeddings_for", lambda task: FakeEmbeddings())


def test_percentiles_of_a_known_series():
    values = [float(v) for v in range(1, 101)]

    result = percentiles(values)

    assert result["min"] == 1.0
    assert result["max"] == 100.0
    assert result["p50"] == pytest.approx(50.5, abs=1.0)


def test_percentiles_of_an_empty_series():
    assert percentiles([]) == {}


def test_collects_one_similarity_per_offer(session, fake_embeddings):
    save_profile(
        session,
        ProfileData(
            experiences=[
                Experience(
                    company="Acme",
                    title="Backend Engineer",
                    description="python fastapi",
                )
            ]
        ),
    )
    embed_mod.ensure_profile_embeddings(session)
    for index, (title, description) in enumerate(
        [("Backend Engineer", "python fastapi"), ("Nurse", "nurse sales")]
    ):
        session.add(
            Offer(
                title=title,
                description=description,
                source="test",
                content_hash=f"h{index}",
                skills=[],
            )
        )
    session.commit()

    rows = collect_similarities(session, PrefilterSettings(top_k=4))

    assert len(rows) == 2
    backend = next(r for r in rows if r[1] == "Backend Engineer")
    nurse = next(r for r in rows if r[1] == "Nurse")
    assert backend[2] > nurse[2]
