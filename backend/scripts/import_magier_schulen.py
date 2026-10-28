"""Import the Magier's 4 elemental schools ("Elementarmagieschulen") and 16
subschools ("Unterschulen") from
https://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Magier
into the seed JSON files. Texts are parsed from the live page at run time
(checked 2026-10-28), like `import_kleriker_unterdomaenen.py`.

Both become more `BaseClassOptionChoice` rows in the Magier's `school` group
(`max_choices` 1, so no `exclusion_keys` are needed: picking a subschool
already means not picking its main school or a sibling).

- An elemental school is a school of its own: its three powers are granted
  at 1st/1st/8th level, like the eight standard schools' powers.
- A subschool ("Hauptschule: X", "Ersatzfähigkeit: ... ersetzen A und B")
  copies its main school choice's grants with each replaced power swapped,
  in the page's order, for the new power at the replaced power's level
  (Gegenzauber: Schutz 1st -> Zauber stören, Energieabsorption 6th ->
  Gegenzaubermeisterschaft), same shape as the Kleriker subdomains.

Each new choice also gets one overview row at 1st level named after the
choice (main school / opposed element and what it replaces), since the
sheet otherwise wouldn't show which school a subschool belongs to.
Gegenzaubermeisterschaft's bonus feat Verbesserter Gegenzauber is a
`base_class_ability_granted_feats` row.

Not modeled (text only, like the standard schools): the bonus spell slot for
school spells and the forbidden schools — an elemental school's mandatory
opposed element included (forbidden schools aren't modeled at all yet).

Run with the project venv active (writes fixtures only; seed afterwards):
    cd backend && python scripts/import_magier_schulen.py
    python -m app.seed.class_option_seed
    python -m app.seed.class_ability_seed
    python -m app.seed.class_ability_granted_feat_seed
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_jaeger import fetch_text  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
URL = "https://prd.5footstep.de/Expertenregeln/Klassen/Grundklassen/Magier"

ID_NAMESPACE = uuid.UUID("8b4f1d27-6a3e-4c95-b0d2-7e1a9c5f3b64")

MAGIER_ID = "3533626c-bcc9-41c6-a16b-0313bd5ddb9c"
ELEMENTAL_LEVELS = (1, 1, 8)
OPPOSED_SCHOOL = {
    "Elementarmagieschule der Erde": "Elementarmagieschule der Luft",
    "Elementarmagieschule der Luft": "Elementarmagieschule der Erde",
    "Elementarmagieschule des Feuers": "Elementarmagieschule des Wassers",
    "Elementarmagieschule des Wassers": "Elementarmagieschule des Feuers",
}

# Replaced-power names as the page spells them -> the seeded ability name.
REPLACED_NAME_FIXES = {"Blendungsstrahl": "Blendstrahl"}

# New-power names that clash with an existing class ability -> the seeded name.
POWER_NAME_FIXES = {
    "Durch Erde gleiten": "Durch Erde gleiten (Elementarmagieschule der Erde)",
    "Dimensionssprung": "Dimensionssprung (Unterschule der Teleportation)",
}

GRANTED_FEATS = {"Gegenzaubermeisterschaft": "Verbesserter Gegenzauber"}

POWER_LINE = re.compile(r"^(?P<name>[^:()]{2,60}?)\s*\((?P<tag>AF|ÜF|ZF)\)\s*:\s*(?P<text>.*)$")
SCHOOL_HEADING = re.compile(r"^(Elementarmagieschule|Unterschule) de[rsn] \S+$")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def parse_powers(name: str, body: list[str]) -> list[dict]:
    """The "Name (ÜF): text" paragraphs of one school, each with the plain
    paragraphs that follow it."""
    powers: list[dict] = []
    for line in body:
        match = POWER_LINE.match(line)
        if match:
            power_name = POWER_NAME_FIXES.get(match["name"], match["name"])
            powers.append({"name": power_name, "paragraphs": [f"({match['tag']}) {match['text']}"]})
        elif powers:
            powers[-1]["paragraphs"].append(line)
    for power in powers:
        power["description"] = f"{name}: " + "\n\n".join(power["paragraphs"])
    return powers


def replaced_names(line: str) -> list[str]:
    """"Ersatzfähigkeit: Die folgenden Fähigkeiten ersetzen Schutz und
    Energieabsorption:" -> ["Schutz", "Energieabsorption"]."""
    target = re.split(r" ersetz(?:t|en) ", line, maxsplit=1)[1].rstrip(":. ")
    return [REPLACED_NAME_FIXES.get(part.strip(), part.strip()) for part in target.split(" und ")]


