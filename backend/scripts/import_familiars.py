"""Familiars — roadmap slice 10, step 4. Fetches the PRD pages, parses them
and writes the seed fixtures; it doesn't touch the database.

Sources:
- http://prd.5footstep.de/Monsterhandbuch/Vertraute — the eleven familiar
  statblocks (Affe … Wiesel). Parsed into one `BaseRace` row per species
  (`companion_kind` "familiar") and one `BaseCompanionSpeciesStage` row
  (level 1: size, ability scores, speeds, natural armor, natural attacks,
  racial skill modifiers "Volksmodifikatoren", the species' feats) plus its
  special abilities (senses, Gift) — reusing the animal companion
  importer's ability rows by name.
- http://prd.5footstep.de/Grundregelwerk/Klassen/Magier, section
  "Vertrauter": the master bonus per species (one `BaseRaceAbility`
  "Bonus für den Meister" per species, its text; the bonus itself is
  computed by `rules/companions.py`'s `FAMILIAR_MASTER_HANDLERS`) and the
  familiar table by master level (`base_familiar_progression.json`, the
  PRD's two-level brackets expanded to 1–20, `…_abilities.json` with the
  abilities' PRD texts as new `BaseClassAbility` rows).
- Entitlements: one "primary" familiar slot per familiar trigger ability
  (Magier "Vertrauter (Magier)", Hexenmeister "Arkane Verbindung",
  Kampfmagus "Vertrauter", Hexe "Hexenvertrauter" — the last one is seeded
  by `build_companion_level_sources.py`, run that first) allowing all
  eleven species.

Not taken from the statblocks: the species' own skill ranks (a 1-HD animal
has a single rank, the statblock only shows totals) — a familiar uses its
master's ranks, which are at least as high for every skill the master has
trained (`app/companions.py`).

Run with the project venv active:
    cd backend && python scripts/build_companion_level_sources.py
    python scripts/import_familiars.py
    python -m app.seed.race_seed && python -m app.seed.class_ability_seed
    python -m app.seed.companion_seed
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_companion_species import (  # noqa: E402
    ATTACK_KINDS,
    DAEMMERSICHT_ABILITY_ID,
    fetch_text,
)
from import_companion_species import uid as companion_uid  # noqa: E402

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
ID_NAMESPACE = uuid.UUID("7f3c9a1e-2b4d-4c6e-9a8f-1d2e3c4b5a69")

STATBLOCK_SOURCE = "http://prd.5footstep.de/Monsterhandbuch/Vertraute"
RULES_SOURCE = "http://prd.5footstep.de/Grundregelwerk/Klassen/Magier"
SOURCE_LABEL = "Monsterhandbuch: Vertraute"

SIZES = {"Sehr kleines": "Sehr klein", "Winziges": "Winzig", "Kleines": "Klein"}
SPEED_KEYS = {"Klettern": "climb", "Kletterm": "climb", "Schwimmen": "swim", "Fliegen": "fly", "Graben": "burrow"}
SENSES = ("Dämmersicht", "Geruchssinn", "Blindgespür")

# (class name, trigger ability name, option choice name or None)
SLOT_TRIGGERS = [
    ("Magier", "Vertrauter (Magier)", "Vertrauter"),
    ("Hexenmeister", "Arkane Verbindung", "Arkane Blutlinie"),
    ("Kampfmagus", "Vertrauter", "Vertrauter"),
    ("Hexe", "Hexenvertrauter", None),
]


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


def meters(text: str) -> float | int:
    value = float(text.replace(",", "."))
    return int(value) if value.is_integer() else value


def parse_statblocks(text: str) -> list[dict]:
    """One dict per "<Name> HG …" statblock."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if re.match(r"^\S+ HG ", line)]
    blocks = []
    for index, start in enumerate(starts):
        block = lines[start : starts[index + 1] if index + 1 < len(starts) else len(lines)]
        blocks.append(parse_block(block))
    return blocks


def _line(block: list[str], prefix: str) -> str:
    return next((line for line in block if line.startswith(prefix)), "")


