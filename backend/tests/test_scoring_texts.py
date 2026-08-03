from aje.extraction.schema import Achievement, Experience, ProfileData, Skill
from aje.models import Offer
from aje.scoring.texts import chunk_text, offer_item_texts, profile_item_texts, text_hash


def _profile():
    return ProfileData(
        skills=[Skill(name="Python"), Skill(name="Postgres")],
        experiences=[
            Experience(
                company="Acme",
                title="Backend Engineer",
                description="Payments platform",
                bullets=["Built the billing service"],
                skills=["Python", "FastAPI"],
            )
        ],
        achievements=[Achievement(text="Cut p99 latency by 40%")],
    )


def test_only_experiences_and_achievements_are_embedded():
    keys = [key for key, _ in profile_item_texts(_profile())]

    # the achievement key is sha256("Cut p99 latency by 40%")[:12]
    assert keys == ["experience:acme|backend engineer", "achievement:ea8230fc1c07"]
    # skills and languages are short and always sent verbatim to the rubric,
    # so vectorising them buys nothing and skews similarity
    assert not any(k.startswith("skill:") for k in keys)


def test_experience_text_includes_company_title_bullets_and_skills():
    _, text = profile_item_texts(_profile())[0]

    assert "Acme" in text
    assert "Backend Engineer" in text
    assert "Built the billing service" in text
    assert "FastAPI" in text


def test_experience_key_is_stable_across_accents_and_case():
    a = Experience(company="Telefónica", title="Backend Engineer")
    b = Experience(company="TELEFONICA ", title="backend  engineer")

    key_a = profile_item_texts(ProfileData(experiences=[a]))[0][0]
    key_b = profile_item_texts(ProfileData(experiences=[b]))[0][0]

    assert key_a == key_b


def test_offer_yields_a_title_vector_and_description_chunks():
    offer = Offer(
        title="Backend Engineer",
        company="Acme",
        location="Madrid",
        description="A" * 900 + "\n\n" + "B" * 300,
        source="test",
        content_hash="h",
    )

    items = offer_item_texts(offer, chunk_chars=800)

    assert items[0][0] == "title"
    assert "Backend Engineer" in items[0][1]
    assert "Madrid" in items[0][1]
    assert [k for k, _ in items[1:]] == ["chunk:0", "chunk:1"]


def test_offer_without_description_still_yields_a_title():
    offer = Offer(title="Backend Engineer", source="test", content_hash="h")
    assert [k for k, _ in offer_item_texts(offer, chunk_chars=800)] == ["title"]


def test_chunking_keeps_paragraphs_together_when_they_fit():
    text = "para one\n\npara two\n\npara three"
    assert chunk_text(text, chunk_chars=800) == ["para one\n\npara two\n\npara three"]


def test_chunking_splits_a_paragraph_longer_than_the_limit():
    chunks = chunk_text("X" * 250, chunk_chars=100)
    assert [len(c) for c in chunks] == [100, 100, 50]


def test_text_hash_is_stable_and_content_sensitive():
    assert text_hash("abc") == text_hash("abc")
    assert text_hash("abc") != text_hash("abd")
