from aje.extraction.schema import (
    Achievement,
    Education,
    Experience,
    Language,
    ProfileData,
    Skill,
)
from aje.keys import (
    achievement_key,
    bullet_key,
    description_key,
    education_key,
    experience_key,
    language_key,
    profile_keys,
    skill_key,
)


def _profile() -> ProfileData:
    return ProfileData(
        skills=[Skill(name="Python")],
        experiences=[
            Experience(
                company="Acme",
                title="Backend Engineer",
                description="Owned the billing API",
                bullets=["Cut p99 latency", "Mentored two juniors"],
            )
        ],
        education=[Education(institution="UC3M", degree="Ingenieria Informatica")],
        achievements=[Achievement(text="Speaker at PyConES 2024")],
        languages=[Language(name="English", level="C1")],
    )


def test_experience_key_is_normalised():
    assert experience_key("Acme", "Backend Engineer") == "experience:acme|backend engineer"


def test_accents_and_casing_do_not_change_the_key():
    assert experience_key("Telefónica", "Ingeniero") == experience_key(
        "TELEFONICA", "  ingeniero  "
    )


def test_sub_keys_hang_off_the_experience_key():
    ek = experience_key("Acme", "Backend Engineer")
    assert description_key(ek) == "experience:acme|backend engineer#description"
    assert bullet_key(ek, 2) == "experience:acme|backend engineer#bullet:2"


def test_profile_keys_covers_every_anchorable_item():
    keys = profile_keys(_profile())
    ek = experience_key("Acme", "Backend Engineer")

    assert ek in keys
    assert description_key(ek) in keys
    assert bullet_key(ek, 0) in keys
    assert bullet_key(ek, 1) in keys
    assert bullet_key(ek, 2) not in keys  # only two bullets exist
    assert skill_key("Python") in keys
    assert education_key("UC3M", "Ingenieria Informatica") in keys
    assert language_key("English") in keys
    assert achievement_key("Speaker at PyConES 2024") in keys


def test_scoring_writes_keys_from_this_vocabulary():
    """The drift guard: scoring's embedding item_keys must be anchorable keys."""
    from aje.scoring.texts import profile_item_texts

    profile = _profile()
    scoring_keys = {key for key, _ in profile_item_texts(profile)}

    assert scoring_keys
    assert scoring_keys <= profile_keys(profile)
