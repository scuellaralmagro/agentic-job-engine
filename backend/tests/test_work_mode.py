import pytest

from aje.discovery.work_mode import HYBRID, ONSITE, REMOTE, detect_work_mode


@pytest.mark.parametrize(
    "description, expected",
    [
        ("Trabajo 100% remoto desde cualquier punto de España", REMOTE),
        ("Ofrecemos teletrabajo y horario flexible", REMOTE),
        ("Fully remote position, distributed team", REMOTE),
        ("This is a remote-first company", REMOTE),
        ("Puesto presencial en nuestra sede de Madrid", ONSITE),
        ("On-site role, five days a week", ONSITE),
        ("Modelo híbrido: 3 días en casa, 2 en oficina", HYBRID),
        ("Trabajo hibrido", HYBRID),
        ("Hybrid working arrangement", HYBRID),
    ],
)
def test_the_description_decides(description, expected):
    assert detect_work_mode(description=description) == expected


def test_remote_and_onsite_together_mean_hybrid():
    """A posting offering both is describing a split week, not a contradiction."""
    text = "Teletrabajo dos días por semana, el resto presencial en Madrid"

    assert detect_work_mode(description=text) == HYBRID


def test_an_unstated_mode_is_unknown_rather_than_guessed():
    text = "Buscamos un desarrollador backend con experiencia en Python."

    assert detect_work_mode(description=text) is None


def test_the_title_and_location_are_read_too():
    assert detect_work_mode(title="Backend Engineer (Remote)") == REMOTE
    assert detect_work_mode(location="Remote - Spain") == REMOTE


def test_the_source_flag_is_used_when_the_text_says_nothing():
    assert detect_work_mode(description="Backend role.", is_remote=True) == REMOTE


def test_the_text_overrides_the_source_flag():
    """JobSpy's is_remote is a board's checkbox; the posting itself is better evidence."""
    text = "El puesto es presencial en nuestras oficinas de Valencia"

    assert detect_work_mode(description=text, is_remote=True) == ONSITE


@pytest.mark.parametrize(
    "description",
    [
        # Benefits copy inside a remote posting.
        "Fully remote team. Compensated onsite retreats at our Bilbao HQ.",
        # Boilerplate about other roles at the company.
        "This is a remote role. A limited number of roles remain office-based "
        "due to the nature of their job responsibilities.",
    ],
)
def test_incidental_english_onsite_words_do_not_make_a_remote_job_hybrid(description):
    """Taken from real stored offers: this rule got 3 of 4 of them wrong before."""
    assert detect_work_mode(description=description) == REMOTE


def test_an_office_mention_alone_is_not_onsite():
    """Remote postings routinely mention where the company's offices are."""
    text = "Somos una empresa 100% remota. Nuestras oficinas están en Barcelona."

    assert detect_work_mode(description=text) == REMOTE


def test_nothing_at_all_is_unknown():
    assert detect_work_mode() is None
