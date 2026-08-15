import pytest

from aje.discovery.location import canonical_location


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Indeed sends "City, REGION, COUNTRY"; Tecnoempleo sends a bare city. The
        # whole point of the function is that these two collapse to one key.
        ("Madrid, MD, ES", "madrid"),
        ("Madrid", "madrid"),
        ("Barcelona, CT, ES", "barcelona"),
        ("Barcelona", "barcelona"),
        # accents are stripped, so the two boards' spellings agree
        ("Málaga, AN, ES", "malaga"),
        ("Málaga", "malaga"),
        ("A Coruña", "a coruna"),
        # multi-word cities keep their words
        ("Pozuelo de Alarcón, MD, ES", "pozuelo de alarcon"),
        ("Palma de Mallorca, IB, ES", "palma de mallorca"),
        # degenerate values Indeed really sends when it has no city
        ("MD, ES", "md"),
        ("ES", "es"),
        # nothing at all
        (None, ""),
        ("", ""),
        ("   ", ""),
    ],
)
def test_canonical_location_reconciles_the_board_formats(raw, expected):
    assert canonical_location(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "100% remoto",  # tecnoempleo
        "En remoto, ES",  # indeed
        "Remote",
        "Teletrabajo",
        "TELETRABAJO, ES",
    ],
)
def test_remote_collapses_to_one_token(raw):
    """A remote posting has no city and the boards spell it differently, so without
    this the likeliest future duplicate — a remote role on both boards — never merges."""
    assert canonical_location(raw) == "remote"


def test_different_cities_stay_different():
    """The regression guard for the whole feature: five of the seven duplicate groups
    in the live DB are real openings in different cities, kept apart only by this."""
    assert canonical_location("Madrid, MD, ES") != canonical_location("Málaga, AN, ES")
    assert canonical_location("Madrid") != canonical_location("Barcelona")


def test_a_city_is_not_confused_with_remote():
    """'Remotos' is not a place, but neither is any Spanish city a substring of it —
    the match is on word boundaries so a city merely containing the letters is safe."""
    assert canonical_location("Torremolinos, AN, ES") == "torremolinos"