def parse_schools() -> list[dict]:
    lines = fetch_text(URL).split("\n")
    # Skip the table of contents: the content starts at the intro paragraph.
    content_start = next(i for i, line in enumerate(lines) if line.startswith("Magier zwingen der Realität"))
    end_marker = next(i for i, line in enumerate(lines) if line.startswith("Regelwerke, Expertenregeln"))
    starts = [i for i in range(content_start, end_marker) if SCHOOL_HEADING.match(lines[i])]
    schools = []
    for k, start in enumerate(starts):
        name = lines[start]
        body = lines[start + 1 : starts[k + 1] if k + 1 < len(starts) else end_marker]
        if "Unterschulen" in body:  # the next section's heading and intro
            body = body[: body.index("Unterschulen")]
        powers = parse_powers(name, body)
        if name.startswith("Elementarmagieschule"):
            assert len(powers) == 3, (name, [p["name"] for p in powers])
            schools.append(
                {
                    "name": name,
                    "powers": powers,
                    "overview": "\n\n".join(
                        [
                            body[0],
                            f"Verbotene Schule: {OPPOSED_SCHOOL[name]} (Pflicht); "
                            "eine zweite Verbotene Schule ist nicht nötig. Bonuszauberplatz pro Zaubergrad für "
                            "einen Zauber der Liste der Elementarmagieschulen.",
                        ]
                    ),
                }
            )
            continue
        main_line = next(line for line in body if line.startswith("Hauptschule:"))
        replace_line = next(line for line in body if line.startswith("Ersatzfähigkeit:"))
        replaced = replaced_names(replace_line)
        assert len(replaced) == len(powers), (name, replaced, [p["name"] for p in powers])
        schools.append(
            {
                "name": name,
                "main": main_line.split(":", 1)[1].strip(" ."),
                "powers": powers,
                "replaced": replaced,
                "overview": "\n\n".join([main_line.rstrip(".") + ".", replace_line.rstrip(":") + "."]),
            }
        )
    assert sum(s["name"].startswith("Elementarmagieschule") for s in schools) == 4, [s["name"] for s in schools]
    assert sum(s["name"].startswith("Unterschule") for s in schools) == 16, [s["name"] for s in schools]
    return schools


def main() -> None:
    schools = parse_schools()

    group = next(g for g in load("base_class_option_groups.json") if g["base_class_id"] == MAGIER_ID and g["key"] == "school")
    choices = load("base_class_option_choices.json")
    abilities = load("base_class_abilities.json")
    grants = load("base_class_ability_grants.json")
    granted_feats = load("base_class_ability_granted_feats.json")
    feat_by_name = {f["name"]: f for f in load("base_feats.json")}
    ability_by_id = {a["id"]: a for a in abilities}

    # Drop this script's own earlier output.
    own_choice_ids = {uid("choice", s["name"]) for s in schools}
    choices = [c for c in choices if c["id"] not in own_choice_ids]
    grants = [g for g in grants if g["option_choice_id"] not in own_choice_ids]
    own_ability_ids = {uid("ability", s["name"], p["name"]) for s in schools for p in s["powers"]}
    existing_names = {a["name"] for a in abilities if a["id"] not in own_ability_ids}

    for s in schools:
        choice_id = uid("choice", s["name"])
        choices.append({"id": choice_id, "group_id": group["id"], "name": s["name"]})

        overview_id = uid("ability", s["name"], "overview")
        abilities.append({"id": overview_id, "name": s["name"], "description": s["overview"]})
        grants.append(
            {
                "id": uid("grant", choice_id, "overview"),
                "base_class_id": MAGIER_ID,
                "ability_id": overview_id,
                "option_choice_id": choice_id,
                "level": 1,
            }
        )

        power_ids = {}
        for power in s["powers"]:
            assert power["name"] not in existing_names, f"name clash: {power['name']}"
            power_ids[power["name"]] = uid("ability", s["name"], power["name"])
            abilities.append({"id": power_ids[power["name"]], "name": power["name"], "description": power["description"]})
            if power["name"] in GRANTED_FEATS:
                granted_feats.append(
                    {
                        "id": uid("granted_feat", s["name"], power["name"]),
                        "ability_id": power_ids[power["name"]],
                        "feat_id": feat_by_name[GRANTED_FEATS[power["name"]]]["id"],
                    }
                )

        if "main" not in s:
            for power, level in zip(s["powers"], ELEMENTAL_LEVELS):
                grants.append(
                    {
                        "id": uid("grant", choice_id, power["name"]),
                        "base_class_id": MAGIER_ID,
                        "ability_id": power_ids[power["name"]],
                        "option_choice_id": choice_id,
                        "level": level,
                    }
                )
            continue

        main_choice = next(c for c in choices if c["group_id"] == group["id"] and c["name"] == s["main"])
        main_grants = [g for g in grants if g["option_choice_id"] == main_choice["id"]]
        swap = {}
        for old, new in zip(s["replaced"], s["powers"]):
            matching = [g for g in main_grants if ability_by_id[g["ability_id"]]["name"] == old]
            assert len(matching) == 1, (s["name"], old)
            swap[matching[0]["id"]] = power_ids[new["name"]]
        for grant in main_grants:
            grants.append(
                {
                    **grant,
                    "id": uid("grant", choice_id, grant["id"]),
                    "ability_id": swap.get(grant["id"], grant["ability_id"]),
                    "option_choice_id": choice_id,
                }
            )

    assert len({(c["group_id"], c["name"]) for c in choices}) == len(choices), "duplicate (group_id, name)"
    save("base_class_option_choices.json", choices)
    save("base_class_abilities.json", abilities)
    save("base_class_ability_grants.json", grants)
    save("base_class_ability_granted_feats.json", granted_feats)

    count = sum(1 for c in choices if c["group_id"] == group["id"])
    print(f"school: {count} choices")


if __name__ == "__main__":
    main()
