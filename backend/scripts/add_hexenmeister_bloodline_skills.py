"""Adds the missing per-bloodline bonus class skill to Hexenmeister
(Sorcerer) - http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister
says explicitly (its "Blutlinien:" intro paragraph): "Jeder Hexenmeister hat
eine Quelle seiner Macht... was ihm Zauber, Bonustalente, eine zusätzliche
Klassenfertigkeit und andere besondere Fähigkeiten verleiht." Each of the 10
bloodline sections has its own "Klassenfertigkeit: X" line - none of them
were captured when the bloodline import (`import_hexenmeister_bloodlines.py`)
ran, since that script only extracted the "Bonustalente:" paragraph.

Found and fixed the same way as Mystiker/Oracle's per-mystery bonus skills
(see the conversation this was scoped from, and todos.md's 2026-08-02
Nachträge): `BaseClassSkill.option_choice_id` scoped to the bloodline choice,
same field, same mechanism, no new schema needed - Mystiker's mysteries
weren't a one-off, this is exactly the recurrence the field was built for.

One bloodline needs a deliberate approximation: "Arkane Blutlinie" grants
"Wissen (freie Wahl)" - a free pick of any one Wissen sub-skill, not a fixed
skill. There's no "pick one from a category" primitive on BaseClassSkill (it
associates one fixed skill per option_choice_id, same as every other class
skill grant in this codebase), so - same choice already made for Mystiker's
Wissen mystery's "Schätzen und alle Wissensfertigkeiten" - this grants *all*
10 Wissen sub-skills as class skills for Arkane-Blutlinie characters, a
conservative over-approximation (every one of them *can* be a class skill,
just not narrowed to the one the player would actually pick) rather than an
unrepresented mechanic.

Run with the project venv active and the database up (writes fixture JSON
only - run the normal seed scripts afterward to load it):
    cd backend && python scripts/add_hexenmeister_bloodline_skills.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"

ID_NAMESPACE = uuid.UUID("d4a1f8b0-6e2a-4b7a-8a5a-2f6a7b9c1d3e")  # same namespace as import_mystiker.py

HEXENMEISTER_ID = "ceb02ad1-268c-4a1c-a7c9-ea8a1cbbe67e"

BLOODLINE_CHOICE_ID = {
    "Abnormale Blutlinie": "b37e5ed9-e3e8-4faa-975b-a3f0948e7b99",
    "Arkane Blutlinie": "11eaf8ef-5b49-4a6b-a096-02ed885a38f7",
    "Blutlinie des Grabes": "e6a81329-81d2-4a7f-9982-04e86250a06d",
    "Dämonische Blutlinie": "9db48ab4-d614-4c2e-b6bb-03b8951dbde4",
    "Drachenblutlinie": "942a3165-44e9-423d-a2db-c22006fb3262",
    "Elementare Blutlinie": "3aeaec6d-0ab8-4222-ad99-5a61dd98ce47",
    "Feenblutlinie": "73165db9-ab05-4711-99f1-a2a338062edb",
    "Himmlische Blutlinie": "5db99c84-10e7-4d11-8e78-1f14d47263ed",
    "Schicksalhafte Blutlinie": "2b0b14c7-ada4-4106-aad5-396e601f4801",
    "Teuflische Blutlinie": "24642261-76ae-4113-bb43-c6120f613aad",
}

ALL_WISSEN_SKILLS = [
    "Wissen (Adel)",
    "Wissen (Arkanes)",
    "Wissen (Baukunst)",
    "Wissen (Die Ebenen)",
    "Wissen (Geographie)",
    "Wissen (Geschichte)",
    "Wissen (Gewölbekunde)",
    "Wissen (Lokales)",
    "Wissen (Natur)",
    "Wissen (Religion)",
]

# Bloodline -> granted skill(s), transcribed from each bloodline's own
# "Klassenfertigkeit:" line.
BLOODLINE_SKILLS = {
    "Abnormale Blutlinie": ["Wissen (Gewölbekunde)"],
    "Arkane Blutlinie": ALL_WISSEN_SKILLS,  # "Wissen (freie Wahl)" - see module docstring
    "Blutlinie des Grabes": ["Wissen (Religion)"],
    "Dämonische Blutlinie": ["Wissen (Die Ebenen)"],
    "Drachenblutlinie": ["Wahrnehmung"],
    "Elementare Blutlinie": ["Wissen (Die Ebenen)"],
    "Feenblutlinie": ["Wissen (Natur)"],
    "Himmlische Blutlinie": ["Heilkunde"],
    "Schicksalhafte Blutlinie": ["Wissen (Geschichte)"],
    "Teuflische Blutlinie": ["Diplomatie"],
}


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def main() -> None:
    skills = json.loads((SEED_DIR / "base_skills.json").read_text(encoding="utf-8"))
    skill_id_by_name = {row["name"]: row["id"] for row in skills}
    for names in BLOODLINE_SKILLS.values():
        for name in names:
            assert name in skill_id_by_name, f"missing skill: {name}"

    class_skills = json.loads((SEED_DIR / "base_class_skills.json").read_text(encoding="utf-8"))
    deduped = {row["id"]: row for row in class_skills}

    for bloodline, names in BLOODLINE_SKILLS.items():
        choice_id = BLOODLINE_CHOICE_ID[bloodline]
        for name in names:
            row_id = uid("hexenmeister-classskill", bloodline, name)
            deduped[row_id] = {
                "id": row_id,
                "base_class_id": HEXENMEISTER_ID,
                "skill_id": skill_id_by_name[name],
                "option_choice_id": choice_id,
            }

    (SEED_DIR / "base_class_skills.json").write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    added = sum(len(v) for v in BLOODLINE_SKILLS.values())
    print(f"Added/updated {added} bloodline class-skill rows.")


if __name__ == "__main__":
    main()