def parse_block(block: list[str]) -> dict:
    name = block[0].split(" HG ")[0]
    size_word = re.match(r"^N (\S+(?: \S+)?) Tier$", next(line for line in block if line.endswith(" Tier"))).group(1)
    size = SIZES[size_word]

    senses = _line(block, "INI").split("Sinne", 1)[1].split(";")[0]
    abilities = [sense for sense in SENSES if sense in senses]
    if any(line.startswith("Gift (AF)") for line in block):
        abilities.append("Gift")

    armor = re.search(r"\+(\d+) natürlich", _line(block, "RK "))
    natural_armor = int(armor.group(1)) if armor else 0

    speeds: dict[str, float | int] = {}
    fly_maneuverability = None
    movement = _line(block, "Bewegungsrate").removeprefix("Bewegungsrate").strip()
    # Split on ", " before a word — "4,50 m" keeps its decimal comma.
    for part in re.split(r",\s+(?=\D)", movement):
        part = part.strip()
        match = re.match(r"^(?:(\S+) )?([\d,]+) m(?: \((\w+)\))?$", part)
        mode, value, maneuverability = match.groups()
        key = SPEED_KEYS[mode] if mode else "land"
        speeds[key] = meters(value)
        if key == "fly":
            fly_maneuverability = maneuverability

    attacks = []
    melee = _line(block, "Nahkampf").removeprefix("Nahkampf").strip()
    for part in filter(None, (p.strip() for p in melee.split(","))):
        match = re.match(r"^(?:(\d+) )?(.+?) [+-]\d+\s*\((\d+W\d+)[+-]?\d*(?: plus (.+))?\)$", part)
        count, attack_name, dice, rider = match.groups()
        damage_type, secondary = ATTACK_KINDS[attack_name]
        attacks.append(
            {
                "name": attack_name,
                "count": int(count or 1),
                "dice": dice,
                "damage_type": damage_type,
                "secondary": secondary,
                "note": rider,
                "alternative": False,
            }
        )

    scores_line = _line(block, "ST ")
    scores = {key: int(value) for key, value in re.findall(r"(ST|GE|KO|IN|WE|CH) (\d+)", scores_line)}

    feats = [
        feat.strip()
        for feat in re.split(r",(?![^(]*\))", _line(block, "Talente").removeprefix("Talente").strip())
        if feat.strip()
    ]
    skill_line = _line(block, "Fertigkeiten")
    racial = skill_line.split("Volksmodifikatoren", 1)[1] if "Volksmodifikatoren" in skill_line else ""
    skill_modifiers = {skill: int(value) for skill, value in re.findall(r"([A-ZÄÖÜ][a-zäöüß]+) \+(\d+)", racial)}
    return {
        "name": name,
        "size": size,
        "abilities": abilities,
        "natural_armor": natural_armor,
        "speeds": speeds,
        "fly_maneuverability": fly_maneuverability,
        "attacks": attacks,
        "scores": scores,
        "feats": feats,
        "skill_modifiers": skill_modifiers,
    }


def parse_master_bonuses(lines: list[str], start: int) -> dict[str, str]:
    """"Vertrauter | Speziell |" table: species -> master bonus text."""
    header = next(i for i in range(start, len(lines)) if lines[i].startswith("Vertrauter | Speziell"))
    bonuses = {}
    for line in lines[header + 1 :]:
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if len(cells) != 2:
            break
        bonuses[cells[0].rstrip("*")] = cells[1]
    return bonuses


def parse_familiar_table(lines: list[str], start: int) -> list[tuple[int, int, int, int, list[str]]]:
    """(from, to, natural armor, IN, abilities) per two-level bracket."""
    header = next(i for i in range(start, len(lines)) if lines[i].startswith("Stufe des Meisters |"))
    rows = []
    for line in lines[header + 1 :]:
        cells = [cell.strip() for cell in line.split("|")]
        match = re.match(r"^(\d+)-(\d+)$", cells[0])
        if not match:
            break
        specials = [] if cells[3] == "-" else [s.strip() for s in cells[3].split(",")]
        rows.append((int(match.group(1)), int(match.group(2)), int(cells[1]), int(cells[2]), specials))
    return rows


def parse_ability_texts(lines: list[str], start: int, names: set[str]) -> dict[str, str]:
    texts = {}
    for line in lines[start:]:
        match = re.match(r"^(.+?)(?: \((AF|ÜF|ZF)\))?: (.+)$", line)
        if match and match.group(1) in names and match.group(1) not in texts:
            tag = f"({match.group(2)}) " if match.group(2) else ""
            texts[match.group(1)] = tag + match.group(3)
    return texts


