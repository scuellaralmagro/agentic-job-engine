import csv
import io
import zipfile
from pathlib import Path

from aje.extraction.schema import (
    CandidateProfile,
    Education,
    Experience,
    Language,
    Skill,
)


def parse_linkedin_zip(path: Path) -> CandidateProfile:
    with zipfile.ZipFile(path) as zf:
        by_base = {Path(n).name: n for n in zf.namelist()}

        def rows(base: str) -> list[dict]:
            full = by_base.get(base)
            if not full:
                return []
            with zf.open(full) as fh:
                reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
                return list(reader)

        skills = [
            Skill(name=r["Name"].strip())
            for r in rows("Skills.csv")
            if r.get("Name", "").strip()
        ]
        experiences = [
            Experience(
                company=r.get("Company Name", "").strip(),
                title=r.get("Title", "").strip(),
                description=(r.get("Description") or "").strip() or None,
                start=(r.get("Started On") or "").strip() or None,
                end=(r.get("Finished On") or "").strip() or None,
                bullets=(
                    [r["Description"].strip()]
                    if r.get("Description", "").strip()
                    else []
                ),
            )
            for r in rows("Positions.csv")
            if r.get("Company Name", "").strip() or r.get("Title", "").strip()
        ]
        education = [
            Education(
                institution=r.get("School Name", "").strip(),
                degree=(r.get("Degree Name") or "").strip() or None,
                start=(r.get("Start Date") or "").strip() or None,
                end=(r.get("End Date") or "").strip() or None,
            )
            for r in rows("Education.csv")
            if r.get("School Name", "").strip()
        ]
        languages = [
            Language(
                name=r["Name"].strip(),
                level=(r.get("Proficiency") or "").strip() or None,
            )
            for r in rows("Languages.csv")
            if r.get("Name", "").strip()
        ]

    return CandidateProfile(
        skills=skills,
        experiences=experiences,
        education=education,
        languages=languages,
    )
