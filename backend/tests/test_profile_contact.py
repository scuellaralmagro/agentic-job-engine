from aje.extraction.profile_service import get_profile, save_profile
from aje.extraction.schema import Contact, Link, ProfileData, Skill


def test_profile_defaults_to_an_empty_contact():
    assert ProfileData().contact.full_name is None
    assert ProfileData().contact.links == []


def test_contact_survives_a_save_and_read_round_trip(session):
    data = ProfileData(
        contact=Contact(
            full_name="Ada Lovelace",
            headline="Backend Engineer",
            email="ada@example.com",
            phone="+34 600 000 000",
            location="Madrid, Spain",
            links=[Link(label="GitHub", url="https://github.com/ada")],
        ),
        skills=[Skill(name="Python")],
    )

    save_profile(session, data)
    loaded = get_profile(session)

    assert loaded.contact.full_name == "Ada Lovelace"
    assert loaded.contact.location == "Madrid, Spain"
    assert loaded.contact.links[0].url == "https://github.com/ada"
    assert [s.name for s in loaded.skills] == ["Python"]


def test_a_profile_saved_without_contact_reads_back_empty(session):
    save_profile(session, ProfileData(skills=[Skill(name="Python")]))

    assert get_profile(session).contact.email is None