def main() -> None:
    blocks = parse_statblocks(fetch_text(STATBLOCK_SOURCE))
    assert len(blocks) == 11, [b["name"] for b in blocks]
    rules = fetch_text(RULES_SOURCE).split("\n")
    section = max(i for i, line in enumerate(rules) if line == "Vertrauter")
    master_bonuses = parse_master_bonuses(rules, section)
    table = parse_familiar_table(rules, section)
    ability_names = {name for *_rest, specials in table for name in specials}
    ability_texts = parse_ability_texts(rules, section, ability_names)
    assert ability_names == set(ability_texts), ability_names ^ set(ability_texts)

    skill_id_by_name = {s["name"]: s["id"] for s in load("base_skills.json")}
    feat_id_by_name = {f["name"]: f["id"] for f in load("base_feats.json")}
    species_ability_ids = {name: companion_uid("species-ability", name) for name in ("Geruchssinn", "Blindgespür", "Gift")}
    species_ability_ids["Dämmersicht"] = DAEMMERSICHT_ABILITY_ID

    races = load("base_races.json")
    race_abilities = load("base_race_abilities.json")
    stages = load("base_companion_species_stages.json")
    stage_abilities = load("base_companion_species_stage_abilities.json")
    race_ids = []
    for block in blocks:
        name = block["name"]
        race_id = uid("familiar", name)
        race_ids.append(race_id)
        races.append(
            {
                "id": race_id,
                "code": "familiar-" + name.lower().replace("ö", "oe").replace("ä", "ae").replace("ü", "ue"),
                "name": name,
                "short_description": f"Vertrauter ({SOURCE_LABEL}). Bonus für den Meister: {master_bonuses[name]}",
                "companion_kind": "familiar",
                "creature_type": "Tier",
                "source": SOURCE_LABEL,
            }
        )
        bonus_id = uid("master-bonus", name)
        race_abilities.append({"id": bonus_id, "name": "Bonus für den Meister", "description": master_bonuses[name]})
        feats = []
        for feat in block["feats"]:
            match = re.match(r"^(.+?)(?: \((.+)\))?$", feat)
            feats.append(
                {
                    "feat_id": feat_id_by_name[match.group(1)],
                    "chosen_skill_id": skill_id_by_name[match.group(2)] if match.group(2) else None,
                }
            )
        stage_id = uid("familiar-stage", name)
        stages.append(
            {
                "id": stage_id,
                "race_id": race_id,
                "level": 1,
                "size": block["size"],
                "natural_armor": block["natural_armor"],
                "ability_scores": block["scores"],
                "speeds": block["speeds"],
                "fly_maneuverability": block["fly_maneuverability"],
                "natural_attacks": block["attacks"],
                "skill_modifiers": {skill_id_by_name[s]: v for s, v in block["skill_modifiers"].items()},
                "feats": feats,
            }
        )
        for ability_id in [species_ability_ids[a] for a in block["abilities"]] + [bonus_id]:
            stage_abilities.append(
                {"id": uid("familiar-stage-ability", stage_id, ability_id), "stage_id": stage_id, "ability_id": ability_id}
            )
        print(f"{name}: {block['size']}, {block['speeds']}, {len(block['attacks'])} attacks, {block['feats']}")

    save("base_races.json", races)
    save("base_race_abilities.json", race_abilities)
    save("base_companion_species_stages.json", stages)
    save("base_companion_species_stage_abilities.json", stage_abilities)

    # ---- familiar table ----
    class_abilities = load("base_class_abilities.json")
    ability_ids = {}
    for name in sorted(ability_names):
        ability_ids[name] = uid("familiar-ability", name)
        class_abilities.append({"id": ability_ids[name], "name": name, "description": ability_texts[name]})
    save("base_class_abilities.json", class_abilities)
    progression, progression_abilities = [], []
    for first, last, natural_armor, intelligence, specials in table:
        for level in range(first, last + 1):
            progression.append(
                {"id": uid("familiar-progression", str(level)), "level": level, "natural_armor": natural_armor,
                 "intelligence": intelligence}
            )
        for name in specials:
            progression_abilities.append(
                {"id": uid("familiar-progression-ability", str(first), name), "level": first,
                 "ability_id": ability_ids[name]}
            )
    assert len(progression) == 20
    save("base_familiar_progression.json", progression)
    save("base_familiar_progression_abilities.json", progression_abilities)

    # ---- entitlements ----
    classes = {c["name"]: c["id"] for c in load("base_classes.json") if c["arch_class_of"] is None}
    groups = {g["id"]: g["base_class_id"] for g in load("base_class_option_groups.json")}
    choices = load("base_class_option_choices.json")
    ability_name_by_id = {a["id"]: a["name"] for a in class_abilities}
    grants = load("base_class_ability_grants.json")
    slot_grants = load("base_companion_slot_grants.json")
    slot_species = load("base_companion_slot_species.json")
    for class_name, ability_name, choice_name in SLOT_TRIGGERS:
        class_id = classes[class_name]
        choice_ids = (
            {c["id"] for c in choices if c["name"] == choice_name and groups.get(c["group_id"]) == class_id}
            if choice_name
            else {None}
        )
        trigger_ids = {
            g["ability_id"]
            for g in grants
            if g["base_class_id"] == class_id
            and g["option_choice_id"] in choice_ids
            and ability_name_by_id[g["ability_id"]] == ability_name
        }
        assert len(trigger_ids) == 1, (class_name, ability_name, trigger_ids)
        trigger_id = trigger_ids.pop()
        grant_id = uid("familiar-slot", trigger_id)
        slot_grants.append(
            {"id": grant_id, "class_ability_id": trigger_id, "track": "familiar", "slot_key": "primary",
             "level_offset": 0, "divisor": 1, "minimum": None}
        )
        for race_id in race_ids:
            slot_species.append(
                {"id": uid("familiar-slot-species", grant_id, race_id), "slot_grant_id": grant_id, "race_id": race_id,
                 "master_sizes": None, "min_level": None}
            )
    save("base_companion_slot_grants.json", slot_grants)
    save("base_companion_slot_species.json", slot_species)
    print(f"Familiars: {len(blocks)} | table rows: {len(progression)} | slots: {len(SLOT_TRIGGERS)}")


if __name__ == "__main__":
    main()
