import zipfile
from pathlib import Path

from aje.extraction.linkedin import parse_linkedin_zip


def _make_zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def test_parses_known_csvs(tmp_path):
    z = tmp_path / "linkedin.zip"
    _make_zip(
        z,
        {
            "Skills.csv": "Name\nPython\nDocker\n",
            "Positions.csv": (
                "Company Name,Title,Description,Started On,Finished On\n"
                "Acme,Backend Dev,Built APIs,Jan 2020,Dec 2022\n"
            ),
            "Education.csv": (
                "School Name,Degree Name,Start Date,End Date\n"
                "UPM,MSc CS,2015,2017\n"
            ),
            "Languages.csv": "Name,Proficiency\nSpanish,Native\n",
        },
    )
    cp = parse_linkedin_zip(z)
    assert {s.name for s in cp.skills} == {"Python", "Docker"}
    assert cp.experiences[0].company == "Acme"
    assert cp.experiences[0].bullets == ["Built APIs"]
    assert cp.education[0].institution == "UPM"
    assert cp.languages[0].name == "Spanish"


def test_tolerates_missing_csvs(tmp_path):
    z = tmp_path / "linkedin.zip"
    _make_zip(z, {"Skills.csv": "Name\nGo\n"})
    cp = parse_linkedin_zip(z)
    assert [s.name for s in cp.skills] == ["Go"]
    assert cp.experiences == []
